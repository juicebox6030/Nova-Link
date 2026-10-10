#!/bin/sh
# Summarise the long-term jobs installed by tools/longterm/install.sh.
lt=${NOVA_LT:-"$HOME/nova-longterm"}
echo "== last results"
cat "$lt"/status/* 2>/dev/null || echo "(none yet)"
echo "== fuzzing"
for dir in "$lt"/fuzz/*/; do
    [ -d "$dir" ] || continue
    printf '%-10s corpus %5s  crashes %s\n' "$(basename "$dir")" \
        "$(ls "$dir/corpus" | wc -l)" "$(ls "$dir/crashes" | wc -l)"
done
echo "== soak"
tail -3 "$lt/soak/history.log" 2>/dev/null || echo "(none yet)"
ls "$lt/soak/failures" 2>/dev/null | sed 's/^/failure: /'
echo "== timers"
systemctl --user list-timers 'nova-*' --no-pager 2>/dev/null | head -4
systemctl --user is-active nova-fuzz.service 2>/dev/null | sed 's/^/nova-fuzz: /'
