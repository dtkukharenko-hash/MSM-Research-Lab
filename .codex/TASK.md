# Current Codex Task

- task_id: `AUTOMATION-005-R1-RESTORE-ALLOWLISTED-RESEARCH-PATHS`
- status: `READY`
- published_at: `2026-07-16`
- original_task_id: `AUTOMATION-005-FEEDER-V1`
- correction_attempt: `1`
- target_branch: `main`
- commit_message: `AUTOMATION-005-R1 restore allowlisted research paths`
- infrastructure_maintenance: `true`

## Objective

Correct one purely technical policy defect in feeder V1: `automation/msm_task_feeder.py::is_protected()` currently rejects every path containing an `artifacts` component and rejects experiment `.md`, `.txt`, `.csv`, `.pine`, and `.json` files. This prevents ordinary explicitly allowlisted research tasks from reaching the orchestrator, contradicting the feeder contract and the already-established allowlist-based research workflow.

Restore exact-path allowlisting for ordinary research files while retaining all required hard protections and fail-closed validation. Do not change research definitions, hypotheses, holdout policy, visual judgments, research decisions, orchestrator transitions, or worker-role semantics.

## Required correction

1. Remove only the unintended blanket restrictions that reject:
   - every path containing an `artifacts` directory;
   - every experiment `.md`, `.txt`, `.csv`, `.pine`, or `.json` path.
2. Continue to reject, at minimum:
   - `docs/DEFINITIONS.md`;
   - `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`;
   - `.codex/RESULT.md`;
   - `.git` and `.git/*`;
   - absolute paths, traversal, non-normalized paths, duplicates, secrets, credentials, private keys, `.env` files, and installed system paths.
3. Preserve the requirement that every writable path must appear explicitly and exactly in `.codex/ALLOWLIST.txt`.
4. Preserve all task-text gates for definition changes, hypothesis changes, holdout access or extension, TradingView or visual review, ambiguous research judgment, and user decisions.
5. Do not broaden infrastructure-task ingestion; `infrastructure_maintenance: true` must remain blocked from automatic production ingestion.

## Validation requirements

Extend deterministic isolated fixtures to prove all of the following:

1. An ordinary allowlisted research source path under `experiments/` is accepted.
2. An ordinary allowlisted research report/artifact path such as an experiment-local `.md` or `.csv` is accepted when explicitly listed and when the task text contains no research-decision gate.
3. `docs/DEFINITIONS.md` is rejected.
4. The protected EXP009A Pine is rejected exactly and remains byte-identical and unstaged.
5. `.codex/RESULT.md`, `.git/*`, absolute, traversing, duplicate, malformed, secret-like, and installed-system paths remain rejected.
6. Existing feeder fixtures still pass, including deduplication, changed-hash blocking, concurrent enqueue, restart preservation, kill switch, no Git mutation, and no Python cache artifacts.
7. No research file is modified by the validation itself.

## Hard protections

Never modify, stage, commit, delete, rename, chmod, rewrite, or include in any allowlist:

- `docs/DEFINITIONS.md`
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- `.codex/RESULT.md`
- `.git` internals

Do not access a new holdout. Do not perform visual review. Do not change definitions, hypotheses, acceptance criteria, or research conclusions.

## Allowed changes

Only:

- `automation/msm_task_feeder.py`
- `automation/verify_feeder.sh`
- `automation/AUTOMATION-005-R1-RESULT.md`

## Result contract

Write `automation/AUTOMATION-005-R1-RESULT.md` only after every validation passes. Set status `IMPLEMENTED_AWAITING_MANUAL_COMMIT`. Record the exact defect corrected, exact changed files, exact commands and outputs, proof that explicitly allowlisted ordinary research paths are accepted, proof that all hard protections remain rejected, and proof that the protected Pine is byte-identical and unstaged. Leave implementation changes unstaged and uncommitted for the deterministic infrastructure bootstrap.