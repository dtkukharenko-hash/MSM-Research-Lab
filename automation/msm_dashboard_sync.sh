#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/nnv/MSM-Research-Lab
STATE=/home/nnv/.local/state/msm-orchestrator
LOCK=/run/lock/msm-dashboard-sync.lock

exec 9>"$LOCK"
flock -n 9 || { echo 'SYNC_ALREADY_IN_PROGRESS'; exit 0; }

for dir in queue running; do
  if find "$STATE/$dir" -maxdepth 1 -type f -name '*.json' -print -quit 2>/dev/null | grep -q .; then
    echo "SYNC_SKIPPED_ACTIVE_TASK directory=$dir"
    exit 0
  fi
done

branch=$(runuser -u nnv -- git -C "$REPO" branch --show-current)
[[ "$branch" == main ]] || { echo "SYNC_REFUSED_BRANCH branch=$branch"; exit 1; }

before=$(runuser -u nnv -- git -C "$REPO" rev-parse HEAD)
runuser -u nnv -- git -C "$REPO" fetch origin main
runuser -u nnv -- git -C "$REPO" merge --ff-only origin/main
after=$(runuser -u nnv -- git -C "$REPO" rev-parse HEAD)

echo "SYNC_OK before=$before after=$after"
