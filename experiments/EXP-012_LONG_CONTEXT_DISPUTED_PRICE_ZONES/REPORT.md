# EXP-012 R3 - HIERARCHICAL PARENT ZONES

Status: AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW

Verdict: AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW

## Motivation

R2 fixed causality and wick-boundary defects but segmented every local accepted departure as a full zone. R3 tests a hierarchy: broad `PARENT_DISPUTED_ZONE`, local `INTERNAL_PHASE`, fresh parent EMA geometry, and joint persistence for final parent resolution.

## Method

R3 preserves R2 body-based boundaries, wick diagnostics, sequential local price attempts, and no post-decision reads. Local price departures become internal phases first. A parent resolution candidate requires a fresh same-direction, directionally qualified 24-bar parent EMA departure. Parent confirmation then requires 12 bars of joint price/EMA persistence.

## Parents

- `P001`: start `2023-10-31 12:00:00`, bounds `0.287500`-`0.303100`, phases `2`, resolution `OPEN_AT_TRAIN_END`, E `2023-11-02 16:00:00`, C `2023-11-02 16:00:00`, EMA `` ``
- `P002`: start `2023-11-12 16:00:00`, bounds `0.356800`-`0.397600`, phases `6`, resolution `OPEN_AT_TRAIN_END`, E `2023-12-04 16:00:00`, C `2023-12-04 16:00:00`, EMA `` ``
- `P003`: start `2023-12-11 00:00:00`, bounds `0.532800`-`0.661500`, phases `5`, resolution `OPEN_AT_TRAIN_END`, E `2024-01-04 04:00:00`, C `2024-01-04 04:00:00`, EMA `` ``

## Internal Phases

- `PH001` `P001` INTERNAL_ACCEPTED_DOWN_EXTENSION: `2023-11-01 04:00:00` -> `2023-11-02 00:00:00`, attempt `XA001`, EMA `STALE`, joint ``
- `PH002` `P001` INTERNAL_UP_DEPARTURE: `2023-11-02 04:00:00` -> `2023-11-02 16:00:00`, attempt `XA002`, EMA `STALE`, joint ``
- `PH003` `P002` INTERNAL_REJECTED_DOWN_EXCURSION: `2023-11-14 16:00:00` -> `2023-11-15 12:00:00`, attempt `XA003`, EMA `STALE`, joint ``
- `PH004` `P002` INTERNAL_REJECTED_UP_EXCURSION: `2023-11-16 04:00:00` -> `2023-11-16 20:00:00`, attempt `XA004`, EMA `STALE`, joint ``
- `PH005` `P002` INTERNAL_REJECTED_UP_EXCURSION: `2023-11-20 08:00:00` -> `2023-11-21 00:00:00`, attempt `XA005`, EMA `FRESH_SAME_DIRECTION`, joint ``
- `PH006` `P002` INTERNAL_UP_DEPARTURE: `2023-11-24 00:00:00` -> `2023-11-24 12:00:00`, attempt `XA006`, EMA `STALE`, joint ``
- `PH007` `P002` INTERNAL_ACCEPTED_UP_EXTENSION: `2023-12-02 20:00:00` -> `2023-12-03 16:00:00`, attempt `XA007`, EMA `FRESH_SAME_DIRECTION`, joint ``
- `PH008` `P002` INTERNAL_UP_DEPARTURE: `2023-12-04 00:00:00` -> `2023-12-04 16:00:00`, attempt `XA008`, EMA `STALE`, joint ``
- `PH009` `P003` INTERNAL_UP_DEPARTURE: `2023-12-13 16:00:00` -> `2023-12-14 04:00:00`, attempt `XA009`, EMA `STALE`, joint ``
- `PH010` `P003` INTERNAL_DOWN_DEPARTURE: `2023-12-17 04:00:00` -> `2023-12-17 16:00:00`, attempt `XA010`, EMA `STALE`, joint ``
- `PH011` `P003` INTERNAL_ACCEPTED_UP_EXTENSION: `2023-12-21 20:00:00` -> `2023-12-23 08:00:00`, attempt `XA011`, EMA `STALE`, joint ``
- `PH012` `P003` INTERNAL_ACCEPTED_UP_EXTENSION: `2023-12-28 00:00:00` -> `2023-12-28 20:00:00`, attempt `XA012`, EMA `FRESH_SAME_DIRECTION`, joint ``
- `PH013` `P003` INTERNAL_FAILED_JOINT_DOWN_RESOLUTION: `2024-01-03 16:00:00` -> `2024-01-04 04:00:00`, attempt `XA013`, EMA `FRESH_SAME_DIRECTION`, joint `FAILED`

## Joint Candidates

- `JC001` `P003` DOWN: local `2024-01-04 04:00:00`, decision `2024-01-04 16:00:00`, `FAILED` PRICE_DEEP_RECLAIM

## Parent EMA Events

- `PE001` DOWN: `2023-10-19 00:00:00` -> `2023-10-19 04:00:00`, `PARENT_EMA_DOWN_TOWARD_EMA200`
- `PE002` UP: `2023-11-20 08:00:00` -> `2023-11-20 12:00:00`, `PARENT_EMA_UP_AWAY_FROM_EMA200`
- `PE003` UP: `2023-12-02 20:00:00` -> `2023-12-03 00:00:00`, `PARENT_EMA_UP_AWAY_FROM_EMA200`
- `PE004` UP: `2023-12-28 00:00:00` -> `2023-12-28 04:00:00`, `PARENT_EMA_UP_AWAY_FROM_EMA200`
- `PE005` DOWN: `2024-01-03 16:00:00` -> `2024-01-03 20:00:00`, `PARENT_EMA_DOWN_TOWARD_EMA200`

## Model Comparison

                                model  parent_zone_count  confirmed_parent_up_count  confirmed_parent_down_count  open_at_train_end_count
R3_HIERARCHICAL_PRICE_PLUS_PARENT_EMA                  3                          0                            0                        3
  PRICE_ONLY_IMMEDIATE_CLOSE_BASELINE                  6                          4                            2                        0
   PRICE_PLUS_INTERNAL_EMA12_BASELINE                  6                          4                            2                        0

## Acceptance Tests

- `EXPECTED_THREE_PARENT_ZONES`: `PASS` - 3 parents
- `FIRST_PARENT_COMPACT`: `PASS` - 1 matching
- `NOVEMBER_SINGLE_PARENT`: `PASS` - 1 matching
- `NOVEMBER_HAS_MULTIPLE_INTERNAL_PHASES`: `PASS` - 6
- `DECEMBER_JANUARY_SINGLE_PARENT`: `PASS` - 1 matching
- `DECEMBER_HAS_MULTIPLE_INTERNAL_PHASES`: `PASS` - 5
- `NOVEMBER_PARENT_UP_WITH_FRESH_EMA_UP_AWAY`: `FAIL` - False
- `DECEMBER_PARENT_DOWN_WITH_FRESH_EMA_DOWN_TOWARD`: `FAIL` - False
- `MID_DECEMBER_UP_REMAINS_INTERNAL`: `PASS` - True
- `MID_DECEMBER_EARLY_DOWN_REMAINS_INTERNAL`: `PASS` - True
- `FINAL_DOWNSIDE_COMPARISON_FILTERS_DIRECTION`: `FAIL` - False
- `NO_PARENT_CLOSE_FROM_PRICE_ONLY`: `PASS` - True
- `NO_PARENT_CLOSE_FROM_EMA_ONLY`: `PASS` - True
- `NO_STALE_EMA_ASSOCIATION`: `PASS` - True
- `NO_DUPLICATE_PARENT_EMA_BEFORE_REARM`: `PASS` - True
- `NO_POST_DECISION_DATA_USED`: `PASS` - True
- `NO_WICK_ONLY_PARENT_BOUNDARY_UPDATE`: `PASS` - True
- `NO_DATE_HARDCODING`: `PASS` - chronological detector
- `NO_PRICE_HARDCODING`: `PASS` - OHLC-derived bounds
- `NO_PARENT_OR_PHASE_ID_HARDCODING`: `PASS` - generated IDs
- `NO_FUTURE_PERIOD_USED`: `PASS` - 2024-01-08 23:59:59.999000

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, forecast, entries, exits, stops, position sizing, trading logic, date hardcoding, price hardcoding, or parent/phase-id hardcoding. R1/R2 outputs were preserved. `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B artifacts were not modified.
