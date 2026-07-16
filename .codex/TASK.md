# Current Codex Task

- task_id: `AUTOMATION-007-OUTER-SANDBOX-ONLY`
- status: `READY`
- published_at: `2026-07-16`
- target_branch: `main`
- infrastructure_maintenance: `true`
- commit_message: `AUTOMATION-007 use outer sandbox only`

## Objective

Remove the nested Codex sandbox conflict while preserving the external `bwrap` boundary, private runtime, authentication handling, read-only Git metadata, role contract, timeout handling, and final allowlist enforcement.

## Required implementation

1. In `automation/msm_worker.sh`, keep the existing outer `bwrap` invocation as the only operating-system sandbox.
2. Invoke Codex with its internal sandbox disabled so it does not start a second `bwrap` inside the outer sandbox.
3. Keep the repository bind and the explicit read-only bind of `$REPO/.git` unchanged.
4. Keep private `HOME`, `XDG_*`, `TMPDIR`, runtime output, and copied credential handling unchanged.
5. Preserve the prohibition on Git mutation commands and the existing JSON role contract.
6. Do not weaken orchestrator-side allowlist validation, protected-file checks, commit checks, or push checks.
7. Add deterministic verification proving:
   - the worker can read the task and allowlist through Codex tools;
   - the previous `Can't mkdir /tmp/.git: Read-only file system` error is absent;
   - `$REPO/.git` remains unwritable inside the outer sandbox;
   - files outside the task allowlist are rejected by the orchestrator validation layer;
   - credentials are not printed or stored in repository files or logs.

## Allowed changes

Only:

- `automation/msm_worker.sh`
- `automation/verify_orchestrator.sh`
- `automation/AUTOMATION-007-RESULT.md`

## Hard protections

Never modify, stage, commit, delete, rename, chmod, or rewrite:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `.codex/RESULT.md`
- `.git` internals
- any research document or artifact
- feeder files or services
- credential source files

The protected Pine may already be modified locally. It must remain byte-identical, unstaged, and uncommitted.

## Validation

Run and record at minimum:

- `bash -n automation/msm_worker.sh automation/verify_orchestrator.sh`
- isolated worker fixtures for task reading and `.git` write denial;
- confirmation that no nested-sandbox `/tmp/.git` failure occurs;
- confirmation that credentials do not appear in output;
- `git diff --check`;
- confirmation that only the three allowed files changed.

## Result contract

Write `automation/AUTOMATION-007-RESULT.md` only after validation passes. Set status `IMPLEMENTED_AWAITING_MANUAL_COMMIT`. Leave changes unstaged and uncommitted for the deterministic infrastructure bootstrap.
