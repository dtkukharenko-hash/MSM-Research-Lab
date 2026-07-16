# AUTOMATION-004-R2 Writable Codex Runtime

- task_id: `AUTOMATION-004-R2-WRITABLE-CODEX-RUNTIME`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`

## Summary

`msm_worker.sh` now creates a private, task-keyed Codex runtime under the MSM
orchestrator state tree. Bubblewrap binds only the private runtime directories
writable and supplies them as `HOME`, all required XDG homes, and `TMPDIR`.
Codex writes its response inside that runtime, after which the worker preserves
the existing requested output path by moving the completed response there.
The repository remains writable only as before and its `.git` directory is
explicitly remounted read-only.

`verify_orchestrator.sh --worker-fixture` provides an isolated Bubblewrap
fixture with a deterministic fake Codex executable. It verifies writes to all
six runtime paths, attempts and rejects a `.git` write, checks the preserved
result path, and confirms that the prior in-process app-server read-only
initialization failure is absent.

## Validation

1. `bash -n automation/msm_worker.sh automation/verify_orchestrator.sh` — PASS.
2. `bash automation/verify_orchestrator.sh --offline` — PASS (`OFFLINE_OK`).
3. `bash automation/verify_orchestrator.sh --worker-fixture` — PASS
   (`WORKER_RUNTIME_FIXTURE_OK`). The fixture created writable files in each of
   `HOME`, `XDG_CACHE_HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`,
   `XDG_STATE_HOME`, and `TMPDIR`; its `.git` write failed with `Read-only file
   system`; and no `failed to initialize in-process app-server client:
   Read-only file system` text was produced.
4. `bash automation/verify_orchestrator.sh --mock-cycle --wait 180` — PASS
   (`MOCK_CYCLE_OK`).
5. `git diff --check` — PASS.
6. Allowed-path, unstaged, and protected-path checks before this report was
   written — PASS. Only `automation/msm_worker.sh` and
   `automation/verify_orchestrator.sh` were changed in addition to the known
   protected Pine modification; no files were staged. `docs/DEFINITIONS.md`
   is unchanged, and the protected Pine is unstaged with SHA-256
   `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`.

## Warnings

The protected Pine file was already modified locally before this task. It was
not modified by this task, remains byte-identical to that pre-existing state,
and remains unstaged. No Git pull, add, commit, push, or mutation of `.git`;
no sudo, systemctl, or installation command was run.
