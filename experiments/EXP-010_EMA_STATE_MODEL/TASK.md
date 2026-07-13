# EXP-010 — EMA STATE MODEL

## Goal

Investigate whether EMA27 and EMA200 describe market movement state rather than entry points.

The experiment must test whether objective trend states can be derived only from price, EMA27, and EMA200.

## Data

- Instrument: ADAUSDT
- Timeframe: 4H
- Period: 2023-07-01 through 2024-12-31
- Data after 2024-12-31 is forbidden.

## Inputs

Use only:

- OHLC
- EMA27
- EMA200

Do not use ZigZag, future data, trading-system logic, entries, exits, PnL, or Irobot.

## Required Artifacts

- `artifacts/ema_state_features.csv`
- `artifacts/ema_state_clusters.csv`
- `artifacts/cluster_statistics.csv`
- `artifacts/state_transition_matrix.csv`
- `artifacts/EMA_STATE_VIEW.pine`
- `artifacts/EMA_STATE_CONTACT_SHEET.pdf`
- `REPORT.md`

## Required Report Questions

1. Did automatic clustering identify recurring market states?
2. Which features most separated the states?
3. Do transitions follow a pattern such as State A -> State B -> State C, or are they random?
4. Does EMA200 behavior change between states?
5. Does correction behavior change between states?

No trading conclusions are allowed.
