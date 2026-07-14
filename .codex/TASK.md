# Current Codex Task

- task_id: `AUTOMATION-001-MSM-CODEX-RUNNER`
- status: `READY`
- published_at: `2026-07-14`
- target_branch: `main`
- commit_message: `automation: add MSM Codex runner and auditor`

## Instruction precedence

This file is the only active task specification.

Read and obey `AGENTS.md` and `PROJECT_INSTRUCTIONS.md` before implementation.

`.codex/TASK_ADDENDUM.md` is historical EXP-012 R2 documentation only and is not part of this task.

## Objective

Create a safe Ubuntu/systemd automation layer for `/home/nnv/MSM-Research-Lab` that executes a newly published `.codex/TASK.md`, records state and logs, and then performs an independent read-only audit.

This is infrastructure work only. Do not change experiment logic or research artifacts.

## Mandatory protections

Never modify, stage, or commit:

- `docs/DEFINITIONS.md`
- any existing file under `experiments/**`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

The existing unstaged EXP009A Pine file must remain untouched and unstaged.

Do not use `git add .`, force push, destructive reset, or root execution of Codex.

Do not store ChatGPT, Codex, GitHub, SSH, or API credentials in the repository.

## Create

- `automation/README.md`
- `automation/install.sh`
- `automation/msm_runner.sh`
- `automation/msm_audit.sh`
- `automation/runner.service`
- `automation/runner.timer`
- `automation/state.example.json`
- `.codex/AUTOPILOT_POLICY.md`

Runtime state must live outside Git in:

- `/home/nnv/.local/state/msm-runner/state.json`
- `/home/nnv/.local/state/msm-runner/logs/`
- `/home/nnv/.local/state/msm-runner/locks/`

Do not create a tracked mutable `automation/state.json` that will dirty the worktree every run. Use `state.example.json` as the documented schema.

## Runner model and execution

Use the exact Codex executable:

`/home/nnv/.local/bin/codex`

Runner implementation model:

- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- sandbox: `workspace-write`
- approval: `never`
- timeout: 4 hours

Auditor model:

- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- sandbox: `read-only`
- approval: `never`
- timeout: 2 hours

Use `codex exec --json` and save the final message separately with `-o` when supported by the installed CLI. Validate command flags against `codex exec --help`; do not invent unsupported flags.

## `msm_runner.sh`

Implement a deterministic non-interactive runner with `set -Eeuo pipefail`.

Required flow:

1. Run as user `nnv`, never root.
2. Obtain a non-blocking `flock` lock. If another run is active, exit successfully without launching another Codex process.
3. Use repository `/home/nnv/MSM-Research-Lab`.
4. Validate the current worktree before pull. The only permitted pre-existing dirty path is exactly:
   `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
5. Any other modified, staged, deleted, renamed, or untracked path must set state `BLOCKED_DIRTY_WORKTREE` and stop.
6. Run `git pull --ff-only origin main`.
7. Re-check the dirty-worktree allowlist after pull.
8. Parse `.codex/TASK.md` safely and require exact `status: READY` plus a non-empty `task_id`.
9. Compute and store the SHA-256 hash of `.codex/TASK.md`.
10. Do not rerun when the same `task_id` and task hash were already completed successfully.
11. Also skip when `.codex/RESULT.md` already names the same task ID and reports the implementation/result pushed, unless an explicit retry marker exists in runtime state.
12. Before execution write state `RUNNING` with task ID, task hash, start time, starting Git SHA and PID.
13. Launch Codex with a prompt that requires reading `.codex/TASK.md`, `AGENTS.md`, and `PROJECT_INSTRUCTIONS.md`; preserving the EXP009A Pine; committing and pushing implementation; and updating `.codex/RESULT.md` according to project workflow.
14. Capture JSONL log, final response, stderr, exit code, duration and ending Git SHA.
15. After Codex exits, validate that the forbidden EXP009A Pine path is neither staged nor changed relative to the pre-run snapshot.
16. Require `.codex/RESULT.md` to exist and refer to the current task ID.
17. On runner failure write `FAILED` with a clear reason and do not launch the auditor.
18. On successful implementation write `WAITING_AUDIT`, then invoke `automation/msm_audit.sh`.

Use explicit path-based staging checks. Never clean or reset the user's worktree automatically.

## `msm_audit.sh`

Run a separate Codex process in read-only sandbox. It must not modify repository files, commit, or push.

Audit the current task and implementation using:

- `.codex/TASK.md`
- `.codex/RESULT.md`
- implementation commit and result commit
- Git diff and repository status
- generated tests and artifacts

Check at minimum:

- task compliance
- forbidden-path changes
- lookahead and future leakage where applicable
- causal timestamp discipline where applicable
- acceptance tests are substantive rather than unconditional booleans
- CSV consistency
- Pine restrictions and compile-oriented source checks where applicable
- REPORT and RESULT consistency with generated artifacts
- deterministic/reproducible claims
- cutoff compliance
- no credentials committed

The auditor must write its machine-readable result only outside Git:

`/home/nnv/.local/state/msm-runner/audit.json`

Required JSON schema:

```json
{
  "task_id": "",
  "task_hash": "",
  "audited_commit": "",
  "audit_status": "PASS|TECHNICAL_CORRECTION_REQUIRED|USER_DECISION_REQUIRED|AUDIT_FAILED",
  "technical_pass": false,
  "research_decision_required": false,
  "blocking_findings": [],
  "warnings": [],
  "recommended_action": "",
  "finished_at": ""
}
```

Because Codex runs read-only, capture its final structured JSON outside the repository and validate it with Python's standard `json` module or `jq` if already installed. Do not add a new dependency only for JSON validation.

Update runtime `state.json` from the audit result:

- `WAITING_USER_REVIEW` for technical PASS where manual review is still required
- `WAITING_USER_DECISION` for ontology/research/holdout/model-choice questions
- `TECHNICAL_CORRECTION_REQUIRED` for a concrete technical defect
- `AUDIT_FAILED` when the auditor itself fails

AUTOMATION-001 must not yet implement automatic correction loops. Document them as a later phase. The first release executes one task and one independent audit, then stops.

## Runtime state schema

Create `automation/state.example.json` with at least:

```json
{
  "runner_state": "IDLE",
  "task_id": "",
  "task_hash": "",
  "started_at": "",
  "finished_at": "",
  "starting_commit": "",
  "last_commit": "",
  "audit_status": "",
  "exit_code": 0,
  "failure_reason": "",
  "runner_pid": 0
}
```

State writes must be atomic: write a temporary file in the same directory and rename it.

## systemd units

`automation/runner.service`:

- `Type=oneshot`
- `User=nnv`
- `Group=nnv`
- working directory `/home/nnv/MSM-Research-Lab`
- execute `/home/nnv/MSM-Research-Lab/automation/msm_runner.sh`
- include a suitable PATH containing `/home/nnv/.local/bin`, `/usr/local/bin`, `/usr/bin`, and `/bin`
- no root Codex execution
- reasonable hardening that does not prevent Git SSH access, Codex authentication, repository writes, or runtime-state writes

`automation/runner.timer`:

- run every 5 minutes
- use `OnBootSec` and `OnUnitActiveSec=5min`
- `Persistent=true`
- target `timers.target`

Use stable installed unit names:

- `msm-codex-runner.service`
- `msm-codex-runner.timer`

The repository filenames may remain `runner.service` and `runner.timer`; `install.sh` must install them under the stable names above.

## `install.sh`

Implement `set -Eeuo pipefail` and require execution with sudo/root only for installation steps.

It must:

1. Verify user `nnv`, repository path, Codex executable, Git, `flock`, `timeout`, `sha256sum`, Python 3 and `bubblewrap`.
2. Create runtime directories owned by `nnv:nnv` with restrictive permissions.
3. Install scripts as executable without changing ownership of the Git working tree.
4. Copy units to `/etc/systemd/system/msm-codex-runner.service` and `/etc/systemd/system/msm-codex-runner.timer`.
5. Run `systemctl daemon-reload`.
6. Enable the timer.
7. Do not start the timer automatically unless `--enable-now` is supplied.
8. Support `--dry-run` that performs validation and prints intended actions without modifying `/etc/systemd`.
9. Print exact verification and rollback commands.

Do not run Codex from `install.sh`.

## `.codex/AUTOPILOT_POLICY.md`

Document that automation may perform only the active READY task and ordinary implementation steps explicitly authorized by that task.

Automatic technical work may include:

- code and script corrections
- test corrections without weakening criteria
- CSV/Pine/report/result generation required by the task
- causal timestamp corrections
- reproducibility fixes

Automation must stop for user decision before:

- changing market definitions or ontology
- changing research criteria
- weakening acceptance criteria
- using a new holdout or previously unseen period
- changing symbol/timeframe/development period
- choosing between competing research models
- accepting or rejecting a hypothesis
- interpreting TradingView manual review
- modifying `docs/DEFINITIONS.md`

The policy must state that the runner does not broaden authority beyond `.codex/TASK.md`.

## `automation/README.md`

Document:

- architecture and safety model
- prerequisites
- dry-run installation
- installation and enablement
- manual one-shot execution
- starting/stopping/disabling timer
- status and logs
- runtime state and audit locations
- lock behavior
- dirty-worktree allowlist
- how to retry a failed task safely
- uninstall/rollback
- known limitation: first release does not generate new tasks or autonomously make research decisions

Required example commands:

```bash
sudo ./automation/install.sh --dry-run
sudo ./automation/install.sh --enable-now
sudo systemctl start msm-codex-runner.service
systemctl status msm-codex-runner.timer
journalctl -u msm-codex-runner.service -f
cat /home/nnv/.local/state/msm-runner/state.json
cat /home/nnv/.local/state/msm-runner/audit.json
sudo systemctl disable --now msm-codex-runner.timer
```

## Validation

Before committing:

- `bash -n automation/install.sh`
- `bash -n automation/msm_runner.sh`
- `bash -n automation/msm_audit.sh`
- validate unit syntax with `systemd-analyze verify` when available; report honestly if environment prevents it
- validate JSON example with Python
- run `automation/install.sh --dry-run`
- perform a safe runner dry-run mode that does not invoke Codex, commit, push, or alter task/result files
- verify exact 5-minute timer interval
- verify service user is `nnv`
- verify runner uses `gpt-5.6-terra`, medium, workspace-write
- verify auditor uses `gpt-5.6-terra`, medium, read-only
- verify no existing `experiments/**`, `docs/**`, `PROJECT_QUEUE.md`, or `MEMORY.md` file changed
- verify EXP009A Pine remains unstaged and unchanged
- verify no credential-like content was added

## Deliverable and result

Commit and push the implementation to `main` with message:

`automation: add MSM Codex runner and auditor`

Then update and push `.codex/RESULT.md` according to `AGENTS.md`.

The result must include:

- implementation commit SHA
- result commit status
- files created
- validation commands and outcomes
- whether systemd installation was performed (expected: not performed by Codex; user performs it after review)
- exact installation path and management commands
- confirmation that no existing research file was modified
- confirmation that the EXP009A Pine remained untouched and unstaged

Final task status:

`AWAITING_AUTOMATION_INSTALL_REVIEW`
