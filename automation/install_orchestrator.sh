#!/usr/bin/env bash
set -Eeuo pipefail
MODE=; for a in "$@"; do case $a in --install|--test-mode|--activate-production) MODE+=" $a";;*) exit 2;;esac;done
[[ $MODE == *" --install"* || $MODE == *" --activate-production"* ]] || exit 2
REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; ROOT=${MSM_ORCH_INSTALL_ROOT:-/}; DEST="$ROOT/usr/local/lib/msm-orchestrator"; UNIT="$ROOT/etc/systemd/system"; STATE=${MSM_ORCH_STATE_DIR:-/home/nnv/.local/state/msm-orchestrator}
for f in msm_orchestrator.py msm_worker.sh install_orchestrator.sh verify_orchestrator.sh; do [[ -f "$REPO/automation/$f" ]] || { echo "missing $f" >&2; exit 1;}; done
python3 -m py_compile "$REPO/automation/msm_orchestrator.py"; bash -n "$REPO/automation/msm_worker.sh"; bash -n "$REPO/automation/verify_orchestrator.sh"
if [[ $MODE == *" --activate-production"* && ${EUID:-$(id -u)} -ne 0 && $ROOT == / ]]; then echo "production activation requires root" >&2; exit 1; fi
install -d -m 755 "$DEST" "$UNIT"; install -m 644 "$REPO/automation/msm_orchestrator.py" "$REPO/automation/msm_worker.sh" "$DEST/"; install -m 644 "$REPO/automation/msm-orchestrator.service" "$UNIT/msm-orchestrator.service"
for d in "$STATE" "$STATE/queue" "$STATE/running" "$STATE/completed" "$STATE/blocked" "$STATE/failed" "$STATE/logs" "$STATE/locks"; do install -d -m 700 "$d"; done
echo "installed immutable source copies at $DEST (old runner unchanged)"
