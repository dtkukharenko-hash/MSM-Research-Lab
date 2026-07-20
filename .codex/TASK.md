# Current Codex Task

- task_id: `EXP-029R-DERIVATIVES-DIAGNOSTIC-DATASET`
- status: `READY`
- published_at: `2026-07-20`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-029-DERIVATIVES-DIAGNOSTIC-DATASET`
- commit_message: `EXP-029R derivatives diagnostic dataset`

## Objective

Correct EXP-029 without changing its frozen data-generation protocol. Rebuild the diagnostic dataset and implement a complete persisted comparator against every directly comparable committed EXP-027 aggregate row. Do not tune thresholds, redefine events, change controls, alter representations, or introduce outcome labels.

The previous EXP-029 attempt is invalid because `transfer_summary.csv` was read but its 7,800 directly comparable aggregate rows were not actually compared; `validation_summary.csv` marked the check PASS unconditionally and `reconciliation.csv` contained no row-level aggregate evidence.

## Frozen inputs

Use the committed outputs under `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/` and validated external archives exactly as in EXP-029. Use exactly BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT over the frozen EXP-027 period. Do not modify EXP-027 or any earlier experiment.

## Diagnostic dataset

Create the same substantive dataset as EXP-029:

- one observation row per event representative and matched control;
- symbol, event family, side, 8H/24H view, episode/control identity;
- chronological third;
- causal volatility regime;
- representation, field, value, validity/history status and explicit UNKNOWN reason;
- coverage and counterexample summaries.

## Mandatory aggregate comparator

For every committed EXP-027 `transfer_summary.csv` row that is directly comparable from the reconstructed diagnostic observations:

1. derive the exact corresponding aggregate using the same frozen grouping key and aggregation rule;
2. preserve the full EXP-027 key and both committed and reconstructed values;
3. write one `reconciliation.csv` row with status exactly `MATCH`, `MISMATCH`, or `NOT_COMPARABLE`;
4. include absolute difference, tolerance, reason, committed support, reconstructed support and source row identifier;
5. compare all 7,800 directly comparable rows, not a sample or selected subset;
6. preserve every mismatch and every non-comparable row; never suppress or overwrite them;
7. use a fixed numeric tolerance declared before comparison and apply it uniformly;
8. derive all comparison totals in `validation_summary.csv` from `reconciliation.csv`, never from hard-coded PASS values.

A row may be `NOT_COMPARABLE` only when required source detail is genuinely absent from committed EXP-027 outputs. The reason must be specific and machine-checkable. Rows that can be reconstructed must never be downgraded to `NOT_COMPARABLE` to avoid a mismatch.

## PASS gate

`READY`/`PASS` is allowed only when all are true:

- expected committed aggregate row count is reproduced;
- every directly comparable row has a persisted reconciliation record;
- unexplained `MISMATCH` count is zero;
- all `NOT_COMPARABLE` rows have explicit allowed reasons and are counted separately;
- report totals equal `reconciliation.csv` totals;
- diagnostic observation joins and identifier uniqueness pass;
- actual two-run SHA-256 manifests for all nine outputs are identical path by path;
- protected baseline files remain byte-identical and unstaged.

If any directly comparable row is missing, any mismatch is unexplained, or PASS is not derived from reconciliation evidence, return `TECHNICAL_CORRECTION_REQUIRED`.

## Decision

Select exactly one dataset status:

- `DIAGNOSTIC_DATASET_READY` — complete dataset and comparator pass all gates;
- `DIAGNOSTIC_DATASET_PARTIAL` — dataset is usable but explicitly documented source limitations leave allowed non-comparable rows;
- `DIAGNOSTIC_DATASET_FAILED` — dataset, reconciliation or source integrity is insufficient.

Do not force a positive status.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/REPORT.md`
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/data_provenance.csv`
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/observations.csv`
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/volatility_state.csv`
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/reconciliation.csv`
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/coverage_summary.csv`
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/validation_summary.csv`
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/counterexamples.csv`
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`

Do not create or retain EXP-028, EXP-028R, EXP-028S or failed EXP-029 task directories.

## Deterministic validation

1. Parse all EXP-027 inputs and verify their hashes and schemas.
2. Verify observation/control joins, uniqueness, causal bar closure, chronological thirds and UNKNOWN handling.
3. Reconstruct and persist the full aggregate comparator.
4. Recompute validation totals only from output CSVs and reproduce REPORT status.
5. Generate all nine outputs once and save ordinary byte SHA-256 manifest externally under `${HOME}/.local/state/msm-orchestrator/evidence/EXP-029R-DERIVATIVES-DIAGNOSTIC-DATASET/run1.sha256`.
6. Run again from identical inputs and save `run2.sha256` in the same directory.
7. Require exact nine-path equality and keep both manifests until audit completes.
8. Compile the script without retaining cache artifacts, run `git diff --check`, and perform baseline-relative allowlist validation.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 file, or any EXP-013 through EXP-029 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Only the nine EXP-029R outputs may change inside the repository. External validated archives may only be read. The two manifests must remain outside the repository and must not be committed.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-029R outputs unstaged. The orchestrator performs final validation, commits once with the declared message and pushes to `main`.