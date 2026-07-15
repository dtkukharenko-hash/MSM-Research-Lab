# Current Codex Task

- task_id: `AUTOMATION-002-R2-ISOLATION-STATE-AND-RETRY-FIX`
- status: `READY`
- published_at: `2026-07-15`
- target_branch: `main`
- commit_message: `AUTOMATION-002-R2 fix isolation state and retry semantics`
- infrastructure_maintenance: `true`

## Objective

Patch the existing uncommitted AUTOMATION-002-R1 implementation in place. Do not redesign the runner again. Fix only the concrete defects listed below, preserve working parts, validate honestly, and leave all changes uncommitted for manual review.

This is a manual bootstrap task. Never execute it through systemd.

## Mandatory protections

Never modify, stage, or commit:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- any research file
- secrets, credentials, SSH/Codex auth files, or files outside the repository

The existing Pine modification must remain byte-identical, unstaged, and uncommitted.

Do not run `git pull`, `git add`, `git commit`, `git push`, `sudo`, `systemctl`, or installation commands.

Do not write `.codex/RESULT.md` in this manual Codex session. Write the bootstrap report to `automation/AUTOMATION-002-R2-RESULT.md`.

## Defects to fix

### 1. Real Bubblewrap isolation for implementation and correction

The current `run_writer()` invokes Codex directly while claiming `.git` is read-only. Replace this with actual Bubblewrap isolation.

Implementation R0 and corrections R1/R2 must run with:

- repository worktree writable;
- repository `.git` explicitly read-only;
- runtime state/log directory writable;
- Codex `workspace-write`;
- approval `never`;
- no Git mutation/network synchronization commands in the prompt.

Use a working Bubblewrap command equivalent to the already verified environment. Do not merely document isolation; enforce it in the command line.

`msm_correct.sh` must use the same enforced `.git` read-only boundary and invoke exactly one Codex correction process per retry.

### 2. Read-only audit filesystem

Audit Codex must not rely only on `-s read-only`. Enforce a read-only repository through Bubblewrap, while allowing only runtime log/audit output outside the repository.

The auditor must not modify repository files or `.git`.

### 3. Restore one-shot retry semantics

The current draft removed the externally requested one-shot retry behavior.

Restore:

- `retry_requested=true` is accepted only when task ID and task hash match;
- it is atomically reset/consumed before rerun;
- it cannot remain permanently true;
- duplicate completed task ID+hash is skipped when no matching retry is requested.

Add a simulation or isolated state test proving consumption happens once.

### 4. Correct outcome routing and final state

Do not write final state `PASS` unconditionally.

Required routing:

- `PASS` + `technical_pass=true` -> commit allowed, final audit status `PASS`;
- `USER_DECISION_REQUIRED` + `technical_pass=true` -> commit allowed, but final state/audit must remain `USER_DECISION_REQUIRED`, not `PASS`;
- `USER_DECISION_REQUIRED` + `technical_pass=false` -> stop without commit;
- `TECHNICAL_CORRECTION_REQUIRED` at R0 -> exactly one R1 correction;
- `TECHNICAL_CORRECTION_REQUIRED` at R1 -> exactly one R2 correction;
- technical failure at R2 -> stop `USER_DECISION_REQUIRED` without commit;
- `AUDIT_FAILED` -> stop without commit.

Persist the actual final attempt number. Do not hardcode attempt `2` in successful state.

### 5. Preserve complete runtime history

Runtime state must retain at minimum:

- original task ID/hash;
- current attempt;
- attempt history for R0/R1/R2;
- implementation/correction start and end times;
- implementation/correction exit codes;
- each worktree diff hash;
- each audit JSON path/status;
- blocking findings and warnings;
- final stop reason;
- starting, implementation, and result commit SHAs when created.

Do not replace the entire state with a minimal object on each transition if that destroys history.

### 6. No-task behavior

After pull and task parsing:

- absent/non-READY task must exit successfully as `NO_ACTIVE_TASK`, not set runner failure;
- malformed READY task with missing task ID may fail explicitly;
- infrastructure task must return `MANUAL_BOOTSTRAP_REQUIRED` only after pull and parsing.

### 7. Self-protection for normal tasks

For normal tasks, reject any changed infrastructure path even if a broad allowlist pattern accidentally matches it:

- `automation/msm_runner.sh`
- `automation/msm_audit.sh`
- `automation/msm_correct.sh`
- `automation/install.sh`
- `automation/runner.service`
- `automation/runner.timer`

Infrastructure maintenance remains manual-only.

### 8. Accurate shell-generated result metadata

The shell-generated `.codex/RESULT.md` must record the real audit outcome and real attempt number. For technically valid `USER_DECISION_REQUIRED`, preserve that status.

Use the two-commit workflow:

1. implementation files plus RESULT with `PENDING_SHELL_COMMIT`;
2. RESULT metadata with actual implementation SHA and push status.

Do not stage the protected Pine.

### 9. Executable modes and installed-copy design

Ensure repository executable modes are correct for all shell scripts, or document that `install.sh` sets modes while validation invokes them through `bash`.

Service must execute the installed copy under `/usr/local/lib/msm-runner/`, not mutable repository source. Helpers must be installed beside it.

Preserve the committed one-minute timer.

## Validation

Run and report exact outcomes. A failed command must be reported as failed.

Required:

- `bash -n` for each `automation/*.sh`;
- `bash automation/install.sh --dry-run`;
- runner dry-run;
- no-active-task simulation;
- duplicate completed task skip simulation;
- matching one-shot retry consumption twice, proving first consumes and second does not;
- infrastructure task simulation -> `MANUAL_BOOTSTRAP_REQUIRED`;
- R0 technical failure -> exactly one R1 correction route;
- R1 technical failure -> exactly one R2 correction route;
- R2 technical failure -> `USER_DECISION_REQUIRED`;
- research-decision case -> zero corrections;
- technically valid `USER_DECISION_REQUIRED` remains that status while commit gate is allowed;
- scans showing actual Bubblewrap `.git` read-only enforcement for implementation and correction;
- scans showing audit repository read-only enforcement;
- scans showing no `git add .` or `git add -A`;
- scans showing normal tasks cannot modify runner infrastructure;
- protected Pine hash before/after;
- `git diff --check`;
- only protected Pine modified among research files.

Tests must not commit, push, install, enable services, or modify protected files.

## Manual bootstrap report

Write `automation/AUTOMATION-002-R2-RESULT.md` with:

- task ID;
- status `IMPLEMENTED_AWAITING_MANUAL_COMMIT` only when every mandatory validation passes;
- exact changed files;
- exact validation commands and outputs;
- isolation command excerpts;
- retry/state-routing simulation results;
- known limitations;
- manual commit/install/enable commands.

When any mandatory validation fails, use status `TECHNICAL_CORRECTION_REQUIRED` and list the failures.

Leave all intended changes uncommitted.