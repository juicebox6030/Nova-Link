#!/usr/bin/env python3
"""Generator boundary tests and real installed-SDK builds of every plugin kind."""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "new_plugin.py"
SDK_BUILD = None
CMAKE = "cmake"
specification = importlib.util.spec_from_file_location("new_plugin", GENERATOR)
scaffold = importlib.util.module_from_spec(specification)
specification.loader.exec_module(scaffold)


def command(arguments, expect_success=True):
    result = subprocess.run([str(argument) for argument in arguments],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if expect_success and result.returncode != 0:
        raise AssertionError("Command failed: %r\n%s" % (arguments, result.stdout))
    return result


def cache_values(build):
    values = {}
    for line in (build / "CMakeCache.txt").read_text(encoding="utf-8").splitlines():
        if not line.startswith(("//", "#")) and ":" in line and "=" in line:
            key, typed_value = line.split(":", 1)
            values[key] = typed_value.split("=", 1)[1]
    return values


class GeneratorBoundaryTests(unittest.TestCase):
    def test_rejects_invalid_or_reserved_names_before_writing(self):
        with tempfile.TemporaryDirectory(prefix="nova scaffold ") as temporary:
            output = Path(temporary) / "project"
            for name in ("../escape", "Upper", "foo_bar", "a;message", "a\nmessage", "static",
                         "nl-internal", "nova-internal", "scaffold-transport", "a" * 64):
                with self.subTest(name=name):
                    result = command([sys.executable, GENERATOR, name, "--output", output], False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())

    def test_rejects_invalid_zone_requirements_and_self_dependency(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "project"
            cases = [["--zone", "0"], ["--zone", "8"], ["--kind", "service", "--zone", "1"],
                     ["--requires", "../other"], ["--requires", "new-plugin"],
                     ["--requires", "other", "--requires", "other"]]
            cases.append([argument for index in range(16) for argument in ("--requires", "provider-%d" % index)])
            for arguments in cases:
                with self.subTest(arguments=arguments):
                    result = command([sys.executable, GENERATOR, "new-plugin", "--output", output] + arguments, False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())

    def test_existing_directory_file_and_symlink_are_never_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            marker = project / "important.txt"
            marker.write_text("preserve", encoding="utf-8")
            plain_file = root / "file"
            plain_file.write_text("preserve", encoding="utf-8")
            link = root / "link"
            try:
                link.symlink_to(root / "missing", target_is_directory=True)
            except OSError:
                link = None  # Windows may require a privilege for symlink creation.
            for output in (project, plain_file, link):
                if output is None:
                    continue
                result = command([sys.executable, GENERATOR, "new-plugin", "--output", output], False)
                self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
            self.assertEqual(plain_file.read_text(encoding="utf-8"), "preserve")
            if link is not None:
                self.assertTrue(link.is_symlink())

    def test_missing_template_does_not_leave_partial_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "project"
            previous = scaffold.TEMPLATES
            try:
                scaffold.TEMPLATES = Path(temporary) / "missing"
                with self.assertRaises(OSError):
                    scaffold.generate("new-plugin", "service", output, 1, [])
            finally:
                scaffold.TEMPLATES = previous
            self.assertFalse(output.exists())

    def test_every_kind_generates_in_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="nova scaffold ") as temporary:
            for kind in ("application", "service", "transport"):
                output = Path(temporary) / (kind + " project")
                command([sys.executable, GENERATOR, "scene-player", "--kind", kind, "--output", output])
                self.assertEqual(len(list(output.rglob("*.*"))), 7 if kind == "transport" else 6)
                self.assertTrue((output / "include" / "scene_player_plugin.h").exists())
                self.assertTrue((output / "examples" / "smoke.c").exists())
                self.assertTrue((output / "examples" / "conformance.c").exists())
                self.assertEqual((output / "examples" / "faults.c").exists(), kind == "transport")
                for path in output.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(b"\r", path.read_bytes())

    def test_relocated_generator_finds_adjacent_templates(self):
        with tempfile.TemporaryDirectory(prefix="nova installed tools ") as temporary:
            root = Path(temporary)
            tools = root / "SDK tools"
            tools.mkdir()
            relocated = tools / "new_plugin.py"
            shutil.copy2(GENERATOR, relocated)
            shutil.copytree(GENERATOR.parent / "plugin_templates", tools / "plugin_templates")
            for kind in ("application", "service", "transport"):
                output = root / kind
                command([sys.executable, relocated, "new-plugin", "--kind", kind, "--output", output])
                self.assertTrue((output / "src" / "new_plugin_plugin.c").exists())

    def test_full_size_manifests_preserve_runtime_without_overfilling_support_tests(self):
        with tempfile.TemporaryDirectory() as temporary:
            for kind in ("application", "service", "transport"):
                output = Path(temporary) / kind
                requirements = ["provider-%d" % index for index in range(14 if kind == "application" else 15)]
                scaffold.generate("full-size", kind, output, 1, requirements)
                cmake_text = (output / "CMakeLists.txt").read_text(encoding="utf-8")
                self.assertIn('option(NOVA_PLUGIN_CONFORMANCE "Build shared plugin contract checks" OFF)', cmake_text)
                if kind == "transport":
                    self.assertIn('option(NOVA_PLUGIN_FAULT_TESTS "Build deterministic transport fault scenarios" OFF)', cmake_text)


class InstalledSDKTests(unittest.TestCase):
    def test_all_generated_kinds_build_and_run_against_installed_sdk(self):
        if SDK_BUILD is None:
            self.skipTest("pass --sdk-build for actual installed-SDK compile/run verification")
        # No build-tree target aliases are available: use the installed package
        # and the installed generator/templates, including paths with spaces.
        with tempfile.TemporaryDirectory(prefix="nova plugin installed ") as temporary:
            root = Path(temporary)
            prefix = root / "SDK prefix"
            command([CMAKE, "--install", SDK_BUILD, "--prefix", prefix])
            cache = cache_values(SDK_BUILD)
            # GNUInstallDirs may leave DATADIR empty in the cache and derive
            # its effective value from DATAROOTDIR during configuration.
            datadir = Path(cache.get("CMAKE_INSTALL_DATADIR") or
                           cache.get("CMAKE_INSTALL_DATAROOTDIR") or "share")
            installed_generator = prefix / datadir / "NovaLink" / "tools" / "new_plugin.py"
            self.assertTrue(installed_generator.exists(), str(installed_generator))
            for kind in ("application", "service", "transport"):
                with self.subTest(kind=kind):
                    project = root / (kind + " project")
                    arguments = [sys.executable, installed_generator, "scene-" + kind,
                                 "--kind", kind, "--requires", "support-service", "--output", project]
                    if kind == "application":
                        arguments += ["--zone", "7"]
                    command(arguments)
                    build = project / "build"
                    configure = [CMAKE, "-S", project, "-B", build, "-DCMAKE_PREFIX_PATH=" + str(prefix),
                                 "-DCMAKE_C_COMPILER=" + cache["CMAKE_C_COMPILER"],
                                 "-DCMAKE_BUILD_TYPE=" + cache.get("CMAKE_BUILD_TYPE", "Debug")]
                    for flag in ("CMAKE_EXE_LINKER_FLAGS", "CMAKE_BUILD_RPATH"):
                        if cache.get(flag):
                            configure += ["-D" + flag + "=" + cache[flag]]
                    c_flags = cache.get("CMAKE_C_FLAGS", "")
                    if cache.get("NOVA_ENABLE_SANITIZERS") == "ON":
                        c_flags += " -fsanitize=address,undefined -fno-omit-frame-pointer"
                    if c_flags:
                        configure += ["-DCMAKE_C_FLAGS=" + c_flags]
                    command(configure)
                    command([CMAKE, "--build", build, "--parallel", "2"])
                    listing = command([CMAKE, "-E", "chdir", build, "ctest", "--show-only=json-v1"])
                    names = [test["name"] for test in json.loads(listing.stdout)["tests"]]
                    self.assertEqual(len(names), 8 if kind == "transport" else 2)
                    self.assertIn("scene_" + kind + "_conformance", names)
                    results = command([CMAKE, "-E", "chdir", build, "ctest", "-V", "--output-on-failure"])
                    self.assertIn({"application": "passed=6 failed=0 skipped=1",
                                   "service": "passed=5 failed=0 skipped=2",
                                   "transport": "passed=7 failed=0 skipped=0"}[kind], results.stdout)
                    if kind == "transport":
                        executable = build / "scene_transport_faults"
                        for scenario in ("clean", "delayed", "disconnected", "congested", "commit-retry", "restart"):
                            first = command([executable, scenario])
                            second = command([executable, scenario])
                            self.assertEqual(first.stdout, second.stdout, scenario)
                        invalid = command([executable, "not-a-profile"], False)
                        self.assertEqual(invalid.returncode, 2)
                        self.assertIn("unknown deterministic scenario", invalid.stdout)
                    runtime_build = project / "runtime-build"
                    command([CMAKE, "-S", project, "-B", runtime_build,
                             "-DCMAKE_PREFIX_PATH=" + str(prefix), "-DBUILD_TESTING=OFF",
                             "-DCMAKE_C_COMPILER=" + cache["CMAKE_C_COMPILER"]])
                    command([CMAKE, "--build", runtime_build, "--parallel", "2"])
                    targets = (runtime_build / "CMakeFiles" / "TargetDirectories.txt").read_text(encoding="utf-8")
                    self.assertNotIn("_conformance.dir", targets)
                    self.assertNotIn("_faults.dir", targets)
                    self.assertNotIn("_smoke.dir", targets)
                    maximum_project = root / (kind + " maximum project")
                    maximum_arguments = [sys.executable, installed_generator, "limit-" + kind,
                                         "--kind", kind, "--output", maximum_project]
                    for index in range(14 if kind == "application" else 15):
                        maximum_arguments += ["--requires", "provider-%d" % index]
                    command(maximum_arguments)
                    maximum_build = maximum_project / "build"
                    maximum_configure = list(configure)
                    maximum_configure[2] = maximum_project
                    maximum_configure[4] = maximum_build
                    command(maximum_configure)
                    command([CMAKE, "--build", maximum_build, "--parallel", "2"])
                    maximum_tests = command([CMAKE, "-E", "chdir", maximum_build,
                                             "ctest", "--show-only=json-v1"])
                    self.assertEqual([test["name"] for test in json.loads(maximum_tests.stdout)["tests"]],
                                     ["limit_" + kind + "_smoke"])
                    command([CMAKE, "-E", "chdir", maximum_build, "ctest", "--output-on-failure"])
                    for option in (["NOVA_PLUGIN_CONFORMANCE"] +
                                   (["NOVA_PLUGIN_FAULT_TESTS"] if kind == "transport" else [])):
                        rejected_configure = list(maximum_configure)
                        rejected_configure[4] = maximum_project / ("rejected-" + option)
                        rejected = command(rejected_configure + ["-D" + option + "=ON"], False)
                        self.assertNotEqual(rejected.returncode, 0)
                        self.assertIn("providers; set " + option + "=OFF", " ".join(rejected.stdout.split()))
                    if kind == "transport":
                        edge_project = root / "transport fourteen providers"
                        edge_arguments = [sys.executable, installed_generator, "edge-transport", "--kind",
                                          "transport", "--output", edge_project]
                        for index in range(14):
                            edge_arguments += ["--requires", "provider-%d" % index]
                        command(edge_arguments)
                        edge_build = edge_project / "build"
                        edge_configure = list(configure)
                        edge_configure[2] = edge_project
                        edge_configure[4] = edge_build
                        command(edge_configure)
                        command([CMAKE, "--build", edge_build, "--parallel", "2"])
                        edge_listing = command([CMAKE, "-E", "chdir", edge_build,
                                                "ctest", "--show-only=json-v1"])
                        edge_names = [test["name"] for test in json.loads(edge_listing.stdout)["tests"]]
                        self.assertEqual(len(edge_names), 7)
                        self.assertNotIn("edge_transport_conformance", edge_names)
                        command([CMAKE, "-E", "chdir", edge_build, "ctest", "--output-on-failure"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--sdk-build", type=Path)
    parser.add_argument("--cmake", default="cmake")
    arguments, remaining = parser.parse_known_args()
    SDK_BUILD = arguments.sdk_build.resolve() if arguments.sdk_build is not None else None
    CMAKE = arguments.cmake
    unittest.main(argv=[sys.argv[0]] + remaining)
