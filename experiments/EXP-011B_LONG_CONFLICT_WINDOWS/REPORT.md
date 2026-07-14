# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

Status: AWAITING_TW_STRUCTURAL_RESET_REVIEW

Verdict: AWAITING_TW_STRUCTURAL_RESET_REVIEW

## Data

Source OHLC: `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`

Exchange/source: Binance public spot klines inherited from EXP-011. Symbol: ADAUSDT. Manual TradingView review is expected on Bybit ADAUSDT Perpetual Contract 4H. Structure should be comparable, but individual candles and boundaries may differ by one or more bars.

Research period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`. Bars in period: `498`. Pine uses 4H `open_time` boundaries.

## R5 Structural Reset

R4 recovery scoring was rejected because its six components clustered around the same EMA27 recovery behavior and overclassified many EMA27 bounces as strong recoveries. R5 stops using a summed score to close sections. It first detects the same causal recovery attempt, then separates a true `STRUCTURAL_RESET` from `INTERNAL_RECOVERY`.

The frozen structural reset level is causal: `pre_dispute_reference_high` is the high from the last aligned run before `DISPUTE_START` or a 12-bar fallback, `dispute_ceiling_before_bar` is the high from `DISPUTE_START` through the bar before detection, and the reset level is their maximum. The current bar is excluded from the dispute ceiling and the level is frozen at candidate detection.

- R4 sections: `6`
- R5 sections: `3`
- Episodes: `10`
- Internal recoveries: `8`
- Failed internal recoveries: `7`
- Confirmed persistent internal recoveries: `1`
- Structural-reset candidates: `1`
- Failed structural resets: `0`
- Confirmed structural resets: `1`
- Confirmed new down configurations: `1`

## R4 To R5 Mapping

- R4 `LC001` -> R5 `LC001` (mapped by overlapping causal bar spans)
- R4 `LC002` -> R5 `LC002` (mapped by overlapping causal bar spans)
- R4 `LC003` -> R5 `LC002` (mapped by overlapping causal bar spans)
- R4 `LC004` -> R5 `LC003` (mapped by overlapping causal bar spans)
- R4 `LC005` -> R5 `LC003` (mapped by overlapping causal bar spans)
- R4 `LC006` -> R5 `LC003` (mapped by overlapping causal bar spans)

## Acceptance Tests

- `NOVEMBER_CHAIN_PRESERVED`: `PASS` — 1 matching section(s): LC002
- `DECEMBER_STRUCTURAL_RESET_SPLIT`: `FAIL` — 1 section(s): LC003
- `LATE_DECEMBER_CHAIN_PRESERVED`: `PASS` — 1 matching section(s): LC003
- `EXPECTED_FOUR_SECTIONS`: `FAIL` — 3 R5 sections
- `NO_DATE_HARDCODING`: `PASS` — general chronological builder
- `NO_SECTION_ID_HARDCODING`: `PASS` — general chronological builder
- `NO_FUTURE_PERIOD_USED`: `PASS` — period slice ends at configured END

## R5 Sections

- `LC001`: R4 `LC001`, R3 `LC001`, R2 `LC001`, D `2023-10-31 12:00:00`, E `2023-11-02 00:00:00`, C `2023-11-03 00:00:00`, `CONFIRMED_STRUCTURAL_RESET`, path `STRUCTURAL_RESET`, episodes `1`
- `LC002`: R4 `LC002;LC003`, R3 `LC002`, R2 `LC002;LC003;LC004`, D `2023-11-12 16:00:00`, E `2023-12-01 16:00:00`, C `2023-12-06 04:00:00`, `CONFIRMED_PERSISTENT_INTERNAL_RECOVERY`, path `INTERNAL_PERSISTENCE`, episodes `4`
- `LC003`: R4 `LC004;LC005;LC006`, R3 `LC003`, R2 `LC005;LC006;LC007`, D `2023-12-11 00:00:00`, E `2024-01-06 16:00:00`, C `2024-01-08 08:00:00`, `CONFIRMED_NEW_DOWN_CONFIGURATION`, path `NEW_DOWN_CONFIGURATION`, episodes `5`

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No date-specific exceptions, section-id exceptions, ZigZag, clustering, BACKBONE_C, Technical Ratings, forecast, PnL, backtest, trading action, or `docs/DEFINITIONS.md` change. EMA27 and EMA200 are not plotted in the R5 Pine; the Pine only displays fixed timestamps and price bounds from CSV.
