#!/usr/bin/env python3
"""Exercise application startup validation beyond parser unit coverage."""
import pathlib
import subprocess
import sys
import tempfile
import unittest


class ConfigManifestTests(unittest.TestCase):
    executable: str
    sample: str

    def invoke(self, text: str | bytes) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "plugins.ini"
            path.write_bytes(text.encode("ascii") if isinstance(text, str) else text)
            return subprocess.run(
                [self.executable, str(path)], capture_output=True, text=True, check=False
            )

    def rejected(self, text: str | bytes, diagnostic: str) -> None:
        result = self.invoke(text)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("Started", result.stdout)
        self.assertIn(diagnostic, result.stderr)

    def rx_config(self) -> str:
        text = self.sample.replace("role=tx", "role=rx")
        for field in (
            "interval_us=1000\n",
            "full_interval_us=10000\n",
            "chunks_per_tick=8\n",
            "slots=512\n",
            "initial_level=128\n",
        ):
            text = text.replace(field, "")
        return text.replace(
            "session=42\n",
            "session=42\npeer_origin=2\nloss_timeout_us=50000\nassembly_timeout_us=5000\n",
        )

    def test_sample_serializes_and_drains(self) -> None:
        result = self.invoke(self.sample)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Started 5 compiled plugins", result.stdout)
        self.assertIn("Accepted TX fragments=9; serialized/drained=9", result.stdout)

    def test_rx_silence(self) -> None:
        result = self.invoke(self.rx_config())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Accepted TX fragments=0; serialized/drained=0", result.stdout)
        self.assertIn("RX receives no injected traffic", result.stdout)

    def test_optional_defaults_and_small_tick_budget(self) -> None:
        text = self.sample.replace("slots=512\n", "").replace("initial_level=128\n", "")
        text = text.replace("chunks_per_tick=8", "chunks_per_tick=1")
        result = self.invoke(text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Accepted TX fragments=2; serialized/drained=2", result.stdout)

    def test_command_and_missing_file(self) -> None:
        result = subprocess.run([self.executable], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [self.executable, str(pathlib.Path(directory) / "missing.ini")],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Started", result.stdout)
        self.assertTrue(result.stderr)

    def test_schema_rejections(self) -> None:
        for text, diagnostic in (
            (self.sample + "unknown=1\n", "unknown"),
            (self.sample + "[foreign]\nkey=1\n", "foreign"),
            (self.sample + "origin=2\n", "origin"),
            (self.sample + "[host]\norigin=2\n", "host"),
            (self.sample.replace("poll_budget=16", "poll_budget=65536"), "poll_budget"),
            (self.sample.replace("session=42", "session=18446744073709551616"), "session"),
        ):
            with self.subTest(diagnostic=diagnostic, text=text):
                self.rejected(text, diagnostic)

    def test_role_field_validation(self) -> None:
        for text, diagnostic in (
            (self.sample.replace("interval_us=1000\n", ""), "interval_us is required"),
            (self.sample.replace("session=42\n", "session=42\npeer_origin=2\n"), "peer_origin is forbidden"),
            (self.rx_config().replace("peer_origin=2\n", ""), "peer_origin is required"),
            (self.rx_config().replace("session=42\n", "session=42\nslots=512\n"), "slots is forbidden"),
        ):
            with self.subTest(diagnostic=diagnostic):
                self.rejected(text, diagnostic)

    def test_cross_field_validation(self) -> None:
        for text, diagnostic in (
            (self.sample.replace("zone=2", "zone=1"), "must differ"),
            (self.sample.replace("full_interval_us=10000", "full_interval_us=999"), "full_interval_us"),
            (self.rx_config().replace("peer_origin=2", "peer_origin=1"), "peer_origin"),
            (self.rx_config().replace("assembly_timeout_us=5000", "assembly_timeout_us=50001"), "assembly_timeout_us"),
        ):
            with self.subTest(diagnostic=diagnostic):
                self.rejected(text, diagnostic)

    def test_input_limit_and_embedded_nul(self) -> None:
        self.rejected(b"#" + b"a" * 8192, "exceeds 8192 bytes")
        self.rejected(self.sample.encode("ascii") + b"\0", "Configuration line")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_config_manifest.py EXECUTABLE SAMPLE_INI")
    ConfigManifestTests.executable = str(pathlib.Path(sys.argv[1]).resolve())
    ConfigManifestTests.sample = pathlib.Path(sys.argv[2]).read_text(encoding="ascii")
    unittest.main(argv=[sys.argv[0]])
