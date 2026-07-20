# EXP-031 — Temporal validation diagnostic dataset

Status: TEMPORAL_VALIDATION_DATASET_DATA_FAILED

## Hypothesis

The frozen EXP-027/EXP-029R causal diagnostic protocol can be prepared for untouched calendar-year 2025 data without inspecting EXP-030R transfer-cell outcomes.

## Data and causal constraints

Only official Bybit V5 linear archives already available locally were examined. Every required archive ends on 2024-12-31; no archive covers the declared half-open 2025 interval. No downloading, synthetic substitution, interpolation, forward fill, gap fill, cross-symbol replacement, outcome label, ranking, or EXP-030R sign/pass-fail filter was used. Consequently, the 2025 observation and volatility files retain the frozen schemas but contain zero data rows.

The identical state/reconstruction path was run on the required 2024-10 overlap probe. `protocol_reconciliation.csv` records expected and reconstructed canonical hashes, identity differences, numeric mismatches at 1e-09, and volatility-state comparisons per symbol.

## Results and verdict

All four required symbols fail the 2025 source-coverage gate because funding, OI, and 15-minute OHLC archives end before 2025. The overlap probe is retained as an integrity diagnostic, but it cannot turn absent 2025 source data into a ready dataset.

**TEMPORAL_VALIDATION_DATASET_DATA_FAILED**. This package makes no predictive, confirmation, rejection, cell-selection, or outcome claim.

## Next actions

Acquire byte-validated official Bybit V5 linear archives covering the exact 2025 interval, then rerun this unchanged script before any preregistered EXP-032 confirmation work.
