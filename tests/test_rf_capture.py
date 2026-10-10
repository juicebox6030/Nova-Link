# SPDX-License-Identifier: GPL-3.0-only
import json
import unittest

from tools.analyze_rf_capture import compare_stimuli, read_capture, summarize


def observation(**changes):
    value = {
        "timestamp_us": 1000,
        "frequency_hz": 2_405_000_000,
        "profile": "candidate-a",
        "payload_hex": "00AB",
    }
    value.update(changes)
    return json.dumps(value)


class CaptureTests(unittest.TestCase):
    def test_candidate_byte_comparison_preserves_boundaries(self):
        entries = list(read_capture([
            observation(stimulus="baseline", crc="ok", payload_hex="000100"),
            observation(timestamp_us=1001, stimulus="baseline", crc="ok", payload_hex="000100"),
            observation(timestamp_us=1002, stimulus="changed", crc="ok", payload_hex="00ff00"),
            observation(timestamp_us=1003, stimulus="changed", crc="bad", payload_hex="aaff00"),
            observation(timestamp_us=1004, stimulus="changed", crc="ok", payload_hex="00ff"),
            observation(timestamp_us=1005, stimulus="changed", profile="other", crc="ok", payload_hex="aaff00"),
        ]))
        compared = compare_stimuli(entries, "baseline", "changed")
        self.assertEqual(len(compared["groups"]), 1)
        group = compared["groups"][0]
        self.assertEqual(group["baseline_observations"], 2)
        self.assertEqual(group["differing_offsets"], [{
            "offset": 1, "baseline_value_counts": {"01": 2},
            "changed_value_counts": {"ff": 1}, "stable_in_both": True,
        }])

    def test_distribution_comparison_is_not_a_sample_count_comparison(self):
        entries = list(read_capture([
            observation(stimulus="a", payload_hex="00"),
            observation(stimulus="a", payload_hex="01"),
            observation(stimulus="b", payload_hex="00"),
            observation(stimulus="b", payload_hex="01"),
            observation(stimulus="b", payload_hex="00"),
            observation(stimulus="b", payload_hex="01"),
        ]))
        self.assertEqual(compare_stimuli(entries, "a", "b")["groups"][0]["differing_offsets"], [])
        with self.assertRaisesRegex(ValueError, "different"):
            compare_stimuli(entries, "a", "a")
        with self.assertRaisesRegex(ValueError, "no matching"):
            compare_stimuli(entries, "a", "missing")

    def test_groups_keep_candidate_phys_and_stimuli_separate(self):
        report = summarize(read_capture([
            observation(rssi_dbm=-50, crc="ok"),
            observation(timestamp_us=21000, rssi_dbm=-54, crc="bad"),
            observation(timestamp_us=30000, profile="candidate-b", stimulus="changed"),
            observation(timestamp_us=40000, frequency_hz=2_410_000_000),
        ]))
        self.assertEqual(report["observations"], 4)
        self.assertEqual(report["capture_span_us"], 39000)
        self.assertFalse(report["multiverse_decoded"])
        self.assertEqual(len(report["groups"]), 3)
        first = report["groups"][0]
        self.assertEqual(first["crc_counts"], {"ok": 1, "bad": 1})
        self.assertEqual(first["rssi_median_dbm"], -52)
        self.assertEqual(first["distinct_payloads"], 1)
        self.assertEqual(first["observed_gap_us"]["median"], 20000)
        self.assertEqual(report["groups"][1]["crc_counts"], {"unknown": 1})

    def test_stimulus_change_is_not_folded_into_baseline(self):
        report = summarize(read_capture([
            observation(stimulus="baseline"),
            observation(timestamp_us=2000, stimulus="channel_1_32"),
        ]))
        self.assertEqual(len(report["groups"]), 2)
        self.assertIsNone(report["groups"][0]["observed_gap_us"])

    def test_invalid_fields(self):
        cases = [
            {"timestamp_us": -1}, {"timestamp_us": True},
            {"frequency_hz": 915_000_000}, {"frequency_hz": "2405000000"},
            {"profile": " "}, {"profile": None}, {"stimulus": []},
            {"payload_hex": "0"}, {"payload_hex": "00 01"},
            {"payload_hex": "zz"}, {"payload_hex": None},
            {"crc": "not-checked"}, {"rssi_dbm": float("nan")},
            {"rssi_dbm": float("inf")}, {"rssi_dbm": True},
        ]
        for fields in cases:
            with self.subTest(fields=fields), self.assertRaisesRegex(ValueError, "line 1:"):
                list(read_capture([observation(**fields)]))

    def test_invalid_log_and_monotonic_timer(self):
        for value in ("not-json", "[]", "null", "{}"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "line 2:"):
                list(read_capture(["\n", value]))
        with self.assertRaisesRegex(ValueError, "timer wraps"):
            list(read_capture([observation(timestamp_us=2000), observation(timestamp_us=1000)]))
        with self.assertRaisesRegex(ValueError, "no observations"):
            summarize(read_capture(["\n"]))

    def test_unknown_crc_and_missing_rssi_stay_unknown(self):
        report = summarize(read_capture([observation()]))
        group = report["groups"][0]
        self.assertEqual(group["crc_counts"], {"unknown": 1})
        self.assertIsNone(group["rssi_median_dbm"])
        self.assertIsNone(group["observed_gap_us"])


if __name__ == "__main__":
    unittest.main()
