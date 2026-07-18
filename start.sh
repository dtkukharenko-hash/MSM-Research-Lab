#!/usr/bin/env bash
set -Eeuo pipefail

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE_ROOT="${HOME}/.local/state/msm-orchestrator"
TASK_FILE="$REPO/.codex/TASK.md"
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
            gsub(/^[`"]|[`"]$/, "")
            print
            exit
        }
    ' "$TASK_FILE"
}

state_file() {
    local task_id="$1"
    local state
    for state in completed blocked failed running queued; do
        local dir="$STATE_ROOT/$state"
        [[ -d "$dir" ]] || continue
        local found
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

echo "[1/5] Git sync"
git pull --ff-only origin main

[[ -f "$TASK_FILE" ]] || {
    echo "ERROR: .codex/TASK.md not found"
    exit 1
}

TASK_ID="$(field task_id)"
TASK_STATUS="$(field status)"

[[ -n "$TASK_ID" ]] || {
    echo "ERROR: task_id not found"
    exit 1
}

echo "TASK_ID=$TASK_ID"
echo "TASK_STATUS=$TASK_STATUS"

LOG_FILE="$STATE_ROOT/logs/${TASK_ID}.jsonl"
LOG_LINES=0
[[ -f "$LOG_FILE" ]] && LOG_LINES="$(wc -l < "$LOG_FILE")"

existing="$(state_file "$TASK_ID")"
existing_state="${existing%%|*}"
existing_path="${existing#*|}"

case "$existing_state" in
    completed)
        echo "STATUS=COMPLETED"
        git pull --ff-only origin main
        git log -3 --oneline
        exit 0
        ;;
    blocked|failed)
        echo "STATUS=${existing_state^^}"
        cat "$existing_path"
        exit 1
        ;;
    running|queued)
        echo "[2/5] Existing run detected: $existing_state"
        ;;
    waiting)
        if [[ "$TASK_STATUS" != "READY" ]]; then
            echo "NO_READY_TASK"
            exit 0
        fi

        echo "[2/5] Install current orchestrator"
        sudo bash automation/install_orchestrator.sh --activate-production
        sudo systemctl daemon-reload

        echo "[3/5] Start production services"
        sudo systemctl disable --now msm-codex-runner.timer >/dev/null 2>&1 || true
        sudo systemctl enable --now msm-orchestrator.service msm-task-feeder.service
        sudo systemctl restart msm-task-feeder.service msm-orchestrator.service
        ;;
esac

echo "[4/5] Run task"
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
            echo "[5/5] COMPLETED"
            git pull --ff-only origin main
            git status --short
            git log -5 --oneline
            exit 0
            ;;
        blocked|failed)
            print_new_log_lines
            echo "[5/5] ${current_state^^}"
            cat "$current_path"
            echo "LOG=$LOG_FILE"
            exit 1
            ;;
    esac

    sleep "$POLL_SECONDS"
done

echo "TIMEOUT: task continues or is stuck"
echo "LOG=$LOG_FILE"
exit 2
