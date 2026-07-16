# Current Codex Task

- task_id: `AUTOMATION-004-R1-INSTALLER-OWNERSHIP-AND-MODE-GUARD`
- status: `READY`
- published_at: `2026-07-16`
- target_branch: `main`
- commit_message: `AUTOMATION-004-R1 fix installer ownership and mode guard`
- infrastructure_maintenance: `true`
- original_task_id: `AUTOMATION-004-LOCAL-ORCHESTRATOR-V1`
- correction_attempt: `1`

## Objective

Correct the purely technical installer defects found in the completed AUTOMATION-004 implementation without changing orchestrator definitions, state-machine semantics, research logic, hypotheses, holdout usage, visual judgments, or project research decisions.

The installed service runs as user `nnv`, but the current installer creates the 0700 runtime state tree without setting owner/group. When the installer is run through sudo, those directories become root-owned and the `nnv` service cannot access them. The argument parser also accepts unsupported mode combinations even though the original task requires exactly two supported invocation modes.

## Required correction

1. In `automation/install_orchestrator.sh`, create and repair the complete runtime state tree with owner `nnv`, group `nnv`, and directory mode `0700`, including pre-existing directories from a prior failed/root-owned installation.
2. Keep runtime state files owned by `nnv` where the installer creates or repairs any files; do not delete existing queue, running, completed, blocked, failed, or log contents.
3. Accept exactly these two invocation forms and reject all others with nonzero exit status:
   - `--install --test-mode`
   - `--activate-production`
4. Preserve idempotency: repeated execution must retain correct ownership/modes and must not damage runtime state.
5. Add an isolated installer fixture that uses temporary install/state roots and verifies:
   - both valid invocation forms;
   - rejection of unsupported combinations;
   - all required runtime directories are owned by the selected run user/group and mode `0700`;
   - a second run remains successful and preserves a sentinel state file.
6. Record exact commands and outcomes in `automation/AUTOMATION-004-R1-RESULT.md`.

## Allowed changes

Only:

- `automation/install_orchestrator.sh`
- `automation/AUTOMATION-004-R1-RESULT.md`

No other file may be created, modified, staged, committed, renamed, deleted, or chmodded.

## Hard protections

Never modify, stage, commit, delete, rename, chmod, rewrite, or include in the allowlist:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `.codex/RESULT.md`
- `.git` internals
- any research document or artifact
- any orchestrator state-machine, worker, verifier, service-unit, or bootstrap file other than the installer explicitly allowed above

The protected Pine may already be modified locally. It must remain byte-identical, unstaged, and uncommitted.

## Research constraints

This is a technical infrastructure correction only. Do not change definitions, hypotheses, acceptance criteria, holdout boundaries, visual-review fields, detector logic, or any research interpretation. If any such change appears necessary, stop and report `BLOCKED_USER_DECISION` rather than implementing it.

## Validation

Run and record at minimum:

- `bash -n automation/install_orchestrator.sh`
- isolated temporary-root fixture covering both valid modes and invalid combinations
- ownership and `0700` checks for every runtime directory
- idempotent second-run check preserving a sentinel file
- `git diff --check`
- confirmation that only the two allowed files changed
- confirmation that `docs/DEFINITIONS.md` and the protected Pine are unchanged and unstaged

## Result contract

Write `automation/AUTOMATION-004-R1-RESULT.md` only after all validations pass. Set its status to `IMPLEMENTED_AWAITING_MANUAL_COMMIT` and leave changes unstaged and uncommitted for deterministic infrastructure bootstrap handling.
