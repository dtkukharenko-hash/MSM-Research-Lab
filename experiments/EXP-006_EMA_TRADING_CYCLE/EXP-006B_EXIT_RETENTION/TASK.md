# EXP-006B — Exit Retention

## Goal

Test whether movement retention can be improved after the unchanged EXP-006 `ENTRY_A`, without changing the EMA regime logic, initial `STOP_A`, or entry timing.

Basis: EXP-006A returned `ENTRY_VALID_EXIT_FAILURE`. The next research step is therefore exit / retention only.

## Fixed Base

- Asset: ADAUSDT
- Timeframe: 4H
- Entry: `ENTRY_A` only
- Initial stop: `STOP_A` only
- EMA regimes: unchanged EMA27 / EMA200 logic from EXP-006
- Entry execution: next open after closed-bar signal
- True holdout not used: 2025-07-01 04:00 UTC -> 2026-07-01 00:00 UTC

## Data Split

TEMPORAL TEST from EXP-006 has already been inspected. It is no longer independent development data.

- DEVELOPMENT: 2023-07-01 00:00 UTC -> 2024-06-30 23:59 UTC
- EXIT VALIDATION: 2024-07-01 00:00 UTC -> 2024-12-19 23:59 UTC
- REUSED TEMPORAL TEST: 2024-12-20 00:00 UTC -> 2025-07-01 00:00 UTC

Exit variants are selected on DEVELOPMENT only. EXIT VALIDATION applies selected variants without changes. REUSED TEMPORAL TEST is used only as a non-independent consistency check.

## Exit Variants

- `EXIT_R0`: baseline two consecutive closes beyond EMA27.
- `EXIT_R1`: break-even activation after MFE >= 1 ATR.
- `EXIT_R2`: ATR giveback after MFE >= 1.5 ATR, exit after 1 ATR giveback from best favorable price.
- `EXIT_R3`: proportional 50% MFE giveback after MFE >= 1 ATR.
- `EXIT_R4`: EMA27 hysteresis warning / confirmation.
- `EXIT_R5`: first of proportional 50% MFE giveback, EMA27 hysteresis, STOP_A, full regime flip.

No thresholds are optimized.

## Required Artifacts

- `REPORT.md`
- `experiment_006b.py`
- `artifacts/all_exit_trades.csv`
- `artifacts/development_metrics.csv`
- `artifacts/selected_exits.csv`
- `artifacts/exit_validation_metrics.csv`
- `artifacts/reused_temporal_metrics.csv`
- `artifacts/mfe_capture_distribution.csv`
- `artifacts/failure_type_comparison.csv`
- `artifacts/exit_reason_counts.csv`
- `artifacts/cost_stress.csv`
- `artifacts/concentration_checks.csv`
- `artifacts/trade_phase_analysis.csv`
- `artifacts/mfe_capture_comparison.png`
- `artifacts/giveback_comparison.png`
- `artifacts/equity_curves.png`
- `artifacts/EMA_EXIT_RETENTION_REVIEW.pine`
- `artifacts/EMA_EXIT_RETENTION_OVERVIEW.pdf`

## Verdict

One of:

- `EXIT_RETENTION_FOUND`
- `PARTIAL_EXIT_IMPROVEMENT`
- `EARLY_EXIT_REPLACES_LATE_EXIT`
- `NO_STABLE_EXIT_IMPROVEMENT`
- `ENTRY_EDGE_TOO_WEAK`
- `DATA_INSUFFICIENT`
