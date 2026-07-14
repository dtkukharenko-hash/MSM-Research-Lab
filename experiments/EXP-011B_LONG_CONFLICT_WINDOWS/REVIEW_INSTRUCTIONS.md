# EXP-011B R4 Adaptive Recovery Review

Status: AWAITING_TW_ADAPTIVE_RECOVERY_REVIEW

## Workflow

1. Open Bybit ADAUSDT Perpetual Contract.
2. Select 4H.
3. Add your own EMA27 and EMA200.
4. Add `artifacts/LONG_DISPUTE_ADAPTIVE_RECOVERY_R4.pine`.
5. Select one R4 `LC` at a time.
6. Review `D -> episode -> W/M/S -> possible F -> E -> C`.
7. Fill `artifacts/manual_adaptive_recovery_review.csv`.

## Event Legend

- `D`: DISPUTE_START.
- `T`: CORE_TRIGGER.
- `W`: WEAK_RECOVERY.
- `M`: MODERATE_RECOVERY.
- `S`: STRONG_RECOVERY.
- `F`: FAILED_RECOVERY.
- `N`: NEW_CONFIGURATION_ATTEMPT.
- `X`: EMA27/EMA200 cross down.
- `E`: EFFECTIVE_EXIT.
- `C`: EXIT_CONFIRMATION.
- `O`: OPEN_AT_TRAIN_END.

## Check Each R4 LC

- Is `D` the first dispute start?
- Is the recovery class weak, moderate, or strong?
- Does strong recovery create a genuinely independent next section?
- Was the November process kept as one section?
- Was the early December conflict separated from the later long conflict?
- Does the yellow dispute area end at `E`?
- Is the light probation area only between `E` and `C`?
- Is `C` understood as causal confirmation, not the factual end of dispute movement?

## Do Not Analyze Yet

- Causes of later movement.
- Technical Ratings.
- Forecasts.
- Trading actions.
- Final conflict classification.

## Source Note

Automatic windows use EXP-011 Binance spot 4H OHLC. Manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so some candles and boundaries may differ by one or more bars.
