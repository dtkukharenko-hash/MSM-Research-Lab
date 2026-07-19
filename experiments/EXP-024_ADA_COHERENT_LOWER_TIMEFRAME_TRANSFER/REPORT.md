# EXP-024 — Coherent lower-timeframe transfer

Status: COHERENT_LOWER_TIMEFRAME_TRANSFER_PARTIAL

## Hypothesis

The frozen causal detector and five predeclared parent-origin representations may retain descriptive, non-degenerate normalized geometry across native Bybit ADAUSDT lower scales. This is not a trading or outcome study.

## Data and causal constraints

All three native archives have the exact EXP-023 hashes and complete UTC coverage from 2023-07-01 through 2024-12-31. Native 3m→15m and 5m→15m OHLCV equality is asserted component-by-component. 1H is derived exclusively from complete groups of four native 15m bars; the older committed 1H source is explicitly excluded as a provenance conflict. States end strictly before each counter start. No pivots, future returns, labels, or selected thresholds are used.

## Method

Actual detector runs use factors 0.8, 1.0 and 1.2. Every representation retains invalid origins and applies the fixed 8-parent-bar, 32-parent-bar cap, two-bar confirmation, and 1.0 parent-ATR rules. `representations.csv` holds row-level geometry and causal assertions; `scale_comparison.csv` uses only the frozen bins. Controls are deterministic, source-excluded and non-overlapping with every detection window.

## Results and verdict

`detections.csv`, `parameter_stability.csv`, and `scale_comparison.csv` report support, factor overlap, direction/time thirds, concentration and scale-specific geometry. `counterexamples.csv` retains invalidity, origin-collapse and overlapping-detection counterexamples rather than excluding them. **COHERENT_LOWER_TIMEFRAME_TRANSFER_PARTIAL** — all three internally coherent mappings are measured, but repeated lower-scale overlap and mapping-specific support/stability make the evidence descriptive and limited rather than broadly transferable. No representation was selected from downstream contrasts.

## Files produced

This report and seven CSVs are deterministic outputs of `experiment_024.py`; `data_provenance.csv` records the coherent source hierarchy.
