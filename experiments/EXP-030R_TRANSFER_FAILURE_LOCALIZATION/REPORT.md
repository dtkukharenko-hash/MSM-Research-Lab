# EXP-030R — Transfer failure localization

Status: TRANSFER_FAILURE_LOCALIZED_VOLATILITY

## Data and causal constraints

This run streams the committed EXP-029R gzip observations through `csv.DictReader`; it keeps only a current episode and bounded categorical accumulators. It verifies the committed hashes of all EXP-029R provenance/validation inputs, the frozen observation schema, `DIAGNOSTIC_DATASET_READY`, and zero reconciliation mismatches. It does not rebuild events, controls, structural states, volatility labels, representations, thresholds, or outcomes.

## Method

Test A is event family and Test B is side within family; neither conditions on volatility. Test C is causal volatility only: its result keys exclude family and side, and contrast pooling gives each populated frozen family equal weight within each symbol before equal-symbol pooling. All cells are retained and independently gated on support, signs, concentration, LOSO, 8H/24H agreement, exclusions, and chronological thirds. UNKNOWN retains support, concentration, exclusions, and reasons, but is diagnostic and never qualifying.

## Result

**TRANSFER_FAILURE_LOCALIZED_VOLATILITY**. Qualifying cells: family 0, side 0, volatility 226. All four volatility regimes, including diagnostic UNKNOWN, are in `volatility_localization.csv`. The external evidence manifests record byte-identical paths across two independent streaming runs.
