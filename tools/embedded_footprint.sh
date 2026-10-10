#!/bin/sh
# Report flash/RAM-free code size and worst stack frames of the core library
# for bare-metal ARM targets, without and with NOVA_SECURITY, and enforce the
# budgets below. Usage: tools/embedded_footprint.sh [out-dir]
# Budgets (bytes, override via environment): MAX_STACK_FRAME per function,
# MAX_TEXT_CORE / MAX_TEXT_SECURE for the whole library on each core.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
out=${1:-"$root/build/footprint"}
cc=${ARM_CC:-arm-none-eabi-gcc}
max_frame=${MAX_STACK_FRAME:-256}
max_core=${MAX_TEXT_CORE:-6500}
max_secure=${MAX_TEXT_SECURE:-9000}
command -v "$cc" >/dev/null || { echo "$cc not found" >&2; exit 2; }
status=0
for cpu in cortex-m0plus cortex-m4; do
    dir="$out/$cpu"
    mkdir -p "$dir"
    for src in "$root"/src/*.c; do
        "$cc" -mcpu="$cpu" -mthumb -Os -std=c99 -Wall -Wextra -Werror -DNOVA_SECURITY=1 \
            -ffunction-sections -fdata-sections -fstack-usage \
            -I"$root/include" -c "$src" -o "$dir/$(basename "$src" .c).o"
    done
    core=$(ls "$dir"/*.o | grep -v -e '/secure\.o$' -e '/dmx\.o$')
    # shellcheck disable=SC2086
    core_text=$(arm-none-eabi-size -t $core | tail -1 | awk '{print $1}')
    secure_text=$((core_text + $(arm-none-eabi-size "$dir/secure.o" | tail -1 | awk '{print $1}')))
    echo "== $cpu (-Os): core text=$core_text  with security text=$secure_text  (data=bss=0)"
    [ "$core_text" -le "$max_core" ] || { echo "core text over budget $max_core" >&2; status=1; }
    [ "$secure_text" -le "$max_secure" ] || { echo "secure text over budget $max_secure" >&2; status=1; }
    echo "largest stack frames (bytes):"
    cat "$dir"/*.su | sort -t"$(printf '\t')" -k2 -n -r | head -8 | sed 's/^.*://'
    over=$(cat "$dir"/*.su | awk -F'\t' -v max="$max_frame" '$2 + 0 > max')
    [ -z "$over" ] || { echo "stack frames over $max_frame:" >&2; echo "$over" >&2; status=1; }
done
exit $status
