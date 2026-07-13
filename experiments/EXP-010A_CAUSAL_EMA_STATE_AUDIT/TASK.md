# EXP-010A — CAUSAL EMA STATE AUDIT

## Goal

Audit EXP-010 and test a corrected two-layer causal model:

- Layer A: EMA backbone state.
- Layer B: local price phase.

The experiment checks whether the model can distinguish:

1. local correction inside a stable trend backbone;
2. local correction inside a weakening trend backbone;
3. loss of trend backbone.

## Constraints

- Asset: ADAUSDT
- Timeframe: 4H
- Period: 2023-07-01 00:00:00 UTC through 2024-12-31 20:00:00 UTC
- Inputs: open, high, low, close, EMA27, EMA200 only

Forbidden:

- Irobot
- ZigZag
- volume, funding, open interest
- future bars as state features
- retrospective labels as input features
- entries, exits, stops, PnL, backtest, trading parameter search
- changes to `docs/DEFINITIONS.md`

Do not modify or commit the existing unstaged EXP-009A Pine file.

## Required Outputs

Create `REPORT.md`, `experiment_010a.py`, and all files listed under `artifacts/`:

- `exp010_audit.json`
- `backbone_features.csv`
- `local_price_phases.csv`
- `composite_states.csv`
- `clustering_runs.csv`
- `cluster_stability.csv`
- `backbone_state_statistics.csv`
- `transition_matrix_full.csv`
- `state_change_matrix.csv`
- `state_dwell_times.csv`
- `state_outcomes.csv`
- `corrections.csv`
- `exp010_vs_exp010a.csv`
- `EMA_STATE_AUDIT_VIEW.pine`
- `EMA_STATE_AUDIT_CONTACT_SHEET.pdf`
