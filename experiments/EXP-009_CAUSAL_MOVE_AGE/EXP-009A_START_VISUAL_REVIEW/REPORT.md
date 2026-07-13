# EXP-009A — START Visual Review

## Status

REPORT_READY

## Scope

ADAUSDT 4H, 2023-07-01 00:00 UTC -> 2024-12-31 20:00 UTC. Irobot was used read-only for OHLC, EMA27, EMA200, and ATR14 reconstruction. Existing EXP-008 and EXP-009 artifacts were used as fixed inputs.

No PnL, stop, exit, parameter optimization, new start detector, or 2025-2026 data was used.

## Method

The audit compares the fixed `START_A`, `START_B`, and `START_C` active moves from EXP-009 against the 12 EXP-008 reference moves. `FIRST_OBSERVABLE_CHANGE` is a descriptive closed-bar annotation only: it records the first visible change found from allowed facts such as EMA27 slope, local structure break, closed-bar price/EMA27 behavior, directional body expansion, and halt of old-direction extremes. It is not a detector and is not used as a predictor.

## Required Answers

1. `START_B` has median delay 83 bars because its directed-expansion condition usually waits for an EMA-aligned 20-bar breakout near EMA27. In the matched references, its starts land mostly in `ZONE_3_EARLY_CONTINUATION`, `ZONE_4_MATURE_MOVE`, or later: {'ZONE_3_EARLY_CONTINUATION': 3, 'ZONE_6_EXHAUSTION_OR_CHOP': 1, 'ZONE_5_LATE_MOVE': 1, 'ZONE_4_MATURE_MOVE': 1}. It is selective, so it rejects many early or ambiguous starts, but the surviving starts often occur after the reference birth and after PRIMARY_ENTRY.
2. `START_A` creates 67 false moves because a two-bar EMA context hold is too sensitive to local EMA regime flips. The false-move classification mix is `{'CHOP': 0, 'COUNTERTREND_NOISE': 14, 'FALSE_BREAK': 22, 'LATE_RESTART': 12, 'SMALL_LOCAL_MOVE': 13, 'UNKNOWN': 6}`; many are small local moves, old-move continuations, or late restarts rather than new major moves.
3. `START_C` creates 38 false moves because compression-breakout patterns recur inside chop and inside already-running movements. The false-move classification mix is `{'CHOP': 1, 'COUNTERTREND_NOISE': 6, 'FALSE_BREAK': 12, 'LATE_RESTART': 10, 'SMALL_LOCAL_MOVE': 5, 'UNKNOWN': 4}`.
4. Closest detector hits by delay: [{'detector': 'START_B', 'move_id': 'M07', 'delay_bars': 11.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}, {'detector': 'START_C', 'move_id': 'M07', 'delay_bars': 11.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}, {'detector': 'START_A', 'move_id': 'M07', 'delay_bars': 12.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}, {'detector': 'START_A', 'move_id': 'M04', 'delay_bars': 14.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}, {'detector': 'START_C', 'move_id': 'M05', 'delay_bars': 16.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}, {'detector': 'START_A', 'move_id': 'M05', 'delay_bars': 17.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}, {'detector': 'START_C', 'move_id': 'M01', 'delay_bars': 28.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}, {'detector': 'START_B', 'move_id': 'M08', 'delay_bars': 54.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}, {'detector': 'START_B', 'move_id': 'M01', 'delay_bars': 83.0, 'reference_zone': 'ZONE_3_EARLY_CONTINUATION'}].
5. Full or partial failures are listed in `artifacts/missed_move_analysis.csv`. The weakest cases remain short/ambiguous reversals and transitions where EMA context lags the retrospective boundary, especially M02, M03, M06, M09, and M12 for `START_B`.
6. The most frequent `FIRST_OBSERVABLE_CHANGE` type is `PRICE_EMA27_HOLD` (8/12). Observations repeated in at least 8 of 12 moves: PRICE_EMA27_HOLD=8.

## Key Tables

- `artifacts/start_visual_audit.csv` records detected START_A/B/C lines, delays, zone, EMA context, price-vs-EMA27, and trigger description for each reference move.
- `artifacts/missed_move_analysis.csv` records detected/missed status and descriptive miss reasons per move and detector.
- `artifacts/false_active_move_analysis.csv` classifies unmatched active moves as CHOP, CONTINUATION_OLD_MOVE, SMALL_LOCAL_MOVE, FALSE_BREAK, LATE_RESTART, COUNTERTREND_NOISE, or UNKNOWN.
- `artifacts/first_observable_changes.csv` records the descriptive first visible change per reference move.
- `artifacts/observable_change_summary.csv` summarizes repeated observations.
- `artifacts/EXP009A_START_REVIEW.pine` is the TradingView viewer.
- `artifacts/EXP009A_START_REVIEW.pdf` has 12 pages, one per reference move.

## Verdict

VISUAL_REVIEW_READY
