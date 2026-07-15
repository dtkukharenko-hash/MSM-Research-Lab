# AUTOMATION-002-R3 result

- task_id: `AUTOMATION-002-R3-CORRECTOR-EVIDENCE-AND-INFRA-GUARD`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`

## Changed files

- `automation/msm_runner.sh` — normal-task infrastructure denylist, audit-evidence validation gate, correction arguments, and isolated gate simulation.
- `automation/msm_audit.sh` — honors the runner-provided exact audit output path.
- `automation/msm_correct.sh` — validates supplied audit evidence and embeds its exact findings and recommended action in the single corrector prompt.
- `automation/AUTOMATION-002-R3-RESULT.md` — this manual report.

## Corrector argument contract

`msm_correct.sh TASK_ID TASK_HASH STARTING_COMMIT CORRECTION_ATTEMPT WORKTREE_DIFF_HASH AUDIT_JSON_PATH`

`CORRECTION_ATTEMPT` is `1` or `2`; the audit evidence is respectively attempt `0` or `1`. The runner invokes exactly one corrector only after its evidence gate succeeds.

## Audit-schema validation

Both runner and corrector require a regular file beneath `$STATE_DIR/audits` (the production default is `/home/nnv/.local/state/msm-runner/audits`). They require strict keys, matching task/original ID, audit attempt, task hash, starting commit, and diff hash; `TECHNICAL_CORRECTION_REQUIRED`; `technical_pass=false`; and a non-empty findings list. The corrector also serializes the exact findings and recommended action into its prompt. A mismatch stops as `AUDIT_FAILED` before corrector invocation.

## Tests run

- `bash -n automation/*.sh` — passed.
- `bash automation/install.sh --dry-run` — passed; reported validation-only dry run.
- `bash automation/msm_runner.sh --dry-run` — exited successfully and reported `DRY RUN: preflight would block worktree.` This is expected because the active R2 implementation is intentionally uncommitted; it performed no pull, task parsing, process invocation, result write, commit, or push.
- Isolated valid R0 fixture with a fake Bubblewrap executable and `msm_runner.sh --simulate-correction-gate` plus `msm_correct.sh` — `CORRECT_R1`; exactly one corrector invocation; literal finding `exact R0 finding` and recommended action present in the captured prompt.
- Isolated malformed R0 fixture — `AUDIT_FAILED`; corrector rejected it and the fake Bubblewrap log remained empty (zero corrector invocations).
- Isolated valid R1 fixture — `CORRECT_R2`; exactly one corrector invocation and literal R1 finding present in the captured prompt.
- `bash automation/msm_runner.sh --simulate-route TECHNICAL_CORRECTION_REQUIRED false 2` — `STOP_USER_DECISION_REQUIRED`; zero further corrections.
- `bash automation/msm_runner.sh --simulate-retry` — `RETRY_FIRST=CONSUMED RETRY_SECOND=NOT_CONSUMED`.
- Static scan of `normal_infra_path` and `verify` — all six infrastructure paths are rejected before the allowlist matcher for normal tasks.
- Static scans of runner/corrector — correction receives both diff hash and audit path; exact findings/action are used; Bubblewrap overlays `.git` read-only after the writable repository bind; corrector uses `workspace-write` and `approval_policy="never"`.
- `! rg -n 'git add (\\.|-A)' automation/*.sh` — passed.
- Shell-script mode scan — `install.sh`, `msm_audit.sh`, `msm_correct.sh`, and `msm_runner.sh` are all mode `755`.
- `git diff --check` — passed.
- Research-change scan — the only modified research path is the protected Pine file: `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`.

## Known limitations

The fixture tests use a fake Bubblewrap executable solely to capture invocation count and prompt content; the Bubblewrap mount configuration was additionally verified by static scan. No live Codex process, pull, commit, push, installation, service operation, or protected-file modification was performed.
