#!/bin/sh
# Install the long-term test jobs as systemd user units on a build machine:
#   nova-fuzz.service    continuous fuzzing, one tools/fuzz.sh round after another
#   nova-nightly.timer   03:17 daily: git pull, tools/check.sh, tools/soak.sh
# Results: tools/longterm/report.sh; logs in ~/nova-longterm/logs and the journal.
# Environment: FORKS (fuzz workers, default nproc*2/3), SOAK_SECONDS (default 7200).
set -eu
root=$(cd "$(dirname "$0")/../.." && pwd)
units="$HOME/.config/systemd/user"
cpus=$(nproc 2>/dev/null || echo 2)
forks=${FORKS:-$(( cpus * 2 / 3 > 0 ? cpus * 2 / 3 : 1 ))}
soak_jobs=$(( cpus - forks > 0 ? cpus - forks : 1 ))
mkdir -p "$units"

cat >"$units/nova-fuzz.service" <<EOF
[Unit]
Description=Nova-Link continuous libFuzzer

[Service]
Environment=FORKS=$forks
ExecStart=$root/tools/longterm/run.sh fuzz
Restart=always
RestartSec=30
Nice=10

[Install]
WantedBy=default.target
EOF

cat >"$units/nova-nightly.service" <<EOF
[Unit]
Description=Nova-Link nightly pull, full checks and field-sim soak

[Service]
Type=oneshot
Environment=JOBS=$soak_jobs SOAK_SECONDS=${SOAK_SECONDS:-7200}
ExecStart=$root/tools/longterm/run.sh nightly
Nice=5
EOF

cat >"$units/nova-nightly.timer" <<EOF
[Unit]
Description=Nova-Link nightly checks

[Timer]
OnCalendar=*-*-* 03:17
Persistent=true

[Install]
WantedBy=timers.target
EOF

loginctl enable-linger "$(id -un)" 2>/dev/null || sudo loginctl enable-linger "$(id -un)"
systemctl --user daemon-reload
systemctl --user enable --now nova-fuzz.service nova-nightly.timer
echo "installed: fuzz workers=$forks, soak jobs=$soak_jobs"
