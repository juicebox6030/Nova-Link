"""Run the real fuzz entry point against host measurements and a bounded build probe."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "tools").mkdir()
        (self.root / ".cache").mkdir()
        shutil.copy2(Path(__file__).resolve().parents[1] / "tools/fuzz.sh",
                     self.root / "tools/fuzz.sh")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.write_command("nproc", '#!/bin/sh\ncat "$NOVA_TEST_PROC/cpus"\n')
        self.write_command("awk", '#!/bin/sh\n'
                           'exec python3 "$NOVA_TEST_PROC/awk.py" "$@"\n')
        (self.root / "awk.py").write_text(
            "import os,sys\n"
            "args=[os.environ['NOVA_TEST_PROC']+'/'+a.rsplit('/',1)[-1] "
            "if a in ['/proc/loadavg','/proc/meminfo'] else a for a in sys.argv[1:]]\n"
            "os.execv(" + repr(shutil.which("awk")) + ", ['awk']+args)\n")
        self.write_command("cmake", '#!/bin/sh\n'
                           'echo "$*" >> "$NOVA_TEST_PROC/build.log"\n'
                           '[ "$1" != --build ] || exit 42\n')
        self.measurements()

    def write_command(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o755)

    def measurements(self, cpus=12, load="10.0", mb=32000):
        (self.root / "cpus").write_text(str(cpus))
        (self.root / "loadavg").write_text(f"{load} 0.0 0.0 1/1 1\n")
        (self.root / "meminfo").write_text(f"MemAvailable: {mb * 1024} kB\n")

    def run_fuzz(self, *args, **env):
        base = {k: v for k, v in os.environ.items() if not k.startswith(
            ("FUZZ_", "FORKS", "RSS_MB"))}
        base.update(HOME=str(self.root), PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                    NOVA_TEST_PROC=str(self.root), TMPDIR=str(self.root),
                    XDG_RUNTIME_DIR=str(self.root), FORKS="8", **env)
        return subprocess.run([str(self.root / "tools/fuzz.sh"), *args],
                              env=base, text=True, capture_output=True)

    def test_busy_gpu_caps_explicit_workers_and_build_without_writes(self):
        result = self.run_fuzz("--admit-only", "10", "radio")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("workers=1 build_jobs=1", result.stdout)
        self.assertFalse((self.root / "build").exists())
        self.assertFalse((self.root / "build.log").exists())

    def test_spare_vm_capacity(self):
        self.measurements(cpus=4, load="0.5", mb=7000)
        result = self.run_fuzz("--admit-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("workers=2 build_jobs=2", result.stdout)

    def test_saturated_host_defers_before_build(self):
        self.measurements(cpus=4, load="3.01")
        result = self.run_fuzz("1", "radio")
        self.assertEqual(result.returncode, 75, result.stderr)
        self.assertFalse((self.root / "build.log").exists())

    def test_memory_limits_workers(self):
        self.measurements(load="0.0", mb=3200)
        result = self.run_fuzz("--admit-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("workers=1", result.stdout)
        self.measurements(load="0.0", mb=1000)
        self.assertEqual(self.run_fuzz("--admit-only").returncode, 75)

    def test_bad_measurement_defers(self):
        (self.root / "meminfo").write_text("")
        self.assertEqual(self.run_fuzz("--admit-only").returncode, 75)
        self.measurements(load="unavailable")
        self.assertEqual(self.run_fuzz("--admit-only").returncode, 75)

    def test_build_uses_admitted_parallelism_and_propagates_failure(self):
        result = self.run_fuzz("1", "radio")
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertIn("--parallel 1", (self.root / "build.log").read_text())

    def test_existing_host_owner_defers(self):
        import fcntl
        lock = self.root / ".cache/nova-link-fuzz.lock"
        with lock.open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.run_fuzz("1", "radio").returncode, 75)
        self.assertFalse((self.root / "build.log").exists())

    def test_invalid_request_never_builds(self):
        for args, env in [(("0",), {}), (("1", "../radio"), {}),
                          (("1",), {"RSS_MB": "0"}),
                          (("1",), {"FUZZ_RESERVE_CPUS": "-1"})]:
            result = self.run_fuzz(*args, **env)
            self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse((self.root / "build.log").exists())

    def test_longterm_keeps_deferred_distinct_from_failure(self):
        wrapper = self.root / "tools/longterm/run.sh"
        wrapper.parent.mkdir()
        shutil.copy2(Path(__file__).resolve().parents[1] / "tools/longterm/run.sh",
                     wrapper)
        fuzz = self.root / "tools/fuzz.sh"
        state = self.root / "longterm"
        for code, status in [(75, "DEFER"), (1, "FAIL rc=1"), (0, "PASS")]:
            fuzz.write_text(f"#!/bin/sh\nexit {code}\n")
            result = subprocess.run([str(wrapper), "fuzz"], text=True,
                                    capture_output=True,
                                    env=dict(os.environ, NOVA_LT=str(state)))
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertIn(status, (state / "status/fuzz").read_text())


if __name__ == "__main__":
    unittest.main()
