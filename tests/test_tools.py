"""Exercise the offline CLI as a consumer, including its exit codes and JSON."""
import json
import pathlib
import subprocess
import sys
import tempfile


def run(*args, data=None, success=True):
    result = subprocess.run([sys.argv[1], *args], input=data, capture_output=True, check=False)
    if (result.returncode == 0) != success:
        raise AssertionError((args, result.returncode, result.stderr.decode()))
    return result


golden = bytes.fromhex("aa0603affe00aaff")
decoded = json.loads(run("frame", golden.hex()).stdout)
assert decoded == {
    "command": 3,
    "fragment": {"origin": 5, "zone": 3, "sequence": 254, "flags": 3,
                 "burst": True, "management_listen": True, "payload_size": 3,
                 "payload_hex": "00aaff"},
}
assert json.loads(run("fragment", "AF FE 00 AA FF").stdout) == decoded["fragment"]
assert json.loads(run("frame", "aa0102").stdout) == {"command": 2}
for invalid in ("", "a", "zz", "aa", "aa0002", "aa0202", "aa01ff", "00" * 106):
    run("frame", invalid, success=False)
run(success=False)
run("frame", "aa0102", "extra", success=False)
run("fragment", "00" * 103, success=False)
stream = b"\x00\xff" + golden + bytes.fromhex("aa0102") + golden
lines = run("stream", "-", data=stream).stdout.splitlines()
assert [json.loads(line) for line in lines] == [decoded, {"command": 2}, decoded]
run("stream", "-", data=b"", success=False)
run("stream", "-", data=golden[:-1], success=False)
run("stream", "-", data=bytes.fromhex("aa00") + golden, success=False)
with tempfile.TemporaryDirectory() as temp:
    fixture = pathlib.Path(temp) / "fixture.bin"
    fixture.write_bytes(stream)
    assert run("stream", str(fixture)).stdout.splitlines() == lines
    run("stream", str(fixture.parent / "missing.bin"), success=False)
print("offline tools: golden JSON, stream input and malformed input checks passed")
