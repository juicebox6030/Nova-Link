#!/bin/sh
# Long field-simulation soak: run nova-field-sim over fresh seeds, without and
# with security, plus an ASan+UBSan build, until the time budget is spent. The
# next seed is persisted so successive soaks never repeat a seed.
#
# Usage: tools/soak.sh
# Environment:
#   SOAK_STATE    state directory (default build/soak-state)
#   SOAK_SECONDS  time budget (default 3600)
#   TICKS         ticks per release run (default 1000000; ASan runs use TICKS/10)
#   JOBS          parallel simulations (default nproc / 2)
# Layout: $SOAK_STATE/next-seed, failures/<build>-<seed>.log, history.log.
# Reproduce a failure: build/soak/<build>/nova-field-sim <seed> <ticks>.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
build="$root/build/soak"
state=${SOAK_STATE:-"$root/build/soak-state"}
seconds=${SOAK_SECONDS:-3600}
ticks=${TICKS:-1000000}
cpus=$(nproc 2>/dev/null || echo 2)
jobs=${JOBS:-$(( cpus > 1 ? cpus / 2 : 1 ))}
mkdir -p "$state/failures"

# name build_type sanitizers security
config() {
    cmake -S "$root" -B "$build/$1" -DCMAKE_C_COMPILER=gcc -DCMAKE_BUILD_TYPE="$2" \
        -DNOVA_ENABLE_SANITIZERS="$3" -DNOVA_SECURITY="$4" -DNOVA_BUILD_TESTS=OFF \
        -DNOVA_BUILD_EXTENDED=OFF >/dev/null
    cmake --build "$build/$1" --parallel "$cpus" --target nova-field-sim >/dev/null
}
config release Release OFF OFF
config release-secure Release OFF ON
config asan-secure Debug ON ON

# One seed through every build; prints "fail" lines for the summary.
run_seed() {
    for b in release release-secure asan-secure; do
        t=$ticks
        [ "$b" = asan-secure ] && t=$((ticks / 10))
        log="$state/failures/$b-$1.log"
        if "$build/$b/nova-field-sim" "$1" "$t" >"$log" 2>&1; then
            rm -f "$log"
        else
            echo "fail $b seed $1 ticks $t"
        fi
    done
}

seed=$(cat "$state/next-seed" 2>/dev/null || echo 1000)
first=$seed
start=$(date +%s)
failures=0
while [ $(( $(date +%s) - start )) -lt "$seconds" ]; do
    batch=$(mktemp)
    i=0
    while [ "$i" -lt "$jobs" ]; do
        (run_seed $((seed + i)) >>"$batch") &
        i=$((i + 1))
    done
    wait
    cat "$batch"
    failures=$((failures + $(grep -c '^fail' "$batch" || true)))
    rm -f "$batch"
    seed=$((seed + jobs))
    echo "$seed" >"$state/next-seed"
done
line="$(date -Is) seeds $first..$((seed - 1)) ticks $ticks failures $failures"
echo "$line" | tee -a "$state/history.log"
[ "$failures" = 0 ] && echo "SOAK CLEAN" || echo "SOAK FAILED (logs in $state/failures)"
[ "$failures" = 0 ]
