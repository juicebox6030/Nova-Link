"""Dimensional/golden checks for explicit offline RF budget assumptions."""
import json
import math
import subprocess
import sys


def run(*args, code=0):
    result = subprocess.run([sys.executable, sys.argv[1], *args], capture_output=True, check=False)
    if result.returncode != code:
        raise AssertionError((args, result.returncode, result.stderr.decode()))
    assert b"Traceback" not in result.stderr
    return json.loads(result.stdout) if result.stdout else None


base = ("--bitrate", "50000", "--overhead-bytes", "11", "--slot-us", "1000", "--fixed-us", "200")
budget = run(*base)["budget"]
assert budget["fragment_bytes"] == 102
assert budget["primary_airtime_us"] == 18080
assert budget["primary_required_us"] == 18280
assert budget["primary_fits"] is False
assert budget["delivery_bound_without_loss_us"] is None
run(*base, "--require-fit", code=2)

fast = ("--bitrate", "2000000", "--overhead-bytes", "9", "--slot-us", "644", "--fixed-us", "200")
budget = run(*fast, "--zones", "4", "--metadata-slot", "--host-us", "250", "--stream-hz", "250", "--require-fit")["budget"]
assert budget["primary_airtime_us"] == 444
assert budget["primary_fits"] is True
assert budget["round_us"] == 3220
assert budget["delivery_bound_without_loss_us"] == 4114
assert math.isclose(budget["zone_service_hz"], 1_000_000 / 3220)
assert math.isclose(budget["stream_load"], 0.805)
assert budget["stream_rate_has_headroom"] is True
assert budget["sequence_half_range_us"] == 512000
assert budget["sequence_wrap_us"] == 1024000
overloaded = run(*fast, "--zones", "4", "--metadata-slot", "--stream-hz", "1000", "--require-fit", code=2)["budget"]
assert overloaded["primary_fits"] is True
assert math.isclose(overloaded["stream_load"], 3.22)
assert overloaded["stream_rate_has_headroom"] is False
assert overloaded["delivery_bound_without_loss_us"] is None
assert overloaded["sequence_half_range_us"] == 128000
# At exactly the service rate there is no capacity headroom under this contract.
run(*fast, "--slot-us", "1000", "--stream-hz", "1000", "--require-fit", code=2)
queued = run(*fast, "--queued-ahead", "7")["budget"]
assert queued["delivery_bound_without_loss_us"] == 8 * 644 + 644
burst_too_long = run(*fast, "--slot-us", "1000", "--fixed-us", "1056", "--burst-extra-us", "1000",
                     "--require-fit", code=2)["budget"]
assert burst_too_long["primary_required_us"] == 1500
assert burst_too_long["available_data_window_us"] == 2000
assert burst_too_long["initial_data_window_us"] == 1000
assert burst_too_long["primary_fits"] is False
assert burst_too_long["delivery_bound_without_loss_us"] is None
# Completion exactly at the original deadline cannot announce an extension.
run(*fast, "--burst-extra-us", "644", "--require-fit", code=2)
burst_ok = run(*fast, "--slot-us", "1000", "--burst-extra-us", "1000",
               "--stream-hz", "250", "--require-fit")["budget"]
assert burst_ok["primary_fits"] is True
assert burst_ok["round_us"] == 2000 and burst_ok["zone_service_hz"] == 500
assert burst_ok["delivery_bound_without_loss_us"] == 2644

dual = run("--bitrate", "200000", "--overhead-bytes", "11", "--slot-us", "7000", "--fixed-us", "200",
           "--secondary-bitrate", "1000000", "--secondary-overhead-bytes", "8", "--band-switch-us", "500")["budget"]
assert math.isclose(dual["dual_band_required_us"], 6800)
assert dual["dual_band_fits"] is True
dual_no_fit = run("--bitrate", "200000", "--overhead-bytes", "11", "--slot-us", "5000", "--fixed-us", "200",
                  "--secondary-bitrate", "1000000", "--secondary-overhead-bytes", "8", "--band-switch-us", "500",
                  "--require-fit", code=2)["budget"]
assert dual_no_fit["primary_fits"] is True
assert dual_no_fit["delivery_bound_without_loss_us"] is not None
assert dual_no_fit["dual_band_fits"] is False
assert dual_no_fit["dual_band_delivery_bound_without_loss_us"] is None
dual_burst = run(*fast, "--slot-us", "1000", "--burst-extra-us", "1000",
                 "--secondary-bitrate", "2000000", "--secondary-overhead-bytes", "9",
                 "--require-fit", code=2)["budget"]
assert dual_burst["primary_fits"] is True
assert dual_burst["dual_band_required_us"] == 1288
assert dual_burst["dual_band_fits"] is False
assert dual_burst["dual_band_delivery_bound_without_loss_us"] is None
dual_overloaded = run("--bitrate", "200000", "--overhead-bytes", "11", "--slot-us", "7000", "--fixed-us", "200",
                      "--secondary-bitrate", "1000000", "--secondary-overhead-bytes", "8", "--band-switch-us", "500",
                      "--stream-hz", "1000", "--require-fit", code=2)["budget"]
assert dual_overloaded["dual_band_fits"] is True
assert dual_overloaded["delivery_bound_without_loss_us"] is None
assert dual_overloaded["dual_band_delivery_bound_without_loss_us"] is None

for flag, value in (("--bitrate", "0"), ("--bitrate", "nan"), ("--slot-us", "inf"),
                    ("--payload-bytes", "101"), ("--zones", "0"), ("--zones", "8"),
                    ("--queued-ahead", "8"), ("--fixed-us", "-1"), ("--burst-extra-us", "1001"),
                    ("--secondary-bitrate", "1000000")):
    run(*base, flag, value, code=2)
for flag, value in (("--slot-us", "0"), ("--slot-us", "0.5"), ("--slot-us", "4294967296"),
                    ("--burst-extra-us", "0.5")):
    run(*base, flag, value, code=2)
run(*base, "--slot-us", "4294967295", "--burst-extra-us", "1", code=2)
assert run(*base, "--slot-us", "4294967295")["budget"]["primary_fits"] is True
for flag, value in (("--bitrate", "5e-324"), ("--slot-us", "1e308"),
                    ("--overhead-bytes", "9" * 400), ("--stream-hz", "5e-324")):
    run(*base, flag, value, "--zones", "7", code=2)
run(*fast, "--secondary-bitrate", "2000000", "--secondary-overhead-bytes", "9",
    "--band-switches", "9" * 400, "--band-switch-us", "1", code=2)
print("RF budgets: golden airtime, backlog, dual-band assumptions and fit checks passed")
