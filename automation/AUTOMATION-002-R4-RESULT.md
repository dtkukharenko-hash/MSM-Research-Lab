# AUTOMATION-002-R4 Result

- task_id: `AUTOMATION-002-R4-REMOVE-DUPLICATE-CORRECTION-DISPATCH`
- original_task_id: `AUTOMATION-002-R3-CORRECTOR-EVIDENCE-AND-INFRA-GUARD`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`
- files changed: `automation/msm_runner.sh`, `automation/AUTOMATION-002-R4-RESULT.md`

## Root cause

The audit/correction loop had two consecutive `case $next` dispatches. The first invoked `msm_correct.sh` with only four arguments, so a technical-correction route failed before the following evidence-gated six-argument dispatch could execute.

## Correction and proof

Removed only the obsolete first dispatch. The loop now has exactly one `case $next` dispatch. Its `CORRECT_R1|CORRECT_R2` route derives the attempt, calls `validate_correction_audit`, records `AUDIT_FAILED` and exits on validation failure, then invokes exactly one corrector with task ID, task hash, starting commit, correction attempt, current diff hash, and audit JSON path, followed by `verify`.

## Tests run

- `bash -n automation/msm_runner.sh` — PASS.
- `bash -n automation/*.sh` — PASS.
- Static audit-loop scan (`awk` from the route assignment through `case $next`) — `dispatch_blocks=1`.
- Static obsolete-call scan — `four_arg_invocations=0`.
- Static retained-call scan — `six_arg_invocations=1`; it includes `"$diff_hash" "$audit_path"`.
- Isolated valid R0 fixture using copied runner/corrector plus mocked Git, audit, bwrap, and Codex boundaries — PASS: exit `0`, exactly one `R1` correction invocation, and both exact findings (`finding-A`, `finding-B`) were present in the correction prompt.
- Isolated valid R1 fixture — PASS: exit `0`, exactly one `R1` and exactly one `R2` correction invocation; no duplicate correction dispatch occurred.
- Isolated R2 technical-failure fixture — PASS: terminal `USER_DECISION_REQUIRED` route, exit `0`, zero corrector invocations.
- Isolated mismatched-audit fixture — PASS: `AUDIT_FAILED`, exit `1`, zero corrector invocations.
- `git diff --check` — PASS.
- Protected Pine integrity check — PASS: SHA-256 remained `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`; it is unstaged. Its pre-existing modification was preserved unchanged.
- Research-file change check — PASS: no research file was modified by this task.

## Known limitations

Behavioral tests used isolated temporary copies and mocked external Git/audit/Codex sandbox boundaries. They did not invoke the installed runner, alter installed files, make commits, push, or change repository state outside the two listed working-tree files.
