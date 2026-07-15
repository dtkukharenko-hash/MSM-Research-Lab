# Current Codex Task

- task_id: `AUTOMATION-003-ENABLE-ALLOWLISTED-RESEARCH-TASKS`
- status: `READY`
- published_at: `2026-07-15`
- target_branch: `main`
- commit_message: `AUTOMATION-003 enable allowlisted research tasks`
- infrastructure_maintenance: `true`

## Objective

Correct the runner so ordinary tasks may modify research files explicitly listed in `.codex/ALLOWLIST.txt`.

At present, `verify()` rejects all `experiments/*` and `docs/*` paths before checking the allowlist, which prevents real research work.

## Hard protections

These paths must remain forbidden even when listed in the allowlist:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- runner infrastructure paths during normal tasks

The protected Pine must remain byte-identical, unstaged, and uncommitted.

Do not change research files, `.codex/RESULT.md`, installed runner copies, Git state, secrets, service files, audit routing, correction limits, or commit policy.

## Allowed changes

- `automation/msm_runner.sh`
- `automation/AUTOMATION-003-RESULT.md`

## Required change

Remove only the blanket rejection of all `experiments/*`, all `docs/*`, and `MEMORY.md` from normal-task verification. Keep explicit allowlist enforcement mandatory. Keep the exact hard protections above.

## Validation

Prove with isolated fixtures that:

1. an allowlisted path under `experiments/` passes;
2. an allowlisted path under `docs/` passes;
3. a non-allowlisted research path fails;
4. `docs/DEFINITIONS.md` fails even if allowlisted;
5. the protected Pine fails if changed or staged;
6. runner infrastructure fails in a normal task even if allowlisted.

Also run:

- `bash -n automation/msm_runner.sh`
- `bash -n automation/*.sh`
- `git diff --check`

Write `automation/AUTOMATION-003-RESULT.md` with status `IMPLEMENTED_AWAITING_MANUAL_COMMIT` only if all checks pass. Leave changes uncommitted.