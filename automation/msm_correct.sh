#!/usr/bin/env bash
# Exactly one Codex correction process per invocation; runner calls only R1/R2.
set -Eeuo pipefail
REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; CODEX=${MSM_CODEX:-/home/nnv/.local/bin/codex}; STATE_DIR=${MSM_STATE_DIR:-/home/nnv/.local/state/msm-runner}; LOG_DIR="$STATE_DIR/logs"
task_id=${1:?}; task_hash=${2:?}; start=${3:?}; attempt=${4:?}; diff_hash=${5:?}; audit_path=${6:?}; [[ $attempt == 1 || $attempt == 2 ]]||{ echo 'msm_correct: attempt must be R1 or R2' >&2;exit 2; }
evidence=$(python3 - "$audit_path" "$task_id" "$attempt" "$task_hash" "$start" "$diff_hash" "$STATE_DIR/audits" <<'PY'
import json,os,sys
p,t,a,h,s,d,root=sys.argv[1:]
try:
 real=os.path.realpath(p); audit_root=os.path.realpath(root)
 assert os.path.isfile(real) and os.path.commonpath((real,audit_root)) == audit_root
 x=json.load(open(real)); need={'task_id','original_task_id','attempt','task_hash','starting_commit','worktree_diff_hash','audit_status','technical_pass','research_decision_required','blocking_findings','warnings','recommended_action','finished_at'}
 assert set(x) == need
 assert (x['task_id'],x['original_task_id'],x['attempt'],x['task_hash'],x['starting_commit'],x['worktree_diff_hash']) == (t,t,int(a)-1,h,s,d)
 assert x['audit_status'] == 'TECHNICAL_CORRECTION_REQUIRED' and x['technical_pass'] is False
 assert isinstance(x['blocking_findings'],list) and x['blocking_findings']
 print(json.dumps({'blocking_findings':x['blocking_findings'],'recommended_action':x['recommended_action']},sort_keys=True))
except Exception as e: raise SystemExit('invalid correction audit evidence: %s' % e)
PY
) || exit $?
mkdir -p "$LOG_DIR";chmod 700 "$STATE_DIR" "$LOG_DIR";stamp=$(date -u +%Y%m%dT%H%M%SZ);out="$LOG_DIR/${task_id}-correction-R${attempt}-${stamp}.final.txt"
prompt="Perform exactly one technical correction attempt R$attempt for task $task_id. The supplied audit evidence is $audit_path for worktree diff hash $diff_hash. Fix only these exact audit findings and follow its recommended action: $evidence. Work only within the original allowlist. Do not restart implementation, invoke another Codex process, write .codex/RESULT.md, or run git pull, git add, git commit, git push, or Git mutation/network synchronization commands. Git mutation is blocked by the read-only .git mount. Leave edits unstaged."
timeout 4h bwrap --die-with-parent --ro-bind / / --bind "$REPO" "$REPO" --ro-bind "$REPO/.git" "$REPO/.git" --bind "$STATE_DIR" "$STATE_DIR" --proc /proc --dev /dev "$CODEX" exec --json -o "$out" -m gpt-5.6-terra -c 'approval_policy="never"' -s workspace-write -C "$REPO" "$prompt" >"${out%.final.txt}.jsonl" 2>"${out%.final.txt}.stderr.log"
