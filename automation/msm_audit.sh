#!/usr/bin/env bash
set -Eeuo pipefail
REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; CODEX=${MSM_CODEX:-/home/nnv/.local/bin/codex}; STATE_DIR=${MSM_STATE_DIR:-/home/nnv/.local/state/msm-runner}; LOG_DIR="$STATE_DIR/logs"; AUDIT_FILE=${MSM_AUDIT_FILE:-"$STATE_DIR/audit.json"}
task_id=${1:?}; original_task_id=${2:?}; attempt=${3:?}; task_hash=${4:?}; starting_commit=${5:?}; worktree_diff_hash=${6:?}
mkdir -p "$LOG_DIR"; chmod 700 "$STATE_DIR" "$LOG_DIR"; stamp=$(date -u +%Y%m%dT%H%M%SZ); raw="$LOG_DIR/${task_id}-audit-R${attempt}-${stamp}.final.json"
fail(){ python3 - "$AUDIT_FILE" "$task_id" "$original_task_id" "$attempt" "$task_hash" "$starting_commit" "$worktree_diff_hash" "$1" <<'PY'
import json,os,sys,datetime
p,t,o,a,h,s,d,r=sys.argv[1:];x={'task_id':t,'original_task_id':o,'attempt':int(a),'task_hash':h,'starting_commit':s,'worktree_diff_hash':d,'audit_status':'AUDIT_FAILED','technical_pass':False,'research_decision_required':False,'blocking_findings':[r],'warnings':[],'recommended_action':'stop and inspect runtime logs','finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')};q=p+'.tmp.%d'%os.getpid();open(q,'w').write(json.dumps(x,indent=2,sort_keys=True)+'\n');os.replace(q,p)
PY
}
prompt="Independently audit uncommitted attempt R$attempt for task $task_id. Bubblewrap mounts the repository and .git read-only: inspect TASK, actual diff/status, tests, artifacts, and constraints. Do not modify files, write .codex, or run Git mutation/network synchronization commands. Return ONLY strict JSON with exactly task_id, original_task_id, attempt, task_hash, starting_commit, worktree_diff_hash, audit_status, technical_pass, research_decision_required, blocking_findings, warnings, recommended_action, finished_at. Values equal $task_id, $original_task_id, $attempt, $task_hash, $starting_commit, $worktree_diff_hash."
set +e; timeout 2h bwrap --die-with-parent --ro-bind / / --ro-bind "$REPO" "$REPO" --bind "$STATE_DIR" "$STATE_DIR" --proc /proc --dev /dev "$CODEX" exec --json -o "$raw" -m gpt-5.6-terra -c 'approval_policy="never"' -s read-only -C "$REPO" "$prompt" >"${raw%.final.json}.jsonl" 2>"${raw%.final.json}.stderr.log";code=$?;set -e;((!code))||{ fail "auditor exit $code";exit "$code"; }
python3 - "$raw" "$AUDIT_FILE" "$task_id" "$original_task_id" "$attempt" "$task_hash" "$starting_commit" "$worktree_diff_hash" <<'PY'
import json,os,sys
raw,out,t,o,a,h,s,d=sys.argv[1:];need={'task_id','original_task_id','attempt','task_hash','starting_commit','worktree_diff_hash','audit_status','technical_pass','research_decision_required','blocking_findings','warnings','recommended_action','finished_at'}
try:
 x=json.load(open(raw));assert set(x)==need;assert (x['task_id'],x['original_task_id'],x['attempt'],x['task_hash'],x['starting_commit'],x['worktree_diff_hash'])==(t,o,int(a),h,s,d);assert x['audit_status'] in {'PASS','USER_DECISION_REQUIRED','TECHNICAL_CORRECTION_REQUIRED','AUDIT_FAILED'};assert isinstance(x['technical_pass'],bool) and isinstance(x['research_decision_required'],bool) and isinstance(x['blocking_findings'],list) and isinstance(x['warnings'],list)
except Exception as e:raise SystemExit('invalid auditor JSON: %s'%e)
q=out+'.tmp.%d'%os.getpid();open(q,'w').write(json.dumps(x,indent=2,sort_keys=True)+'\n');os.replace(q,out)
PY
