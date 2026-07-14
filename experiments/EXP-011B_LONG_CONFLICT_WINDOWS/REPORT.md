# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

Status: AWAITING_TW_BOUNDARY_REVIEW

Verdict: AWAITING_TW_BOUNDARY_REVIEW

## Data

Source OHLC: `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`

Exchange/source: Binance public spot klines inherited from EXP-011. Symbol: ADAUSDT. Manual TradingView review is expected on Bybit ADAUSDT Perpetual Contract 4H, so one or more bars may differ between sources.

Research period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59 UTC`. Bars in period: `498`.

## Counts

- CORE_CONFLICT_TRIGGER: `124`
- Raw conflicts: `10`
- LONG CONFLICT sections: `6`
- FULL_RESET_CONFIRMED: `9`
- EMA_CROSS: `1`
- OPEN_AT_PERIOD_END: `0`

## Sections

- `LC001`: `2023-10-31 19:59:59.999000` -> `2023-11-02 03:59:59.999000`, raw events `1`, end `FULL_RESET_CONFIRMED`
- `LC002`: `2023-11-13 11:59:59.999000` -> `2023-11-19 23:59:59.999000`, raw events `2`, end `FULL_RESET_CONFIRMED`
- `LC003`: `2023-11-21 15:59:59.999000` -> `2023-11-24 07:59:59.999000`, raw events `1`, end `FULL_RESET_CONFIRMED`
- `LC004`: `2023-11-26 19:59:59.999000` -> `2023-12-02 11:59:59.999000`, raw events `1`, end `FULL_RESET_CONFIRMED`
- `LC005`: `2023-12-11 19:59:59.999000` -> `2023-12-12 15:59:59.999000`, raw events `1`, end `FULL_RESET_CONFIRMED`
- `LC006`: `2023-12-15 23:59:59.999000` -> `2024-01-06 19:59:59.999000`, raw events `4`, end `EMA_CROSS`

## Merge Parameters

- Max gap between raw conflicts: `6` 4H bars
- Gap must preserve `ema27 > ema200`
- At least `0.67` of gap bars must have `ema200_slope_6 >= 0`

## Constraints

SHORT context was not analyzed. Data after `2024-01-08 23:59:59 UTC` was not used. Pine does not draw EMA27 or EMA200. No continuation/reversal/transition classification is made.

No ZigZag, clustering, BACKBONE_C, previous high/low condition, Irobot, PnL, backtest, entry, exit, stop, risk, or future outcome was used. `docs/DEFINITIONS.md` was not changed.
