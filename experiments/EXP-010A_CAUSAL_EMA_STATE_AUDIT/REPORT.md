# EXP-010A — CAUSAL EMA STATE AUDIT

Status: DONE / REPORT_READY

Verdict: CAUSAL_EMA_STATE_STRUCTURE_FOUND

## Data

ADAUSDT 4H, `2023-07-01 00:00:00` -> `2024-12-31 20:00:00`. Source: local EXP-010 OHLC artifact, recomputed EMA27/EMA200. Irobot was not read. No 2025+ rows were used.

## Answers

1. Did EXP-010 contain future leakage?

Yes. `last_correction_updated_extreme` and `last_correction_bars_to_update_extreme` were outcome-style fields measured after correction end and then used as clustering inputs on later rows. EXP-010A excludes them from backbone clustering.

2. Which EXP-010 features were duplicating?

EXP-010 constructed speed as slope, so `ema27_speed_pct` duplicated `ema27_slope_pct`, and `ema200_speed_pct` duplicated `ema200_slope_pct`. Near-duplicate correlations are listed in `exp010_audit.json`.

3. Why did k=2 in EXP-010 split the market into 88.4% and 11.6%?

Because the mixed feature set included price-to-EMA distance, EMA distance, and post-correction outcome fields. That separated the rare late-2024 expansion/extreme-distance regime from the rest more than it separated lifecycle states.

4. Was EXP-010 State 2 a lifecycle state or extreme price expansion?

Mostly an extreme price expansion: EXP-010 State 2 had large `price_to_ema200_pct` and large EMA distance. EXP-010A treats that as an audit finding, not a lifecycle label.

5. Was a stable k found after removing lookahead and duplicate features?

Chosen model: `MODEL_RAW`, k=`2`, seed=`100`. Median silhouette `0.576`, median ARI `0.989`, p10 ARI `0.881`, min cluster fraction `0.119`. Stable candidate: `True`.

6. Which model is more stable: MODEL_RAW or MODEL_ALIGNED?

The selected model is `MODEL_RAW`. Full comparison for all k is in `cluster_stability.csv`.

7. Does the model distinguish PULLBACK inside one backbone state, PULLBACK inside another backbone state, and CONTEXT_LOSS?

Partially. Pullback/recovery bars exist by backbone state: `{1: 2729, 2: 324}`. CONTEXT_LOSS events: `28`. The distinction is structural and causal, but visual review is still required before assigning semantic names.

8. Does the model visually distinguish correction while EMA200 keeps rising vs correction while EMA200 flattens?

Partially. EMA200 slope statistics differ by state in `backbone_state_statistics.csv`, and Pine/PDF artifacts expose examples. No semantic names are assigned.

9. Do backbone states recur on multiple segments, not only one extreme expansion?

Episodes by state are in `state_dwell_times.csv`; states with at least two episodes: `2`.

10. Can the states be considered causal?

Yes for assignment: backbone features use only current and previous closed bars, and local phases are determined after the current bar closes. Outcome data are retrospective evaluation only. They are not state input features.

11. What verdict does EXP-010A receive?

`CAUSAL_EMA_STATE_STRUCTURE_FOUND`.

## Correction Summary

- correction count: `113`
- median correction duration: `11.00` bars
- one-bar correction fraction: `0.000`

## Artifacts

All required artifacts were created under `artifacts/`.
