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
def result_schema(role, x):
    if not isinstance(x, dict) or set(x) != {"role", "verdict", "findings", "summary"}: raise ValueError("malformed role JSON")
    if x["role"] != role or x["verdict"] not in VERDICTS or not isinstance(x["findings"], list) or not all(isinstance(v, str) for v in x["findings"]) or not isinstance(x["summary"], str): raise ValueError("invalid role result")
def next_state(e, verdict):
    s=e["status"]
    if verdict == "USER_DECISION_REQUIRED": return "BLOCKED_USER_DECISION"
    if verdict == "FAILED": return "FAILED_TECHNICAL"
    if s == "PLANNING": return "IMPLEMENTING" if verdict == "PASS" else "BLOCKED_USER_DECISION"
    if s == "IMPLEMENTING": return "AUDITING" if verdict == "PASS" else "BLOCKED_USER_DECISION"
    if s in {"CORRECTING_R1", "CORRECTING_R2"}: return "AUDITING" if verdict == "PASS" else "BLOCKED_USER_DECISION"
    if s == "AUDITING":
        if verdict == "PASS": return "COMPLETED"
        return "CORRECTING_R1" if e["attempt"] == 0 else "CORRECTING_R2" if e["attempt"] == 1 else "BLOCKED_USER_DECISION"
    raise ValueError("invalid transition from " + s)
def protected_ok(repo: Path):
    pine=repo / "experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
    return digest(pine), subprocess.run(["git","-C",str(repo),"diff","--cached","--quiet","--",str(pine)], check=False).returncode == 0
def git_run(repo, *args):
    return subprocess.run(["git","-C",str(repo),*args], text=True, capture_output=True, check=True)
def git_preflight(repo, e):
    """The sole Git synchronization owner; callers cannot bypass this gate."""
    if git_run(repo,"branch","--show-current").stdout.strip() != "main": raise RuntimeError("branch is not main")
    pine_hash, pine_unstaged = protected_ok(repo)
    if not pine_unstaged: raise RuntimeError("protected Pine is staged")
    dirty=git_run(repo,"status","--porcelain=v1","--untracked-files=all").stdout.splitlines()
    pine="experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
    if any(line[3:] != pine or line[:2] != " M" for line in dirty): raise RuntimeError("unexpected pre-existing worktree changes")
    git_run(repo,"fetch","origin","main"); git_run(repo,"merge","--ff-only","origin/main")
    if protected_ok(repo)[0] != pine_hash or not protected_ok(repo)[1]: raise RuntimeError("protected Pine changed during sync")
    e["protected_pine_sha256"] = pine_hash
def commit_once(repo, e):
    """Stage explicit allowlisted paths only after the final deterministic checks."""
    pine="experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
    if protected_ok(repo)[0] != e.get("protected_pine_sha256") or not protected_ok(repo)[1]: raise RuntimeError("protected Pine integrity failure")
    allowed={x.strip() for x in (repo/e["allowlist_path"]).read_text().splitlines() if x.strip() and not x.startswith("#")}
    changed=set(git_run(repo,"diff","--name-only").stdout.splitlines()) | set(git_run(repo,"ls-files","--others","--exclude-standard").stdout.splitlines())
    changed.discard(pine)
    if not changed or not changed <= allowed: raise RuntimeError("changed path outside allowlist")
    git_run(repo,"diff","--check")
    if not subprocess.run(["git","-C",str(repo),"diff","--cached","--quiet"],check=False).returncode: raise RuntimeError("model left staged changes")
    git_run(repo,"add","--",*sorted(changed)); git_run(repo,"commit","-m",e["task_id"]); git_run(repo,"push","origin","main")
def worker(repo, root, e, role, mock=None):
    out=root/"logs"/(e["task_id"]+"-"+role+".result.json")
    cmd=["bash", str(Path(__file__).with_name("msm_worker.sh")), "--role", role, "--task", str(repo/e["task_path"]), "--allowlist", str(repo/e["allowlist_path"]), "--output", str(out)]
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
    try: result=worker(repo,root,e,role,mock)
    except Exception as ex: return fail(e,str(ex))
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
