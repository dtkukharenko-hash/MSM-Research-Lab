# AUTOMATION-004-R1 Installer Ownership and Mode Guard

- task_id: `AUTOMATION-004-R1-INSTALLER-OWNERSHIP-AND-MODE-GUARD`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`

## Summary

`automation/install_orchestrator.sh` now accepts only `--install --test-mode` or
`--activate-production`. It repairs every runtime state directory to the selected
run user/group and mode `0700` without deleting state contents. The installer also
contains an opt-in temporary-root fixture (`MSM_ORCH_INSTALLER_FIXTURE=1`) that
checks both valid modes, invalid-mode rejection, ownership/modes, and sentinel
preservation across a repeated run.

## Validation commands and outcomes

1. `bash -n automation/install_orchestrator.sh` — PASS.
2. `MSM_ORCH_INSTALLER_FIXTURE=1 bash automation/install_orchestrator.sh --install --test-mode` — PASS; output ended with `INSTALLER_FIXTURE_OK`. The fixture used temporary install and state roots, ran both supported invocation forms, rejected unsupported combinations, verified `0700` and the selected user/group on `state`, `queue`, `running`, `completed`, `blocked`, `failed`, `logs`, and `locks`, then confirmed that `queue/sentinel` survived a repeated installation.
3. `git diff --check` — PASS.
4. Changed-path check (`git diff --name-only`, `git diff --cached --name-only`, and `git ls-files --others --exclude-standard`) — PASS before this report was written: only `automation/install_orchestrator.sh` was modified, nothing was staged, and no untracked files remained.
5. Protected-path checks (`git diff --quiet -- docs/DEFINITIONS.md`, staged checks for `docs/DEFINITIONS.md` and the protected Pine) — PASS. `docs/DEFINITIONS.md` is unchanged; the protected Pine remains unstaged and was not modified by this task.

## Warnings

The protected Pine was already modified in the worktree before this task. It was preserved byte-for-byte and remains unstaged. No Git staging, commit, push, pull, installation, sudo, or systemctl command was run.
