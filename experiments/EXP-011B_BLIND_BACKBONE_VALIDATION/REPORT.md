# EXP-011B — BLIND VISUAL BACKBONE VALIDATION

Status: AWAITING_HUMAN_LABELS

Verdict: AWAITING_HUMAN_LABELS

## Phase 1 Package

Prepared blind review windows for human visual validation of frozen EXP-011A `BACKBONE_C`.

- Blind windows: `28`
- TYPE_A source windows: `8`
- TYPE_B source windows: `7`
- Mirror DOWN windows: `5`
- ACTIVE+ALIGNED windows: `4`
- Control windows: `4`
- Random seed: `11011`

## Frozen Model

`BACKBONE_C` is frozen from EXP-011A. No formulas, thresholds, windows, hysteresis, or persistence rules were changed. EXP-011A artifacts were used read-only.

## Review Mode

Preferred TradingView mode is used. The PDF lists one blind window per page with `blind_id` and UTC interval only. Visual assessment should be done on ADAUSDT 1H in TradingView with the user's own EMA27 and EMA200.

Pine path: `artifacts/BLIND_BACKBONE_REVIEW.pine`

Human label template: `artifacts/human_labels.csv`

Do not open `artifacts/blind_key.csv` until all human labels are complete.

## No Final Verdict

This is Phase 1 only. Final semantic validation requires Phase 2 scoring after `human_labels.csv` is filled.

## Constraints

No Irobot, no 2025+ data, no PnL, no backtest, no entry/exit/stop/risk, no model tuning, and no change to `docs/DEFINITIONS.md`.
