"""Exercise the actual C emulator and replay with independent golden CRC vectors."""
# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and len(sys.argv) == 3:
    SIM, ENGINE = map(Path, sys.argv[1:3])
else:
    SIM, ENGINE = ROOT / "build/nova-multiverse-sim", ROOT / "build/nova-multiverse-replay"
CLI = ROOT / "tools/replay_multiverse.py"


def run(command, success=True):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, check=False)
    if (result.returncode == 0) != success:
        raise AssertionError((command, result.returncode, result.stderr))
    return result


def packet(kind=0, universe=1, session=42, seq=0, base=0, slots=2,
           start=0, span=2, offset=0, values=b"\x00\x01", reserved=0):
    raw = b"NVS1" + struct.pack("<BBHI7H", kind, reserved, universe, session,
                               seq, base, slots, start, span, offset, len(values)) + values
    return (raw + struct.pack("<I", zlib.crc32(raw))).hex()


def entry(timestamp=0, **fields):
    result = {"timestamp_us": timestamp, "frequency_hz": 2405000000,
              "profile": "nova-mv-synthetic-v1", "synthetic": True,
              "crc": "ok", "payload_hex": packet()}
    result.update(fields)
    return result


class ReplayTests(unittest.TestCase):
    def replay(self, entries, *args, success=True):
        with tempfile.TemporaryDirectory() as temp:
            capture = Path(temp) / "capture.jsonl"
            capture.write_text("".join(json.dumps(e) + "\n" for e in entries))
            result = run([sys.executable, CLI, capture, "--engine", ENGINE, *args], success)
            return [json.loads(line) for line in result.stdout.splitlines()] if success else result

    def test_generated_lossy_scenarios_and_captured_truth(self):
        for seed, loss in ((1, 0), (42, 20), (999, 75), (3, 100)):
            with self.subTest(seed=seed, loss=loss), tempfile.TemporaryDirectory() as temp:
                capture = Path(temp) / "synthetic.jsonl"
                sim = json.loads(run([SIM, "--seed", seed, "--loss-percent", loss,
                                      "--capture", capture]).stdout)
                self.assertEqual(sim["tx_updates"], 301)
                self.assertTrue(sim["final_levels_match"])
                self.assertTrue(sim["loss_detected"])
                events = [json.loads(line) for line in run([
                    sys.executable, CLI, capture, "--engine", ENGINE, "--end-us", 3130200]).stdout.splitlines()]
                summary = events[-1]
                self.assertEqual(summary["frames"], sim["rx_frames"])
                self.assertEqual(summary["frames"], summary["expected_frames_checked"])
                self.assertEqual(summary["duplicates"], sim["duplicates"])
                self.assertEqual(summary["bad"], sim["bad_packets"])
                self.assertEqual(summary["unverified"], sim["unknown_integrity"])
                self.assertEqual(summary["missing_base"], sim["missing_base"])
                self.assertEqual(summary["link"], "lost")
                self.assertEqual(summary["losses"], sim["losses"])
                self.assertFalse(summary["multiverse_rf_verified"])
                self.assertEqual(events[-2]["slots_hex"], json.loads(capture.read_text().splitlines()[-1])["expected_slots_hex"])
                self.assertFalse(json.loads(run([sys.executable, ROOT / "tools/analyze_rf_capture.py", capture]).stdout)["multiverse_decoded"])

    def test_independent_golden_codec_and_sequence_wrap(self):
        events = self.replay([
            entry(payload_hex=packet(seq=65535)),
            entry(10, payload_hex=packet(kind=1, seq=0, base=65535, start=1, span=1, values=b"\xff")),
            entry(11, payload_hex=packet(seq=65535)),
            entry(12, payload_hex=packet(seq=0)),
            entry(13, payload_hex=packet(seq=32768)),
        ])
        self.assertEqual([e["result"] for e in events[:-1]], ["frame_ready", "frame_ready", "stale", "duplicate", "stale"])
        self.assertEqual(events[1]["slots_hex"], "00ff")

    def test_integrity_and_framing(self):
        invalid = [packet(reserved=1), packet(slots=1), packet(kind=9), packet(base=1),
                   packet()[:-2], packet() + "00", "", "00"]
        events = self.replay([entry(i, payload_hex=p) for i, p in enumerate(invalid)] + [
            entry(20, crc="unknown"), entry(21, crc="bad"), entry(22),
        ])
        self.assertEqual([e["result"] for e in events[:len(invalid)]], ["bad_packet"] * len(invalid))
        self.assertEqual(events[-1]["bad"], len(invalid) + 1)
        self.assertEqual(events[-1]["unverified"], 1)
        self.assertEqual(events[-1]["frames"], 1)

    def test_missing_base_expiry_and_reacquisition(self):
        events = self.replay([
            entry(),
            entry(100, payload_hex=packet(kind=1, seq=2, base=1, values=b"\xff\xff")),
            entry(200, payload_hex=packet(seq=3, values=b"\x10\x20")),
        ], "--end-us", "100200")
        self.assertEqual(events[1]["result"], "need_full")
        self.assertEqual(events[1]["link"], "recovering")
        self.assertEqual(events[2]["slots_hex"], "1020")
        self.assertEqual(events[-1]["link"], "lost")

    def test_explicit_result_and_link_acceptance(self):
        events = self.replay([
            entry(expected_result="frame_ready", expected_link="live", expected_slots_hex="0001"),
            entry(1, expected_result="duplicate", expected_link="live"),
            entry(2, payload_hex=packet(kind=1, seq=2, base=1),
                  expected_result="need_full", expected_link="recovering"),
            # A verified FULL with a newer sequence restores exact host levels.
            entry(3, payload_hex=packet(seq=3, values=b"\x10\x20"),
                  expected_result="frame_ready", expected_link="live", expected_slots_hex="1020"),
            # The old full is rejected after silence and cannot revive the link.
            entry(100003, payload_hex=packet(seq=3, values=b"\x10\x20"),
                  expected_result="duplicate", expected_link="lost"),
            entry(100004, payload_hex=packet(seq=4, values=b"\x30\x40"),
                  expected_result="frame_ready", expected_link="live", expected_slots_hex="3040"),
        ], "--end-us", "200004", "--expect-frames", "3", "--expect-link", "lost")
        summary = events[-1]
        self.assertEqual(summary["expected_results_checked"], 6)
        self.assertEqual(summary["expected_links_checked"], 6)
        self.assertEqual(summary["expected_frames_checked"], 3)
        self.assertEqual(summary["final_expectations_checked"], 2)
        self.assertEqual(summary["losses"], 2)

    def test_snapshot_labels_remain_optional_delivery_expectations(self):
        # Historical simulator labels describe host snapshots even for packets
        # that are deliberately corrupt, filtered or incomplete.
        events = self.replay([entry(crc="bad", expected_slots_hex="0001")])
        self.assertEqual(events[-1]["frames"], 0)
        self.assertEqual(events[-1]["expected_frames_checked"], 0)
        self.assertEqual(events[-1]["final_expectations_checked"], 0)
        failed = self.replay([entry(crc="bad", expected_result="frame_ready",
                                   expected_slots_hex="0001")], success=False)
        self.assertIn("expected frame_ready, got bad_packet", failed.stderr)

    def test_missing_and_extra_frames_fail_explicit_acceptance(self):
        for expected in (0, 2):
            with self.subTest(expected=expected):
                failed = self.replay([entry()], "--expect-frames", expected, success=False)
                self.assertIn(f"frame count mismatch: expected {expected}, got 1", failed.stderr)
        # A second update where the trace expects a duplicate is an extra frame,
        # even if its levels happen to match the first frame exactly.
        failed = self.replay([entry(), entry(1, payload_hex=packet(seq=1),
                                           expected_result="duplicate")], success=False)
        self.assertIn("expected duplicate, got frame_ready", failed.stderr)
        events = self.replay([entry(crc="bad", expected_result="bad_packet",
                                    expected_link="wait_full")],
                             "--expect-frames", 0, "--expect-link", "wait_full")
        self.assertEqual(events[-1]["expected_results_checked"], 1)

    def test_link_and_result_expectation_errors(self):
        failed = self.replay([entry(expected_link="lost")], success=False)
        self.assertIn("expected lost, got live", failed.stderr)
        failed = self.replay([entry()], "--expect-link", "lost", success=False)
        self.assertIn("final link mismatch: expected lost, got live", failed.stderr)
        for fields in ({"expected_result": None}, {"expected_result": "FRAME_READY"},
                       {"expected_result": []}, {"expected_result": 0},
                       {"expected_link": None}, {"expected_link": "unknown"},
                       {"expected_link": True}):
            with self.subTest(fields=fields):
                self.replay([entry(**fields)], success=False)
        for flag, value in (("--expect-frames", "-1"), ("--expect-frames", str(2**64)),
                            ("--expect-frames", "1.0"), ("--expect-link", "unknown")):
            with self.subTest(flag=flag, value=value):
                self.replay([entry()], flag, value, success=False)

    def test_mismatch_profile_and_clock_are_errors(self):
        self.replay([entry(expected_slots_hex="ffff")], success=False)
        for fields in ({"profile": "candidate-real"}, {"synthetic": False},
                       {"expected_slots_hex": "0"}, {"timestamp_us": 2**64},
                       {"payload_hex": "00" * 543}):
            with self.subTest(fields=fields):
                self.replay([entry(**fields)], success=False)
        self.replay([entry(100), entry(99)], success=False)
        self.replay([entry(100)], "--end-us", "99", success=False)
        self.replay([entry()], "--session", "-1", success=False)
        self.replay([], success=False)

    def test_universe_and_session_filter(self):
        events = self.replay([entry(), entry(1, payload_hex=packet(universe=2)),
                              entry(2, payload_hex=packet(session=43))])
        self.assertEqual(events[-1]["frames"], 1)
        self.assertEqual(events[-1]["filtered"], 2)
        events = self.replay([entry()], "--session", "43")
        self.assertEqual(events[-1]["link"], "wait_full")

    def test_cli_output_and_capture_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            capture = Path(temp) / "capture.jsonl"
            output = Path(temp) / "output.jsonl"
            original = json.dumps(entry()) + "\n"
            capture.write_text(original)
            run([sys.executable, CLI, capture, "--engine", ENGINE, "--output", output, "--summary-only"])
            self.assertEqual(json.loads(output.read_text())["frames"], 1)
            run([sys.executable, CLI, capture, "--engine", ENGINE, "--output", capture], success=False)
            self.assertEqual(capture.read_text(), original)
            previous_output = output.read_text()
            run([sys.executable, CLI, capture, "--engine", ENGINE, "--output", output,
                 "--expect-frames", "2"], success=False)
            self.assertEqual(output.read_text(), previous_output)

    def test_versioned_example_and_differential_analyzer_cli(self):
        capture = ROOT / "examples/multiverse.synthetic.jsonl"
        summary = json.loads(run([sys.executable, CLI, capture, "--engine", ENGINE,
                                  "--end-us", "104000", "--expect-frames", "4",
                                  "--expect-link", "lost", "--summary-only"]).stdout)
        self.assertEqual(summary["frames"], 4)
        self.assertEqual(summary["expected_frames_checked"], 4)
        self.assertEqual(summary["link"], "lost")
        self.assertEqual(summary["expected_results_checked"], 11)
        self.assertEqual(summary["expected_links_checked"], 11)
        analyzer = ROOT / "tools/analyze_rf_capture.py"
        report = json.loads(run([sys.executable, analyzer, capture, "--compare-stimuli",
                                 "resync", "channel_1_85"]).stdout)
        self.assertFalse(report["multiverse_decoded"])
        self.assertEqual(len(report["stimulus_comparison"]["groups"]), 1)
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "capture.jsonl"
            original = capture.read_text()
            copy.write_text(original)
            run([sys.executable, analyzer, copy, "--output", copy], success=False)
            self.assertEqual(copy.read_text(), original)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
