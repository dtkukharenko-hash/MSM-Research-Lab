# EXP-006C — Frozen Exit Robustness

## Goal

Audit robustness of already discovered exit mechanisms `EXIT_R2` and `EXIT_R5` without changing `ENTRY_A`, `STOP_A`, EMA27/EMA200, thresholds, or exit logic.

This is a frozen-rule robustness audit. It must not create new entries, exits, filters, parameters, or open the true holdout.

## Frozen Variants

- `EXIT_R0`: baseline, two consecutive closes against EMA27.
- `EXIT_R2`: after MFE >= 1.5 ATR, exit on 1.0 ATR giveback from maximum favorable price.
- `EXIT_R5`: first of proportional 50% MFE giveback after MFE >= 1 ATR, EMA27 hysteresis, STOP_A, full regime flip.

## Fixed System

- Asset: ADAUSDT
- Timeframe: 4H
- Entry: `ENTRY_A` from EXP-006
- Initial stop: `STOP_A` from EXP-006
- EMA: EMA27 and EMA200 unchanged
- Baseline costs: 0.10% fee per side, 0.05% slippage per side
- Stress costs: x2 and x3
- True holdout not used: 2025-07-01 04:00 UTC -> 2026-07-01 00:00 UTC

## Required Checks

1. Audit MFE capture calculation manually and explain why reused temporal median capture was identical.
2. Confirm entry identity between R0/R2/R5, and explicitly mark whether comparisons are common-entry or variant-specific.
3. Run fixed calendar block metrics.
4. Run rolling-origin metrics.
5. Pairwise compare common trades.
6. Run concentration stress tests.
7. Report LONG/SHORT stability.
8. Report cost robustness by block and overall.

## Artifacts

- `REPORT.md`
- `experiment_006c.py`
- `artifacts/mfe_capture_audit.csv`
- `artifacts/entry_alignment.csv`
- `artifacts/quarterly_metrics.csv`
- `artifacts/rolling_origin_metrics.csv`
- `artifacts/paired_trade_comparison.csv`
- `artifacts/bootstrap_pair_differences.csv`
- `artifacts/concentration_stress.csv`
- `artifacts/direction_metrics.csv`
- `artifacts/cost_robustness_by_block.csv`
- `artifacts/quarterly_pf.png`
- `artifacts/rolling_pf.png`
- `artifacts/paired_return_difference.png`
- `artifacts/concentration_plot.png`
- `artifacts/EXIT_ROBUSTNESS_REVIEW.pine`
- `artifacts/EXIT_ROBUSTNESS_OVERVIEW.pdf`

## Verdict

One of:

- `EXIT_RULE_FROZEN_READY`
- `EXIT_RULE_PARTIAL`
- `EXIT_RULE_REJECTED`
- `METRIC_IMPLEMENTATION_ERROR`
- `DATA_INSUFFICIENT`
