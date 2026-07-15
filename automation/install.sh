#!/usr/bin/env bash
set -Eeuo pipefail
REPO=/home/nnv/MSM-Research-Lab; USER=nnv; STATE=/home/nnv/.local/state/msm-runner
DRY=false; ENABLE_NOW=false
for arg in "$@"; do case $arg in --dry-run) DRY=true;; --enable-now) ENABLE_NOW=true;; *) echo "usage: $0 [--dry-run] [--enable-now]" >&2; exit 2;; esac; done
[[ $DRY == true || $(id -u) -eq 0 ]] || { echo 'install.sh: run as root (or use --dry-run)' >&2; exit 1; }
for item in "id $USER" "$REPO" /home/nnv/.local/bin/codex git flock timeout sha256sum python3 bwrap; do
  if [[ $item == "id $USER" ]]; then id "$USER" >/dev/null || { echo "missing user $USER" >&2; exit 1; }
  elif [[ $item == "$REPO" ]]; then [[ -d $item/.git ]] || { echo "missing repository $item" >&2; exit 1; }
  else command -v "$item" >/dev/null || { echo "missing required command: $item" >&2; exit 1; }; fi
done
for file in automation/msm_runner.sh automation/msm_audit.sh automation/runner.service automation/runner.timer; do [[ -f $REPO/$file ]] || { echo "missing required file: $file" >&2; exit 1; }; done
bash -n "$REPO/automation/msm_runner.sh"; bash -n "$REPO/automation/msm_audit.sh"
echo "Validated user=$USER repository=$REPO source files and required commands"
if $DRY; then echo 'DRY RUN: source validation does not require executable bits; would create runtime directories, install units, daemon-reload, and enable timer.'; exit 0; fi
install -d -m 700 -o nnv -g nnv "$STATE" "$STATE/logs" "$STATE/locks"
chmod 755 "$REPO/automation/msm_runner.sh" "$REPO/automation/msm_audit.sh"
install -m 644 "$REPO/automation/runner.service" /etc/systemd/system/msm-codex-runner.service
install -m 644 "$REPO/automation/runner.timer" /etc/systemd/system/msm-codex-runner.timer
systemctl daemon-reload; systemctl enable msm-codex-runner.timer
$ENABLE_NOW && systemctl enable --now msm-codex-runner.timer || true
echo 'Installed. Timer starts only with --enable-now or a later systemctl start.'
