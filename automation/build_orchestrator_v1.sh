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

fail(){ echo "ORCHESTRATOR_V1_FAILED: $*" >&2; exit 1; }
field(){ sed -nE "s/^- $1: *\`?([^\`[:space:]]+)\`? *$/\1/p" "$TASK" | head -n1; }

[[ $(id -u) -eq 0 ]] || fail "run with sudo"
[[ -d $REPO/.git ]] || fail "repository not found: $REPO"
install -d -m 700 -o "$RUN_USER" -g "$RUN_USER" "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/bootstrap.log") 2>&1

old_was_enabled=$(systemctl is-enabled "$OLD_TIMER" 2>/dev/null || true)
new_was_enabled=$(systemctl is-enabled "$NEW_SERVICE" 2>/dev/null || true)
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
[[ $(field task_id) == AUTOMATION-004-LOCAL-ORCHESTRATOR-V1 ]] || fail "unexpected active task"

# Only the known protected Pine may be dirty.
while IFS= read -r line; do
  [[ -z $line ]] && continue
  [[ ${line:0:2} == ' M' && "$REPO/${line:3}" == "$PINE" ]] || fail "unexpected dirty path: $line"
done < <(sudo -u "$RUN_USER" git status --porcelain=v1 --untracked-files=all)

task_status=$(field status)
case "$task_status" in
  READY)
    echo "[2/7] Build, validate, commit and push through existing safe bootstrap"
    bash "$REPO/automation/apply_ready_infrastructure_task.sh"
    [[ $(field status) == COMPLETED ]] || fail "AUTOMATION-004 was not completed"
    ;;
  COMPLETED)
    echo "[2/7] Build already completed; resume installation and verification"
    ;;
  *)
    fail "AUTOMATION-004 has unsupported status: $task_status"
    ;;
esac

[[ -f "$REPO/automation/install_orchestrator.sh" ]] || fail "installer missing"
[[ -f "$REPO/automation/verify_orchestrator.sh" ]] || fail "verifier missing"

# GitHub content writes may create shell files as 0644. Execute repository scripts
# through bash; installed copies receive their executable modes from the installer.
echo "[3/7] Static verification"
bash -n "$REPO/automation/"*.sh
python3 -m py_compile "$REPO/automation/msm_orchestrator.py"
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
echo "task=$(field task_id)"
echo "commit=$(sudo -u "$RUN_USER" git rev-parse HEAD)"
echo "logs=$LOG_DIR"
