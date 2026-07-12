# EXP-005C — Taxonomy of Matched Non-Major Outcomes

## Status

DONE / REPORT_READY

## Context

EXP-005B showed that `OPPOSITE_TREND` does not separate major starts from matched local turn candidates. The previous technical label `failed_turn` is not treated here as an established market type.

This experiment uses the neutral object name:

- `matched_non_major_event`
- `matched_non_major_outcome`

## Research Question

Can the 45 matched non-major events from EXP-005B be split into stable, interpretable outcome classes using only OHLC behavior after the event point?

## Scope

This is a post-event descriptive experiment. It answers:

> What happened after matched event points?

It does not answer:

> Can the outcome be predicted before the event?

Prediction is reserved for a separate future experiment using only pre-event features.

## Inputs

Use EXP-005B artifacts:

- `major_starts.csv`
- `failed_turns.csv`
- `matched_turn_controls.csv`
- `selection_bias_comparison.csv`

Primary dataset:

- 45 matched non-major events from `failed_turns.csv`

Major starts are used only after taxonomy construction for comparison.

## Constraints

- Use OHLC and OHLC-derived features only.
- Do not use holdout.
- Do not use EMA, ZigZag, volume, funding, OI, PnL, or strategy logic.
- Do not manually assign categories before feature calculation.
- Do not optimize features to separate major vs failed.
- Do not remove inconvenient events without documentation.

## Outcome Windows

For each event, calculate outcome windows:

- H=10
- H=20
- H=30
- H=60

Primary horizon:

- H=30

Outcome window:

- `[t0 + 1, t0 + H]`

The event bar is not included in the future outcome window.

## Required Outputs

- `REPORT.md`
- `experiment_005c.py`
- `artifacts/outcome_features.csv`
- `artifacts/outcome_features_wide.csv`
- `artifacts/outcome_feature_summary.csv`
- `artifacts/outcome_feature_correlations.csv`
- `artifacts/cluster_assignments.csv`
- `artifacts/cluster_profiles.csv`
- `artifacts/cluster_stability.csv`
- `artifacts/co_clustering_matrix.csv`
- `artifacts/outcome_taxonomy.csv`
- `artifacts/taxonomy_rules.md`
- `artifacts/major_vs_taxonomy_comparison.csv`
- `artifacts/representative_events.csv`
- `artifacts/outcome_pca.csv`
- `artifacts/outcome_pca.png`
- `artifacts/outcome_embedding.png`
- `artifacts/OUTCOME_TAXONOMY_REVIEW.pine`
- `artifacts/OUTCOME_TAXONOMY_OVERVIEW.pdf`

## Verdict Options

- `STABLE_OUTCOME_TAXONOMY_FOUND`
- `WEAK_OUTCOME_TAXONOMY`
- `CONTINUOUS_OUTCOME_SPECTRUM`
- `INSUFFICIENT_SAMPLE_FOR_TAXONOMY`
- `FAILED_TURNS_CONTAIN_DELAYED_MAJOR_MOVES`
