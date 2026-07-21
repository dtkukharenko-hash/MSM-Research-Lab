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

# No task is active. Freeze the role pipeline before changing TASK/runtime so a
# newly synchronized READY task cannot be consumed by an older worker.
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

[[ "$pine_hash_after" == "$pine_hash_before" ]] || {
  echo 'SYNC_ABORT_PROTECTED_PINE_HASH_CHANGED'
  exit 1
}
[[ "$pine_status_after" == "$pine_status_before" ]] || {
  echo 'SYNC_ABORT_PROTECTED_PINE_STATUS_CHANGED'
  exit 1
}
if ! "${GIT[@]}" diff --cached --quiet; then
  echo 'SYNC_ABORT_STAGED_CHANGES_CREATED'
  exit 1
fi

runtime_changed=''
if [[ "$before" != "$after" ]]; then
  runtime_changed=$("${GIT[@]}" diff --name-only "$before" "$after" -- automation start.sh | head -n 1)
fi

if [[ -n "$runtime_changed" ]]; then
  # The production installer also performs the constrained held R6A3R
  # publication when TASK.md carries the dedicated HOLD marker.
  bash "$REPO/automation/install_orchestrator.sh" --activate-production
  systemctl daemon-reload
  systemctl enable --now msm-dashboard-sync.timer msm-reporter.service >/dev/null

  # Publication may have advanced origin/main. Pull that collision-free commit
  # into the local main branch before returning control to the dashboard.
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
  deploy='scheduled'
else
  deploy='not-needed'
fi

pine_hash_final=$(sha256sum "$pine_path" | awk '{print $1}')
pine_status_final=$("${GIT[@]}" status --porcelain=v1 -- "$PINE")
[[ "$pine_hash_final" == "$pine_hash_before" ]] || { echo 'SYNC_FINAL_PROTECTED_PINE_HASH_CHANGED'; exit 1; }
[[ "$pine_status_final" == "$pine_status_before" ]] || { echo 'SYNC_FINAL_PROTECTED_PINE_STATUS_CHANGED'; exit 1; }
"${GIT[@]}" diff --cached --quiet || { echo 'SYNC_FINAL_STAGED_CHANGES'; exit 1; }

echo "SYNC_OK before=$before after=$after local_only=$local_only remote_only=$remote_only backup=${backup:-none} runtime_deploy=$deploy feeder=stopped orchestrator=stopped"
