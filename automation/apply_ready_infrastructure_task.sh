#!/usr/bin/env bash
set -Eeuo pipefail

REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}
RUN_USER=${MSM_RUN_USER:-nnv}
CODEX=${MSM_CODEX:-/home/nnv/.local/bin/codex}
TIMER=msm-codex-runner.timer
SERVICE=msm-codex-runner.service
TASK=.codex/TASK.md
PINE=experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
LOG_ROOT=${MSM_BOOTSTRAP_LOG_DIR:-/home/nnv/.local/state/msm-runner/bootstrap}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG_DIR="$LOG_ROOT/$STAMP"

fail(){ echo "BOOTSTRAP_FAILED: $*" >&2; exit 1; }
field(){ sed -nE "s/^- $1: *\`?([^\`[:space:]]+)\`? *$/\1/p" "$REPO/$TASK" | head -n1; }

[[ $(id -u) -eq 0 ]] || fail "run with sudo"
[[ -d $REPO/.git ]] || fail "repository not found: $REPO"
[[ -x $CODEX ]] || fail "Codex not executable: $CODEX"
install -d -m 700 -o "$RUN_USER" -g "$RUN_USER" "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/bootstrap.log") 2>&1

echo "[1/10] Stop timer"
was_enabled=$(systemctl is-enabled "$TIMER" 2>/dev/null || true)
systemctl stop "$TIMER" || true

cleanup(){
  rc=$?
  if (( rc != 0 )); then
    echo "Bootstrap failed with rc=$rc; restoring timer state"
    if [[ $was_enabled == enabled ]]; then systemctl enable --now "$TIMER" || true; fi
  fi
}
trap cleanup EXIT

echo "[2/10] Repository preflight"
cd "$REPO"
status=$(sudo -u "$RUN_USER" git status --porcelain=v1 --untracked-files=all)
while IFS= read -r line; do
  [[ -z $line ]] && continue
  [[ ${line:0:2} == ' M' && ${line:3} == "$PINE" ]] || fail "unexpected dirty path before pull: $line"
done <<< "$status"
pine_before=$(sha256sum "$PINE" | awk '{print $1}')
sudo -u "$RUN_USER" git diff --cached --quiet -- "$PINE" || fail "protected Pine is staged"

echo "[3/10] Pull latest main"
sudo -u "$RUN_USER" git pull --ff-only origin main
[[ $(field status) == READY ]] || fail "TASK is not READY"
[[ $(field infrastructure_maintenance) == true ]] || fail "TASK is not infrastructure_maintenance=true"
task_id=$(field task_id); [[ -n $task_id ]] || fail "missing task_id"
commit_message=$(field commit_message); [[ -n $commit_message ]] || fail "missing commit_message"
start_sha=$(sudo -u "$RUN_USER" git rev-parse HEAD)

echo "Active task: $task_id"

echo "[4/10] Execute Codex"
sudo -u "$RUN_USER" "$CODEX" exec \
  --json \
  -o "$LOG_DIR/codex.final.txt" \
  -m gpt-5.6-terra \
  -c 'model_reasoning_effort="medium"' \
  -c 'approval_policy="never"' \
  -s workspace-write \
  -C "$REPO" \
  "Execute the active READY infrastructure task in .codex/TASK.md completely. Read AGENTS.md, PROJECT_INSTRUCTIONS.md, the task, and all relevant automation files first. Modify only files explicitly listed under Allowed changes. Do not modify .git, do not run git pull/add/commit/push, sudo, systemctl, or installation commands. Do not touch docs/DEFINITIONS.md or the protected EXP009A_START_REVIEW.pine. Run every validation required by the task, write its result report, and leave edits unstaged." \
  > "$LOG_DIR/codex.jsonl" \
  2> "$LOG_DIR/codex.stderr.log"

echo "[5/10] Validate worktree and task allowlist"
[[ $(sha256sum "$PINE" | awk '{print $1}') == "$pine_before" ]] || fail "protected Pine changed"
sudo -u "$RUN_USER" git diff --cached --quiet || fail "Codex staged files"
sudo -u "$RUN_USER" git diff --check

mapfile -t allowed < <(python3 - "$TASK" <<'PY'
import re,sys
s=open(sys.argv[1],encoding='utf-8').read().splitlines(); active=False
for line in s:
    if line.strip().lower() == '## allowed changes': active=True; continue
    if active and line.startswith('## '): break
    if active:
        m=re.match(r'^- `([^`]+)`\s*$',line.strip())
        if m: print(m.group(1))
PY
)
((${#allowed[@]})) || fail "Allowed changes section is empty or unparsable"
mapfile -t changed < <(sudo -u "$RUN_USER" bash -c 'git diff --name-only; git ls-files --others --exclude-standard' | sort -u)
((${#changed[@]})) || fail "Codex produced no changes"
for p in "${changed[@]}"; do
  [[ $p == "$PINE" ]] && continue
  ok=false
  for a in "${allowed[@]}"; do [[ $p == "$a" ]] && ok=true; done
  $ok || fail "changed path outside task allowlist: $p"
done

for f in automation/*.sh; do bash -n "$f"; done
[[ -f automation/install.sh ]] || fail "installer missing"
bash automation/install.sh --dry-run

echo "[6/10] Commit implementation"
for p in "${changed[@]}"; do
  [[ $p == "$PINE" ]] && continue
  sudo -u "$RUN_USER" git add -- "$p"
done
sudo -u "$RUN_USER" git diff --cached --check
sudo -u "$RUN_USER" git commit -m "$commit_message"
implementation_sha=$(sudo -u "$RUN_USER" git rev-parse HEAD)

echo "[7/10] Close TASK automatically"
python3 - "$TASK" "$implementation_sha" <<'PY'
import datetime,re,sys
p,sha=sys.argv[1:]; s=open(p,encoding='utf-8').read()
s,n=re.subn(r'(?m)^- status: `READY`$', '- status: `COMPLETED`', s, count=1)
assert n==1
stamp=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
if '- completed_at:' not in s:
    s=s.replace('- published_at:', f'- completed_at: `{stamp}`\n- published_at:',1)
if '- completion_commit:' not in s:
    s=s.replace('- target_branch:', f'- completion_commit: `{sha}`\n- target_branch:',1)
open(p,'w',encoding='utf-8').write(s)
PY
sudo -u "$RUN_USER" git add -- "$TASK"
sudo -u "$RUN_USER" git commit -m "$task_id complete"
closure_sha=$(sudo -u "$RUN_USER" git rev-parse HEAD)
sudo -u "$RUN_USER" git push origin main

echo "[8/10] Install and enable"
bash automation/install.sh --enable-now

echo "[9/10] Verify installed copies and service"
for f in msm_runner.sh msm_audit.sh msm_correct.sh; do
  cmp -s "automation/$f" "/usr/local/lib/msm-runner/$f" || fail "installed copy mismatch: $f"
done
systemctl is-enabled --quiet "$TIMER" || fail "timer not enabled"
systemctl is-active --quiet "$TIMER" || fail "timer not active"
systemctl start "$SERVICE"
sleep 3
systemctl is-failed --quiet "$SERVICE" && fail "runner service failed"
state=/home/nnv/.local/state/msm-runner/state.json
[[ -s $state ]] || fail "state.json missing"
python3 - "$state" <<'PY'
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('runner_state') in {'NO_ACTIVE_TASK','RESULT_PUSHED','USER_DECISION_REQUIRED'}
print('runner_state='+x['runner_state'])
PY

echo "[10/10] Final repository protection check"
final_status=$(sudo -u "$RUN_USER" git status --porcelain=v1 --untracked-files=all)
while IFS= read -r line; do
  [[ -z $line ]] && continue
  [[ ${line:0:2} == ' M' && ${line:3} == "$PINE" ]] || fail "unexpected final dirty path: $line"
done <<< "$final_status"

trap - EXIT
echo "BOOTSTRAP_OK"
echo "task_id=$task_id"
echo "start_sha=$start_sha"
echo "implementation_sha=$implementation_sha"
echo "closure_sha=$closure_sha"
echo "logs=$LOG_DIR"
