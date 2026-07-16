# Current Codex Task

- task_id: `AUTOMATION-006-CODEX-AUTH-RUNTIME`
- status: `READY`
- published_at: `2026-07-16`
- target_branch: `main`
- infrastructure_maintenance: `true`
- commit_message: `AUTOMATION-006 provide Codex auth to private runtime`

## Objective

Allow the sandboxed Codex worker to authenticate while preserving the private writable runtime, read-only Git metadata, narrow repository permissions, and existing role contract.

## Required implementation

1. In `automation/msm_worker.sh`, locate the existing Codex credential material from the service account's normal Codex home without printing its contents.
2. Before entering `bwrap`, provision only the minimum required credential/configuration files into the per-task private runtime Codex directory.
3. Use file mode `0600` for credential files and directory mode `0700` for their parent directories.
4. Point Codex at that private runtime location using the supported runtime environment expected by the installed CLI.
5. Do not bind the complete host home directory into the sandbox.
6. Do not place credentials in the repository, task package, role output, JSONL logs, journal, command-line prompt, or Git history.
7. Fail closed with a clear non-secret error when credentials are absent or unreadable.
8. Keep `$REPO/.git` explicitly read-only and preserve all existing writable runtime directories.
9. Preserve timeout handling, role JSON contract, output handling, model invocation, and the prohibition on Git mutation commands.

## Validation

Extend `automation/verify_orchestrator.sh` with isolated fixtures proving:

- the worker receives usable credential material inside its private runtime;
- credential contents never appear in stdout, stderr, generated JSONL, or verification output;
- copied credential files are `0600` and containing directories are `0700`;
- a missing credential produces a controlled non-secret failure;
- `.git` remains read-only inside `bwrap`;
- repository and installed worker logic remain deterministic;
- no credential or runtime file is created under the repository;
- `bash -n automation/msm_worker.sh automation/verify_orchestrator.sh` passes;
- `git diff --check` passes.

The live validation may verify authenticated Codex initialization, but must not print or record credential values.

## Allowed changes

Only:

- `automation/msm_worker.sh`
- `automation/verify_orchestrator.sh`
- `automation/AUTOMATION-006-RESULT.md`

## Hard protections

Never modify, stage, commit, delete, rename, chmod, rewrite, or include in any allowlist:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `.codex/RESULT.md`
- `.git` internals
- any research document or artifact
- feeder files or services
- credential files outside the private runtime copy operation

The protected Pine may already be modified locally. It must remain byte-identical, unstaged, and uncommitted.

## Result contract

Write `automation/AUTOMATION-006-RESULT.md` only after all validation passes. Set status `IMPLEMENTED_AWAITING_MANUAL_COMMIT`. Record commands and non-secret outcomes only. Leave changes unstaged and uncommitted for deterministic infrastructure bootstrap handling.
