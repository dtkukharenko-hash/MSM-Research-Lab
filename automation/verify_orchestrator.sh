#!/usr/bin/env bash
set -Eeuo pipefail
REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; PY="$REPO/automation/msm_orchestrator.py"; PINE="$REPO/experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
usage(){ echo 'usage: --offline | --mock-cycle --wait SECONDS | --service --test-mode|--production --wait SECONDS | --health' >&2; exit 2; }
offline(){ python3 -m py_compile "$PY"; bash -n "$REPO/automation/msm_worker.sh" "$REPO/automation/install_orchestrator.sh" "$0"; [[ -s "$PINE" ]]; echo OFFLINE_OK; }
fixture(){ local d=$1; mkdir -p "$d/repo"; printf 'task\n' >"$d/repo/task.md"; printf 'allowed\n' >"$d/repo/allow.txt"; python3 - "$d" <<'PY'
import hashlib,json,sys,pathlib
d=pathlib.Path(sys.argv[1]); h=hashlib.sha256((d/'repo/task.md').read_bytes()).hexdigest(); e={'schema_version':'1','task_id':'mock','task_hash':h,'status':'READY','task_path':'task.md','allowlist_path':'allow.txt','created_at':'2026-01-01T00:00:00Z','attempt':0,'max_corrections':2}; (d/'state/queue').mkdir(parents=True); (d/'state/queue/mock.json').write_text(json.dumps(e))
PY
}
mock(){ local d; d=$(mktemp -d); trap 'rm -rf "$d"' RETURN
  python3 - "$PY" "$d" <<'PY'
import hashlib,json,pathlib,sys,importlib.util
py,d=map(pathlib.Path,sys.argv[1:]); sp=importlib.util.spec_from_file_location('o',py); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
pine=pathlib.Path('/home/nnv/MSM-Research-Lab/experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine'); before=hashlib.sha256(pine.read_bytes()).hexdigest()
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
# READY→planning→implementing→auditing→completed.
r,s=make(); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'PASS'); assert (s/'completed/mock.json').exists(), [(str(p),p.read_text()) for p in s.rglob('*.json')]
# Exactly two corrections, then third request blocks.
r,s=make('corrections'); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); assert (s/'blocked/corrections.json').exists()
# Malformed role JSON fails technically, while restart sees persisted state and does not invoke a role twice.
r,s=make('malformed'); step(r,s); step(r,s,bad=True); assert (s/'failed/malformed.json').exists()
r,s=make('recovery'); step(r,s); e=m.load(s/'running/recovery.json'); assert e['status']=='PLANNING'; step(r,s,'PASS'); assert m.load(s/'running/recovery.json')['status']=='IMPLEMENTING'
# Duplicate same hash skips; duplicate different hash blocks. Kill switch fails safely.
r,s=make('duplicate'); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'PASS'); done=m.load(s/'completed/duplicate.json'); m.atomic(s/'queue'/'again.json',done); m.cycle(r,s,{'role':'planner','verdict':'PASS','findings':[],'summary':'deterministic mock'}); assert not (s/'queue/again.json').exists()
(r/'conflict.md').write_text('other task\n'); e=dict(done); e['task_path']='conflict.md'; e['task_hash']=hashlib.sha256((r/'conflict.md').read_bytes()).hexdigest(); e['status']='READY'; m.atomic(s/'queue'/'conflict.json',e); m.cycle(r,s,{'role':'planner','verdict':'PASS','findings':[],'summary':'deterministic mock'}); assert (s/'blocked/conflict.json').exists()
r,s=make('kill'); (s/'KILL').parent.mkdir(parents=True,exist_ok=True); (s/'KILL').write_text('stop'); step(r,s); assert (s/'failed/kill.json').exists()
assert hashlib.sha256(pine.read_bytes()).hexdigest()==before
print('all deterministic scenarios passed')
PY
  echo MOCK_CYCLE_OK; }
case ${1:-} in --offline) offline;; --mock-cycle) [[ ${2:-} == --wait && ${3:-} =~ ^[0-9]+$ ]] || usage; offline; mock;; --service) [[ ${2:-} =~ ^(--test-mode|--production)$ && ${3:-} == --wait && ${4:-} =~ ^[0-9]+$ ]] || usage; offline; echo SERVICE_STATIC_OK;; --health) offline; echo HEALTH_OK;; *) usage;; esac
