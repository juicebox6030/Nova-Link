"""Segmentation and reassembly against tests/vectors/segments.json."""

import unittest

from novalink import NLError
from novalink.segment import (DATA_MAX, MAX_MESSAGE, Reassembler, build_segment, build_segments,
                              parse_segment_header, seg_count, segment_problem)
from tests.vectors import VectorMixin, h


class SegmentVectors(VectorMixin, unittest.TestCase):
    VECTOR_FILE = "segments"
    SECTIONS = ("count", "build", "build_errors", "reasm")

    def test_count(self):
        for v in self.vectors("count"):
            with self.subTest(msg_len=v["msg_len"]):
                if "count" in v:
                    self.assertEqual(seg_count(v["msg_len"]), v["count"])
                else:
                    with self.assertRaises(NLError) as cm:
                        seg_count(v["msg_len"])
                    self.assertEqual(cm.exception.status, v["status"])

    def test_build(self):
        for v in self.vectors("build"):
            with self.subTest(msg_len=len(v["message"]) // 2):
                segs = build_segments(h(v["message"]))
                self.assertEqual([s.hex() for s in segs], v["segments"])

    def test_build_roundtrip(self):
        for v in self.vectors("build"):
            r = Reassembler()
            results = [r.feed(7 + i, h(s)) for i, s in enumerate(v["segments"])]
            self.assertEqual(results[-1], h(v["message"]))
            self.assertTrue(all(x is None for x in results[:-1]))

    def test_build_errors(self):
        for v in self.vectors("build_errors"):
            with self.subTest(v=v):
                with self.assertRaises(NLError) as cm:
                    build_segment(bytes(v["msg_len"]), v["index"])
                self.assertEqual(cm.exception.status, v["status"])

    def test_reasm(self):
        for v in self.vectors("reasm"):
            with self.subTest(name=v["name"]):
                r = Reassembler(v["cap"])
                for i, feed in enumerate(v["feeds"]):
                    try:
                        msg = r.feed(feed["seq"], h(feed["payload"]))
                        result = "more" if msg is None else "complete"
                    except NLError as e:
                        msg, result = None, e.status
                    self.assertEqual(result, feed["result"], "feed %d" % i)
                    if result == "complete":
                        self.assertEqual(msg.hex(), feed["message"], "feed %d" % i)
                self.assertEqual((r.completed, r.aborted), (v["completed"], v["aborted"]))


class SegmentUnit(unittest.TestCase):
    def test_limits(self):
        self.assertEqual(MAX_MESSAGE, 1584)
        self.assertEqual(len(build_segments(bytes(MAX_MESSAGE))), 16)

    def test_build_cap(self):
        with self.assertRaises(NLError) as cm:
            build_segment(bytes(10), 0, cap=10)
        self.assertEqual(cm.exception.status, "size")

    def test_header(self):
        self.assertEqual(parse_segment_header(b"\x21xyz"), (2, 2, b"xyz"))
        self.assertIsNone(segment_problem(b"\x00"))
        self.assertIsNotNone(segment_problem(b"\x01" + bytes(DATA_MAX - 1)))
        self.assertIsNotNone(segment_problem(b"\x11"))


if __name__ == "__main__":
    unittest.main()
