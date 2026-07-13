# EXP-006D Visual Review — Frozen Holdout Trades

## Scope

This audit visualizes the already calculated frozen holdout trades from `holdout_trades_r5.csv`. It does not rerun the backtest, search ENTRY_A, change STOP_A, change EXIT_R5, or create new signals.

Pine file: `artifacts/EXP006D_HOLDOUT_TRADES.pine`.

## Source Consistency

- Trades in source: 31
- Trades in Pine/map: 31
- `visual_status=MATCH`: 31
- Mismatches: 0
- Intrabar ambiguity trades in EXIT_R5: 1 (H_EXIT_R5_0018)

`visual_audit_mismatches.csv` is intentionally empty except for headers because the Pine arrays and `holdout_trade_map.csv` were generated directly from the frozen CSV source.

## Exit Types

- MFE_50_GIVEBACK: 18
- STOP_A: 11
- EMA27_HYSTERESIS: 2

## Required Answers

1. All 31 trades are displayed in the Pine script as hardcoded entries/exits from `holdout_trades_r5.csv`.
2. No Pine/source mismatches were found in entry_time, exit_time, entry_price, exit_price, direction, exit_reason, stop, PnL, or bars held.
3. The most frequent exit type is `MFE_50_GIVEBACK`, followed by `STOP_A`; `EMA27_HYSTERESIS` appears rarely. No `REGIME_FLIP` exits appear in the frozen R5 holdout trades.
4. Trades that gave back most of their MFE are the negative-capture trades: H_EXIT_R5_0028, H_EXIT_R5_0011, H_EXIT_R5_0024, H_EXIT_R5_0006, H_EXIT_R5_0009, H_EXIT_R5_0001, H_EXIT_R5_0012, H_EXIT_R5_0018, H_EXIT_R5_0022, H_EXIT_R5_0026, H_EXIT_R5_0031, H_EXIT_R5_0017, H_EXIT_R5_0015, H_EXIT_R5_0023, H_EXIT_R5_0007.
5. Trades that were losing almost immediately, using frozen fields only (`net_return < 0` and `bars <= 2`): H_EXIT_R5_0001, H_EXIT_R5_0006, H_EXIT_R5_0009, H_EXIT_R5_0017, H_EXIT_R5_0020, H_EXIT_R5_0024, H_EXIT_R5_0028, H_EXIT_R5_0031.
6. Cases where entry had at least `1 ATR` MFE but final PnL was negative, so they deserve visual review as possible normal-entry / poor-exit cases: H_EXIT_R5_0007, H_EXIT_R5_0015, H_EXIT_R5_0023.
7. Cases where the problem was already in the entry context, using the existing `NO_MOVEMENT` failure type or sub-1 ATR MFE with negative PnL: H_EXIT_R5_0001, H_EXIT_R5_0006, H_EXIT_R5_0009, H_EXIT_R5_0011, H_EXIT_R5_0012, H_EXIT_R5_0017, H_EXIT_R5_0018, H_EXIT_R5_0020, H_EXIT_R5_0022, H_EXIT_R5_0024, H_EXIT_R5_0026, H_EXIT_R5_0028, H_EXIT_R5_0031.
8. Quarter labels show 2025-Q3/Q4 and 2026-Q1/Q2 in Pine. The report does not make a new strategy conclusion before manual visual review; the frozen metrics already showed deterioration in 2026-Q1/Q2.
9. LONG/SHORT are visually separated in Pine by direction labels and colors. The sample is imbalanced (4 LONG, 27 SHORT), so the visual audit should not infer a strategy conclusion from direction alone.
10. First 10 TradingView manual-review priorities, ranked only from frozen audit fields: H_EXIT_R5_0018, H_EXIT_R5_0009, H_EXIT_R5_0011, H_EXIT_R5_0020, H_EXIT_R5_0028, H_EXIT_R5_0006, H_EXIT_R5_0001, H_EXIT_R5_0024, H_EXIT_R5_0022, H_EXIT_R5_0017.

## Groups Marked In Pine

- Winning trades: exit label uses green PnL color.
- Losing trades: exit label uses red PnL color.
- Stop exits: `STOP_A` label at stop line.
- Giveback exits: `MFE_50_GIVEBACK` in exit label and yellow 50% giveback line when source MFE exists.
- EMA hysteresis exits: separate `EMA warning / hysteresis exit` label.
- Regime flip exits: supported by script, but none are present in R5 holdout trades.
- Ambiguous intrabar trades: magenta `INTRABAR AMBIGUITY` label.
- LONG / SHORT: direction in entry label and direction color.

## Special Labels

- Top 5 winners: H_EXIT_R5_0010, H_EXIT_R5_0019, H_EXIT_R5_0005, H_EXIT_R5_0002, H_EXIT_R5_0013
- Top 5 losers: H_EXIT_R5_0009, H_EXIT_R5_0020, H_EXIT_R5_0011, H_EXIT_R5_0018, H_EXIT_R5_0022
- 2026-Q1 trades: H_EXIT_R5_0015, H_EXIT_R5_0016, H_EXIT_R5_0017, H_EXIT_R5_0018, H_EXIT_R5_0019, H_EXIT_R5_0020, H_EXIT_R5_0021
- 2026-Q2 trades: H_EXIT_R5_0022, H_EXIT_R5_0023, H_EXIT_R5_0024, H_EXIT_R5_0025, H_EXIT_R5_0026, H_EXIT_R5_0027, H_EXIT_R5_0028, H_EXIT_R5_0029, H_EXIT_R5_0030, H_EXIT_R5_0031
- MFE >= 2 ATR but final PnL negative: none
- Negative MFE capture: H_EXIT_R5_0001, H_EXIT_R5_0006, H_EXIT_R5_0007, H_EXIT_R5_0009, H_EXIT_R5_0011, H_EXIT_R5_0012, H_EXIT_R5_0015, H_EXIT_R5_0017, H_EXIT_R5_0018, H_EXIT_R5_0022, H_EXIT_R5_0023, H_EXIT_R5_0024, H_EXIT_R5_0026, H_EXIT_R5_0028, H_EXIT_R5_0031
- EXIT_R0 would be better than EXIT_R5 per trade: not marked, because the available `exit_comparison.csv` is aggregate and does not contain per-trade pairwise superiority.

## Pine Limitations

- First exact `MFE >= 1 ATR` activation time is not present in `holdout_trades_r5.csv`; the script marks the source `mfe_time` and the derived 50% giveback level for visual review.
- EMA warning cancellation and hysteresis internals are not present as per-bar event fields in the frozen trade CSV; the script marks EMA hysteresis exit trades only.
- Regime flip support is present in Pine, but no frozen R5 holdout trade exited by `REGIME_FLIP`.

## Verdict

VISUAL_REVIEW_READY
