# MSM Research Lab — Codex Operating Rules

These rules apply to the entire repository.

## Required reading

Before changing anything, read:

1. `PROJECT_INSTRUCTIONS.md`
2. `.codex/TASK.md`
3. Any experiment or research documents explicitly referenced by the current task

`PROJECT_INSTRUCTIONS.md` is mandatory and cannot be overridden by a task.

## Start procedure

1. Run `git pull --ff-only origin main`.
2. Run `git status --short`.
3. Read `.codex/TASK.md`.
4. Continue only when its status is `READY`.
5. If the task status is not `READY`, make no repository changes and report `NO_ACTIVE_TASK`.

## Repository safety

- Preserve all unrelated local changes.
- Never stage or commit files that are not part of the current task.
- Never stage or commit the known unrelated local file:
  `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- Never modify `docs/DEFINITIONS.md`.
- Never delete rejected, failed, superseded, or snapshot research artifacts unless the current task explicitly requires a new snapshot and preserves the old result.
- Do not rewrite history or force-push.
- Work on `main` unless `.codex/TASK.md` explicitly requires another existing branch.

## Execution rules

- Perform the complete task from `.codex/TASK.md`; do not substitute a smaller task.
- Use causal calculations only when required by the research task.
- Do not introduce lookahead, repainting, future pivots, or manually selected evidence.
- Do not use additional datasets, tools, indicators, or periods unless allowed by the task.
- Keep generated artifacts deterministic and reproducible.
- Run all validations and acceptance tests requested by the task.
- Inspect `git diff` and `git status --short` before committing.
- If an acceptance condition fails, record the failure honestly; do not hardcode a passing answer.

## Commit and result protocol

Unless the task explicitly says not to commit or push:

1. Commit only the implementation files required by the task.
2. Use the commit message specified in `.codex/TASK.md`.
3. Push the implementation commit to `origin/main`.
4. Record the result in `.codex/RESULT.md` using the required structure below.
5. Include the implementation commit SHA, push status, tests, acceptance results, artifacts, warnings, and final `git status --short`.
6. Commit only `.codex/RESULT.md` with message:
   `codex: record result <task_id>`
7. Push the result commit to `origin/main`.

Do not place secrets, credentials, tokens, or private keys in task or result files.

## Required `.codex/RESULT.md` fields

- `task_id`
- `task_status`
- `implementation_commit_sha`
- `implementation_push_status`
- `result_commit_status`
- `summary`
- `created_files`
- `modified_files`
- `tests_run`
- `acceptance_results`
- `metrics`
- `warnings`
- `final_git_status`
- `unrelated_changes_preserved`

The final response in Codex should be brief and direct the user to `.codex/RESULT.md`.
