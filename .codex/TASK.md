# Current Codex Task

- task_id: `AUTOMATION-002-FAST-LOCAL-AUDIT-AND-CORRECTION`
- status: `READY`
- published_at: `2026-07-15`
- target_branch: `main`
- commit_message: `AUTOMATION-002 add fast local audit and bounded correction loop`

## Objective

Upgrade the MSM automation runner so the fast execution/audit/correction loop runs entirely on the Ubuntu host without waiting for the hourly ChatGPT orchestrator.

This is a one-time manual bootstrap task because it changes the runner itself. Do not execute this task through the active systemd runner. The timer is intentionally disabled.

## Non-negotiable protections

Never modify, stage, or commit:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- any research file outside the explicit task allowlist
- secrets, credentials, SSH material, Codex auth files, or files outside the repository

The existing local Pine modification must remain byte-identical, unstaged, and uncommitted.

Do not use `sudo`. Do not install or start systemd units during this task. Do not run `git pull`, `git add`, `git commit`, or `git push`.

## Required architecture

Implement a bounded local loop with clear separation of roles:

1. Shell runner owns Git pull, validation, staging, commits, pushes, state, locking, attempt limits, and protected-path enforcement.
2. Implementation Codex runs with `workspace-write`, approval `never`, and may modify only task-allowed working files plus `.codex/RESULT.md`.
3. Audit Codex runs separately in read-only mode and must independently inspect the active task, actual worktree diff, tests, artifacts, and project constraints.
4. Audit Codex must not trust the implementation narrative in `.codex/RESULT.md` without checking the actual files and diff.
5. Purely technical audit failures may trigger an immediate local correction attempt without waiting for ChatGPT.
6. At most two automatic correction attempts are allowed for one original task: `R1` and `R2`.
7. After two failed corrections, stop with `USER_DECISION_REQUIRED`.
8. Immediately stop without correction when the issue requires visual review, new holdout use, a definition change, hypothesis change, research interpretation, or any user judgment.

## Self-modification protection

Normal future tasks must never be allowed to modify the runner while it is executing.

Protect at minimum:

- `automation/msm_runner.sh`
- `automation/msm_audit.sh`
- `automation/msm_correct.sh` or equivalent correction component
- `automation/install.sh`
- `automation/runner.service`
- `automation/runner.timer`

Only an explicit manual bootstrap task marked as infrastructure maintenance may modify these files. The systemd runner must refuse such a task and record `MANUAL_BOOTSTRAP_REQUIRED` rather than execute it.

The running shell script must not continue reading mutable source after Codex starts. Use a stable installed copy, immutable execution snapshot, or an equivalent design that prevents the prior `unexpected EOF` self-rewrite failure.

## Fast local audit

Create or revise the automation components so that after implementation completes:

1. shell validates protected hashes, staged state, forbidden paths, result task ID, and explicit allowlist;
2. shell records a deterministic diff snapshot/hash;
3. a separate Codex audit process runs with read-only filesystem access;
4. the auditor writes its decision only to runtime state under `/home/nnv/.local/state/msm-runner/`, not to repository files;
5. audit output is strict JSON and schema-validated before use.

Required audit fields:

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

Allowed statuses:

- `PASS`
- `USER_DECISION_REQUIRED`
- `TECHNICAL_CORRECTION_REQUIRED`
- `AUDIT_FAILED`

Commit and push are allowed only for `PASS`, or `USER_DECISION_REQUIRED` with `technical_pass=true` when the implementation itself is technically valid and only later research judgment is pending.

## Immediate technical correction

For `TECHNICAL_CORRECTION_REQUIRED`:

1. preserve the original task and audit evidence in runtime state;
2. do not commit the failed worktree;
3. invoke a separate correction Codex process immediately;
4. provide the correction process the original task, actual diff, audit JSON, current files, and exact blocking findings;
5. correction may edit only the original task allowlist plus `.codex/RESULT.md`;
6. rerun deterministic validation and independent read-only audit after correction;
7. allow at most attempts `R1` and `R2`;
8. never broaden the allowlist automatically;
9. never change definitions, hypotheses, holdout boundaries, acceptance criteria, or research conclusions;
10. stop and persist `USER_DECISION_REQUIRED` when classification is ambiguous.

Do not create or publish a new GitHub `.codex/TASK.md` for local technical retries. Track retries in runtime state so the active original task ID/hash remains authoritative.

## State and logging

Runtime state remains under:

`/home/nnv/.local/state/msm-runner/`

Persist at minimum:

- original task ID/hash
- current attempt number
- attempt history
- implementation start/end times
- implementation exit code
- audit status and JSON path
- correction start/end times
- blocking findings
- starting and final commit SHAs
- final runner state
- reason for stopping

Keep per-attempt JSONL, stderr, final response, human-readable summary, audit JSON, and deterministic diff hash.

A duplicate task with the same task ID and hash must not run again after `RESULT_PUSHED`, unless an explicit one-shot retry flag is externally set and atomically consumed.

## Timing

Preserve the one-minute timer configuration currently committed:

- first trigger approximately 15 seconds after activation
- subsequent trigger approximately one minute after the service becomes inactive
- small randomized delay

Do not revert it to five minutes.

## Files to inspect and update

At minimum inspect and revise as needed:

- `automation/msm_runner.sh`
- `automation/msm_audit.sh`
- `automation/install.sh`
- `automation/README.md`
- `automation/runner.service`
- `automation/runner.timer`
- `automation/state.json`
- `.codex/AUTOPILOT_POLICY.md`
- `.codex/RESULT.md`

Additional files under `automation/` may be created when separation improves safety and maintainability.

## Validation

Run and report:

- `bash -n` for every shell script under `automation/`
- `systemd-analyze verify` for service and timer where available
- runner `--dry-run`
- a no-task/duplicate-task skip test
- a simulated technical-failure test proving immediate correction routing without Git commit/push
- a simulated second-failure test proving the two-correction limit and `USER_DECISION_REQUIRED`
- a simulated research-decision case proving no correction is attempted
- a self-modification task simulation proving `MANUAL_BOOTSTRAP_REQUIRED`
- scans proving no `git add .` or `git add -A`
- scans proving the protected Pine and `docs/DEFINITIONS.md` exclusions
- scans proving audit Codex is read-only
- scans proving implementation and correction Codex cannot perform Git mutation
- confirmation that only the pre-existing protected Pine remains modified among research files
- confirmation that no secret/auth file is included

Tests must not push, commit, install units, or alter the protected Pine.

## Result requirements

Update `.codex/RESULT.md` with:

- task ID `AUTOMATION-002-FAST-LOCAL-AUDIT-AND-CORRECTION`
- status `IMPLEMENTED_AWAITING_MANUAL_COMMIT`
- files created/modified
- architecture summary
- all validation commands and exact outcomes
- simulated correction-loop outcomes
- explicit confirmation that the protected Pine and research files were not modified
- exact manual bootstrap commit/install commands
- known limitations

Leave all intended changes uncommitted for manual review. Do not attempt Git mutation or systemd installation from Codex.
