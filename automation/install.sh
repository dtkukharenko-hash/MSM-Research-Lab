#!/usr/bin/env bash
set -Eeuo pipefail
REPO=/home/nnv/MSM-Research-Lab; USER=nnv; DEST=/usr/local/lib/msm-runner; STATE=/home/nnv/.local/state/msm-runner
DRY=false; ENABLE=false
for x in "$@";do case $x in --dry-run)DRY=true;;--enable-now)ENABLE=true;;*)echo "usage: $0 [--dry-run] [--enable-now]" >&2;exit 2;;esac;done
[[ $DRY == true || $(id -u) -eq 0 ]]||{ echo 'install.sh: run as root (or use --dry-run)' >&2;exit 1; }
for f in automation/msm_runner.sh automation/msm_audit.sh automation/msm_correct.sh automation/runner.service automation/runner.timer;do [[ -f $REPO/$f ]]||{ echo "missing $f" >&2;exit 1;};bash -n "$REPO/$f";done
for x in git flock timeout sha256sum python3 bwrap;do command -v "$x" >/dev/null||{ echo "missing required command: $x" >&2;exit 1;};done
echo "Validated installed-copy design: service=$DEST/msm_runner.sh helpers=$DEST/msm_audit.sh,$DEST/msm_correct.sh"
$DRY&&{ echo 'DRY RUN: would install runner/helper copies and one-minute timer; no files or services changed.';exit 0; }
install -d -m 755 "$DEST";install -m 755 "$REPO/automation/msm_runner.sh" "$REPO/automation/msm_audit.sh" "$REPO/automation/msm_correct.sh" "$DEST/"
install -d -m 700 -o "$USER" -g "$USER" "$STATE" "$STATE/logs" "$STATE/locks"
install -m 644 "$REPO/automation/runner.service" /etc/systemd/system/msm-codex-runner.service;install -m 644 "$REPO/automation/runner.timer" /etc/systemd/system/msm-codex-runner.timer
systemctl daemon-reload;systemctl enable msm-codex-runner.timer;$ENABLE&&systemctl enable --now msm-codex-runner.timer||true
