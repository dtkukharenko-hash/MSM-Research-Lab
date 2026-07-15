#!/usr/bin/env bash
set -Eeuo pipefail
REPO=/home/nnv/MSM-Research-Lab; CODEX=/home/nnv/.local/bin/codex; STATE_DIR=/home/nnv/.local/state/msm-runner
STATE_FILE="$STATE_DIR/state.json"; LOG_DIR="$STATE_DIR/logs"; AUDIT_FILE="$STATE_DIR/audit.json"
task_id=${1:?task_id required}; task_hash=${2:?task_hash required}; starting_commit=${3:?starting_commit required}; worktree_diff_hash=${4:?worktree_diff_hash required}
now(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
write_failure(){ python3 - "$AUDIT_FILE" "$task_id" "$task_hash" "$starting_commit" "$worktree_diff_hash" "$1" <<'PY'
import json,os,sys
p,task,digest,start,snapshot,reason=sys.argv[1:]; d={"task_id":task,"task_hash":digest,"starting_commit":start,"worktree_diff_hash":snapshot,"audit_status":"AUDIT_FAILED","technical_pass":False,"research_decision_required":False,"blocking_findings":[reason],"warnings":[],"recommended_action":"inspect audit logs and rerun audit","finished_at":__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat().replace('+00:00','Z')}
t=p+'.tmp.%d'%os.getpid(); open(t,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n'); os.replace(t,p)
PY
}
update_state(){ python3 - "$STATE_FILE" "$AUDIT_FILE" <<'PY'
import json,os,sys
p,a=sys.argv[1:]
try: d=json.load(open(p))
except FileNotFoundError: d={}
x=json.load(open(a)); s=x['audit_status']; d.update(audit_status=s,finished_at=x['finished_at'],failure_reason='')
d['runner_state']={'PASS':'AUDIT_PASS','USER_DECISION_REQUIRED':'WAITING_USER_DECISION','TECHNICAL_CORRECTION_REQUIRED':'TECHNICAL_CORRECTION_REQUIRED'}.get(s,'AUDIT_FAILED')
if s=='AUDIT_FAILED': d['failure_reason']='audit failed'
t=p+'.tmp.%d'%os.getpid(); open(t,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n'); os.replace(t,p)
PY
}
[[ $(id -un) == nnv && -x $CODEX ]] || { echo 'msm_audit: must run as nnv with Codex available' >&2; exit 1; }
mkdir -p "$LOG_DIR" "$STATE_DIR"; chmod 700 "$STATE_DIR" "$LOG_DIR"
raw="$LOG_DIR/${task_id}-audit-$(date -u +%Y%m%dT%H%M%SZ).final.json"; jsonl="${raw%.final.json}.jsonl"; stderr="${raw%.final.json}.stderr.log"
prompt="Independently audit the uncommitted worktree for task $task_id in $REPO. No implementation or result commit exists yet. Read TASK, RESULT, git diff/status, tests and artifacts. Read-only: do not modify files, commit, push, pull, fetch, or otherwise synchronize Git/network state. Return ONLY JSON with exactly task_id, task_hash, starting_commit, worktree_diff_hash, audit_status, technical_pass, research_decision_required, blocking_findings, warnings, recommended_action, finished_at. Identifiers must equal $task_id $task_hash $starting_commit $worktree_diff_hash. audit_status must be PASS, USER_DECISION_REQUIRED, TECHNICAL_CORRECTION_REQUIRED, or AUDIT_FAILED."
set +e; timeout 2h "$CODEX" exec --json -o "$raw" -m gpt-5.6-terra -c 'model_reasoning_effort="medium"' -c 'approval_policy="never"' -s read-only -C "$REPO" "$prompt" >"$jsonl" 2>"$stderr"; code=$?; set -e
if ((code)); then write_failure "auditor exit $code; see $stderr"; update_state; exit "$code"; fi
if ! python3 - "$raw" "$AUDIT_FILE" "$task_id" "$task_hash" "$starting_commit" "$worktree_diff_hash" <<'PY'
import json,os,sys
raw,out,task,digest,start,snapshot=sys.argv[1:]
try:
 d=json.load(open(raw)); required={'task_id','task_hash','starting_commit','worktree_diff_hash','audit_status','technical_pass','research_decision_required','blocking_findings','warnings','recommended_action','finished_at'}
 assert set(d)==required and (d['task_id'],d['task_hash'],d['starting_commit'],d['worktree_diff_hash'])==(task,digest,start,snapshot)
 assert d['audit_status'] in {'PASS','USER_DECISION_REQUIRED','TECHNICAL_CORRECTION_REQUIRED','AUDIT_FAILED'} and isinstance(d['technical_pass'],bool) and isinstance(d['research_decision_required'],bool) and isinstance(d['blocking_findings'],list) and isinstance(d['warnings'],list)
except Exception as e: print('invalid auditor JSON:',e,file=sys.stderr); raise SystemExit(1)
t=out+'.tmp.%d'%os.getpid(); open(t,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n'); os.replace(t,out)
PY
then write_failure 'auditor final response was not valid required JSON'; update_state; exit 1; fi
update_state
