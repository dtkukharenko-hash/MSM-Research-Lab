# AUTOMATION-003 Result

- task_id: `AUTOMATION-003-ENABLE-ALLOWLISTED-RESEARCH-TASKS`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`
- scope: `automation/msm_runner.sh`, `automation/AUTOMATION-003-RESULT.md`

## Change

Removed normal-task verification's blanket rejections for `experiments/*`, `docs/*`, and `MEMORY.md`. Explicit `.codex/ALLOWLIST.txt` matching remains mandatory. `docs/DEFINITIONS.md`, the protected EXP009A Pine hash/staging checks, normal-task infrastructure protection, and the general no-staged-changes check are unchanged.

## Validation

All checks passed:

- Isolated fixture: allowlisted `experiments/EXP-TEST/result.md` passes.
- Isolated fixture: allowlisted `docs/RESEARCH_NOTE.md` passes.
- Isolated fixture: non-allowlisted `experiments/EXP-UNLISTED/result.md` fails with `outside allowlist`.
- Isolated fixture: allowlisted `docs/DEFINITIONS.md` fails with `forbidden path changed`.
- Isolated fixture: protected Pine fails when its expected hash differs, and separately fails when simulated as staged.
- Isolated fixture: allowlisted `automation/msm_runner.sh` fails for a normal task with `normal task cannot modify infrastructure path`.
- `bash -n automation/msm_runner.sh`
- `bash -n automation/*.sh`
- `git diff --check`

## Protection record

The existing protected Pine worktree modification was not changed, staged, or committed. Its SHA-256 after validation was:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

## Worktree

Edits are intentionally unstaged. The modified paths are `automation/msm_runner.sh` and this report; the pre-existing protected Pine modification remains preserved and unrelated.
