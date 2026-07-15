# Current Codex Task

- task_id: `AUTOMATION-002-R3-CORRECTOR-EVIDENCE-AND-INFRA-GUARD`
- status: `READY`
- published_at: `2026-07-15`
- target_branch: `main`
- commit_message: `AUTOMATION-002-R3 fix corrector evidence and infrastructure guard`
- infrastructure_maintenance: `true`

## Objective

Patch the existing uncommitted R2 implementation in place. Make only the targeted fixes below. Do not redesign or broadly rewrite the runner.

## Mandatory protections

Never modify, stage, or commit:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- any research file
- secrets, credentials, SSH/Codex auth material, or files outside the repository

The existing Pine modification must remain byte-identical, unstaged, and uncommitted.

Do not run `git pull`, `git add`, `git commit`, `git push`, `sudo`, `systemctl`, or installation commands. Do not write `.codex/RESULT.md`. Write the manual report to `automation/AUTOMATION-002-R3-RESULT.md`.

## Targeted fixes only

### 1. Hard infrastructure guard for normal tasks

In runner validation, when the active task is not infrastructure maintenance, reject any modification to these paths even if `.codex/ALLOWLIST.txt` contains a broad pattern such as `automation/**`:

- `automation/msm_runner.sh`
- `automation/msm_audit.sh`
- `automation/msm_correct.sh`
- `automation/install.sh`
- `automation/runner.service`
- `automation/runner.timer`

This guard must be independent of the allowlist matcher.

### 2. Pass actual audit evidence to exactly one corrector

Change correction invocation so `msm_correct.sh` receives at minimum:

- original task ID
- task hash
- starting commit
- correction attempt (`1` or `2`)
- current worktree diff hash
- exact audit JSON path

Do not invoke another implementation agent after correction. Sequence remains:

`implementation R0 -> audit R0 -> one correction R1 -> audit R1 -> one correction R2 -> audit R2`.

### 3. Validate audit JSON before correction

Before invoking the corrector, shell must verify that the audit JSON:

- exists and is a regular file under `/home/nnv/.local/state/msm-runner/audits/`;
- is valid JSON;
- matches current `task_id`, `original_task_id`, `attempt`, `task_hash`, `starting_commit`, and `worktree_diff_hash`;
- has `audit_status=TECHNICAL_CORRECTION_REQUIRED`;
- has `technical_pass=false`;
- has non-empty `blocking_findings`.

Any mismatch must stop as `AUDIT_FAILED` without correction, commit, or push.

### 4. Corrector must use exact findings

`msm_correct.sh` must load and schema-check the supplied audit JSON itself. Its prompt must include the exact blocking findings and recommended action from that JSON. It must not rely on vague wording such as “fix audit findings” without supplying them.

The corrector must remain exactly one Codex process, with:

- writable repository worktree;
- `.git` read-only via Bubblewrap;
- runtime state/log directory writable;
- `workspace-write`;
- approval `never`;
- no `.codex/RESULT.md` write;
- no Git mutation or synchronization.

### 5. Retry cleanliness

Keep the existing one-shot `retry_requested` consumption. Before any implementation rerun, require the post-pull worktree to contain only the exact pre-existing protected Pine modification. Record the new current `starting_commit`. Do not reset, restore, stage, or modify the Pine.

## Validation

Run and report exact outcomes:

- `bash -n` for every `automation/*.sh`;
- `bash automation/install.sh --dry-run`;
- runner dry-run;
- static proof that normal tasks reject all six infrastructure paths independent of allowlist;
- isolated valid audit fixture proving R0 routes to one R1 corrector with exact findings;
- invalid/mismatched audit fixture proving `AUDIT_FAILED` and zero corrector invocations;
- R1 fixture proving one R2 correction;
- R2 failure proving `USER_DECISION_REQUIRED` and zero further corrections;
- scans proving corrector receives audit path and diff hash;
- scans proving actual Bubblewrap `.git` read-only enforcement;
- scans proving no `git add .` or `git add -A`;
- executable modes for all automation shell scripts;
- `git diff --check`;
- confirmation that only the protected Pine is modified among research files.

Tests must not commit, push, install, enable services, or alter protected files.

## Manual report

Write `automation/AUTOMATION-002-R3-RESULT.md` containing:

- task ID;
- status `IMPLEMENTED_AWAITING_MANUAL_COMMIT` only if every mandatory validation passes;
- exact files changed;
- exact test commands and results;
- corrector argument contract;
- audit-schema validation details;
- known limitations.

Leave all changes uncommitted.