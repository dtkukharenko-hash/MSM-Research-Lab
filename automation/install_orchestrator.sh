#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "usage: $0 --install --test-mode | --activate-production" >&2
  exit 2
}

run_fixture() {
  local tmp run_user run_group mode path
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' RETURN
  run_user=${MSM_ORCH_RUN_USER:-$(id -un)}
  run_group=${MSM_ORCH_RUN_GROUP:-$(id -gn "$run_user")}

  for mode in '--install --test-mode' '--activate-production'; do
    MSM_ORCH_INSTALLER_FIXTURE=0 \
      MSM_ORCH_INSTALL_ROOT="$tmp/install" \
      MSM_ORCH_STATE_DIR="$tmp/state" \
      MSM_MARKET_DATA_ROOT="$tmp/market-data" \
      MSM_ORCH_RUN_USER="$run_user" \
      MSM_ORCH_RUN_GROUP="$run_group" \
      bash "$0" $mode
  done

  printf 'preserve-this-state\n' >"$tmp/state/queue/sentinel"
  MSM_ORCH_INSTALLER_FIXTURE=0 \
    MSM_ORCH_INSTALL_ROOT="$tmp/install" \
    MSM_ORCH_STATE_DIR="$tmp/state" \
    MSM_MARKET_DATA_ROOT="$tmp/market-data" \
    MSM_ORCH_RUN_USER="$run_user" \
    MSM_ORCH_RUN_GROUP="$run_group" \
    bash "$0" --install --test-mode

  for path in "$tmp/state" "$tmp/state"/{queue,running,completed,blocked,failed,logs,locks} "$tmp/market-data"; do
    [[ $(stat -c '%U:%G:%a' "$path") == "$run_user:$run_group:700" ]] || {
      echo "fixture failed runtime ownership or mode: $path" >&2
      return 1
    }
  done
  [[ $(<"$tmp/state/queue/sentinel") == preserve-this-state ]] || {
    echo 'fixture failed to preserve sentinel state file' >&2
    return 1
  }

  for mode in '' '--install' '--test-mode' '--activate-production --test-mode' '--activate-production --install' '--install --activate-production' '--install --test-mode --test-mode' '--test-mode --install'; do
    if MSM_ORCH_INSTALLER_FIXTURE=0 \
      MSM_ORCH_INSTALL_ROOT="$tmp/install" \
      MSM_ORCH_STATE_DIR="$tmp/state" \
      MSM_MARKET_DATA_ROOT="$tmp/market-data" \
      bash "$0" $mode >/dev/null 2>&1; then
      echo "fixture accepted unsupported invocation: ${mode:-<none>}" >&2
      return 1
    fi
  done
  echo INSTALLER_FIXTURE_OK
}

if [[ ${MSM_ORCH_INSTALLER_FIXTURE:-0} == 1 ]]; then
  run_fixture
  exit $?
fi

if [[ $# -eq 2 && $1 == --install && $2 == --test-mode ]]; then
  MODE=test
elif [[ $# -eq 1 && $1 == --activate-production ]]; then
  MODE=production
else
  usage
fi

REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}
ROOT=${MSM_ORCH_INSTALL_ROOT:-/}
DEST="$ROOT/usr/local/lib/msm-orchestrator"
UNIT="$ROOT/etc/systemd/system"
STATE=${MSM_ORCH_STATE_DIR:-/home/nnv/.local/state/msm-orchestrator}
RUN_USER=${MSM_ORCH_RUN_USER:-nnv}
RUN_GROUP=${MSM_ORCH_RUN_GROUP:-$RUN_USER}
if [[ -n ${MSM_MARKET_DATA_ROOT:-} ]]; then
  DATA_ROOT=$MSM_MARKET_DATA_ROOT
elif [[ $ROOT == / ]]; then
  DATA_ROOT=/home/nnv/.local/share/msm-market-data
else
  DATA_ROOT="$ROOT/home/nnv/.local/share/msm-market-data"
fi
PYCACHE_ROOT=$(mktemp -d)
trap 'rm -rf "$PYCACHE_ROOT"' EXIT

for f in msm_orchestrator.py msm_task_feeder.py msm_worker.sh install_orchestrator.sh verify_orchestrator.sh msm-orchestrator.service msm-task-feeder.service; do
  [[ -f "$REPO/automation/$f" ]] || { echo "missing $f" >&2; exit 1; }
done
PYTHONPYCACHEPREFIX="$PYCACHE_ROOT" python3 -m py_compile "$REPO/automation/msm_orchestrator.py" "$REPO/automation/msm_task_feeder.py"
bash -n "$REPO/automation/msm_worker.sh"
bash -n "$REPO/automation/verify_orchestrator.sh"
if [[ $MODE == production && ${EUID:-$(id -u)} -ne 0 && $ROOT == / ]]; then
  echo 'production activation requires root' >&2
  exit 1
fi

install -d -m 755 "$DEST" "$UNIT"
install -m 644 "$REPO/automation/msm_orchestrator.py" "$REPO/automation/msm_task_feeder.py" "$REPO/automation/msm_worker.sh" "$DEST/"
install -m 644 "$REPO/automation/msm-orchestrator.service" "$REPO/automation/msm-task-feeder.service" "$UNIT/"
for d in "$STATE" "$STATE"/{queue,running,completed,blocked,failed,logs,locks}; do
  install -d -m 700 -o "$RUN_USER" -g "$RUN_GROUP" "$d"
done
install -d -m 700 -o "$RUN_USER" -g "$RUN_GROUP" "$DATA_ROOT"
echo "installed immutable source copies at $DEST; persistent market data at $DATA_ROOT"
