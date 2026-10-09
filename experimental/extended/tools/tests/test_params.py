"""Link payload codecs against tests/vectors/params.json."""

import unittest

from novalink import NLError
from novalink.link import (Cmd, Pong, RadioParams, RadioStatus, ZonePlan, ZoneRF, decode_frame,
                           encode_frame)
from tests.vectors import VectorMixin, h

PARAM_FIELDS = ("origin_id", "band", "tx_policy", "tx_repeats", "dwell_us", "burst_extend_us",
                "mgmt_hold_us", "repeat_interval_us", "tracker_stale_us", "repeat_jitter_us",
                "discovery_interval_us", "mgmt_repeats", "cca_backoff_us")
STATUS_FIELDS = ("proto_version", "flags", "rx_queue_len", "tx_queue_len", "rx_ok", "rx_dup",
                 "rx_dropped", "rx_ignored", "tx_sent", "tx_dropped")
PONG_FIELDS = ("proto_version", "fw_major", "fw_minor", "fw_patch")


class ParamsVectors(VectorMixin, unittest.TestCase):
    VECTOR_FILE = "params"
    SECTIONS = ("radio_params", "radio_params_decode_errors", "zone_plan",
                "zone_plan_decode_errors", "status", "status_decode_errors", "pong",
                "pong_decode_errors")

    def check_codec(self, section, cls, field_names, cmd):
        for v in self.vectors(section):
            with self.subTest(section=section, name=v.get("name", v["wire"])):
                obj = cls(**{k: v[k] for k in field_names})
                self.assertEqual(obj.encode().hex(), v["wire"])
                self.assertEqual(encode_frame(cmd, obj.encode()).hex(), v["frame"])
                back = cls.decode(h(v["wire"]))
                self.assertEqual(back, obj)
                r = decode_frame(h(v["frame"]))
                self.assertEqual((r.status, r.frame.cmd, r.frame.data.hex()), ("ok", cmd, v["wire"]))

    def check_errors(self, section, cls):
        for v in self.vectors(section):
            with self.subTest(section=section, wire=v["wire"]):
                with self.assertRaises(NLError) as cm:
                    cls.decode(h(v["wire"]))
                self.assertEqual(cm.exception.status, v["status"])

    def test_radio_params(self):
        self.check_codec("radio_params", RadioParams, PARAM_FIELDS, Cmd.RADIO_CONFIG)

    def test_radio_params_default(self):
        default = [v for v in self.vectors("radio_params") if v["name"] == "default"][0]
        self.assertEqual(RadioParams.default().encode().hex(), default["wire"])

    def test_radio_params_decode_errors(self):
        self.check_errors("radio_params_decode_errors", RadioParams)

    def test_zone_plan(self):
        for v in self.vectors("zone_plan"):
            with self.subTest(name=v["name"]):
                plan = ZonePlan([ZoneRF(**z) for z in v["zones"]])
                self.assertEqual(plan.encode().hex(), v["wire"])
                self.assertEqual(encode_frame(Cmd.ZONE_CONFIG, plan.encode()).hex(), v["frame"])
                self.assertEqual(ZonePlan.decode(h(v["wire"])), plan)

    def test_zone_plan_decode_errors(self):
        self.check_errors("zone_plan_decode_errors", ZonePlan)

    def test_status(self):
        self.check_codec("status", RadioStatus, STATUS_FIELDS, Cmd.RSP_STATUS)

    def test_status_decode_errors(self):
        self.check_errors("status_decode_errors", RadioStatus)

    def test_pong(self):
        self.check_codec("pong", Pong, PONG_FIELDS, Cmd.RSP_PONG)

    def test_pong_decode_errors(self):
        self.check_errors("pong_decode_errors", Pong)


class ParamsUnit(unittest.TestCase):
    def test_encode_does_not_validate_ranges(self):
        # Like nl_radio_params_encode: only the decoder range-checks.
        wire = RadioParams(origin_id=9, band=7, tx_repeats=0).encode()
        with self.assertRaises(NLError) as cm:
            RadioParams.decode(wire)
        self.assertEqual(cm.exception.status, "arg")

    def test_field_overflow_rejected(self):
        with self.assertRaises(NLError):
            RadioParams(dwell_us=1 << 32).encode()

    def test_to_dict(self):
        d = RadioParams(band=2, tx_policy=1).to_dict()
        self.assertEqual((d["band_name"], d["tx_policy_name"]), ("DUAL", "IN_SLOT"))
        self.assertEqual(RadioStatus(flags=3).to_dict()["flag_names"], ["RX_PENDING", "CONFIGURED"])


if __name__ == "__main__":
    unittest.main()
