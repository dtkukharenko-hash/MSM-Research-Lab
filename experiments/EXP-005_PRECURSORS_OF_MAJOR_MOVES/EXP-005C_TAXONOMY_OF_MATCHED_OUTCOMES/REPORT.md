# EXP-005C — Taxonomy of Matched Non-Major Outcomes

## Status

DONE / REPORT_READY

## Executive Verdict

`WEAK_OUTCOME_TAXONOMY`

The 45 matched non-major events do not form a strong multi-class taxonomy. The primary H=30 clustering produced one broad cluster containing 41/45 events and two small trend-continuation outlier clusters of size 3 and 1.

Secondary verdict:

`FAILED_TURNS_CONTAIN_DELAYED_MAJOR_MOVES` is not supported. Delayed major move count was 0.

## Context

EXP-005B found that `OPPOSITE_TREND` is likely a selection artifact: it appears before matched failed turns at least as often as before major starts. EXP-005C therefore does not search for another pre-event filter. It describes what happened after the 45 matched non-major event points.

The label `failed_turn` from EXP-005B is treated as a technical label only, not as an established market behavior type.

## Research Question

Can the 45 matched non-major outcomes be split into stable and interpretable classes using only post-event OHLC behavior?

Answer: only weakly. There is a dominant broad outcome group plus a few outliers, not a robust taxonomy of several stable classes.

## Input Events

- matched non-major events: 45
- major starts used only for final comparison: 15
- symbol: ADAUSDT
- timeframe: 4H
- source: read-only Irobot OHLC feature file

## Data Integrity Checks

The script verifies that the EXP-005B input contains exactly 45 matched non-major events.

Generated feature tables:

- `outcome_features.csv`: 180 rows, one row per event x horizon.
- `outcome_features_wide.csv`: 45 rows, one row per event.

No holdout data was used.

## Outcome Windows

Outcome windows were calculated for:

- H=10
- H=20
- H=30
- H=60

Primary horizon:

- H=30

The future window is `[t0 + 1, t0 + H]`. The event bar `t0` is not included in the outcome window.

## Feature Definitions

Features include:

- signed close return;
- MFE and MAE;
- efficiency and signed efficiency;
- total path;
- return sign changes;
- local pivots;
- high-low range;
- realized volatility ratio;
- ATR decay;
- overlap ratio;
- candle structure;
- trend persistence;
- reversal timing;
- delayed outcome checks.

Local pivots are offline descriptors of a completed outcome window. They are not trading signals.

## Normalization

Two normalizations were used:

- percentage normalization relative to `close_t0`;
- ATR normalization using ATR(14), calculated only on bars up to and including `t0`.

Directional normalization uses the event direction:

- positive signed values mean movement in the hypothetical reversal direction;
- negative signed values mean movement against that direction.

## Exploratory Analysis

Artifacts:

- `outcome_feature_summary.csv`
- `outcome_feature_correlations.csv`

The sample is small and contains correlated OHLC-derived features. No features were silently removed; the compact clustering feature set was fixed from the task's core list.

## Cluster Selection

Primary feature set:

- `signed_close_return_atr`
- `mfe_atr`
- `mae_atr`
- `signed_efficiency`
- `net_to_path_ratio`
- `return_sign_changes`
- `number_of_local_pivots`
- `high_low_range_atr`
- `realized_volatility_ratio`
- `ATR_decay`
- `overlap_ratio`
- `fraction_bars_in_event_direction`
- `longest_same_direction_run`
- `time_to_MFE`
- `time_to_MAE`

Scaling:

- RobustScaler-style median/IQR scaling.

Algorithms checked:

- KMeans, k=2..7
- Agglomerative average-linkage, k=2..7
- DBSCAN-style density clustering

Primary clustering:

- H=30, agglomerative, k=3

This produced:

- cluster 0: 3 events
- cluster 1: 41 events
- cluster 2: 1 event

## Cluster Stability

Stability checks:

- H=20 vs H=30 vs H=60
- KMeans vs agglomerative vs DBSCAN-style clustering
- robust vs standard scaling
- reduced feature set
- 500 subsampling iterations at 80% of events

Key results:

- bootstrap mean ARI: 0.659
- H=20 ARI vs primary: 0.421
- H=60 ARI vs primary: 0.712
- KMeans H=30 ARI vs primary: 0.487
- DBSCAN-style ARI vs primary: 0.096

The cluster structure is not robust enough to claim a stable taxonomy.

## Cluster Profiles

Primary H=30 cluster profiles:

| cluster | size | name | profile |
|---:|---:|---|---|
| 0 | 3 | `TREND_CONTINUATION` | strong movement against the hypothetical reversal direction |
| 1 | 41 | `RANGE_WHIPSAW` | broad mixed group with low positive signed efficiency and many sign changes |
| 2 | 1 | `TREND_CONTINUATION` | single outlier, not a stable type |

Only one cluster has enough size to be treated as a recurring group, and it is broad rather than sharply defined.

## Rule-Based Taxonomy

Rules are documented in `artifacts/taxonomy_rules.md`.

They are post-hoc interpretations of cluster profiles and are not optimized for prediction.

Rule-based labels include:

- `TREND_CONTINUATION`
- `WEAK_REVERSAL`
- `RANGE_WHIPSAW`
- `COMPRESSION`
- `DELAYED_MAJOR_MOVE`
- `UNCLASSIFIED`

The rule taxonomy is useful for review, but not strong enough to declare stable market outcome classes.

## Delayed Major Moves

Delayed major move flag:

- 0/45

No matched non-major event became a delayed major move after the primary 30-bar window under the fixed EXP-005A/EXP-005B major threshold.

## Comparison With Major Starts

Major starts were added only after taxonomy construction.

H=30 median comparison:

- major starts median signed return: 3.217 ATR
- matched non-major median signed return: 0.446 ATR
- major starts median MFE: 4.302 ATR
- matched non-major median MFE: 2.091 ATR
- major starts median signed efficiency: 0.255
- matched non-major median signed efficiency: 0.041

Major starts look more like the stronger right tail of directionality, MFE, and efficiency than a cleanly separate discrete class.

## Discrete Classes Vs Continuous Spectrum

Embedding/PCA artifacts:

- `outcome_pca.csv`
- `outcome_pca.png`
- `outcome_embedding.png`

Discrete-class verdict:

`WEAK_CLUSTER_STRUCTURE`

The data show a broad central cloud with outliers, not several balanced and stable discrete types.

## Visual Review

Visual review artifacts:

- `OUTCOME_TAXONOMY_REVIEW.pine`
- `OUTCOME_TAXONOMY_OVERVIEW.pdf`

The Pine script contains fixed labels from `outcome_taxonomy.csv`. It does not compute classes and is not a trading tool.

## Limitations

- Sample size is small: 45 non-major events and 15 major starts.
- The primary clustering contains one very large cluster and two small outlier clusters.
- DBSCAN-style clustering does not agree with the primary assignment.
- UMAP was unavailable in the environment; deterministic PCA coordinates are used as the embedding fallback.
- The taxonomy is descriptive and post-event only.

## Verdict

`WEAK_OUTCOME_TAXONOMY`

EXP-005C did not find a stable multi-class taxonomy. It found a broad `RANGE_WHIPSAW`-like group and a few trend-continuation outliers.

## Implications For EXP-005

The 45 matched non-major outcomes are not one homogeneous "failure" type, but the evidence is too weak to freeze a taxonomy for prediction.

Major starts appear stronger in scale and path efficiency than non-major outcomes. The difference may be continuous severity rather than a discrete class boundary.

## Recommended Next Experiment

Do not open EXP-005D as a classifier yet.

Recommended next step:

`EXP-005D_CONTINUOUS_OUTCOME_SEVERITY`

Goal: model post-event outcome severity and efficiency as continuous quantities, then later test whether pre-event OHLC features can explain severity without using post-event outcome features.
