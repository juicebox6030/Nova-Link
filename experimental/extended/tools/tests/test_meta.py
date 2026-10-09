"""Zone 0 metadata against tests/vectors/meta.json."""

import unittest

from novalink import NLError
from novalink.meta import (MAX_VALUE, Claim, DeviceAnnounce, MetaQueue, MetaRecord, MetaType,
                           decode_claims, decode_congestion, decode_device, decode_plugin_data,
                           decode_records, describe_record, encode_claims, encode_congestion,
                           encode_debug_text, encode_device, encode_plugin_data, encode_record,
                           encode_records, iter_records)
from tests.vectors import VectorMixin, h


class MetaVectors(VectorMixin, unittest.TestCase):
    VECTOR_FILE = "meta"
    SECTIONS = ("tlv", "device", "device_decode_errors", "claims", "claims_errors",
                "plugin_data", "congestion", "queue")

    def test_tlv(self):
        for v in self.vectors("tlv"):
            with self.subTest(name=v["name"]):
                records, status = decode_records(h(v["payload"]))
                self.assertEqual([{"type": r.type, "value": r.value.hex()} for r in records],
                                 v["records"])
                self.assertEqual(status, v["status"])
                if status == "ok":
                    self.assertEqual(encode_records(records).hex(), v["payload"])

    def test_device(self):
        for v in self.vectors("device"):
            with self.subTest(name=v["name"]):
                name = v["name"].encode("latin-1")
                value = encode_device(v["proto_version"], v["fw_major"], v["fw_minor"],
                                      v["fw_patch"], name)
                self.assertEqual(value.hex(), v["value"])
                dev = decode_device(value)
                self.assertEqual((dev.proto_version, dev.fw_major, dev.fw_minor, dev.fw_patch),
                                 (v["proto_version"], v["fw_major"], v["fw_minor"], v["fw_patch"]))
                self.assertEqual(dev.c_name.decode("latin-1"), v["decoded_name"])
                self.assertEqual(dev.encode().hex(), v["value"])

    def test_device_decode_errors(self):
        for v in self.vectors("device_decode_errors"):
            with self.subTest(len=len(v["wire"]) // 2):
                with self.assertRaises(NLError) as cm:
                    decode_device(h(v["wire"]))
                self.assertEqual(cm.exception.status, v["status"])

    def test_claims(self):
        for v in self.vectors("claims"):
            with self.subTest(n=len(v["claims"])):
                claims = [Claim(**c) for c in v["claims"]]
                self.assertEqual(encode_claims(claims).hex(), v["value"])
                self.assertEqual(decode_claims(h(v["value"])), claims)

    def test_claims_errors(self):
        for v in self.vectors("claims_errors"):
            with self.subTest(v=v):
                with self.assertRaises(NLError) as cm:
                    if v["op"] == "encode":
                        encode_claims([Claim(1, 1, 1)] * v["count"])
                    else:
                        decode_claims(h(v["value"]))
                self.assertEqual(cm.exception.status, v["status"])

    def test_plugin_data(self):
        for v in self.vectors("plugin_data"):
            with self.subTest(plugin_type=v["plugin_type"]):
                value = encode_plugin_data(v["plugin_type"], h(v["data"]))
                self.assertEqual(value.hex(), v["value"])
                self.assertEqual(decode_plugin_data(value), (v["plugin_type"], h(v["data"])))

    def test_congestion(self):
        for v in self.vectors("congestion"):
            with self.subTest(v=v):
                value = encode_congestion(v["zone_mask"], v["dropped"])
                self.assertEqual(value.hex(), v["value"])
                self.assertEqual(decode_congestion(value), (v["zone_mask"], v["dropped"]))

    def test_queue(self):
        for v in self.vectors("queue"):
            with self.subTest(name=v["name"]):
                q = MetaQueue()
                for i, op in enumerate(v["ops"]):
                    if op["op"] == "push":
                        try:
                            q.push(op["type"], h(op["value"]))
                            status = "ok"
                        except NLError as e:
                            status = e.status
                        self.assertEqual(status, op["status"], "op %d" % i)
                    elif op["op"] == "remove_type":
                        q.remove_type(op["type"])
                    elif op["op"] == "pack":
                        self.assertEqual(q.pack(op["cap"]).hex(), op["payload"], "op %d" % i)
                    else:
                        self.fail("unknown op %r" % op["op"])
                    self.assertEqual(q.used, op["used"], "op %d" % i)
                self.assertEqual(q.dropped, v["dropped"])


class MetaUnit(unittest.TestCase):
    def test_iter_records_raises_after_good_records(self):
        it = iter_records(bytes.fromhex("0501610302"))
        self.assertEqual(next(it), MetaRecord(5, b"a"))
        with self.assertRaises(NLError) as cm:
            next(it)
        self.assertEqual(cm.exception.status, "proto")

    def test_record_limits(self):
        self.assertEqual(len(encode_record(0x80, bytes(MAX_VALUE))), 100)
        with self.assertRaises(NLError):
            encode_record(0x80, bytes(MAX_VALUE + 1))
        with self.assertRaises(NLError):
            encode_records([MetaRecord(1, bytes(60)), MetaRecord(1, bytes(60))])

    def test_device_name_utf8_and_truncation(self):
        value = encode_device(1, 0, 1, 0, "café")
        self.assertEqual(decode_device(value).name, "café")
        self.assertEqual(len(encode_device(1, 0, 1, 0, "x" * 40)), 28)
        self.assertEqual(DeviceAnnounce(name_bytes=b"ab\0cd").name, "ab")

    def test_congestion_clamps(self):
        self.assertEqual(encode_congestion(1, 70000).hex(), "01ffff")

    def test_debug_text_truncated_to_98_bytes(self):
        self.assertEqual(len(encode_debug_text("x" * 200)), MAX_VALUE)

    def test_plugin_data_limits(self):
        with self.assertRaises(NLError) as cm:
            encode_plugin_data(1, bytes(97))
        self.assertEqual(cm.exception.status, "size")
        with self.assertRaises(NLError):
            decode_plugin_data(b"\x01")

    def test_describe_record(self):
        d = describe_record(MetaRecord(MetaType.CLAIM_ANNOUNCE, bytes.fromhex("03020201")))
        self.assertEqual(d["claims"][0]["mode_name"], "exclusive")
        d = describe_record(MetaRecord(MetaType.DEVICE_ANNOUNCE, b"\x01"))
        self.assertEqual(d["error"], "proto")
        d = describe_record(MetaRecord(MetaType.PEERS, b"\x41"))
        self.assertEqual((d["type_name"], d["peers"]), ("PEERS", [0, 6]))
        self.assertEqual(describe_record(MetaRecord(MetaType.PEERS, b""))["error"], "proto")
        self.assertEqual(describe_record(MetaRecord(0x90, b""))["type_name"], "VENDOR_0x90")

    def test_queue_stalls_on_oversized_head(self):
        q = MetaQueue()
        q.push(0x80, bytes(98))
        self.assertEqual(q.pack(99), b"")
        self.assertEqual(q.used, 100)


if __name__ == "__main__":
    unittest.main()
