# EXP-008 — Major Move Entry Labeling

## Goal

Build a reference visual labeling of proper and improper entry locations inside major ADAUSDT 4H movements for
2023-07-01 00:00 UTC -> 2024-12-31 23:59 UTC.

This experiment must not generate automatic trades. It is a qualitative labeling pass after EXP-007 showed that
EMA27 relative to EMA200 can describe direction, but EMA27 pullbacks can create late and repeated entries inside
mature movements.

## Data

- Asset: ADAUSDT
- Timeframe: 4H
- Source: `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv` read-only
- Indicators allowed: EMA27, EMA200, ATR14 for normalized distances only
- Do not use data after 2024-12-31.

## Stages

1. Retrospectively mark a limited set of major directional movements. Do not use the old 50 local movements as
   boundaries. If more than 20 movements are found, stop and treat the map as too local.
2. Split each major movement into reference zones:
   - `ZONE_0_BEFORE_MOVE`
   - `ZONE_1_BIRTH`
   - `ZONE_2_FIRST_PULLBACK`
   - `ZONE_3_EARLY_CONTINUATION`
   - `ZONE_4_MATURE_MOVE`
   - `ZONE_5_LATE_MOVE`
   - `ZONE_6_EXHAUSTION_OR_CHOP`
3. Mark no more than one `PRIMARY_ENTRY`, one `OPTIONAL_SECONDARY_ENTRY`, and three `BLOCKED_EXAMPLES` per
   movement.
4. Compare early approved entry labels with blocked examples using only observed EMA and price-context fields.
5. Map existing EXP-007 signals into the major-move labels for diagnosis only. Do not recompute trades or PnL.

## Required Artifacts

- `REPORT.md`
- `experiment_008.py`
- `artifacts/major_moves.csv`
- `artifacts/move_zones.csv`
- `artifacts/approved_entries.csv`
- `artifacts/blocked_entries.csv`
- `artifacts/exp007_signals_mapped_to_moves.csv`
- `artifacts/good_vs_blocked_features.csv`
- `artifacts/one_entry_per_move_diagnosis.csv`
- `artifacts/EXP008_MAJOR_MOVE_ENTRY_LABELS.pine`
- `artifacts/EXP008_MAJOR_MOVE_ENTRY_OVERVIEW.pdf`

## Required Answers

REPORT.md must answer:

1. How many major movements were found.
2. How many `PRIMARY_ENTRY` labels were marked.
3. How many `OPTIONAL_SECONDARY_ENTRY` labels were marked.
4. How many `BLOCKED_EXAMPLES` were marked.
5. How many EXP-007 signals occurred inside one major movement.
6. What share of EXP-007 signals appeared in mature or late phases.
7. How early approved entries differ from late blocked examples.
8. Whether EMA27/EMA200 is enough to determine direction.
9. What is missing to determine entry timing.
10. Whether the rule "maximum one primary entry per major movement" works as a reference constraint.
11. Whether one causal start detector can already be formulated.
12. Which cases remain ambiguous.

## Verdict

One of:

- `ENTRY_LABEL_STRUCTURE_FOUND`
- `PARTIAL_ENTRY_STRUCTURE`
- `NO_COMMON_ENTRY_STRUCTURE`
- `GLOBAL_MOVE_BOUNDARIES_AMBIGUOUS`
- `DATA_INSUFFICIENT`

## Restrictions

- Do not calculate PnL.
- Do not build a strategy.
- Do not use 2025-2026.
- Do not add indicators beyond EMA27, EMA200, ATR14.
- Do not change EMA27/EMA200.
- Do not modify Irobot.
- Do not modify `docs/DEFINITIONS.md`.
- Do not generate mass trades.
- Maximum two approved entry labels per major movement.
