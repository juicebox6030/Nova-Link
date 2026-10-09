#!/usr/bin/env python3
"""Summarize 2.4 GHz radio observations; this is not a Multiverse decoder."""
# SPDX-License-Identifier: GPL-3.0-only

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import statistics


def read_capture(lines):
    """Read one receiver's JSONL log with extended, monotonic timestamps."""
    previous = -1
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError("expected an object")
            for key in ("timestamp_us", "frequency_hz"):
                if type(entry.get(key)) is not int:
                    raise ValueError(f"{key} must be an integer")
            if entry["timestamp_us"] < 0:
                raise ValueError("timestamp_us must be non-negative")
            if entry["timestamp_us"] < previous:
                raise ValueError("timestamps must be monotonic; extend timer wraps in firmware")
            if not 2_400_000_000 <= entry["frequency_hz"] <= 2_483_500_000:
                raise ValueError("frequency_hz must be in the 2.4 GHz ISM band")
            for key in ("profile", "stimulus"):
                if key == "stimulus":
                    entry.setdefault(key, "unspecified")
                if not isinstance(entry.get(key), str) or not entry[key].strip():
                    raise ValueError(f"{key} must be a non-empty string")
            payload = entry.get("payload_hex")
            if not isinstance(payload, str) or re.fullmatch(r"(?:[0-9a-fA-F]{2})*", payload) is None:
                raise ValueError("payload_hex must contain complete hex bytes without whitespace")
            entry.setdefault("crc", "unknown")
            if entry["crc"] not in ("ok", "bad", "unknown"):
                raise ValueError("crc must be ok, bad, or unknown")
            rssi = entry.get("rssi_dbm")
            if rssi is not None and (type(rssi) not in (int, float) or not math.isfinite(rssi)):
                raise ValueError("rssi_dbm must be a finite number or null")
            previous = entry["timestamp_us"]
            entry["payload_hex"] = payload.lower()
            yield entry
        except (ValueError, TypeError) as error:
            raise ValueError(f"line {number}: {error}") from error


def summarize(entries):
    groups = defaultdict(list)
    count = 0
    first = last = None
    for entry in entries:
        if first is None:
            first = entry["timestamp_us"]
        last = entry["timestamp_us"]
        count += 1
        groups[(entry["profile"], entry["frequency_hz"], entry["stimulus"])].append(entry)
    if not count:
        raise ValueError("capture contains no observations")

    summaries = []
    for (profile, frequency, stimulus), observed in sorted(groups.items()):
        gaps = [b["timestamp_us"] - a["timestamp_us"] for a, b in zip(observed, observed[1:])]
        rssi = [e["rssi_dbm"] for e in observed if e.get("rssi_dbm") is not None]
        summaries.append({
            "profile": profile,
            "frequency_hz": frequency,
            "stimulus": stimulus,
            "observations": len(observed),
            "crc_counts": dict(sorted(Counter(e["crc"] for e in observed).items())),
            "payload_length_counts": dict(sorted(Counter(len(e["payload_hex"]) // 2 for e in observed).items())),
            "distinct_payloads": len({e["payload_hex"] for e in observed}),
            "rssi_median_dbm": statistics.median(rssi) if rssi else None,
            "observed_gap_us": {
                "min": min(gaps), "median": statistics.median(gaps), "max": max(gaps),
            } if gaps else None,
        })
    return {
        "observations": count,
        "capture_span_us": last - first,
        "multiverse_decoded": False,
        "groups": summaries,
        "interpretation": "Observed gaps include missed receptions and retuning; they do not establish a hop schedule. CRC results describe the configured candidate PHY, not proven Multiverse compatibility.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="JSONL log from one receiver")
    parser.add_argument("--output", type=Path, help="write the summary as JSON")
    args = parser.parse_args()
    try:
        with args.capture.open(encoding="utf-8") as capture:
            report = summarize(read_capture(capture))
        output = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
    except (OSError, ValueError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
