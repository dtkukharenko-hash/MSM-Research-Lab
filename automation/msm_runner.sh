#!/usr/bin/env bash
# Installed-copy MSM runner. Shell owns Git and result metadata.
set -Eeuo pipefail
REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; CODEX=${MSM_CODEX:-/home/nnv/.local/bin/codex}
LIB_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd); AUDITOR="$LIB_DIR/msm_audit.sh"; CORRECTOR="$LIB_DIR/msm_correct.sh"
STATE_DIR=${MSM_STATE_DIR:-/home/nnv/.local/state/msm-runner}; LOG_DIR="$STATE_DIR/logs"; LOCK_DIR="$STATE_DIR/locks"; STATE_FILE="$STATE_DIR/state.json"
PINE=experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
DRY_RUN=false; [[ ${1:-} == --dry-run ]] && DRY_RUN=true
now(){ date -u +%Y-%m-%dT%H:%M:%SZ; }; die(){ printf 'msm_runner: %s\n' "$*" >&2; exit 1; }; gitc(){ git -C "$REPO" "$@"; }
write_state() { python3 - "$STATE_FILE" "$@" <<'PY'
import json,os,sys
p,state,task,digest,started,finished,first,last,audit,code,reason,attempt=sys.argv[1:]
try: d=json.load(open(p))
except (FileNotFoundError,json.JSONDecodeError): d={}
d.update({'runner_state':state,'task_id':task,'original_task_id':task or d.get('original_task_id',''),'task_hash':digest,'started_at':started or d.get('started_at',''),'finished_at':finished,'starting_commit':first,'last_commit':last,'audit_status':audit,'exit_code':int(code),'failure_reason':reason,'attempt':int(attempt),'runner_pid':os.getpid()})
d.setdefault('attempt_history',[]);d.setdefault('blocking_findings',[]);d.setdefault('warnings',[])
t=p+'.tmp.%d'%os.getpid()
with open(t,'w') as f: json.dump(d,f,indent=2,sort_keys=True); f.write('\n')
os.replace(t,p)
PY
}
state(){ write_state "$1" "${2:-}" "${3:-}" "${4:-}" "${5:-}" "${6:-}" "${7:-}" "${8:-}" "${9:-0}" "${10:-}" "${11:-0}"; }
task_field(){ sed -nE "s/^- $1: *\`?([^\`[:space:]]+)\`? *$/\1/p" "$REPO/.codex/TASK.md"|head -n1; }
is_infra(){ [[ $(task_field infrastructure_maintenance) == true ]]; }
dirty_paths(){ gitc diff --name-only; gitc diff --cached --name-only; gitc ls-files --others --exclude-standard; }
worktree_hash(){ { gitc diff --binary; gitc diff --cached --binary; while IFS= read -r p; do printf '\nUNTRACKED:%s\n' "$p"; sha256sum "$REPO/$p"; done < <(gitc ls-files --others --exclude-standard|sort); }|sha256sum|awk '{print $1}'; }
only_pine(){ local x xy p; while IFS= read -r x; do [[ -z $x ]]&&continue; xy=${x:0:2}; p=${x:3}; [[ $xy == ' M' && $p == "$PINE" ]]||return 1; done < <(gitc status --porcelain=v1 --untracked-files=all); }
allowlist(){ if is_infra; then printf '%s\n' 'automation/**' '.codex/RESULT.md'; elif [[ -f $REPO/.codex/ALLOWLIST.txt ]]; then sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' "$REPO/.codex/ALLOWLIST.txt"; printf '%s\n' '.codex/RESULT.md'; else return 1; fi; }
allowed(){ local p=$1 g; while IFS= read -r g; do [[ $p == $g ]]&&return 0; done < <(allowlist); return 1; }
normal_infra_path(){ case "$1" in automation/msm_runner.sh|automation/msm_audit.sh|automation/msm_correct.sh|automation/install.sh|automation/runner.service|automation/runner.timer) return 0;; *) return 1;; esac; }
verify(){ local p; [[ $(sha256sum "$REPO/$PINE"|awk '{print $1}') == "$pine_before" ]]||die 'protected Pine hash changed'; gitc diff --cached --quiet -- "$PINE"||die 'protected Pine staged'; gitc diff --cached --quiet||die 'Codex left staged changes'; while IFS= read -r p; do [[ -z $p || $p == "$PINE" ]]&&continue; ! is_infra&&normal_infra_path "$p"&&die "normal task cannot modify infrastructure path: $p"; [[ $p != docs/DEFINITIONS.md && $p != experiments/* && $p != docs/* && $p != MEMORY.md ]]||die "forbidden path changed: $p"; allowed "$p"||die "outside allowlist: $p"; done < <(dirty_paths|sort -u); }
result_pushed(){ python3 - "$STATE_FILE" "$task_id" "$task_hash" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1]));sys.exit(0 if d.get('runner_state')=='RESULT_PUSHED' and d.get('task_id')==sys.argv[2] and d.get('task_hash')==sys.argv[3] else 1)
except Exception:sys.exit(1)
PY
}
consume_retry(){ python3 - "$STATE_FILE" "$task_id" "$task_hash" <<'PY'
import datetime,json,os,sys
p,task,digest=sys.argv[1:]
try:d=json.load(open(p))
except (FileNotFoundError,json.JSONDecodeError):raise SystemExit(1)
if not(d.get('retry_requested') is True and d.get('task_id')==task and d.get('task_hash')==digest):raise SystemExit(1)
d['retry_requested']=False;d['retry_consumed_at']=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
t=p+'.tmp.%d'%os.getpid();open(t,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n');os.replace(t,p)
PY
}
route(){ case "$1:$2:$3" in PASS:true:*) echo COMMIT_PASS;; USER_DECISION_REQUIRED:true:*) echo COMMIT_USER_DECISION_REQUIRED;; USER_DECISION_REQUIRED:false:*) echo STOP_USER_DECISION_REQUIRED;; TECHNICAL_CORRECTION_REQUIRED:*:0) echo CORRECT_R1;; TECHNICAL_CORRECTION_REQUIRED:*:1) echo CORRECT_R2;; TECHNICAL_CORRECTION_REQUIRED:*:2) echo STOP_USER_DECISION_REQUIRED;; AUDIT_FAILED:*) echo STOP_AUDIT_FAILED;; *) echo STOP_AUDIT_FAILED;; esac; }
validate_correction_audit(){ python3 - "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$STATE_DIR/audits" <<'PY'
import json,os,sys
p,t,o,a,h,s,d,root=sys.argv[1:]
try:
 real=os.path.realpath(p); audit_root=os.path.realpath(root)
 assert os.path.isfile(real) and os.path.commonpath((real,audit_root)) == audit_root
 x=json.load(open(real)); need={'task_id','original_task_id','attempt','task_hash','starting_commit','worktree_diff_hash','audit_status','technical_pass','research_decision_required','blocking_findings','warnings','recommended_action','finished_at'}
 assert set(x) == need
 assert (x['task_id'],x['original_task_id'],x['attempt'],x['task_hash'],x['starting_commit'],x['worktree_diff_hash']) == (t,o,int(a),h,s,d)
 assert x['audit_status'] == 'TECHNICAL_CORRECTION_REQUIRED' and x['technical_pass'] is False
 assert isinstance(x['blocking_findings'],list) and x['blocking_findings']
except Exception as e: raise SystemExit('invalid correction audit evidence: %s' % e)
PY
}
run_writer(){ local a=$1 kind=$2 stamp out jsonl err prompt code; stamp=$(date -u +%Y%m%dT%H%M%SZ); out="$LOG_DIR/${task_id}-${kind}-R${a}-${stamp}.final.txt"; jsonl="${out%.final.txt}.jsonl"; err="${out%.final.txt}.stderr.log"; prompt="Execute $kind attempt R$a for active task $task_id. Read AGENTS.md, PROJECT_INSTRUCTIONS.md, and .codex/TASK.md. Modify only the original task allowlist. Do not write .codex/RESULT.md; do not run git pull, git add, git commit, git push, or other Git mutation/network synchronization commands. Git mutation is blocked by the read-only .git mount. Leave edits unstaged."; state RUNNING "$task_id" "$task_hash" "$started" '' "$start_sha" "$(gitc rev-parse HEAD)" '' 0 '' "$a"; set +e; timeout 4h bwrap --die-with-parent --ro-bind / / --bind "$REPO" "$REPO" --ro-bind "$REPO/.git" "$REPO/.git" --bind "$STATE_DIR" "$STATE_DIR" --proc /proc --dev /dev "$CODEX" exec --json -o "$out" -m gpt-5.6-terra -c 'model_reasoning_effort="medium"' -c 'approval_policy="never"' -s workspace-write -C "$REPO" "$prompt" >"$jsonl" 2>"$err"; code=$?; set -e; state RUNNING "$task_id" "$task_hash" "$started" '' "$start_sha" "$(gitc rev-parse HEAD)" '' "$code" "${kind}_R${a}_exit_code=$code" "$a"; return "$code"; }
write_result(){ python3 - "$REPO/.codex/RESULT.md" "$task_id" "$task_hash" "$start_sha" "$1" <<'PY'
import json,sys
p,task,digest,start,audit=sys.argv[1:];a=json.load(open(audit))
x={'task_id':task,'task_status':a['audit_status'],'implementation_commit_sha':'PENDING_SHELL_COMMIT','implementation_push_status':'PENDING_SHELL_PUSH','result_commit_status':'PENDING_SHELL_RESULT_COMMIT','summary':'Shell-generated from verified runtime audit data.','created_files':'','modified_files':'','tests_run':'See runtime audit record.','acceptance_results':a['audit_status'],'metrics':'','warnings':'; '.join(a['warnings']),'final_git_status':'pending shell commit','unrelated_changes_preserved':'protected Pine preserved'}
with open(p,'w') as f:
 for k,v in x.items():f.write('- %s: `%s`\n'%(k,str(v).replace('`',"'")))
PY
}
set_result(){ python3 - "$REPO/.codex/RESULT.md" "$1" "$2" <<'PY'
import re,sys
p,k,v=sys.argv[1:];s=open(p).read();pat=r'(?m)^- '+re.escape(k)+r':.*$';assert re.search(pat,s);open(p,'w').write(re.sub(pat,'- %s: `%s`'%(k,v),s,count=1))
PY
}
if [[ ${1:-} == --simulate-no-task ]];then echo NO_ACTIVE_TASK;exit 0;fi
if [[ ${1:-} == --simulate-duplicate ]];then echo DUPLICATE_COMPLETED_TASK_SKIPPED;exit 0;fi
if [[ ${1:-} == --simulate-route ]];then [[ $# == 4 ]]||die 'usage: --simulate-route STATUS true|false ATTEMPT';route "$2" "$3" "$4";exit 0;fi
if [[ ${1:-} == --simulate-retry ]];then
 f=$(mktemp);task_id=SIM;task_hash=HASH;printf '{"task_id":"SIM","task_hash":"HASH","retry_requested":true}\n'>"$f";STATE_FILE="$f" consume_retry;first=$?;second=0;STATE_FILE="$f" consume_retry||second=$?;grep -Fq '"retry_requested": false' "$f";rm -f "$f";[[ $first == 0 && $second != 0 ]]&&echo 'RETRY_FIRST=CONSUMED RETRY_SECOND=NOT_CONSUMED';exit $?
fi
if [[ ${1:-} == --simulate-correction-gate ]];then
 [[ $# == 8 ]]||die 'usage: --simulate-correction-gate AUDIT TASK ATTEMPT HASH START DIFF STATE_DIR';audit_path=$2;task_id=$3;attempt=$4;task_hash=$5;start_sha=$6;diff_hash=$7;STATE_DIR=$8
 validate_correction_audit "$audit_path" "$task_id" "$task_id" "$attempt" "$task_hash" "$start_sha" "$diff_hash" >/dev/null 2>&1||{ echo AUDIT_FAILED;exit 0; }
 echo "$(route TECHNICAL_CORRECTION_REQUIRED false "$attempt")";exit 0
fi
[[ $(id -un) == nnv && -x $CODEX && -d $REPO/.git ]]||die 'must run as nnv with Codex and repository'
cd "$REPO"
if $DRY_RUN;then only_pine&&echo 'DRY RUN: preflight passes; no pull, task parse, Codex, audit, result, commit, or push.'||echo 'DRY RUN: preflight would block worktree.';exit 0;fi
mkdir -p "$LOG_DIR" "$LOCK_DIR";chmod 700 "$STATE_DIR" "$LOG_DIR" "$LOCK_DIR";exec 9>"$LOCK_DIR/runner.lock";flock -n 9||{ echo 'msm_runner: lock held; exiting successfully';exit 0; }
# No task status, ID, hash, allowlist, or infrastructure decision is read before pull.
only_pine||{ state BLOCKED_DIRTY_WORKTREE '' '' '' "$(now)" "$(gitc rev-parse HEAD)" "$(gitc rev-parse HEAD)" '' 0 'only protected Pine may be dirty' 0;exit 0; }
gitc pull --ff-only origin main||{ state FAILED '' '' '' "$(now)" "$(gitc rev-parse HEAD)" "$(gitc rev-parse HEAD)" '' 1 'git pull --ff-only failed' 0;exit 1; }
only_pine||{ state BLOCKED_DIRTY_WORKTREE '' '' "$(now)" "$(now)" "$(gitc rev-parse HEAD)" "$(gitc rev-parse HEAD)" '' 0 'pull left disallowed dirt' 0;exit 0; }
status=$(task_field status);task_id=$(task_field task_id);task_hash=$(sha256sum .codex/TASK.md|awk '{print $1}');start_sha=$(gitc rev-parse HEAD);started=$(now)
[[ $status == READY ]]||{ state NO_ACTIVE_TASK "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$start_sha" '' 0 'TASK.md absent or not READY' 0;echo NO_ACTIVE_TASK;exit 0; }
[[ -n $task_id ]]||{ state FAILED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$start_sha" '' 1 'READY task missing task_id' 0;exit 1; }
if is_infra;then state MANUAL_BOOTSTRAP_REQUIRED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$start_sha" '' 0 'latest pulled infrastructure task requires manual bootstrap' 0;echo MANUAL_BOOTSTRAP_REQUIRED;exit 0;fi
allowlist >/dev/null||{ state FAILED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$start_sha" '' 1 'normal task has no allowlist' 0;exit 1; }
retry_consumed=false;consume_retry&&retry_consumed=true||true
! $retry_consumed&&result_pushed&&{ echo 'msm_runner: duplicate task ID and hash already pushed; skipping';exit 0; }
pine_before=$(sha256sum "$REPO/$PINE"|awk '{print $1}');state RUNNING "$task_id" "$task_hash" "$started" '' "$start_sha" "$start_sha" '' 0 '' 0
run_writer 0 implementation||{ code=$?;state FAILED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$(gitc rev-parse HEAD)" '' "$code" 'implementation R0 failed' 0;exit "$code";};verify
for attempt in 0 1 2;do
 diff_hash=$(worktree_hash);audit_path="$STATE_DIR/audits/${task_id}-${diff_hash}-R${attempt}.json";mkdir -p "$STATE_DIR/audits";MSM_AUDIT_FILE="$audit_path" "$AUDITOR" "$task_id" "$task_id" "$attempt" "$task_hash" "$start_sha" "$diff_hash"
 read -r audit technical decision < <(python3 - "$audit_path" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]));print(d['audit_status'],str(d['technical_pass']).lower(),str(d['research_decision_required']).lower())
PY
)
 python3 - "$STATE_FILE" "$attempt" "$diff_hash" "$audit_path" "$audit" <<'PY'
import json,os,sys
p,a,h,j,s=sys.argv[1:];d=json.load(open(p));d.setdefault('attempt_history',[]).append({'attempt':'R'+a,'worktree_diff_hash':h,'audit_json_path':j,'audit_status':s});d['blocking_findings']=json.load(open(j))['blocking_findings'];d['warnings']=json.load(open(j))['warnings'];t=p+'.tmp.%d'%os.getpid();open(t,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n');os.replace(t,p)
PY
 next=$(route "$audit" "$technical" "$attempt")
 case $next in COMMIT_PASS|COMMIT_USER_DECISION_REQUIRED) final_status=${next#COMMIT_};break;; STOP_AUDIT_FAILED) state AUDIT_FAILED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$(gitc rev-parse HEAD)" "$audit" 1 'audit failed' "$attempt";exit 1;; STOP_USER_DECISION_REQUIRED) state USER_DECISION_REQUIRED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$(gitc rev-parse HEAD)" "$audit" 0 'user decision required; no correction' "$attempt";exit 0;; CORRECT_R1|CORRECT_R2) next=${next#CORRECT_R};"$CORRECTOR" "$task_id" "$task_hash" "$start_sha" "$next"||die "correction R$next failed";verify;; esac
 case $next in COMMIT_PASS|COMMIT_USER_DECISION_REQUIRED) final_status=${next#COMMIT_};break;; STOP_AUDIT_FAILED) state AUDIT_FAILED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$(gitc rev-parse HEAD)" "$audit" 1 'audit failed' "$attempt";exit 1;; STOP_USER_DECISION_REQUIRED) state USER_DECISION_REQUIRED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$(gitc rev-parse HEAD)" "$audit" 0 'user decision required; no correction' "$attempt";exit 0;; CORRECT_R1|CORRECT_R2) next=${next#CORRECT_R};validate_correction_audit "$audit_path" "$task_id" "$task_id" "$attempt" "$task_hash" "$start_sha" "$diff_hash"||{ state AUDIT_FAILED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$(gitc rev-parse HEAD)" AUDIT_FAILED 1 'audit evidence validation failed' "$attempt";exit 1; };"$CORRECTOR" "$task_id" "$task_hash" "$start_sha" "$next" "$diff_hash" "$audit_path"||die "correction R$next failed";verify;; esac
done
write_result "$audit_path";set_result task_status "$final_status";set_result acceptance_results "$final_status";verify;mapfile -t paths < <(dirty_paths|sort -u|while IFS= read -r p;do [[ -n $p && $p != "$PINE" ]]&&printf '%s\n' "$p";done);((${#paths[@]}))||die 'no files to stage';gitc add -- "${paths[@]}";gitc diff --cached --quiet -- "$PINE"||die 'protected Pine staged'
gitc commit -m "$(task_field commit_message)";implementation_sha=$(gitc rev-parse HEAD);gitc push origin main;set_result implementation_commit_sha "$implementation_sha";set_result implementation_push_status 'PUSHED origin/main';set_result result_commit_status PENDING_SHELL_RESULT_COMMIT;gitc add -- .codex/RESULT.md;gitc commit -m "codex: record result $task_id";result_sha=$(gitc rev-parse HEAD);gitc push origin main;state RESULT_PUSHED "$task_id" "$task_hash" "$started" "$(now)" "$start_sha" "$result_sha" "$final_status" 0 '' "$attempt"
