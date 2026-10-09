#!/usr/bin/env python3
"""Offline airtime budget calculator. Inputs are assumptions, never measured PHY data."""
import argparse
import json
import math
import sys


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return number


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be finite and nonnegative")
    return number


def natural(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return number


def calculate(args):
    fragment_bytes = args.payload_bytes + 2
    airtime = (fragment_bytes + args.overhead_bytes) * 8_000_000 / args.bitrate
    required = airtime + args.fixed_us
    available = args.slot_us + args.burst_extra_us
    # One TX fragment per data-zone window, no loss, common timing, and no catch-up delays.
    round_us = args.zones * available + (args.slot_us if args.metadata_slot else 0)
    service_hz = 1_000_000 / round_us
    # A continuous input stream requires positive service headroom for this bound.
    rate_fits = args.stream_hz is None or args.stream_hz < service_hz
    # The first accepted fragment announces BURST. It must finish strictly
    # before the original window closes; this one-fragment model has no earlier
    # short announcement. Conservatively apply the same rule to both copies.
    def fits_initial_window(cost):
        return cost < args.slot_us if args.burst_extra_us else cost <= args.slot_us

    primary_fits = fits_initial_window(required)
    budget = {
        "fragment_bytes": fragment_bytes,
        "primary_airtime_us": airtime,
        "primary_required_us": required,
        "available_data_window_us": available,
        "initial_data_window_us": args.slot_us,
        "primary_fits": primary_fits,
        "round_us": round_us,
        "zone_service_hz": service_hz,
        "delivery_bound_without_loss_us":
            (args.queued_ahead + 1) * round_us + required + args.host_us if primary_fits and rate_fits else None,
    }
    fits = primary_fits
    if args.secondary_bitrate is not None:
        secondary_airtime = (fragment_bytes + args.secondary_overhead_bytes) * 8_000_000 / args.secondary_bitrate
        dual_required = required + secondary_airtime + args.fixed_us + args.band_switches * args.band_switch_us
        fits = fits_initial_window(dual_required)
        budget.update({
            "secondary_airtime_us": secondary_airtime,
            "dual_band_required_us": dual_required,
            "dual_band_fits": fits,
            "dual_band_delivery_bound_without_loss_us":
                (args.queued_ahead + 1) * round_us + dual_required + args.host_us if fits and rate_fits else None,
        })
    if args.stream_hz is not None:
        budget["stream_load"] = args.stream_hz / service_hz
        budget["stream_rate_has_headroom"] = rate_fits
        budget["sequence_half_range_us"] = 128_000_000 / args.stream_hz
        budget["sequence_wrap_us"] = 256_000_000 / args.stream_hz
    if any(value is not None and not math.isfinite(value) for value in budget.values()):
        raise OverflowError("assumptions produce a non-finite budget")
    return budget, fits and rate_fits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitrate", required=True, type=positive, help="assumed effective primary bits/second after FEC/spreading/line coding")
    parser.add_argument("--overhead-bytes", required=True, type=natural, help="assumed preamble/sync/length/CRC bytes")
    parser.add_argument("--slot-us", required=True, type=natural, help="configured integer base slot duration, 1..UINT32_MAX")
    parser.add_argument("--payload-bytes", default=100, type=natural)
    parser.add_argument("--zones", default=1, type=natural, help="active data zones, 1..7")
    parser.add_argument("--metadata-slot", action="store_true", help="assume metadata in every round")
    parser.add_argument("--burst-extra-us", default=0, type=natural, help="bounded extension lengthens rounds; copies must still finish before the base deadline")
    parser.add_argument("--fixed-us", default=0.0, type=nonnegative, help="assumed setup/turnaround plus receiver processing and clock margin per copy")
    parser.add_argument("--host-us", default=0.0, type=nonnegative, help="assumed total host/transport/dispatch overhead")
    parser.add_argument("--queued-ahead", default=0, type=natural, help="older TX fragments in the same zone, 0..7")
    parser.add_argument("--stream-hz", type=positive, help="assumed continuous input rate for the sole stream in a zone; also gives sequence horizons")
    parser.add_argument("--secondary-bitrate", type=positive, help="assumed effective bits/second for a second copy on one time-shared transceiver")
    parser.add_argument("--secondary-overhead-bytes", type=natural)
    parser.add_argument("--band-switch-us", default=0.0, type=nonnegative, help="assumed cost per band switch")
    parser.add_argument("--band-switches", default=2, type=natural, help="assumed switches per dual-band fragment, including return")
    parser.add_argument("--require-fit", action="store_true", help="exit 2 if transmissions cannot fit or the input rate leaves no service headroom")
    args = parser.parse_args()
    if args.payload_bytes > 100 or not 1 <= args.zones <= 7 or args.queued_ahead > 7:
        parser.error("payload must be 0..100, zones 1..7, and queued-ahead 0..7")
    if not 1 <= args.slot_us <= 0xFFFFFFFF or args.burst_extra_us > args.slot_us or args.slot_us + args.burst_extra_us > 0xFFFFFFFF:
        parser.error("slot-us must be 1..UINT32_MAX; burst-extra-us must not exceed slot-us or overflow their uint32 sum")
    if (args.secondary_bitrate is None) != (args.secondary_overhead_bytes is None):
        parser.error("secondary-bitrate and secondary-overhead-bytes must be supplied together")
    try:
        budget, fits = calculate(args)
    except OverflowError:
        parser.error("assumptions produce a non-finite budget")
    print(json.dumps({
        "scope": "offline sender budget; no measured PHY data, receiver rendezvous, synchronization, collisions, retries or regulatory validation",
        "assumptions": vars(args),
        "budget": budget,
    }, allow_nan=False, indent=2))
    if args.require_fit and not fits:
        print("Assumed transmissions miss the base-window/announcement deadline or the input rate leaves no service headroom.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
