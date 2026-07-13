# EXP-007 — Trend-Aligned EMA Entry

## Scope

ADAUSDT 4H, development 2023-07-01 -> 2024-06-30, validation 2024-07-01 -> 2024-12-31. Data after 2024-12-31 was not used. The consumed 2025-2026 holdout was not opened.

## Selected Entries

| entry_variant | selection_rank | selection_reason |
| --- | --- | --- |
| ENTRY_T1 | 1 | fixed predeclared score on DEVELOPMENT only |
| ENTRY_T4 | 2 | fixed predeclared score on DEVELOPMENT only |

## Development Metrics

| entry_variant | signals | executed_trades | blocked_by_context | blocked_by_late_entry | blocked_by_chop | long_trades | short_trades | profit_factor | total_return | max_drawdown | win_rate | average_trade | median_trade | average_mfe | average_mae | median_mfe | median_mae | mfe_3b | mfe_6b | mfe_12b | mfe_24b | mae_3b | mae_6b | mae_12b | mae_24b | plus1_before_minus1 | plus2_before_minus1 | bad_entry_share | late_entry_share | good_entry_bad_exit_share | stop_out_rate | average_distance_to_ema27_at_entry | average_move_already_completed_before_entry | top1_profit_share | result_without_top1 | cost_mult |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENTRY_A | 62 | 12 | 1 | 38 | 33 | 6 | 6 | 1.11283 | 0.00889378 | -0.0892607 | 0.416667 | 0.00130463 | -0.0113219 | 1.29482 | -0.922939 | 0.483885 | -0.823931 | 1.07392 | 1.31618 | 1.4018 | 1.90401 | -0.75132 | -1.03096 | -2.05954 | -2.45369 | 0.416667 | 0.333333 | 0.583333 | 0 | 0 | 0.416667 | 0.140632 | -0.823915 | 0.648091 | -0.0828803 | 1 |
| ENTRY_T1 | 376 | 60 | 0 | 71 | 220 | 23 | 37 | 1.76127 | 0.421369 | -0.143849 | 0.466667 | 0.00792109 | -0.00500848 | 1.9808 | -0.804985 | 1.09361 | -0.606973 | 1.03362 | 1.4934 | 2.51909 | 3.72814 | -0.750175 | -1.23548 | -1.90077 | -2.62021 | 0.6 | 0.466667 | 0.466667 | 0 | 0.0333333 | 0.4 | 0.474377 | -0.207849 | 0.472459 | -0.0645818 | 1 |
| ENTRY_T2 | 295 | 57 | 0 | 76 | 153 | 20 | 37 | 1.5042 | 0.252445 | -0.143849 | 0.438596 | 0.00612244 | -0.00458222 | 2.04342 | -0.950311 | 1.03078 | -0.787237 | 0.899973 | 1.3629 | 1.95096 | 3.35395 | -0.784419 | -1.32761 | -2.06961 | -2.96323 | 0.508772 | 0.403509 | 0.473684 | 0 | 0.0350877 | 0.350877 | 0.726525 | 0.206862 | 0.498252 | -0.175339 | 1 |
| ENTRY_T3 | 12 | 1 | 0 | 10 | 9 | 0 | 1 | 999 | 0.00602491 | 0 | 1 | 0.00602491 | 0.00602491 | 1.69089 | -0.103158 | 1.69089 | -0.103158 | 1.69089 | 1.69089 | 1.69089 | 1.69089 | -0.103158 | -0.84 | -2.98645 | -6.25419 | 1 | 0 | 0 | 0 | 0 | 0 | 1.11576 | 0.736842 | 1 | 0 | 1 |
| ENTRY_T4 | 176 | 35 | 0 | 46 | 94 | 13 | 22 | 1.83632 | 0.304762 | -0.173763 | 0.457143 | 0.0109378 | -0.00826679 | 2.24755 | -1.03548 | 0.825149 | -0.89615 | 0.823386 | 1.15994 | 1.92023 | 3.30085 | -0.940552 | -1.31323 | -2.16985 | -2.84141 | 0.485714 | 0.371429 | 0.514286 | 0 | 0 | 0.4 | 0.804233 | 0.358121 | 0.617126 | -0.140892 | 1 |

## Validation Metrics

| entry_variant | signals | executed_trades | blocked_by_context | blocked_by_late_entry | blocked_by_chop | long_trades | short_trades | profit_factor | total_return | max_drawdown | win_rate | average_trade | median_trade | average_mfe | average_mae | median_mfe | median_mae | mfe_3b | mfe_6b | mfe_12b | mfe_24b | mae_3b | mae_6b | mae_12b | mae_24b | plus1_before_minus1 | plus2_before_minus1 | bad_entry_share | late_entry_share | good_entry_bad_exit_share | stop_out_rate | average_distance_to_ema27_at_entry | average_move_already_completed_before_entry | top1_profit_share | result_without_top1 | cost_mult |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENTRY_T1 | 183 | 23 | 0 | 28 | 118 | 12 | 11 | 0.645132 | -0.113696 | -0.166281 | 0.304348 | -0.0047908 | -0.010966 | 1.3287 | -0.729641 | 0.658485 | -0.648577 | 0.788443 | 1.14709 | 1.98533 | 2.82272 | -0.757143 | -1.10603 | -1.52708 | -2.04754 | 0.434783 | 0.26087 | 0.608696 | 0 | 0.0869565 | 0.478261 | 0.476164 | -0.0566604 | 0.502636 | -0.194772 | 1 |
| ENTRY_T4 | 74 | 13 | 0 | 20 | 41 | 7 | 6 | 0.768434 | -0.0845305 | -0.215756 | 0.307692 | -0.00544749 | -0.0188122 | 2.03273 | -0.778498 | 0.676988 | -0.718143 | 1.21605 | 1.76978 | 2.37694 | 2.87405 | -0.711483 | -1.12252 | -1.26252 | -2.33167 | 0.461538 | 0.384615 | 0.615385 | 0 | 0.0769231 | 0.384615 | 0.72251 | 0.231656 | 0.390278 | -0.16144 | 1 |

## Required Answers

1. Baseline ENTRY_A raw signals against strict EMA context: 1.
2. Directional gate blocked 1 candidate signals.
3. LATE_ENTRY_BLOCK blocked 289; CHOP_BLOCK blocked 668.
4. Best SHORT_CONTEXT entry on development: ENTRY_T1.
5. Best LONG_CONTEXT entry on development: ENTRY_T4.
6. Bad-entry reduction is assessed in `entry_quality.csv`; selected entries are compared to gated ENTRY_A.
7. Late entries are blocked before execution by the fixed LATE_ENTRY_BLOCK.
8. +1 ATR before -1 ATR is reported in development and validation metrics.
9. PF and DD are reported in development and validation metrics.
10. Validation transfer is summarized by the verdict below.
11. LONG/SHORT symmetry remains limited if one side has a small sample.
12. Candidate entries: ENTRY_T1, ENTRY_T4.
13. Next experiment should visually review selected entry failures before any new holdout.
14. Research can continue without new holdout as long as it remains on 2023-2024 or other non-consumed research data.

## Verdict

NO_STABLE_ENTRY
