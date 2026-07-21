#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/nnv/MSM-Research-Lab
STATE=/home/nnv/.local/state/msm-orchestrator
TASK_FILE="$REPO/.codex/TASK.md"
LOCK=/run/lock/msm-dashboard-launch-task.lock

exec 9>"$LOCK"
flock -n 9 || { echo 'START_ALREADY_IN_PROGRESS'; exit 1; }

field() {
  local name="$1"
  awk -v key="$name" '
    $0 ~ "^- " key ":" {
      sub("^- " key ":[[:space:]]*", "")
      gsub(/^[`\"]|[`\"]$/, "")
      print
      exit
    }
  ' "$TASK_FILE"
}

runuser -u nnv -- git -C "$REPO" pull --ff-only origin main

[[ -f "$TASK_FILE" ]] || { echo 'TASK_FILE_MISSING'; exit 1; }
TASK_ID=$(field task_id)
TASK_STATUS=$(field status)

[[ -n "$TASK_ID" ]] || { echo 'TASK_ID_MISSING'; exit 1; }
[[ "$TASK_STATUS" == READY ]] || { echo "TASK_NOT_READY status=$TASK_STATUS"; exit 1; }

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
echo 'START_REQUEST_ACCEPTED'
