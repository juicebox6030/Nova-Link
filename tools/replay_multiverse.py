#!/usr/bin/env python3
"""Replay synthetic Multiverse-model logs through the portable C RX engine.

No RF transmission or hardware access. Real/candidate-PHY profiles are refused:
there is no verified Multiverse decoder yet. The future RF adapter can reuse the
normalized packet API without adopting this test codec.
"""
# SPDX-License-Identifier: GPL-3.0-only

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

if __package__:
    from .analyze_rf_capture import read_capture
else:
    from analyze_rf_capture import read_capture

PROFILE = "nova-mv-synthetic-v1"
MAX_PACKET_BYTES = 542


def integer(minimum, maximum):
    def convert(text):
        if re.fullmatch(r"[0-9]+", text) is None:
            raise argparse.ArgumentTypeError("expected a non-negative integer")
        value = int(text)
        if not minimum <= value <= maximum:
            raise argparse.ArgumentTypeError(f"expected {minimum}..{maximum}")
        return value
    return convert


def replay(entries, executable, universe=1, session=42, loss_us=100000,
           assembly_us=5000, end_us=None):
    entries = list(entries)
    if not entries:
        raise ValueError("capture contains no observations")
    for entry in entries:
        if entry["profile"] != PROFILE or entry.get("synthetic") is not True:
            raise ValueError("only explicitly synthetic nova-mv-synthetic-v1 logs can be decoded; real Multiverse RF format is unknown")
        if entry["timestamp_us"] > 2**64 - 1:
            raise ValueError("timestamp_us exceeds the C adapter clock")
        if len(entry["payload_hex"]) // 2 > MAX_PACKET_BYTES:
            raise ValueError("synthetic payload exceeds 542 bytes")
        expected = entry.get("expected_slots_hex")
        if expected is not None and (not isinstance(expected, str) or
                re.fullmatch(r"(?:[0-9a-fA-F]{2}){0,512}", expected) is None):
            raise ValueError("expected_slots_hex must encode 0..512 slots")
    if end_us is None:
        end_us = entries[-1]["timestamp_us"]
    if end_us < entries[-1]["timestamp_us"] or end_us > 2**64 - 1:
        raise ValueError("end_us must be >= the last observation and fit uint64")
    text = "".join(f'{e["timestamp_us"]} {e["crc"]} {e["payload_hex"] or "-"}\n' for e in entries)
    result = subprocess.run([str(executable), str(universe), str(session), str(loss_us),
                             str(assembly_us), str(end_us)], input=text,
                            text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "C replay engine failed")
    events = [json.loads(line) for line in result.stdout.splitlines()]
    if len(events) != len(entries) + 1 or not events[-1].get("summary"):
        raise ValueError("unexpected C replay output")
    checked = 0
    for event, entry in zip(events[:-1], entries):
        event["stimulus"] = entry["stimulus"]
        if event["result"] == "frame_ready" and "expected_slots_hex" in entry:
            if event["slots_hex"] != entry["expected_slots_hex"].lower():
                raise ValueError(f'level mismatch at {entry["timestamp_us"]} us ({entry["stimulus"]})')
            checked += 1
    summary = events[-1]
    summary["expected_frames_checked"] = checked
    summary["observations"] = len(entries)
    summary["result_counts"] = dict(sorted(Counter(e["result"] for e in events[:-1]).items()))
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--engine", type=Path, default=Path(__file__).resolve().parents[1] / "build/nova-multiverse-replay")
    parser.add_argument("--universe", type=integer(1, 63999), default=1)
    parser.add_argument("--session", type=integer(0, 2**32 - 1), default=42)
    parser.add_argument("--loss-us", type=integer(1, 2**64 - 1), default=100000)
    parser.add_argument("--assembly-us", type=integer(1, 2**64 - 1), default=5000)
    parser.add_argument("--end-us", type=integer(0, 2**64 - 1), help="advance clock after the last observation to check loss")
    parser.add_argument("--output", type=Path, help="write decoded events and summary as JSONL")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    try:
        with args.capture.open(encoding="utf-8") as capture:
            events = replay(read_capture(capture), args.engine.resolve(), args.universe,
                            args.session, args.loss_us, args.assembly_us, args.end_us)
        if args.output and args.output.resolve() == args.capture.resolve():
            raise ValueError("output must not overwrite the capture")
        chosen = events[-1:] if args.summary_only else events
        output = "".join(json.dumps(e, sort_keys=True, allow_nan=False) + "\n" for e in chosen)
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
