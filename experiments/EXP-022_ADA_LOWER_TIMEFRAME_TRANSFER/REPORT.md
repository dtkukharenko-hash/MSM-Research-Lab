# EXP-022 — ADA lower-timeframe transfer

Status: LOWER_TIMEFRAME_DATA_UNAVAILABLE

## Hypothesis

The frozen parent/counter detector and five parent-origin representations might retain non-degenerate causal geometry on ADAUSDT 15m→1H, 5m→15m, and 3m→15m. This audit cannot test that hypothesis without valid lower-timeframe bars.

## Data readiness and causal constraints

The documented local ADAUSDT archives are the committed 1H (13,200 rows) and 4H (3,300 rows) OHLC CSVs. `data_readiness.csv` hashes and audits both sources for every requested timeframe. They are UTC-aligned, ordered archives, but are coarser than every requested child interval. Aggregating coarser bars cannot reconstruct 15m, 5m, or 3m components; no data were downloaded, fabricated, interpolated, forward-filled, or substituted. Therefore every requested mapping is `UNAVAILABLE`; no aggregate was constructed.

## Method, baselines, and controls

Factors 0.8, 1.0, and 1.2; `FIXED_8`, `DIRECTION_RUN`, `ATR_ORIGIN`, `CONFIRMED_DIRECTION_CHANGE`, and `HYBRID_ORIGIN`; the 8/32/two-parent/1.0-ATR rules; and all geometry families are frozen in the emitted schemas. Detector and representation rows explicitly state `NOT_RUN_DATA_UNAVAILABLE`, rather than presenting zeros as observations. The control file preserves the predeclared source-excluded/non-overlapping method flags but has zero paired support. No outcome labels or threshold choices are used.

## Results and verdict

There are no native or causally derivable local 15m, 5m, or 3m bars, and consequently no ready parent mapping. It would be invalid to compare these empty samples with the committed 4H→1H result or to claim shared-15m-parent agreement. Counterexample classes are explicitly retained as not evaluable rather than fabricated.

**LOWER_TIMEFRAME_DATA_UNAVAILABLE** — no requested mapping has sufficient local data for an honest test. The rejection condition for availability is met. Obtain a content-verifiable native 3m/5m/15m ADAUSDT archive (and audit UTC completeness and overlap) before rerunning; do not infer lower bars from 1H or 4H.

## Files produced

`data_readiness.csv`, `detections.csv`, `representations.csv`, `scale_comparison.csv`, `matched_controls.csv`, `parameter_stability.csv`, and `counterexamples.csv` are deterministic outputs of `experiment_022.py`.
