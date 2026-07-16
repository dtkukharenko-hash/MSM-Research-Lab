# Current Codex Task

- task_id: `AUTOMATION-004-R2-WRITABLE-CODEX-RUNTIME`
- status: `READY`
- published_at: `2026-07-16`
- original_task_id: `AUTOMATION-004-LOCAL-ORCHESTRATOR-V1`
- correction_attempt: `2`
- target_branch: `main`
- commit_message: `AUTOMATION-004-R2 writable Codex runtime`
- infrastructure_maintenance: `true`

## Objective

Correct the worker sandbox so the installed Codex CLI can initialize its own runtime files while the repository Git metadata remains read-only and all task allowlist protections remain unchanged.

## Required correction

1. In `automation/msm_worker.sh`, create a per-task private runtime directory under the existing MSM orchestrator state tree.
2. Provide writable values for `HOME`, `XDG_CACHE_HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, and `TMPDIR` inside that private runtime directory when invoking Codex.
3. Bind only those private runtime directories writable inside `bwrap`.
4. Keep the repository mounted writable only as currently required for allowlisted implementation files.
5. Keep `$REPO/.git` explicitly read-only.
6. Preserve the existing role contract, timeout, output paths, model invocation, and prohibition on Git mutation commands.
7. Do not make the host home directory or any credential directory broadly writable inside the sandbox.
8. Add deterministic verification proving that the worker reaches Codex initialization without the previous read-only filesystem error and that `.git` remains read-only.

## Allowed changes

Only:

- `automation/msm_worker.sh`
- `automation/verify_orchestrator.sh`
- `automation/AUTOMATION-004-R2-RESULT.md`

No other file may be created, modified, staged, committed, renamed, deleted, or chmodded.

## Hard protections

Never modify, stage, commit, delete, rename, chmod, rewrite, or include in any allowlist:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `.codex/RESULT.md`
- `.git` internals
- any research document or artifact
- feeder files or feeder services

The protected Pine may already be modified locally. It must remain byte-identical, unstaged, and uncommitted.

## Validation

Run and record at minimum:

- `bash -n automation/msm_worker.sh automation/verify_orchestrator.sh`
- an isolated worker fixture using a temporary runtime root;
- confirmation that Codex runtime paths are writable inside the sandbox;
- confirmation that repository `.git` remains read-only inside the sandbox;
- confirmation that the prior `failed to initialize in-process app-server client: Read-only file system` failure is absent;
- `git diff --check`;
- confirmation that only the three allowed files changed;
- confirmation that protected files are unchanged and unstaged.

## Result contract

Write `automation/AUTOMATION-004-R2-RESULT.md` only after all validations pass. Set status `IMPLEMENTED_AWAITING_MANUAL_COMMIT`. Leave implementation changes unstaged and uncommitted for the deterministic infrastructure bootstrap.