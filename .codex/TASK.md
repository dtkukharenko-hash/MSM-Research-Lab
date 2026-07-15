# Current Codex Task

- task_id: `AUTOMATION-002-R4-REMOVE-DUPLICATE-CORRECTION-DISPATCH`
- original_task_id: `AUTOMATION-002-R3-CORRECTOR-EVIDENCE-AND-INFRA-GUARD`
- correction_sequence: `1`
- status: `COMPLETED`
- published_at: `2026-07-15`
- completed_at: `2026-07-15`
- completion_commit: `1570a5de793bc7f51bde8d9705955ef8bab7991f`
- target_branch: `main`
- commit_message: `AUTOMATION-002-R4 remove duplicate correction dispatch`
- infrastructure_maintenance: `true`

## Objective

Correct one purely technical defect in the committed R3 runner. Do not redesign or broadly rewrite the automation.

`automation/msm_runner.sh` contained two consecutive `case $next` dispatch blocks inside the audit/correction loop. The first stale block invoked `msm_correct.sh` with only four arguments and before `validate_correction_audit`; the second block contained the intended validated six-argument invocation. Because `msm_correct.sh` requires six arguments, any technical-correction route reached the stale block first and failed before the evidence-gated dispatch could run.

The stale duplicate dispatch block was removed. Exactly one dispatch path now validates the exact audit evidence before invoking exactly one corrector with:

`msm_correct.sh TASK_ID TASK_HASH STARTING_COMMIT CORRECTION_ATTEMPT WORKTREE_DIFF_HASH AUDIT_JSON_PATH`

## Completion

Implementation commit:

`1570a5de793bc7f51bde8d9705955ef8bab7991f`

Result report:

`automation/AUTOMATION-002-R4-RESULT.md`

Validated outcomes:

- `bash -n automation/msm_runner.sh` — PASS.
- `bash -n automation/*.sh` — PASS.
- Exactly one `case $next` dispatch remains.
- No obsolete four-argument corrector invocation remains.
- Exactly one evidence-gated six-argument corrector invocation remains.
- Valid R0 fixture produced exactly one R1 correction.
- Valid R1 fixture produced exactly one R2 correction.
- Mismatched audit evidence produced `AUDIT_FAILED` with zero corrector invocations.
- R2 technical failure produced `USER_DECISION_REQUIRED` with no further correction.
- `git diff --check` — PASS.
- No research file was changed by the task.
- The pre-existing protected Pine modification remained unstaged, uncommitted, and byte-identical.

## Mandatory protections

Never modify, stage, or commit:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- secrets, credentials, SSH/Codex auth material, or files outside the repository

The protected Pine modification must remain byte-identical, unstaged, and uncommitted.
