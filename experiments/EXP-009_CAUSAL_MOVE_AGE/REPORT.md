# EXP-009 — Causal Move Age

## Scope

ADAUSDT 4H, 2023-07-01 00:00 UTC -> 2024-12-31 20:00 UTC. No 2025-2026 data was used.
The experiment used only OHLC, EMA27, EMA200, ATR14, and closed bars. It did not calculate PnL and did not use stop or exit logic.

## Required Answers

1. Causal active-move starts can be detected partially; best fixed detector: `START_B`.
2. Best START_A/B/C: `START_B`.
3. Reference moves found by best detector: 6 of 12.
4. Median start delay: 83.0 bars.
5. False active moves: 14.
6. Primary entries: 17; secondary entries: 3.
7. Entry zone share ZONE_1/2/3: 25.0%; ZONE_4/5/6: 25.0%.
8. Repeated-signal reduction vs EXP-007: 96.2%.
9. BLOCKED_EXAMPLES rejected: 97.2%.
10. Maximum one primary entry per active move was enforced by state; max total causal entries per active move: 2.
11. Do not proceed to backtest as a trading system yet; the state machine is causal but only partially aligned with EXP-008 reference boundaries.
12. Ambiguous or missed reference moves for best detector: M02, M03, M04, M06, M09, M12.

## Start Detector Metrics

| detector | reference_moves_detected | recall | false_active_moves | median_start_delay_bars | primary_entries_generated | secondary_entries_generated | signals_per_active_move | entry_zone_1_2_3_share | entry_zone_4_5_6_share | primary_label_hit_pm6_bars | secondary_label_hit_pm6_bars | blocked_example_rejection_rate | repeated_signal_reduction | unknown_rate | max_entries_per_active_move |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| START_A | 9 | 0.75 | 67 | 22.0 | 71 | 18 | 1.1710526315789473 | 0.1348314606741573 | 0.24719101123595505 | 0.3333333333333333 | 0.4166666666666667 | 0.8333333333333334 | 0.832391713747646 | 0.5955056179775281 | 2 |
| START_B | 6 | 0.5 | 14 | 83.0 | 17 | 3 | 1.0 | 0.25 | 0.25 | 0.16666666666666666 | 0.08333333333333333 | 0.9722222222222222 | 0.9623352165725048 | 0.45 | 2 |
| START_C | 10 | 0.8333333333333334 | 38 | 52.5 | 41 | 11 | 1.0833333333333333 | 0.17307692307692307 | 0.25 | 0.3333333333333333 | 0.3333333333333333 | 0.9722222222222222 | 0.9020715630885122 | 0.5384615384615384 | 2 |

## Best Detector Reference Matching

| detector | reference_move_id | reference_direction | matched_active_move_id | detected | start_delay_bars | start_before_primary | causal_move_covers_reference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| START_B | M01 | LONG | START_B_AM007 | True | 83.0 | False | False |
| START_B | M02 | SHORT |  | False | nan | False | False |
| START_B | M03 | LONG |  | False | nan | False | False |
| START_B | M04 | LONG |  | False | nan | False | False |
| START_B | M05 | LONG | START_B_AM011 | True | 116.0 | False | False |
| START_B | M06 | SHORT |  | False | nan | False | False |
| START_B | M07 | SHORT | START_B_AM013 | True | 11.0 | False | False |
| START_B | M08 | SHORT | START_B_AM015 | True | 54.0 | False | False |
| START_B | M09 | LONG |  | False | nan | False | False |
| START_B | M10 | SHORT | START_B_AM016 | True | 83.0 | False | False |
| START_B | M11 | LONG | START_B_AM020 | True | 148.0 | False | False |
| START_B | M12 | SHORT |  | False | nan | False | False |

## Best Detector Entry Zone Counts

| entry_label | reference_zone | count |
| --- | --- | --- |
| PRIMARY_CAUSAL_ENTRY | OUTSIDE_REFERENCE | 8 |
| PRIMARY_CAUSAL_ENTRY | ZONE_0_BEFORE_MOVE | 1 |
| PRIMARY_CAUSAL_ENTRY | ZONE_1_BIRTH | 1 |
| PRIMARY_CAUSAL_ENTRY | ZONE_3_EARLY_CONTINUATION | 4 |
| PRIMARY_CAUSAL_ENTRY | ZONE_4_MATURE_MOVE | 2 |
| PRIMARY_CAUSAL_ENTRY | ZONE_5_LATE_MOVE | 1 |
| SECONDARY_CAUSAL_ENTRY | OUTSIDE_REFERENCE | 1 |
| SECONDARY_CAUSAL_ENTRY | ZONE_4_MATURE_MOVE | 1 |
| SECONDARY_CAUSAL_ENTRY | ZONE_5_LATE_MOVE | 1 |

## Best Detector Blocked Examples

| blocked_reason | rejected | count |
| --- | --- | --- |
| EXHAUSTION | True | 12 |
| MATURE_MOVE | True | 12 |
| TOO_LATE | False | 1 |
| TOO_LATE | True | 11 |

## Verdict

PARTIAL_CAUSAL_MOVE_AGE
