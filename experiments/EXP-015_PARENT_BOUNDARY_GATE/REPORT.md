# EXP-015 — Parent boundary gate

Status: BOUNDARY_GATE_PARTIAL

## Hypothesis

Preserving the established direction-aware parent invalidation boundary through a closed-bar child reassertion is a necessary structural gate for the fixed EXP-014 transition.

## Data and causal constraints

ADAUSDT is the only available local archive. Completed 4H UTC bars are rebuilt from the existing 1H archive through the committed EXP-014 detector conventions. The original EXP-013 interval is excluded by assertion. All predicates use only bars complete at reassertion; no pivots, future bars, returns, outcome labels, or chart interpretation are used.

## Method and controls

BASE and four executable boundary predicates are evaluated at factor 1.0 before rows are compared. `BOUNDARY_MARGIN` uses the predeclared 0.1 ATR default; 0.0, 0.1, 0.2, and 0.3 ATR are separately rerun at factors 0.8, 1.0, and 1.2. Controls are deterministic, source-excluded, non-overlapping with every base detection, and matched on their own parent direction, duration, parent age, reassertion ATR, and nearest feasible time location; all residual mismatches are explicit.

## Results

BASE has 425 rows. Preservation through reassertion retains 369 (0.868), removes 56 of 56 diagnostic rows, and has paired rank contrast 0.219512 versus BASE 0.204706. It retains 166 UP and 203 DOWN rows. The margin thresholds produce the reported actual-run support and contrasts in `parameter_stability.csv`; chronological, exhaustive row thirds and direction splits are in `time_segment_summary.csv`.

## Verdict

**BOUNDARY_GATE_PARTIAL** — preservation through balance removes all documented boundary-failure diagnostics without collapsing support, but the separation improvement is modest and the fixed margin adds no discriminating reduction in this archive. The result is descriptive and remains limited to one instrument.

## Files produced

`gated_detections.csv`, `matched_controls.csv`, `gate_comparison.csv`, `parameter_stability.csv`, `time_segment_summary.csv`, and `counterexamples.csv` are generated deterministically by `experiment_015.py`.
