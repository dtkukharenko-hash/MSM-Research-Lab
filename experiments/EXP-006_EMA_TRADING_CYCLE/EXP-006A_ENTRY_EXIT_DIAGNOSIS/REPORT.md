# EXP-006A — Entry / Exit Diagnosis Report

Verdict: **ENTRY_VALID_EXIT_FAILURE**

## Scope

- Primary combo: `ENTRY_A_STOP_A_EXIT_B`.
- Shortlisted EXP-006 combos only.
- Source: `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv` read-only.
- True holdout after 2025-07-01 04:00:00 was not used.

## Entry Quality

| scope | horizon_bars | trades | avg_signed_return | avg_mfe_atr | avg_mae_atr | plus1_before_minus1_share | plus2_before_minus1_share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TEMPORAL_TEST | 3 | 18 | 0.0219595 | 1.18999 | -0.8911 | 0.444444 | 0.0555556 |
| TEMPORAL_TEST | 6 | 18 | 0.0176643 | 1.70668 | -1.37048 | 0.555556 | 0.166667 |
| TEMPORAL_TEST | 12 | 18 | 0.00765791 | 2.21053 | -2.06482 | 0.555556 | 0.222222 |
| TEMPORAL_TEST | 24 | 18 | -0.00390089 | 2.58973 | -2.50811 | 0.555556 | 0.222222 |
| TEMPORAL_TEST | 48 | 18 | -0.0389923 | 5.76861 | -5.59998 | 0.555556 | 0.277778 |
| TRAIN | 3 | 39 | 0.00617257 | 1.18712 | -0.878705 | 0.487179 | 0.205128 |
| TRAIN | 6 | 39 | 0.00213594 | 1.49063 | -1.46459 | 0.538462 | 0.282051 |
| TRAIN | 12 | 39 | 0.0169238 | 2.46966 | -1.86173 | 0.538462 | 0.384615 |
| TRAIN | 24 | 39 | 0.0235976 | 3.42269 | -2.45714 | 0.538462 | 0.435897 |
| TRAIN | 48 | 39 | 0.00289619 | 4.20809 | -3.62183 | 0.538462 | 0.435897 |

## Failure Mix

| scope | n | BAD_ENTRY | GOOD_ENTRY_BAD_EXIT | LATE_ENTRY | EARLY_EXIT | LATE_EXIT | STOP_TOO_TIGHT | REGIME_FAILURE | MIXED |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TEMPORAL_TEST | 18 | 0 | 0.444444 | 0.222222 | 0.111111 | 0.166667 | 0 | 0 | 0.0555556 |
| TRAIN | 39 | 0.102564 | 0.435897 | 0 | 0.128205 | 0.102564 | 0 | 0 | 0.230769 |

## Environment

| scope | atr14_median | atr14_iqr | share_above_ema200 | ema27_crosses | ema200_crosses | avg_bull_regime_bars | avg_bear_regime_bars | avg_transition_regime_bars | transition_share | avg_directional_run_bars | avg_pullback_depth_atr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TRAIN | 0.00871429 | 0.00813393 | 0.459418 | 362 | 104 | 42.2667 | 44.1667 | 5.60606 | 0.114622 | 1.87852 | 1.75562 |
| TEMPORAL_TEST | 0.0212929 | 0.0136429 | 0.300259 | 127 | 52 | 17.1765 | 53 | 4.03226 | 0.107852 | 2.01045 | 1.51703 |

## Stop Diagnosis

| scope | pairs | stop_a_premature | stop_b_increased_loss | avg_return_diff_b_minus_a |
| --- | --- | --- | --- | --- |
| TEMPORAL_TEST | 19 | 0.0526316 | 0.157895 | 0.00263429 |
| TRAIN | 39 | 0.0512821 | 0.153846 | -0.00216631 |

## Exit Diagnosis

| scope | net_return_ENTRY_A_STOP_A_EXIT_A | net_return_ENTRY_A_STOP_A_EXIT_B |
| --- | --- | --- |
| TEMPORAL_TEST | -0.0070472 | -0.00392285 |
| TRAIN | 0.0182515 | 0.0310611 |

## Answers

1. ENTRY_A on TEMPORAL TEST: 24-bar average signed return `-0.0039`, average MFE `2.59` ATR. Entry had some favorable path, but it was weaker than TRAIN.
2. +1 ATR before -1 ATR: TRAIN `53.8%`, TEST `55.6%` on 24 bars.
3. BAD_ENTRY share: TRAIN `10.3%`, TEST `0.0%`.
4. GOOD_ENTRY_BAD_EXIT share: TRAIN `43.6%`, TEST `44.4%`.
5. MFE giveback: TRAIN `131.4%`, TEST `147.3%`.
6. EXIT_A vs EXIT_B: see `exit_diagnosis.csv`; no new exit is selected here.
7. STOP_A vs STOP_B: see `stop_diagnosis.csv`; no-stop and stop differences are diagnostic only.
8. TEST trendiness worsened: `False`.
9. LONG/SHORT differences are in `train_test_failure_comparison.csv` groups `direction:*`.
10. Regime differences are in `train_test_failure_comparison.csv` groups `entry_regime:*`.
11. Main source of failure: `ENTRY_VALID_EXIT_FAILURE`.
12. Continue branch: only with the diagnosed cause, no immediate new rules.
13. Next experiment: follow the verdict category only; do not invent a new entry now.

## Artifacts

- `artifacts/trade_path_metrics.csv`
- `artifacts/fixed_horizon_outcomes.csv`
- `artifacts/oracle_exit_analysis.csv`
- `artifacts/failure_classification.csv`
- `artifacts/train_test_failure_comparison.csv`
- `artifacts/regime_environment_comparison.csv`
- `artifacts/stop_diagnosis.csv`
- `artifacts/exit_diagnosis.csv`
- `artifacts/entry_quality_train_vs_test.png`
- `artifacts/failure_types_train_vs_test.png`
- `artifacts/mfe_giveback_train_vs_test.png`
- `artifacts/regime_comparison.png`
- `artifacts/EMA_CYCLE_DIAGNOSIS_REVIEW.pine`
- `artifacts/EMA_CYCLE_DIAGNOSIS_OVERVIEW.pdf`
