# Current Codex Task

- task_id: `EXP-018-PARENT-STATE`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-017-PHASE-GEOMETRY`
- commit_message: `EXP-018 parent state`

## Objective

Test whether the causal state of the established parent movement immediately before `ChildCounterMotion` contains stable structural information that was missed by the rejected phase-filter and phase-geometry branches.

EXP-015 established a useful but weak parent-boundary gate. EXP-016 rejected isolated balance quality, and EXP-017 rejected dimensionless geometry of the completed transition. This task must stop further filtering of `BalanceOrOverlap` and `ParentReassertion` and move upstream to the state of the parent movement before counter-motion begins.

Use only existing local data. Missing datasets are recorded as `UNAVAILABLE` and do not stop execution.

## Fixed scope

- Instrument: ADAUSDT only.
- Data interval, source exclusion, 4H parent scale, 1H fallback, and closed-bar conventions: exactly as committed in EXP-015 through EXP-017.
- Starting population: reconstruct the original 425 EXP-014 BASE rows at detector factor `1.0`; report the 369 EXP-015 boundary-preserved rows as a fixed subgroup, not as the only population.
- Reconstruct and assert exact row identity against committed EXP-014 through EXP-017 outputs before analysis.
- No future pivots, lookahead, repainting, future returns, outcome-derived labels, chart interpretation, predictive claims, or strategy language.

## Parent-state measurements

At the last completed parent bar strictly before counter start, derive only causal, direction-aware fields:

1. `parent_age_bars`: completed parent bars since the executable parent state began.
2. `parent_displacement_atr`: direction-aware displacement from parent origin to pre-counter close, normalized by ATR available then.
3. `parent_efficiency`: absolute net displacement divided by cumulative true range over the parent-age window.
4. `parent_extension_from_origin_atr`: distance from parent origin to the most advanced completed extreme in parent direction.
5. `parent_close_location`: close position within the established parent range, direction-normalized to `[0,1]` where finite.
6. `parent_recent_slope_atr`: direction-aware close slope over the last three completed parent bars, normalized by ATR per bar.
7. `parent_slope_change_atr`: recent three-bar slope minus the preceding three-bar slope.
8. `parent_range_expansion_ratio`: mean true range of the latest three completed parent bars divided by the preceding three.
9. `parent_body_efficiency`: direction-aware net body displacement divided by summed absolute bodies over the latest three bars.
10. `distance_to_parent_boundary_atr`: direction-aware distance from pre-counter close to the established invalidation boundary.
11. `distance_from_parent_extreme_atr`: retracement from the established direction-aware parent extreme at counter start.
12. `parent_maturity_fraction`: parent age divided by the full executable parent duration known only up to counter start; do not use future termination.

Document minimum-history, zero-denominator, missingness, and mechanically redundant cases explicitly. Do not replace invalid values with arbitrary constants.

## Predeclared state families

Evaluate independently, without arbitrary threshold search:

1. `AGE`: fixed bins `1-2`, `3-4`, `5-8`, `9+` parent bars.
2. `DISPLACEMENT`: deterministic full-source quartiles of `parent_displacement_atr`.
3. `EFFICIENCY`: fixed bands `<0.25`, `[0.25,0.50)`, `[0.50,0.75)`, `>=0.75`.
4. `CLOSE_LOCATION`: fixed direction-normalized bands `<0.25`, `[0.25,0.50)`, `[0.50,0.75)`, `>=0.75`.
5. `SLOPE_STATE`: `accelerating`, `stable`, `decelerating` using fixed slope-change tolerance `0.10 ATR/bar`.
6. `RANGE_STATE`: contraction `<0.75`, stable `[0.75,1.25]`, expansion `>1.25`.
7. `BOUNDARY_DISTANCE`: deterministic full-source quartiles.
8. `EXTREME_RETRACEMENT`: fixed bands `<0.10`, `[0.10,0.25)`, `[0.25,0.50)`, `>=0.50 ATR`.

## Predeclared joint states

Evaluate only these combinations:

1. `YOUNG_EFFICIENT`: age `<=4` and efficiency `>=0.50`.
2. `MATURE_DECELERATING`: age `>=5` and slope state `decelerating`.
3. `EXTENDED_NEAR_EXTREME`: displacement at or above source median and extreme retracement `<0.25 ATR`.
4. `MATURE_RETRACED`: age `>=5` and extreme retracement `>=0.25 ATR`.
5. `PARENT_EXHAUSTION_STATE`: age `>=5`, slope state `decelerating`, and range state not expanding.

Do not promote a state solely because it is best in aggregate. Every candidate must survive support-size, direction, time, and factor checks.

## Required analysis

### A. Reconstruction

Regenerate the 425 EXP-014 BASE rows and the 369 EXP-015 boundary-preserved subgroup. Assert exact interval identity, direction, phase timestamps, and boundary membership.

### B. Measurement audit

For every parent-state field report finite support, missingness, quantiles, direction split, chronological-third split, and pairwise rank correlations. Flag direct duplication with previously tested EXP-015 through EXP-017 fields.

### C. State comparison

For every predeclared state calculate:

- support and retained fraction from the 425-row BASE population;
- support inside and outside the fixed EXP-015 boundary subgroup;
- rate per 1,000 parent bars;
- median and mean closed reassertion ATR;
- matched-control median and mean;
- paired rank contrast;
- fraction above matched control;
- distribution overlap;
- UP/DOWN support and contrast;
- chronological-third support and contrast;
- sample-collapse and concentration flags;
- incremental contrast versus deterministic support-size subsets of BASE and boundary-only rows.

### D. Matched controls

Use deterministic, non-overlapping controls from the same ADA interval. Match as closely as feasible on parent direction, ATR or realized range, calendar time, total transition duration, and counter duration, but do not match away the tested parent-state field. Exclude all source detections and the EXP-013 source interval. Record every mismatch column.

### E. Stability

Rerun detector factors `0.8`, `1.0`, and `1.2` with unchanged state definitions. Report row overlap with factor `1.0`, support, contrast direction, direction stability, chronological-third stability, and verdict stability.

### F. Incremental independence

For each state compare:

- state on the original 425-row BASE population;
- state inside the 369-row boundary subgroup;
- boundary subgroup without the state;
- deterministic equal-support subsets from both populations.

A state is not independent if its apparent effect is explained by boundary membership, support shrinkage, direction imbalance, time concentration, or direct duplication of age/range variables already used by controls.

### G. Counterexamples

Export strongest causal examples of:

- young/efficient parents followed by weak structural reassertion;
- mature/decelerating parents followed by strong structural reassertion;
- aggregate effects reversed by direction or chronological third;
- apparent exhaustion states explained only by boundary failure;
- invalid or minimum-history parent-state rows.

Record structural reasons only.

## Decision

Select exactly one verdict:

- `PARENT_STATE_SUPPORTED` — at least one predeclared parent state adds stable independent separation, retains adequate support, has consistent contrast direction across directions and chronological thirds, survives detector factors, and is not explained by boundary membership or support reduction.
- `PARENT_STATE_PARTIAL` — parent state contains incremental structural information, but effect size, support, time, direction, factor stability, or transfer is limited.
- `PARENT_STATE_REJECTED` — no predeclared parent state adds robust independent information, or apparent effects arise from redundancy, concentration, boundary duplication, or sample collapse.

Do not force a positive verdict. This remains descriptive structural evaluation only.

## Required outputs

Create exactly these eight files:

- `experiments/EXP-018_PARENT_STATE/REPORT.md`
- `experiments/EXP-018_PARENT_STATE/parent_state.csv`
- `experiments/EXP-018_PARENT_STATE/matched_controls.csv`
- `experiments/EXP-018_PARENT_STATE/state_comparison.csv`
- `experiments/EXP-018_PARENT_STATE/parameter_stability.csv`
- `experiments/EXP-018_PARENT_STATE/time_segment_summary.csv`
- `experiments/EXP-018_PARENT_STATE/counterexamples.csv`
- `experiments/EXP-018_PARENT_STATE/experiment_018.py`

Do not create or modify any other path. Do not create `__pycache__` or `.pyc` files.

## Python requirements

`experiment_018.py` must regenerate all seven CSV files and `REPORT.md` deterministically; assert exact reconstruction of the committed source populations; assert causal parent-state timestamps and direction-aware calculations; explicitly flag invalid values; assert fixed bins and joint states; assert non-overlapping controls; reproduce report values and verdict from CSV rows; and print a compact summary with source support, parent-state audit, strongest stable contrasts, boundary independence, direction/time/factor stability, verdict, and report path.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, any EXP-009 or EXP-013 through EXP-017 file, `start.sh`, `.git` internals, or any path outside the eight EXP-018 outputs. Existing local dirty files must remain byte-identical, unstaged, and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_018.py` twice and verify identical SHA-256 hashes for all eight outputs.
2. Parse all seven CSV files and verify documented columns.
3. Verify exact reconstruction of the committed 425-row BASE and 369-row boundary subgroup.
4. Verify every parent-state measurement uses only information complete before counter start.
5. Verify invalid denominators and insufficient-history rows are explicitly flagged.
6. Verify no outcome-derived thresholds or arbitrary grid search occurred.
7. Verify every control is non-overlapping and all mismatch fields are explicit.
8. Verify chronological thirds are deterministic and exhaustive.
9. Verify parameter rows come from actual factor runs `0.8`, `1.0`, and `1.2`.
10. Verify equal-support incremental comparisons for BASE and boundary populations.
11. Verify REPORT values and verdict reproduce from generated CSV outputs.
12. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-018_PARENT_STATE/experiment_018.py`, then remove any generated cache artifact before validation.
13. Run `git diff --check` and baseline-relative allowlist validation.
14. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves only the eight allowlisted EXP-018 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.
