# Current Codex Task

- task_id: `EXP-030R-TRANSFER-FAILURE-LOCALIZATION`
- status: `READY`
- published_at: `2026-07-20`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-030-TRANSFER-FAILURE-LOCALIZATION`
- commit_message: `EXP-030R transfer failure localization`

## Objective

Correct EXP-030 without changing its frozen analytical protocol. Reuse only the committed EXP-029R diagnostic dataset and EXP-027 frozen criteria. Do not rebuild structural states, volatility labels, events, controls, representations, thresholds, or outcome labels.

The prior EXP-030 attempt is invalid because it loaded the complete gzip dataset into memory, omitted `UNKNOWN` volatility support from the volatility output, and required manifests in a read-only temporary location.

## Frozen input

Read `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/observations.csv.gz` and the remaining committed EXP-029R validation/provenance outputs. Verify their committed hashes and require EXP-029R status `DIAGNOSTIC_DATASET_READY` with zero reconciliation mismatches.

## Mandatory implementation corrections

1. Read `observations.csv.gz` by streaming iteration. `list(csv.DictReader(...))`, full-file DataFrame loading, or any equivalent whole-file materialisation is forbidden.
2. Aggregation may retain only bounded grouped accumulators needed for the declared cells and diagnostics.
3. Preserve three independent tests exactly as EXP-030: event family, side within family, and causal volatility regime.
4. Volatility output must include `LOW_VOL`, `MID_VOL`, `HIGH_VOL`, and `UNKNOWN`. `UNKNOWN` is diagnostic only and can never qualify as an explanatory passing cell.
5. For `UNKNOWN`, preserve row count, event/control support, symbol support, family/side concentration, validity exclusions, and explicit reason counts.
6. Tests A and B must not condition on volatility. Test C primary result keys must not contain family or side and must use equal-family safeguards.
7. Each test independently calculates support, contrast, sign consistency, concentration, leave-one-symbol-out survival, 8H/24H agreement, exclusion rate, chronological-third stability, and verdict.
8. Preserve every cell and every failed gate. Do not select the strongest cell after inspection.

## Frozen gates

A non-UNKNOWN cell passes only when all EXP-027 gates pass: sufficient support in at least three symbols; same sign in at least three symbols; no symbol above 50% pooled absolute-contrast concentration; every feasible LOSO sign survives; 8H and 24H signs agree; exclusions are at most 50%; and sign persists in at least two chronological thirds in at least three symbols.

## Decision

Select exactly one:

- `TRANSFER_FAILURE_LOCALIZED_FAMILY`
- `TRANSFER_FAILURE_LOCALIZED_SIDE`
- `TRANSFER_FAILURE_LOCALIZED_VOLATILITY`
- `TRANSFER_FAILURE_LOCALIZED_MULTIPLE`
- `TRANSFER_FAILURE_NOT_LOCALIZED`
- `TRANSFER_FAILURE_LOCALIZATION_DATA_FAILED`

`UNKNOWN` support cannot create a positive localization verdict.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/REPORT.md`
- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/data_provenance.csv`
- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/family_localization.csv`
- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/side_localization.csv`
- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/volatility_localization.csv`
- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/localization_summary.csv`
- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/validation_summary.csv`
- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/counterexamples.csv`
- `experiments/EXP-030R_TRANSFER_FAILURE_LOCALIZATION/experiment_030r.py`

Do not create or retain an EXP-030 task directory.

## Deterministic validation

1. Validate EXP-029R provenance, schema, reconciliation status and compressed input hash.
2. Prove streaming use by code inspection and a machine-checkable validation row; whole-file materialisation is a hard failure.
3. Verify all four volatility regimes are present in `volatility_localization.csv`, with `UNKNOWN` marked diagnostic/non-qualifying.
4. Reproduce report counts and verdict directly from output CSVs.
5. Run twice from identical inputs.
6. Store ordinary byte SHA-256 manifests outside the repository in the first writable location selected in this order: `${XDG_STATE_HOME:-$HOME/.local/state}/msm-exp-evidence/EXP-030R-TRANSFER-FAILURE-LOCALIZATION/`, `$HOME/msm-exp-evidence/EXP-030R-TRANSFER-FAILURE-LOCALIZATION/`, then `/dev/shm/EXP-030R-TRANSFER-FAILURE-LOCALIZATION/`.
7. Before use, create the directory and perform an actual write/delete probe. Do not use `/tmp` or the orchestrator-owned read-only evidence directory.
8. Keep both manifests through audit and require exact path-by-path equality for all nine outputs.
9. Compile without retained cache files, run `git diff --check`, and perform baseline-relative allowlist validation.

If no writable external evidence location exists, return `TECHNICAL_CORRECTION_REQUIRED` with the probed paths and errors.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 file, or any EXP-013 through EXP-030 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Only the nine EXP-030R outputs may change inside the repository. The external manifests must not be committed.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-030R outputs unstaged. The orchestrator performs final baseline-relative validation, commits once with the declared message and pushes to `main`.