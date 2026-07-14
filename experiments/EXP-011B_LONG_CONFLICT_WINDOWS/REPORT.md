# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

Status: AWAITING_TW_FULL_SECTION_REVIEW

Verdict: AWAITING_TW_FULL_SECTION_REVIEW

## Data

Source OHLC: `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`

Exchange/source: Binance public spot klines inherited from EXP-011. Symbol: ADAUSDT. Manual TradingView review is expected on Bybit ADAUSDT Perpetual Contract 4H. Structure should be comparable, but individual candles and boundaries may differ by one or more bars.

Research period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`. Bars in period: `498`. Pine uses 4H `open_time` boundaries.

## R2 Full Section Revision

V1 started too late because the left boundary was the already-confirmed `CORE_CONFLICT_TRIGGER`. V1 also ended too early because a technical reset or EMA27/EMA200 cross was treated as a right boundary. R2 keeps those as internal events and expands each section to the full dispute process.

- Old LC count: `6`
- New LC count: `7`
- Sections expanded left: `6`
- Sections expanded right: `1`
- Sections merged: `0`
- Sections split: `1`
- RECOVERED_LONG: `6`
- NEW_DOWN_CONFIGURATION: `1`
- OPEN_AT_TRAIN_END: `0`
- Mean bars added left vs V1 overlaps: `2.14`
- Mean bars added right vs V1 overlaps: `0.29`
- Mean bars before first CORE_TRIGGER: `2.29`
- Mean bars after last CORE_TRIGGER: `6.14`

## R2 Sections

- `LC001`: A `2023-10-31 08:00:00`, D `2023-10-31 12:00:00`, T `2023-10-31 16:00:00` -> `2023-11-01 12:00:00`, R `2023-11-01 16:00:00`, E `2023-11-02 00:00:00`, `RECOVERED_LONG`
- `LC002`: A `2023-11-12 12:00:00`, D `2023-11-12 16:00:00`, T `2023-11-13 08:00:00` -> `2023-11-18 12:00:00`, R `2023-11-19 12:00:00`, E `2023-11-19 20:00:00`, `RECOVERED_LONG`
- `LC003`: A `2023-11-21 00:00:00`, D `2023-11-21 04:00:00`, T `2023-11-21 12:00:00` -> `2023-11-22 12:00:00`, R `2023-11-22 20:00:00`, E `2023-11-23 08:00:00`, `RECOVERED_LONG`
- `LC004`: A `2023-11-26 04:00:00`, D `2023-11-26 08:00:00`, T `2023-11-26 16:00:00` -> `2023-12-01 04:00:00`, R `2023-12-01 16:00:00`, E `2023-12-02 04:00:00`, `RECOVERED_LONG`
- `LC005`: A `2023-12-10 20:00:00`, D `2023-12-11 00:00:00`, T `2023-12-11 16:00:00` -> `2023-12-11 16:00:00`, R `2023-12-12 04:00:00`, E `2023-12-12 12:00:00`, `RECOVERED_LONG`
- `LC006`: A `2023-12-15 08:00:00`, D `2023-12-15 12:00:00`, T `2023-12-15 20:00:00` -> `2023-12-20 20:00:00`, R `2023-12-21 08:00:00`, E `2023-12-21 20:00:00`, `RECOVERED_LONG`
- `LC007`: A `2023-12-22 20:00:00`, D `2023-12-23 00:00:00`, T `2023-12-23 04:00:00` -> `2024-01-05 08:00:00`, R `2024-01-06 16:00:00`, E `2024-01-07 00:00:00`, `NEW_DOWN_CONFIGURATION`

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. EMA-cross does not close a section automatically. RECOVERED_LONG and NEW_DOWN_CONFIGURATION both require 3-of-4 confirmation. No SHORT model, future validation period, ZigZag, clustering, BACKBONE_C, Technical Ratings, previous high/low hard filter, PnL, backtest, trading action, or `docs/DEFINITIONS.md` change.
