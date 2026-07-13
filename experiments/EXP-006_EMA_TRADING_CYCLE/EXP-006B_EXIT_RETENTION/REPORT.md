# EXP-006B — Exit Retention Report

Verdict: **EXIT_RETENTION_FOUND**

## Boundary

- Entry, initial STOP_A, EMA27/EMA200 regimes and costs are unchanged from EXP-006.
- Source: `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv` read-only.
- True holdout after 2025-07-01 04:00:00 was not used.
- REUSED TEMPORAL TEST is explicitly not independent OOS.

## Development Metrics

| exit_variant | trades | profit_factor | total_return | max_drawdown | median_mfe_capture | mean_mfe_capture | good_entry_bad_exit_share | early_exit_share | late_exit_share | pf_cost_x2 | return_cost_x2 | without_top1_return | passes_development |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXIT_R0 | 43 | 2.29525 | 0.778136 | -0.160701 | -0.383443 | -1.95285 | 0.162791 | 0 | 0.0465116 | 2.00886 | 0.633141 | 0.497116 | False |
| EXIT_R1 | 43 | 0.148893 | -0.348444 | -0.348452 | 0.0194393 | -2.67712 | 0.0465116 | 0 | 0 | 0.123618 | -0.402714 | -0.392804 | False |
| EXIT_R2 | 43 | 2.09387 | 0.640264 | -0.162086 | 0.342187 | -2.45475 | 0 | 0 | 0.0232558 | 1.85327 | 0.506303 | 0.402972 | True |
| EXIT_R3 | 43 | 1.54933 | 0.26752 | -0.181905 | 0.332787 | -2.48295 | 0 | 0 | 0 | 1.34661 | 0.163446 | 0.130026 | True |
| EXIT_R4 | 43 | 2.29525 | 0.778136 | -0.160701 | -0.383443 | -1.95285 | 0.162791 | 0 | 0.0465116 | 2.00886 | 0.633141 | 0.497116 | False |
| EXIT_R5 | 43 | 1.98949 | 0.418244 | -0.128957 | 0.332787 | -1.78951 | 0 | 0 | 0 | 1.69305 | 0.302097 | 0.264401 | True |

## Selected Exits

| exit_variant | profit_factor | median_mfe_capture | good_entry_bad_exit_share | max_drawdown | rank_score |
| --- | --- | --- | --- | --- | --- |
| EXIT_R2 | 2.09387 | 0.342187 | 0 | -0.162086 | 3.45678 |
| EXIT_R5 | 1.98949 | 0.332787 | 0 | -0.128957 | 3.15102 |

## Exit Validation

| exit_variant | trades | profit_factor | total_return | max_drawdown | median_mfe_capture | good_entry_bad_exit_share | early_exit_share | late_exit_share | without_top1_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXIT_R0 | 12 | 13.3866 | 2.45129 | -0.0655941 | -0.00792389 | 0.0833333 | 0 | 0.0833333 | 1.01157 |
| EXIT_R2 | 12 | 1.21168 | 0.0307055 | -0.10467 | 0.11353 | 0 | 0 | 0.0833333 | -0.048411 |
| EXIT_R5 | 12 | 3.1354 | 0.222747 | -0.0655941 | 0.165803 | 0 | 0 | 0 | 0.0397632 |

## Reused Temporal Test

| exit_variant | trades | profit_factor | total_return | max_drawdown | median_mfe_capture | good_entry_bad_exit_share | without_top1_return |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EXIT_R0 | 21 | 0.714102 | -0.121588 | -0.178257 | -0.743992 | 0.0952381 | -0.221521 |
| EXIT_R2 | 21 | 1.45132 | 0.13956 | -0.180851 | -0.743992 | 0 | -0.0177242 |
| EXIT_R5 | 21 | 1.26777 | 0.0708576 | -0.144246 | -0.743992 | 0 | -0.050969 |

## Answers

1. MFE capture was recalculated directionally as realized favorable price delta divided by max favorable price delta; UNKNOWN is used when MFE <= 0.
2. Baseline EXIT_R0 DEVELOPMENT median MFE capture: `-0.383`, GOOD_ENTRY_BAD_EXIT `16.3%`.
3. Best DEVELOPMENT retention candidates: `EXIT_R2, EXIT_R5`.
4. GOOD_ENTRY_BAD_EXIT changes are in `failure_type_comparison.csv` and metric tables.
5. EARLY_EXIT share is reported per exit; no early-exit replacement is accepted without validation.
6. Phase analysis for MFE <1, 1-2, >=2 ATR is in `trade_phase_analysis.csv`.
7. DEVELOPMENT passed variants: `EXIT_R2, EXIT_R5`.
8. EXIT VALIDATION was applied without rule changes to selected variants only.
9. REUSED TEMPORAL TEST is a consistency check only, not independent OOS.
10. Costs x2/x3 are in `cost_stress.csv`.
11. Concentration checks are in `concentration_checks.csv`.
12. LONG/SHORT totals are in `development_metrics.csv`.
13. Working retention mechanism: `EXIT_RETENTION_FOUND`.
14. Do not prepare a true holdout unless the strong criteria are met; otherwise continue only from the diagnosed exit-retention result.

## Artifacts

- `artifacts/all_exit_trades.csv`
- `artifacts/development_metrics.csv`
- `artifacts/selected_exits.csv`
- `artifacts/exit_validation_metrics.csv`
- `artifacts/reused_temporal_metrics.csv`
- `artifacts/mfe_capture_distribution.csv`
- `artifacts/failure_type_comparison.csv`
- `artifacts/exit_reason_counts.csv`
- `artifacts/cost_stress.csv`
- `artifacts/concentration_checks.csv`
- `artifacts/trade_phase_analysis.csv`
- `artifacts/mfe_capture_comparison.png`
- `artifacts/giveback_comparison.png`
- `artifacts/equity_curves.png`
- `artifacts/EMA_EXIT_RETENTION_REVIEW.pine`
- `artifacts/EMA_EXIT_RETENTION_OVERVIEW.pdf`
