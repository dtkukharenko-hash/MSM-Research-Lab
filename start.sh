#!/usr/bin/env bash
set -Eeuo pipefail

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE_ROOT="${HOME}/.local/state/msm-orchestrator"
TASK_FILE="$REPO/.codex/TASK.md"
REPORTER=/usr/local/lib/msm-orchestrator/msm_reporter.py
LOG_FILE=""
POLL_SECONDS=5
TIMEOUT_SECONDS=$((12 * 60 * 60))

cd "$REPO"
chmod +x "$REPO/start.sh" 2>/dev/null || true

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

state_file() {
    local task_id="$1"
    local state dir found
    for state in completed blocked failed running queue; do
        dir="$STATE_ROOT/$state"
        [[ -d "$dir" ]] || continue
        found="$(find "$dir" -maxdepth 1 -type f -name "${task_id}-*.json" -print -quit 2>/dev/null || true)"
        if [[ -n "$found" ]]; then
            printf '%s|%s\n' "$state" "$found"
            return 0
        fi
    done
    printf 'waiting|\n'
}

print_new_log_lines() {
    [[ -n "$LOG_FILE" && -f "$LOG_FILE" ]] || return 0
    local current
    current="$(wc -l < "$LOG_FILE")"
    if (( current > LOG_LINES )); then
        sed -n "$((LOG_LINES + 1)),${current}p" "$LOG_FILE"
        LOG_LINES="$current"
    fi
}

show_report() {
    local task_id="$1" fallback="${2:-}" report="$STATE_ROOT/reports/${task_id}.md"
    if [[ -f "$REPORTER" ]]; then
        sudo -u nnv /usr/bin/python3 -B "$REPORTER" \
            --repo "$REPO" --state-dir "$STATE_ROOT" --task-id "$task_id" >/dev/null 2>&1 || true
    fi
    local i
    for i in {1..20}; do
        [[ -s "$report" ]] && break
        sleep 1
    done
    if [[ -s "$report" ]]; then
        echo "REPORT=$report"
        cat "$report"
    elif [[ -n "$fallback" && -f "$fallback" ]]; then
        echo "REPORT_NOT_AVAILABLE; raw envelope follows:"
        cat "$fallback"
    else
        echo "REPORT_NOT_AVAILABLE"
    fi
}

echo "[1/6] Git sync"
git pull --ff-only origin main

[[ -f "$TASK_FILE" ]] || {
    echo "ERROR: .codex/TASK.md not found"
    exit 1
}

TASK_ID="$(field task_id)"
TASK_STATUS="$(field status)"
TASK_INFRA="$(field infrastructure_maintenance)"

[[ -n "$TASK_ID" ]] || {
    echo "ERROR: task_id not found"
    exit 1
}

echo "TASK_ID=$TASK_ID"
echo "TASK_STATUS=$TASK_STATUS"
echo "INFRASTRUCTURE_MAINTENANCE=$TASK_INFRA"

LOG_FILE="$STATE_ROOT/logs/${TASK_ID}.jsonl"
LOG_LINES=0
[[ -f "$LOG_FILE" ]] && LOG_LINES="$(wc -l < "$LOG_FILE")"

echo "[2/6] Install current runtime, reporter and dashboard"
sudo bash automation/install_orchestrator.sh --activate-production
sudo systemctl daemon-reload
sudo systemctl enable --now msm-reporter.service msm-dashboard.service
sudo systemctl restart msm-reporter.service msm-dashboard.service

echo "DASHBOARD=http://10.43.44.254:8765/"

if [[ "$TASK_INFRA" == "true" ]]; then
    echo "[3/6] Infrastructure bootstrap completed"
    echo "REPORTS=$STATE_ROOT/reports"
    echo "LATEST_REPORT=$STATE_ROOT/reports/latest.md"
    exit 0
fi

existing="$(state_file "$TASK_ID")"
existing_state="${existing%%|*}"
existing_path="${existing#*|}"

case "$existing_state" in
    completed)
        echo "STATUS=COMPLETED"
        show_report "$TASK_ID" "$existing_path"
        git pull --ff-only origin main
        git log -3 --oneline
        exit 0
        ;;
    blocked|failed)
        echo "STATUS=${existing_state^^}"
        show_report "$TASK_ID" "$existing_path"
        exit 1
        ;;
    running|queue)
        echo "[3/6] Existing run detected: $existing_state"
        ;;
    waiting)
        if [[ "$TASK_STATUS" != "READY" ]]; then
            echo "NO_READY_TASK"
            exit 0
        fi
        echo "[3/6] Start production services"
        sudo systemctl disable --now msm-codex-runner.timer >/dev/null 2>&1 || true
        sudo systemctl enable --now msm-orchestrator.service msm-task-feeder.service msm-reporter.service msm-dashboard.service
        sudo systemctl restart msm-task-feeder.service msm-orchestrator.service msm-reporter.service msm-dashboard.service
        ;;
esac

echo "[4/6] Run task"
echo "The process continues in systemd; Ctrl+C only stops this screen, not the task."

started=$SECONDS
last_state=""
while (( SECONDS - started < TIMEOUT_SECONDS )); do
    print_new_log_lines
    current="$(state_file "$TASK_ID")"
    current_state="${current%%|*}"
    current_path="${current#*|}"

    if [[ "$current_state" != "$last_state" ]]; then
        echo "STATE=$current_state"
        last_state="$current_state"
    fi

    case "$current_state" in
        completed)
            print_new_log_lines
            echo "[5/6] COMPLETED"
            show_report "$TASK_ID" "$current_path"
            echo "[6/6] Git status"
            git pull --ff-only origin main
            git status --short
            git log -5 --oneline
            exit 0
            ;;
        blocked|failed)
            print_new_log_lines
            echo "[5/6] ${current_state^^}"
            show_report "$TASK_ID" "$current_path"
            echo "LOG=$LOG_FILE"
            exit 1
            ;;
    esac

    sleep "$POLL_SECONDS"
done

echo "TIMEOUT: task continues or is stuck"
echo "LOG=$LOG_FILE"
echo "LATEST_REPORT=$STATE_ROOT/reports/latest.md"
exit 2
