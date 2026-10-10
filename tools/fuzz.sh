#!/bin/sh
# Build the libFuzzer harnesses (clang, NOVA_SECURITY=ON) and fuzz each one,
# growing a persistent corpus. Exits 1 if any harness has saved crashes.
#
# Usage: tools/fuzz.sh [seconds-per-harness] [harness...]
#   default: 300 seconds, all of transport radio secure.
# Environment:
#   FUZZ_STATE  corpus/crash/log directory (default build/fuzz-state); keep it
#               across runs so coverage accumulates.
#   FORKS       parallel worker processes per harness (default nproc / 2).
#   RSS_MB      per-worker memory cap (default 2048).
# Layout: $FUZZ_STATE/<harness>/{corpus,crashes}/, per-worker fuzz-N.log and last.log.
# Reproduce a crash: build/fuzz/tests/fuzz/fuzz_<harness> <crash-file>. Once fixed, copy
# the file into tests/fuzz/seeds/<harness>/ so ctest replays it forever.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
build="$root/build/fuzz"
state=${FUZZ_STATE:-"$root/build/fuzz-state"}
seconds=${1:-300}
[ $# -gt 0 ] && shift
harnesses=${*:-transport radio secure}
cpus=$(nproc 2>/dev/null || echo 2)
forks=${FORKS:-$(( cpus > 1 ? cpus / 2 : 1 ))}
rss=${RSS_MB:-2048}

cmake -S "$root" -B "$build" -DCMAKE_C_COMPILER=clang -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DNOVA_FUZZ=ON -DNOVA_SECURITY=ON -DNOVA_BUILD_TESTS=OFF -DNOVA_BUILD_TOOLS=OFF \
    -DNOVA_BUILD_EXTENDED=OFF >/dev/null
cmake --build "$build" --parallel "$cpus" >/dev/null

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
