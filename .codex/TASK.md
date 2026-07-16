# Current Codex Task

- task_id: `AUTOMATION-008-PREEXISTING-DIRTY-BASELINE`
- status: `READY`
- published_at: `2026-07-16`
- target_branch: `main`
- infrastructure_maintenance: `true`
- commit_message: `AUTOMATION-008 preserve pre-existing dirty baseline`

## Objective

Allow the production orchestrator to complete tasks when a protected file was already modified before task start, provided that file remains byte-identical, unstaged, and uncommitted throughout the task.

## Required implementation

1. Capture the initial worktree baseline before the first role runs, including the protected Pine SHA256 and the set of pre-existing modified/untracked paths.
2. Pass sufficient non-secret baseline context to planner, implementer, auditor, and corrector so they can distinguish pre-existing changes from task-created changes.
3. A pre-existing protected Pine modification with the same recorded SHA256 must not cause `TECHNICAL_CORRECTION_REQUIRED` or `USER_DECISION_REQUIRED` by itself.
4. Any byte change, staging, deletion, rename, chmod, or commit involving the protected Pine after task start must still fail closed.
5. Validation must evaluate the task delta relative to the captured baseline, not require an otherwise clean repository.
6. `TECHNICAL_CORRECTION_REQUIRED` must enter the existing bounded correction path while attempts remain. Only `USER_DECISION_REQUIRED` may transition directly to `BLOCKED_USER_DECISION`.
7. Preserve the maximum of two correction attempts, external sandbox, private runtime, authentication handling, read-only `.git`, allowlist enforcement, commit checks, and push checks.
8. Do not automatically modify, restore, stage, commit, delete, or clean any pre-existing user file.

## Regression fixture

Reproduce the SMOKE-005 condition:

- protected Pine is already modified before task start;
- its initial SHA256 remains unchanged;
- implementer creates only one allowlisted file;
- no files are staged.

Expected behavior:

- implementer and auditor evaluate only the task delta;
- the unchanged pre-existing Pine is reported as preserved, not as a task violation;
- the task may proceed to commit and push only the allowlisted file.

Also verify:

- changing the protected Pine after baseline capture is rejected;
- staging the protected Pine is rejected;
- creating a non-allowlisted path after baseline capture is rejected;
- `TECHNICAL_CORRECTION_REQUIRED` invokes corrector R1/R2 rather than user blocking;
- `USER_DECISION_REQUIRED` still blocks immediately.

## Allowed changes

Only:

- `automation/msm_orchestrator.py`
- `automation/msm_worker.sh`
- `automation/verify_orchestrator.sh`
- `automation/AUTOMATION-008-RESULT.md`

## Hard protections

Never modify, stage, commit, delete, rename, chmod, or rewrite:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `.codex/RESULT.md`
- `.git` internals
- any research document or artifact
- feeder files or services
- credential source files

The protected Pine is intentionally allowed to be dirty before execution. It must remain byte-identical to the SHA256 captured at task start, unstaged, and uncommitted.

## Validation

Run and record at minimum:

- `bash -n automation/msm_worker.sh automation/verify_orchestrator.sh`;
- Python syntax validation for `automation/msm_orchestrator.py`;
- deterministic fixtures for baseline-relative path validation;
- deterministic fixtures for both correction and user-decision transitions;
- `git diff --check`;
- confirmation that only the four allowed files changed;
- confirmation that the protected Pine remained byte-identical and unstaged.

## Result contract

Write `automation/AUTOMATION-008-RESULT.md` only after all validations pass. Set status `IMPLEMENTED_AWAITING_MANUAL_COMMIT`. Leave implementation changes unstaged and uncommitted for the deterministic infrastructure bootstrap.
