# EXP-011B — BLIND VISUAL BACKBONE VALIDATION

## Goal

Prepare a blind visual validation package for the frozen `BACKBONE_C` model from EXP-011A. This phase does not score human labels and does not produce a final semantic verdict.

## Phase

Phase 1 only: `AWAITING_HUMAN_LABELS`.

The human reviewer must inspect blind windows without opening `artifacts/blind_key.csv`, then fill `artifacts/human_labels.csv`.

## Sources

Use only saved artifacts from:

- `experiments/EXP-011A_SLOW_BACKBONE_FAST_PHASE/artifacts/`
- saved OHLC from `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/`

Do not recalculate or modify the model. Do not change formulas, thresholds, windows, hysteresis, or persistence. Do not use 2025+ data.

## Constraints

Forbidden: Irobot, ZigZag, clustering, PnL, backtest, entry, exit, stop, risk, model tuning, changing `docs/DEFINITIONS.md`, changing EXP-011A, and staging the existing EXP009A Pine file.

## Outputs

Create blind review windows, blind key, empty human label template, blind navigation Pine, blind PDF, review instructions, scoring script, and Phase 1 report.

Commit message: `EXP-011B prepare blind backbone validation`.
