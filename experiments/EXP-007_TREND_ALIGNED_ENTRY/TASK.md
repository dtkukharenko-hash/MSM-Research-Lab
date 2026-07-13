# EXP-007 — Trend-Aligned EMA Entry

## Goal

Learn whether entry quality improves when trades are allowed only in the direction of the higher EMA context.

Key rule:

- EMA27 below EMA200 means SHORT context only.
- EMA27 above EMA200 means LONG context only.
- If EMA27 is close to EMA200, crosses often, EMA200 is flat, or price is between EMA27 and EMA200, entries are blocked.

The consumed 2025-07-01 -> 2026-07-01 holdout must not be used for rule choice, visual selection, or repair.

## Data

- Asset: ADAUSDT
- Timeframe: 4H
- Source: `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv` read-only
- Development period: 2023-07-01 00:00 UTC -> 2024-06-30 23:59 UTC
- Validation period: 2024-07-01 00:00 UTC -> 2024-12-31 23:59 UTC

Do not use data after 2024-12-31.

## Fixed Components

Do not change:

- STOP_A
- EXIT_R5
- costs
- one position at a time
- sequential simulation
- next-open execution
- no leverage
- no pyramiding
- EMA27 / EMA200

## Hypothesis

H-ENTRY-ALIGNMENT:

Entries should only occur in the direction of EMA27 relative to EMA200.

## Context Gate

SHORT_CONTEXT:

- EMA27 < EMA200
- EMA200 slope_20 < 0
- close < EMA200
- ema_distance_atr >= 0.25
- crossings_last30 <= 1
- price not between EMA27 and EMA200

LONG_CONTEXT:

- EMA27 > EMA200
- EMA200 slope_20 > 0
- close > EMA200
- ema_distance_atr >= 0.25
- crossings_last30 <= 1
- price not between EMA27 and EMA200

All other bars are BLOCK_CONTEXT.

## Compared Entries

Compare exactly:

- ENTRY_A baseline from EXP-006
- ENTRY_T1: EMA27 trend retake after pullback
- ENTRY_T2: pullback and confirmation
- ENTRY_T3: pullback then break
- ENTRY_T4: EMA27 hold after pullback

All variants use STOP_A + EXIT_R5.

## Split

On DEVELOPMENT:

- test all five entries;
- choose at most two candidates.

On VALIDATION:

- run only selected candidates;
- do not change rules;
- do not add filters.

## Required Artifacts

- `REPORT.md`
- `experiment_007.py`
- `artifacts/all_entry_signals.csv`
- `artifacts/all_entry_trades.csv`
- `artifacts/development_metrics.csv`
- `artifacts/selected_entries.csv`
- `artifacts/validation_metrics.csv`
- `artifacts/validation_trades.csv`
- `artifacts/context_blocks.csv`
- `artifacts/late_entry_blocks.csv`
- `artifacts/chop_blocks.csv`
- `artifacts/entry_quality.csv`
- `artifacts/fixed_horizon_outcomes.csv`
- `artifacts/cost_stress.csv`
- `artifacts/concentration_checks.csv`
- `artifacts/entry_distance_analysis.csv`
- `artifacts/entry_comparison.png`
- `artifacts/mfe_mae_comparison.png`
- `artifacts/context_distribution.png`
- `artifacts/EXP007_TREND_ENTRY_REVIEW.pine`
- `artifacts/EXP007_TREND_ENTRY_OVERVIEW.pdf`

## Verdict

One of:

- TREND_ALIGNED_ENTRY_FOUND
- SHORT_ENTRY_FOUND_LONG_WEAK
- LONG_ENTRY_FOUND_SHORT_WEAK
- ENTRY_FILTERS_HELP_BUT_WEAK
- NO_STABLE_ENTRY
- DATA_INSUFFICIENT

## Restrictions

- Do not inspect or tune on the consumed holdout.
- Do not change exits, stops, EMA periods, or costs.
- Do not add new entry variants after results.
- Do not use ML.
- Do not use ZigZag.
- Do not optimize parameters.
- Do not change Irobot.
- Do not change `docs/DEFINITIONS.md`.
