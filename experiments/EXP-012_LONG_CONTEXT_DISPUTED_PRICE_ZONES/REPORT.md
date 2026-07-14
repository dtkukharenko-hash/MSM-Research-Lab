# EXP-012 R4 - CAUSAL PARENT STATE MACHINE

Status: AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW

Verdict: AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW

R4 replaces the R3 post-hoc grouping with a chronological raw-bar state machine. R2/R3/R5 artifacts are loaded only after R4 outputs are frozen, for temporal-overlap mapping and diagnostics.

## Model Comparison

                                       model  parent_count  confirmed_up_count  confirmed_down_count  open_at_train_end_count  joint_candidate_count  failed_joint_count
             R4_PRICE_PLUS_ACTIVE_PARENT_EMA             3                   2                     1                        0                      5                   2
      PRICE_ONLY_IMMEDIATE_CLOSE_BASELINE_R4             7                   4                     3                        0                      0                   0
PRICE_PLUS_ACTIVE_INTERNAL_EMA12_BASELINE_R4             3                   2                     1                        0                      5                   2

## Primary Parents
- `P001`: start `2023-10-31 12:00:00`, bounds `0.287500`-`0.303100`, phases `2`, resolution `CONFIRMED_PARENT_UP_RESOLUTION`, confirmation `2023-11-04 16:00:00`
- `P002`: start `2023-11-12 16:00:00`, bounds `0.356800`-`0.397600`, phases `6`, resolution `CONFIRMED_PARENT_UP_RESOLUTION`, confirmation `2023-12-06 16:00:00`
- `P003`: start `2023-12-11 00:00:00`, bounds `0.532800`-`0.667500`, phases `2`, resolution `CONFIRMED_PARENT_DOWN_RESOLUTION`, confirmation `2024-01-08 08:00:00`

## Joint Candidates
- `JC001` `P001` UP: overlap `2023-11-02 20:00:00`, decision `2023-11-04 16:00:00`, `CONFIRMED`
- `JC002` `P002` UP: overlap `2023-11-24 16:00:00`, decision `2023-11-26 12:00:00`, `FAILED` JOINT_12_BAR_CRITERIA_NOT_MET
- `JC003` `P002` UP: overlap `2023-11-26 16:00:00`, decision `2023-11-27 00:00:00`, `FAILED` PRICE_DEEP_RECLAIM
- `JC004` `P002` UP: overlap `2023-12-04 20:00:00`, decision `2023-12-06 16:00:00`, `CONFIRMED`
- `JC005` `P003` DOWN: overlap `2024-01-06 12:00:00`, decision `2024-01-08 08:00:00`, `CONFIRMED`

## January Continuation Audit
- First failed joint: `JC002` at `2023-11-26 12:00:00`, reason `JOINT_12_BAR_CRITERIA_NOT_MET`.
- Later local candidates after failure: `4`.
- Later joint candidates after failure: `3`.

## Acceptance Tests
- `DETECTION_USES_RAW_OHLC_NOT_R2_R3_LABELS`: `PASS` -
- `NO_SOURCE_R5_GROUPING_IN_DETECTOR`: `PASS` -
- `EXPECTED_THREE_PRIMARY_PARENTS`: `PASS` - 3
- `FIRST_PARENT_COMPACT`: `PASS` - P001
- `NOVEMBER_SINGLE_PARENT`: `PASS` - P002
- `NOVEMBER_MULTIPLE_INTERNAL_PHASES`: `PASS` -
- `DECEMBER_JANUARY_SINGLE_PARENT`: `PASS` - P003
- `DECEMBER_MULTIPLE_INTERNAL_PHASES`: `PASS` -
- `MID_DECEMBER_UP_REMAINS_INTERNAL`: `PASS` -
- `MID_DECEMBER_EARLY_DOWN_REMAINS_INTERNAL`: `PASS` -
- `FAILED_JOINT_PARENT_REMAINS_ACTIVE`: `PASS` -
- `FAILED_JOINT_CONTINUES_FROM_NEXT_BAR`: `PASS` -
- `LATER_LOCAL_CANDIDATE_AFTER_FAILED_JOINT`: `PASS` -
- `LATER_JOINT_CANDIDATE_ALLOWED_AFTER_FAILED_JOINT`: `PASS` -
- `PRIMARY_FIRST_PARENT_UP_RESOLUTION`: `PASS` -
- `PRIMARY_NOVEMBER_UP_RESOLUTION`: `PASS` -
- `PRIMARY_DECEMBER_DOWN_RESOLUTION`: `PASS` -
- `DOWNSIDE_COMPARISON_FILTERS_DOWN_DIRECTION`: `PASS` -
- `OPEN_PARENT_COVERS_ACTUAL_TRAIN_END`: `PASS` - open_parent_count=0
- `ACTIVE_REGIME_OVERLAP_NOT_ARBITRARY_EVENT_AGE`: `PASS` -
- `NO_DUPLICATE_EMA_EVENT_BEFORE_REARM`: `PASS` -
- `NEW_BAND_WINDOW_STRICTLY_AFTER_PREVIOUS_CONFIRMATION`: `PASS` -
- `NO_POST_DECISION_DATA_USED`: `PASS` -
- `NO_WICK_ONLY_PARENT_BOUNDARY_UPDATE`: `PASS` -
- `PRICE_ONLY_BASELINE_EXECUTED_INDEPENDENTLY`: `PASS` -
- `INTERNAL_EMA12_BASELINE_EXECUTED_WITH_EMA_AND_PROBATION`: `PASS` -
- `NO_DATE_HARDCODING`: `PASS` -
- `NO_PRICE_HARDCODING`: `PASS` -
- `NO_PARENT_PHASE_OR_LEGACY_ID_HARDCODING`: `PASS` -
- `NO_FUTURE_PERIOD_USED`: `PASS` - 2024-01-08 20:00:00

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, forecast, entries, stops, position sizing, or trading logic. `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B were not modified.

Automatic OHLC outputs use Binance spot; manual review remains Bybit ADAUSDT Perpetual 4H, so candle and boundary differences may exist.
