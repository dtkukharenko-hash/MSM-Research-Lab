# EXP-011A — SLOW BACKBONE / FAST PHASE DECOMPOSITION

## Goal

Fix the main methodological issue found in EXP-011: a single state mixed the slow EMA200 trend backbone with the fast EMA27 phase. EXP-011A separates the model into:

1. DIRECTION — EMA27/EMA200 order with causal confirmation.
2. SLOW BACKBONE — EMA200-only trend-base state.
3. FAST PHASE — EMA27 and EMA27-EMA200 distance behavior inside the backbone.

The experiment runs independently on ADAUSDT 4H and 1H, then checks whether the same logic transfers between timeframes.

## Data

Use only saved EXP-011 OHLC artifacts:

- `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_1h.csv`
- `experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`

Period: 2023-07-01 00:00:00 UTC through 2024-12-31 23:59:59 UTC. Data after 2024-12-31 is forbidden.

## Constraints

Allowed inputs: OHLC, EMA27, EMA200, and causal EMA-derived transformations only.

Forbidden: ZigZag, clustering, future bars, retrospective outcomes as state inputs, volume, funding, open interest, Irobot, entry, exit, stop, risk, PnL, backtest, trading optimization, changing `docs/DEFINITIONS.md`, and 2025+ data.

Do not change EXP-010, EXP-010A, or EXP-011. Do not stage the existing unstaged EXP009A Pine file.

## Required Outputs

Create `REPORT.md`, `experiment_011a.py`, and all artifacts listed in the task: feature CSVs, direction/backbone/fast/composite states, model comparison, statistics, dwell times, multiscale mapping, visual review windows, EXP-011 comparison, Pine viewer, and contact sheet.

Commit message: `EXP-011A slow backbone fast phase decomposition`.
