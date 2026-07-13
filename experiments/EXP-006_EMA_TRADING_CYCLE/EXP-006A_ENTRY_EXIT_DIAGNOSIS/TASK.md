# EXP-006A — Entry / Exit Diagnosis

## Goal

Diagnose why the strong EXP-006 TRAIN result did not transfer to TEMPORAL TEST:

- entry failure;
- exit failure;
- stop failure;
- market regime shift;
- or a combination.

This experiment must not create a new strategy, optimize parameters, open the true holdout, or change the MSM model.

## Scope

Use only the three EXP-006 shortlisted combinations:

- `ENTRY_A_STOP_A_EXIT_B`
- `ENTRY_A_STOP_B_EXIT_B`
- `ENTRY_A_STOP_A_EXIT_A`

Primary focus:

- `ENTRY_A_STOP_A_EXIT_B`

## Periods

TRAIN:

- 2023-07-01 00:00 UTC -> 2024-12-19 23:59 UTC

TEMPORAL TEST:

- 2024-12-20 00:00 UTC -> 2025-07-01 00:00 UTC

True holdout after 2025-07-01 04:00 UTC must not be used.

## Method

1. Measure entry quality independently of the actual exit using fixed horizons:
   3, 6, 12, 24, 48 bars.
2. Run oracle exit diagnostics for each entry path. Oracle is diagnostic only.
3. Assign one diagnostic failure type per trade using fixed thresholds:
   `BAD_ENTRY`, `GOOD_ENTRY_BAD_EXIT`, `LATE_ENTRY`, `EARLY_EXIT`,
   `LATE_EXIT`, `STOP_TOO_TIGHT`, `REGIME_FAILURE`, or `MIXED`.
4. Compare TRAIN and TEMPORAL TEST overall, by side, and by entry regime.
5. Compare market environment between TRAIN and TEMPORAL TEST.
6. Diagnose STOP_A vs STOP_B for ENTRY_A.
7. Diagnose EXIT_A vs EXIT_B and fixed exits for ENTRY_A + STOP_A.

## Required Artifacts

- `REPORT.md`
- `experiment_006a.py`
- `artifacts/trade_path_metrics.csv`
- `artifacts/fixed_horizon_outcomes.csv`
- `artifacts/oracle_exit_analysis.csv`
- `artifacts/failure_classification.csv`
- `artifacts/train_test_failure_comparison.csv`
- `artifacts/regime_environment_comparison.csv`
- `artifacts/stop_diagnosis.csv`
- `artifacts/exit_diagnosis.csv`
- `artifacts/entry_quality_train_vs_test.png`
- `artifacts/failure_types_train_vs_test.png`
- `artifacts/mfe_giveback_train_vs_test.png`
- `artifacts/regime_comparison.png`
- `artifacts/EMA_CYCLE_DIAGNOSIS_REVIEW.pine`
- `artifacts/EMA_CYCLE_DIAGNOSIS_OVERVIEW.pdf`

## Verdict

One of:

- `ENTRY_VALID_EXIT_FAILURE`
- `EXIT_VALID_ENTRY_FAILURE`
- `STOP_FAILURE`
- `REGIME_SHIFT_DOMINATES`
- `MULTIPLE_FAILURES`
- `NO_RECOVERABLE_EDGE`
- `DATA_INSUFFICIENT`
