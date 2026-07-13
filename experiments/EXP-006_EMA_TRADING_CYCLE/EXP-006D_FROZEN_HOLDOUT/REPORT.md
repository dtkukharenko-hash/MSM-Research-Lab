# EXP-006D — Frozen Holdout Report

Verdict: **HOLDOUT_REJECTED**

Frozen specification hash: `8068360398844bfcc47614cd5e1d6806bf94bbfe2d7f3e9224feeba1f3f9cee2`

## Boundary

- Holdout: 2025-07-01 04:00:00 -> 2026-07-01 00:00:00.
- System: `ENTRY_A + STOP_A + EXIT_R5`.
- This holdout is now consumed for this branch and must not be reused as an independent tuning set.

## Primary EXIT_R5 Metrics

| trades | long_trades | short_trades | win_rate | profit_factor | total_return | max_drawdown | final_equity | median_mfe_capture | good_entry_bad_exit_share | top1_profit_share | top3_profit_share | return_without_top1 | return_without_top3 | longest_losing_streak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 31 | 4 | 27 | 0.483871 | 0.655734 | -0.105988 | -0.142319 | 894.012 | 0.00789083 | 0 | 0.230753 | 0.484529 | -0.145776 | -0.187907 | 3 |

## Exit Comparison

| exit_variant | trades | profit_factor | total_return | max_drawdown | median_mfe_capture | good_entry_bad_exit_share | return_without_top1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EXIT_R0 | 26 | 1.27226 | 0.0672476 | -0.312278 | -0.821875 | 0.307692 | -0.180194 |
| EXIT_R2 | 28 | 0.867577 | -0.0546102 | -0.148801 | 0.143082 | 0 | -0.107003 |
| EXIT_R5 | 31 | 0.655734 | -0.105988 | -0.142319 | 0.00789083 | 0 | -0.145776 |

## Cost Stress

| exit_variant | cost_mult | trades | profit_factor | total_return | max_drawdown |
| --- | --- | --- | --- | --- | --- |
| EXIT_R5 | 1 | 31 | 0.655734 | -0.105988 | -0.142319 |
| EXIT_R5 | 2 | 31 | 0.508828 | -0.159984 | -0.18608 |
| EXIT_R5 | 3 | 31 | 0.391581 | -0.210819 | -0.22769 |

## Direction Metrics

| direction | trades | profit_factor | total_return | max_drawdown | median_mfe_capture | pf_cost_x2 |
| --- | --- | --- | --- | --- | --- | --- |
| LONG | 4 | 0.817016 | -0.00733833 | -0.0168402 | -0.347889 | 0.638819 |
| SHORT | 27 | 0.633844 | -0.099379 | -0.127628 | 0.00789083 | 0.491225 |

## Quarterly Metrics

| quarter | trades | sample_flag | profit_factor | total_return | max_drawdown | pf_cost_x2 | long_trades | short_trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-Q3 | 3 | LOW_SAMPLE | 1.54697 | 0.0104683 | 0 | 1.22374 | 2 | 1 |
| 2025-Q4 | 11 | OK | 1.07466 | 0.00460078 | -0.0581666 | 0.873991 | 1 | 10 |
| 2026-Q1 | 7 | OK | 0.394495 | -0.0577882 | -0.0550665 | 0.306035 | 1 | 6 |
| 2026-Q2_to_2026-07-01 | 10 | OK | 0.259418 | -0.0652864 | -0.0444155 | 0.154767 | 0 | 10 |

## Causality Audit

| check_id | check_name | status | evidence | affected_trades |
| --- | --- | --- | --- | --- |
| C01 | frozen specification written before holdout metrics | PASS | spec_hash=8068360398844bfcc47614cd5e1d6806bf94bbfe2d7f3e9224feeba1f3f9cee2 | 0 |
| C02 | entries execute on next open | PASS | signal_time < entry_time for all trades | 0 |
| C03 | close exits execute on next open | PASS | exit logic returns next open for close-based exits | 0 |
| C04 | MFE bounded by entry to exit window | PASS | MFE updated only while position open | 0 |
| C05 | position occupancy blocks new entries | PASS | skipped_signals=5 | 0 |
| C06 | intrabar ambiguities conservative | PASS | ambiguities=4 stop_priority | 4 |

## Answers

1. Frozen specification: `ENTRY_A + STOP_A + EXIT_R5`, hash `8068360398844bfcc47614cd5e1d6806bf94bbfe2d7f3e9224feeba1f3f9cee2`.
2. Holdout had not been used in EXP-006/006A/006B/006C; EXP-006D consumes it once.
3. Signals: 37.
4. Executed trades with position occupancy: 31.
5. Signals skipped due to open position: 5.
6. EXIT_R5 PF `0.656`, return `-10.60%`, DD `-14.23%`.
7. costs x2 PF `0.509`, costs x3 PF `0.392`.
8. Return without top-1 `-14.58%`, without top-3 `-18.79%`.
9. Top-3 profit share `48.5%`.
10. LONG/SHORT are shown in `direction_metrics.csv`.
11. Quarterly distribution is shown in `quarterly_metrics.csv`.
12. MFE retention is shown in `mfe_capture.csv`.
13. Implementation ambiguities: 4.
14. Ambiguities use conservative stop priority and do not change verdict.
15. Frozen EXIT_R5 result: `HOLDOUT_REJECTED`.
16. Paper trading: not approved by this verdict.
17. Remaining limits: single asset, 4H timeframe, one consumed holdout, no parameter tuning on this result.

## Artifacts

- `artifacts/FROZEN_SPECIFICATION.md`
- `artifacts/frozen_specification.json`
- `artifacts/holdout_signals.csv`
- `artifacts/holdout_trades_r5.csv`
- `artifacts/holdout_metrics.csv`
- `artifacts/causality_audit.csv`
- `artifacts/intrabar_ambiguities.csv`
- `artifacts/HOLDOUT_TRADING_CYCLE_REVIEW.pine`
- `artifacts/HOLDOUT_TRADING_CYCLE_OVERVIEW.pdf`
