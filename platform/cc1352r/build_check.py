#!/usr/bin/env python3
"""Stage and compile a CC1352R native-protocol check with the pinned TI SDK.

The vendor installation is read-only. Generated project ownership is confined
inside BUILD_DIR/cc1352r-project, which is refreshed on every invocation.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

SDK_VERSION = "7.41.00.17"
PROJECT_NAME = "cc1352r-project"
MARKER = ".nova-build-owner"
OWNER = "Nova-Link CC1352R build-check stage v1\n"
VENDOR_EXAMPLE = Path("examples/rtos/CC1352R1_LAUNCHXL/drivers/empty")
VENDOR_FILES = (
    "empty.c", "README.md", "tirtos7/empty.syscfg",
    "tirtos7/main_tirtos.c", "tirtos7/ticlang/makefile",
    "tirtos7/ticlang/cc13x2_cc26x2_tirtos7.cmd",
)
SOURCES = (
    "status", "fragment", "transport", "stream", "queue", "scheduler",
    "radio", "spi_slave",
)
# TI imports.mak requires paths without spaces. A deliberately narrow alphabet
# also prevents shell/make expansion of paths inside the vendor makefile.
SAFE_PATH = re.compile(r"^[A-Za-z0-9_./+-]+$")


def real_path(value):
    path = Path(value).expanduser().resolve()
    if not SAFE_PATH.fullmatch(str(path)):
        raise ValueError("TI make paths must contain only letters, digits, /, ., _, + or -: " + str(path))
    return path


def require_file(path):
    if not path.is_file():
        raise ValueError("Required file does not exist: " + str(path))


def stage_project(sdk, compiler, sysconfig, build_dir, repo):
    """Validate inputs before refreshing the single script-owned directory."""
    require_file(sdk / ".metadata/product.json")
    metadata = json.loads((sdk / ".metadata/product.json").read_text())
    if (not isinstance(metadata, dict) or
            metadata.get("name") != "simplelink_cc13xx_cc26xx_sdk" or
            metadata.get("version") != SDK_VERSION):
        raise ValueError("Expected SimpleLink CC13xx/CC26xx SDK " + SDK_VERSION)
    require_file(sdk / "imports.mak")
    require_file(compiler / "bin/tiarmclang")
    require_file(compiler / "bin/tiarmobjcopy")
    require_file(sysconfig)
    vendor = sdk / VENDOR_EXAMPLE
    for relative in VENDOR_FILES:
        require_file(vendor / relative)
    require_file(repo / "platform/cc1352r/example/nova_radio_check.c")
    for source in SOURCES:
        require_file(repo / "src" / (source + ".c"))
    if not (repo / "include").is_dir():
        raise ValueError("Repository public headers are missing")

    stage = build_dir / PROJECT_NAME
    # Refuse any destination that could modify the SDK, tool installations, or
    # tracked repository files, including when a parent path resolves a symlink.
    protected = (sdk, compiler, sysconfig.parent, repo / "src", repo / "include",
                 repo / "platform", repo / "tools", repo / "tests", repo / "docs")
    for root in protected:
        if stage == root or stage in root.parents or root in stage.parents:
            raise ValueError("Build stage overlaps a protected source/tool directory: " + str(root))
    if stage.is_symlink():
        raise ValueError("Refusing symlink build stage: " + str(stage))
    if stage.exists():
        marker = stage / MARKER
        if (not stage.is_dir() or marker.is_symlink() or not marker.is_file() or
                marker.read_text() != OWNER):
            raise ValueError("Refusing to replace a stage without the Nova-Link ownership marker: " + str(stage))
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    (stage / MARKER).write_text(OWNER)
    for relative in VENDOR_FILES:
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(vendor / relative, destination)
    shutil.copytree(repo / "include", stage / "nova/include")
    for source in SOURCES:
        shutil.copyfile(repo / "src" / (source + ".c"),
                        stage / "nova" / (source + ".c"))
    shutil.copyfile(repo / "platform/cc1352r/example/nova_radio_check.c",
                    stage / "nova/nova_radio_check.c")
    startup = stage / "tirtos7/main_tirtos.c"
    startup_text = startup.read_text()
    if startup_text.count("#define THREADSTACKSIZE 1024") != 1:
        raise ValueError("Pinned vendor startup stack definition changed")
    startup.write_text(startup_text.replace("#define THREADSTACKSIZE 1024",
                                           "#define THREADSTACKSIZE 2048"))
    makefile = stage / "tirtos7/ticlang/makefile"
    contents = makefile.read_text()
    source_names = ("nova_radio_check",) + SOURCES
    object_names = " ".join("nova_" + name + ".obj" for name in source_names)
    old_objects = "OBJECTS = empty.obj tirtos7_main_tirtos.obj"
    if contents.count(old_objects) != 1:
        raise ValueError("Pinned vendor makefile object definition changed")
    contents = contents.replace(old_objects, "OBJECTS = " + object_names + " tirtos7_main_tirtos.obj")
    for original, replacement in (
            ("NAME = empty", "NAME = nova-radio-check"),
            ("CFLAGS += -I../..", "CFLAGS += -std=c99 -I../../nova/include -I../..")):
        if contents.count(original) != 1:
            raise ValueError("Pinned vendor makefile definition changed: " + original)
        contents = contents.replace(original, replacement)
    old_rule = ("empty.obj: ../../empty.c $(SYSCFG_H_FILES)\n"
                "\t@ echo Building $@\n"
                "\t@ $(CC) $(CFLAGS) -c $< -o $@\n")
    if contents.count(old_rule) != 1:
        raise ValueError("Pinned vendor makefile application rule changed")
    rules = "\n".join(
        "nova_" + name + ".obj: ../../nova/" + name + ".c $(SYSCFG_H_FILES)\n"
        "\t@ echo Building $@\n"
        "\t@ $(CC) $(CFLAGS) -c $< -o $@\n" for name in source_names)
    contents = contents.replace(old_rule, rules)
    makefile.write_text(contents)
    (stage / "build-inputs.json").write_text(json.dumps({
        "sdk": str(sdk), "sdk_version": SDK_VERSION,
        "compiler": str(compiler), "sysconfig": str(sysconfig),
        "vendor_compile_board": "CC1352R1_LAUNCHXL",
        "thread_stack_bytes": 2048,
        "note": "Compile/startup check only; stock board scaffold is not deployment wiring or RF configuration.",
    }, indent=2) + "\n")
    return stage / "tirtos7/ticlang"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, help="SimpleLink SDK 7.41.00.17 installation")
    parser.add_argument("--compiler", required=True, help="TI Arm Clang installation directory")
    parser.add_argument("--sysconfig", required=True, help="SysConfig CLI executable")
    parser.add_argument("--build-dir", required=True, help="Parent of the script-owned cc1352r-project stage")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    try:
        sdk, compiler, sysconfig, build_dir = (
            real_path(value) for value in (args.sdk, args.compiler, args.sysconfig, args.build_dir))
        repo = real_path(Path(__file__).resolve().parents[2])
        output = stage_project(sdk, compiler, sysconfig, build_dir, repo)
        print("Staged CC1352R compile check: " + str(output), flush=True)
        if not args.prepare_only:
            subprocess.run([
                "make", "-C", str(output), "-j", str(args.jobs),
                "SIMPLELINK_CC13XX_CC26XX_SDK_INSTALL_DIR=" + str(sdk),
                "TICLANG_ARMCOMPILER=" + str(compiler),
                "SYSCONFIG_TOOL=" + str(sysconfig),
            ], check=True)
            subprocess.run([
                str(compiler / "bin/tiarmobjcopy"), "-O", "ihex",
                str(output / "nova-radio-check.out"),
                str(output / "nova-radio-check.hex"),
            ], check=True)
            print("Firmware artifact: " + str(output / "nova-radio-check.out"))
            print("Intel HEX artifact: " + str(output / "nova-radio-check.hex"))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print("CC1352R build-check failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
