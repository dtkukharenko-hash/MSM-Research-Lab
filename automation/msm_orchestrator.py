#!/usr/bin/env python3
"""Deterministic, single-task local orchestrator for MSM task envelopes.

Models supply only role verdicts.  This module owns every transition and all
runtime persistence; it deliberately never treats prose as a state transition.
"""
from __future__ import annotations
import argparse, datetime as dt, fcntl, hashlib, json, os, signal, subprocess, sys, time
from pathlib import Path

STATES = {"READY", "PLANNING", "IMPLEMENTING", "AUDITING", "CORRECTING_R1", "CORRECTING_R2", "COMPLETED", "BLOCKED_USER_DECISION", "FAILED_TECHNICAL"}
VERDICTS = {"PASS", "TECHNICAL_CORRECTION_REQUIRED", "USER_DECISION_REQUIRED", "FAILED"}
ROLES = {"PLANNING": "planner", "IMPLEMENTING": "implementer", "AUDITING": "auditor", "CORRECTING_R1": "corrector", "CORRECTING_R2": "corrector"}
REQUIRED = {"schema_version": str, "task_id": str, "task_hash": str, "status": str, "task_path": str, "allowlist_path": str, "created_at": str, "attempt": int, "max_corrections": int}
PINE = "experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"

def now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def atomic(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True); os.chmod(path.parent, 0o700)
    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    with open(tmp, "w", encoding="utf-8") as f: json.dump(value, f, sort_keys=True, indent=2); f.write("\n")
    os.chmod(tmp, 0o600); os.replace(tmp, path)
def load(path: Path):
    with open(path, encoding="utf-8") as f: return json.load(f)
def digest(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()
def log(root, envelope, role, **fields):
    row = {"timestamp": now(), "task_id": envelope.get("task_id"), "role": role, **fields}
    p = root / "logs" / (envelope["task_id"] + ".jsonl"); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f: f.write(json.dumps(row, sort_keys=True) + "\n")
    os.chmod(p, 0o600)
def fail(e, reason): e.update(status="FAILED_TECHNICAL", failure_reason=reason, updated_at=now()); return e
def validate(e, repo: Path):
    if not isinstance(e, dict) or set(REQUIRED) - set(e): raise ValueError("missing envelope fields")
    for k, typ in REQUIRED.items():
        if not isinstance(e[k], typ) or (typ is str and not e[k]): raise ValueError("invalid " + k)
    if e["status"] not in STATES or e["max_corrections"] != 2 or e["attempt"] < 0 or e["attempt"] > 2: raise ValueError("invalid state or correction limits")
    for key in ("task_path", "allowlist_path"):
        p = (repo / e[key]).resolve()
        if not p.is_file() or repo.resolve() not in p.parents: raise ValueError("invalid referenced " + key)
    if e["task_hash"] != digest((repo / e["task_path"]).resolve()): raise ValueError("task hash mismatch")
    if "baseline" in e:
        b=e["baseline"]
        if not isinstance(b,dict) or not isinstance(b.get("protected_pine_sha256"),str) or not isinstance(b.get("preexisting_paths"),dict): raise ValueError("invalid baseline")
def result_schema(role, x):
    if not isinstance(x, dict) or set(x) != {"role", "verdict", "findings", "summary"}: raise ValueError("malformed role JSON")
    if x["role"] != role or x["verdict"] not in VERDICTS or not isinstance(x["findings"], list) or not all(isinstance(v, str) for v in x["findings"]) or not isinstance(x["summary"], str): raise ValueError("invalid role result")
def next_state(e, verdict):
    s=e["status"]
    if verdict == "USER_DECISION_REQUIRED": return "BLOCKED_USER_DECISION"
    if verdict == "FAILED": return "FAILED_TECHNICAL"
    if verdict == "TECHNICAL_CORRECTION_REQUIRED":
        return "CORRECTING_R1" if e["attempt"] == 0 else "CORRECTING_R2" if e["attempt"] == 1 else "FAILED_TECHNICAL"
    if s == "PLANNING": return "IMPLEMENTING"
    if s == "IMPLEMENTING": return "AUDITING"
    if s in {"CORRECTING_R1", "CORRECTING_R2"}: return "AUDITING"
    if s == "AUDITING":
        return "COMPLETED"
    raise ValueError("invalid transition from " + s)
def protected_ok(repo: Path):
    pine=repo / PINE
    return digest(pine), subprocess.run(["git","-C",str(repo),"diff","--cached","--quiet","--",str(pine)], check=False).returncode == 0
def git_run(repo, *args):
    return subprocess.run(["git","-C",str(repo),*args], text=True, capture_output=True, check=True)

def status_entries(repo: Path):
    """Return porcelain-v1 worktree entries without losing whitespace in paths."""
    raw=subprocess.run(["git","-C",str(repo),"status","--porcelain=v1","-z","--untracked-files=all"],capture_output=True,check=True).stdout
    records=raw.split(b"\0"); entries={}; i=0
    while i < len(records)-1:
        row=records[i]; i += 1
        if len(row) < 4: raise RuntimeError("malformed Git status entry")
        code=row[:2].decode("ascii"); path=row[3:].decode("utf-8","surrogateescape")
        if "R" in code or "C" in code:
            raise RuntimeError("rename or copy status is not permitted")
        if not path or Path(path).is_absolute() or "\0" in path: raise RuntimeError("unsafe Git status path")
        entries[path]=code
    return entries

def path_signature(repo: Path, rel: str, code: str):
    path=(repo/rel).resolve()
    if repo.resolve() not in path.parents or not path.is_file(): raise RuntimeError("pre-existing path is missing or not a regular file: "+rel)
    return {"status":code,"sha256":digest(path),"mode":path.stat().st_mode & 0o777}

def capture_baseline(repo: Path):
    entries=status_entries(repo)
    if any(code != "??" and code[0] != " " for code in entries.values()): raise RuntimeError("pre-existing staged changes are not permitted")
    baseline={path:path_signature(repo,path,code) for path,code in entries.items()}
    pine=repo/PINE
    if not pine.is_file(): raise RuntimeError("protected Pine is missing")
    pine_hash, pine_unstaged=protected_ok(repo)
    if not pine_unstaged: raise RuntimeError("protected Pine is staged")
    return {"protected_pine_sha256":pine_hash,"preexisting_paths":baseline}

def verify_baseline(repo: Path, e: dict):
    b=e.get("baseline")
    if not b: raise RuntimeError("missing captured worktree baseline")
    current=status_entries(repo)
    if any(code != "??" and code[0] != " " for code in current.values()): raise RuntimeError("staged changes detected after task start")
    pine_hash, pine_unstaged=protected_ok(repo)
    if pine_hash != b["protected_pine_sha256"] or not pine_unstaged:
        raise RuntimeError("protected Pine integrity failure")
    for path, expected in b["preexisting_paths"].items():
        if current.get(path) != expected["status"] or path_signature(repo,path,current[path]) != expected:
            raise RuntimeError("pre-existing path changed after task start: "+path)

def task_delta_paths(repo: Path, e: dict):
    verify_baseline(repo,e)
    return set(status_entries(repo)) - set(e["baseline"]["preexisting_paths"])

def allowed_paths(repo: Path, e: dict):
    return {x.strip() for x in (repo/e["allowlist_path"]).read_text().splitlines() if x.strip() and not x.startswith("#")}

def validate_task_delta(repo: Path, e: dict):
    changed=task_delta_paths(repo,e)
    if not changed <= allowed_paths(repo,e): raise RuntimeError("changed path outside allowlist")
    return changed

def empty_required_output_result(role: str):
    return {
        "role": role,
        "verdict": "TECHNICAL_CORRECTION_REQUIRED",
        "findings": ["no task-created allowlisted output paths exist; required task outputs were not created"],
        "summary": "No task-created paths exist. Required allowlisted outputs must be created before audit can pass.",
    }

def git_preflight(repo, e):
    """The sole Git synchronization owner; callers cannot bypass this gate."""
    if git_run(repo,"branch","--show-current").stdout.strip() != "main": raise RuntimeError("branch is not main")
    e["baseline"]=capture_baseline(repo)
    git_run(repo,"fetch","origin","main"); git_run(repo,"merge","--ff-only","origin/main")
    verify_baseline(repo,e)
def commit_once(repo, e):
    """Stage explicit allowlisted paths only after the final deterministic checks."""
    changed=validate_task_delta(repo,e)
    if not changed: raise RuntimeError("no task-created changes to commit")
    git_run(repo,"diff","--check","--",*sorted(changed))
    if not subprocess.run(["git","-C",str(repo),"diff","--cached","--quiet"],check=False).returncode: raise RuntimeError("model left staged changes")
    git_run(repo,"add","--",*sorted(changed)); git_run(repo,"commit","-m",e["task_id"]); git_run(repo,"push","origin","main")
def worker(repo, root, e, role, mock=None):
    out=root/"logs"/(e["task_id"]+"-"+role+".result.json")
    cmd=["bash", str(Path(__file__).with_name("msm_worker.sh")), "--role", role, "--task", str(repo/e["task_path"]), "--allowlist", str(repo/e["allowlist_path"]), "--output", str(out)]
    if "baseline" in e:
        baseline=root/"logs"/(e["task_id"]+".baseline.json"); atomic(baseline,e["baseline"]); cmd += ["--baseline-json",str(baseline)]
    if mock is not None: cmd += ["--mock-response", json.dumps(mock)]
    started=now(); cp=subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=3900)
    log(root,e,role,attempt=e["attempt"],started_at=started,finished_at=now(),exit_code=cp.returncode,output_path=str(out),stderr=cp.stderr[-500:])
    if cp.returncode: raise RuntimeError("worker exit %s" % cp.returncode)
    x=load(out); result_schema(role,x); return x
def process(repo: Path, root: Path, e: dict, mock=None):
    validate(e,repo)
    if (root/"KILL").exists(): return fail(e,"kill switch present")
    if e["status"] == "READY":
        # Mock callers do not have a Git repository; real queued work is gated.
        if mock is None: git_preflight(repo,e)
        e["status"]="PLANNING"; e["updated_at"]=now(); return e
    if e["status"] in {"COMPLETED","BLOCKED_USER_DECISION","FAILED_TECHNICAL"}: return e
    role=ROLES.get(e["status"])
    if not role: return fail(e,"unknown state")
    try:
        if mock is None: validate_task_delta(repo,e)
        result=worker(repo,root,e,role,mock)
        changed=validate_task_delta(repo,e) if mock is None else set()
    except Exception as ex: return fail(e,str(ex))
    if mock is None and role == "auditor" and not changed:
        result=empty_required_output_result(role)
    # Research stop gates always dominate a role verdict.
    gates=("definition change","hypothesis change","holdout","tradingview","ambiguous","conflict")
    if any(any(g in f.lower() for g in gates) for f in result["findings"]): verdict="USER_DECISION_REQUIRED"
    else: verdict=result["verdict"]
    try: target=next_state(e,verdict)
    except ValueError as ex: return fail(e,str(ex))
    e["last_result"]=result; e["status"]=target
    if e["status"] in {"CORRECTING_R1","CORRECTING_R2"}: e["attempt"] += 1
    if target == "COMPLETED" and mock is None:
        try: commit_once(repo,e)
        except Exception as ex: return fail(e,"commit/push failed: "+str(ex))
    e["updated_at"]=now(); return e
def move(src: Path, dst: Path, e):
    atomic(dst/src.name,e)
    if src.parent != dst: src.unlink(missing_ok=True)
def cycle(repo: Path, root: Path, mock=None):
    for n in ("queue","running","completed","blocked","failed","logs","locks"): (root/n).mkdir(parents=True,exist_ok=True); os.chmod(root/n,0o700)
    lock=open(root/"locks/orchestrator.lock","a+")
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: return 0
    try:
        for srcname in ("running","queue"):
            for src in sorted((root/srcname).glob("*.json")):
                try: e=load(src); validate(e,repo)
                except Exception as ex:
                    bad={"task_id":src.stem,"status":"FAILED_TECHNICAL","failure_reason":str(ex),"updated_at":now()}; move(src,root/"failed",bad); continue
                # completed ID/hash makes identical envelopes idempotent; conflicts block.
                seen=list((root/"completed").glob("*.json"))+list((root/"blocked").glob("*.json"))
                conflict=False
                for p in seen:
                    x=load(p)
                    if x.get("task_id")==e["task_id"]:
                        if x.get("task_hash")==e["task_hash"]: src.unlink(); conflict=True; break
                        e["status"]="BLOCKED_USER_DECISION"; e["failure_reason"]="duplicate task ID with different hash"; move(src,root/"blocked",e); conflict=True; break
                if conflict: continue
                if src.parent.name=="queue": move(src,root/"running",e); src=root/"running"/src.name
                before=e["status"]; e=process(repo,root,e,mock)
                destination="running" if e["status"] not in {"COMPLETED","BLOCKED_USER_DECISION","FAILED_TECHNICAL"} else {"COMPLETED":"completed","BLOCKED_USER_DECISION":"blocked","FAILED_TECHNICAL":"failed"}[e["status"]]
                move(src,root/destination,e); log(root,e,ROLES.get(before,"state"),from_state=before,to_state=e["status"])
                return 0 # sequential: at most one transition per poll
    finally: lock.close()
    return 0
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",default="/home/nnv/MSM-Research-Lab"); ap.add_argument("--state-dir",default="/home/nnv/.local/state/msm-orchestrator"); ap.add_argument("--once",action="store_true"); ap.add_argument("--poll",type=int,default=10); args=ap.parse_args()
    stop=False
    def term(*_): nonlocal_stop[0]=True
    nonlocal_stop=[False]; signal.signal(signal.SIGTERM,term); signal.signal(signal.SIGINT,term)
    while not nonlocal_stop[0]:
        cycle(Path(args.repo),Path(args.state_dir))
        if args.once: break
        time.sleep(max(1,args.poll))
if __name__ == "__main__": main()
