#!/usr/bin/env python3
"""Airtime table and per-zone transmit budget for NOVA-LINK fragments.

Examples:
    nl_airtime.py                         # 50 kbps sub-GHz table, default budget
    nl_airtime.py --phy all --step 10
    nl_airtime.py --repeats 2 --interval-us 20000 --payload 64 --duty-limit 0.01
    nl_airtime.py --phy prop-500k --dual --json
    nl_airtime.py --fcc

The defaults for the budget mirror nl_radio_params_default() in src/nl_link.c.
See novalink/airtime.py for the packet model and its assumptions.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from novalink.airtime import (DEFAULT_PHY, FCC_NOTE, PHYS, airtime_table,  # noqa: E402
                              zone_budget)
from novalink.common import MAX_PAYLOAD  # noqa: E402
from novalink.link import RadioParams  # noqa: E402

_DEFAULTS = RadioParams.default()


def _fmt_rate(v):
    return "-" if v is None else "%.2f" % v


def render_text(phys, tables, budgets, show_fcc):
    out = []
    for phy in phys:
        out.append("PHY %s: %s" % (phy.name, phy.description))
        out.append("  %d bps, preamble %d, sync %d, length %d, address %d, CRC %d bytes, "
                   "whitening %s, setup %.0f us (overhead %d bytes + 2-byte fragment header)"
                   % (phy.bitrate_bps, phy.preamble_bytes, phy.sync_bytes, phy.length_bytes,
                      phy.address_bytes, phy.crc_bytes, "on" if phy.whitening else "off",
                      phy.setup_us, phy.overhead_bytes))
        out.append("  %7s %8s %11s %12s" % ("payload", "fragment", "on-air B", "airtime us"))
        for row in tables[phy.name]:
            out.append("  %7d %8d %11d %12.1f" % (row["payload_len"], row["fragment_len"],
                                                 row["frame_bytes"], row["airtime_us"]))
        b = budgets[phy.name]
        out.append("  Zone budget: payload %d B, %d repeat(s) x %d band(s) = %d TX per fragment"
                   % (b.payload_len, b.tx_repeats, b.bands, b.tx_per_fragment))
        out.append("    airtime per TX            %10.1f us" % b.airtime_us)
        out.append("    radio time per fragment   %10.1f us" % b.radio_time_per_fragment_us)
        out.append("    mean repeat gap           %10.1f us" % b.repeat_gap_mean_us)
        out.append("    TX queue residence        %10.1f us" % b.queue_residence_us)
        out.append("    max fragments/s (radio)   %10.2f" % b.max_fps_radio)
        out.append("    max fragments/s (queue 8) %10.2f" % b.max_fps_queue)
        out.append("    max fragments/s           %10.2f" % b.max_fps)
        out.append("    at %.2f fragments/s: channel duty %.2f %%, radio duty %.2f %%"
                   % (b.offered_fps, b.channel_duty * 100, b.radio_duty * 100))
        if b.duty_limit is not None:
            out.append("    max fragments/s under %.3g %% duty limit: %s"
                       % (b.duty_limit * 100, _fmt_rate(b.max_fps_duty)))
        for w in b.warnings:
            out.append("    WARNING: " + w)
        out.append("")
    if show_fcc:
        out.append(FCC_NOTE.rstrip())
    return "\n".join(out).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="NOVA-LINK airtime table and zone budget.")
    ap.add_argument("--phy", default=DEFAULT_PHY, choices=sorted(PHYS) + ["all"],
                    help="PHY preset (default %s)" % DEFAULT_PHY)
    g = ap.add_argument_group("PHY overrides (applied to every selected PHY)")
    g.add_argument("--bitrate", type=int, metavar="BPS")
    g.add_argument("--preamble", type=int, metavar="BYTES")
    g.add_argument("--sync", type=int, metavar="BYTES")
    g.add_argument("--length-bytes", type=int, metavar="BYTES")
    g.add_argument("--address", type=int, metavar="BYTES")
    g.add_argument("--crc", type=int, metavar="BYTES")
    g.add_argument("--whitening", choices=("on", "off"))
    g.add_argument("--setup-us", type=float, metavar="US", help="fixed per-packet cost")
    t = ap.add_argument_group("table")
    t.add_argument("--step", type=int, default=1, help="payload size step (default 1)")
    z = ap.add_argument_group("zone budget (defaults from nl_radio_params_default)")
    z.add_argument("--payload", type=int, default=MAX_PAYLOAD, help="payload bytes (default 100)")
    z.add_argument("--repeats", type=int, default=_DEFAULTS.tx_repeats,
                   help="tx_repeats (default %d); zone 0 uses mgmt_repeats, default %d"
                        % (_DEFAULTS.tx_repeats, _DEFAULTS.mgmt_repeats))
    z.add_argument("--dual", action="store_true", help="dual-band zone: every repeat is sent twice")
    z.add_argument("--interval-us", type=int, default=_DEFAULTS.repeat_interval_us)
    z.add_argument("--jitter-us", type=int, default=_DEFAULTS.repeat_jitter_us)
    z.add_argument("--dwell-us", type=int, default=_DEFAULTS.dwell_us)
    z.add_argument("--turnaround-us", type=float, default=0.0,
                   help="extra radio time per TX (RX/TX switching), default 0")
    z.add_argument("--duty-limit", type=float, metavar="FRACTION",
                   help="per-channel duty-cycle limit, e.g. 0.01 for 1 %%")
    z.add_argument("--rate", type=float, metavar="FPS",
                   help="offered fragments/s for the duty figures (default: the maximum)")
    ap.add_argument("--fcc", action="store_true", help="print the FCC Part 15 note")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    if args.step < 1:
        ap.error("--step must be >= 1")
    if not 0 <= args.payload <= MAX_PAYLOAD:
        ap.error("--payload must be 0..%d" % MAX_PAYLOAD)
    if args.repeats < 1:
        ap.error("--repeats must be >= 1")
    if args.duty_limit is not None and not 0 < args.duty_limit <= 1:
        ap.error("--duty-limit is a fraction in (0, 1]")

    names = sorted(PHYS) if args.phy == "all" else [args.phy]
    overrides = dict(bitrate_bps=args.bitrate, preamble_bytes=args.preamble,
                     sync_bytes=args.sync, length_bytes=args.length_bytes,
                     address_bytes=args.address, crc_bytes=args.crc, setup_us=args.setup_us,
                     whitening=None if args.whitening is None else args.whitening == "on")
    phys = [PHYS[n].with_overrides(**overrides) for n in names]
    for phy in phys:
        if phy.bitrate_bps <= 0:
            ap.error("--bitrate must be positive")

    payloads = list(range(0, MAX_PAYLOAD + 1, args.step))
    if payloads[-1] != MAX_PAYLOAD:
        payloads.append(MAX_PAYLOAD)
    tables = {p.name: airtime_table(p, payloads) for p in phys}
    budgets = {p.name: zone_budget(p, payload_len=args.payload, tx_repeats=args.repeats,
                                   bands=2 if args.dual else 1,
                                   repeat_interval_us=args.interval_us,
                                   repeat_jitter_us=args.jitter_us, dwell_us=args.dwell_us,
                                   turnaround_us=args.turnaround_us, duty_limit=args.duty_limit,
                                   offered_fps=args.rate)
               for p in phys}

    if args.json:
        doc = {"phys": [dict(vars(p), overhead_bytes=p.overhead_bytes,
                             table=tables[p.name], budget=budgets[p.name].to_dict())
                        for p in phys]}
        if args.fcc:
            doc["fcc_note"] = FCC_NOTE
        json.dump(doc, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_text(phys, tables, budgets, args.fcc))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
