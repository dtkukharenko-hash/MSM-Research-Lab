#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/nnv/MSM-Research-Lab
STATE=/home/nnv/.local/state/msm-orchestrator
TASK_FILE="$REPO/.codex/TASK.md"
RUNTIME=/usr/local/lib/msm-orchestrator
SYNC="$RUNTIME/msm_dashboard_sync.sh"
LOCK=/run/lock/msm-dashboard-launch-task.lock

exec 9>"$LOCK"
flock -n 9 || { echo 'START_ALREADY_IN_PROGRESS'; exit 1; }

field() {
  local name=$1
  awk -v key="$name" '
    /^## / { exit }
    $0 ~ "^- " key ":" {
      sub("^- " key ":[[:space:]]*", "")
      gsub(/^[`\"]|[`\"]$/, "")
      print
      exit
    }
  ' "$TASK_FILE"
}

[[ -x $SYNC ]] || { echo 'SYNC_HELPER_MISSING'; exit 1; }
"$SYNC"

[[ -f $TASK_FILE ]] || { echo 'TASK_FILE_MISSING'; exit 1; }
TASK_ID=$(field task_id)
TASK_STATUS=$(field status)

[[ -n $TASK_ID ]] || { echo 'TASK_ID_MISSING'; exit 1; }
[[ $TASK_STATUS == READY ]] || { echo "TASK_NOT_READY status=$TASK_STATUS"; exit 1; }

for file in msm_orchestrator.py msm_worker.sh msm_task_feeder.py msm_reporter.py; do
  [[ -f "$REPO/automation/$file" && -f "$RUNTIME/$file" ]] || {
    echo "RUNTIME_FILE_MISSING file=$file"
    exit 1
  }
  cmp -s "$REPO/automation/$file" "$RUNTIME/$file" || {
    repo_hash=$(sha256sum "$REPO/automation/$file" | awk '{print $1}')
    runtime_hash=$(sha256sum "$RUNTIME/$file" | awk '{print $1}')
    echo "RUNTIME_IDENTITY_MISMATCH file=$file repo=$repo_hash installed=$runtime_hash"
    exit 1
  }
done

for dir in queue running; do
  if find "$STATE/$dir" -maxdepth 1 -type f -name '*.json' -print -quit 2>/dev/null | grep -q .; then
    echo "ANOTHER_TASK_ACTIVE directory=$dir"
    exit 1
  fi
done

for dir in completed failed blocked; do
  if find "$STATE/$dir" -maxdepth 1 -type f -name "${TASK_ID}-*.json" -print -quit 2>/dev/null | grep -q .; then
    echo "TASK_ALREADY_TERMINAL task_id=$TASK_ID directory=$dir"
    exit 1
  fi
done

systemctl enable --now msm-reporter.service msm-task-feeder.service msm-orchestrator.service
systemctl restart msm-reporter.service msm-task-feeder.service msm-orchestrator.service

if systemctl cat msm-telegram-report@.service >/dev/null 2>&1; then
  systemctl enable --now "msm-telegram-report@${TASK_ID}.service" >/dev/null 2>&1 || true
fi

echo "TASK_ID=$TASK_ID"
echo 'RUNTIME_IDENTITY_OK'
echo 'START_REQUEST_ACCEPTED'
