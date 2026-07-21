#!/usr/bin/env python3
"""Fail-closed, deterministic ingress for local MSM orchestrator tasks."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

TASK_PATH = ".codex/TASK.md"
ALLOWLIST_PATH = ".codex/ALLOWLIST.txt"
TERMINAL_DIRS = ("queue", "running", "completed", "blocked", "failed")
TASK_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,127}$")
FIELD_RE = re.compile(r"^- ([a-z_][a-z0-9_]*): `([^`\r\n]+)`$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_EXACT = {
    "docs/DEFINITIONS.md",
    "experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine",
    ".codex/RESULT.md",
}


class FeedError(ValueError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _owner_ids(owner: str, group: str) -> tuple[int, int]:
    import grp
    import pwd
    return pwd.getpwnam(owner).pw_uid, grp.getgrnam(group).gr_gid


def secure_dir(path: Path, owner: str, group: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    uid, gid = _owner_ids(owner, group)
    if (os.getuid(), os.getgid()) != (uid, gid):
        os.chown(path, uid, gid)


def atomic_new(path: Path, value: dict, owner: str, group: str) -> bool:
    """Create a JSON file exactly once; never replace an existing state file."""
    secure_dir(path.parent, owner, group)
    data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise FeedError("stale temporary envelope exists: " + tmp.name)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(fd, data[offset:])
        os.fsync(fd)
        os.fchmod(fd, 0o600)
        uid, gid = _owner_ids(owner, group)
        if (os.getuid(), os.getgid()) != (uid, gid):
            os.fchown(fd, uid, gid)
    finally:
        os.close(fd)
    try:
        os.link(tmp, path)
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)
    return True


def parse_metadata(task_bytes: bytes) -> dict[str, str]:
    try:
        lines = task_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise FeedError("TASK.md is not UTF-8") from exc
    fields: dict[str, str] = {}
    for line in lines:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            match = FIELD_RE.match(line)
            if not match:
                raise FeedError("malformed Markdown metadata")
            key, value = match.groups()
            if key in fields:
                raise FeedError("duplicate metadata field: " + key)
            fields[key] = value
    required = {
        "task_id", "status", "target_branch", "infrastructure_maintenance",
        "task_kind", "data_ready",
    }
    if not required <= set(fields):
        raise FeedError("missing required metadata")
    if not TASK_ID_RE.fullmatch(fields["task_id"]):
        raise FeedError("invalid task_id")
    if fields["status"] not in {"READY", "COMPLETED", "OPEN", "BLOCKED", "REJECT", "ACCEPT"}:
        raise FeedError("invalid status")
    if fields["target_branch"] != "main":
        raise FeedError("target branch must be main")
    if fields["infrastructure_maintenance"] not in {"true", "false"}:
        raise FeedError("invalid infrastructure_maintenance")
    if fields["task_kind"] not in {"DATA", "RESEARCH", "INFRASTRUCTURE"}:
        raise FeedError("invalid task_kind")
    if fields["data_ready"] not in {"true", "false"}:
        raise FeedError("invalid data_ready")
    return fields


def is_protected(path: str) -> bool:
    lower = path.lower()
    return (
        path in FORBIDDEN_EXACT
        or path == ".git" or path.startswith(".git/")
        or path.startswith("/usr/") or path.startswith("/etc/") or path.startswith("/home/")
        or any(token in lower for token in ("secret", "credential", "private_key", ".pem", ".key", ".env"))
    )


def normalized_repo_file(repo: Path, value: str, label: str) -> Path:
    candidate = Path(value)
    if (
        value != candidate.as_posix()
        or value.endswith("/")
        or candidate.is_absolute()
        or "\\" in value
        or "." in candidate.parts
        or ".." in candidate.parts
        or is_protected(value)
    ):
        raise FeedError(label + " path is not normalized or permitted")
    resolved = (repo / candidate).resolve()
    if repo.resolve() not in resolved.parents or not resolved.is_file():
        raise FeedError(label + " file is missing")
    return resolved


def read_allowlist(repo: Path) -> list[str]:
    source = repo / ALLOWLIST_PATH
    if not source.is_file():
        raise FeedError("ALLOWLIST.txt missing")
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise FeedError("ALLOWLIST.txt is not UTF-8") from exc
    if not lines or any(not line.strip() for line in lines):
        raise FeedError("empty allowlist entry")
    entries: list[str] = []
    for raw in lines:
        value = raw.strip()
        candidate = Path(value)
        if value != raw or value != candidate.as_posix() or value.endswith("/") or candidate.is_absolute() or "\\" in value or "." in candidate.parts or ".." in candidate.parts:
            raise FeedError("allowlist path is not normalized")
        if value.startswith("-") or is_protected(value):
            raise FeedError("forbidden allowlist path: " + value)
        if value in entries:
            raise FeedError("duplicate allowlist entry: " + value)
        entries.append(value)
    return entries


def data_gate_reason(repo: Path, fields: dict[str, str]) -> str | None:
    if fields["task_kind"] != "RESEARCH":
        return None
    if fields["data_ready"] != "true":
        return "research task requires data_ready=true"
    manifest_value = fields.get("data_manifest")
    expected_hash = fields.get("data_manifest_sha256")
    if not manifest_value or not expected_hash:
        return "research task requires data_manifest and data_manifest_sha256"
    if not SHA256_RE.fullmatch(expected_hash):
        raise FeedError("invalid data_manifest_sha256")
    manifest = normalized_repo_file(repo, manifest_value, "data manifest")
    actual_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        return "data manifest hash mismatch"
    try:
        text = manifest.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FeedError("data manifest is not UTF-8") from exc
    if "DATA_READY=YES" not in text:
        return "data manifest does not declare DATA_READY=YES"
    return None


def block_reason(task_bytes: bytes, fields: dict[str, str]) -> str | None:
    if fields["status"] != "READY":
        return "task status is not READY"
    if fields["infrastructure_maintenance"] == "true":
        return "infrastructure task requires manual bootstrap"
    text = task_bytes.decode("utf-8", errors="replace").lower()
    gates = {
        "definition change": "definition change requires user decision",
        "hypothesis change": "hypothesis change requires user decision",
        "holdout": "holdout access requires user decision",
        "tradingview": "visual or TradingView review requires user decision",
        "visual review": "visual or TradingView review requires user decision",
        "ambiguous": "ambiguous research judgment requires user decision",
        "user decision": "task explicitly requires user decision",
    }
    return next((reason for token, reason in gates.items() if token in text), None)


def envelope(fields: dict[str, str], task_hash: str, status: str = "READY", reason: str | None = None) -> dict:
    item = {
        "schema_version": "1", "task_id": fields["task_id"], "task_hash": task_hash,
        "status": status, "task_path": TASK_PATH, "allowlist_path": ALLOWLIST_PATH,
        "created_at": utc_now(), "attempt": 0, "max_corrections": 2,
    }
    if reason:
        item["failure_reason"] = reason
        item["updated_at"] = utc_now()
    return item


def existing(root: Path, task_id: str) -> list[dict]:
    found = []
    for name in TERMINAL_DIRS:
        directory = root / name
        if directory.exists():
            for path in directory.glob("*.json"):
                try:
                    value = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if value.get("task_id") == task_id:
                    found.append(value)
    return found


def ingest(repo: Path, state: Path, *, dry_run: bool = False, owner: str = "nnv", group: str = "nnv") -> tuple[str, str]:
    task_file = repo / TASK_PATH
    if not task_file.is_file():
        raise FeedError("TASK.md missing")
    task_bytes = task_file.read_bytes()
    fields = parse_metadata(task_bytes)
    task_hash = hashlib.sha256(task_bytes).hexdigest()
    if fields["status"] != "READY":
        return "IGNORED", "task status is not READY"
    # Validate even blocked tasks: invalid allowlists must never reach the queue.
    read_allowlist(repo)
    for name in ("queue", "running", "completed", "blocked", "failed", "logs", "locks"):
        secure_dir(state / name, owner, group)
    lock_path = state / "locks" / "feeder.lock"
    with open(lock_path, "a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (state / "KILL").exists():
            return "BLOCKED", "kill switch present"
        matches = existing(state, fields["task_id"])
        if any(item.get("task_hash") == task_hash for item in matches):
            return "NOOP", "identical task already recorded"
        conflict = bool(matches)
        reason = data_gate_reason(repo, fields) or block_reason(task_bytes, fields)
        if conflict:
            reason = "duplicate task ID with different hash"
        destination = "blocked" if reason else "queue"
        item = envelope(fields, task_hash, "BLOCKED_USER_DECISION" if reason else "READY", reason)
        filename = fields["task_id"] + "-" + task_hash + ".json"
        if dry_run:
            return ("BLOCKED" if reason else "DRY_RUN"), reason or "validation passed"
        if atomic_new(state / destination / filename, item, owner, group):
            return ("BLOCKED" if reason else "ENQUEUED"), reason or filename
        return "NOOP", "envelope already exists"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="/home/nnv/MSM-Research-Lab")
    parser.add_argument("--state-dir", default="/home/nnv/.local/state/msm-orchestrator")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=int, default=10)
    parser.add_argument("--owner", default="nnv")
    parser.add_argument("--group", default="nnv")
    args = parser.parse_args()
    while True:
        try:
            status, detail = ingest(Path(args.repo), Path(args.state_dir), owner=args.owner, group=args.group)
            print(status + ": " + detail)
        except FeedError as exc:
            print("REJECTED: " + str(exc), file=sys.stderr)
        if args.once:
            return 0
        time.sleep(max(1, args.poll))


if __name__ == "__main__":
    raise SystemExit(main())
