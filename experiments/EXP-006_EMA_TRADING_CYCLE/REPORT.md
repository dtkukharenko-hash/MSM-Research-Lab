# EXP-006 — EMA Trading Cycle Report

Verdict: **WEAK_EMA_CYCLE**

## Data Boundary

- Source: `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv` read-only.
- Research rows used: 4387, from 2023-07-01 00:00:00 to 2025-07-01 00:00:00.
- Train: 2023-07-01 00:00:00 -> 2024-12-19 23:59:00.
- Temporal test: 2024-12-20 00:00:00 -> 2025-07-01 00:00:00.
- True holdout from 2025-07-01 04:00:00 was not loaded into the experiment dataframe.
- Costs: fee 0.10% per side and slippage 0.05% per side; stress x2 and x3 are reported separately.
- Causality: all entries and close-based exits are executed on the next open; active references are updated only from closed bars.

## Train Shortlist

| combo_id | trades | profit_factor | total_return | max_drawdown | mfe_capture_ratio | pf_cost_x2 | return_cost_x2 | top1_profit_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENTRY_A_STOP_A_EXIT_B | 39 | 3.74399 | 1.74329 | -0.162226 | -2.28435 | 3.31021 | 1.54158 | 0.379326 |
| ENTRY_A_STOP_B_EXIT_B | 37 | 3.47121 | 1.64391 | -0.188347 | -2.77806 | 3.12096 | 1.45913 | 0.379023 |
| ENTRY_A_STOP_A_EXIT_A | 55 | 2.62888 | 1.20367 | -0.160094 | -5.62002 | 2.28057 | 0.976381 | 0.411887 |

## Temporal Test

| combo_id | trades | profit_factor | total_return | max_drawdown | mfe_capture_ratio | stop_out_rate | regime_flip_exit_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ENTRY_A_STOP_A_EXIT_A | 21 | 0.635924 | -0.153754 | -0.188467 | -4.3139 | 0.47619 | 0 |
| ENTRY_A_STOP_A_EXIT_B | 18 | 0.783693 | -0.0839845 | -0.146538 | -3.65173 | 0.555556 | 0 |
| ENTRY_A_STOP_B_EXIT_B | 18 | 0.670024 | -0.141173 | -0.18744 | -3.8006 | 0.388889 | 0 |

Cost stress for shortlisted temporal-test combinations is stored in `artifacts/cost_stress.csv`.

## Answers

1. Working EMA regime: train trades occurred mainly in explicit EMA regimes; best train combo was `ENTRY_A_STOP_A_EXIT_B`. The regime filter was not enough by itself; transfer is judged by temporal test.
2. Best entry by adverse-move proxy: `ENTRY_A`.
3. Stop that least broke favorable movement by average MFE: `STOP_B`.
4. Exit with highest average MFE capture on train: `EXIT_D`.
5. Active reference candle helped only where reference exits appeared; reference exit counts are in `exit_analysis.csv` and `reference_candles.csv`.
6. Best temporal MFE capture: `-365.17%`.
7. Error location: compare `entry_analysis.csv` for early/late starts and `exit_analysis.csv` for giveback/delay; this run keeps those as descriptive diagnostics, not new rules.
8. LONG/SHORT symmetry: shortlist gating rejected combinations with a complete side conflict; exact side returns are in `train_rankings.csv`.
9. TRAIN passed combinations: 3.
10. Temporal transfer: at least one shortlisted combination was tested.
11. Costs x2/x3: reported in `cost_stress.csv`; shortlist gate required x2 not to destroy train result.
12. Concentration: top-1 profit share and without-top1 return are in `concentration_checks.csv`.
13. Simple working system: allowed only if strong verdict criteria pass; otherwise keep as research-only evidence.
14. Ready for separate holdout test: no, current evidence is not strong enough.
15. Next experiment: if evidence is weak, inspect whether failure is entry timing or exit retention before any holdout; do not open true holdout yet.

## Top 3 Train Ranking Rows

| combo_id | passes_train_gate | trades | profit_factor | total_return | max_drawdown | mfe_capture_ratio | rank_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ENTRY_A_STOP_A_EXIT_B | True | 39 | 3.74399 | 1.74329 | -0.162226 | -2.28435 | 6.13703 |
| ENTRY_A_STOP_B_EXIT_B | True | 37 | 3.47121 | 1.64391 | -0.188347 | -2.77806 | 5.65773 |
| ENTRY_A_STOP_A_EXIT_A | True | 55 | 2.62888 | 1.20367 | -0.160094 | -5.62002 | 4.08454 |

## Artifacts

- `artifacts/trades_all_combinations.csv`
- `artifacts/combination_metrics.csv`
- `artifacts/train_rankings.csv`
- `artifacts/shortlist.csv`
- `artifacts/temporal_test_metrics.csv`
- `artifacts/temporal_test_trades.csv`
- `artifacts/entry_analysis.csv`
- `artifacts/exit_analysis.csv`
- `artifacts/reference_candles.csv`
- `artifacts/cost_stress.csv`
- `artifacts/concentration_checks.csv`
- `artifacts/equity_curves.png`
- `artifacts/entry_comparison.png`
- `artifacts/exit_comparison.png`
- `artifacts/mfe_capture.png`
- `artifacts/EMA_TRADING_CYCLE_REVIEW.pine`
- `artifacts/EMA_TRADING_CYCLE_OVERVIEW.pdf`
