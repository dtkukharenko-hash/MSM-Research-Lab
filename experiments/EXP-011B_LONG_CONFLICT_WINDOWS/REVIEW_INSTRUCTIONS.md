# EXP-011B Long Conflict Boundary Review

Status: AWAITING_TW_BOUNDARY_REVIEW

## Workflow

1. Open Bybit ADAUSDT Perpetual Contract.
2. Select 4H.
3. Add your own EMA27 and EMA200.
4. Add `artifacts/LONG_CONFLICT_WINDOWS.pine`.
5. Select `LC001`, `LC002`, and so on.
6. Fill `artifacts/manual_boundary_review.csv`.

## Check Only Boundaries

For each section, answer:

- Was there a LONG context before the section?
- Is the start of the conflict correct?
- Should it start earlier?
- Should it start later?
- Is the end of the conflict correct?
- Should it end earlier?
- Should it end later?
- Should the section be split?
- Should it be merged with a neighboring section?
- Is a conflict missing between sections?

## Do Not Analyze Yet

- Why the move continued.
- Why a transition happened.
- Which section is stronger.
- What the section predicts.
- Trading entries, exits, stops, risk, or PnL.

## Source Note

The automatic windows were generated from EXP-011 Binance spot 4H OHLC. Manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so small bar-level differences are possible.
