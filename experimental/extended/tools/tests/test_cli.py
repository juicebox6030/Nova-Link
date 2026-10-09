"""End-to-end tests of tools/nl_decode.py and tools/nl_airtime.py (run as
subprocesses with the current interpreter)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from novalink.fragment import encode_fragment
from novalink.link import Cmd, Pong, RadioParams, encode_frame
from novalink.meta import Claim, MetaType, encode_claims, encode_device, encode_records, MetaRecord
from novalink.segment import build_segments
from tests.vectors import TOOLS_DIR, load

DECODE = str(TOOLS_DIR / "nl_decode.py")
AIRTIME = str(TOOLS_DIR / "nl_airtime.py")


def run(script, *args, stdin=None):
    p = subprocess.run([sys.executable, script] + list(args), input=stdin, capture_output=True,
                       text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


def meta_fragment():
    payload = encode_records([
        MetaRecord(MetaType.DEVICE_ANNOUNCE, encode_device(1, 0, 3, 2, "stage-left")),
        MetaRecord(MetaType.CLAIM_ANNOUNCE, encode_claims([Claim(3, 2, 0x0102)])),
    ])
    return encode_fragment(2, 0, 0, 9, payload)


class DecodeCli(unittest.TestCase):
    def decode_json(self, *args, expect=0, stdin=None):
        rc, out, err = run(DECODE, "--json", *args, stdin=stdin)
        if expect is not None:
            self.assertEqual(rc, expect, err)
        return json.loads(out)

    def test_raw_fragment_with_meta(self):
        doc = self.decode_json(meta_fragment().hex())
        item = doc["inputs"][0]
        self.assertEqual((item["source"], item["kind"]), ("arg 1", "fragment"))
        recs = item["fragment"]["meta"]["records"]
        self.assertEqual(recs[0]["device"]["name"], "stage-left")
        self.assertEqual(recs[1]["claims"][0]["mode_name"], "exclusive")

    def test_hex_formats(self):
        wire = encode_fragment(1, 4, 0, 1, b"\x01\x02")
        spaced = " ".join("0x%02x" % b for b in wire)
        coloned = ":".join("%02X" % b for b in wire)
        a = self.decode_json(spaced, coloned)
        self.assertEqual([i["hex"] for i in a["inputs"]], [wire.hex(), wire.hex()])

    def test_link_stream_scan_and_parser(self):
        stream = (encode_frame(Cmd.RSP_FRAGMENT, meta_fragment()) +
                  encode_frame(Cmd.RSP_PONG, Pong(1, 0, 1, 0).encode()) +
                  encode_frame(Cmd.RADIO_CONFIG, RadioParams.default().encode()) +
                  encode_frame(Cmd.RSP_FRAGMENT))
        scan = self.decode_json(stream.hex())["inputs"][0]
        self.assertEqual((scan["kind"], scan["decoder"]), ("link", "scan"))
        self.assertEqual([f["cmd_name"] for f in scan["frames"]],
                         ["RSP_FRAGMENT", "RSP_PONG", "RADIO_CONFIG", "RSP_FRAGMENT"])
        self.assertEqual(scan["frames"][1]["offset"], len(meta_fragment()) + 4)
        self.assertEqual(scan["frames"][2]["radio_params"]["tx_repeats"],
                         RadioParams.default().tx_repeats)
        self.assertEqual(scan["frames"][3]["note"], "no fragment pending")
        parsed = self.decode_json("--stream", stream.hex())["inputs"][0]
        self.assertEqual(parsed["decoder"], "parser")
        self.assertEqual([f["offset"] for f in parsed["frames"]],
                         [f["offset"] for f in scan["frames"]])

    def test_scan_vs_parser_differ_like_c(self):
        v = [x for x in load("link_frames")["decode"] if x["name"] == "spurious_sync_swallows_frame"][0]
        p = [x for x in load("link_frames")["parser"] if x["name"] == v["name"]][0]
        scan = self.decode_json("--mode", "link", v["input"], expect=None)
        parsed = self.decode_json("--mode", "link", "--stream", v["input"], expect=None)
        self.assertEqual(len(scan["inputs"][0]["frames"]),
                         sum(1 for r in v["results"] if r["status"] == "ok"))
        self.assertEqual(len(parsed["inputs"][0]["frames"]), len(p["frames"]))

    def test_file_join_and_reassemble(self):
        msg = bytes(range(256)) * 2
        frames = [encode_frame(Cmd.PUSH, encode_fragment(5, 3, 0, 20 + i, seg))
                  for i, seg in enumerate(build_segments(msg))]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cap.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("# capture\n\n")
                for fr in frames:
                    fh.write(fr.hex() + "  # frame\n")
            doc = self.decode_json("-f", path, "--reassemble")
            self.assertEqual([i["source"] for i in doc["inputs"]],
                             ["%s:%d" % (path, n + 3) for n in range(len(frames))])
            self.assertEqual(doc["messages"], [{"origin": 5, "zone": 3,
                                                "source": "%s:%d" % (path, len(frames) + 2),
                                                "len": len(msg), "data": msg.hex()}])
            joined = self.decode_json("-f", path, "--join")
            self.assertEqual(len(joined["inputs"]), 1)
            self.assertEqual(joined["inputs"][0]["source"], "joined %d input(s)" % len(frames))
            self.assertEqual(len(joined["inputs"][0]["frames"]), len(frames))
            seg = joined["inputs"][0]["frames"][0]["fragment"]["segment"]
            self.assertEqual((seg["index"], seg["count"]), (0, len(frames)))

    def test_stdin(self):
        doc = self.decode_json("-f", "-", stdin=meta_fragment().hex() + "\n")
        self.assertEqual(doc["inputs"][0]["source"], "stdin:1")

    def test_text_output(self):
        stream = encode_frame(Cmd.RSP_FRAGMENT, meta_fragment())
        rc, out, err = run(DECODE, stream.hex())
        self.assertEqual(rc, 0, err)
        self.assertIn("RSP_FRAGMENT", out)
        self.assertIn('"stage-left"', out)
        self.assertIn("exclusive", out)

    def test_decode_error_exit_1(self):
        rc, out, _ = run(DECODE, "20")
        self.assertEqual(rc, 1)
        self.assertIn("ERROR size", out)
        bad = bytearray(encode_frame(Cmd.PING))
        bad[-1] ^= 0xFF
        self.assertEqual(run(DECODE, "--mode", "link", bad.hex())[0], 1)
        self.assertEqual(run(DECODE, "--mode", "link", "--stream", bad.hex())[0], 1)

    def test_usage_errors_exit_2(self):
        self.assertEqual(run(DECODE)[0], 2)
        rc, _, err = run(DECODE, "abc")
        self.assertEqual(rc, 2)
        self.assertIn("nl_decode", err)
        self.assertEqual(run(DECODE, "zz")[0], 2)
        self.assertEqual(run(DECODE, "-f", "/nonexistent/nl_decode_input.txt")[0], 2)


class AirtimeCli(unittest.TestCase):
    def test_json_table_and_budget(self):
        rc, out, err = run(AIRTIME, "--json", "--fcc")
        self.assertEqual(rc, 0, err)
        doc = json.loads(out)
        phy = doc["phys"][0]
        self.assertEqual(phy["name"], "subghz-50k")
        self.assertEqual(len(phy["table"]), 101)
        self.assertAlmostEqual(phy["table"][100]["airtime_us"], 18240.0)
        self.assertAlmostEqual(phy["budget"]["airtime_us"], 18240.0)
        self.assertIn("15.249", doc["fcc_note"])

    def test_all_phys_step_and_overrides(self):
        rc, out, err = run(AIRTIME, "--json", "--phy", "all", "--step", "30", "--preamble", "8",
                           "--dual", "--payload", "20", "--duty-limit", "0.01")
        self.assertEqual(rc, 0, err)
        doc = json.loads(out)
        self.assertEqual([p["name"] for p in doc["phys"]], ["ble-1m", "prop-500k", "subghz-50k"])
        for p in doc["phys"]:
            self.assertEqual(p["preamble_bytes"], 8)
            self.assertEqual([r["payload_len"] for r in p["table"]], [0, 30, 60, 90, 100])
            self.assertEqual(p["budget"]["bands"], 2)
            self.assertIsNotNone(p["budget"]["max_fps_duty"])

    def test_text(self):
        rc, out, err = run(AIRTIME, "--step", "50")
        self.assertEqual(rc, 0, err)
        self.assertIn("subghz-50k", out)
        self.assertIn("18240", out)

    def test_bad_args(self):
        self.assertEqual(run(AIRTIME, "--payload", "101")[0], 2)
        self.assertEqual(run(AIRTIME, "--repeats", "0")[0], 2)
        self.assertEqual(run(AIRTIME, "--phy", "nope")[0], 2)


if __name__ == "__main__":
    unittest.main()
