# EXP-029R — Derivatives diagnostic dataset

Status: DIAGNOSTIC_DATASET_READY

## Hypothesis

The frozen EXP-027 event representatives and matched controls can be rebuilt from
the validated 15-minute archives without changing event definitions, controls,
representations, or aggregation rules.

## Data, method, and causal constraints

BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT use the frozen EXP-027 period and identities.
Each scalar diagnostic observation retains its event/control role, chronological
third, representation, field, value, validity, and explicit UNKNOWN reason. OHLC
state is restricted to bars closed at or before the observation timestamp. The
volatility regime compares current ATR only to the preceding 96 closed bars.

The null/control model is the frozen matched-control cohort. Every committed
aggregate key is reconstructed with the frozen aggregation rule and reconciled at
the fixed tolerance `1e-09`; support counts must match as well as values.

## Results and verdict

Committed rows: 17752. MATCH: 17752; MISMATCH: 0; NOT_COMPARABLE: 0. Totals are re-read from `reconciliation.csv` for `validation_summary.csv`.

**DIAGNOSTIC_DATASET_READY**. This is a diagnostic audit, not an outcome-labelled edge claim.

## Next actions

Any predictive hypothesis must be preregistered and tested separately against this
matched-control baseline.
