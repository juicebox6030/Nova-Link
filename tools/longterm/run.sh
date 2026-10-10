#!/bin/sh
# Wrapper used by the systemd user units: run one long-term job, keep a dated
# log, and record its result in $NOVA_LT/status/<job>.
#
# Usage: tools/longterm/run.sh fuzz|nightly
#   fuzz     one tools/fuzz.sh round (FUZZ_SECONDS per harness, default 1200)
#   nightly  git pull --ff-only, full tools/check.sh, then tools/soak.sh
set -u
root=$(cd "$(dirname "$0")/../.." && pwd)
lt=${NOVA_LT:-"$HOME/nova-longterm"}
job=$1
mkdir -p "$lt/logs" "$lt/status"
log="$lt/logs/$job-$(date +%Y%m%d-%H%M%S).log"
export FUZZ_STATE="$lt/fuzz" SOAK_STATE="$lt/soak"

case $job in
fuzz)
    "$root/tools/fuzz.sh" "${FUZZ_SECONDS:-1200}" >"$log" 2>&1 ;;
nightly)
    {
        git -C "$root" pull --ff-only &&
            "$root/tools/check.sh" &&
            "$root/tools/soak.sh"
    } >"$log" 2>&1 ;;
*)
    echo "unknown job: $job" >&2
    exit 2 ;;
esac
rc=$?
result=PASS
[ "$rc" = 0 ] || result="FAIL rc=$rc"
echo "$(date -Is) $result $(git -C "$root" rev-parse --short HEAD) $log" | tee "$lt/status/$job"
# Keep two weeks of logs.
find "$lt/logs" -name '*.log' -mtime +14 -delete
exit "$rc"
