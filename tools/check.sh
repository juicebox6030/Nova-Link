#!/bin/sh
# Local pre-push gate. The project deliberately has no hosted CI: run this and
# push only when it ends with "ALL CHECKS PASSED".
#
# Usage: tools/check.sh [--quick]
#   --quick   one gcc build with sanitizers and security on, plus formatting.
# Optional tools are skipped with a notice when missing: clang, valgrind,
# cppcheck, doxygen, arm-none-eabi-gcc, qemu-system-arm.
# Environment: JOBS (default: nproc), SEEDS (field-sim seeds, default 8),
# BENCH=1 to also print Cortex-M4 secure seal/open instruction counts.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
out="$root/build/check"
jobs=${JOBS:-$(nproc 2>/dev/null || echo 2)}
seeds=${SEEDS:-8}
quick=0
[ "${1:-}" = "--quick" ] && quick=1
skipped=""

step() { printf '\n=== %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
skip() { echo "SKIP: $1"; skipped="$skipped\n  $1"; }

# name cc build_type sanitizers security
config() {
    dir="$out/$1"
    step "build $1 ($2, $3, sanitizers=$4, security=$5)"
    cmake -S "$root" -B "$dir" -DCMAKE_C_COMPILER="$2" -DCMAKE_BUILD_TYPE="$3" \
        -DNOVA_ENABLE_SANITIZERS="$4" -DNOVA_SECURITY="$5" >/dev/null
    cmake --build "$dir" --parallel "$jobs"
    ctest --test-dir "$dir" --output-on-failure --parallel "$jobs"
}

step "whitespace (working tree and staged changes)"
git -C "$root" diff --check
git -C "$root" diff --cached --check

config gcc-asan-secure gcc Debug ON ON
if [ "$quick" = 1 ]; then
    printf '\nQUICK CHECKS PASSED (run without --quick before pushing)\n'
    exit 0
fi
config gcc-release gcc Release OFF OFF
config gcc-release-secure gcc Release OFF ON
if have clang; then
    config clang-release-secure clang Release OFF ON
    config clang-asan clang Debug ON OFF
else
    skip "clang builds"
fi

step "installed SDK consumer"
rel="$out/gcc-release-secure"
cmake --install "$rel" --prefix "$rel/sdk" >/dev/null
cmake -S "$root/tests/consumer" -B "$rel/consumer" -DCMAKE_PREFIX_PATH="$rel/sdk" >/dev/null
cmake --build "$rel/consumer"
"$rel/consumer/consumer"

step "standalone extended prototype (UBSan traps)"
cmake -S "$root/experimental/extended" -B "$out/extended" -DCMAKE_BUILD_TYPE=Debug -DNL_UBSAN=ON >/dev/null
cmake --build "$out/extended" --parallel "$jobs"
ctest --test-dir "$out/extended" --output-on-failure --parallel "$jobs"
(cd "$root/experimental/extended" && python3 -m unittest discover -s tools/tests -t tools)

step "field simulation, $seeds seeds, with and without security"
seed=1
while [ "$seed" -le "$seeds" ]; do
    for build in gcc-release gcc-release-secure; do
        "$out/$build/nova-field-sim" "$seed" >"$out/field-$build-$seed.log" ||
            { cat "$out/field-$build-$seed.log"; echo "field sim failed: $build seed $seed" >&2; exit 1; }
    done
    seed=$((seed + 1))
done
echo "field simulation passed for seeds 1..$seeds"

if have valgrind; then
    step "valgrind memcheck (release + security test binaries)"
    for test in "$rel"/test_*; do
        [ -x "$test" ] || continue
        valgrind -q --error-exitcode=1 --leak-check=full "$test" >/dev/null
        echo "clean: $(basename "$test")"
    done
    valgrind -q --error-exitcode=1 "$rel/nova-field-sim" 7 20000 >/dev/null
    echo "clean: nova-field-sim"
else
    skip "valgrind"
fi

if have cppcheck; then
    step "cppcheck"
    cppcheck --quiet --error-exitcode=1 --std=c99 --enable=warning,portability,performance \
        --inline-suppr -DNOVA_SECURITY=1 -I"$root/include" "$root/src"
else
    skip "cppcheck"
fi

step "gcc -fanalyzer"
for src in "$root"/src/*.c; do
    gcc -std=c99 -fanalyzer -Werror -DNOVA_SECURITY=1 -I"$root/include" -c "$src" -o /dev/null
done
echo "analyzer clean"

if have doxygen; then
    step "API docs (warnings are errors)"
    cmake -S "$root" -B "$out/docs" -DNOVA_BUILD_TESTS=OFF -DNOVA_BUILD_TOOLS=OFF >/dev/null
    cmake --build "$out/docs" --target docs docs-extended
else
    skip "doxygen"
fi

if have arm-none-eabi-gcc; then
    step "embedded footprint budgets"
    "$root/tools/embedded_footprint.sh" "$out/footprint"
    if [ "${BENCH:-0}" = 1 ]; then
        if have qemu-system-arm; then "$root/tools/embedded_bench.sh" "$out/bench"; else skip "qemu bench"; fi
    fi
else
    skip "embedded footprint (arm-none-eabi-gcc)"
fi

[ -z "$skipped" ] || printf '\nSkipped (install to cover):%b\n' "$skipped"
printf '\nALL CHECKS PASSED\n'
