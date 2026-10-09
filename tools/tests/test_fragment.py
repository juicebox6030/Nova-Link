"""DataFragment codec against tests/vectors/fragments.json."""

import unittest

from novalink import NLError
from novalink.fragment import (FLAG_BURST, FLAG_MGMT_LISTEN, Fragment, decode_fragment,
                               encode_fragment, flag_names, seq_cmp)
from tests.vectors import VectorMixin, h


class FragmentVectors(VectorMixin, unittest.TestCase):
    VECTOR_FILE = "fragments"
    SECTIONS = ("encode", "encode_errors", "decode", "decode_errors")

    def test_encode(self):
        for v in self.vectors("encode"):
            with self.subTest(v=v["wire"][:8]):
                wire = encode_fragment(v["origin"], v["zone"], v["flags"], v["seq"], h(v["payload"]))
                self.assertEqual(wire.hex(), v["wire"])
                frag = Fragment(v["origin"], v["zone"], v["flags"], v["seq"], h(v["payload"]))
                self.assertEqual(frag.encode().hex(), v["wire"])

    def test_encode_errors(self):
        for v in self.vectors("encode_errors"):
            with self.subTest(v=v):
                with self.assertRaises(NLError) as cm:
                    encode_fragment(v["origin"], v["zone"], v["flags"], 0, bytes(v["payload_len"]))
                self.assertEqual(cm.exception.status, v["status"])

    def test_decode(self):
        for v in self.vectors("decode"):
            with self.subTest(wire=v["wire"][:8]):
                f = decode_fragment(h(v["wire"]))
                self.assertEqual((f.origin, f.zone, f.flags, f.seq, f.payload.hex()),
                                 (v["origin"], v["zone"], v["flags"], v["seq"], v["payload"]))
                self.assertEqual(f.encode().hex(), v["wire"])

    def test_decode_covers_every_header(self):
        headers = {h(v["wire"])[0] for v in self.vectors("decode")}
        self.assertEqual(headers, set(range(256)))

    def test_decode_errors(self):
        for v in self.vectors("decode_errors"):
            with self.subTest(len=len(v["wire"]) // 2):
                with self.assertRaises(NLError) as cm:
                    decode_fragment(h(v["wire"]))
                self.assertEqual(cm.exception.status, v["status"])


class FragmentUnit(unittest.TestCase):
    def test_flags(self):
        f = Fragment(1, 0, FLAG_BURST | FLAG_MGMT_LISTEN, 0)
        self.assertTrue(f.burst and f.mgmt_listen and f.is_meta)
        self.assertEqual(flag_names(f.flags), ["BURST", "MGMT_LISTEN"])
        self.assertEqual(f.to_dict()["payload_len"], 0)

    def test_seq_cmp(self):
        self.assertEqual(seq_cmp(5, 5), 0)
        self.assertEqual(seq_cmp(6, 5), 1)
        self.assertEqual(seq_cmp(5, 6), -1)
        self.assertEqual(seq_cmp(0, 255), 1)
        self.assertEqual(seq_cmp(255, 0), -1)
        self.assertEqual(seq_cmp(127, 0), 127)
        self.assertEqual(seq_cmp(128, 0), -128)
        self.assertEqual(seq_cmp(0, 128), -128)

    def test_bad_seq(self):
        with self.assertRaises(NLError) as cm:
            encode_fragment(0, 0, 0, 256)
        self.assertEqual(cm.exception.status, "arg")


if __name__ == "__main__":
    unittest.main()
