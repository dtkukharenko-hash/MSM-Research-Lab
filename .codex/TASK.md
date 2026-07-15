# Current Codex Task

- task_id: `AUTOMATION-002-R1-FAST-LOCAL-AUDIT-CORRECTION-FIX`
- status: `READY`
- published_at: `2026-07-15`
- target_branch: `main`
- commit_message: `AUTOMATION-002-R1 fix fast local audit and bounded correction loop`
- infrastructure_maintenance: `true`

## Objective

Replace the rejected local draft from `AUTOMATION-002` with a safe, faster Ubuntu runner. This is a one-time manual bootstrap. Do not execute it through systemd.

## Mandatory protections

Never modify, stage, or commit:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- research files outside a future task's explicit allowlist
- secrets, credentials, SSH/Codex auth material, or files outside the repository

The existing Pine modification must remain byte-identical, unstaged, and uncommitted. Do not run `git pull`, `git add`, `git commit`, `git push`, `sudo`, `systemctl`, or installation commands.

## Rejected-draft defects that must be fixed

1. Codex in `workspace-write` cannot write `.codex/` in this environment. Do not require implementation or correction Codex to create or update `.codex/RESULT.md`.
2. The shell runner must perform `git pull --ff-only origin main` before reading `status`, `task_id`, task hash, allowlist, or deciding whether the task is infrastructure maintenance.
3. Do not run two correction agents for one retry. For each failed audit, invoke exactly one correction Codex process, then validate and audit its resulting worktree directly. Required sequence: implementation R0 -> audit R0 -> correction R1 -> audit R1 -> correction R2 -> audit R2 -> stop/commit.
4. The normal implementation loop must not invoke a second implementation process after `msm_correct.sh` already edited the worktree.
5. The shell-owned result record must not depend on Codex writing `.codex/`. Store runtime result/audit records under `/home/nnv/.local/state/msm-runner/`. After technical PASS, the shell may write/update `.codex/RESULT.md` itself before staging, using verified runtime data. Codex must never write this file.
6. Preserve the existing two-commit workflow: implementation commit, then result-metadata commit with the actual implementation SHA and push status.
7. Validate the actual installed-copy design: service executes `/usr/local/lib/msm-runner/msm_runner.sh`; helper scripts are installed beside it; repository source may be edited without changing the running process.
8. Normal research tasks must never modify runner infrastructure. Infrastructure tasks must return `MANUAL_BOOTSTRAP_REQUIRED` only after the latest task has been pulled and parsed.
9. Keep the one-minute timer already committed.
10. Do not claim validation passed when a command failed. Record exact limitations.

## Required architecture

### Shell runner

The installed shell runner owns:

- non-blocking lock;
- preflight allowing only the exact protected Pine modification;
- Git pull before task parsing;
- task ID/hash and duplicate detection;
- allowlist parsing and protected-path enforcement;
- deterministic worktree diff hash;
- attempt state/history;
- invoking implementation, audit, and correction processes;
- shell-generated result metadata;
- explicit-path staging, commits, and pushes.

Never use `git add .` or `git add -A`.

### Implementation Codex

Run once for R0 with:

- `workspace-write`;
- approval `never`;
- `.git` read-only through Bubblewrap;
- exact task allowlist;
- no requirement to write `.codex/RESULT.md`.

Capture JSONL, stderr, and final response only under runtime state/log paths.

### Audit Codex

Run independently after R0/R1/R2:

- read-only repository;
- no trust in implementation narrative;
- inspect task, actual diff/status, tests, artifacts, and project constraints;
- write strict JSON only to runtime state.

Required fields:

- `task_id`
- `original_task_id`
- `attempt`
- `task_hash`
- `starting_commit`
- `worktree_diff_hash`
- `audit_status`
- `technical_pass`
- `research_decision_required`
- `blocking_findings`
- `warnings`
- `recommended_action`
- `finished_at`

Allowed statuses: `PASS`, `USER_DECISION_REQUIRED`, `TECHNICAL_CORRECTION_REQUIRED`, `AUDIT_FAILED`.

### Correction routing

- R0 technical failure -> invoke one correction process R1 -> validate -> audit R1.
- R1 technical failure -> invoke one correction process R2 -> validate -> audit R2.
- R2 technical failure -> `USER_DECISION_REQUIRED`.
- Visual review, holdout, definition, hypothesis, acceptance-criteria, interpretation, or research judgment -> stop immediately with `USER_DECISION_REQUIRED` and no correction.
- `AUDIT_FAILED` means stop without commit.
- Do not broaden the original allowlist.

### Result and commit flow

Codex cannot write `.codex/`, so the shell creates a deterministic `.codex/RESULT.md` from verified runtime state only after an allowed audit outcome.

Commit only for:

- `PASS` with `technical_pass=true`; or
- `USER_DECISION_REQUIRED` with `technical_pass=true` when implementation is technically valid and later user judgment remains.

Two commits are required:

1. implementation files plus shell-generated RESULT with `implementation_commit_sha: PENDING_SHELL_COMMIT`;
2. RESULT metadata containing the actual first commit SHA and push status.

The protected Pine must never be staged.

## Files

Inspect and revise as needed:

- `automation/msm_runner.sh`
- `automation/msm_audit.sh`
- `automation/msm_correct.sh`
- `automation/install.sh`
- `automation/README.md`
- `automation/runner.service`
- `automation/runner.timer`
- `automation/state.json`
- `automation/state.example.json`

Do not attempt to update `.codex/RESULT.md` during this manual Codex run. Put the manual bootstrap report in `automation/AUTOMATION-002-R1-RESULT.md` instead.

## Validation

Run and report exact outcomes:

- `bash -n automation/*.sh` individually;
- `bash automation/install.sh --dry-run`;
- runner `--dry-run`;
- duplicate skip simulation;
- infrastructure task simulation proving `MANUAL_BOOTSTRAP_REQUIRED` after pull/task parse logic;
- R0 technical failure routes to exactly one R1 correction;
- R1 technical failure routes to exactly one R2 correction;
- R2 technical failure stops with `USER_DECISION_REQUIRED`;
- research-decision case performs zero corrections;
- scans proving no Codex process writes `.codex/` or mutates Git;
- scans proving no `git add .`/`git add -A`;
- scans proving protected Pine and `docs/DEFINITIONS.md` exclusions;
- `git diff --check`;
- confirmation that only the pre-existing Pine is modified among research files.

Tests must not commit, push, install, start services, or alter the protected Pine.

## Manual result

Write `automation/AUTOMATION-002-R1-RESULT.md` containing:

- task ID and status `IMPLEMENTED_AWAITING_MANUAL_COMMIT`;
- files changed;
- architecture summary;
- exact validation commands/outcomes;
- proof that each retry invokes exactly one correction agent;
- known limitations;
- exact manual review, commit, installation, and timer-enable commands.

Leave all intended changes uncommitted.