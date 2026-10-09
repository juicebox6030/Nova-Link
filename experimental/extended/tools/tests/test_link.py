"""Link framing: CRC-8, nl_link_encode/decode and the byte-at-a-time parser."""

import unittest

from novalink import NLError
from novalink.link import (MAX_DATA, Cmd, LinkFrame, LinkParser, cmd_invalid, cmd_name, crc8,
                           decode_frame, decode_stream, encode_frame)
from tests.vectors import VectorMixin, h


class Crc8Vectors(VectorMixin, unittest.TestCase):
    VECTOR_FILE = "crc8"
    SECTIONS = ("crc8",)

    def test_crc8(self):
        for v in self.vectors("crc8"):
            with self.subTest(data=v["data"]):
                self.assertEqual(crc8(h(v["data"])), v["crc"])

    def test_check_value(self):
        self.assertEqual(crc8(b"123456789"), 0xF4)

    def test_chaining(self):
        for v in self.vectors("crc8"):
            data = h(v["data"])
            mid = len(data) // 2
            self.assertEqual(crc8(data[mid:], crc8(data[:mid])), v["crc"])


class LinkVectors(VectorMixin, unittest.TestCase):
    VECTOR_FILE = "link_frames"
    SECTIONS = ("encode", "encode_errors", "decode", "parser")

    def test_encode(self):
        for v in self.vectors("encode"):
            with self.subTest(cmd=v["cmd"], data=v["data"]):
                self.assertEqual(encode_frame(v["cmd"], h(v["data"])).hex(), v["frame"])
                self.assertEqual(LinkFrame(v["cmd"], h(v["data"])).encode().hex(), v["frame"])

    def test_encode_errors(self):
        for v in self.vectors("encode_errors"):
            with self.subTest(v=v):
                with self.assertRaises(NLError) as cm:
                    encode_frame(v["cmd"], bytes(v["data_len"]))
                self.assertEqual(cm.exception.status, v["status"])

    def test_encoded_frames_decode(self):
        for v in self.vectors("encode"):
            r = decode_frame(h(v["frame"]))
            if cmd_invalid(v["cmd"]):
                self.assertNotEqual(r.status, "ok")
            else:
                self.assertEqual((r.status, r.frame.cmd, r.frame.data.hex(), r.consumed),
                                 ("ok", v["cmd"], v["data"], len(v["frame"]) // 2))

    def test_decode(self):
        for v in self.vectors("decode"):
            with self.subTest(name=v["name"]):
                got = []
                for r in decode_stream(h(v["input"])):
                    d = {"status": r.status}
                    if r.status == "ok":
                        d["cmd"] = r.frame.cmd
                        d["data"] = r.frame.data.hex()
                    d["consumed"] = r.consumed
                    got.append(d)
                self.assertEqual(got, v["results"])

    def test_parser(self):
        for v in self.vectors("parser"):
            with self.subTest(name=v["name"]):
                p = LinkParser()
                frames = [{"at": at, "cmd": f.cmd, "data": f.data.hex()}
                          for at, f in p.feed_bytes(h(v["input"]))]
                self.assertEqual(frames, v["frames"])
                self.assertEqual((p.crc_errors, p.len_errors, p.cmd_errors, p.state),
                                 (v["crc_errors"], v["len_errors"], v["cmd_errors"], v["state"]))

    def test_parser_and_scan_streams_match(self):
        names = {v["name"] for v in self.vectors("parser")}
        self.assertEqual(names, {v["name"] for v in self.vectors("decode")})


class LinkUnit(unittest.TestCase):
    def test_cmd_names(self):
        self.assertEqual(cmd_name(Cmd.RSP_STATUS), "RSP_STATUS")
        self.assertEqual(cmd_name(0x42), "0x42")

    def test_max_data(self):
        f = encode_frame(Cmd.PUSH, bytes(range(MAX_DATA)))
        self.assertEqual(len(f), MAX_DATA + 4)
        self.assertEqual(decode_frame(f).frame.data, bytes(range(MAX_DATA)))

    def test_invalid_cmds_are_encoded_but_never_decoded(self):
        for cmd in (0x00, 0xFF):
            frame = encode_frame(cmd)
            self.assertEqual(decode_frame(frame).status, "empty")
            p = LinkParser()
            self.assertEqual(p.feed_bytes(frame), [])
            self.assertEqual(p.cmd_errors, 1)

    def test_parser_double_sync(self):
        p = LinkParser()
        frames = p.feed_bytes(b"\xaa\xaa" + encode_frame(Cmd.PING)[1:])
        self.assertEqual([f.cmd for _, f in frames], [Cmd.PING])

    def test_parser_recovers_after_crc_error(self):
        p = LinkParser()
        bad = bytearray(encode_frame(Cmd.PUSH, b"abc"))
        bad[-1] ^= 1
        out = p.feed_bytes(bytes(bad) + encode_frame(Cmd.PULL))
        self.assertEqual([f.cmd for _, f in out], [Cmd.PULL])
        self.assertEqual(p.crc_errors, 1)

    def test_partial_frame_status(self):
        r = decode_frame(encode_frame(Cmd.PUSH, b"abcd")[:-1])
        self.assertEqual((r.status, r.consumed), ("empty", 7))


if __name__ == "__main__":
    unittest.main()
