# EXP-010 — EMA STATE MODEL

Status: DONE / REPORT_READY

## Data

ADAUSDT 4H, Binance public spot klines, `2023-07-01 00:00:00` -> `2024-12-31 20:00:00`.
Rows used: `3300` raw bars, `3298` clustered bars after causal rolling-feature warmup.
No Irobot source was read. No data after 2024-12-31 was used.

## Method

Only OHLC, EMA27, and EMA200 were used. EMA-derived features were computed per closed bar: EMA values, slope percent, angle, angle change, speed, speed change, EMA relation, EMA distance, EMA distance change state, and price distances to EMA27/EMA200.

Corrections were defined without ZigZag as continuous close-to-close movement against the current EMA direction:
`EMA27 > EMA200` with non-negative EMA27 slope means up-direction, `EMA27 < EMA200` with non-positive EMA27 slope means down-direction, otherwise no correction is started. For each completed correction the script measured duration, maximum depth, nearest distance to EMA27/EMA200, whether EMA slopes changed sign, and whether the directional extreme was updated within the next 20 bars. These post-correction fields are attached only after a correction is complete.

State discovery used k-means clustering for k=2..8 on standardized features. k was selected by silhouette score. No state labels were manually assigned; final names are only State numbers.

## Answers

1. Did automatic clustering identify recurring market states?

Yes, with caveats. The best silhouette was `0.406` at `k=2`. This is enough to say the EMA/price/correction features form recurring regimes, but not enough to call them predictive or tradable.

2. Which features most separated the states?

Most separating features by standardized between-state mean distance:
`ema200_slope_pct`, `price_to_ema200_pct`, `ema_distance_pct`, `ema27_slope_pct`, `price_to_ema27_pct`, `ema_distance_change_pct`, `last_correction_bars_to_update_extreme`, `last_correction_updated_extreme`.

3. Do transitions follow State A -> State B -> State C, or are they random?

Transitions are not purely random, but they are not a clean universal chain. Dominant observed transition routes were: State 1 -> State 2 (1.00); State 2 -> State 1 (1.00). The transition matrix should be read as descriptive state persistence/rotation, not as a forecast rule.

4. Does EMA200 behavior change between states?

Yes. Mean EMA200 slope differs across states by `0.3962` percentage points per 4H bar. State-level values are in `cluster_statistics.csv`.

5. Does correction behavior change between states?

Yes. Average completed-correction depth differs by `0.776` percentage points and average completed-correction duration differs by `0.11` bars across states. State-level correction update frequency is also reported in `cluster_statistics.csv`.

## Constraints Audit

- No 2025+ data used.
- No Irobot read.
- No ZigZag used.
- No future data was used for assigning current-bar state; post-correction measurements are only attached after the correction has ended.
- No trading system, entries, exits, stop logic, backtest, or PnL.
- `docs/DEFINITIONS.md` was not changed.

## Artifacts

- `artifacts/ema_state_features.csv`
- `artifacts/ema_state_clusters.csv`
- `artifacts/cluster_statistics.csv`
- `artifacts/state_transition_matrix.csv`
- `artifacts/EMA_STATE_VIEW.pine`
- `artifacts/EMA_STATE_CONTACT_SHEET.pdf`
