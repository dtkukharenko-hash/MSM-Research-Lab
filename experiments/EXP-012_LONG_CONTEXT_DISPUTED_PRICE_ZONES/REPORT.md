# EXP-012 — LONG CONTEXT DISPUTED PRICE ZONES

Status: AWAITING_TW_PRICE_ZONE_REVIEW

Verdict: AWAITING_TW_PRICE_ZONE_REVIEW

## Motivation

EXP-011B EMA/recovery state machines were paused because EMA-centered conflict boundaries were visually unstable. R4 overclassified EMA27 recoveries as strong, and R5 preserved some chains but still could not describe the horizontal disputed price area directly.

EXP-012 studies a different object: a causal horizontal disputed price zone inside LONG context. EMA27 and EMA200 are context and diagnostics; price defines the zone bounds and accepted exit.

## Data

Source: `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`. Binance spot ADAUSDT 4H is used for automatic detection. Manual review is expected on Bybit ADAUSDT Perpetual 4H, so individual candles and boundaries may differ.

Development period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`.

## Method

The detector uses local EXP-012 LONG context, aligned-run, dispute-start and diagnostic core-trigger logic. Initial upper seed is the high of the last aligned run, or a 12-bar fallback. The lower seed is confirmed causally by an adverse move and rebound, or by a bounded fallback. Bounds then remain frozen until a failed outside-close attempt expands one side. A zone closes only after a six-bar accepted outside move.

## Zones

- `Z001`: R5 `LC001`, Z `2023-10-31 12:00:00`, B `2023-10-31 20:00:00`, bounds `0.284500`–`0.304600`, E `2023-11-01 20:00:00`, C `2023-11-02 16:00:00`, `ACCEPTED_UPSIDE_EXIT`
- `Z002`: R5 `LC002`, Z `2023-11-12 16:00:00`, B `2023-11-14 04:00:00`, bounds `0.350000`–`0.415000`, E `2023-12-05 16:00:00`, C `2023-12-06 12:00:00`, `ACCEPTED_UPSIDE_EXIT`
- `Z003`: R5 `LC003`, Z `2023-12-11 00:00:00`, B `2023-12-12 00:00:00`, bounds `0.464300`–`0.680000`, E `2024-01-08 20:00:00`, C `2024-01-08 20:00:00`, `OPEN_AT_TRAIN_END`

## Exit Attempts

- `XA001` `Z001` UP: candidate `2023-11-01 20:00:00`, status `ACCEPTED_UPSIDE_EXIT`, boundary `0.304600`
- `XA002` `Z002` UP: candidate `2023-12-02 20:00:00`, status `FAILED_UPSIDE_EXIT`, boundary `0.395100`
- `XA003` `Z002` UP: candidate `2023-12-04 04:00:00`, status `FAILED_UPSIDE_EXIT`, boundary `0.403000`
- `XA004` `Z002` UP: candidate `2023-12-05 16:00:00`, status `ACCEPTED_UPSIDE_EXIT`, boundary `0.415000`
- `XA005` `Z003` UP: candidate `2023-12-13 20:00:00`, status `FAILED_UPSIDE_EXIT`, boundary `0.647400`
- `XA006` `Z003` DOWN: candidate `2024-01-07 20:00:00`, status `FAILED_DOWNSIDE_EXIT`, boundary `0.510600`

## R5 Mapping

r5_section_id zone_id zone_start_open_time zone_effective_exit_open_time zone_resolution_kind             mapping_reason
        LC001    Z001  2023-10-31 12:00:00           2023-11-01 20:00:00 ACCEPTED_UPSIDE_EXIT overlap by causal bar span
        LC002    Z002  2023-11-12 16:00:00           2023-12-05 16:00:00 ACCEPTED_UPSIDE_EXIT overlap by causal bar span
        LC003    Z003  2023-12-11 00:00:00           2024-01-08 20:00:00    OPEN_AT_TRAIN_END overlap by causal bar span

## Acceptance Tests

- `EXPECTED_THREE_ZONES`: `PASS` — 3 zones
- `FIRST_ZONE_PRESERVED`: `PASS` — 1 matching zone(s): Z001
- `NOVEMBER_SINGLE_ZONE`: `PASS` — 1 matching zone(s): Z002
- `DECEMBER_JANUARY_SINGLE_ZONE`: `PASS` — 1 matching zone(s): Z003
- `LC003_EARLIER_DOWNSIDE_EXIT_THAN_R5`: `FAIL` — zone 2024-01-08 20:00:00 vs R5 2024-01-06 16:00:00
- `NO_DATE_HARDCODING`: `PASS` — general chronological builder
- `NO_PRICE_BOUND_HARDCODING`: `PASS` — causal seeds and failed-exit expansions
- `NO_SECTION_ID_HARDCODING`: `PASS` — section IDs used only in diagnostics
- `NO_FUTURE_PERIOD_USED`: `PASS` — period slice ends at configured END

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, trading logic, date hardcoding, price-bound hardcoding, or section-id hardcoding. `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B artifacts were not modified.
