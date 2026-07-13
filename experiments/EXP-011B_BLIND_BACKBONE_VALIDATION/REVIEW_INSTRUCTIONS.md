# EXP-011B Blind Review Instructions

Status: AWAITING_HUMAN_LABELS

Do not open `artifacts/blind_key.csv` until every row in `artifacts/human_labels.csv` is complete.

## Workflow

1. Open ADAUSDT on the 1H chart.
2. Add your own EMA27 and EMA200 to TradingView.
3. Add `artifacts/BLIND_BACKBONE_REVIEW.pine`.
4. Select `BV001`, `BV002`, and so on with `selectedBlindId`.
5. Evaluate the 4H EMA200-backbone state for each blind window.
6. Fill `artifacts/human_labels.csv`.

## Labels

Use only:

- `ACTIVE`
- `FLATTENING`
- `AMBIGUOUS`

Confidence:

- `1` low
- `2` medium
- `3` high

## ACTIVE

- EMA200 keeps a stable direction.
- EMA200 slope is preserved.
- Local price movement and EMA27 movement against the direction do not destroy the backbone.
- EMA200 does not visually look directionless.

## FLATTENING

- EMA200 visibly loses slope.
- EMA200 becomes close to horizontal.
- Directional stability of EMA200 weakens.
- EMA200 changes look less consistent.

## AMBIGUOUS

- Visual difference is insufficient.
- ACTIVE and FLATTENING both look plausible.
- The window is directly around a transition.

## Do Not Evaluate

- Future price movement.
- Profitability.
- Joining points.
- Future direction.
