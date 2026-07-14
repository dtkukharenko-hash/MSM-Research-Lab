# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

## Goal

Automatically discover all potential LONG conflict sections on ADAUSDT 4H for:

`2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59 UTC`.

Current status: `AWAITING_TW_EPISODE_CHAIN_REVIEW`.

This phase does not classify continuation/reversal, does not validate BACKBONE_C, does not seek entries/exits, and does not calculate PnL.

## Data

Use saved EXP-011 4H OHLC:

`experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`

EXP-011 data source is Binance public spot klines. Manual review will be done on Bybit ADAUSDT Perpetual Contract 4H, so minor bar-level differences are possible.

## Method

Compute EMA27 and EMA200 on the full available history before slicing to the research period. Discover `CORE_CONFLICT_TRIGGER` bars in LONG context only:

- `ema27 > ema200`
- `ema200_slope_6 > 0`
- EMA27 moving down
- `close < ema27`

Raw conflicts end by `FULL_RESET_CONFIRMED`, `EMA_CROSS`, or `OPEN_AT_PERIOD_END`. Nearby raw conflicts are merged into `LC###` sections when the gap is at most 6 4H bars and EMA structure remains compatible.

## Constraints

Forbidden: SHORT analysis, data after 2024-01-08, future outcomes, ZigZag, clustering, BACKBONE_C for selection, previous high/low conditions, PnL, backtest, entry, exit, stop, risk, Irobot, changing `docs/DEFINITIONS.md`, changing EXP-011, changing EXP-011A, and staging existing EXP009A Pine changes.

## Outputs

- `raw_conflict_events.csv`
- `long_conflict_sections.csv`
- `conflict_bar_features.csv`
- `manual_boundary_review.csv`
- `LONG_CONFLICT_WINDOWS.pine`
- `REVIEW_INSTRUCTIONS.md`
- `REPORT.md`

## R2 Outputs

R2 preserves V1 in `long_conflict_sections_v1_snapshot.csv` and adds full dispute sections:

- `long_dispute_sections_v2.csv`
- `long_dispute_events_v2.csv`
- `conflict_bar_features_v2.csv`
- `boundary_revision_comparison.csv`
- `manual_full_section_review.csv`

R2 status: `AWAITING_TW_FULL_SECTION_REVIEW`.

## R3 Outputs

R3 preserves R2 snapshots and treats the R2 `3 of 4 recovered_long_bar` rule as a `RECOVERY_ATTEMPT`, not as a final section close. A fixed `RECOVERY_PROBATION_BARS = 24` confirms or fails each recovery attempt. Failed recoveries continue the same section as a new episode.

- `long_dispute_sections_v2_snapshot.csv`
- `long_dispute_events_v2_snapshot.csv`
- `LONG_CONFLICT_WINDOWS_R2_SNAPSHOT.pine`
- `long_dispute_sections_r3.csv`
- `dispute_episodes_r3.csv`
- `recovery_attempts_r3.csv`
- `new_configuration_attempts_r3.csv`
- `conflict_bar_features_r3.csv`
- `r2_r3_section_mapping.csv`
- `manual_episode_chain_review.csv`
- `LONG_DISPUTE_EPISODE_CHAINS_R3.pine`

R3 status: `AWAITING_TW_EPISODE_CHAIN_REVIEW`.

Commit message: `EXP-011B chain dispute episodes and confirm exits`.
