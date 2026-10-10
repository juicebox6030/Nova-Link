#!/bin/sh
# Instructions per secure seal/open on Cortex-M4 (QEMU mps2-an386, -icount).
# Usage: tools/embedded_bench.sh [out-dir]   Needs arm-none-eabi-gcc + newlib
# and qemu-system-arm. Real cycles are roughly 1.2-1.5x the instruction count
# (loads and taken branches cost 2+ cycles; flash wait states add more).
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
out=${1:-"$root/build/embedded_bench"}
cc=${ARM_CC:-arm-none-eabi-gcc}
opt=${BENCH_OPT:--Os}
for tool in "$cc" qemu-system-arm; do
    command -v "$tool" >/dev/null || { echo "$tool not found" >&2; exit 2; }
done
mkdir -p "$out"
"$cc" -mcpu=cortex-m4 -mthumb "$opt" -std=c99 -Wall -Wextra -Werror -DNOVA_SECURITY=1 \
    -ffunction-sections -fdata-sections -I"$root/include" \
    "$root/tools/embedded_bench/bench.c" "$root/src/secure.c" "$root/src/fragment.c" \
    "$root/src/status.c" "$root/src/stream.c" "$root/src/queue.c" "$root/src/scheduler.c" \
    "$root/src/radio.c" "$root/src/transport.c" \
    --specs=rdimon.specs -nostartfiles -Wl,--gc-sections -T "$root/tools/embedded_bench/mps2.ld" \
    -o "$out/bench.elf"
echo "== cortex-m4 ($opt), instructions per call"
timeout 300 qemu-system-arm -M mps2-an386 -nographic -monitor none -serial none \
    -semihosting-config enable=on,target=native -icount shift=0 -kernel "$out/bench.elf"
