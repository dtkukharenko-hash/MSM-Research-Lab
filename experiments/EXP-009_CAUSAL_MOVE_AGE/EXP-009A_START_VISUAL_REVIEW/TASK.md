# EXP-009A — START Visual Review

## Goal

Visually audit fixed EXP-009 `START_A`, `START_B`, and `START_C` against the 12 EXP-008 reference moves.

## Restrictions

- Do not create a new detector.
- Do not calculate PnL.
- Do not use stop or exit logic.
- Do not change parameters.
- Do not choose a detector from one aggregate metric.
- Do not use 2025-2026 data.
- Do not modify Irobot.
- Do not modify `docs/DEFINITIONS.md`.

## Inputs

Use existing EXP-008/EXP-009 artifacts plus read-only ADAUSDT 4H OHLC from Irobot for charting and descriptive closed-bar facts.

## Required Artifacts

- `REPORT.md`
- `artifacts/start_visual_audit.csv`
- `artifacts/missed_move_analysis.csv`
- `artifacts/false_active_move_analysis.csv`
- `artifacts/first_observable_changes.csv`
- `artifacts/observable_change_summary.csv`
- `artifacts/EXP009A_START_REVIEW.pine`
- `artifacts/EXP009A_START_REVIEW.pdf`
