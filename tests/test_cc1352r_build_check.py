#!/usr/bin/env python3
"""Exercise build staging and destructive-operation boundaries without TI tools."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "platform/cc1352r/build_check.py"
SPEC = importlib.util.spec_from_file_location("cc1352r_build_check", SCRIPT)
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class BuildStageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nova-cc1352r-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sdk = self.root / "sdk"
        self.compiler = self.root / "compiler"
        self.sysconfig = self.root / "sysconfig/cli.sh"
        self.repo = self.root / "repo"
        self.build_dir = self.root / "build"
        for path, text in (
            (self.sdk / ".metadata/product.json", json.dumps({"name": "simplelink_cc13xx_cc26xx_sdk", "version": BUILD.SDK_VERSION})),
            (self.sdk / "imports.mak", "# vendor imports\n"),
            (self.compiler / "bin/tiarmclang", "compiler fixture"),
            (self.compiler / "bin/tiarmobjcopy", "objcopy fixture"),
            (self.sysconfig, "sysconfig fixture"),
            (self.repo / "platform/cc1352r/example/nova_radio_check.c", "/* check */\n"),
            (self.repo / "include/nova_link/status.h", "/* header */\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        vendor = self.sdk / BUILD.VENDOR_EXAMPLE
        for relative in BUILD.VENDOR_FILES:
            destination = vendor / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("/* vendor license */\n")
        (vendor / "tirtos7/main_tirtos.c").write_text("/* vendor license */\n#define THREADSTACKSIZE 1024\n")
        (vendor / "tirtos7/ticlang/makefile").write_text(
            "OBJECTS = empty.obj tirtos7_main_tirtos.obj\nNAME = empty\n"
            "CFLAGS += -I../..\n"
            "empty.obj: ../../empty.c $(SYSCFG_H_FILES)\n"
            "\t@ echo Building $@\n"
            "\t@ $(CC) $(CFLAGS) -c $< -o $@\n")
        # Existing SDK artifacts must never leak into the staged project.
        (vendor / "tirtos7/ticlang/stale.obj").write_text("old vendor object")
        for name in BUILD.SOURCES:
            path = self.repo / "src" / (name + ".c")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("/* " + name + " */\n")

    def stage(self):
        return BUILD.stage_project(self.sdk, self.compiler, self.sysconfig,
                                   self.build_dir, self.repo)

    def test_stages_only_inputs_and_refreshes_source(self):
        vendor = self.sdk / BUILD.VENDOR_EXAMPLE
        originals = {relative: (vendor / relative).read_bytes() for relative in BUILD.VENDOR_FILES}
        output = self.stage()
        project = output.parents[1]
        makefile = (output / "makefile").read_text()
        self.assertIn("-std=c99 -I../../nova/include", makefile)
        self.assertIn("nova_spi_slave.obj:", makefile)
        self.assertNotIn("empty.obj:", makefile)
        self.assertFalse((output / "stale.obj").exists())
        self.assertIn("THREADSTACKSIZE 2048", (project / "tirtos7/main_tirtos.c").read_text())
        self.assertIn("vendor license", (project / "tirtos7/main_tirtos.c").read_text())
        (output / "stale-generated.obj").write_text("stale")
        (self.repo / "src/radio.c").write_text("new source\n")
        self.stage()
        self.assertFalse((output / "stale-generated.obj").exists())
        self.assertEqual((project / "nova/radio.c").read_text(), "new source\n")
        for relative, contents in originals.items():
            self.assertEqual((vendor / relative).read_bytes(), contents)
        self.assertTrue((vendor / "tirtos7/ticlang/stale.obj").exists())

    def test_refuses_unowned_stage_without_deleting_contents(self):
        stage = self.build_dir / BUILD.PROJECT_NAME
        stage.mkdir(parents=True)
        sentinel = stage / "keep.txt"
        sentinel.write_text("keep")
        with self.assertRaisesRegex(ValueError, "ownership marker"):
            self.stage()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_refuses_symlink_stage(self):
        destination = self.root / "unrelated"
        destination.mkdir()
        (destination / BUILD.MARKER).write_text(BUILD.OWNER)
        self.build_dir.mkdir()
        (self.build_dir / BUILD.PROJECT_NAME).symlink_to(destination, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.stage()
        self.assertTrue(destination.exists())

    def test_refuses_symlink_marker(self):
        stage = self.build_dir / BUILD.PROJECT_NAME
        stage.mkdir(parents=True)
        marker = self.root / "external-marker"
        marker.write_text(BUILD.OWNER)
        (stage / BUILD.MARKER).symlink_to(marker)
        with self.assertRaisesRegex(ValueError, "ownership marker"):
            self.stage()
        self.assertTrue(stage.is_dir())

    def test_sdk_version_failure_preserves_existing_stage(self):
        self.stage()
        stage = self.build_dir / BUILD.PROJECT_NAME
        sentinel = stage / "keep.txt"
        sentinel.write_text("keep")
        (self.sdk / ".metadata/product.json").write_text(json.dumps({"name": "simplelink_cc13xx_cc26xx_sdk", "version": "8.00.00.00"}))
        with self.assertRaisesRegex(ValueError, "7.41.00.17"):
            self.stage()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_refuses_destination_inside_sdk(self):
        self.build_dir = self.sdk / "build"
        with self.assertRaisesRegex(ValueError, "protected"):
            self.stage()
        self.assertFalse(self.build_dir.exists())

    def test_rejects_shell_make_metacharacters_and_whitespace(self):
        for suffix in ("bad path", "bad$path", "bad;path", "bad`path", "bad#path", "bad:path", "bad\\path"):
            with self.subTest(suffix=suffix):
                with self.assertRaises(ValueError):
                    BUILD.real_path(self.root / suffix)


if __name__ == "__main__":
    unittest.main()
