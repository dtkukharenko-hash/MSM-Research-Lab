# EXP-006C — Frozen Exit Robustness Report

Verdict: **EXIT_RULE_FROZEN_READY**

## Boundary

- Frozen variants only: EXIT_R0, EXIT_R2, EXIT_R5.
- ENTRY_A, STOP_A, EMA27/EMA200 and thresholds unchanged.
- True holdout after 2025-07-01 04:00:00 was not used.

## MFE Capture Audit

Manual audit mismatches: `0`.
Reused temporal median capture equality after EXP-006C metric audit: `False`.
The identical `-0.743992` median seen in EXP-006B does not persist after applying the literal EXP-006C exit-time-inclusive capture audit. No per-trade sign error or copied capture value remains in the corrected EXP-006C artifacts.

## Entry Alignment

| exit_variant | entry_records | common_entry_records | variant_specific_entries | comparison_mode |
| --- | --- | --- | --- | --- |
| EXIT_R0 | 76 | 76 | 0 | COMMON_SIGNAL_GRID_NO_POSITION_OCCUPANCY |
| EXIT_R2 | 76 | 76 | 0 | COMMON_SIGNAL_GRID_NO_POSITION_OCCUPANCY |
| EXIT_R5 | 76 | 76 | 0 | COMMON_SIGNAL_GRID_NO_POSITION_OCCUPANCY |

## All Research Metrics

| exit_variant | trades | profit_factor | total_return | max_drawdown | median_mfe_capture | good_entry_bad_exit_share | pf_cost_x2 | pf_cost_x3 | long_pf | short_pf |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXIT_R0 | 76 | 3.08273 | 4.39069 | -0.207379 | -0.400503 | 0.131579 | 2.76075 | 2.49035 | 3.89538 | 2.25196 |
| EXIT_R2 | 76 | 1.70899 | 0.926573 | -0.180851 | 0.0885556 | 0 | 1.52976 | 1.37091 | 0.952976 | 2.96798 |
| EXIT_R5 | 76 | 1.82657 | 0.857032 | -0.144246 | 0.141405 | 0 | 1.59274 | 1.39172 | 1.26974 | 2.60348 |

## Rolling Folds

| scope | exit_variant | trades | sample_flag | profit_factor | total_return | median_mfe_capture | good_entry_bad_exit_share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | EXIT_R0 | 8 | OK | 1.05627 | 0.000755333 | -0.360559 | 0.25 |
| F1 | EXIT_R2 | 8 | OK | 3.72132 | 0.22038 | 0.575534 | 0 |
| F1 | EXIT_R5 | 8 | OK | 2.45359 | 0.112203 | 0.325404 | 0 |
| F2 | EXIT_R0 | 14 | OK | 7.83123 | 0.925983 | 0.32526 | 0.214286 |
| F2 | EXIT_R2 | 14 | OK | 6.20343 | 0.509753 | 0.503706 | 0 |
| F2 | EXIT_R5 | 14 | OK | 6.12765 | 0.375716 | 0.426177 | 0 |
| F3 | EXIT_R0 | 7 | OK | 3.0739 | 0.124554 | -0.0763836 | 0.142857 |
| F3 | EXIT_R2 | 7 | OK | 0.774369 | -0.0232869 | 0.0856552 | 0 |
| F3 | EXIT_R5 | 7 | OK | 2.16734 | 0.0411468 | 0.141405 | 0 |
| F4 | EXIT_R0 | 5 | OK | 22.8178 | 2.06903 | 0.553077 | 0 |
| F4 | EXIT_R2 | 5 | OK | 1.57689 | 0.0552797 | 0.374858 | 0 |
| F4 | EXIT_R5 | 5 | OK | 3.66073 | 0.174423 | 0.379032 | 0 |
| F5 | EXIT_R0 | 10 | OK | 1.24849 | 0.033354 | -0.803766 | 0.2 |
| F5 | EXIT_R2 | 10 | OK | 1.60656 | 0.0719571 | 0.149288 | 0 |
| F5 | EXIT_R5 | 10 | OK | 2.07308 | 0.160152 | -0.55192 | 0 |
| F6 | EXIT_R0 | 11 | OK | 0.191277 | -0.149941 | -0.743992 | 0 |
| F6 | EXIT_R2 | 11 | OK | 1.3657 | 0.0630648 | -1.15073 | 0 |
| F6 | EXIT_R5 | 11 | OK | 0.630103 | -0.076968 | -0.743992 | 0 |

## Paired Differences

| exit_variant | phase | n | share_better_than_R0 | median_return_diff | median_capture_diff | bootstrap_ci_low | bootstrap_ci_high | sign_test_p_approx |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXIT_R2 | ALL | 69 | 0.318841 | 0 | 0 | 0 | 0 | 0.00354481 |
| EXIT_R2 | NO_MOVEMENT_MFE_LT_1_ATR | 35 | 0 | 0 | 0 | 0 | 0 | 5.82077e-11 |
| EXIT_R2 | STRONG_MOVEMENT_MFE_GE_2_ATR | 26 | 0.653846 | 0.0134091 | 0.272864 | -0.0185721 | 0.034121 | 0.168638 |
| EXIT_R2 | WEAK_MOVEMENT_MFE_1_2_ATR | 8 | 0.625 | 0.00716932 | 0.218398 | 0 | 0.0211557 | 0.726562 |
| EXIT_R5 | ALL | 67 | 0.328358 | 0 | 0 | 0 | 0 | 0.00674145 |
| EXIT_R5 | NO_MOVEMENT_MFE_LT_1_ATR | 36 | 0 | 0 | 0 | 0 | 0 | 2.91038e-11 |
| EXIT_R5 | STRONG_MOVEMENT_MFE_GE_2_ATR | 22 | 0.590909 | 0.00712665 | 0.0924799 | -0.0444681 | 0.0220673 | 0.523467 |
| EXIT_R5 | WEAK_MOVEMENT_MFE_1_2_ATR | 9 | 1 | 0.011107 | 0.503691 | 0.00975254 | 0.0176365 | 0.00390625 |

## Concentration

| exit_variant | total_return | return_without_top1 | return_without_top3 | top1_profit_share | top3_profit_share | top5_profit_share | best_block | pf_without_best_block | return_without_best_block |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXIT_R0 | 4.39069 | 2.14194 | 0.625955 | 0.228929 | 0.489509 | 0.606044 | 2024-Q4 to 2024-12-19 | 1.69598 | 0.756481 |
| EXIT_R2 | 0.926573 | 0.647862 | 0.214933 | 0.0923683 | 0.272183 | 0.428365 | 2024-Q2 | 1.32226 | 0.276085 |
| EXIT_R5 | 0.857032 | 0.579127 | 0.247669 | 0.114867 | 0.278072 | 0.431731 | 2024-Q2 | 1.46297 | 0.349866 |

## Cost Robustness

| exit_variant | blocks | pf_gt1_x1 | pf_gt1_x2 | pf_gt1_x3 |
| --- | --- | --- | --- | --- |
| EXIT_R0 | 8 | 6 | 4 | 4 |
| EXIT_R2 | 8 | 5 | 5 | 5 |
| EXIT_R5 | 8 | 5 | 5 | 5 |

## Answers

1. MFE capture calculation is correct based on manual reconstruction.
2. The reused temporal median capture match from EXP-006B was a metric-convention artifact; after the EXP-006C exit-time-inclusive audit it no longer matches across R0/R2/R5.
3. Entries match across variants in a common signal grid; this audit does not simulate missed re-entry from position occupancy and labels that explicitly.
4. Quarterly behavior is in `quarterly_metrics.csv`; low-sample blocks are flagged.
5. Rolling positive fold counts are in `rolling_origin_metrics.csv`; see cost summary and report tables.
6. Paired comparisons show whether R2/R5 improve common entries; bootstrap and sign-test approximations are in `bootstrap_pair_differences.csv`.
7. Top-1/top-3 stress is in `concentration_stress.csv`.
8. Best-quarter dependency is reported as `pf_without_best_block`.
9. Cost x2/x3 robustness is in `cost_robustness_by_block.csv`.
10. LONG/SHORT metrics are in `direction_metrics.csv`.
11. R2/R5 robustness should be judged by concentration and rolling folds, not validation PF alone.
12. Holdout readiness verdict: `EXIT_RULE_FROZEN_READY`; ready candidate: `EXIT_R5`.
13. EXP-006B verdict should be treated as frozen-ready after this audit.

## Artifacts

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
