# EXP-014 — Common invariant transfer

Status: PARTIAL_TRANSFER

## Reuse map

The executable closed-bar aggregation, ATR convention, direction-aware sign, overlap predicate, and 1H child fallback are reused from EXP-013 (`load_bars`, `phase_metrics`, and its detector conventions). This audit imports EXP-013 before loading data. Fixed factor 1.0 was selected before rows were evaluated.

## Data inventory

ADAUSDT uses the existing project 1H archive, aggregated into completed 4H UTC bars, from 2023-07-01 00:00:00 through 2024-12-31 20:00:00, with no gaps. The child scale is documented 1H fallback because no local 15m archive exists. BTCUSDT, ETHUSDT, SOLUSDT, and XRPUSDT are UNAVAILABLE: no existing local OHLC archive was discovered. ADA rows inside 2023-10-19 00:00:00 through 2024-01-03 23:59:59 are excluded.

## Detection and controls

There are 369 accepted rows and 56 DIAGNOSTIC_FLAG rows over 3300 parent bars (111.818 per 1,000). Each control is a deterministic, non-overlapping same-instrument row; explicit duration, ATR, parent-age, and phase mismatch fields are in `matched_controls.csv`. Exact matching is not claimed. Accepted median reassertion is 0.755653 ATR versus 0.764307 for controls; paired rank-biserial is 0.105691, above-control fraction 0.552846. These are descriptive structural contrasts.

## Ablation and stability

`component_ablation.csv` evaluates base plus each fixed EXP-013 component predicate; sample-collapse warnings prevent a stricter subset from replacing the base rule. `parameter_stability.csv` contains actual detector calls at 0.8, 1.0, and 1.2.

## Counterexamples and limitations

The strongest flagged rows are retained in `detections.csv`; their explicit reason is parent-boundary failure. This shows balance plus a renewed displacement can occur after the established parent boundary has failed, so the minimal source transition alone is insufficient for those rows. Coverage is one available instrument, exclusively 1H fallback, and the control sample is finite. Direction and time-segment dependence remain reported at row level rather than generalized.

## Verdict

**PARTIAL_TRANSFER** — the rule is observed outside the source interval for ADAUSDT but cannot meet the required three-instrument breadth. The strongest retained knowledge is that the closed-bar sequence remains computable without future pivots and parent-boundary diagnostics identify a structural insufficiency.
