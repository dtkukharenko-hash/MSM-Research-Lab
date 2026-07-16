#!/usr/bin/env bash
set -Eeuo pipefail
usage(){ echo "usage: $0 --install --test-mode | --activate-production" >&2; exit 2; }
if [[ $# -eq 2 && $1 == --install && $2 == --test-mode ]]; then MODE=test; elif [[ $# -eq 1 && $1 == --activate-production ]]; then MODE=production; else usage; fi
REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; ROOT=${MSM_FEEDER_INSTALL_ROOT:-/}; DEST="$ROOT/usr/local/lib/msm-orchestrator"; UNIT="$ROOT/etc/systemd/system"; STATE=${MSM_FEEDER_STATE_DIR:-/home/nnv/.local/state/msm-orchestrator}; RUN_USER=${MSM_FEEDER_RUN_USER:-nnv}; RUN_GROUP=${MSM_FEEDER_RUN_GROUP:-$RUN_USER}
[[ -f $REPO/automation/msm_task_feeder.py && -f $REPO/automation/enqueue_task.py && -f $REPO/automation/msm-task-feeder.service ]] || { echo 'missing feeder source' >&2; exit 1; }
PYTHONDONTWRITEBYTECODE=1 python3 -B - "$REPO/automation/msm_task_feeder.py" "$REPO/automation/enqueue_task.py" <<'PY'
from pathlib import Path
import sys
for p in map(Path, sys.argv[1:]): compile(p.read_text(encoding='utf-8'), str(p), 'exec')
PY
bash -n "$0"
if [[ $MODE == production && ${EUID:-$(id -u)} -ne 0 && $ROOT == / ]]; then echo 'production activation requires root' >&2; exit 1; fi
install -d -m 755 "$DEST" "$UNIT"
install -m 644 "$REPO/automation/msm_task_feeder.py" "$REPO/automation/enqueue_task.py" "$DEST/"
install -m 644 "$REPO/automation/msm-task-feeder.service" "$UNIT/msm-task-feeder.service"
for d in "$STATE" "$STATE"/{queue,running,completed,blocked,failed,logs,locks}; do install -d -m 700 -o "$RUN_USER" -g "$RUN_GROUP" "$d"; done
echo "installed feeder immutable copies at $DEST; mode=$MODE (service enablement is external)"
