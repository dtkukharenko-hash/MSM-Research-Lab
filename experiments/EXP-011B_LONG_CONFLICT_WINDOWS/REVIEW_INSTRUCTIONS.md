# EXP-011B R2 Full Section Review

Status: AWAITING_TW_FULL_SECTION_REVIEW

## Workflow

1. Open Bybit ADAUSDT Perpetual Contract.
2. Select 4H.
3. Add your own EMA27 and EMA200.
4. Add `artifacts/LONG_CONFLICT_WINDOWS.pine`.
5. Select `LC001`, `LC002`, and so on.
6. Review the whole process, not only the strict trigger.
7. Fill `artifacts/manual_full_section_review.csv`.

## Check Each LC

- Is a stable aligned long visible before `D`?
- Did loss of alignment start earlier than `D`?
- Is `D` the first dispute bar?
- Is `T` inside an already-started process?
- Does the yellow area avoid ending on a temporary bounce?
- Is there a clear stable state after `E`?
- Should the section continue further?
- Should it merge with a neighboring LC?
- Are events missing to the left or right?

## Do Not Analyze Yet

- Causes of later movement.
- Technical Ratings.
- Forecasts.
- Trading actions.
- Final conflict classification.

## Source Note

Automatic windows use EXP-011 Binance spot 4H OHLC. Manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so some candles and boundaries may differ by one or more bars.
