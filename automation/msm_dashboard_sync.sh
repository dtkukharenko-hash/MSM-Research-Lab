#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/nnv/MSM-Research-Lab
STATE=/home/nnv/.local/state/msm-orchestrator
PINE=experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
LOCK=/run/lock/msm-dashboard-sync.lock

exec 9>"$LOCK"
flock -n 9 || { echo 'SYNC_ALREADY_IN_PROGRESS'; exit 0; }

for dir in queue running; do
  if find "$STATE/$dir" -maxdepth 1 -type f -name '*.json' -print -quit 2>/dev/null | grep -q .; then
    echo "SYNC_SKIPPED_ACTIVE_TASK directory=$dir"
    exit 0
  fi
done

# Freeze the role pipeline before changing TASK/runtime. It stays stopped until
# the user explicitly presses Start for the synchronized READY task.
systemctl stop msm-task-feeder.service msm-orchestrator.service >/dev/null 2>&1 || true

GIT=(runuser -u nnv -- git -C "$REPO")
branch=$("${GIT[@]}" branch --show-current)
[[ "$branch" == main ]] || { echo "SYNC_REFUSED_BRANCH branch=$branch"; exit 1; }

if ! "${GIT[@]}" diff --cached --quiet; then
  echo 'SYNC_REFUSED_STAGED_CHANGES'
  exit 1
fi

pine_path="$REPO/$PINE"
[[ -f "$pine_path" ]] || { echo 'SYNC_REFUSED_PROTECTED_PINE_MISSING'; exit 1; }
pine_hash_before=$(sha256sum "$pine_path" | awk '{print $1}')
pine_status_before=$("${GIT[@]}" status --porcelain=v1 -- "$PINE")

before=$("${GIT[@]}" rev-parse HEAD)
"${GIT[@]}" fetch origin main
read -r local_only remote_only < <("${GIT[@]}" rev-list --left-right --count HEAD...origin/main)
backup=''

if (( remote_only == 0 )); then
  :
elif (( local_only == 0 )); then
  "${GIT[@]}" merge --ff-only origin/main
else
  backup="backup/dashboard-sync-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  "${GIT[@]}" branch "$backup" HEAD
  if ! "${GIT[@]}" reset --keep origin/main; then
    echo "SYNC_DIVERGENCE_REQUIRES_MANUAL_REVIEW backup=$backup"
    exit 1
  fi
fi

after=$("${GIT[@]}" rev-parse HEAD)
pine_hash_after=$(sha256sum "$pine_path" | awk '{print $1}')
pine_status_after=$("${GIT[@]}" status --porcelain=v1 -- "$PINE")

[[ "$pine_hash_after" == "$pine_hash_before" ]] || { echo 'SYNC_ABORT_PROTECTED_PINE_HASH_CHANGED'; exit 1; }
[[ "$pine_status_after" == "$pine_status_before" ]] || { echo 'SYNC_ABORT_PROTECTED_PINE_STATUS_CHANGED'; exit 1; }
"${GIT[@]}" diff --cached --quiet || { echo 'SYNC_ABORT_STAGED_CHANGES_CREATED'; exit 1; }

# Always reinstall the checked-in runtime. Comparing Git revisions is not enough:
# the repository may already be current while /usr/local still contains an older worker.
bash "$REPO/automation/install_orchestrator.sh" --activate-production
systemctl daemon-reload
systemctl enable --now msm-dashboard-sync.timer msm-reporter.service >/dev/null

# An installer-side constrained publication may advance origin/main. Reconcile it
# without touching pre-existing dirty/untracked paths.
"${GIT[@]}" fetch origin main
read -r local_after remote_after < <("${GIT[@]}" rev-list --left-right --count HEAD...origin/main)
if (( local_after == 0 && remote_after > 0 )); then
  "${GIT[@]}" merge --ff-only origin/main
elif (( local_after > 0 || remote_after > 0 )); then
  echo "SYNC_POST_DEPLOY_DIVERGENCE local=$local_after remote=$remote_after"
  exit 1
fi
after=$("${GIT[@]}" rev-parse HEAD)

systemd-run \
  --unit=msm-dashboard-restart \
  --on-active=2s \
  --collect \
  /usr/bin/systemctl restart msm-dashboard.service >/dev/null

pine_hash_final=$(sha256sum "$pine_path" | awk '{print $1}')
pine_status_final=$("${GIT[@]}" status --porcelain=v1 -- "$PINE")
[[ "$pine_hash_final" == "$pine_hash_before" ]] || { echo 'SYNC_FINAL_PROTECTED_PINE_HASH_CHANGED'; exit 1; }
[[ "$pine_status_final" == "$pine_status_before" ]] || { echo 'SYNC_FINAL_PROTECTED_PINE_STATUS_CHANGED'; exit 1; }
"${GIT[@]}" diff --cached --quiet || { echo 'SYNC_FINAL_STAGED_CHANGES'; exit 1; }

echo "SYNC_OK before=$before after=$after local_only=$local_only remote_only=$remote_only backup=${backup:-none} runtime_deploy=installed feeder=stopped orchestrator=stopped"
