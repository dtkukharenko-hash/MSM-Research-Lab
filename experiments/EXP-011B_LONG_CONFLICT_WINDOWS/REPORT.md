# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

Status: AWAITING_TW_ADAPTIVE_RECOVERY_REVIEW

Verdict: AWAITING_TW_ADAPTIVE_RECOVERY_REVIEW

## Data

Source OHLC: `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`

Exchange/source: Binance public spot klines inherited from EXP-011. Symbol: ADAUSDT. Manual TradingView review is expected on Bybit ADAUSDT Perpetual Contract 4H. Structure should be comparable, but individual candles and boundaries may differ by one or more bars.

Research period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`. Bars in period: `498`. Pine uses 4H `open_time` boundaries.

## R4 Adaptive Recovery Strength

R3 used one fixed 24-bar probation for every recovery attempt. That was too blunt: weak internal bounces can still need long confirmation, while a strong recovery can justify closing the dispute section earlier and allowing the next dispute start to become a new section.

R4 keeps the R2/R3 EMA, DISPUTE_START and CORE_TRIGGER logic, and adds ATR14 using Wilder-style RMA (`ewm alpha = 1/14`). Recovery strength has six causal components: price separation from EMA27, EMA27 acceleration, EMA-gap expansion, alignment persistence, structural clearance above the prior conflict ceiling, and price persistence above EMA27.

- R3 sections: `3`
- R4 sections: `6`
- Episodes: `12`
- WEAK_RECOVERY: `0`
- MODERATE_RECOVERY: `1`
- STRONG_RECOVERY: `10`
- Failed moderate recovery: `1`
- Failed strong recovery: `5`
- Confirmed moderate recovery: `0`
- Confirmed strong recovery: `5`
- Confirmed new down configuration: `1`

## R3 To R4 Mapping

Split R3 sections:

- `LC002` -> `LC002;LC003` (`adaptive recovery confirmed split`)
- `LC003` -> `LC004;LC005;LC006` (`adaptive recovery confirmed split`)

Kept R3 sections:

- `LC001` -> `LC001`

## Acceptance Tests

- `NOVEMBER_CHAIN_PRESERVED`: `FAIL` — 2 R4 sections
- `DECEMBER_STRONG_RECOVERY_SPLIT`: `PASS` — 3 R4 sections
- `EXPECTED_FOUR_SECTIONS`: `FAIL` — 6 R4 sections
- `NO_DATE_HARDCODING`: `PASS` — general chronological builder
- `NO_FUTURE_PERIOD_USED`: `PASS` — period slice ends at configured END

## R4 Sections

- `LC001`: source R3 `LC001`, source R2 `LC001`, D `2023-10-31 12:00:00`, E `2023-11-01 16:00:00`, C `2023-11-03 00:00:00`, `CONFIRMED_STRONG_RECOVERY`, recovery `STRONG_RECOVERY`, score `5`, episodes `1`
- `LC002`: source R3 `LC002`, source R2 `LC002`, D `2023-11-12 16:00:00`, E `2023-11-19 12:00:00`, C `2023-11-20 20:00:00`, `CONFIRMED_STRONG_RECOVERY`, recovery `STRONG_RECOVERY`, score `5`, episodes `2`
- `LC003`: source R3 `LC002`, source R2 `LC003;LC004`, D `2023-11-21 04:00:00`, E `2023-12-01 16:00:00`, C `2023-12-03 04:00:00`, `CONFIRMED_STRONG_RECOVERY`, recovery `STRONG_RECOVERY`, score `5`, episodes `3`
- `LC004`: source R3 `LC003`, source R2 `LC005`, D `2023-12-11 00:00:00`, E `2023-12-13 12:00:00`, C `2023-12-15 00:00:00`, `CONFIRMED_STRONG_RECOVERY`, recovery `STRONG_RECOVERY`, score `5`, episodes `2`
- `LC005`: source R3 `LC003`, source R2 `LC006`, D `2023-12-15 12:00:00`, E `2023-12-21 08:00:00`, C `2023-12-22 20:00:00`, `CONFIRMED_STRONG_RECOVERY`, recovery `STRONG_RECOVERY`, score `5`, episodes `1`
- `LC006`: source R3 `LC003`, source R2 `LC007`, D `2023-12-23 00:00:00`, E `2024-01-06 16:00:00`, C `2024-01-08 08:00:00`, `CONFIRMED_NEW_DOWN_CONFIGURATION`, recovery ``, score ``, episodes `3`

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No date-specific exceptions, section-id exceptions, ZigZag, clustering, BACKBONE_C, Technical Ratings, forecast, PnL, backtest, trading action, or `docs/DEFINITIONS.md` change. EMA27 and EMA200 are not plotted in the R4 Pine; the Pine only displays fixed timestamps and price bounds from CSV.
