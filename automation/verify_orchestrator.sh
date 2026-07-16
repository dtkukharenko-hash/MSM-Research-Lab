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
  printf '%s\n' 'fixture-credential-never-print' >"$d/codex-home/auth.json"
  printf '%s\n' 'model = "fixture"' >"$d/codex-home/config.toml"
  chmod 600 "$d/codex-home/auth.json" "$d/codex-home/config.toml"
  cat >"$d/bin/codex" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
out=
while (($#)); do
  case $1 in -o) out=$2; shift 2;; *) shift;; esac
done
[[ -n $out ]]
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
    bash "$REPO/automation/msm_worker.sh" --role planner --task "$d/repo/task.md" --allowlist "$d/repo/allow.txt" --output "$output" >"$d/worker.stdout" 2>"$d/worker.stderr"
  [[ -s $output ]] || { echo 'worker fixture did not preserve output path' >&2; return 1; }
  [[ ! -e "$d/repo/.git/worker-fixture-must-not-exist" ]] || { echo '.git became writable inside worker sandbox' >&2; return 1; }
  runtime=$(find "$d/state/runtime" -type f -name runtime-write-check | wc -l)
  [[ $runtime == 6 ]] || { echo "worker fixture expected six writable runtime paths, got $runtime" >&2; return 1; }
  runtime=$(find "$d/state/runtime" -type f -name auth.json | wc -l)
  [[ $runtime == 1 ]] || { echo "worker fixture expected one private credential copy, got $runtime" >&2; return 1; }
  [[ $(stat -c '%a' "$d/state"/runtime/*/planner/codex "$d/state"/runtime/*/planner/codex/auth.json) == $'700\n600' ]] || { echo 'worker fixture credential modes are unsafe' >&2; return 1; }
  ! rg -q -F 'fixture-credential-never-print' "$output" "${output%.json}.jsonl" "$d/worker.stdout" "$d/worker.stderr" "$d/repo"
  ! rg -q 'failed to initialize in-process app-server client: Read-only file system' "$output" "${output%.json}.jsonl"
  if MSM_REPO="$d/repo" MSM_CODEX="$d/bin/codex" MSM_CODEX_HOME="$d/no-credentials" MSM_STATE_DIR="$d/missing-state" \
    bash "$REPO/automation/msm_worker.sh" --role planner --task "$d/repo/task.md" --allowlist "$d/repo/allow.txt" --output "$d/missing.json" >"$d/missing.stdout" 2>"$d/missing.stderr"; then
    echo 'worker fixture accepted absent credentials' >&2; return 1
  fi
  rg -qx 'Codex credentials are unavailable' "$d/missing.stderr" || { echo 'worker fixture missing-credential failure was not controlled' >&2; return 1; }
  [[ ! -e $d/missing.json && ! -e ${d}/missing.jsonl ]] || { echo 'worker fixture emitted output without credentials' >&2; return 1; }
  ! rg -q -F 'fixture-credential-never-print' "$d/missing.stdout" "$d/missing.stderr"
  echo WORKER_RUNTIME_FIXTURE_OK
}
mock(){ local d; d=$(mktemp -d); trap 'rm -rf "$d"' RETURN
  python3 -B - "$PY" "$d" <<'PY'
import hashlib,json,pathlib,sys,importlib.util
sys.dont_write_bytecode=True
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
r,s=make(); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'PASS'); assert (s/'completed/mock.json').exists()
r,s=make('corrections'); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); step(r,s,'PASS'); step(r,s,'TECHNICAL_CORRECTION_REQUIRED'); assert (s/'blocked/corrections.json').exists()
r,s=make('malformed'); step(r,s); step(r,s,bad=True); assert (s/'failed/malformed.json').exists()
r,s=make('recovery'); step(r,s); e=m.load(s/'running/recovery.json'); assert e['status']=='PLANNING'; step(r,s,'PASS'); assert m.load(s/'running/recovery.json')['status']=='IMPLEMENTING'
r,s=make('duplicate'); step(r,s); step(r,s,'PASS'); step(r,s,'PASS'); step(r,s,'PASS'); done=m.load(s/'completed/duplicate.json'); m.atomic(s/'queue'/'again.json',done); m.cycle(r,s,{'role':'planner','verdict':'PASS','findings':[],'summary':'deterministic mock'}); assert not (s/'queue/again.json').exists()
(r/'conflict.md').write_text('other task\n'); e=dict(done); e['task_path']='conflict.md'; e['task_hash']=hashlib.sha256((r/'conflict.md').read_bytes()).hexdigest(); e['status']='READY'; m.atomic(s/'queue'/'conflict.json',e); m.cycle(r,s,{'role':'planner','verdict':'PASS','findings':[],'summary':'deterministic mock'}); assert (s/'blocked/conflict.json').exists()
r,s=make('kill'); (s/'KILL').parent.mkdir(parents=True,exist_ok=True); (s/'KILL').write_text('stop'); step(r,s); assert (s/'failed/kill.json').exists()
assert hashlib.sha256(pine.read_bytes()).hexdigest()==before
print('all deterministic scenarios passed')
PY
  echo MOCK_CYCLE_OK; }
case ${1:-} in --offline) offline;; --worker-fixture) worker_fixture;; --mock-cycle) [[ ${2:-} == --wait && ${3:-} =~ ^[0-9]+$ ]] || usage; offline; mock;; --service) [[ ${2:-} =~ ^(--test-mode|--production)$ && ${3:-} == --wait && ${4:-} =~ ^[0-9]+$ ]] || usage; offline; echo SERVICE_STATIC_OK;; --health) offline; echo HEALTH_OK;; *) usage;; esac
