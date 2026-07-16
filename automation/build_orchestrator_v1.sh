#!/usr/bin/env bash
set -Eeuo pipefail

REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}
RUN_USER=${MSM_RUN_USER:-nnv}
OLD_TIMER=msm-codex-runner.timer
NEW_SERVICE=msm-orchestrator.service
TASK="$REPO/.codex/TASK.md"
PINE="$REPO/experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
LOG_ROOT=${MSM_ORCH_BOOTSTRAP_LOG_DIR:-/home/nnv/.local/state/msm-runner/orchestrator-bootstrap}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG_DIR="$LOG_ROOT/$STAMP"
BASE_TASK_ID=AUTOMATION-004-LOCAL-ORCHESTRATOR-V1

fail(){ echo "ORCHESTRATOR_V1_FAILED: $*" >&2; exit 1; }
field(){ sed -nE "s/^- $1: *\`?([^\`[:space:]]+)\`? *$/\1/p" "$TASK" | head -n1; }

[[ $(id -u) -eq 0 ]] || fail "run with sudo"
[[ -d $REPO/.git ]] || fail "repository not found: $REPO"
install -d -m 700 -o "$RUN_USER" -g "$RUN_USER" "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/bootstrap.log") 2>&1

old_was_enabled=$(systemctl is-enabled "$OLD_TIMER" 2>/dev/null || true)
pine_before=$(sha256sum "$PINE" | awk '{print $1}')

rollback(){
  rc=$?
  if (( rc != 0 )); then
    echo "Rollback after rc=$rc"
    systemctl disable --now "$NEW_SERVICE" 2>/dev/null || true
    if [[ $old_was_enabled == enabled ]]; then systemctl enable --now "$OLD_TIMER" || true; fi
  fi
}
trap rollback EXIT

cd "$REPO"
echo "[1/7] Sync main"
sudo -u "$RUN_USER" git fetch --prune origin main
local_sha=$(sudo -u "$RUN_USER" git rev-parse HEAD)
remote_sha=$(sudo -u "$RUN_USER" git rev-parse origin/main)
if [[ $local_sha != "$remote_sha" ]]; then
  sudo -u "$RUN_USER" git merge-base --is-ancestor "$local_sha" "$remote_sha" || fail "local main diverged"
  sudo -u "$RUN_USER" git merge --ff-only origin/main
fi

# Remove only bytecode produced by the previous bootstrap revision. Never remove
# tracked files or any other cache contents.
if [[ -d "$REPO/automation/__pycache__" ]]; then
  while IFS= read -r -d '' pyc; do
    rel=${pyc#"$REPO/"}
    if ! sudo -u "$RUN_USER" git ls-files --error-unmatch -- "$rel" >/dev/null 2>&1; then
      rm -f -- "$pyc"
    fi
  done < <(find "$REPO/automation/__pycache__" -maxdepth 1 -type f -name 'msm_orchestrator.cpython-*.pyc' -print0)
  rmdir "$REPO/automation/__pycache__" 2>/dev/null || true
fi

# Only the known protected Pine may be dirty.
while IFS= read -r line; do
  [[ -z $line ]] && continue
  [[ ${line:0:2} == ' M' && "$REPO/${line:3}" == "$PINE" ]] || fail "unexpected dirty path: $line"
done < <(sudo -u "$RUN_USER" git status --porcelain=v1 --untracked-files=all)

active_task=$(field task_id)
active_status=$(field status)
active_original=$(field original_task_id)
active_infra=$(field infrastructure_maintenance)

case "$active_status" in
  READY)
    if [[ $active_task == "$BASE_TASK_ID" || $active_original == "$BASE_TASK_ID" ]]; then
      [[ $active_infra == true ]] || fail "active AUTOMATION-004 task is not infrastructure maintenance"
      echo "[2/7] Execute active AUTOMATION-004 task: $active_task"
      bash "$REPO/automation/apply_ready_infrastructure_task.sh"
      [[ $(field status) == COMPLETED ]] || fail "$active_task was not completed"
    else
      fail "unrelated READY task blocks orchestrator installation: $active_task"
    fi
    ;;
  COMPLETED)
    if [[ $active_task == "$BASE_TASK_ID" || $active_original == "$BASE_TASK_ID" ]]; then
      echo "[2/7] AUTOMATION-004 build/correction already completed; resume installation"
    else
      echo "[2/7] Active task is unrelated but completed; resume committed orchestrator installation"
    fi
    ;;
  *)
    fail "unsupported active task state: task=$active_task status=$active_status"
    ;;
esac

[[ -f "$REPO/automation/install_orchestrator.sh" ]] || fail "installer missing"
[[ -f "$REPO/automation/verify_orchestrator.sh" ]] || fail "verifier missing"
[[ -f "$REPO/automation/msm_orchestrator.py" ]] || fail "orchestrator missing"

# Validate Python syntax without creating __pycache__ or .pyc files in the repository.
echo "[3/7] Static verification"
bash -n "$REPO/automation/"*.sh
python3 - "$REPO/automation/msm_orchestrator.py" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
compile(p.read_text(encoding='utf-8'), str(p), 'exec')
PY
bash "$REPO/automation/verify_orchestrator.sh" --offline

echo "[4/7] Install in test mode"
bash "$REPO/automation/install_orchestrator.sh" --install --test-mode
systemctl daemon-reload
systemctl enable --now "$NEW_SERVICE"
bash "$REPO/automation/verify_orchestrator.sh" --service --test-mode --wait 90

echo "[5/7] Full mock state-machine cycle"
bash "$REPO/automation/verify_orchestrator.sh" --mock-cycle --wait 180

# Switch only after every test above succeeds.
echo "[6/7] Atomic production switch"
systemctl stop "$NEW_SERVICE"
bash "$REPO/automation/install_orchestrator.sh" --activate-production
systemctl enable --now "$NEW_SERVICE"
bash "$REPO/automation/verify_orchestrator.sh" --service --production --wait 90
systemctl disable --now "$OLD_TIMER"
systemctl is-active --quiet "$NEW_SERVICE" || fail "new service is not active"
! systemctl is-active --quiet "$OLD_TIMER" || fail "old timer is still active"

[[ $(sha256sum "$PINE" | awk '{print $1}') == "$pine_before" ]] || fail "protected Pine changed"
while IFS= read -r line; do
  [[ -z $line ]] && continue
  [[ ${line:0:2} == ' M' && "$REPO/${line:3}" == "$PINE" ]] || fail "unexpected final dirty path: $line"
done < <(sudo -u "$RUN_USER" git status --porcelain=v1 --untracked-files=all)

echo "[7/7] Final health"
bash "$REPO/automation/verify_orchestrator.sh" --health

trap - EXIT
echo "ORCHESTRATOR_V1_OK"
echo "service=$NEW_SERVICE"
echo "old_timer=disabled"
echo "active_task=$(field task_id)"
echo "commit=$(sudo -u "$RUN_USER" git rev-parse HEAD)"
echo "logs=$LOG_DIR"
