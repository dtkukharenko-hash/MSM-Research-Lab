#!/usr/bin/env bash
# Shell-owned orchestration.  Codex is deliberately never given Git duties.
set -Eeuo pipefail

REPO=/home/nnv/MSM-Research-Lab
CODEX=/home/nnv/.local/bin/codex
STATE_DIR=/home/nnv/.local/state/msm-runner
LOG_DIR="$STATE_DIR/logs"; LOCK_DIR="$STATE_DIR/locks"; STATE_FILE="$STATE_DIR/state.json"
PINE=experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
DRY_RUN=false; [[ ${1:-} == --dry-run ]] && DRY_RUN=true
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
die() { printf 'msm_runner: %s\n' "$*" >&2; exit 1; }

write_state() { # state task hash started finished start last audit exit reason
  python3 - "$STATE_FILE" "$@" <<'PY'
import json, os, sys
p, state, task, digest, started, finished, first, last, audit, code, reason = sys.argv[1:]
d = {"runner_state": state, "task_id": task, "task_hash": digest,
     "started_at": started, "finished_at": finished, "starting_commit": first,
     "last_commit": last, "audit_status": audit, "exit_code": int(code),
     "failure_reason": reason, "runner_pid": os.getpid(), "retry_requested": False}
t = p + ".tmp.%d" % os.getpid()
with open(t, "w") as f: json.dump(d, f, indent=2, sort_keys=True); f.write("\n")
os.replace(t, p)
PY
}
state() { write_state "$1" "${2:-}" "${3:-}" "${4:-}" "${5:-}" "${6:-}" "${7:-}" "${8:-}" "${9:-0}" "${10:-}"; }
field() { sed -nE "s/^- $1: *\`?([^\`[:space:]]+)\`? *$/\1/p" "$REPO/.codex/TASK.md" | head -n1; }
tracked_dirty_paths() { git -C "$REPO" diff --name-only; git -C "$REPO" diff --cached --name-only; git -C "$REPO" ls-files --others --exclude-standard; }
worktree_hash() { { git -C "$REPO" diff --binary; git -C "$REPO" diff --cached --binary; while IFS= read -r p; do printf '\nUNTRACKED:%s\n' "$p"; sha256sum "$REPO/$p"; done < <(git -C "$REPO" ls-files --others --exclude-standard | sort); } | sha256sum | awk '{print $1}'; }
allowed_preflight_worktree() {
  local entry xy path
  while IFS= read -r entry; do
    [[ -z $entry ]] && continue
    xy=${entry:0:2}; path=${entry:3}
    [[ $xy == ' M' && $path == "$PINE" ]] || return 1
  done < <(git -C "$REPO" status --porcelain=v1 --untracked-files=all)
}
task_allowlist() {
  local task_id=$1
  if [[ $task_id == AUTOMATION-001-R1-RUNNER-SANDBOX-CORRECTION ]]; then
    printf '%s\n' 'automation/**' '.codex/AUTOPILOT_POLICY.md' '.codex/RESULT.md' 'PROJECT_QUEUE.md'
  elif [[ -f $REPO/.codex/ALLOWLIST.txt ]]; then
    sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' "$REPO/.codex/ALLOWLIST.txt"
    printf '%s\n' '.codex/RESULT.md'
  else
    return 1
  fi
}
path_allowed() { local p=$1 glob; while IFS= read -r glob; do [[ $p == $glob ]] && return 0; done < <(task_allowlist "$task_id"); return 1; }
verify_post_codex() {
  local p
  [[ $(sha256sum "$PINE" | awk '{print $1}') == "$pine_before" ]] || die 'protected Pine hash changed'
  git diff --cached --quiet -- "$PINE" || die 'protected Pine is staged'
  git diff --cached --quiet || die 'Codex left staged changes; shell runner requires none'
  while IFS= read -r p; do
    [[ -z $p || $p == "$PINE" ]] && continue
    [[ $p != experiments/* && $p != docs/* && $p != MEMORY.md ]] || die "forbidden path changed: $p"
    path_allowed "$p" || die "changed path outside task allowlist: $p"
  done < <(tracked_dirty_paths | sort -u)
  [[ -f .codex/RESULT.md ]] && grep -Fq "task_id: \`$task_id\`" .codex/RESULT.md || die 'RESULT.md missing or task ID differs'
  [[ $(tracked_dirty_paths | grep -Fvx "$PINE" | sed '/^$/d' | wc -l) -gt 0 ]] || die 'no allowed implementation path changed'
}
consume_retry() { # Atomic replacement makes a requested retry one-shot.
  python3 - "$STATE_FILE" "$task_id" "$task_hash" <<'PY'
import json, os, sys
p, task, digest = sys.argv[1:]
try:
    with open(p) as f: d = json.load(f)
except FileNotFoundError:
    sys.exit(1)
if not (d.get("retry_requested") is True and d.get("task_id") == task and d.get("task_hash") == digest): sys.exit(1)
d["retry_requested"] = False; d["retry_consumed_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
t = p + ".tmp.%d" % os.getpid()
with open(t, "w") as f: json.dump(d, f, indent=2, sort_keys=True); f.write("\n")
os.replace(t, p)
PY
}
result_pushed() { python3 - "$STATE_FILE" "$task_id" "$task_hash" <<'PY'
import json,sys
try:
 with open(sys.argv[1]) as f: d=json.load(f)
 sys.exit(0 if d.get("task_id")==sys.argv[2] and d.get("task_hash")==sys.argv[3] and d.get("runner_state")=="RESULT_PUSHED" else 1)
except Exception: sys.exit(1)
PY
}
set_result_field() { python3 - .codex/RESULT.md "$1" "$2" <<'PY'
import re,sys
p,key,value=sys.argv[1:]; s=open(p).read(); pattern=r'(?m)^- '+re.escape(key)+r':.*$'
replacement='- %s: `%s`' % (key,value)
if not re.search(pattern,s): raise SystemExit('missing RESULT field: '+key)
open(p,'w').write(re.sub(pattern,replacement,s,count=1))
PY
}

[[ $(id -un) == nnv ]] || die 'must run as nnv, never root'
[[ -x $CODEX && -d $REPO/.git ]] || die 'missing Codex executable or repository'
cd "$REPO"
if $DRY_RUN; then
  allowed_preflight_worktree && echo 'DRY RUN: preflight allowlist passes; no pull, Codex, audit, commit, push, TASK.md, or RESULT.md changes.' || echo 'DRY RUN: worktree would be blocked outside the sole protected Pine exception.'
  exit 0
fi
mkdir -p "$LOG_DIR" "$LOCK_DIR"; chmod 700 "$STATE_DIR" "$LOG_DIR" "$LOCK_DIR"
exec 9>"$LOCK_DIR/runner.lock"; flock -n 9 || { echo 'msm_runner: lock held; exiting successfully'; exit 0; }
allowed_preflight_worktree || { state BLOCKED_DIRTY_WORKTREE '' '' '' "$(now)" "$(git rev-parse HEAD)" "$(git rev-parse HEAD)" '' 0 'only the exact protected Pine modification may be dirty before pull'; exit 0; }
git pull --ff-only origin main || { state FAILED '' '' '' "$(now)" "$(git rev-parse HEAD)" "$(git rev-parse HEAD)" '' 1 'git pull --ff-only failed'; exit 1; }
allowed_preflight_worktree || { state BLOCKED_DIRTY_WORKTREE '' '' '' "$(now)" "$(git rev-parse HEAD)" "$(git rev-parse HEAD)" '' 0 'worktree changed outside protected Pine after pull'; exit 0; }
status=$(field status); task_id=$(field task_id); start_sha=$(git rev-parse HEAD)
[[ $status == READY && -n $task_id ]] || { state FAILED "$task_id" '' '' "$(now)" "$start_sha" "$start_sha" '' 1 'TASK.md requires exact READY status and a task_id'; exit 1; }
task_hash=$(sha256sum .codex/TASK.md | awk '{print $1}')
retry_consumed=false
if consume_retry; then retry_consumed=true; echo 'msm_runner: consumed one explicit retry request'; fi
if ! $retry_consumed && result_pushed; then echo 'msm_runner: completed task ID and hash already recorded; skipping'; exit 0; fi
started=$(now); pine_before=$(sha256sum "$PINE" | awk '{print $1}'); stamp=$(date -u +%Y%m%dT%H%M%SZ)
jsonl="$LOG_DIR/${task_id}-${stamp}.jsonl"; final="$LOG_DIR/${task_id}-${stamp}.final.txt"; stderr="$LOG_DIR/${task_id}-${stamp}.stderr.log"; summary="$LOG_DIR/${task_id}-${stamp}.summary.log"
printf '%s task=%s phase=codex start=%s\n' "$(now)" "$task_id" "$start_sha" | tee -a "$summary"
state RUNNING "$task_id" "$task_hash" "$started" '' "$start_sha" "$start_sha" '' 0 ''
prompt="Execute the active READY task in .codex/TASK.md completely. Read AGENTS.md, PROJECT_INSTRUCTIONS.md, and .codex/TASK.md first. Modify only repository files required by the task. Do not run Git mutation or network synchronization commands: do not run git pull, git add, git commit, or git push. Do not touch the protected Pine file $PINE. Write/update .codex/RESULT.md with task ID, tests, changed files, and task_status IMPLEMENTED_AWAITING_AUDIT. Leave all changes uncommitted for the shell runner."
set +e; timeout 4h "$CODEX" exec --json -o "$final" -m gpt-5.6-terra -c 'model_reasoning_effort="medium"' -c 'approval_policy="never"' -s workspace-write -C "$REPO" "$prompt" >"$jsonl" 2>"$stderr"; code=$?; set -e
ended=$(now)
if ((code)); then state FAILED "$task_id" "$task_hash" "$started" "$ended" "$start_sha" "$(git rev-parse HEAD)" '' "$code" "Codex failed; see $stderr"; exit "$code"; fi
verify_post_codex
diff_hash=$(worktree_hash); printf '%s task=%s phase=audit diff=%s\n' "$(now)" "$task_id" "$diff_hash" | tee -a "$summary"
state WAITING_AUDIT "$task_id" "$task_hash" "$started" "$ended" "$start_sha" "$(git rev-parse HEAD)" '' 0 ''
"$REPO/automation/msm_audit.sh" "$task_id" "$task_hash" "$start_sha" "$diff_hash"
audit_status=$(python3 - "$STATE_DIR/audit.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); print(d['audit_status']); print(str(d['technical_pass']).lower())
PY
)
audit_kind=$(sed -n '1p' <<<"$audit_status"); technical=$(sed -n '2p' <<<"$audit_status")
if [[ $audit_kind != PASS && ! ($audit_kind == USER_DECISION_REQUIRED && $technical == true) ]]; then
  printf '%s task=%s phase=stop audit=%s technical=%s\n' "$(now)" "$task_id" "$audit_kind" "$technical" | tee -a "$summary"; exit 0
fi
verify_post_codex; set_result_field implementation_commit_sha PENDING_SHELL_COMMIT; set_result_field implementation_push_status PENDING_SHELL_PUSH; set_result_field result_commit_status PENDING_SHELL_RESULT_COMMIT
mapfile -t paths < <(tracked_dirty_paths | sort -u | while IFS= read -r p; do [[ -n $p && $p != "$PINE" ]] && printf '%s\n' "$p"; done)
(( ${#paths[@]} > 0 )) || die 'no paths to stage after audit'
git add -- "${paths[@]}"; git diff --cached --quiet -- "$PINE" && ! git diff --cached --name-only | grep -Eq '^(experiments/|docs/|MEMORY\.md$)' || die 'staged protected or forbidden path'
git commit -m "$(field commit_message)"; implementation_sha=$(git rev-parse HEAD); git push origin main
set_result_field implementation_commit_sha "$implementation_sha"; set_result_field implementation_push_status 'PUSHED origin/main'; set_result_field result_commit_status PENDING_SHELL_RESULT_COMMIT
git add -- .codex/RESULT.md; git commit -m "codex: record result $task_id"; result_sha=$(git rev-parse HEAD); git push origin main
state RESULT_PUSHED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$result_sha" "$audit_kind" 0 ''
printf '%s task=%s phase=complete implementation=%s result=%s\n' "$(now)" "$task_id" "$implementation_sha" "$result_sha" | tee -a "$summary"
