#!/usr/bin/env python3
"""Decode NOVA-LINK fragments and SPI link byte streams from hex.

Examples:
    nl_decode.py 2007010401000100 6e6f7661
    nl_decode.py aa0300... --mode link
    nl_decode.py -f capture.txt --join --json
    some_tool | nl_decode.py -f -

Each positional argument and each non-blank line of a file (text after '#'
is ignored) is one input. --join concatenates them into one buffer, which
is what you want for an SPI stream that was split across lines.

Exit status: 0 on success, 1 if any input failed to decode, 2 on usage or
hex-parsing errors.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from novalink import NLError, parse_hex  # noqa: E402
from novalink.common import META_ZONE  # noqa: E402
from novalink.fragment import decode_fragment  # noqa: E402
from novalink.link import (Cmd, LinkParser, Pong, RadioParams, RadioStatus,  # noqa: E402
                           ZonePlan, cmd_name, decode_frame, decode_stream)
from novalink.meta import decode_records, describe_record  # noqa: E402
from novalink.segment import Reassembler, parse_segment_header, segment_problem  # noqa: E402


# ---- Decoding into plain dicts (shared by text and --json output) -----------

def describe_fragment(raw):
    """Decode a fragment and its zone 0 records / segment sub-header."""
    try:
        frag = decode_fragment(raw)
    except NLError as e:
        return {"error": e.status, "message": str(e), "raw": raw.hex()}
    d = frag.to_dict()
    if frag.zone == META_ZONE:
        records, status = decode_records(frag.payload)
        d["meta"] = {"records": [describe_record(r) for r in records], "status": status}
        if status != "ok":
            d["error"] = status
    elif frag.payload and segment_problem(frag.payload) is None:
        index, count, data = parse_segment_header(frag.payload)
        d["segment"] = {"index": index, "count": count, "data_len": len(data)}
    return d


_PAYLOAD_CODECS = {
    Cmd.ZONE_CONFIG: ("zone_plan", ZonePlan),
    Cmd.RADIO_CONFIG: ("radio_params", RadioParams),
    Cmd.RSP_PONG: ("pong", Pong),
    Cmd.RSP_STATUS: ("status", RadioStatus),
}


def describe_link_frame(cmd, data, offset=None):
    d = {"cmd": cmd, "cmd_name": cmd_name(cmd), "len": len(data), "data": data.hex()}
    if offset is not None:
        d["offset"] = offset
    if cmd in (Cmd.PUSH, Cmd.RSP_FRAGMENT):
        if cmd == Cmd.RSP_FRAGMENT and not data:
            d["note"] = "no fragment pending"
        else:
            d["fragment"] = describe_fragment(data)
            if "error" in d["fragment"]:
                d["error"] = d["fragment"]["error"]
    elif cmd in _PAYLOAD_CODECS:
        key, codec = _PAYLOAD_CODECS[cmd]
        try:
            d[key] = codec.decode(data).to_dict()
        except NLError as e:
            d["error"] = e.status
            d["message"] = str(e)
    elif cmd in (Cmd.PING, Cmd.PULL, Cmd.STATUS):
        if data:
            d["note"] = "unexpected data for %s" % cmd_name(cmd)
    else:
        d["note"] = "unknown command"
    return d


def decode_link_scan(buf):
    """Repeated nl_link_decode, like the radio's SPI handler."""
    frames = []
    off = 0
    results = decode_stream(buf)
    for r in results:
        if r.status == "ok":
            start = off + r.consumed - len(r.frame.data) - 4
            frames.append(describe_link_frame(r.frame.cmd, r.frame.data, start))
            off += r.consumed
    last = results[-1]
    d = {"kind": "link", "decoder": "scan", "frames": frames, "status": last.status}
    if last.status != "ok" and frames:
        d["discarded_tail"] = len(buf) - off
    return d


def decode_link_parser(buf):
    """Byte-at-a-time nl_link_parser_feed."""
    p = LinkParser()
    frames = []
    for at, f in p.feed_bytes(buf):
        frames.append(describe_link_frame(f.cmd, f.data, at - len(f.data) - 3))
    return {"kind": "link", "decoder": "parser", "frames": frames,
            "crc_errors": p.crc_errors, "len_errors": p.len_errors,
            "cmd_errors": p.cmd_errors, "state": p.state}


def decode_input(buf, mode, use_parser):
    if mode == "auto":
        mode = "link" if decode_frame(buf).status == "ok" else "fragment"
    if mode == "fragment":
        d = {"kind": "fragment", "fragment": describe_fragment(buf)}
        failed = "error" in d["fragment"]
    else:
        d = decode_link_parser(buf) if use_parser else decode_link_scan(buf)
        failed = (not d["frames"] or d.get("status") == "crc" or d.get("crc_errors", 0) > 0
                  or any("error" in f for f in d["frames"]))
    return d, failed


def fragments_of(item):
    if item["kind"] == "fragment":
        yield item["fragment"]
    else:
        for f in item["frames"]:
            if "fragment" in f:
                yield f["fragment"]


# ---- Text rendering ----------------------------------------------------------

def _hexdump(hexs, width=32):
    b = bytes.fromhex(hexs)
    return [b[i:i + width].hex(" ") for i in range(0, len(b), width)] or [""]


def render_record(rec, ind):
    head = "%smeta %s (0x%02x) len %d" % (ind, rec["type_name"], rec["type"], rec["len"])
    if "device" in rec:
        dv = rec["device"]
        return ["%s: proto %d fw %d.%d.%d name %s" % (head, dv["proto_version"], dv["fw_major"],
                                                      dv["fw_minor"], dv["fw_patch"],
                                                      json.dumps(dv["name"]))]
    if "claims" in rec:
        out = ["%s: %d claim(s)" % (head, len(rec["claims"]))]
        out += ["%s  zone %d %s plugin_type 0x%04x" % (ind, c["zone"], c["mode_name"],
                                                       c["plugin_type"]) for c in rec["claims"]]
        return out
    if "plugin_data" in rec:
        pd = rec["plugin_data"]
        return ["%s: plugin_type 0x%04x data [%s]" % (head, pd["plugin_type"],
                                                      bytes.fromhex(pd["data"]).hex(" "))]
    if "congestion" in rec:
        c = rec["congestion"]
        return ["%s: zones %s dropped %d" % (head, c["zones"], c["dropped"])]
    if "text" in rec:
        return ["%s: %s" % (head, json.dumps(rec["text"]))]
    if "peers" in rec:
        return ["%s: knows %s" % (head, rec["peers"])]
    tail = " (%s)" % rec["error"] if "error" in rec else ""
    return ["%s%s: [%s]" % (head, tail, bytes.fromhex(rec["value"]).hex(" "))]


def render_fragment(f, ind):
    if "message" in f and "origin" not in f:
        return ["%sfragment ERROR %s: %s  [%s]" % (ind, f["error"], f["message"],
                                                  bytes.fromhex(f["raw"]).hex(" "))]
    flags = "|".join(f["flag_names"]) or "-"
    out = ["%sfragment origin %d zone %d flags %s seq %d payload %d bytes"
           % (ind, f["origin"], f["zone"], flags, f["seq"], f["payload_len"])]
    if "meta" in f:
        for rec in f["meta"]["records"]:
            out += render_record(rec, ind + "  ")
        if f["meta"]["status"] != "ok":
            out.append("%s  meta ERROR %s: truncated record" % (ind, f["meta"]["status"]))
    else:
        if "segment" in f:
            s = f["segment"]
            out.append("%s  segment %d of %d (index %d), %d data bytes"
                       % (ind, s["index"] + 1, s["count"], s["index"], s["data_len"]))
        if f["payload"]:
            out += ["%s  %s" % (ind, line) for line in _hexdump(f["payload"])]
    return out


def render_codec(key, d, ind):
    if key == "zone_plan":
        return ["%szone %d priority %d subghz %d Hz 2.4G %d Hz"
                % (ind, z["zone"], z["priority"], z["subghz_hz"], z["ghz24_hz"]) for z in d["zones"]]
    if key == "status":
        d = dict(d)
        d["flags"] = "%d (%s)" % (d["flags"], "|".join(d.pop("flag_names")) or "-")
    return ["%s%s" % (ind, ", ".join("%s %s" % kv for kv in d.items()))]


def render_link_frame(fr, ind):
    off = "@%d " % fr["offset"] if "offset" in fr else ""
    out = ["%s%s%s (0x%02x) len %d" % (ind, off, fr["cmd_name"], fr["cmd"], fr["len"])]
    sub = ind + "  "
    if "fragment" in fr:
        out += render_fragment(fr["fragment"], sub)
    for key in ("zone_plan", "radio_params", "pong", "status"):
        if key in fr:
            out += render_codec(key, fr[key], sub)
    if "message" in fr:
        out.append("%sERROR %s: %s" % (sub, fr["error"], fr["message"]))
    if "note" in fr:
        out.append("%s(%s)" % (sub, fr["note"]))
    if fr["data"] and "fragment" not in fr and not any(k in fr for k in _CODEC_KEYS):
        out += ["%s%s" % (sub, line) for line in _hexdump(fr["data"])]
    return out


_CODEC_KEYS = ("zone_plan", "radio_params", "pong", "status")


def render_item(item):
    out = ["[%s] %d bytes" % (item["source"], item["length"])]
    if item["kind"] == "fragment":
        out += render_fragment(item["fragment"], "  ")
        return out
    if item["decoder"] == "scan":
        summary = "link (nl_link_decode scan): %d frame(s), final status %s" % (
            len(item["frames"]), item["status"])
        if "discarded_tail" in item:
            summary += ", %d trailing byte(s) discarded" % item["discarded_tail"]
    else:
        summary = ("link (byte parser): %d frame(s), crc_errors %d len_errors %d cmd_errors %d, "
                   "end state %d" % (len(item["frames"]), item["crc_errors"], item["len_errors"],
                                     item["cmd_errors"], item["state"]))
    out.append("  " + summary)
    for fr in item["frames"]:
        out += render_link_frame(fr, "  ")
    return out


# ---- CLI ---------------------------------------------------------------------

def read_inputs(args):
    items = []
    for i, text in enumerate(args.hex, 1):
        items.append(("arg %d" % i, text))
    for path in args.file or []:
        fh = sys.stdin if path == "-" else open(path, encoding="utf-8")
        try:
            for n, line in enumerate(fh, 1):
                line = line.split("#", 1)[0].strip()
                if line:
                    items.append(("%s:%d" % ("stdin" if path == "-" else path, n), line))
        finally:
            if fh is not sys.stdin:
                fh.close()
    parsed = [(src, parse_hex(text)) for src, text in items]
    if args.join and parsed:
        parsed = [("joined %d input(s)" % len(parsed), b"".join(b for _, b in parsed))]
    return parsed


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Decode NOVA-LINK DataFragments and SPI link streams from hex.",
        epilog="Exit status: 0 ok, 1 decode error, 2 usage/hex error.")
    ap.add_argument("hex", nargs="*", help="hex string(s); spaces, colons and 0x prefixes are ok")
    ap.add_argument("-f", "--file", action="append", metavar="FILE",
                    help="file with one hex input per line ('-' for stdin); repeatable")
    ap.add_argument("--join", action="store_true", help="concatenate all inputs into one buffer")
    ap.add_argument("--mode", choices=("auto", "fragment", "link"), default="auto",
                    help="auto (default) treats an input as a link stream if it contains a "
                         "valid link frame, otherwise as a raw fragment")
    ap.add_argument("--stream", action="store_true",
                    help="decode link streams with the byte-at-a-time parser "
                         "(nl_link_parser_feed) instead of the nl_link_decode scan")
    ap.add_argument("--reassemble", action="store_true",
                    help="reassemble segmented messages per (origin, zone) across inputs")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    if not args.hex and not args.file:
        ap.error("no input: give hex strings or -f FILE")
    try:
        inputs = read_inputs(args)
    except (OSError, ValueError) as e:
        print("nl_decode: %s" % e, file=sys.stderr)
        return 2

    results = []
    any_failed = False
    reasm = {}
    messages = []
    for src, buf in inputs:
        item, failed = decode_input(buf, args.mode, args.stream)
        item = dict({"source": src, "length": len(buf), "hex": buf.hex()}, **item)
        any_failed |= failed
        results.append(item)
        if args.reassemble:
            for f in fragments_of(item):
                if "segment" not in f:
                    continue
                key = (f["origin"], f["zone"])
                r = reasm.setdefault(key, Reassembler())
                try:
                    msg = r.feed(f["seq"], bytes.fromhex(f["payload"]))
                except NLError as e:
                    messages.append({"origin": key[0], "zone": key[1], "source": src,
                                     "error": e.status, "message": str(e)})
                    continue
                if msg is not None:
                    messages.append({"origin": key[0], "zone": key[1], "source": src,
                                     "len": len(msg), "data": msg.hex()})

    if args.json:
        doc = {"inputs": results}
        if args.reassemble:
            doc["messages"] = messages
        json.dump(doc, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for item in results:
            print("\n".join(render_item(item)))
        if args.reassemble:
            for m in messages:
                if "error" in m:
                    print("message origin %d zone %d: ERROR %s (%s)" % (
                        m["origin"], m["zone"], m["error"], m["message"]))
                else:
                    print("message origin %d zone %d: %d bytes (completed at %s)" % (
                        m["origin"], m["zone"], m["len"], m["source"]))
                    for line in _hexdump(m["data"]):
                        print("  " + line)
    return 1 if any_failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
