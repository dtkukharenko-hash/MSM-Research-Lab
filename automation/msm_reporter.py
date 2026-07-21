#!/usr/bin/env python3
"""Generate scoped human-readable reports for terminal MSM task envelopes.

The reporter is read-only with respect to the repository. For failed or blocked
runs it may inspect only task-created paths that are also present in that task's
allowlist. Unrelated dirty or untracked experiment directories are never treated
as artifacts of the current task.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

TERMINAL_DIRS = ("failed", "completed", "blocked")
ROLE_NAMES = ("planner", "implementer", "auditor", "corrector")
CLAIM_VALUES = {
    "ACCEPT",
    "PARTIAL",
    "REJECT",
    "DATA_FAILED",
    "TEMPORAL_VALIDATION_DATASET_READY",
    "TEMPORAL_VALIDATION_DATASET_PARTIAL",
    "TEMPORAL_VALIDATION_DATASET_FAILED",
    "DIAGNOSTIC_DATASET_READY",
    "DIAGNOSTIC_DATASET_PARTIAL",
    "DIAGNOSTIC_DATASET_FAILED",
    "DATA_READY",
    "DATA_PARTIAL",
    "DATA_FAILED",
    "BOUNDED_WORKER_REPRESENTATION_READY",
}
CLAIM_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:status|verdict|scientific verdict|experiment status)\s*:\s*[`\"]?([A-Z][A-Z0-9_ -]*)[`\"]?\s*$",
    re.IGNORECASE,
)


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_json(path: Path):
    with open(path, encoding="utf-8") as source:
        return json.load(source)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(path.name + ".tmp.%d" % os.getpid())
    with open(temporary, "w", encoding="utf-8", newline="") as target:
        target.write(text)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_status(repo: Path) -> dict[str, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True,
        check=True,
    )
    records = completed.stdout.split(b"\0")
    entries: dict[str, str] = {}
    index = 0
    while index < len(records) - 1:
        row = records[index]
        index += 1
        if len(row) < 4:
            continue
        code = row[:2].decode("ascii", "replace")
        relative = row[3:].decode("utf-8", "surrogateescape")
        if relative:
            entries[relative] = code
    return entries


def allowed_paths(repo: Path, envelope: dict) -> set[str]:
    relative = envelope.get("allowlist_path")
    if not isinstance(relative, str) or not relative:
        return set()
    path = (repo / relative).resolve()
    if repo.resolve() not in path.parents or not path.is_file():
        return set()
    try:
        return {
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    except OSError:
        return set()


def committed_paths(repo: Path, task_id: str) -> tuple[list[str], str]:
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%H", "--grep", f"^{task_id}$"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        if not commit:
            return [], ""
        paths = subprocess.run(
            ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        return sorted(path for path in paths if path), commit
    except (OSError, subprocess.CalledProcessError):
        return [], ""


def artifact_paths(repo: Path, envelope: dict) -> tuple[list[str], str]:
    task_id = str(envelope.get("task_id", ""))
    allowlist = allowed_paths(repo, envelope)
    if envelope.get("status") == "COMPLETED":
        paths, commit = committed_paths(repo, task_id)
        if paths:
            scoped = sorted(set(paths) & allowlist) if allowlist else paths
            return scoped, commit
    baseline = envelope.get("baseline", {}).get("preexisting_paths")
    if not isinstance(baseline, dict) or not allowlist:
        return [], ""
    try:
        changed = set(git_status(repo)) - set(baseline)
    except Exception:
        return [], ""
    return sorted(changed & allowlist), ""


def report_claim(repo: Path, paths: list[str]) -> tuple[str, str]:
    for relative in sorted(path for path in paths if Path(path).name == "REPORT.md"):
        path = repo / relative
        if not path.is_file():
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as source:
                for index, line in enumerate(source):
                    if index >= 120:
                        break
                    match = CLAIM_LINE_RE.fullmatch(line.rstrip("\n"))
                    if not match:
                        continue
                    claim = match.group(1).strip().upper().replace(" ", "_")
                    if claim in CLAIM_VALUES:
                        return claim, relative
        except OSError:
            continue
    return "NOT_DECLARED", ""


def markdown_cell(value) -> str:
    return str(value).replace("|", r"\|").replace("\n", "<br>")


def small_csv_table(path: Path, max_rows: int = 200, max_columns: int = 24) -> str:
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        return ""
    try:
        with open(path, newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            fields = (reader.fieldnames or [])[:max_columns]
            rows = []
            for index, row in enumerate(reader):
                if index >= max_rows:
                    rows.append({field: "…" for field in fields})
                    break
                rows.append(row)
    except Exception:
        return ""
    if not fields:
        return ""
    lines = [
        "| " + " | ".join(markdown_cell(field) for field in fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(markdown_cell(row.get(field, "")) for field in fields)
            + " |"
        )
    return "\n".join(lines)


def role_results(state: Path, envelope: dict):
    task_id = str(envelope.get("task_id", "unknown"))
    results = []
    for role in ROLE_NAMES:
        path = state / "logs" / f"{task_id}-{role}.result.json"
        if not path.is_file():
            continue
        try:
            value = load_json(path)
        except Exception:
            continue
        if isinstance(value, dict):
            results.append((role, value, path))
    last = envelope.get("last_result")
    if isinstance(last, dict) and not any(value == last for _, value, _ in results):
        results.append((str(last.get("role", "last_result")), last, None))
    return results


def transitions(state: Path, task_id: str):
    path = state / "logs" / f"{task_id}.jsonl"
    rows = []
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as source:
                for line in source:
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if value.get("from_state") or value.get("to_state"):
                        rows.append(value)
        except OSError:
            pass
    return rows, path


def render(repo: Path, state: Path, envelope_path: Path, envelope: dict) -> Path:
    task_id = str(envelope.get("task_id") or envelope_path.stem)
    final_status = str(envelope.get("status") or "FAILED_TECHNICAL")
    acceptance = "ACCEPTED" if final_status == "COMPLETED" else "NOT ACCEPTED"
    paths, commit = artifact_paths(repo, envelope)
    claim, claim_path = report_claim(repo, paths)
    results = role_results(state, envelope)
    transition_rows, transition_path = transitions(state, task_id)

    warnings = []
    if final_status != "COMPLETED" and ("READY" in claim or claim == "ACCEPT"):
        warnings.append(
            f"Experiment report claims `{claim}`, but the orchestrator ended as `{final_status}`. The claim is not accepted."
        )
    if not paths:
        warnings.append(
            "No task-scoped artifact paths were reconstructed. Unrelated dirty or untracked repository reports were intentionally excluded."
        )

    lines = [
        f"# MSM terminal report — {task_id}",
        "",
        f"- Generated: `{utc_now()}`",
        f"- FINAL STATUS: `{final_status}`",
        f"- ORCHESTRATOR ACCEPTANCE: `{acceptance}`",
        f"- EXPERIMENT REPORT CLAIM: `{claim}`",
        f"- Attempt: `{envelope.get('attempt', '')}/{envelope.get('max_corrections', '')}`",
        f"- Task hash: `{envelope.get('task_hash', '')}`",
        f"- Envelope: `{envelope_path}`",
        f"- Transition log: `{transition_path}`",
    ]
    if commit:
        lines.append(f"- Implementation commit: `{commit}`")
    if claim_path:
        lines.append(f"- Experiment report: `{repo / claim_path}`")
    if envelope.get("failure_reason"):
        lines += ["", "## Failure reason", "", str(envelope["failure_reason"])]

    lines += ["", "## Final interpretation", ""]
    if final_status == "COMPLETED":
        lines.append("The independent audit passed and the orchestrator accepted the package.")
    elif final_status == "FAILED_TECHNICAL":
        lines.append("The package was not accepted. This is a technical outcome, not a scientific ACCEPT/REJECT verdict.")
    else:
        lines.append("The package was not accepted because an explicitly permitted user research decision is required.")

    if warnings:
        lines += ["", "## Warnings", ""]
        lines.extend(f"- {warning}" for warning in warnings)

    lines += ["", "## Role results", ""]
    if not results:
        lines.append("No role-result JSON files were found.")
    for role, value, path in results:
        lines += [
            f"### {role}",
            "",
            f"- Verdict: `{value.get('verdict', 'UNKNOWN')}`",
            f"- Summary: {value.get('summary', '')}",
        ]
        if path:
            lines.append(f"- Source: `{path}`")
        findings = value.get("findings", [])
        if findings:
            lines.append("- Findings:")
            lines.extend(
                f"  {index}. {finding}"
                for index, finding in enumerate(findings, 1)
            )
        lines.append("")

    lines += ["## State transitions", ""]
    if transition_rows:
        lines += [
            "| Timestamp | Role | From | To |",
            "| --- | --- | --- | --- |",
        ]
        for item in transition_rows:
            lines.append(
                f"| {markdown_cell(item.get('timestamp', ''))} | "
                f"{markdown_cell(item.get('role', ''))} | "
                f"{markdown_cell(item.get('from_state', ''))} | "
                f"{markdown_cell(item.get('to_state', ''))} |"
            )
    else:
        lines.append("No state-transition rows were found.")

    lines += ["", "## Artifacts", ""]
    if paths:
        lines += [
            "| Path | Size, bytes | SHA-256 | Present |",
            "| --- | ---: | --- | --- |",
        ]
        for relative in paths:
            path = repo / relative
            present = path.is_file()
            size = path.stat().st_size if present else ""
            file_digest = sha256(path) if present else ""
            lines.append(
                f"| {markdown_cell(relative)} | {size} | {file_digest} | {'YES' if present else 'NO'} |"
            )
    else:
        lines.append("No task-scoped artifact paths available.")

    for relative in paths:
        if Path(relative).name not in {
            "validation_summary.csv",
            "protocol_reconciliation.csv",
        }:
            continue
        table = small_csv_table(repo / relative)
        if table:
            lines += ["", f"## {Path(relative).name}", "", table]

    lines += ["", "## Runtime references", ""]
    for role in ROLE_NAMES:
        path = state / "logs" / f"{task_id}-{role}.result.json"
        if path.exists():
            lines.append(f"- `{path}`")
    lines += [f"- `{envelope_path}`", f"- `{transition_path}`", ""]

    report = state / "reports" / f"{task_id}.md"
    atomic_text(report, "\n".join(lines))
    return report


def terminal_envelopes(state: Path, task_id: str | None = None):
    values = []
    for directory_name in TERMINAL_DIRS:
        directory = state / directory_name
        if not directory.exists():
            continue
        for path in directory.glob("*.json"):
            try:
                envelope = load_json(path)
            except Exception:
                continue
            if task_id and envelope.get("task_id") != task_id:
                continue
            values.append((path.stat().st_mtime, path, envelope))
    return sorted(values, key=lambda item: item[0])


def scan(repo: Path, state: Path, task_id: str | None = None) -> list[Path]:
    reports = []
    latest = None
    for modified, envelope_path, envelope in terminal_envelopes(state, task_id):
        report = render(repo, state, envelope_path, envelope)
        reports.append(report)
        latest = (modified, report)
    if latest:
        atomic_text(
            state / "reports" / "latest.md",
            latest[1].read_text(encoding="utf-8"),
        )
    return reports


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repo = root / "repo"
        state = root / "state"
        own = repo / "experiments" / "EXP-TEST"
        unrelated = repo / "experiments" / "EXP-OLD"
        own.mkdir(parents=True)
        unrelated.mkdir(parents=True)
        (repo / ".codex").mkdir()
        (repo / ".codex" / "ALLOWLIST.txt").write_text(
            "experiments/EXP-TEST/REPORT.md\n", encoding="utf-8"
        )
        (own / "REPORT.md").write_text("Status: REJECT\n", encoding="utf-8")
        (unrelated / "REPORT.md").write_text(
            "Status: TEMPORAL_VALIDATION_DATASET_READY\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "fixture@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Fixture"], check=True)
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)
        (own / "REPORT.md").write_text("Status: REJECT\nchanged\n", encoding="utf-8")
        (unrelated / "REPORT.md").write_text(
            "Status: TEMPORAL_VALIDATION_DATASET_READY\nchanged\n",
            encoding="utf-8",
        )
        envelope = {
            "task_id": "EXP-TEST",
            "task_hash": "fixture",
            "status": "FAILED_TECHNICAL",
            "attempt": 0,
            "max_corrections": 2,
            "allowlist_path": ".codex/ALLOWLIST.txt",
            "baseline": {
                "preexisting_paths": {
                    "experiments/EXP-OLD/REPORT.md": {}
                }
            },
            "last_result": {
                "role": "planner",
                "verdict": "TECHNICAL_CORRECTION_REQUIRED",
                "findings": ["fixture finding"],
                "summary": "fixture summary",
            },
        }
        envelope_path = state / "failed" / "EXP-TEST-fixture.json"
        envelope_path.parent.mkdir(parents=True)
        envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
        (state / "logs").mkdir(parents=True)
        (state / "logs" / "EXP-TEST.jsonl").write_text(
            json.dumps(
                {
                    "timestamp": utc_now(),
                    "role": "planner",
                    "from_state": "PLANNING",
                    "to_state": "FAILED_TECHNICAL",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        reports = scan(repo, state, "EXP-TEST")
        assert len(reports) == 1
        text = reports[0].read_text(encoding="utf-8")
        assert "EXPERIMENT REPORT CLAIM: `REJECT`" in text
        assert "EXP-OLD" not in text
        assert "TEMPORAL_VALIDATION_DATASET_READY" not in text
        assert "fixture finding" in text
        assert (state / "reports" / "latest.md").is_file()
    print("REPORTER_SELF_TEST_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="/home/nnv/MSM-Research-Lab")
    parser.add_argument(
        "--state-dir",
        default="/home/nnv/.local/state/msm-orchestrator",
    )
    parser.add_argument("--poll", type=int, default=10)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--task-id")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    repo = Path(args.repo)
    state = Path(args.state_dir)
    while True:
        scan(repo, state, args.task_id)
        if args.once or args.task_id:
            return 0
        time.sleep(max(1, args.poll))


if __name__ == "__main__":
    raise SystemExit(main())
