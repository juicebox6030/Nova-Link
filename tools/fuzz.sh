#!/bin/sh
# Build the libFuzzer harnesses (clang, NOVA_SECURITY=ON) and fuzz each one,
# growing a persistent corpus. Exits 1 if any harness has saved crashes.
#
# Usage: tools/fuzz.sh [--admit-only] [seconds-per-harness] [harness...]
#   default: 300 seconds, all of transport radio secure.
# Environment:
#   FUZZ_STATE  corpus/crash/log directory (default build/fuzz-state); keep it
#               across runs so coverage accumulates.
#   FORKS       parallel worker processes per harness (default nproc / 2).
#   RSS_MB      per-worker memory cap (default 2048).
#   FUZZ_RESERVE_CPUS  CPUs left for other work (default 1).
#   FUZZ_RESERVE_MB    available memory left for other work (default 1024).
# --admit-only prints the current admission decision without building or running.
# Exit 75 means retry later or use an existing compatible CPU-only build host.
# Layout: $FUZZ_STATE/<harness>/{corpus,crashes}/, per-worker fuzz-N.log and last.log.
# Reproduce a crash: build/fuzz/tests/fuzz/fuzz_<harness> <crash-file>. Once fixed, copy
# the file into tests/fuzz/seeds/<harness>/ so ctest replays it forever.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
build="$root/build/fuzz"
state=${FUZZ_STATE:-"$root/build/fuzz-state"}
admit_only=0
if [ "${1:-}" = --admit-only ]; then
    admit_only=1
    shift
fi
seconds=${1:-300}
[ $# -gt 0 ] && shift
harnesses=${*:-transport radio secure}
cpus=$(nproc 2>/dev/null || echo 2)
forks=${FORKS:-$(( cpus > 1 ? cpus / 2 : 1 ))}
rss=${RSS_MB:-2048}
reserve_cpus=${FUZZ_RESERVE_CPUS:-1}
reserve_mb=${FUZZ_RESERVE_MB:-1024}

integer() {
    case $2 in ''|*[!0-9]*) echo "invalid $1: expected a nonnegative integer" >&2; exit 2 ;; esac
    [ "$2" -le 1048576 ] 2>/dev/null || { echo "$1 is too large" >&2; exit 2; }
    expr "$2" + 0 || true
}
seconds=$(integer seconds "$seconds")
forks=$(integer FORKS "$forks")
rss=$(integer RSS_MB "$rss")
reserve_cpus=$(integer FUZZ_RESERVE_CPUS "$reserve_cpus")
reserve_mb=$(integer FUZZ_RESERVE_MB "$reserve_mb")
[ "$seconds" -gt 0 ] && [ "$forks" -gt 0 ] && [ "$rss" -gt 0 ] || {
    echo "seconds, FORKS and RSS_MB must be positive" >&2; exit 2;
}
for name in $harnesses; do
    case $name in transport|radio|secure) ;; *) echo "unknown harness: $name" >&2; exit 2 ;; esac
done

# Serialize this user's future fuzz rounds on a host, including their builds.
# Existing service-owned rounds are never signalled or moved.
if [ "$admit_only" = 0 ]; then
    mkdir -p "$HOME/.cache"
    exec 9>"$HOME/.cache/nova-link-fuzz.lock"
    flock -n 9 || { echo "DEFER: another fuzz round owns this host" >&2; exit 75; }
fi
load=$(awk '{ if ($1 !~ /^[0-9]+([.][0-9]+)?$/) exit 1; print $1; ok=1; exit } END { if (!ok) exit 1 }' /proc/loadavg) || {
    echo "DEFER: cannot measure host load" >&2; exit 75;
}
available_mb=$(awk '/^MemAvailable:/ { print int($2/1024); ok=1; exit } END { if (!ok) exit 1 }' /proc/meminfo) || {
    echo "DEFER: cannot measure available memory" >&2; exit 75;
}
slots=$(awk -v cpus="$cpus" -v reserve="$reserve_cpus" -v host_load="$load" \
    'BEGIN { busy=int(host_load); if (host_load>busy) busy++; print cpus-reserve-busy }')
memory_slots=$(( (available_mb - reserve_mb) / rss ))
if [ "$slots" -le 0 ] || [ "$memory_slots" -le 0 ]; then
    echo "DEFER: cpus=$cpus load=$load reserve_cpus=$reserve_cpus available_mb=$available_mb reserve_mb=$reserve_mb rss_mb=$rss" >&2
    exit 75
fi
[ "$forks" -le "$slots" ] || forks=$slots
[ "$forks" -le "$memory_slots" ] || forks=$memory_slots
echo "ADMIT: workers=$forks build_jobs=$forks cpus=$cpus load=$load available_mb=$available_mb"
[ "$admit_only" = 0 ] || exit 0

cmake -S "$root" -B "$build" -DCMAKE_C_COMPILER=clang -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DNOVA_FUZZ=ON -DNOVA_SECURITY=ON -DNOVA_BUILD_TESTS=OFF -DNOVA_BUILD_TOOLS=OFF \
    -DNOVA_BUILD_EXTENDED=OFF >/dev/null
cmake --build "$build" --parallel "$forks" >/dev/null

failed=0
for name in $harnesses; do
    dir="$state/$name"
    mkdir -p "$dir/corpus" "$dir/crashes"
    echo "=== fuzz_$name: ${seconds}s x $forks workers"
    rm -f "$dir"/fuzz-*.log
    # Independent workers share the corpus directory; a crashing worker stops
    # but the others keep fuzzing. (-fork mode segfaults in clang 22's libFuzzer.)
    (cd "$dir" && "$build/tests/fuzz/fuzz_$name" "$dir/corpus" "$root/tests/fuzz/seeds/$name" \
        -dict="$root/tests/fuzz/nova.dict" -max_total_time="$seconds" \
        -jobs="$forks" -workers="$forks" -rss_limit_mb="$rss" -timeout=10 -max_len=4096 \
        -artifact_prefix="$dir/crashes/" -print_final_stats=1 >"$dir/last.log" 2>&1) || true
    cat "$dir"/fuzz-*.log >>"$dir/last.log" 2>/dev/null || true
    grep -h 'DONE' "$dir"/fuzz-*.log 2>/dev/null | sort -t: -k2 -n | tail -1 || true
    echo "corpus: $(ls "$dir/corpus" | wc -l) inputs"
    crashes=$(ls "$dir/crashes" | wc -l)
    if [ "$crashes" -gt 0 ]; then
        echo "CRASHES: $crashes in $dir/crashes" >&2
        failed=1
    fi
done
[ "$failed" = 0 ] && echo "FUZZ CLEAN" || echo "FUZZ FOUND CRASHES"
exit $failed
