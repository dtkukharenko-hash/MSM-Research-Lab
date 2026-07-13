# EXP-008 — Major Move Entry Labeling

## Scope

ADAUSDT 4H, 2023-07-01 00:00 UTC -> 2024-12-31 20:00 UTC. Data after 2024-12-31 was not used.
Irobot was used as a read-only data source. No PnL, backtest, stop, exit, optimization, or mass trade generation was performed.

## Method

Major movements were marked retrospectively with a coarse local-extrema window of 36 bars and a minimum absolute close-to-close move of 25%.
This method is used only to create a reference visual map. It is not a live boundary detector and not a ZigZag proof.
Each movement received at most one `PRIMARY_ENTRY`, one `OPTIONAL_SECONDARY_ENTRY`, and three blocked examples.

## Required Answers

1. Major movements found: 12.
2. `PRIMARY_ENTRY` labels: 12.
3. `OPTIONAL_SECONDARY_ENTRY` labels: 12.
4. `BLOCKED_EXAMPLES`: 36.
5. EXP-007 signals per major movement: max 126, median 25.0; details are in `artifacts/one_entry_per_move_diagnosis.csv`.
6. Share of mapped EXP-007 signals in mature/late/exhaustion zones: 65.3%.
7. Early approved labels differ mainly by lower movement age and lower completed-fraction; late blocked labels can still have acceptable EMA direction, so EMA proximity alone does not separate them.
8. EMA27/EMA200 is useful for direction context, but it is not enough to decide timing inside one already-running movement.
9. Timing needs movement age, completed fraction, whether the entry is the first same-move label, and whether the move is already mature or exhausting.
10. The reference rule `maximum one primary entry per major movement` is useful diagnostically: it directly removes repeated same-move signals without changing EMA direction logic.
11. One causal start detector cannot be formulated yet from this label pass; the labels expose timing structure but remain retrospective.
12. Ambiguous cases: M02, M03, M04, M06, M07, M08, M10.

## Movement Summary

| move_id | direction | start_time | end_time | start_price | end_price | duration_bars | return_pct | ema27_vs_ema200_at_start | confidence | boundary_method | boundary_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | LONG | 2023-10-19 00:00:00 | 2023-12-13 20:00:00 | 0.2406 | 0.6681 | 335 | 177.68079800498754 | EMA27_BELOW_EMA200 | HIGH | coarse_retrospective_local_extrema_order36_return25pct | LOW_to_HIGH; reference labeling only |
| M02 | SHORT | 2023-12-28 04:00:00 | 2024-01-08 00:00:00 | 0.6626 | 0.4741 | 65 | -28.44853607002716 | EMA27_ABOVE_EMA200 | MEDIUM | coarse_retrospective_local_extrema_order36_return25pct | HIGH_to_LOW; reference labeling only |
| M03 | LONG | 2024-01-08 00:00:00 | 2024-01-11 08:00:00 | 0.4741 | 0.5993 | 20 | 26.407930816283493 | EMA27_BELOW_EMA200 | LOW | coarse_retrospective_local_extrema_order36_return25pct | LOW_to_HIGH; reference labeling only |
| M04 | LONG | 2024-02-07 08:00:00 | 2024-02-18 08:00:00 | 0.4757 | 0.6352 | 66 | 33.52953542148413 | EMA27_BELOW_EMA200 | MEDIUM | coarse_retrospective_local_extrema_order36_return25pct | LOW_to_HIGH; reference labeling only |
| M05 | LONG | 2024-02-24 00:00:00 | 2024-03-14 08:00:00 | 0.5762 | 0.796 | 116 | 38.14647691773689 | EMA27_ABOVE_EMA200 | HIGH | coarse_retrospective_local_extrema_order36_return25pct | LOW_to_HIGH; reference labeling only |
| M06 | SHORT | 2024-03-14 08:00:00 | 2024-03-19 20:00:00 | 0.796 | 0.5866 | 33 | -26.306532663316585 | EMA27_ABOVE_EMA200 | MEDIUM | coarse_retrospective_local_extrema_order36_return25pct | HIGH_to_LOW; reference labeling only |
| M07 | SHORT | 2024-04-08 16:00:00 | 2024-04-17 12:00:00 | 0.6153 | 0.4322 | 53 | -29.757841703234195 | EMA27_BELOW_EMA200 | MEDIUM | coarse_retrospective_local_extrema_order36_return25pct | HIGH_to_LOW; reference labeling only |
| M08 | SHORT | 2024-05-20 20:00:00 | 2024-06-24 16:00:00 | 0.5022 | 0.3685 | 209 | -26.622859418558342 | EMA27_BELOW_EMA200 | MEDIUM | coarse_retrospective_local_extrema_order36_return25pct | HIGH_to_LOW; reference labeling only |
| M09 | LONG | 2024-07-05 00:00:00 | 2024-07-16 00:00:00 | 0.3236 | 0.4512 | 66 | 39.431396786155744 | EMA27_BELOW_EMA200 | HIGH | coarse_retrospective_local_extrema_order36_return25pct | LOW_to_HIGH; reference labeling only |
| M10 | SHORT | 2024-07-16 00:00:00 | 2024-08-05 08:00:00 | 0.4512 | 0.2956 | 122 | -34.48581560283689 | EMA27_ABOVE_EMA200 | MEDIUM | coarse_retrospective_local_extrema_order36_return25pct | HIGH_to_LOW; reference labeling only |
| M11 | LONG | 2024-10-26 12:00:00 | 2024-12-03 00:00:00 | 0.3255 | 1.3 | 225 | 299.38556067588326 | EMA27_BELOW_EMA200 | HIGH | coarse_retrospective_local_extrema_order36_return25pct | LOW_to_HIGH; reference labeling only |
| M12 | SHORT | 2024-12-03 00:00:00 | 2024-12-20 08:00:00 | 1.3 | 0.7621 | 104 | -41.37692307692308 | EMA27_ABOVE_EMA200 | HIGH | coarse_retrospective_local_extrema_order36_return25pct | HIGH_to_LOW; reference labeling only |

## Good vs Blocked Feature Summary

| feature | approved_median | blocked_median | approved_mean | blocked_mean | difference_note |
| --- | --- | --- | --- | --- | --- |
| bars_from_move_start | 5.5 | 60.0 | 10.75 | 87.36111111111111 | blocked labels are later in bar-count age |
| atr_from_move_start | 2.1169161573764157 | 7.003288969746903 | 2.3052815000007043 | 8.112220707603408 | context feature compared for descriptive audit only |
| fraction_move_completed | 0.19339940043999976 | 0.6702653908647769 | 0.17703967886435298 | 0.6087994888564524 | blocked labels occur after much more of the retrospective move has already happened |
| price_distance_ema27_atr | 1.0056026602742905 | 1.2445658847598988 | 1.122858075910486 | 1.39038164846653 | EMA proximity alone is not enough; blocked labels can still be near EMA27 |
| ema_distance_atr | 2.2183548857260997 | 2.7698482138843072 | 2.255989724233626 | 2.6537456040883436 | context feature compared for descriptive audit only |
| ema27_crossings_last10 | 1.0 | 0.0 | 1.2083333333333333 | 0.8611111111111112 | crossing count helps with chop but does not separate all late examples |

## EXP-007 Diagnostic

Existing EXP-007 signal timestamps were mapped into this reference movement map for diagnosis only. EXP-008 did not recompute trades or PnL.

| move_id | exp007_signal_count | first_signal_time | first_signal_variant | first_signal_zone | mature_late_exhaustion_signal_count | one_entry_per_move_keeps_signal | one_entry_per_move_discards_count | diagnosis_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | 126 | 2023-10-19 16:00:00 | ENTRY_T1 | ZONE_1_BIRTH | 104 | 2023-10-19 16:00:00 | 125 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M02 | 11 | 2023-12-28 08:00:00 | ENTRY_T2 | ZONE_1_BIRTH | 4 | 2023-12-28 08:00:00 | 10 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M03 | 22 | 2024-01-09 04:00:00 | ENTRY_A | ZONE_2_FIRST_PULLBACK | 18 | 2024-01-09 04:00:00 | 21 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M04 | 25 | 2024-02-07 20:00:00 | ENTRY_T1 | ZONE_1_BIRTH | 24 | 2024-02-07 20:00:00 | 24 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M05 | 95 | 2024-02-24 20:00:00 | ENTRY_T1 | ZONE_1_BIRTH | 72 | 2024-02-24 20:00:00 | 94 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M07 | 20 | 2024-04-10 00:00:00 | ENTRY_T1 | ZONE_3_EARLY_CONTINUATION | 3 | 2024-04-10 00:00:00 | 19 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M08 | 120 | 2024-05-22 04:00:00 | ENTRY_T1 | ZONE_3_EARLY_CONTINUATION | 71 | 2024-05-22 04:00:00 | 119 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M09 | 5 | 2024-07-05 20:00:00 | ENTRY_T4 | ZONE_2_FIRST_PULLBACK | 0 | 2024-07-05 20:00:00 | 4 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M10 | 14 | 2024-07-18 08:00:00 | ENTRY_T1 | ZONE_3_EARLY_CONTINUATION | 0 | 2024-07-18 08:00:00 | 13 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M11 | 50 | 2024-10-27 20:00:00 | ENTRY_T1 | ZONE_3_EARLY_CONTINUATION | 37 | 2024-10-27 20:00:00 | 49 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |
| M12 | 43 | 2024-12-03 16:00:00 | ENTRY_T1 | ZONE_3_EARLY_CONTINUATION | 14 | 2024-12-03 16:00:00 | 42 | diagnostic count only; no PnL or trade simulation computed in EXP-008 |

## Verdict

PARTIAL_ENTRY_STRUCTURE
