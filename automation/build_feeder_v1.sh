#!/usr/bin/env bash
set -Eeuo pipefail

REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}
RUN_USER=${MSM_RUN_USER:-nnv}
ORCH=msm-orchestrator.service
OLD_TIMER=msm-codex-runner.timer
TASK="$REPO/.codex/TASK.md"
PINE="$REPO/experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
LOG_ROOT=${MSM_FEEDER_BOOTSTRAP_LOG_DIR:-/home/nnv/.local/state/msm-runner/feeder-bootstrap}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG_DIR="$LOG_ROOT/$STAMP"
BASE_TASK=AUTOMATION-005-FEEDER-V1

fail(){ echo "FEEDER_V1_FAILED: $*" >&2; exit 1; }
field(){ sed -nE "s/^- $1: *\`?([^\`[:space:]]+)\`? *$/\1/p" "$TASK" | head -n1; }

[[ $(id -u) -eq 0 ]] || fail "run with sudo"
[[ -d $REPO/.git ]] || fail "repository not found: $REPO"
install -d -m 700 -o "$RUN_USER" -g "$RUN_USER" "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/bootstrap.log") 2>&1

orch_was_enabled=$(systemctl is-enabled "$ORCH" 2>/dev/null || true)
pine_before=$(sha256sum "$PINE" | awk '{print $1}')
rollback(){
  rc=$?
  if (( rc != 0 )); then
    echo "Rollback after rc=$rc"
    systemctl disable --now msm-task-feeder.service 2>/dev/null || true
    if [[ $orch_was_enabled == enabled ]]; then systemctl enable --now "$ORCH" 2>/dev/null || true; fi
    systemctl disable --now "$OLD_TIMER" 2>/dev/null || true
  fi
}
trap rollback EXIT

cd "$REPO"
echo "[1/8] Sync main"
sudo -u "$RUN_USER" git fetch --prune origin main
local_sha=$(sudo -u "$RUN_USER" git rev-parse HEAD)
remote_sha=$(sudo -u "$RUN_USER" git rev-parse origin/main)
if [[ $local_sha != "$remote_sha" ]]; then
  sudo -u "$RUN_USER" git merge-base --is-ancestor "$local_sha" "$remote_sha" || fail "local main diverged"
  sudo -u "$RUN_USER" git merge --ff-only origin/main
fi

# Remove only known untracked Python bytecode from prior verification.
find "$REPO/automation" -maxdepth 2 -type f -name '*.pyc' -path '*/__pycache__/*' -delete 2>/dev/null || true
find "$REPO/automation" -maxdepth 2 -type d -name '__pycache__' -empty -delete 2>/dev/null || true

while IFS= read -r line; do
  [[ -z $line ]] && continue
  [[ ${line:0:2} == ' M' && "$REPO/${line:3}" == "$PINE" ]] || fail "unexpected dirty path: $line"
done < <(sudo -u "$RUN_USER" git status --porcelain=v1 --untracked-files=all)

active=$(field task_id); status=$(field status); original=$(field original_task_id)
if [[ $status == READY && ( $active == "$BASE_TASK" || $original == "$BASE_TASK" ) ]]; then
  echo "[2/8] Execute infrastructure task: $active"
  systemctl stop "$ORCH" 2>/dev/null || true
  bash "$REPO/automation/apply_ready_infrastructure_task.sh"
elif [[ $status == COMPLETED && ( $active == "$BASE_TASK" || $original == "$BASE_TASK" ) ]]; then
  echo "[2/8] Build already completed; resume installation"
else
  fail "unexpected task: id=$active status=$status original=$original"
fi

for f in automation/msm_task_feeder.py automation/enqueue_task.py automation/install_feeder.sh automation/verify_feeder.sh automation/msm-task-feeder.service; do
  [[ -f $REPO/$f ]] || fail "missing $f"
done

echo "[3/8] Static and isolated verification"
bash -n "$REPO/automation/"*.sh
python3 -B - "$REPO/automation/msm_task_feeder.py" "$REPO/automation/enqueue_task.py" <<'PY'
from pathlib import Path
import sys
for name in sys.argv[1:]:
    p=Path(name); compile(p.read_text(encoding='utf-8'), str(p), 'exec')
PY
bash "$REPO/automation/verify_feeder.sh" --offline
bash "$REPO/automation/verify_feeder.sh" --fixtures

echo "[4/8] Install feeder in disabled test mode"
bash "$REPO/automation/install_feeder.sh" --install --test-mode
systemctl daemon-reload
bash "$REPO/automation/verify_feeder.sh" --installed --test-mode

echo "[5/8] End-to-end mock ingestion"
bash "$REPO/automation/verify_feeder.sh" --mock-ingestion

echo "[6/8] Activate production feeder"
bash "$REPO/automation/install_feeder.sh" --activate-production
systemctl daemon-reload
systemctl enable --now "$ORCH"
systemctl enable --now msm-task-feeder.service
systemctl disable --now "$OLD_TIMER" 2>/dev/null || true
bash "$REPO/automation/verify_feeder.sh" --service --production --wait 90

echo "[7/8] Repository and protection checks"
[[ $(sha256sum "$PINE" | awk '{print $1}') == "$pine_before" ]] || fail "protected Pine changed"
find "$REPO/automation" -maxdepth 2 -type f -name '*.pyc' -path '*/__pycache__/*' -delete 2>/dev/null || true
find "$REPO/automation" -maxdepth 2 -type d -name '__pycache__' -empty -delete 2>/dev/null || true
while IFS= read -r line; do
  [[ -z $line ]] && continue
  [[ ${line:0:2} == ' M' && "$REPO/${line:3}" == "$PINE" ]] || fail "unexpected final dirty path: $line"
done < <(sudo -u "$RUN_USER" git status --porcelain=v1 --untracked-files=all)

echo "[8/8] Final health"
bash "$REPO/automation/verify_feeder.sh" --health

trap - EXIT
echo "FEEDER_V1_OK"
echo "feeder=msm-task-feeder.service"
echo "orchestrator=$ORCH"
echo "old_timer=disabled"
echo "commit=$(sudo -u "$RUN_USER" git rev-parse HEAD)"
echo "logs=$LOG_DIR"
