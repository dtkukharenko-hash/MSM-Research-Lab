#!/usr/bin/env bash
set -Eeuo pipefail
REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}
FEEDER="$REPO/automation/msm_task_feeder.py"
ENQUEUE="$REPO/automation/enqueue_task.py"
PINE="$REPO/experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
usage(){ echo "usage: $0 --offline | --fixtures | --service --test-mode|--production --wait SECONDS | --health" >&2; exit 2; }
offline(){
  PYTHONDONTWRITEBYTECODE=1 python3 -B - "$FEEDER" "$ENQUEUE" <<'PY'
from pathlib import Path
import sys
for p in map(Path, sys.argv[1:]): compile(p.read_text(encoding='utf-8'), str(p), 'exec')
PY
  bash -n "$REPO/automation/install_feeder.sh" "$0"
  grep -Fqx 'Environment=PYTHONDONTWRITEBYTECODE=1' "$REPO/automation/msm-task-feeder.service"
  grep -Fqx 'ExecStart=/usr/bin/python3 -B /usr/local/lib/msm-orchestrator/msm_task_feeder.py --poll 10' "$REPO/automation/msm-task-feeder.service"
  echo OFFLINE_OK
}
fixtures(){
  local before; before=$(sha256sum "$PINE" | awk '{print $1}')
  PYTHONDONTWRITEBYTECODE=1 python3 -B - "$REPO" "$FEEDER" "$ENQUEUE" "$PINE" <<'PY'
import hashlib, importlib.util, json, os, pathlib, pwd, grp, subprocess, sys, tempfile
repo, feeder, enqueue, pine = map(pathlib.Path, sys.argv[1:])
spec=importlib.util.spec_from_file_location('f', feeder); f=importlib.util.module_from_spec(spec); sys.modules['f']=f; spec.loader.exec_module(f)
user=pwd.getpwuid(os.getuid()).pw_name; group=grp.getgrgid(os.getgid()).gr_name
def write(root, task, allow='automation/example.py\n'):
    (root/'.codex').mkdir(parents=True, exist_ok=True)
    (root/'.codex/TASK.md').write_text(task, encoding='utf-8')
    (root/'.codex/ALLOWLIST.txt').write_text(allow, encoding='utf-8')
def task(task_id='SAFE-001', status='READY', infra='false', body='ordinary implementation'):
    return '# Task\n\n- task_id: `'+task_id+'`\n- status: `'+status+'`\n- target_branch: `main`\n- infrastructure_maintenance: `'+infra+'`\n\n## Objective\n\n'+body+'\n'
def run(root, state, dry=False): return f.ingest(root,state,dry_run=dry,owner=user,group=group)
with tempfile.TemporaryDirectory() as raw:
    base=pathlib.Path(raw); r=base/'repo'; s=base/'state'; write(r,task())
    assert run(r,s)[0]=='ENQUEUED'; files=list((s/'queue').glob('*.json')); assert len(files)==1
    e=json.loads(files[0].read_text())
    required={'schema_version','task_id','task_hash','status','task_path','allowlist_path','created_at','attempt','max_corrections'}; assert required <= set(e) and e['status']=='READY'
    assert run(r,s)[0]=='NOOP' # repeated identical
    write(r,task(body='ordinary implementation changed')); assert run(r,s)[0]=='BLOCKED'; assert len(list((s/'blocked').glob('*.json')))==1
    write(r,task(status='COMPLETED')); assert run(r,s)[0]=='IGNORED'
    write(r,task(infra='true')); assert run(r,s)[0]=='BLOCKED'
    # Ordinary experiment files, including experiment-local artifacts, are valid only
    # when listed exactly; task-text gates remain independently enforced below.
    for index, allow in enumerate((
        'experiments/EXP-TEST/source.py\n',
        'experiments/EXP-TEST/artifacts/report.md\n',
        'experiments/EXP-TEST/artifacts/metrics.csv\n',
    ), 1):
        q=base/('research'+str(index)); st=base/('research-state'+str(index)); write(q,task('RESEARCH-'+str(index)),allow)
        assert f.read_allowlist(q)==[allow.strip()]
        assert run(q,st)[0]=='ENQUEUED'
    bad_allows=(
        '\n', '/tmp/x\n', '/usr/local/lib/msm-orchestrator/x.py\n', '/etc/msm/x\n', '/home/nnv/x\n',
        '../x\n', 'automation/../x.py\n', 'automation/./x.py\n', 'automation//x.py\n', 'automation/x.py/\n',
        'automation/x.py\nautomation/x.py\n', 'docs/DEFINITIONS.md\n', '.codex/RESULT.md\n', '.git\n', '.git/config\n',
        'automation/secret.txt\n', 'automation/credentials.json\n', 'automation/private_key.txt\n', 'automation/key.pem\n', 'automation/key.key\n', 'automation/.env\n',
        'experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine\n',
    )
    for index, allow in enumerate(bad_allows, 1):
        q=base/('bad'+str(index)); write(q,task('BAD-'+str(index)),allow)
        try: run(q,base/('bad-state'+str(index))); raise AssertionError(allow)
        except f.FeedError: pass
    for word in ('TradingView review','definition change','hypothesis change','holdout extension','ambiguous research judgment','user decision'):
        q=base/('gate'+str(abs(hash(word)))); st=base/('gate-state'+str(abs(hash(word)))); write(q,task('GATE-'+str(abs(hash(word)))[:8],body=word)); assert run(q,st)[0]=='BLOCKED'; assert not list((st/'queue').glob('*.json'))
    q=base/'malformed'; q.mkdir(); write(q,'# Task\n- task_id: SAFE\n- status: READY\n')
    try: run(q,base/'malformed-state'); raise AssertionError('malformed metadata accepted')
    except f.FeedError: pass
    # Explicit CLI modes use the same validator and do not require model calls.
    q=base/'cli'; st=base/'cli-state'; write(q,task('CLI-001'))
    cmd=[sys.executable,'-B',str(enqueue),'--repo',str(q),'--state-dir',str(st),'--owner',user,'--group',group]
    assert subprocess.run(cmd+['--dry-run'],capture_output=True,text=True).returncode==0
    assert not list((st/'queue').glob('*.json')); assert subprocess.run(cmd+['--enqueue'],capture_output=True,text=True).returncode==0
    # Concurrent processes must create one envelope, and a fresh invocation preserves it.
    q=base/'concurrent'; st=base/'concurrent-state'; write(q,task('RACE-001'))
    args=[sys.executable,'-B',str(enqueue),'--enqueue','--repo',str(q),'--state-dir',str(st),'--owner',user,'--group',group]
    a=subprocess.Popen(args,stdout=subprocess.PIPE,text=True); b=subprocess.Popen(args,stdout=subprocess.PIPE,text=True); assert a.wait()==0 and b.wait()==0
    assert len(list((st/'queue').glob('*.json')))==1; assert run(q,st)[0]=='NOOP'
    q=base/'kill'; st=base/'kill-state'; write(q,task('KILL-001')); st.mkdir(); (st/'KILL').write_text('stop'); assert run(q,st)[0]=='BLOCKED'; assert not list((st/'queue').glob('*.json'))
print('FIXTURES_OK')
PY
  [[ $(sha256sum "$PINE" | awk '{print $1}') == "$before" ]]
  git diff --cached --quiet -- "$PINE"
  ! find "$REPO" -type f -name '*.pyc' -o -type d -name '__pycache__' | grep -q .
  ! grep -E '\b(git (add|commit|push|pull|reset|clean|checkout|merge)|subprocess.*git)' "$FEEDER" "$ENQUEUE"
  echo FIXTURES_OK
}
service(){
  [[ ${2:-} =~ ^(--test-mode|--production)$ && ${3:-} == --wait && ${4:-} =~ ^[0-9]+$ ]] || usage
  offline
  grep -Fq 'msm_orchestrator.py' "$REPO/automation/msm-orchestrator.service"
  ! grep -Eq 'Conflicts=msm-orchestrator.service|Conflicts=msm-codex-runner.timer' "$REPO/automation/msm-task-feeder.service"
  echo SERVICE_STATIC_OK
}
case ${1:-} in
  --offline) offline ;;
  --fixtures) offline; fixtures ;;
  --service) service "$@" ;;
  --health) offline; echo HEALTH_OK ;;
  *) usage ;;
esac
