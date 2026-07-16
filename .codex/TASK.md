# Current Codex Task

- task_id: `AUTOMATION-004-LOCAL-ORCHESTRATOR-V1`
- status: `COMPLETED`
- completed_at: `2026-07-16`
- published_at: `2026-07-16`
- completion_commit: `bf77f32fcafec69c6c36ea6073afed559ba36072`
- target_branch: `main`
- commit_message: `AUTOMATION-004 implement local orchestrator v1`
- infrastructure_maintenance: `true`

## Objective

Build the first production-safe local MSM orchestrator. It must run entirely on the Ubuntu server through the existing Codex CLI, react within seconds, execute one task at a time, and move work through four restricted roles: planner, implementer, auditor, and corrector.

The state machine, safety gates, retries, limits, Git ownership, and service lifecycle must be deterministic code. Codex roles may produce structured decisions but must not control process transitions directly.

## Required files

Create:

- `automation/msm_orchestrator.py`
- `automation/msm_worker.sh`
- `automation/install_orchestrator.sh`
- `automation/verify_orchestrator.sh`
- `automation/msm-orchestrator.service`
- `automation/AUTOMATION-004-RESULT.md`

Do not create additional production files unless strictly needed for tests; test fixtures must be temporary and removed before completion.

## Allowed changes

- `automation/msm_orchestrator.py`
- `automation/msm_worker.sh`
- `automation/install_orchestrator.sh`
- `automation/verify_orchestrator.sh`
- `automation/msm-orchestrator.service`
- `automation/AUTOMATION-004-RESULT.md`

## Hard protections

Never modify, stage, commit, delete, rename, chmod, or rewrite:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `automation/build_orchestrator_v1.sh`
- `.git` internals
- secrets, credentials, SSH configuration, Codex authentication, Telegram secrets, or files outside the repository

The protected Pine may already be modified locally. It must remain byte-identical, unstaged, and uncommitted.

## Architecture

Use one systemd service and one Python state machine. Version 1 is sequential: no parallel writers and no git worktrees.

Runtime directories must live outside the repository under:

`/home/nnv/.local/state/msm-orchestrator/`

Required runtime subdirectories:

- `queue/`
- `running/`
- `completed/`
- `blocked/`
- `failed/`
- `logs/`
- `locks/`

All runtime state belongs to user `nnv`, mode 0700 for directories and 0600 for state files where practical.

The repository remains the source of task definitions and research artifacts. Runtime queue/status files must not dirty the repository.

## State machine

Allowed task states:

- `READY`
- `PLANNING`
- `IMPLEMENTING`
- `AUDITING`
- `CORRECTING_R1`
- `CORRECTING_R2`
- `COMPLETED`
- `BLOCKED_USER_DECISION`
- `FAILED_TECHNICAL`

Allowed role verdicts:

- `PASS`
- `TECHNICAL_CORRECTION_REQUIRED`
- `USER_DECISION_REQUIRED`
- `FAILED`

Transitions must be explicit and validated. Invalid or missing transitions must stop the task as `FAILED_TECHNICAL`; never guess a next state.

Maximum corrections: exactly two. A further correction request becomes `BLOCKED_USER_DECISION`.

No role may publish an unbounded next research hypothesis. Planner may only expand steps already present in the queued task package.

## Queue contract

Use JSON task envelopes in the runtime `queue/` directory. Each envelope must include at least:

- `schema_version`
- `task_id`
- `task_hash`
- `status`
- `task_path`
- `allowlist_path`
- `created_at`
- `attempt`
- `max_corrections`

Validate required fields, types, unique task ID/hash, referenced files, and status before execution.

Move envelopes atomically between runtime directories using write-to-temp plus `os.replace`. Never process a partially written file.

Duplicate task ID plus identical hash must be skipped idempotently. Duplicate task ID with a different hash must be blocked as a conflict.

## Worker roles

`msm_worker.sh` must invoke the installed Codex CLI as user `nnv`, with a timeout, isolated prompt per role, JSONL log, final text output, and no Git mutation permission for model processes.

Roles:

1. Planner reads the queued task package and returns a structured execution plan limited to the existing objective and allowlist.
2. Implementer edits only explicitly allowed files and leaves changes unstaged.
3. Auditor independently checks task compliance, diff, tests, causal restrictions, look-ahead risk, protected paths, and required artifacts. It returns strict structured JSON.
4. Corrector receives only the exact blocking findings from the preceding audit and may modify only the original allowlist.

Every role output must be validated against a JSON schema implemented in deterministic Python. Malformed output is a technical failure, not a research verdict.

## Git ownership

Only deterministic orchestrator code may run Git mutation commands. Model processes must not run pull, fetch, add, commit, push, reset, checkout, clean, rebase, merge, or modify `.git`.

Before a task:

- acquire one global nonblocking lock;
- require branch `main`;
- allow only the known protected Pine as pre-existing dirt;
- record protected Pine SHA-256;
- synchronize with `origin/main` using `git fetch origin main` and a checked `merge --ff-only origin/main`; do not use ambiguous `git pull`;
- re-check the worktree after synchronization.

Before commit:

- verify protected Pine SHA-256 and staging state;
- verify every changed path against the task allowlist;
- reject changes to definitions, protected Pine, infrastructure during normal research tasks, secrets, or files outside the repository;
- require no model-staged files;
- run `git diff --check` and required task tests;
- stage exact verified paths only;
- commit and push once.

A failed push must preserve recoverable state and must not rerun the model blindly.

## Research stop gates

The orchestrator must stop with `BLOCKED_USER_DECISION` when any role identifies:

- definition change;
- hypothesis change not pre-authorized by the task;
- new holdout access;
- visual TradingView judgment;
- ambiguous research interpretation;
- request to exceed two corrections;
- conflict between task instructions and project protections.

These are not technical failures and must not trigger automatic correction.

## Reliability requirements

Implement:

- one global lock preventing concurrent orchestrators;
- process timeout per Codex role;
- atomic state writes;
- crash recovery from a valid last state;
- no duplicate model invocation after restart when a completed role result already exists;
- bounded exponential backoff only for transient process/network failures;
- maximum role calls per task;
- kill switch file under runtime state;
- structured logs with task ID, role, attempt, timestamps, exit code, and output paths;
- safe handling of SIGTERM from systemd;
- no busy loop; polling interval around 10 seconds is acceptable;
- no external API usage.

## Installer

`install_orchestrator.sh` must be idempotent and support exactly these modes used by the outer bootstrap:

- `--install --test-mode`
- `--activate-production`

It must:

- validate dependencies and syntax before changing services;
- install immutable copies under `/usr/local/lib/msm-orchestrator/`;
- install `msm-orchestrator.service` under `/etc/systemd/system/`;
- create runtime directories with correct owner/mode;
- support test mode without consuming real research tasks;
- preserve the existing old runner until production activation succeeds;
- never expose or require an API key;
- be safe to run repeatedly.

Production activation must not itself disable the old runner timer; the outer bootstrap performs the final atomic switch only after verification.

## Verifier

`verify_orchestrator.sh` must be idempotent and support:

- `--offline`
- `--service --test-mode --wait SECONDS`
- `--mock-cycle --wait SECONDS`
- `--service --production --wait SECONDS`
- `--health`

The mock cycle must exercise, without modifying research files or Git history:

1. READY to PLANNING;
2. PLANNING to IMPLEMENTING;
3. IMPLEMENTING to AUDITING;
4. PASS to COMPLETED;
5. technical failure to CORRECTING_R1;
6. second failure to CORRECTING_R2;
7. third correction request to BLOCKED_USER_DECISION;
8. malformed role JSON to FAILED_TECHNICAL;
9. duplicate identical task skip;
10. duplicate conflicting task block;
11. restart recovery without duplicate invocation;
12. kill switch behavior;
13. protected Pine unchanged and unstaged.

Mock mode may use deterministic fake worker responses. It must not spend Codex tokens.

## Service

The systemd unit must:

- run as `nnv`;
- use the installed immutable copy;
- restart on genuine process failure with bounded delay;
- use a restrictive umask;
- set a clear working directory;
- stop cleanly on SIGTERM;
- avoid access to secrets not required by this service.

## Validation

Run and record:

- `python3 -m py_compile automation/msm_orchestrator.py`
- `bash -n automation/msm_worker.sh`
- `bash -n automation/install_orchestrator.sh`
- `bash -n automation/verify_orchestrator.sh`
- offline verifier;
- full deterministic mock-cycle verifier;
- installer idempotency fixture;
- service unit static validation where available;
- `git diff --check`;
- confirmation that only Allowed changes were modified;
- confirmation that protected Pine is byte-identical and unstaged.

## Result report

Write `automation/AUTOMATION-004-RESULT.md` only after every required validation passes. Include architecture summary, state transitions, safety gates, mock scenarios, exact test commands and outcomes, known limitations, and status `IMPLEMENTED_AWAITING_BOOTSTRAP_COMMIT`.

Leave all changes unstaged and uncommitted. The outer deterministic bootstrap owns commit, installation, service switching, and push.
