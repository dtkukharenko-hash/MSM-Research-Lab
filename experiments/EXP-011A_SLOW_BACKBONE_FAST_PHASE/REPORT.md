# EXP-011A — SLOW BACKBONE / FAST PHASE DECOMPOSITION

Status: DONE / REPORT_READY

Verdict: PARTIAL_BACKBONE_PHASE_DECOMPOSITION

## Data

Source: saved EXP-011 OHLC CSVs only. 1H rows `13200` from `2023-07-01 00:00:00` to `2024-12-31 23:59:59.999000`. 4H rows `3300` from `2023-07-01 00:00:00` to `2024-12-31 23:59:59.999000`. No 2025+ data, no Irobot, no network fetch.

## Answers

1. Selected backbone model: `BACKBONE_C`.

2. Same backbone logic on 4H and 1H: yes by formula. Structural transfer is partial because 4H changes/100=`3.76` and 1H changes/100=`3.88`.

3. Slow backbone can remain ACTIVE while EMA27 moves toward EMA200. ACTIVE+CONTRACTING bars: 4H `471`, 1H `1778`.

4. ACTIVE+CONTRACTING exists on both timeframes.

5. ACTIVE+OPPOSING exists on both timeframes: 4H `640`, 1H `3109`.

6. Mean duration: ACTIVE+CONTRACTING 4H `4.36`, 1H `3.60`; ACTIVE+OPPOSING 4H `9.01`, 1H `10.00`.

7. TYPE_A and TYPE_B differ numerically: TYPE_A=`8`, TYPE_B=`7`, TYPE_C=`6`, TYPE_D=`8`.

8. Visual comparison: PDF vector contact sheet generated without external plotting libraries. TYPE_A and TYPE_B are placed in the same contact-sheet artifact when both exist.

9. Main TYPE_A/TYPE_B difference is EMA200 backbone: TYPE_A requires 4H ACTIVE; TYPE_B requires 4H FLATTENING.

10. EMA27 movement no longer automatically weakens backbone. Fast phase is separate from the EMA200-only backbone.

11. TYPE_A/TYPE_B repeat across distinct months where available; see `visual_review_windows.csv`.

12. Model transfers between 4H and 1H without formula changes; strict verdict depends on visual counts and dwell thresholds.

13. Semantically false WEAKENING is reduced by replacing EXP-011 single WEAKENING with EMA200 backbone plus separate fast phase. See `exp011_vs_exp011a.csv`.

14. Relative corrections remain postponed. EXP-011A supports researching scale relations next only if the partial verdict is accepted as sufficient.

## Verdict Rationale

The layers separate causally and transfer by formula, but at least one strict visual or dwell threshold remains incomplete.

## Constraints

No ZigZag, clustering, Irobot, volume, funding, open interest, outcome fields, backtest, PnL, entry, exit, stop, risk, or 2025+ data. `docs/DEFINITIONS.md` was not changed.
