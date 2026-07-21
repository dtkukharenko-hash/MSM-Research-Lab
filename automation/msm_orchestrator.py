#!/usr/bin/env python3
"""Deterministic, single-task local orchestrator for MSM task envelopes.

Models supply role verdicts. This module owns every transition and all runtime
persistence. User-decision blocking is available only when TASK.md explicitly
sets ``allow_user_decision: true``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

STATES = {
    "READY",
    "PLANNING",
    "IMPLEMENTING",
    "AUDITING",
    "CORRECTING_R1",
    "CORRECTING_R2",
    "COMPLETED",
    "BLOCKED_USER_DECISION",
    "FAILED_TECHNICAL",
}
VERDICTS = {
    "PASS",
    "TECHNICAL_CORRECTION_REQUIRED",
    "USER_DECISION_REQUIRED",
    "FAILED",
}
ROLES = {
    "PLANNING": "planner",
    "IMPLEMENTING": "implementer",
    "AUDITING": "auditor",
    "CORRECTING_R1": "corrector",
    "CORRECTING_R2": "corrector",
}
REQUIRED = {
    "schema_version": str,
    "task_id": str,
    "task_hash": str,
    "status": str,
    "task_path": str,
    "allowlist_path": str,
    "created_at": str,
    "attempt": int,
    "max_corrections": int,
}
PINE = "experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine"
DECISION_MARKERS = (
    "definition change requires user decision",
    "hypothesis change requires user decision",
    "holdout access requires user decision",
    "visual or tradingview review requires user decision",
    "ambiguous research judgment requires user decision",
    "task explicitly requires user decision",
)


def now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(path.name + ".tmp.%d" % os.getpid())
    with open(temporary, "w", encoding="utf-8") as target:
        json.dump(value, target, sort_keys=True, indent=2)
        target.write("\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def load(path: Path):
    with open(path, encoding="utf-8") as source:
        return json.load(source)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(root: Path, envelope: dict, role: str, **fields) -> None:
    row = {
        "timestamp": now(),
        "task_id": envelope.get("task_id"),
        "role": role,
        **fields,
    }
    path = root / "logs" / (envelope["task_id"] + ".jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as target:
        target.write(json.dumps(row, sort_keys=True) + "\n")
    os.chmod(path, 0o600)


def fail(envelope: dict, reason: str) -> dict:
    envelope.update(
        status="FAILED_TECHNICAL",
        failure_reason=reason,
        updated_at=now(),
    )
    return envelope


def validate(envelope: dict, repo: Path) -> None:
    if not isinstance(envelope, dict) or set(REQUIRED) - set(envelope):
        raise ValueError("missing envelope fields")
    for key, expected_type in REQUIRED.items():
        value = envelope[key]
        if not isinstance(value, expected_type) or (
            expected_type is str and not value
        ):
            raise ValueError("invalid " + key)
    if (
        envelope["status"] not in STATES
        or envelope["max_corrections"] != 2
        or envelope["attempt"] < 0
        or envelope["attempt"] > 2
    ):
        raise ValueError("invalid state or correction limits")
    for key in ("task_path", "allowlist_path"):
        path = (repo / envelope[key]).resolve()
        if not path.is_file() or repo.resolve() not in path.parents:
            raise ValueError("invalid referenced " + key)
    task_path = (repo / envelope["task_path"]).resolve()
    if envelope["task_hash"] != digest(task_path):
        raise ValueError("task hash mismatch")
    if "baseline" in envelope:
        baseline = envelope["baseline"]
        if (
            not isinstance(baseline, dict)
            or not isinstance(baseline.get("protected_pine_sha256"), str)
            or not isinstance(baseline.get("preexisting_paths"), dict)
        ):
            raise ValueError("invalid baseline")


def result_schema(role: str, value: dict) -> None:
    if not isinstance(value, dict) or set(value) != {
        "role",
        "verdict",
        "findings",
        "summary",
    }:
        raise ValueError("malformed role JSON")
    if (
        value["role"] != role
        or value["verdict"] not in VERDICTS
        or not isinstance(value["findings"], list)
        or not all(isinstance(item, str) for item in value["findings"])
        or not isinstance(value["summary"], str)
    ):
        raise ValueError("invalid role result")


def next_state(envelope: dict, verdict: str) -> str:
    state = envelope["status"]
    if verdict == "USER_DECISION_REQUIRED":
        return "BLOCKED_USER_DECISION"
    if verdict == "FAILED":
        return "FAILED_TECHNICAL"
    if verdict == "TECHNICAL_CORRECTION_REQUIRED":
        if envelope["attempt"] == 0:
            return "CORRECTING_R1"
        if envelope["attempt"] == 1:
            return "CORRECTING_R2"
        return "FAILED_TECHNICAL"
    if state == "PLANNING":
        return "IMPLEMENTING"
    if state == "IMPLEMENTING":
        return "AUDITING"
    if state in {"CORRECTING_R1", "CORRECTING_R2"}:
        return "AUDITING"
    if state == "AUDITING":
        return "COMPLETED"
    raise ValueError("invalid transition from " + state)


def protected_ok(repo: Path) -> tuple[str, bool]:
    pine = repo / PINE
    unstaged = (
        subprocess.run(
            ["git", "-C", str(repo), "diff", "--cached", "--quiet", "--", str(pine)],
            check=False,
        ).returncode
        == 0
    )
    return digest(pine), unstaged


def git_run(repo: Path, *args: str):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
    )


def status_entries(repo: Path) -> dict[str, str]:
    raw = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True,
        check=True,
    ).stdout
    records = raw.split(b"\0")
    entries: dict[str, str] = {}
    index = 0
    while index < len(records) - 1:
        row = records[index]
        index += 1
        if len(row) < 4:
            raise RuntimeError("malformed Git status entry")
        code = row[:2].decode("ascii")
        path = row[3:].decode("utf-8", "surrogateescape")
        if "R" in code or "C" in code:
            raise RuntimeError("rename or copy status is not permitted")
        if not path or Path(path).is_absolute() or "\0" in path:
            raise RuntimeError("unsafe Git status path")
        entries[path] = code
    return entries


def path_signature(repo: Path, relative: str, code: str) -> dict:
    path = (repo / relative).resolve()
    if repo.resolve() not in path.parents or not path.is_file():
        raise RuntimeError("pre-existing path is missing or not a regular file: " + relative)
    return {
        "status": code,
        "sha256": digest(path),
        "mode": path.stat().st_mode & 0o777,
    }


def capture_baseline(repo: Path) -> dict:
    entries = status_entries(repo)
    if any(code != "??" and code[0] != " " for code in entries.values()):
        raise RuntimeError("pre-existing staged changes are not permitted")
    baseline = {
        path: path_signature(repo, path, code)
        for path, code in entries.items()
    }
    pine = repo / PINE
    if not pine.is_file():
        raise RuntimeError("protected Pine is missing")
    pine_hash, pine_unstaged = protected_ok(repo)
    if not pine_unstaged:
        raise RuntimeError("protected Pine is staged")
    return {
        "protected_pine_sha256": pine_hash,
        "preexisting_paths": baseline,
    }


def verify_baseline(repo: Path, envelope: dict) -> None:
    baseline = envelope.get("baseline")
    if not baseline:
        raise RuntimeError("missing captured worktree baseline")
    current = status_entries(repo)
    if any(code != "??" and code[0] != " " for code in current.values()):
        raise RuntimeError("staged changes detected after task start")
    pine_hash, pine_unstaged = protected_ok(repo)
    if pine_hash != baseline["protected_pine_sha256"] or not pine_unstaged:
        raise RuntimeError("protected Pine integrity failure")
    for path, expected in baseline["preexisting_paths"].items():
        if current.get(path) != expected["status"]:
            raise RuntimeError("pre-existing path changed after task start: " + path)
        if path_signature(repo, path, current[path]) != expected:
            raise RuntimeError("pre-existing path changed after task start: " + path)


def task_delta_paths(repo: Path, envelope: dict) -> set[str]:
    verify_baseline(repo, envelope)
    return set(status_entries(repo)) - set(envelope["baseline"]["preexisting_paths"])


def allowed_paths(repo: Path, envelope: dict) -> set[str]:
    return {
        line.strip()
        for line in (repo / envelope["allowlist_path"]).read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def validate_task_delta(repo: Path, envelope: dict) -> set[str]:
    changed = task_delta_paths(repo, envelope)
    if not changed <= allowed_paths(repo, envelope):
        raise RuntimeError("changed path outside allowlist")
    return changed


def task_metadata(repo: Path, envelope: dict) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in (repo / envelope["task_path"]).read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            break
        if line.startswith("- ") and ": `" in line and line.endswith("`"):
            key, value = line[2:-1].split(": `", 1)
            fields[key] = value
    return fields


def allow_user_decision(metadata: dict[str, str]) -> bool:
    return metadata.get("allow_user_decision", "false").strip().lower() == "true"


def normalize_role_result(result: dict, metadata: dict[str, str]) -> dict:
    normalized = {
        "role": result["role"],
        "verdict": result["verdict"],
        "findings": list(result["findings"]),
        "summary": result["summary"],
    }
    permitted = allow_user_decision(metadata)
    marker_present = any(
        any(marker in finding.lower() for marker in DECISION_MARKERS)
        for finding in normalized["findings"]
    )
    if permitted and metadata.get("task_kind", "RESEARCH") == "RESEARCH" and marker_present:
        normalized["verdict"] = "USER_DECISION_REQUIRED"
    elif normalized["verdict"] == "USER_DECISION_REQUIRED":
        normalized["verdict"] = "TECHNICAL_CORRECTION_REQUIRED"
        normalized["findings"].append(
            "orchestrator normalized USER_DECISION_REQUIRED to TECHNICAL_CORRECTION_REQUIRED because TASK.md does not explicitly allow a user decision"
        )
        normalized["summary"] = (
            normalized["summary"]
            + " User-decision blocking is disabled for this task; the issue is treated as technical."
        ).strip()
    return normalized


def empty_required_output_result(role: str) -> dict:
    return {
        "role": role,
        "verdict": "TECHNICAL_CORRECTION_REQUIRED",
        "findings": [
            "no task-created allowlisted output paths exist; required task outputs were not created"
        ],
        "summary": "No task-created paths exist. Required allowlisted outputs must be created before audit can pass.",
    }


def git_preflight(repo: Path, envelope: dict) -> None:
    if git_run(repo, "branch", "--show-current").stdout.strip() != "main":
        raise RuntimeError("branch is not main")
    envelope["baseline"] = capture_baseline(repo)
    git_run(repo, "fetch", "origin", "main")
    git_run(repo, "merge", "--ff-only", "origin/main")
    verify_baseline(repo, envelope)


def commit_once(repo: Path, envelope: dict) -> None:
    changed = validate_task_delta(repo, envelope)
    if not changed:
        raise RuntimeError("no task-created changes to commit")
    git_run(repo, "diff", "--check", "--", *sorted(changed))
    if subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--quiet"],
        check=False,
    ).returncode != 0:
        raise RuntimeError("model left staged changes")
    git_run(repo, "add", "--", *sorted(changed))
    git_run(repo, "commit", "-m", envelope["task_id"])
    git_run(repo, "push", "origin", "main")


def worker(repo: Path, root: Path, envelope: dict, role: str, mock=None) -> dict:
    output = root / "logs" / (envelope["task_id"] + "-" + role + ".result.json")
    command = [
        "bash",
        str(Path(__file__).with_name("msm_worker.sh")),
        "--role",
        role,
        "--task",
        str(repo / envelope["task_path"]),
        "--allowlist",
        str(repo / envelope["allowlist_path"]),
        "--output",
        str(output),
    ]
    if "baseline" in envelope:
        baseline_path = root / "logs" / (envelope["task_id"] + ".baseline.json")
        atomic(baseline_path, envelope["baseline"])
        command += ["--baseline-json", str(baseline_path)]
    if mock is not None:
        command += ["--mock-response", json.dumps(mock)]
    started = now()
    completed = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=3900,
    )
    log(
        root,
        envelope,
        role,
        attempt=envelope["attempt"],
        started_at=started,
        finished_at=now(),
        exit_code=completed.returncode,
        output_path=str(output),
        stderr=completed.stderr[-500:],
    )
    if completed.returncode:
        raise RuntimeError("worker exit %s" % completed.returncode)
    value = load(output)
    result_schema(role, value)
    return value


def process(repo: Path, root: Path, envelope: dict, mock=None) -> dict:
    validate(envelope, repo)
    if (root / "KILL").exists():
        return fail(envelope, "kill switch present")
    if envelope["status"] == "READY":
        if mock is None:
            git_preflight(repo, envelope)
        envelope["status"] = "PLANNING"
        envelope["updated_at"] = now()
        return envelope
    if envelope["status"] in {
        "COMPLETED",
        "BLOCKED_USER_DECISION",
        "FAILED_TECHNICAL",
    }:
        return envelope
    role = ROLES.get(envelope["status"])
    if not role:
        return fail(envelope, "unknown state")
    try:
        if mock is None:
            validate_task_delta(repo, envelope)
        result = worker(repo, root, envelope, role, mock)
        changed = validate_task_delta(repo, envelope) if mock is None else set()
    except Exception as exc:
        return fail(envelope, str(exc))
    if mock is None and role == "auditor" and not changed:
        result = empty_required_output_result(role)
    metadata = task_metadata(repo, envelope)
    result = normalize_role_result(result, metadata)
    try:
        target = next_state(envelope, result["verdict"])
    except ValueError as exc:
        return fail(envelope, str(exc))
    envelope["last_result"] = result
    envelope["status"] = target
    if envelope["status"] in {"CORRECTING_R1", "CORRECTING_R2"}:
        envelope["attempt"] += 1
    if target == "COMPLETED" and mock is None:
        try:
            commit_once(repo, envelope)
        except Exception as exc:
            return fail(envelope, "commit/push failed: " + str(exc))
    envelope["updated_at"] = now()
    return envelope


def move(source: Path, destination: Path, envelope: dict) -> None:
    atomic(destination / source.name, envelope)
    if source.parent != destination:
        source.unlink(missing_ok=True)


def cycle(repo: Path, root: Path, mock=None) -> int:
    for name in ("queue", "running", "completed", "blocked", "failed", "logs", "locks"):
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
    lock = open(root / "locks" / "orchestrator.lock", "a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    try:
        for source_name in ("running", "queue"):
            for source in sorted((root / source_name).glob("*.json")):
                try:
                    envelope = load(source)
                    validate(envelope, repo)
                except Exception as exc:
                    bad = {
                        "task_id": source.stem,
                        "status": "FAILED_TECHNICAL",
                        "failure_reason": str(exc),
                        "updated_at": now(),
                    }
                    move(source, root / "failed", bad)
                    continue
                seen = (
                    list((root / "completed").glob("*.json"))
                    + list((root / "blocked").glob("*.json"))
                    + list((root / "failed").glob("*.json"))
                )
                conflict = False
                for existing_path in seen:
                    existing = load(existing_path)
                    if existing.get("task_id") != envelope["task_id"]:
                        continue
                    if existing.get("task_hash") == envelope["task_hash"]:
                        source.unlink(missing_ok=True)
                    else:
                        envelope["status"] = "FAILED_TECHNICAL"
                        envelope["failure_reason"] = "duplicate task ID with different hash"
                        envelope["updated_at"] = now()
                        move(source, root / "failed", envelope)
                    conflict = True
                    break
                if conflict:
                    continue
                if source.parent.name == "queue":
                    move(source, root / "running", envelope)
                    source = root / "running" / source.name
                before = envelope["status"]
                envelope = process(repo, root, envelope, mock)
                if envelope["status"] == "COMPLETED":
                    destination = "completed"
                elif envelope["status"] == "BLOCKED_USER_DECISION":
                    destination = "blocked"
                elif envelope["status"] == "FAILED_TECHNICAL":
                    destination = "failed"
                else:
                    destination = "running"
                move(source, root / destination, envelope)
                log(
                    root,
                    envelope,
                    ROLES.get(before, "state"),
                    from_state=before,
                    to_state=envelope["status"],
                )
                return 0
    finally:
        lock.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="/home/nnv/MSM-Research-Lab")
    parser.add_argument(
        "--state-dir",
        default="/home/nnv/.local/state/msm-orchestrator",
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=int, default=10)
    args = parser.parse_args()
    stopped = [False]

    def terminate(*_args):
        stopped[0] = True

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    while not stopped[0]:
        cycle(Path(args.repo), Path(args.state_dir))
        if args.once:
            break
        time.sleep(max(1, args.poll))


if __name__ == "__main__":
    main()
