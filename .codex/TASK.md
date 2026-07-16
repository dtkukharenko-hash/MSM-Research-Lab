# Current Codex Task

- task_id: `AUTOMATION-005-FEEDER-V1`
- status: `COMPLETED`
- completed_at: `2026-07-16`
- published_at: `2026-07-16`
- completion_commit: `948fe44b7b62ce8bc858bf843a4707811daf6318`
- target_branch: `main`
- commit_message: `AUTOMATION-005 feeder v1`
- infrastructure_maintenance: `true`

## Objective

Add a deterministic feeder and enqueue CLI connecting GitHub `.codex/TASK.md` to the installed local orchestrator queue. The feeder must never make research judgments and must fail closed.

## Architecture

```text
GitHub .codex/TASK.md + .codex/ALLOWLIST.txt
  -> msm_task_feeder.py
  -> atomic envelope in /home/nnv/.local/state/msm-orchestrator/queue
  -> existing msm-orchestrator.service
```

Keep the orchestrator state machine authoritative. The feeder only validates and enqueues.

## Required files

Create:

- `automation/msm_task_feeder.py`
- `automation/enqueue_task.py`
- `automation/install_feeder.sh`
- `automation/verify_feeder.sh`
- `automation/msm-task-feeder.service`
- `automation/AUTOMATION-005-RESULT.md`

Modify only when required for immutable-copy installation compatibility:

- `automation/install_orchestrator.sh`
- `automation/msm-orchestrator.service`

Do not modify orchestrator transitions or worker role semantics.

## Feeder contract

1. Read only repository-local `.codex/TASK.md` and `.codex/ALLOWLIST.txt`.
2. Accept only `status: READY`.
3. Reject infrastructure tasks and tasks with `infrastructure_maintenance: true` from automatic production ingestion.
4. Reject or place into `blocked/` without invoking Codex when task text or metadata requires any of:
   - definition change;
   - hypothesis change;
   - holdout access or extension;
   - TradingView or visual review;
   - ambiguous research judgment;
   - user decision.
5. Validate task ID format, branch `main`, nonempty allowlist, repository-relative normalized paths, no duplicates, no directory traversal, and no protected paths.
6. Always forbid:
   - `docs/DEFINITIONS.md`;
   - `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`;
   - `.git` internals;
   - secrets and installed system paths.
7. Compute task SHA-256 from exact task bytes.
8. Create the queue envelope atomically with schema fields expected by `msm_orchestrator.py`.
9. Preserve idempotency across restarts: same task ID/hash is a no-op wherever it already exists in queue/running/completed/blocked/failed; same ID with a different hash becomes blocked and never runs.
10. Feeder must not run git mutation commands, commit, push, stage, reset, clean, checkout, or merge.
11. Production feeder may perform read-only detection against the already synchronized local repository. It must not fetch while a task is running. Git synchronization remains owned by the orchestrator preflight.
12. Poll interval: 10 seconds. One feeder instance only, protected by a lock.
13. `enqueue_task.py` must support an explicit manual dry-run and explicit enqueue mode using the same validation code.
14. All writes under the runtime state tree must be atomic, mode 0600 for files, 0700 for directories, owner/group `nnv`.
15. Never overwrite queue or state files silently.

## Service and installation

- Install immutable copies under `/usr/local/lib/msm-orchestrator/`.
- Install `msm-task-feeder.service` under `/etc/systemd/system/`.
- Run as user/group `nnv`.
- Set `PYTHONDONTWRITEBYTECODE=1`.
- Use restart-on-failure with bounded delay.
- Do not enable the service inside `install_feeder.sh --install --test-mode`.
- Support exactly:
  - `--install --test-mode`
  - `--activate-production`
- Repeated installation must be safe and preserve all runtime queues/logs.

## Validation fixtures

`verify_feeder.sh` must test in isolated temporary roots:

1. valid READY task creates exactly one valid envelope;
2. repeated identical task is a no-op;
3. same ID with changed hash blocks;
4. COMPLETED/non-READY task is ignored;
5. infrastructure task is rejected;
6. empty, absolute, traversing, duplicate and protected allowlist entries fail;
7. visual/TradingView, definition, hypothesis, holdout, ambiguous and user-decision tasks block before any worker call;
8. malformed Markdown metadata fails closed;
9. concurrent feeder processes create at most one envelope;
10. restart preserves dedupe state;
11. kill switch prevents ingestion;
12. no `.pyc` or `__pycache__` is created in the repository;
13. protected Pine remains byte-identical and unstaged;
14. feeder executes no git mutation command;
15. production service and orchestrator service can run together while old timer remains disabled.

## Real smoke-test preparation

Do not automatically run a research task during installation. Provide a documented command in `AUTOMATION-005-RESULT.md` for a later harmless real Codex smoke task. Installation verification itself must use deterministic fixtures without model calls.

## Hard protections

Never modify, stage, commit, delete, rename, chmod, rewrite, or include in any allowlist:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `.codex/RESULT.md`
- `.git` internals
- research documents or artifacts

The protected Pine may already be modified locally. It must remain byte-identical, unstaged, and uncommitted.

## Allowed changes

Only:

- `automation/msm_task_feeder.py`
- `automation/enqueue_task.py`
- `automation/install_feeder.sh`
- `automation/verify_feeder.sh`
- `automation/msm-task-feeder.service`
- `automation/AUTOMATION-005-RESULT.md`
- `automation/install_orchestrator.sh` only if immutable-copy integration requires it
- `automation/msm-orchestrator.service` only if service integration requires it

## Result contract

Write `automation/AUTOMATION-005-RESULT.md` only after all validations pass. Set status `IMPLEMENTED_AWAITING_MANUAL_COMMIT`, include exact test commands/results, installed paths, service names, rollback instructions, queue schema, manual enqueue usage, and the harmless real smoke-test command. Leave changes unstaged and uncommitted for deterministic bootstrap handling.
