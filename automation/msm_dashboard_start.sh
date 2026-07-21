#!/usr/bin/env bash
set -Eeuo pipefail

UNIT=msm-dashboard-launch.service

systemctl reset-failed "$UNIT" >/dev/null 2>&1 || true

if ! systemctl start "$UNIT"; then
  systemctl status "$UNIT" --no-pager -l || true
  exit 1
fi

RESULT=$(systemctl show "$UNIT" -p Result --value 2>/dev/null || true)
STATUS=$(systemctl show "$UNIT" -p ExecMainStatus --value 2>/dev/null || true)

echo "LAUNCH_UNIT=$UNIT"
echo "RESULT=${RESULT:-unknown}"
echo "EXEC_MAIN_STATUS=${STATUS:-unknown}"
echo 'START_REQUEST_ACCEPTED'
