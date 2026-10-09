"""Airtime and zone budget model."""

import unittest

from novalink.airtime import (DEFAULT_PHY, FCC_NOTE, PHYS, TXQ_DEPTH, airtime_table, airtime_us,
                              get_phy, zone_budget)
from novalink.link import RadioParams


class AirtimeUnit(unittest.TestCase):
    def test_default_phy_numbers(self):
        phy = get_phy()
        self.assertEqual(phy.name, DEFAULT_PHY)
        self.assertEqual(phy.bitrate_bps, 50_000)
        self.assertEqual(phy.overhead_bytes, 12)
        self.assertEqual(phy.frame_bytes(0), 14)
        self.assertAlmostEqual(airtime_us(phy, 0), 2240.0)
        self.assertAlmostEqual(airtime_us(phy, 100), 18240.0)

    def test_other_phys(self):
        self.assertAlmostEqual(airtime_us(get_phy("ble-1m"), 100), 8 * (10 + 102))
        self.assertAlmostEqual(airtime_us(get_phy("prop-500k"), 100), 8 * 114 / 0.5)
        self.assertEqual(set(PHYS), {"subghz-50k", "ble-1m", "prop-500k"})
        with self.assertRaises(ValueError):
            get_phy("lora")

    def test_payload_range(self):
        for bad in (-1, 101):
            with self.assertRaises(ValueError):
                airtime_us(get_phy(), bad)

    def test_table(self):
        rows = airtime_table(get_phy())
        self.assertEqual([r["payload_len"] for r in rows], list(range(101)))
        self.assertEqual(rows[100]["fragment_len"], 102)
        times = [r["airtime_us"] for r in rows]
        self.assertEqual(times, sorted(times))

    def test_overrides(self):
        phy = get_phy().with_overrides(preamble_bytes=8, setup_us=100, crc_bytes=None)
        self.assertEqual(phy.overhead_bytes, 16)
        self.assertEqual(phy.crc_bytes, 2)
        self.assertAlmostEqual(airtime_us(phy, 0), 18 * 8 * 20 + 100)
        # Whitening is length-neutral.
        self.assertEqual(airtime_us(get_phy().with_overrides(whitening=False), 50),
                         airtime_us(get_phy(), 50))

    def test_default_budget(self):
        p = RadioParams.default()
        b = zone_budget(get_phy(), 100, p.tx_repeats, 1, p.repeat_interval_us,
                        p.repeat_jitter_us, p.dwell_us)
        self.assertEqual(b.tx_per_fragment, p.tx_repeats)
        self.assertAlmostEqual(b.radio_time_per_fragment_us, p.tx_repeats * 18240.0)
        self.assertAlmostEqual(b.max_fps_radio, 1e6 / (p.tx_repeats * 18240.0))
        self.assertAlmostEqual(b.repeat_gap_mean_us, 18240.0)
        self.assertAlmostEqual(b.max_fps, min(b.max_fps_radio, b.max_fps_queue))
        self.assertAlmostEqual(b.radio_duty, 1.0)
        self.assertEqual(len(b.warnings), 2)

    def test_queue_bound(self):
        b = zone_budget(get_phy("ble-1m"), 0, tx_repeats=3, repeat_interval_us=10_000,
                        repeat_jitter_us=0)
        self.assertAlmostEqual(b.queue_residence_us, 2 * 10_000 + 96)
        self.assertAlmostEqual(b.max_fps_queue, TXQ_DEPTH * 1e6 / 20_096)
        self.assertEqual(b.max_fps, b.max_fps_queue)
        self.assertEqual(b.warnings, [])

    def test_dual_band_and_duty_limit(self):
        b = zone_budget(get_phy(), 10, tx_repeats=2, bands=2, duty_limit=0.01, offered_fps=1.0)
        air = airtime_us(get_phy(), 10)
        self.assertEqual(b.tx_per_fragment, 4)
        self.assertAlmostEqual(b.channel_duty, 2 * air / 1e6)
        self.assertAlmostEqual(b.radio_duty, 4 * air / 1e6)
        self.assertAlmostEqual(b.max_fps_duty, 0.01 * 1e6 / (2 * air))
        b = zone_budget(get_phy(), 10, duty_limit=0.001, offered_fps=1000)
        self.assertTrue(any("exceeds" in w for w in b.warnings))

    def test_budget_arg_checks(self):
        with self.assertRaises(ValueError):
            zone_budget(get_phy(), tx_repeats=0)
        with self.assertRaises(ValueError):
            zone_budget(get_phy(), bands=3)

    def test_fcc_note(self):
        self.assertIn("15.247", FCC_NOTE)
        self.assertIn("15.249", FCC_NOTE)


if __name__ == "__main__":
    unittest.main()
