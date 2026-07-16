# AUTOMATION-005 Feeder V1 Result

- task_id: `AUTOMATION-005-FEEDER-V1`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`

## Summary

Implemented a deterministic, fail-closed feeder from repository-local `.codex/TASK.md` and `.codex/ALLOWLIST.txt` into the existing local orchestrator queue. The feeder validates and atomically creates envelopes only; it does not make research decisions, invoke Codex, alter orchestrator transitions, or run Git commands.

## Installed paths and services

The installer copies immutable sources to:

- `/usr/local/lib/msm-orchestrator/msm_task_feeder.py`
- `/usr/local/lib/msm-orchestrator/enqueue_task.py`
- `/etc/systemd/system/msm-task-feeder.service`

The runtime state root is `/home/nnv/.local/state/msm-orchestrator/`. The feeder service is `msm-task-feeder.service`; it can run alongside `msm-orchestrator.service`. The legacy `msm-codex-runner.timer` must remain disabled during production activation.

## Queue schema

Each envelope has the schema consumed by `msm_orchestrator.py`:

```json
{
  "schema_version": "1",
  "task_id": "SAFE-001",
  "task_hash": "<sha256 of exact TASK.md bytes>",
  "status": "READY",
  "task_path": ".codex/TASK.md",
  "allowlist_path": ".codex/ALLOWLIST.txt",
  "created_at": "<UTC RFC3339>",
  "attempt": 0,
  "max_corrections": 2
}
```

Blocked envelopes use `BLOCKED_USER_DECISION` and include a `failure_reason`. Files are exclusive-created at mode `0600`; runtime directories are mode `0700` and owned by `nnv:nnv` in production.

## Manual enqueue usage

Validate a synchronized local task without writing an envelope:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B automation/enqueue_task.py --dry-run
```

Explicitly enqueue only after that validation succeeds:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B automation/enqueue_task.py --enqueue
```

The daemon polls every 10 seconds and has a state-tree lock. Identical ID/hash inputs are no-ops across all queue and terminal directories; a reused ID with different task bytes is moved to `blocked/`. A `KILL` file in the state root prevents ingestion.

## Validation commands and results

Passed:

- `PYTHONDONTWRITEBYTECODE=1 bash automation/verify_feeder.sh --fixtures` — `OFFLINE_OK`, `FIXTURES_OK`.
- `PYTHONDONTWRITEBYTECODE=1 bash automation/verify_feeder.sh --service --test-mode --wait 1` — `OFFLINE_OK`, `SERVICE_STATIC_OK`.
- `PYTHONDONTWRITEBYTECODE=1 bash automation/verify_feeder.sh --service --production --wait 1` — `OFFLINE_OK`, `SERVICE_STATIC_OK`.
- `PYTHONDONTWRITEBYTECODE=1 bash automation/verify_orchestrator.sh --offline` — `OFFLINE_OK`.
- `for f in automation/*.sh; do bash -n "$f"; done` — passed.
- Python source compilation of both feeder files with `python3 -B` — `PYTHON_STATIC_OK`.
- `git diff --check` — passed.
- Repository scan for `.pyc` and `__pycache__` — passed.
- Cached-diff checks, including the protected Pine and `docs/DEFINITIONS.md` — passed.

The isolated fixture suite covers valid envelope creation, identical deduplication, changed-hash blocking, non-READY ignore, infrastructure rejection, invalid allowlists, all specified research/user-decision stop gates, malformed metadata, concurrent ingestion, restart deduplication, kill switch behavior, bytecode absence, protected-Pine integrity and unstaged state, absence of Git mutation calls, and static feeder/orchestrator coexistence with no legacy-timer conflict.

## Harmless real smoke task

After a human prepares and synchronizes a harmless non-infrastructure `READY` task whose allowlist contains only a disposable automation code file, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B automation/enqueue_task.py --dry-run && PYTHONDONTWRITEBYTECODE=1 python3 -B automation/enqueue_task.py --enqueue
```

Do not use the active infrastructure task for this smoke test; automatic ingestion correctly blocks it.

## Rollback

Stop and disable only the feeder service, remove its installed immutable copies and unit, then reload systemd. Preserve `/home/nnv/.local/state/msm-orchestrator/` unless an operator has independently archived the queues and logs. Do not re-enable the legacy timer until the orchestrator/feeder deployment is intentionally retired.

## Warnings

Per execution constraints, no installation command, service activation, `systemctl`, Git mutation, or network synchronization command was run. The existing protected Pine modification was preserved byte-for-byte and remains unstaged.
