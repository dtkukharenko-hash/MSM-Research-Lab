# EXP-006 — EMA Trading Cycle

## Goal

Build and test a practical, fixed EMA200/EMA27 trading cycle for ADAUSDT 4H:

context -> preparation -> entry -> management -> exit.

This experiment compares predefined entry/stop/exit logic. It does not search for a new strategy, optimize parameters, use ML, or open the true 12-month holdout.

## Data

- Asset: ADAUSDT
- Timeframe: 4H
- Source: `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv` as read-only OHLC data
- Research period: 2023-07-01 00:00 UTC -> 2025-07-01 00:00 UTC
- Train: 2023-07-01 00:00 UTC -> 2024-12-19 23:59 UTC
- Temporal test: 2024-12-20 00:00 UTC -> 2025-07-01 00:00 UTC
- True holdout, not used: 2025-07-01 04:00 UTC -> 2026-07-01 00:00 UTC

## Allowed Inputs

- OHLC
- EMA27
- EMA200
- ATR14 only for risk and distance normalization
- Closed bars only

## Prohibited

- ZigZag
- OI, funding, volume
- ML
- complex optimization
- true holdout data
- future bars
- manual marking of entries after results
- modifying Irobot
- modifying `docs/DEFINITIONS.md`

## Fixed Regimes

`slope_20 = EMA200[t] - EMA200[t-20]`.

`BULL_REGIME`:

- close > EMA200
- EMA200 slope_20 > 0
- EMA27 > EMA200

`BEAR_REGIME`:

- close < EMA200
- EMA200 slope_20 < 0
- EMA27 < EMA200

`TRANSITION` otherwise.

## Preparation

`LONG_PREP`:

- context is `BULL_REGIME`, or `TRANSITION` with EMA27 > EMA200 and EMA200 slope_20 not negative
- last 10 bars price was at least once below EMA27
- current close is back above EMA27
- EMA27 slope_5 > 0
- EMA27 slope_10 >= 0
- last 3 closes do not show sustained fall
- close is not farther than 2 ATR above EMA27

`SHORT_PREP` is mirrored.

## Entries

`ENTRY_A`: return across EMA27. For long: `LONG_PREP`, current close > EMA27, previous close <= EMA27, enter next open. Short mirrored.

`ENTRY_B`: continuation. For long: `LONG_PREP`, after return above EMA27 price updates max of last 3 bars, enter next open. Short mirrored.

`ENTRY_C`: two-bar hold. For long: `LONG_PREP`, two consecutive closes above EMA27, second close not below first, enter next open. Short mirrored.

## Stops

`STOP_A`: nearest local extreme of last 5 closed bars.

- Long: min low of last 5 closed bars
- Short: max high of last 5 closed bars

`STOP_B`: ATR stop.

- Long: entry - 1.5 ATR14
- Short: entry + 1.5 ATR14

## Management

Track last active directional candle, EMA27, extreme update, continuation attempts, and counter-move depth.

For long, the active reference candle is the latest bullish candle whose body is greater than the median body of the previous 10 candles, closed in the upper third of its own range, and after which a local high has already been updated. Short is mirrored.

If a new candle meets the reference condition, it replaces the previous one. If none exists, active reference is `UNKNOWN`.

## Exits

`EXIT_A`: close beyond EMA27. Long exits after first close below EMA27; short mirrored.

`EXIT_B`: two-bar EMA27 confirmation. Long exits after two consecutive closes below EMA27; short mirrored.

`EXIT_C`: active reference violation. Long exits when a counter bearish candle closes below midpoint of the active bullish reference body, then within the next two closed bars the movement high is not updated. Short mirrored.

`EXIT_D`: combined. Long exits on the first of: two closes below EMA27, close below open of active bullish reference candle, or stop-loss. Short mirrored.

Regime flip is a mandatory exit for every exit variant. No opposite position is opened on the same bar.

## Matrix

Run all fixed combinations:

- 3 entries
- 2 stops
- 4 exits

Total: 24 combinations.

On train, build a shortlist of at most 3 combinations using PF, drawdown, trade count, MFE capture, cost robustness, concentration, and LONG/SHORT balance. Do not choose only by total return.

Apply only the shortlist to temporal test without changes.

## Required Artifacts

- `REPORT.md`
- `experiment_006.py`
- `artifacts/trades_all_combinations.csv`
- `artifacts/combination_metrics.csv`
- `artifacts/train_rankings.csv`
- `artifacts/shortlist.csv`
- `artifacts/temporal_test_metrics.csv`
- `artifacts/temporal_test_trades.csv`
- `artifacts/entry_analysis.csv`
- `artifacts/exit_analysis.csv`
- `artifacts/reference_candles.csv`
- `artifacts/cost_stress.csv`
- `artifacts/concentration_checks.csv`
- `artifacts/equity_curves.png`
- `artifacts/entry_comparison.png`
- `artifacts/exit_comparison.png`
- `artifacts/mfe_capture.png`
- `artifacts/EMA_TRADING_CYCLE_REVIEW.pine`
- `artifacts/EMA_TRADING_CYCLE_OVERVIEW.pdf`

## Verdict

One of:

- `WORKABLE_EMA_CYCLE_FOUND`
- `ENTRY_WORKS_EXIT_WEAK`
- `EXIT_WORKS_ENTRY_WEAK`
- `WEAK_EMA_CYCLE`
- `NO_WORKABLE_CYCLE`
- `DATA_INSUFFICIENT`
