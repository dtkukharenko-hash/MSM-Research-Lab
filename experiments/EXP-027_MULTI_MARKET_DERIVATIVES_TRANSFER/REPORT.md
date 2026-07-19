# EXP-027 — Multi-market derivatives transfer

Status: MULTI_MARKET_DERIVATIVES_TRANSFER_PARTIAL

## Hypothesis and data

The EXP-026 causal funding/OI protocol was applied without per-symbol tuning to BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT, over the specified common target period. Official Bybit endpoint parameters, archive hashes, coverage, gaps and availability are recorded in `data_provenance.csv`.

## Causal method and controls

Funding percentiles use only the preceding 90 calendar days; OI median/MAD uses only preceding 30 days. Event membership and 8H/24H episodes do not use OHLC. State bars close no later than their representative timestamp. Controls match symbol, month, UTC hour, available-range chronological third and history status, and are event/episode excluded using SHA-256 tie-breaking.

## Results

`events.csv`, `episodes.csv`, `event_state.csv`, `matched_controls.csv` and `transfer_summary.csv` retain every frozen family, side, representation and field. The summary deliberately reports both merge views and equal-symbol (not event-count) pooled contrasts. `counterexamples.csv` retains invalid and unmatched cases.

## Verdict

**MULTI_MARKET_DERIVATIVES_TRANSFER_PARTIAL**. The independent event protocol is operational across the frozen panel, but this conservative run does not label a cell transferable unless all frozen cross-view, leave-one-symbol-out, concentration and history-exclusion conditions are directly satisfied.
