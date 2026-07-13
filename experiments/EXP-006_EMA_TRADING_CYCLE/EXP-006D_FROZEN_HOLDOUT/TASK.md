# EXP-006D — Frozen Holdout

## Goal

Run the final independent confirmatory test of the fully frozen EMA trading cycle:

`ENTRY_A + STOP_A + EXIT_R5`

on the untouched holdout:

- 2025-07-01 04:00 UTC -> 2026-07-01 00:00 UTC

This is the final confirmatory test of the EXP-006 branch. After this run, the same holdout cannot be used again as an independent test or as a tuning source.

## Frozen System

- Asset: ADAUSDT
- Timeframe: 4H
- Indicators: EMA27, EMA200, ATR14
- Entry: `ENTRY_A`
- Stop: `STOP_A`
- Exit: `EXIT_R5`
- Costs: fee 0.10% per side, slippage 0.05% per side
- Position: 100% equity, compounding, one position, no leverage

## Required Artifacts

- `REPORT.md`
- `experiment_006d.py`
- `artifacts/FROZEN_SPECIFICATION.md`
- `artifacts/frozen_specification.json`
- `artifacts/holdout_signals.csv`
- `artifacts/holdout_trades_r5.csv`
- `artifacts/holdout_trades_r0.csv`
- `artifacts/holdout_trades_r2.csv`
- `artifacts/holdout_metrics.csv`
- `artifacts/exit_comparison.csv`
- `artifacts/direction_metrics.csv`
- `artifacts/quarterly_metrics.csv`
- `artifacts/cost_stress.csv`
- `artifacts/concentration_checks.csv`
- `artifacts/mfe_capture.csv`
- `artifacts/causality_audit.csv`
- `artifacts/intrabar_ambiguities.csv`
- `artifacts/monthly_returns.csv`
- `artifacts/equity_curve.png`
- `artifacts/drawdown_curve.png`
- `artifacts/quarterly_returns.png`
- `artifacts/mfe_capture_distribution.png`
- `artifacts/HOLDOUT_TRADING_CYCLE_REVIEW.pine`
- `artifacts/HOLDOUT_TRADING_CYCLE_OVERVIEW.pdf`

## Verdict

One of:

- `HOLDOUT_CONFIRMED`
- `HOLDOUT_PARTIAL`
- `HOLDOUT_REJECTED`
- `IMPLEMENTATION_BLOCKED`
- `DATA_INSUFFICIENT`
