# Current Codex Task

- task_id: `SMOKE-001-ORCHESTRATOR-REAL-CYCLE`
- status: `READY`
- published_at: `2026-07-16`
- target_branch: `main`
- infrastructure_maintenance: `false`
- commit_message: `SMOKE-001 real orchestrator cycle`

## Objective

Prove that the production feeder and local orchestrator can complete one real end-to-end Codex cycle without manual enqueue, without infrastructure changes, and without touching research definitions or protected artifacts.

## Required implementation

Create exactly one file:

- `automation/SMOKE-001-RESULT.md`

Its complete content must be:

```markdown
# SMOKE-001 Result

- status: `PASS`
- task_id: `SMOKE-001-ORCHESTRATOR-REAL-CYCLE`
- execution: `production feeder -> planner -> implementer -> auditor -> commit -> push`

The local MSM orchestrator completed the real technical smoke cycle.
```

Do not create or modify any other file.

## Allowed changes

Only:

- `automation/SMOKE-001-RESULT.md`

The exact same path is the sole entry in `.codex/ALLOWLIST.txt`.

## Validation

Before returning PASS, verify:

- the file exists and matches the required content exactly;
- `git diff --check` passes;
- the protected Pine remains byte-identical, unstaged, and uncommitted;
- `docs/DEFINITIONS.md` remains unchanged;
- no other tracked or untracked path was created or modified by this task;
- no files are staged.

## Hard protections

Never modify, stage, commit, delete, rename, chmod, rewrite, or include in the allowlist:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `.codex/RESULT.md`
- `.git` internals
- any research document or artifact
- any orchestrator, feeder, runner, service, installer, verifier, or bootstrap file

## Research constraints

This is a technical smoke test only. Do not access holdout data, perform visual review, change a definition or hypothesis, or make a research decision.

## Result contract

Planner, implementer, and auditor must use the required JSON role contract. The implementer creates only the allowed result file and leaves it unstaged. The auditor returns PASS only after every validation succeeds. The orchestrator must perform the final allowlist check, commit once, and push to `main`.
