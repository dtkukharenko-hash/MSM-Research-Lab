# EXP-006D Visual Review — Frozen Holdout Trades

## Goal

Create a visual audit for the already calculated EXP-006D frozen holdout trades.

The Pine Script must show factual entries and exits for the frozen system:

- ENTRY_A
- STOP_A
- EXIT_R5

Holdout period:

2025-07-01 04:00 UTC -> 2026-07-01 00:00 UTC

## Source

Primary source:

- `experiments/EXP-006_EMA_TRADING_CYCLE/EXP-006D_FROZEN_HOLDOUT/artifacts/holdout_trades_r5.csv`

Optional context sources:

- `holdout_signals.csv`
- `intrabar_ambiguities.csv`
- `causality_audit.csv`
- `frozen_specification.json`

## Rules

- This is not a new backtest.
- Do not recalculate trades with another algorithm.
- Do not optimize anything.
- Do not change rules.
- Do not create new signals.
- Use Pine `indicator()`, not `strategy()`.
- Hardcode all visual trade marks from `holdout_trades_r5.csv`.
- Do not change Irobot.
- Do not change `docs/DEFINITIONS.md`.

## Required Outputs

- `artifacts/EXP006D_HOLDOUT_TRADES.pine`
- `artifacts/holdout_trade_map.csv`
- `artifacts/visual_audit_mismatches.csv`
- `REPORT.md`

## Report Questions

1. Are all 31 trades displayed?
2. Are there any mismatches between Pine and `holdout_trades_r5.csv`?
3. Which exit types occur most often?
4. Which trades gave back most of their MFE?
5. Which trades became losers almost immediately?
6. Where was entry normal but exit poor?
7. Where was the issue already in the entry?
8. Is there a visible difference between 2025-Q3/Q4 and 2026-Q1/Q2?
9. Is there a visible LONG/SHORT difference?
10. Which 10 trades should be manually reviewed in TradingView first?
