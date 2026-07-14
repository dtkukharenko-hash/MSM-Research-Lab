# EXP-011B R5 Structural Reset Review

Status: AWAITING_TW_STRUCTURAL_RESET_REVIEW

## Workflow

1. Open Bybit ADAUSDT Perpetual Contract.
2. Select 4H.
3. Add your own EMA27 and EMA200.
4. Add `artifacts/LONG_DISPUTE_STRUCTURAL_RESET_R5.pine`.
5. Select one R5 `LC` at a time.
6. Review `D -> episode -> I or S? -> SF/SR -> E -> C`.
7. Fill `artifacts/manual_structural_reset_review.csv`.

## Event Legend

- `D`: DISPUTE_START.
- `T`: CORE_TRIGGER.
- `I`: INTERNAL_RECOVERY.
- `S?`: STRUCTURAL_RESET_CANDIDATE.
- `SF`: FAILED_STRUCTURAL_RESET.
- `SR`: CONFIRMED_STRUCTURAL_RESET.
- `N`: NEW_CONFIGURATION_ATTEMPT.
- `E`: EFFECTIVE_EXIT.
- `C`: EXIT_CONFIRMATION.
- `O`: OPEN_AT_TRAIN_END.

## Check Each R5 LC

- Is `D` the first dispute start?
- Is `I` only an internal recovery inside the same disputed price area?
- Does `S?` truly clear the frozen structural reset level?
- Does `SR` separate a genuinely new section?
- Does `SF` keep the section open?
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
