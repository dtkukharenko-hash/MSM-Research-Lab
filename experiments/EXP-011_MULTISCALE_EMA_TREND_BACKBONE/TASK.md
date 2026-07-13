# EXP-011 — MULTISCALE EMA TREND BACKBONE

## Goal

Define a causal transferable EMA trend-state model independently on 4H and 1H,
then study the relation between closed 1H state and the last fully closed 4H
state.

Do not use correction as an absolute state. Each timeframe must first receive
its own absolute trend state. Relative scale relation is then derived as:

- `ALIGNED_UP`
- `ALIGNED_DOWN`
- `LOWER_OPPOSES_PARENT`
- `LOWER_TRANSITION`
- `PARENT_TRANSITION`

## Data

- Asset: ADAUSDT
- Source: Binance public spot klines
- Base download timeframe: 1H
- Period: 2023-07-01 00:00:00 UTC through 2024-12-31 23:59:59 UTC

The 4H OHLC series is causally aggregated from 1H bars using UTC 4H buckets.
Incomplete 4H candles are removed.

## Constraints

Allowed inputs:

- OHLC
- EMA27
- EMA200
- causal EMA27/EMA200-derived features

Forbidden:

- ZigZag
- clustering
- future bars as features
- retrospective labels as features
- volume, funding, open interest
- Irobot
- backtest, PnL
- entry/exit/stop/joining-point research
- changes to `docs/DEFINITIONS.md`
- 2025+ data

Do not modify EXP-010, EXP-010A, or the existing unstaged EXP009A Pine file.

## Required Outputs

Create `REPORT.md`, `experiment_011.py`, and all required CSV/Pine/PDF artifacts
under `artifacts/`.
