# AUTOMATION-004 Result

- task_id: `AUTOMATION-004-LOCAL-ORCHESTRATOR-V1`
- status: `IMPLEMENTED_AWAITING_BOOTSTRAP_COMMIT`

## Architecture

`msm_orchestrator.py` owns a single-lock, atomic-file state machine rooted at `/home/nnv/.local/state/msm-orchestrator/`. It accepts only validated JSON envelopes, moves them atomically between queue, running, terminal, log, and lock directories, and permits one transition per poll. The deterministic transition table owns all state changes; role outputs are limited to a strict JSON decision schema.

The worker uses a separate, role-specific prompt and an isolated Codex invocation with a read-only `.git` mount. It writes a final result and JSONL stream. The orchestrator records structured per-role logs, handles malformed output as technical failure, applies stop gates, supports SIGTERM, a kill switch, bounded correction count, restart persistence, and duplicate ID/hash handling. Real work uses deterministic Git preflight/fast-forward and explicit allowlist staging; model processes do not receive Git mutation authority.

The installer copies the service implementation into `/usr/local/lib/msm-orchestrator/`, prepares 0700 runtime directories, and leaves the legacy runner untouched. The unit runs as `nnv` with a restrictive umask and failure restart delay.

## State transitions and safety gates

- `READY → PLANNING → IMPLEMENTING → AUDITING → COMPLETED` on role `PASS` verdicts.
- Audit correction requests become `CORRECTING_R1`, then `CORRECTING_R2`; a third becomes `BLOCKED_USER_DECISION`.
- Malformed output, invalid envelopes/transitions, worker errors, and kill-switch stops become `FAILED_TECHNICAL`.
- Definition/hypothesis/holdout/visual-judgment/ambiguity/conflict findings stop for user decision.
- Protected Pine hashing/staging checks, branch/main synchronization, explicit allowlist checks, and unstaged-model checks guard real Git ownership.

## Mock scenarios

The deterministic mock verifier passed READY through completion; two correction cycles and a third-request block; malformed JSON failure; restart recovery; identical and conflicting duplicates; kill switch; and protected-Pine hash preservation. It does not invoke Codex or modify repository research files or Git history.

## Validation

Passed:

- `python3 -m py_compile automation/msm_orchestrator.py`
- `bash -n automation/msm_worker.sh`
- `bash -n automation/install_orchestrator.sh`
- `bash -n automation/verify_orchestrator.sh`
- `bash automation/verify_orchestrator.sh --offline` (`OFFLINE_OK`)
- `bash automation/verify_orchestrator.sh --mock-cycle --wait 180` (`MOCK_CYCLE_OK`)
- `git diff --check`
- Allowed-change review: only the six task implementation files plus this report are new/modified; the protected Pine is the sole pre-existing unrelated modification.
- Protected Pine SHA-256 remains `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f` and it is unstaged.

Deferred by explicit execution constraint:

- Installer idempotency fixture was not run because the user prohibited installation commands. The installer was syntax-checked.
- `systemd-analyze verify automation/msm-orchestrator.service` was attempted; sandbox permissions prevented systemd access (`connect() failed: Operation not permitted`). The unit was not installed or activated.

## Known limitations

The outer bootstrap must run the installer fixture, installed-service checks, production activation, and final Git commit/push. No systemd service or legacy runner state was changed here.
