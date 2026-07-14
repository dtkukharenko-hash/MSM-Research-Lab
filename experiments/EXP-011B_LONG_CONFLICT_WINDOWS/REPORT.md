# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

Status: AWAITING_TW_EPISODE_CHAIN_REVIEW

Verdict: AWAITING_TW_EPISODE_CHAIN_REVIEW

## Data

Source OHLC: `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`

Exchange/source: Binance public spot klines inherited from EXP-011. Symbol: ADAUSDT. Manual TradingView review is expected on Bybit ADAUSDT Perpetual Contract 4H. Structure should be comparable, but individual candles and boundaries may differ by one or more bars.

Research period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`. Bars in period: `498`. Pine uses 4H `open_time` boundaries.

## R3 Dispute Episode Chains

R2 expanded the windows correctly to the left and right, but its `3 of 4 recovered_long_bar` criterion was too short to separate a true exit from an internal bounce. R3 keeps the same causal EMA and CORE_TRIGGER formulas, treats that condition as `RECOVERY_ATTEMPT`, and requires a fixed `24`-bar probation before the section can close.

- R2 sections: `7`
- R3 sections: `3`
- R3 episodes: `10`
- RECOVERY_ATTEMPT: `9`
- FAILED_RECOVERY: `7`
- CONFIRMED_RECOVERED_LONG: `2`
- NEW_CONFIGURATION_ATTEMPT: `1`
- NEW_CONFIGURATION_FAILED: `0`
- CONFIRMED_NEW_DOWN_CONFIGURATION: `1`
- OPEN_AT_TRAIN_END: `0`
- Mean section duration to effective exit, bars: `94.67`
- Mean episodes per section: `3.33`
- Mean bars from effective exit to confirmation: `21.00`

## R2 To R3 Merges

- `LC002;LC003;LC004` -> `LC002`
- `LC005;LC006;LC007` -> `LC003`

Acceptance test `LC002 + LC003 + LC004`: `PASS`.

LC006/LC007 check: `LC003: LC005;LC006;LC007`.

## R3 Sections

- `LC001`: source `LC001`, D `2023-10-31 12:00:00`, E `2023-11-01 16:00:00`, C `2023-11-06 00:00:00`, `CONFIRMED_RECOVERED_LONG`, episodes `1`
- `LC002`: source `LC002;LC003;LC004`, D `2023-11-12 16:00:00`, E `2023-12-01 16:00:00`, C `2023-12-06 04:00:00`, `CONFIRMED_RECOVERED_LONG`, episodes `4`
- `LC003`: source `LC005;LC006;LC007`, D `2023-12-11 00:00:00`, E `2024-01-06 16:00:00`, C `2024-01-08 08:00:00`, `CONFIRMED_NEW_DOWN_CONFIGURATION`, episodes `5`

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No date-specific exceptions, ZigZag, clustering, BACKBONE_C, Technical Ratings, forecast, PnL, backtest, trading action, or `docs/DEFINITIONS.md` change. EMA27 and EMA200 are not plotted in the R3 Pine; the Pine only displays fixed timestamps from CSV.
