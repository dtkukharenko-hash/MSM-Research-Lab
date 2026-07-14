# EXP-012 R2 - ACCEPTED BOUNDARY STATE

Status: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

Verdict: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

## Motivation

R1 correctly changed the object from EMA conflict windows to horizontal disputed price zones, but it had two defects. A failed attempt could expand a boundary using highs/lows from bars after the causal failure bar, and single wick extremes influenced boundaries too strongly. R2 fixes both defects by processing outside states bar by bar and by separating wick references from accepted body boundaries. The mandatory addendum adds a separate EMA27 compact-band departure layer to describe whether EMA27 leaves its own narrow band upward away from EMA200 or downward toward EMA200.

## Data

Source: `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`. Binance spot ADAUSDT 4H is used for automatic detection. Manual review is expected on Bybit ADAUSDT Perpetual 4H, so individual candles and boundaries may differ.

Development period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`.

## Causal Fix

Initial boundaries are medians of body highs/lows from causal source intervals. Wick extremes are stored as diagnostics only. Outside candidates freeze the active boundary and ATR at candidate start, then update only from candidate bar through the current closed bar. Accepted exits can confirm from bar 4 through bar 12. Rejected attempts stop immediately at their decision bar. A rejected attempt expands a boundary only if it qualifies as an accepted extension using repeated outside closes and outside body levels.

EMA27 band diagnostics use a trailing 12-bar prior window that excludes the current bar. A departure freezes that prior band at candidate time and confirms only after two consecutive closed bars remain beyond the frozen edge. This layer annotates price exits and failed departures; it never changes price bounds and never closes a zone.

## Primary R2 Zones

- `Z001`: R5 `LC001`, Z `2023-10-31 12:00:00`, B `2023-10-31 20:00:00`, body bounds `0.289500`-`0.303100` -> `0.287500`-`0.303100`, E `2023-11-02 04:00:00`, C `2023-11-02 16:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`
- `Z002`: R5 `LC002`, Z `2023-11-12 16:00:00`, B `2023-11-14 04:00:00`, body bounds `0.356800`-`0.390500` -> `0.356800`-`0.390500`, E `2023-11-24 00:00:00`, C `2023-11-24 12:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`
- `Z003`: R5 `LC002`, Z `2023-11-26 08:00:00`, B `2023-11-28 12:00:00`, body bounds `0.373900`-`0.394900` -> `0.373900`-`0.397600`, E `2023-12-04 00:00:00`, C `2023-12-04 16:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`
- `Z004`: R5 `LC003`, Z `2023-12-11 00:00:00`, B `2023-12-12 00:00:00`, body bounds `0.532800`-`0.624300` -> `0.532800`-`0.624300`, E `2023-12-13 16:00:00`, C `2023-12-14 04:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`
- `Z005`: R5 `LC003`, Z `2023-12-15 12:00:00`, B `2023-12-16 12:00:00`, body bounds `0.600400`-`0.667500` -> `0.600400`-`0.667500`, E `2023-12-17 04:00:00`, C `2023-12-17 16:00:00`, `ACCEPTED_DOWNSIDE_EXIT_R2`
- `Z006`: R5 `LC003`, Z `2023-12-18 04:00:00`, B `2023-12-18 16:00:00`, body bounds `0.559900`-`0.622000` -> `0.559900`-`0.661500`, E `2024-01-03 16:00:00`, C `2024-01-04 04:00:00`, `ACCEPTED_DOWNSIDE_EXIT_R2`

## Outside-State Candidates

- `XA001` `Z001` DOWN: candidate `2023-11-01 04:00:00`, decision `2023-11-02 00:00:00`, `ACCEPTED_EXTENSION`, outside fraction `0.50`, last data `2023-11-02 00:00:00`
- `XA002` `Z001` UP: candidate `2023-11-02 04:00:00`, decision `2023-11-02 16:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`, outside fraction `0.75`, last data `2023-11-02 16:00:00`
- `XA003` `Z002` DOWN: candidate `2023-11-14 16:00:00`, decision `2023-11-15 12:00:00`, `REJECTED_WICK_OR_SINGLE_EXCURSION`, outside fraction `0.33`, last data `2023-11-15 12:00:00`
- `XA004` `Z002` UP: candidate `2023-11-16 04:00:00`, decision `2023-11-16 20:00:00`, `REJECTED_WICK_OR_SINGLE_EXCURSION`, outside fraction `0.40`, last data `2023-11-16 20:00:00`
- `XA005` `Z002` UP: candidate `2023-11-20 08:00:00`, decision `2023-11-21 00:00:00`, `REJECTED_WICK_OR_SINGLE_EXCURSION`, outside fraction `0.40`, last data `2023-11-21 00:00:00`
- `XA006` `Z002` UP: candidate `2023-11-24 00:00:00`, decision `2023-11-24 12:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`, outside fraction `0.75`, last data `2023-11-24 12:00:00`
- `XA007` `Z003` UP: candidate `2023-12-02 20:00:00`, decision `2023-12-03 16:00:00`, `ACCEPTED_EXTENSION`, outside fraction `0.50`, last data `2023-12-03 16:00:00`
- `XA008` `Z003` UP: candidate `2023-12-04 00:00:00`, decision `2023-12-04 16:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`, outside fraction `0.80`, last data `2023-12-04 16:00:00`
- `XA009` `Z004` UP: candidate `2023-12-13 16:00:00`, decision `2023-12-14 04:00:00`, `ACCEPTED_UPSIDE_EXIT_R2`, outside fraction `1.00`, last data `2023-12-14 04:00:00`
- `XA010` `Z005` DOWN: candidate `2023-12-17 04:00:00`, decision `2023-12-17 16:00:00`, `ACCEPTED_DOWNSIDE_EXIT_R2`, outside fraction `0.75`, last data `2023-12-17 16:00:00`
- `XA011` `Z006` UP: candidate `2023-12-21 20:00:00`, decision `2023-12-23 08:00:00`, `ACCEPTED_EXTENSION`, outside fraction `0.30`, last data `2023-12-23 08:00:00`
- `XA012` `Z006` UP: candidate `2023-12-28 00:00:00`, decision `2023-12-28 20:00:00`, `ACCEPTED_EXTENSION`, outside fraction `0.50`, last data `2023-12-28 20:00:00`
- `XA013` `Z006` DOWN: candidate `2024-01-03 16:00:00`, decision `2024-01-04 04:00:00`, `ACCEPTED_DOWNSIDE_EXIT_R2`, outside fraction `0.75`, last data `2024-01-04 04:00:00`

## Accepted Extensions

- `XA001` `Z001` DOWN: old `0.289500`-`0.303100`, proposed body `0.287500`, new `0.287500`-`0.303100`, wick ignored `0.283900`
- `XA007` `Z003` UP: old `0.373900`-`0.394900`, proposed body `0.397600`, new `0.373900`-`0.397600`, wick ignored `0.403000`
- `XA011` `Z006` UP: old `0.559900`-`0.622000`, proposed body `0.635100`, new `0.559900`-`0.635100`, wick ignored `0.651300`
- `XA012` `Z006` UP: old `0.559900`-`0.635100`, proposed body `0.661500`, new `0.559900`-`0.661500`, wick ignored `0.676900`

## EMA27 Compact-Band Departures

- `ED001` `Z001` UP: candidate `2023-11-02 00:00:00`, confirmation `2023-11-02 04:00:00`, `EMA27_EXIT_UP_AWAY_FROM_EMA200`, related price attempts `XA001;XA002`
- `ED002` `Z001` UP: candidate `2023-11-02 08:00:00`, confirmation `2023-11-02 12:00:00`, `EMA27_EXIT_UP_AWAY_FROM_EMA200`, related price attempts `XA002`
- `ED003` `Z002` DOWN: candidate `2023-11-14 16:00:00`, confirmation `2023-11-14 20:00:00`, `EMA27_EXIT_DOWN_TOWARD_EMA200`, related price attempts `XA003`
- `ED004` `Z002` UP: candidate `2023-11-16 08:00:00`, confirmation `2023-11-16 12:00:00`, `EMA27_EXIT_UP_AWAY_FROM_EMA200`, related price attempts `XA004`
- `ED005` `Z002` UP: candidate `2023-11-24 00:00:00`, confirmation `2023-11-24 04:00:00`, `EMA27_EXIT_UP_AWAY_FROM_EMA200`, related price attempts `XA006`
- `ED006` `Z003` UP: candidate `2023-12-02 16:00:00`, confirmation `2023-12-02 20:00:00`, `EMA27_EXIT_UP_AWAY_FROM_EMA200`, related price attempts `XA007`
- `ED007` `Z006` DOWN: candidate `2023-12-18 04:00:00`, confirmation `2023-12-18 08:00:00`, `EMA27_EXIT_DOWN_TOWARD_EMA200`, related price attempts ``
- `ED008` `Z006` UP: candidate `2023-12-21 20:00:00`, confirmation `2023-12-22 00:00:00`, `EMA27_EXIT_UP_AWAY_FROM_EMA200`, related price attempts `XA011`
- `ED009` `Z006` UP: candidate `2023-12-28 00:00:00`, confirmation `2023-12-28 04:00:00`, `EMA27_EXIT_UP_AWAY_FROM_EMA200`, related price attempts `XA012`
- `ED010` `Z006` DOWN: candidate `2024-01-03 16:00:00`, confirmation `2024-01-03 20:00:00`, `EMA27_EXIT_DOWN_TOWARD_EMA200`, related price attempts `XA013`

## Price And EMA Geometry Alignment

- `XA001` `Z001` price `ACCEPTED_EXTENSION`: EMA relation `NO_EMA27_BAND_EXIT`, classification ``
- `XA002` `Z001` price `ACCEPTED_UPSIDE_EXIT_R2`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_UP_AWAY_FROM_EMA200`
- `XA003` `Z002` price `REJECTED_WICK_OR_SINGLE_EXCURSION`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_DOWN_TOWARD_EMA200`
- `XA004` `Z002` price `REJECTED_WICK_OR_SINGLE_EXCURSION`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_UP_AWAY_FROM_EMA200`
- `XA005` `Z002` price `REJECTED_WICK_OR_SINGLE_EXCURSION`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_UP_AWAY_FROM_EMA200`
- `XA006` `Z002` price `ACCEPTED_UPSIDE_EXIT_R2`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_UP_AWAY_FROM_EMA200`
- `XA007` `Z003` price `ACCEPTED_EXTENSION`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_UP_AWAY_FROM_EMA200`
- `XA008` `Z003` price `ACCEPTED_UPSIDE_EXIT_R2`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_UP_AWAY_FROM_EMA200`
- `XA009` `Z004` price `ACCEPTED_UPSIDE_EXIT_R2`: EMA relation `NO_EMA27_BAND_EXIT`, classification ``
- `XA010` `Z005` price `ACCEPTED_DOWNSIDE_EXIT_R2`: EMA relation `NO_EMA27_BAND_EXIT`, classification ``
- `XA011` `Z006` price `ACCEPTED_EXTENSION`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_UP_AWAY_FROM_EMA200`
- `XA012` `Z006` price `ACCEPTED_EXTENSION`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_UP_AWAY_FROM_EMA200`
- `XA013` `Z006` price `ACCEPTED_DOWNSIDE_EXIT_R2`: EMA relation `SAME_DIRECTION_EMA27_EXIT`, classification `EMA27_EXIT_DOWN_TOWARD_EMA200`

## Price-Only Versus Price-Plus-EMA Geometry

                  layer  zone_count  accepted_exit_count  accepted_upside_exit_count  accepted_downside_exit_count accepted_exits_with_same_direction_ema27_departure accepted_exits_without_same_direction_ema27_departure                                                              description
  PRICE_ONLY_ACCEPTANCE           6                    6                           4                             2                                                                                                                                          primary R2 price-zone state machine only
PRICE_PLUS_EMA_GEOMETRY           6                    6                           4                             2                                                  4                                                     2 same price exits annotated by most recent confirmed EMA27 band departure

## Primary Versus Fixed-Bound Baseline

                         model  zone_count  accepted_upside_exit_count  accepted_downside_exit_count  open_at_train_end_count  outside_candidate_count  accepted_extension_count  rejected_wick_or_single_excursion_count
ACCEPTED_EXTENSION_BODY_BOUNDS           6                           4                             2                        0                       13                         4                                        3
    FIXED_BODY_BOUNDS_BASELINE           7                           5                             2                        0                       14                         0                                        3

## R1/R2 Mapping

r1_zone_id r2_zone_id   r1_resolution_kind        r2_resolution_kind             mapping_reason
      Z001       Z001 ACCEPTED_UPSIDE_EXIT   ACCEPTED_UPSIDE_EXIT_R2 overlap by causal bar span
      Z002       Z002 ACCEPTED_UPSIDE_EXIT   ACCEPTED_UPSIDE_EXIT_R2 overlap by causal bar span
      Z002       Z003 ACCEPTED_UPSIDE_EXIT   ACCEPTED_UPSIDE_EXIT_R2 overlap by causal bar span
      Z003       Z004    OPEN_AT_TRAIN_END   ACCEPTED_UPSIDE_EXIT_R2 overlap by causal bar span
      Z003       Z005    OPEN_AT_TRAIN_END ACCEPTED_DOWNSIDE_EXIT_R2 overlap by causal bar span
      Z003       Z006    OPEN_AT_TRAIN_END ACCEPTED_DOWNSIDE_EXIT_R2 overlap by causal bar span

## Acceptance Tests

- `EXPECTED_THREE_PRIMARY_ZONES`: `FAIL` - 6 zones
- `FIRST_ZONE_COMPACT`: `PASS` - 1 matching zone(s)
- `NOVEMBER_SINGLE_ZONE`: `FAIL` - 2 matching zone(s)
- `DECEMBER_JANUARY_SINGLE_ZONE`: `FAIL` - 3 matching zone(s)
- `DECEMBER_DOWNSIDE_EXIT_ACCEPTED`: `PASS` - True
- `DOWNSIDE_EXIT_EARLIER_THAN_R1`: `PASS` - R2 2023-12-13 16:00:00 vs R1 2024-01-08 20:00:00
- `NO_POST_FAILURE_DATA_USED`: `PASS` - True
- `NO_WICK_ONLY_BOUNDARY_EXPANSION`: `PASS` - True
- `NO_DATE_HARDCODING`: `PASS` - general chronological builder
- `NO_PRICE_HARDCODING`: `PASS` - body median estimators and accepted extensions
- `NO_ZONE_ID_HARDCODING`: `PASS` - section IDs used only in diagnostics
- `NO_FUTURE_PERIOD_USED`: `PASS` - period slice ends at 2024-01-08 23:59:59.999000
- `NOVEMBER_EMA27_EXIT_UP_AWAY`: `PASS` - True
- `DECEMBER_EMA27_EXIT_DOWN_TOWARD_EMA200`: `PASS` - True
- `EMA_GEOMETRY_NEVER_DEFINES_PRICE_BOUNDARY`: `PASS` - True
- `EMA_DEPARTURE_CAUSAL_NO_CURRENT_BAR_IN_PRIOR_BAND`: `PASS` - True
- `NO_EMA_ONLY_ZONE_CLOSE`: `PASS` - True

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, forecast, trading logic, date hardcoding, price hardcoding, or zone-id hardcoding. `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B artifacts were not modified.
