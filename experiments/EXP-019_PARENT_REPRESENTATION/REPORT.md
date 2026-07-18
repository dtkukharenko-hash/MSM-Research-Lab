# EXP-019 — Parent representation

Status: PARENT_REPRESENTATION_PARTIAL

## Hypothesis and causal scope

Multiple predeclared causal origins may restore upstream parent variability before `ChildCounterMotion`. This is a descriptive structural audit, not a predictive claim. Every representation ends on the last completed 4H bar strictly before counter start; no future pivots, returns, labels, or chart selection are used.

## Reconstruction

The executable independently reconstructs and identity-asserts EXP-014's 425 factor-1.0 BASE rows and EXP-015's 369 boundary-preserved rows.

## Representation audit

- FIXED_8: valid 425/425; invalid 0; age q25/q50/q75 8.0/8.0/8.0; cap-hit 0.000.
- DIRECTION_RUN: valid 425/425; invalid 0; age q25/q50/q75 1.0/2.0/3.0; cap-hit 0.000.
- ATR_ORIGIN: valid 391/425; invalid 34; age q25/q50/q75 4.0/6.0/9.0; cap-hit 0.002.
- CONFIRMED_DIRECTION_CHANGE: valid 423/425; invalid 2; age q25/q50/q75 4.0/6.0/8.0; cap-hit 0.000.
- HYBRID_ORIGIN: valid 391/425; invalid 34; age q25/q50/q75 1.0/2.0/3.0; cap-hit 0.002.

`parent_representations.csv` preserves invalidity, minimum-history, cap-hit, zero-denominator, and origin reasons. Pairwise rank correlations are recorded from finite paired source rows: FIXED_8:age_bars/displacement_atr=undefined; FIXED_8:age_bars/efficiency=undefined; FIXED_8:age_bars/distance_to_boundary_atr=undefined; FIXED_8:age_bars/distance_from_extreme_atr=undefined; FIXED_8:displacement_atr/efficiency=0.978; FIXED_8:displacement_atr/distance_to_boundary_atr=0.807; FIXED_8:displacement_atr/distance_from_extreme_atr=-0.224; FIXED_8:efficiency/distance_to_boundary_atr=0.755; FIXED_8:efficiency/distance_from_extreme_atr=-0.289; FIXED_8:distance_to_boundary_atr/distance_from_extreme_atr=-0.312; DIRECTION_RUN:age_bars/displacement_atr=0.907; DIRECTION_RUN:age_bars/efficiency=0.827; DIRECTION_RUN:age_bars/distance_to_boundary_atr=0.848; DIRECTION_RUN:age_bars/distance_from_extreme_atr=-0.279; DIRECTION_RUN:displacement_atr/efficiency=0.961; DIRECTION_RUN:displacement_atr/distance_to_boundary_atr=0.931; DIRECTION_RUN:displacement_atr/distance_from_extreme_atr=-0.328; DIRECTION_RUN:efficiency/distance_to_boundary_atr=0.876; DIRECTION_RUN:efficiency/distance_from_extreme_atr=-0.409; DIRECTION_RUN:distance_to_boundary_atr/distance_from_extreme_atr=-0.350; ATR_ORIGIN:age_bars/displacement_atr=-0.123; ATR_ORIGIN:age_bars/efficiency=-0.891; ATR_ORIGIN:age_bars/distance_to_boundary_atr=-0.025; ATR_ORIGIN:age_bars/distance_from_extreme_atr=0.537; ATR_ORIGIN:displacement_atr/efficiency=0.377; ATR_ORIGIN:displacement_atr/distance_to_boundary_atr=0.617; ATR_ORIGIN:displacement_atr/distance_from_extreme_atr=0.010; ATR_ORIGIN:efficiency/distance_to_boundary_atr=0.110; ATR_ORIGIN:efficiency/distance_from_extreme_atr=-0.629; ATR_ORIGIN:distance_to_boundary_atr/distance_from_extreme_atr=0.066; CONFIRMED_DIRECTION_CHANGE:age_bars/displacement_atr=0.217; CONFIRMED_DIRECTION_CHANGE:age_bars/efficiency=-0.224; CONFIRMED_DIRECTION_CHANGE:age_bars/distance_to_boundary_atr=0.308; CONFIRMED_DIRECTION_CHANGE:age_bars/distance_from_extreme_atr=0.292; CONFIRMED_DIRECTION_CHANGE:displacement_atr/efficiency=0.776; CONFIRMED_DIRECTION_CHANGE:displacement_atr/distance_to_boundary_atr=0.849; CONFIRMED_DIRECTION_CHANGE:displacement_atr/distance_from_extreme_atr=-0.268; CONFIRMED_DIRECTION_CHANGE:efficiency/distance_to_boundary_atr=0.568; CONFIRMED_DIRECTION_CHANGE:efficiency/distance_from_extreme_atr=-0.420; CONFIRMED_DIRECTION_CHANGE:distance_to_boundary_atr/distance_from_extreme_atr=-0.185; HYBRID_ORIGIN:age_bars/displacement_atr=0.835; HYBRID_ORIGIN:age_bars/efficiency=0.747; HYBRID_ORIGIN:age_bars/distance_to_boundary_atr=0.788; HYBRID_ORIGIN:age_bars/distance_from_extreme_atr=-0.268; HYBRID_ORIGIN:displacement_atr/efficiency=0.953; HYBRID_ORIGIN:displacement_atr/distance_to_boundary_atr=0.934; HYBRID_ORIGIN:displacement_atr/distance_from_extreme_atr=-0.317; HYBRID_ORIGIN:efficiency/distance_to_boundary_atr=0.865; HYBRID_ORIGIN:efficiency/distance_from_extreme_atr=-0.424; HYBRID_ORIGIN:distance_to_boundary_atr/distance_from_extreme_atr=-0.341.

## Structural comparison and controls

`representation_comparison.csv` contains deterministic full-source quartiles for age, displacement, efficiency, and boundary distance; support, rates, boundary subgroup support, matched-control contrasts, UP/DOWN and chronological-third cells, collapse/concentration flags, and deterministic equal-support FIXED_8 comparisons. Controls are source-excluded, non-overlapping, deterministic, and retain explicit mismatch fields.

## Stability and counterexamples

Actual detector runs at 0.8, 1.0, and 1.2 are in `parameter_stability.csv`. `counterexamples.csv` retains causal disagreement, invalidity/cap, and direction-reversal disclosures.

## Verdict

**PARENT_REPRESENTATION_PARTIAL** — the alternatives restore non-degenerate age/origin variability where valid, but invalidity/cap disclosures and direction/time contrast variation limit evidence of stable independent separation. No representation is selected from outcome statistics.
