# EXP-017 — Phase geometry

Status: PHASE_GEOMETRY_REJECTED

## Hypothesis

Dimensionless, direction-aware relations across completed parent, counter, balance, and reassertion phases add descriptive structural separation beyond the fixed EXP-015 boundary-only population.

## Data and causal method

The EXP-014 detector is reconstructed exactly, EXP-015 strict boundary membership is independently rebuilt and asserted at **369** rows, and committed EXP-016 balance fields are asserted by interval ID. Parent magnitude/duration use the eight completed bars before counter start; counter uses the first three completed child bars; committed balance is the penultimate completed child bar; reassertion uses the final completed child bar. No future bar, pivot, return, outcome label, or chart interpretation is used.

## Ratio audit

- counter_parent_ratio: finite=369/369, q25=0.16972367794188023, q50=0.4330097562053312, q75=0.9659767605203504, UP=166, DOWN=203
- balance_counter_ratio: finite=366/369, q25=1.144115713346486, q50=2.181928395914148, q75=4.692803970223319, UP=165, DOWN=201
- reassertion_counter_ratio: finite=366/369, q25=1.0606757880949378, q50=2.0958596324084118, q75=4.393149090295962, UP=165, DOWN=201
- reassertion_parent_ratio: finite=369/369, q25=0.47091020226717256, q50=0.8108565202646255, q75=1.775077693370175, UP=166, DOWN=203
- counter_speed_ratio: finite=369/369, q25=0.4525964745116806, q50=1.1546926832142166, q75=2.575938028054268, UP=166, DOWN=203
- reassertion_counter_speed_ratio: finite=366/369, q25=3.182027364284813, q50=6.287578897225235, q75=13.179447270887888, UP=165, DOWN=201
- balance_time_ratio: finite=369/369, q25=0.3333333333333333, q50=0.3333333333333333, q75=0.3333333333333333, UP=166, DOWN=203
- transition_symmetry: finite=366/369, q25=0.38967582008175905, q50=0.6746001820747825, q75=1.1967100650493052, UP=165, DOWN=201

Zero, non-positive, missing and logarithm-invalid denominators are retained and flagged in `phase_geometry.csv`; no constants replace them. Balance and reassertion duration are mechanically one under the committed detector and are explicitly retained as redundant. Fixed full-source quartiles and fixed unity bands are in `geometry_comparison.csv`; deterministic chronological thirds are exhaustive in `time_segment_summary.csv`.

## Controls and stability

Every comparison has deterministic same-archive controls excluding all source detections and the EXP-013 interval, with non-overlap assertion and explicit direction, age, duration, ATR, range and time mismatch fields in `matched_controls.csv`. Support-size boundary subsets are included for each comparison. Actual detector calls at factors 0.8, 1.0 and 1.2 are recorded in `parameter_stability.csv`.

## Verdict

**PHASE_GEOMETRY_REJECTED** — predeclared geometry relations are descriptive measurements, but none is promoted: any aggregate contrast must survive support-size, direction, chronological-third and factor checks, all of which remain reported rather than inferred. The largest support-size incremental contrast is counter_parent_ratio_Q1 (0.000000); it is not a selected threshold or predictive claim.

## Files produced

This report and all seven CSV files regenerate deterministically from `experiment_017.py`.

Pairwise stable-rank correlations: counter_parent_ratio~balance_counter_ratio=-0.602, counter_parent_ratio~reassertion_counter_ratio=-0.599, counter_parent_ratio~reassertion_parent_ratio=0.611, counter_parent_ratio~counter_speed_ratio=1.000, counter_parent_ratio~reassertion_counter_speed_ratio=-0.599, counter_parent_ratio~balance_time_ratio=0.007, counter_parent_ratio~transition_symmetry=0.090, balance_counter_ratio~reassertion_counter_ratio=0.853, balance_counter_ratio~reassertion_parent_ratio=0.046, balance_counter_ratio~counter_speed_ratio=-0.602, balance_counter_ratio~reassertion_counter_speed_ratio=0.853, balance_counter_ratio~balance_time_ratio=0.045, balance_counter_ratio~transition_symmetry=-0.015, reassertion_counter_ratio~reassertion_parent_ratio=0.169, reassertion_counter_ratio~counter_speed_ratio=-0.599, reassertion_counter_ratio~reassertion_counter_speed_ratio=1.000, reassertion_counter_ratio~balance_time_ratio=0.030, reassertion_counter_ratio~transition_symmetry=-0.018, reassertion_parent_ratio~counter_speed_ratio=0.611, reassertion_parent_ratio~reassertion_counter_speed_ratio=0.169, reassertion_parent_ratio~balance_time_ratio=0.027, reassertion_parent_ratio~transition_symmetry=-0.049, counter_speed_ratio~reassertion_counter_speed_ratio=-0.599, counter_speed_ratio~balance_time_ratio=0.007, counter_speed_ratio~transition_symmetry=0.090, reassertion_counter_speed_ratio~balance_time_ratio=0.030, reassertion_counter_speed_ratio~transition_symmetry=-0.018, balance_time_ratio~transition_symmetry=0.081.
