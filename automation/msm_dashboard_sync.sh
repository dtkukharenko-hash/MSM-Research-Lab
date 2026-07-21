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
  bash "$REPO/automation/install_orchestrator.sh" --activate-production
  systemctl daemon-reload
  systemctl enable --now msm-dashboard-sync.timer msm-reporter.service >/dev/null
  systemd-run \
    --unit=msm-dashboard-restart \
    --on-active=2s \
    --collect \
    /usr/bin/systemctl restart msm-dashboard.service >/dev/null
  deploy='scheduled'
else
  deploy='not-needed'
fi

echo "SYNC_OK before=$before after=$after local_only=$local_only remote_only=$remote_only backup=${backup:-none} runtime_deploy=$deploy"
