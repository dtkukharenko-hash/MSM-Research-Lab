# Current Codex Task

- task_id: `EXP-017-PHASE-GEOMETRY`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-016-BALANCE-QUALITY-GATE`
- commit_message: `EXP-017 phase geometry`

## Objective

Test whether dimensionless relations across the complete closed-bar transition provide stable structural information beyond the fixed EXP-015 parent-boundary gate:

`ChildCounterMotion -> BalanceOrOverlap -> ParentReassertion`

EXP-016 found no robust independent gate in the properties of the single balance bar. This task must stop isolated phase filtering and evaluate only relations between parent, counter, balance, and reassertion phases. Do not tune the EXP-015 boundary margin or revive rejected EXP-016 gates.

Use only existing local data. Missing datasets are recorded as `UNAVAILABLE` and do not stop execution.

## Fixed scope

- Instrument: ADAUSDT only.
- Data interval, source exclusion, 4H parent scale, 1H fallback, and closed-bar conventions: exactly as committed in EXP-015 and EXP-016.
- Starting population: the 369 rows passing the committed EXP-015 `BOUNDARY_THROUGH_REASSERTION` predicate at detector factor `1.0`.
- Reconstruct and assert exact identity against committed EXP-015 and EXP-016 rows before analysis.
- No future pivots, lookahead, repainting, future returns, outcome-derived labels, chart interpretation, predictive claims, or strategy language.

## Phase measurements

Derive direction-aware causal magnitudes and durations from completed bars only:

1. `parent_magnitude_atr`: signed established parent displacement magnitude before counter start, normalized by parent ATR.
2. `parent_duration_bars`: completed parent bars defining that displacement.
3. `counter_magnitude_atr`: absolute counter displacement against parent direction.
4. `counter_duration_bars`: completed child bars from counter start through counter end.
5. `balance_range_atr`: committed EXP-016 balance range.
6. `balance_duration_bars`: committed detector-defined duration, retained even if mechanically fixed.
7. `reassertion_magnitude_atr`: signed displacement with parent direction from balance close through closed reassertion.
8. `reassertion_duration_bars`: completed child bars used by reassertion.

## Predeclared dimensionless geometry

Calculate these relations without outcome-based selection:

1. `counter_parent_ratio = counter_magnitude_atr / parent_magnitude_atr`.
2. `balance_counter_ratio = balance_range_atr / counter_magnitude_atr`.
3. `reassertion_counter_ratio = reassertion_magnitude_atr / counter_magnitude_atr`.
4. `reassertion_parent_ratio = reassertion_magnitude_atr / parent_magnitude_atr`.
5. `counter_speed_ratio = (counter_magnitude_atr / counter_duration_bars) / (parent_magnitude_atr / parent_duration_bars)`.
6. `reassertion_counter_speed_ratio = (reassertion_magnitude_atr / reassertion_duration_bars) / (counter_magnitude_atr / counter_duration_bars)`.
7. `balance_time_ratio = balance_duration_bars / counter_duration_bars`.
8. `transition_symmetry = abs(log(counter_parent_ratio) + log(reassertion_counter_ratio))`, only where ratios are finite and positive.

Document zero-denominator, sign, missingness, and mechanically redundant cases explicitly. Do not hide invalid rows or replace them with arbitrary constants.

## Predeclared evaluation

For every geometry field:

- report quantiles, finite support, direction split, chronological-third split, and rank correlations;
- divide valid rows into deterministic quartiles calculated on the full fixed source population only;
- evaluate fixed broad bands around unity where applicable: `[0.25,0.50)`, `[0.50,1.00)`, `[1.00,2.00)`, `[2.00,+inf)`;
- compare each quartile/band with deterministic non-overlapping matched controls;
- report support, rate per 1,000 parent bars, reassertion ATR median/mean, control median/mean, paired rank contrast, fraction above control, overlap, direction/time stability, and sample-collapse flags.

Do not search arbitrary cutoffs and do not promote a bin solely because it is best in aggregate.

## Joint geometry test

Evaluate only these predeclared combinations:

1. `PROPORTIONAL_COUNTER`: `0.25 <= counter_parent_ratio < 1.00`.
2. `COMPACT_TRANSITION`: `balance_counter_ratio < 1.00` and `balance_time_ratio <= 1.00`.
3. `STRONG_REASSERTION`: `reassertion_counter_ratio >= 1.00`.
4. `FAST_REASSERTION`: `reassertion_counter_speed_ratio >= 1.00`.
5. `GEOMETRIC_CHAIN`: conjunction of 1, 2, and either 3 or 4.

Measure incremental information relative to the fixed EXP-015 boundary-only population and deterministic support-size subsets. A combination is not independent if apparent improvement is explained by support shrinkage, direction imbalance, time concentration, duplicated variables, or one extreme subset.

## Controls and stability

- Controls must come from the same ADA interval, exclude every source detection and the original EXP-013 interval, and never overlap detections.
- Match as closely as feasible on parent direction, parent age, ATR or realized range, total transition duration, counter duration, and time location; record all mismatches.
- Rerun detector factors `0.8`, `1.0`, and `1.2` with unchanged ratio definitions and bands.
- Report detection overlap with factor `1.0`, support, contrast direction, direction stability, chronological-third stability, and verdict stability.

## Counterexamples

Export the strongest causal examples of:

- proportional geometry with no separation from control;
- extreme geometry with strong reassertion;
- aggregate improvement reversed in one direction or chronological third;
- joint-chain passes caused only by support collapse;
- rows invalidated by zero or non-positive denominators.

Record structural reasons only.

## Decision

Select exactly one verdict:

- `PHASE_GEOMETRY_SUPPORTED` — at least one predeclared dimensionless relation or joint chain adds stable separation beyond boundary preservation, retains adequate support, has the same contrast direction across parent directions and chronological thirds, survives detector factors, and is not explained by support reduction or redundancy.
- `PHASE_GEOMETRY_PARTIAL` — phase relations contain incremental structural information, but effect size, support, time, direction, factor stability, or transfer is limited.
- `PHASE_GEOMETRY_REJECTED` — no predeclared relation adds robust information beyond the boundary-only population, or apparent effects arise from concentration, redundancy, invalid ratios, or sample collapse.

Do not force a positive verdict. This is descriptive structural evaluation only.

## Required outputs

Create exactly these eight files:

- `experiments/EXP-017_PHASE_GEOMETRY/REPORT.md`
- `experiments/EXP-017_PHASE_GEOMETRY/phase_geometry.csv`
- `experiments/EXP-017_PHASE_GEOMETRY/matched_controls.csv`
- `experiments/EXP-017_PHASE_GEOMETRY/geometry_comparison.csv`
- `experiments/EXP-017_PHASE_GEOMETRY/parameter_stability.csv`
- `experiments/EXP-017_PHASE_GEOMETRY/time_segment_summary.csv`
- `experiments/EXP-017_PHASE_GEOMETRY/counterexamples.csv`
- `experiments/EXP-017_PHASE_GEOMETRY/experiment_017.py`

Do not create or modify any other path. Do not create `__pycache__` or `.pyc` files.

## Python requirements

`experiment_017.py` must regenerate all seven CSV files and `REPORT.md` deterministically; assert exact reconstruction of the committed source population; assert causal phase ordering, direction-aware calculations, finite/invalid ratio handling, fixed bands, non-overlapping controls, and report reproduction from CSV rows; and print a compact summary with source support, valid-ratio support, strongest stable contrasts, direction/time/factor stability, verdict, and report path.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, any EXP-009 or EXP-013 through EXP-016 file, `start.sh`, `.git` internals, or any path outside the eight EXP-017 outputs. Existing local dirty files must remain byte-identical, unstaged, and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_017.py` twice and verify identical SHA-256 hashes for all eight outputs.
2. Parse all seven CSV files and verify documented columns.
3. Verify exact reconstruction of the committed 369-row EXP-015 population and agreement with applicable EXP-016 fields.
4. Verify all phase measurements and ratios are executable causal calculations rather than labels.
5. Verify zero/non-positive denominators and invalid logarithms are explicitly flagged.
6. Verify no outcome-derived thresholds or arbitrary grid search occurred.
7. Verify every control is non-overlapping and all mismatch fields are explicit.
8. Verify chronological thirds are deterministic and exhaustive.
9. Verify parameter rows come from actual factor runs `0.8`, `1.0`, and `1.2`.
10. Verify incremental comparisons include deterministic support-size controls.
11. Verify REPORT values and verdict reproduce from generated CSV outputs.
12. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-017_PHASE_GEOMETRY/experiment_017.py`, then remove any generated cache artifact before validation.
13. Run `git diff --check` and baseline-relative allowlist validation.
14. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves only the eight allowlisted EXP-017 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.
