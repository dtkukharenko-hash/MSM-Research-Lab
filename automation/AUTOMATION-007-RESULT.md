# AUTOMATION-007 result

- task_id: `AUTOMATION-007-OUTER-SANDBOX-ONLY`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`
- completed_at: `2026-07-16`

## Summary

Codex now runs without its internal sandbox inside the existing outer `bwrap`
boundary. The repository bind and explicit read-only `$REPO/.git` bind are
unchanged. Private runtime paths and credential-copy handling are unchanged.

## Changed files

- `automation/msm_worker.sh`
- `automation/verify_orchestrator.sh`
- `automation/AUTOMATION-007-RESULT.md`

## Validation

- `bash -n automation/msm_worker.sh automation/verify_orchestrator.sh` — PASS
- `bash automation/verify_orchestrator.sh --offline` — PASS
- `bash automation/verify_orchestrator.sh --worker-fixture` — PASS
  - task and allowlist were readable by the fixture Codex invocation;
  - Codex was invoked with its internal sandbox bypassed;
  - `.git` remained unwritable in the outer sandbox;
  - the historical `Can't mkdir /tmp/.git: Read-only file system` error was absent;
  - credentials were absent from worker output, JSONL, stderr, stdout, and repository files;
  - the orchestrator rejected an out-of-allowlist change before Git mutation.
- `bash automation/verify_orchestrator.sh --mock-cycle --wait 0` — PASS
- `git diff --check` — PASS

## Protections and warnings

- No Git mutation, staging, commit, pull, or push was performed.
- The protected Pine file remains modified from before this task and was not edited:
  `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`.
- All task-created/modified paths are within the task allowlist. The Pine is the
  sole pre-existing unrelated worktree modification and remains unstaged.
