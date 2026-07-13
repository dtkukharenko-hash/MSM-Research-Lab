# EXP-011 — MULTISCALE EMA TREND BACKBONE

Status: DONE / REPORT_READY

Verdict: NO_TRANSFERABLE_TREND_MODEL

## Data

ADAUSDT Binance public spot klines. 1H source rows: `13200` from `2023-07-01 00:00:00` to `2024-12-31 23:59:59.999000`. 4H rows after causal UTC aggregation: `3300`. No 2025+ data was used. Irobot was not read.

## Answers

1. Best model: `MODEL_B`. It best balanced causal logic, repeated states, and switching control across 4H and 1H.

2. Transfer 4H -> 1H: partial. The same formulas and coefficients run on both timeframes; 4H changes/100=`10.52`, 1H changes/100=`11.08`.

3. Least switching model is recorded in `model_comparison.csv`; selected model switching is within the fixed thresholds: 4H <= 12 and 1H <= 18.

4. Repeating multi-bar episodes form on both timeframes. See `state_dwell_times_4h.csv` and `state_dwell_times_1h.csv`.

5. Direction and condition are separated as `direction` and `condition` fields. MODEL_B/C split EXPANDING, STABLE, WEAKENING, and TRANSITION.

6. 4H UP + 1H DOWN cases occur through `LOWER_OPPOSES_PARENT`; its fraction is `0.2146`.

7. 1H DOWN under 4H UP is treated as a lower-scale directed movement opposite the parent, not as a predefined correction.

8. TYPE_A and TYPE_B visual candidates were generated: TYPE_A=`2`, TYPE_B=`8`, mirror-down=`6`. Full visual confirmation remains the next research-only step.

9. TYPE_A/TYPE_B are selected across distinct months where available; see `visual_review_windows.csv`.

10. The selected result does not intentionally isolate only late-2024 expansion, but dominance is checked in `model_comparison.csv` via largest-state fraction and quarter coverage.

11. 1H/4H mapping is causal: each 1H bar uses only the last fully closed 4H state via `parent.close_time <= child.close_time`.

12. Yes, after EXP-011 it is reasonable to research relative corrections as scale relations, not as absolute single-timeframe states.

## Constraints

No ZigZag, clustering, Irobot, volume, funding, open interest, backtest, PnL, entry, exit, stop, joining-point logic, or 2025+ data. `docs/DEFINITIONS.md` was not changed.
