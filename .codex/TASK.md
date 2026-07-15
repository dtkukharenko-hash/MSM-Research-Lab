# Current Codex Task

- task_id: `AUTOMATION-002-R4-REMOVE-DUPLICATE-CORRECTION-DISPATCH`
- original_task_id: `AUTOMATION-002-R3-CORRECTOR-EVIDENCE-AND-INFRA-GUARD`
- correction_sequence: `1`
- status: `READY`
- published_at: `2026-07-15`
- target_branch: `main`
- commit_message: `AUTOMATION-002-R4 remove duplicate correction dispatch`
- infrastructure_maintenance: `true`

## Objective

Correct one purely technical defect in the committed R3 runner. Do not redesign or broadly rewrite the automation.

`automation/msm_runner.sh` currently contains two consecutive `case $next` dispatch blocks inside the audit/correction loop. The first stale block invokes `msm_correct.sh` with only four arguments and before `validate_correction_audit`; the second block contains the intended validated six-argument invocation. Because `msm_correct.sh` requires six arguments, any technical-correction route reaches the stale block first and fails before the evidence-gated dispatch can run.

Remove the stale duplicate dispatch block and retain exactly one dispatch path that validates the exact audit evidence before invoking exactly one corrector with:

`msm_correct.sh TASK_ID TASK_HASH STARTING_COMMIT CORRECTION_ATTEMPT WORKTREE_DIFF_HASH AUDIT_JSON_PATH`

## Mandatory protections

Never modify, stage, or commit:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- any research file
- `.codex/RESULT.md`
- secrets, credentials, SSH/Codex auth material, or files outside the repository

The protected Pine modification must remain byte-identical, unstaged, and uncommitted.

Do not run `git pull`, `git add`, `git commit`, `git push`, `sudo`, `systemctl`, installation commands, or modify installed copies under `/usr/local/lib/msm-runner`.

## Allowed changes

Only:

- `automation/msm_runner.sh`
- `automation/AUTOMATION-002-R4-RESULT.md`

## Required correction

1. Delete the obsolete first `case $next` block that calls:

   `"$CORRECTOR" "$task_id" "$task_hash" "$start_sha" "$next"`

2. Keep one and only one `case $next` block.
3. For `CORRECT_R1` and `CORRECT_R2`, that block must:
   - derive correction attempt `1` or `2`;
   - call `validate_correction_audit` first;
   - stop as `AUDIT_FAILED` on evidence mismatch;
   - invoke exactly one corrector with all six required arguments, including current diff hash and exact audit JSON path;
   - call `verify` after successful correction.
4. Do not change definitions, schemas, retry policy, route policy, commit policy, allowlist behavior, research constraints, or correction-count limits.

## Validation

Run and report exact outcomes:

- `bash -n automation/msm_runner.sh`
- `bash -n automation/*.sh`
- static scan proving only one `case $next` dispatch block remains in the audit loop
- static scan proving no four-argument corrector invocation remains
- static scan proving the retained corrector invocation includes diff hash and audit path
- isolated valid R0 audit fixture proving exactly one R1 corrector invocation and exact findings reach the prompt
- invalid or mismatched audit fixture proving `AUDIT_FAILED` and zero corrector invocations
- valid R1 audit fixture proving exactly one R2 corrector invocation
- R2 technical failure proving `USER_DECISION_REQUIRED` and zero further corrector invocations
- `git diff --check`
- confirmation that no research file was changed and the protected Pine remains byte-identical, unstaged, and uncommitted

Tests must not commit, push, install, enable services, modify installed runner copies, or alter protected files.

## Manual report

Write `automation/AUTOMATION-002-R4-RESULT.md` containing:

- task ID and original task ID
- status `IMPLEMENTED_AWAITING_MANUAL_COMMIT` only if every mandatory validation passes
- exact files changed
- root cause
- exact test commands and results
- proof of one evidence-gated correction dispatch
- known limitations

Leave all changes uncommitted.
