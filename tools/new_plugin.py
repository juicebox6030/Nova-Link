#!/usr/bin/env python3
"""Create an independent C99 plugin project for the installed Nova-Link SDK."""

import argparse
from pathlib import Path
import re
import shutil
import sys


TEMPLATES = Path(__file__).resolve().parent / "plugin_templates"
NAME_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
C_KEYWORDS = frozenset("auto break case char const continue default do double else enum "
                      "extern float for goto if inline int long register restrict return "
                      "short signed sizeof static struct switch typedef union unsigned "
                      "void volatile while alignas alignof atomic bool complex imaginary "
                      "noreturn static-assert thread-local".split())
# The installed SDK's static host has sixteen registration slots.
MAX_REQUIREMENTS = 15


def valid_name(value):
    if not NAME_RE.fullmatch(value) or len(value) > 63:
        raise argparse.ArgumentTypeError("names must be 1..63 lowercase ASCII letters/digits separated by hyphens")
    return value


def plugin_name(value):
    value = valid_name(value)
    if value in C_KEYWORDS or value.startswith(("nl-", "nova-")) or value == "scaffold-transport":
        raise argparse.ArgumentTypeError("name uses a reserved C, SDK, or scaffold identifier")
    return value


def render(template, values):
    for key, value in values.items():
        template = template.replace("@" + key + "@", value)
    if re.search(r"@[A-Z_]+@", template):
        raise ValueError("unresolved template placeholder")
    return template


def smoke_providers(kind, requirements):
    """Smoke providers deliberately have no hardware or external service work."""
    providers = list(requirements)
    definitions = []
    manifest = []
    for index, name in enumerate(providers):
        transport = kind == "application" and name == "radio-link"
        definitions.append('    nl_module provider_%d = {.name = "%s", .version = "1",\n'
                           '        .kind = %s%s};' %
                           (index, name, "NL_MODULE_TRANSPORT" if transport else "NL_MODULE_SERVICE",
                            ", .hooks = {.start = transport_start, .stop = transport_stop}" if transport else ""))
        manifest.append("&provider_%d" % index)
    return "\n".join(definitions), ", " + ", ".join(manifest) if manifest else ""


def conformance_providers(kind, requirements):
    definitions = []
    for index, name in enumerate(requirements):
        transport = kind == "application" and name == "radio-link"
        definitions.append('    state->providers[%d] = (nl_module){.name = "%s", .version = "1",\n'
                           '        .kind = %s%s};\n'
                           '    fixture->modules[%d] = &state->providers[%d];' %
                           (index, name, "NL_MODULE_TRANSPORT" if transport else "NL_MODULE_SERVICE",
                            ", .hooks = {.start = transport_start, .stop = transport_stop, .context = state}"
                            if transport else "", index + 1, index))
    return "\n".join(definitions)


def generate(name, kind, output, zone, requirements):
    """Create only a new destination; never replace an existing project."""
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists; choose a new project directory")
    if name in requirements:
        raise ValueError("a plugin cannot require itself")
    if len(set(requirements)) != len(requirements):
        raise ValueError("duplicate required providers")
    if kind == "application" and "radio-link" not in requirements:
        requirements = ["radio-link"] + requirements
    if name in requirements:
        raise ValueError("a plugin cannot require itself (application default is radio-link)")
    if len(requirements) > MAX_REQUIREMENTS:
        raise ValueError("at most 15 providers fit alongside a plugin in the static host")
    prefix = name.replace("-", "_")
    provider_definitions, provider_manifest = smoke_providers(kind, requirements)
    values = {
        "NAME": name, "PREFIX": prefix, "GUARD": prefix.upper(), "KIND": kind,
        "ZONE": str(zone),
        "DEPENDENCY_DECL": '    static const char *const dependencies[] = {' +
                           ", ".join('"%s"' % requirement for requirement in requirements) + '};\n'
                           if requirements else "",
        "DEPENDENCY_FIELDS": '        .requires = dependencies, .require_count = %du,\n' % len(requirements)
                             if requirements else "",
        "PROVIDER_DEFINITIONS": provider_definitions,
        "PROVIDER_MANIFEST": provider_manifest,
        "REQUIREMENTS": ", ".join(requirements) if requirements else "none",
        "CONFORMANCE_PROVIDER_SETUP": conformance_providers(kind, requirements),
        "CONFORMANCE_COUNT": str(1 + len(requirements)),
        "REQUIREMENT_COUNT": str(len(requirements)),
        "CONFORMANCE_ROLE": str({"application": 1, "service": 2, "transport": 3}[kind]),
        "CONFORMANCE_DEFAULT": "ON" if len(requirements) <= (13 if kind == "transport" else 14) else "OFF",
        "CONFORMANCE_LIMIT": str(13 if kind == "transport" else 14),
        "FAULT_TESTS": """    option(NOVA_PLUGIN_FAULT_TESTS "Build deterministic transport fault scenarios" %s)
    if(NOVA_PLUGIN_FAULT_TESTS)
        if(%d GREATER 14)
            message(FATAL_ERROR "Fault scenarios require at most 14 providers; set NOVA_PLUGIN_FAULT_TESTS=OFF")
        endif()
        add_executable(%s_faults examples/faults.c)
        target_link_libraries(%s_faults PRIVATE %s_plugin NovaLink::nova_fault_backend)
        set_target_properties(%s_faults PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
        if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
            target_compile_options(%s_faults PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror)
        endif()
        foreach(scenario clean delayed disconnected congested commit-retry restart)
            add_test(NAME %s_fault_${scenario} COMMAND %s_faults ${scenario})
        endforeach()
    endif()
""" % (("ON" if len(requirements) <= 14 else "OFF", len(requirements)) + ((prefix,) * 7)) if kind == "transport" else "",
        "FAULT_README": """Transport scenarios are individually selectable:

```sh
ctest --test-dir build --output-on-failure -R '_fault_(delayed|disconnected|congested|commit-retry|restart)$'
./build/%s_faults delayed
```

They connect two deterministic logical backends through the generated transport,
exercise exact native payload delivery, and drain ownership before stopping.
They model software queue/timing failures, without claiming device or RF behavior.
Set `NOVA_PLUGIN_FAULT_TESTS=OFF` to omit the scenario executable.
It defaults off above 14 providers because each fault host also registers a
real sender/receiver probe in addition to the transport and its providers.

""" % prefix if kind == "transport" else "",
    }
    files = {
        "CMakeLists.txt": "CMakeLists.txt.in",
        "README.md": "README.md.in",
        "include/%s_plugin.h" % prefix: "%s.h.in" % kind,
        "src/%s_plugin.c" % prefix: "%s.c.in" % kind,
        "examples/smoke.c": "%s_smoke.c.in" % kind,
        "examples/conformance.c": "conformance.c.in",
    }
    if kind == "transport":
        files["examples/faults.c"] = "transport_faults.c.in"
    # Read/render all inputs before creating output, so a broken installation
    # does not leave a partial generated project.
    contents = {path: render((TEMPLATES / template).read_text(encoding="utf-8"), values)
                for path, template in files.items()}
    output.mkdir(parents=True, exist_ok=False)
    try:
        for relative, content in contents.items():
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
    except BaseException:
        shutil.rmtree(output)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog="Build: cmake -S OUTPUT -B OUTPUT/build -DCMAKE_PREFIX_PATH=/path/to/sdk")
    parser.add_argument("name", type=plugin_name, help="unique plugin name, e.g. scene-player")
    parser.add_argument("--kind", choices=("application", "transport", "service"), default="application")
    parser.add_argument("--output", required=True, type=Path, help="new directory; existing files are never replaced")
    parser.add_argument("--zone", type=int, choices=range(1, 8), default=None, help="application data zone (default 1)")
    parser.add_argument("--requires", action="append", type=valid_name, default=[], metavar="PROVIDER",
                        help="additional provider name; repeat for multiple providers (applications include radio-link)")
    arguments = parser.parse_args(argv)
    if arguments.zone is not None and arguments.kind != "application":
        parser.error("--zone applies only to application plugins")
    try:
        generate(arguments.name, arguments.kind, arguments.output,
                 arguments.zone if arguments.zone is not None else 1, arguments.requires)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print("Created %s plugin in %s" % (arguments.kind, arguments.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
