#!/usr/bin/env bash
set -Eeuo pipefail
REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; PY="$REPO/automation/msm_orchestrator.py"; PINE="$REPO/experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
usage(){ echo 'usage: --offline | --worker-fixture | --mock-cycle --wait SECONDS | --service --test-mode|--production --wait SECONDS | --health' >&2; exit 2; }
offline(){ python3 -B - "$PY" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1]); compile(p.read_text(encoding='utf-8'),str(p),'exec')
PY
bash -n "$REPO/automation/msm_worker.sh" "$REPO/automation/install_orchestrator.sh" "$0"; [[ -s "$PINE" ]]; echo OFFLINE_OK; }
fixture(){ local d=$1; mkdir -p "$d/repo"; printf 'task\n' >"$d/repo/task.md"; printf 'allowed\n' >"$d/repo/allow.txt"; python3 -B - "$d" <<'PY'
import hashlib,json,sys,pathlib
d=pathlib.Path(sys.argv[1]); h=hashlib.sha256((d/'repo/task.md').read_bytes()).hexdigest(); e={'schema_version':'1','task_id':'mock','task_hash':h,'status':'READY','task_path':'task.md','allowlist_path':'allow.txt','created_at':'2026-01-01T00:00:00Z','attempt':0,'max_corrections':2}; (d/'state/queue').mkdir(parents=True); (d/'state/queue/mock.json').write_text(json.dumps(e))
PY
}
worker_fixture(){ local d output runtime
  command -v bwrap >/dev/null || { echo 'bwrap is required for worker fixture' >&2; return 1; }
  d=$(mktemp -d); trap 'rm -rf "$d"' RETURN
  mkdir -p "$d/repo/.git" "$d/bin" "$d/codex-home"
  printf 'task\n' >"$d/repo/task.md"; printf 'allowed\n' >"$d/repo/allow.txt"
  printf '%s\n' '{"protected_pine_sha256":"fixture-pine-hash","preexisting_paths":{}}' >"$d/repo/baseline.json"
  printf '%s\n' 'fixture-credential-never-print' >"$d/codex-home/auth.json"
  printf '%s\n' 'model = "fixture"' >"$d/codex-home/config.toml"
  chmod 600 "$d/codex-home/auth.json" "$d/codex-home/config.toml"
  cat >"$d/bin/codex" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
out=
task= allowlist= outer_sandbox_only=false
while (($#)); do
  case $1 in
    -o) out=$2; shift 2;;
    --dangerously-bypass-approvals-and-sandbox) outer_sandbox_only=true; shift;;
    -s|--sandbox) echo 'worker must not select a nested Codex sandbox' >&2; exit 1;;
    *)
      if [[ $1 == *'Read only task package '* ]]; then
        [[ $1 == *'fixture-pine-hash'* ]]
        task=${1#*Read only task package }; task=${task%% and allowlist *}
        allowlist=${1#* and allowlist }; allowlist=${allowlist%%. Return ONLY JSON:*}
      fi
      shift;;
  esac
done
[[ -n $out ]]
[[ $outer_sandbox_only == true ]]
[[ -r $task && -r $allowlist ]]
[[ $(<"$task") == task && $(<"$allowlist") == allowed ]]
[[ ${CODEX_HOME:?} != "$HOME" ]]
[[ $(<"$CODEX_HOME/auth.json") == fixture-credential-never-print ]]
[[ $(stat -c '%a' "$CODEX_HOME" "$CODEX_HOME/auth.json" "$CODEX_HOME/config.toml") == $'700\n600\n600' ]]
for path in "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME" "$TMPDIR"; do
  touch "$path/runtime-write-check"
done
[[ ! -w "$MSM_REPO/.git" ]]
! touch "$MSM_REPO/.git/worker-fixture-must-not-exist"
printf '%s\n' '{"role":"planner","verdict":"PASS","findings":[],"summary":"runtime initialized"}' >"$out"
SH
  chmod 700 "$d/bin/codex"
  output="$d/result.json"
  MSM_REPO="$d/repo" MSM_CODEX="$d/bin/codex" MSM_CODEX_HOME="$d/codex-home" MSM_STATE_DIR="$d/state" \
    bash "$REPO/automation/msm_worker.sh" --role planner --task "$d/repo/task.md" --allowlist "$d/repo/allow.txt" --baseline-json "$d/repo/baseline.json" --output "$output" >"$d/worker.stdout" 2>"$d/worker.stderr"
  [[ -s $output ]] || { echo 'worker fixture did not preserve output path' >&2; return 1; }
  [[ ! -e "$d/repo/.git/worker-fixture-must-not-exist" ]] || { echo '.git became writable inside worker sandbox' >&2; return 1; }
  runtime=$(find "$d/state/runtime" -type f -name runtime-write-check | wc -l)
  [[ $runtime == 6 ]] || { echo "worker fixture expected six writable runtime paths, got $runtime" >&2; return 1; }
  runtime=$(find "$d/state/runtime" -type f -name auth.json | wc -l)
  [[ $runtime == 1 ]] || { echo "worker fixture expected one private credential copy, got $runtime" >&2; return 1; }
  [[ $(stat -c '%a' "$d/state"/runtime/*/planner/codex "$d/state"/runtime/*/planner/codex/auth.json) == $'700\n600' ]] || { echo 'worker fixture credential modes are unsafe' >&2; return 1; }
  ! rg -q -F 'fixture-credential-never-print' "$output" "${output%.json}.jsonl" "$d/worker.stdout" "$d/worker.stderr" "$d/repo"
  ! rg -q -F "Can't mkdir /tmp/.git: Read-only file system" "$output" "${output%.json}.jsonl" "$d/worker.stdout" "$d/worker.stderr"
  ! rg -q 'failed to initialize in-process app-server client: Read-only file system' "$output" "${output%.json}.jsonl"
  if MSM_REPO="$d/repo" MSM_CODEX="$d/bin/codex" MSM_CODEX_HOME="$d/no-credentials" MSM_STATE_DIR="$d/missing-state" \
    bash "$REPO/automation/msm_worker.sh" --role planner --task "$d/repo/task.md" --allowlist "$d/repo/allow.txt" --output "$d/missing.json" >"$d/missing.stdout" 2>"$d/missing.stderr"; then
    echo 'worker fixture accepted absent credentials' >&2; return 1
  fi
  rg -qx 'Codex credentials are unavailable' "$d/missing.stderr" || { echo 'worker fixture missing-credential failure was not controlled' >&2; return 1; }
  [[ ! -e $d/missing.json && ! -e ${d}/missing.jsonl ]] || { echo 'worker fixture emitted output without credentials' >&2; return 1; }
  ! rg -q -F 'fixture-credential-never-print' "$d/missing.stdout" "$d/missing.stderr"
  printf 'allowed.txt\n' >"$d/repo/allowlist-for-orchestrator.txt"
  python3 -B - "$REPO/automation/msm_orchestrator.py" "$d/repo" <<'PY'
import importlib.util, pathlib, sys
from types import SimpleNamespace
source, repo = map(pathlib.Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('orchestrator_fixture', source)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
module.protected_ok = lambda _: ('fixture-pine-hash', True)
module.status_entries = lambda _: {'outside-allowlist.txt':'??'}
module.path_signature = lambda _, path, code: {'status':code,'sha256':'fixture','mode':0o644}
try:
    module.validate_task_delta(repo, {'allowlist_path': 'allowlist-for-orchestrator.txt','baseline':{'protected_pine_sha256':'fixture-pine-hash','preexisting_paths':{}}})
except RuntimeError as exc:
    assert str(exc) == 'changed path outside allowlist'
else:
    raise AssertionError('orchestrator accepted an out-of-allowlist change')
PY
  echo WORKER_RUNTIME_FIXTURE_OK
}
mock(){ local d; d=$(mktemp -d); trap 'rm -rf "$d"' RETURN
  python3 -B - "$PY" "$d" <<'PY'
import hashlib,json,pathlib,sys,importlib.util
sys.dont_write_bytecode=True
py,d=map(pathlib.Path,sys.argv[1:]); sp=importlib.util.spec_from_file_location('o',py); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
actual_pine=pathlib.Path('/home/nnv/MSM-Research-Lab/experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine'); before=hashlib.sha256(actual_pine.read_bytes()).hexdigest()
def make(name='mock', different=False):
 r=d/name/'repo'; s=d/name/'state'; r.mkdir(parents=True); (r/'task.md').write_text('task '+('different' if different else '')+'\n'); (r/'allow.txt').write_text('allowed\n'); h=hashlib.sha256((r/'task.md').read_bytes()).hexdigest(); e={'schema_version':'1','task_id':name,'task_hash':h,'status':'READY','task_path':'task.md','allowlist_path':'allow.txt','created_at':'2026-01-01T00:00:00Z','attempt':0,'max_corrections':2}; (s/'queue').mkdir(parents=True); m.atomic(s/'queue'/(name+'.json'),e); return r,s
def step(r,s,v=None,bad=False):
 f=next(iter((s/'running').glob('*.json')),None)
 if not f:
  m.cycle(r,s,{'role':'planner','verdict':'PASS','findings':[],'summary':'deterministic mock'})
  return
 e=m.load(f); role=m.ROLES[e['status']]
 if bad: z={'bad':True}
 else: z={'role':role,'verdict':v,'findings':[],'summary':'deterministic mock'}
 e=m.process(r,s,e,z); dest={'COMPLETED':'completed','BLOCKED_USER_DECISION':'blocked','FAILED_TECHNICAL':'failed'}.get(e['status'],'running'); m.move(f,s/dest,e)
r,s=make(); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'PASS'); assert (s/'completed/mock.json').exists()
r,s=make('corrections'); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); assert m.load(s/'running/corrections.json')['status']=='CORRECTING_R1'; step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); assert m.load(s/'running/corrections.json')['status']=='CORRECTING_R2'; step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); assert (s/'failed/corrections.json').exists()
r,s=make('user-decision'); step(r,s); step(r,s,'USER_DECISION_REQUIRED'); assert (s/'blocked/user-decision.json').exists()
r,s=make('empty-delta-audit'); e=m.load(s/'queue/empty-delta-audit.json'); e['status']='AUDITING'; e['baseline']={'protected_pine_sha256':'fixture-pine-hash','preexisting_paths':{}}; m.move(s/'queue/empty-delta-audit.json',s/'running',e)
orig_validate,orig_worker=m.validate_task_delta,m.worker
m.validate_task_delta=lambda repo,envelope: set()
m.worker=lambda repo,root,envelope,role,mock=None: {'role':'auditor','verdict':'PASS','findings':[],'summary':'model accepted empty delta'}
m.cycle(r,s)
e=m.load(s/'running/empty-delta-audit.json'); assert e['status']=='CORRECTING_R1' and e['attempt']==1 and e['last_result']['verdict']=='TECHNICAL_CORRECTION_REQUIRED'
m.validate_task_delta, m.worker = orig_validate, orig_worker
# SMOKE-005: an unchanged dirty protected Pine is baseline state, while only an
# allowlisted task file is delta.  Later Pine changes, staging, and outside paths fail closed.
r=d/'baseline-repo'; r.mkdir(); pine=r/'experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine'; pine.parent.mkdir(parents=True); pine.write_text('pre-existing dirty pine\n'); (r/'allowed.txt').write_text('allowed\n'); (r/'allow.txt').write_text('allowed.txt\n')
statuses={m.PINE:' M'}; m.status_entries=lambda _: dict(statuses); m.protected_ok=lambda _: (hashlib.sha256(pine.read_bytes()).hexdigest(),True)
baseline=m.capture_baseline(r); e={'allowlist_path':'allow.txt','baseline':baseline}; statuses['allowed.txt']='??'; assert m.validate_task_delta(r,e)=={'allowed.txt'}
pine.write_text('changed after baseline\n')
try: m.validate_task_delta(r,e)
except RuntimeError as exc: assert 'protected Pine integrity failure' == str(exc)
else: raise AssertionError('protected Pine byte change was accepted')
pine.write_text('pre-existing dirty pine\n'); statuses[m.PINE]='M '
try: m.validate_task_delta(r,e)
except RuntimeError as exc: assert 'staged changes detected after task start' == str(exc)
else: raise AssertionError('protected Pine staging was accepted')
statuses[m.PINE]=' M'; statuses['outside.txt']='??'
try: m.validate_task_delta(r,e)
except RuntimeError as exc: assert 'changed path outside allowlist' == str(exc)
else: raise AssertionError('outside task delta was accepted')
r,s=make('malformed'); step(r,s); step(r,s,bad=True); assert (s/'failed/malformed.json').exists()
r,s=make('recovery'); step(r,s); e=m.load(s/'running/recovery.json'); assert e['status']=='PLANNING'; step(r,s,'PASS'); assert m.load(s/'running/recovery.json')['status']=='IMPLEMENTING'
r,s=make('duplicate'); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'PASS'); done=m.load(s/'completed/duplicate.json'); m.atomic(s/'queue'/'again.json',done); m.cycle(r,s,{'role':'planner','verdict':'PASS','findings':[],'summary':'deterministic mock'}); assert not (s/'queue/again.json').exists()
(r/'conflict.md').write_text('other task\n'); e=dict(done); e['task_path']='conflict.md'; e['task_hash']=hashlib.sha256((r/'conflict.md').read_bytes()).hexdigest(); e['status']='READY'; m.atomic(s/'queue'/'conflict.json',e); m.cycle(r,s,{'role':'planner','verdict':'PASS','findings':[],'summary':'deterministic mock'}); assert (s/'blocked/conflict.json').exists()
r,s=make('kill'); (s/'KILL').parent.mkdir(parents=True,exist_ok=True); (s/'KILL').write_text('stop'); step(r,s); assert (s/'failed/kill.json').exists()
assert hashlib.sha256(actual_pine.read_bytes()).hexdigest()==before
print('all deterministic scenarios passed')
PY
  echo MOCK_CYCLE_OK; }
case ${1:-} in --offline) offline;; --worker-fixture) worker_fixture;; --mock-cycle) [[ ${2:-} == --wait && ${3:-} =~ ^[0-9]+$ ]] || usage; offline; mock;; --service) [[ ${2:-} =~ ^(--test-mode|--production)$ && ${3:-} == --wait && ${4:-} =~ ^[0-9]+$ ]] || usage; offline; echo SERVICE_STATIC_OK;; --health) offline; echo HEALTH_OK;; *) usage;; esac
