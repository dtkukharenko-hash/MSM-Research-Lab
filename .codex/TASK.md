# Current Codex Task

- task_id: `EXP-019-PARENT-REPRESENTATION`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-018-PARENT-STATE`
- commit_message: `EXP-019 parent representation`

## Objective

Test whether the fixed eight-bar parent window used by EXP-017 and EXP-018 suppresses real structural variability. Compare multiple causal definitions of parent origin, age, duration, magnitude, boundary, and extreme before `ChildCounterMotion`.

EXP-018 rejected parent-state fields partly because `parent_age_bars=8` and `parent_maturity_fraction=1.0` were mechanically fixed. This task evaluates the representation itself. Do not add another filter to the existing eight-bar state and do not tune prior boundary, balance, or phase-geometry thresholds.

Use only existing local data. Missing datasets are recorded as `UNAVAILABLE` and do not stop execution.

## Fixed scope

- Instrument: ADAUSDT only.
- Data interval, source exclusion, 4H parent scale, 1H fallback, closed-bar rules, and factor conventions: exactly as committed in EXP-014 through EXP-018.
- Starting population: reconstruct the 425 EXP-014 BASE rows at factor `1.0`; retain the 369 EXP-015 boundary-preserved rows as a declared subgroup.
- Every parent representation must end at the last completed 4H bar strictly before counter start.
- No future pivots, lookahead, repainting, future returns, outcome-derived labels, chart interpretation, predictive claims, or strategy language.

## Predeclared parent representations

Implement these independently and causally:

1. `FIXED_8`: committed eight completed parent bars before counter start. This is the reference only.
2. `DIRECTION_RUN`: walk backward over completed parent bars while direction-aware close displacement remains with the established parent direction; stop at the first opposite close step or maximum 32 bars.
3. `ATR_ORIGIN`: walk backward until cumulative direction-aware displacement from the candidate origin first reaches at least `1.0 ATR` measured causally at counter start; maximum 32 bars. If never reached, mark invalid.
4. `CONFIRMED_DIRECTION_CHANGE`: origin is the first completed bar after the most recent causal two-bar direction change confirmed before counter start; maximum lookback 32 bars.
5. `HYBRID_ORIGIN`: choose the later origin from `DIRECTION_RUN` and `ATR_ORIGIN`, preserving only information available before counter start.

Do not introduce arbitrary alternatives or select a representation from outcome statistics.

## Representation measurements

For every source row and representation calculate:

- `origin_time`, `end_time`, `age_bars`, `duration_hours`;
- direction-aware `displacement_atr` and `extension_atr`;
- `efficiency` = absolute net displacement / cumulative true range;
- `close_location` within the representation range;
- `distance_to_boundary_atr` and `distance_from_extreme_atr` using a boundary and extreme derived from that representation;
- recent and whole-window direction-aware slope;
- validity, minimum-history, cap-hit, zero-denominator, and origin-reason fields.

All ATR and boundaries must use values available by the representation end. Invalid cases remain explicit and are never imputed.

## Required analysis

### A. Reconstruction

Regenerate and identity-assert the 425 BASE rows and 369 boundary subgroup against committed outputs.

### B. Representation audit

For each representation report:

- valid support and invalid reasons;
- age/duration distribution and cap-hit rate;
- origin disagreement with `FIXED_8` in bars and hours;
- direction split and chronological-third split;
- pairwise overlap and rank correlations for age, displacement, efficiency, boundary distance, and extreme distance;
- fraction of rows where the representation restores non-degenerate age variability.

### C. Structural comparison

Compare representations without selecting arbitrary thresholds. Use deterministic full-source quartiles for age, displacement, efficiency, and boundary distance. For every representation and quartile report:

- support and rate per 1,000 parent bars;
- support inside/outside the boundary subgroup;
- median/mean closed reassertion ATR;
- matched-control median/mean;
- paired rank contrast, fraction above control, and distribution overlap;
- UP/DOWN and chronological-third support/contrast;
- sample-collapse, concentration, invalidity, and cap-hit flags;
- equal-support contrast relative to `FIXED_8`.

### D. Representation independence

A representation is useful only if it creates genuine upstream variability and any structural separation is not explained by support reduction, invalid-row exclusion, direction imbalance, time concentration, or direct duplication of the EXP-015 boundary.

Compare identical source rows where both candidate and `FIXED_8` are valid. Include deterministic equal-support subsets and row-paired representation differences.

### E. Matched controls

Use deterministic non-overlapping controls from the same ADA interval, excluding all source detections and the original EXP-013 interval. Match as closely as feasible on parent direction, ATR/range, calendar time, transition duration, and counter duration, without matching away the tested representation field. Record all mismatches.

### F. Stability

Rerun detector factors `0.8`, `1.0`, and `1.2` with unchanged representation definitions. Report source-row overlap, representation validity, age variability, origin agreement, contrast direction, direction/time stability, and verdict stability.

### G. Counterexamples

Export strongest causal examples of:

- large origin disagreement with no structural difference;
- variable-age representation collapsing to the same geometry as `FIXED_8`;
- apparent improvement caused by invalid-row removal or cap hits;
- aggregate effects reversed by direction or chronological third;
- rows where representations disagree on boundary preservation.

Record structural reasons only.

## Decision

Select exactly one verdict:

- `PARENT_REPRESENTATION_SUPPORTED` — at least one predeclared causal representation restores meaningful age/origin variability and adds stable independent structural separation across directions, chronological thirds, and detector factors without support or invalidity artifacts.
- `PARENT_REPRESENTATION_PARTIAL` — alternative representations restore variability or clarify boundaries, but separation, support, transfer, or stability remains limited.
- `PARENT_REPRESENTATION_REJECTED` — alternative origins do not create useful independent structure, or apparent effects arise from invalidity, support reduction, concentration, redundancy, or instability.

Do not force a positive verdict. This is descriptive structural evaluation only.

## Required outputs

Create exactly these eight files:

- `experiments/EXP-019_PARENT_REPRESENTATION/REPORT.md`
- `experiments/EXP-019_PARENT_REPRESENTATION/parent_representations.csv`
- `experiments/EXP-019_PARENT_REPRESENTATION/matched_controls.csv`
- `experiments/EXP-019_PARENT_REPRESENTATION/representation_comparison.csv`
- `experiments/EXP-019_PARENT_REPRESENTATION/parameter_stability.csv`
- `experiments/EXP-019_PARENT_REPRESENTATION/time_segment_summary.csv`
- `experiments/EXP-019_PARENT_REPRESENTATION/counterexamples.csv`
- `experiments/EXP-019_PARENT_REPRESENTATION/experiment_019.py`

Do not create or modify any other path. Do not create `__pycache__` or `.pyc` files.

## Python requirements

`experiment_019.py` must regenerate all seven CSV files and `REPORT.md` deterministically; assert exact source reconstruction; implement each representation from completed bars rather than labels; assert causal origin times and maximum lookback; preserve invalidity and cap-hit flags; assert controls do not overlap detections; reproduce report values and verdict from CSV rows; and print a compact summary with representation validity, age variability, origin disagreement, strongest equal-support contrasts, direction/time/factor stability, verdict, and report path.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, any EXP-009 or EXP-013 through EXP-018 file, `start.sh`, `.git` internals, or any path outside the eight EXP-019 outputs. Existing local dirty files must remain byte-identical, unstaged, and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_019.py` twice and verify identical SHA-256 hashes for all eight outputs.
2. Parse all seven CSV files and verify documented columns.
3. Verify exact reconstruction of the committed 425-row BASE and 369-row boundary subgroup.
4. Verify every representation uses only completed bars before counter start and respects the 32-bar cap.
5. Verify invalid, insufficient-history, zero-denominator, and cap-hit rows are explicit.
6. Verify no outcome-derived representation or arbitrary threshold search occurred.
7. Verify every control is non-overlapping and all mismatch fields are explicit.
8. Verify chronological thirds are deterministic and exhaustive.
9. Verify parameter rows come from actual factor runs `0.8`, `1.0`, and `1.2`.
10. Verify row-paired and equal-support comparisons against `FIXED_8`.
11. Verify REPORT values and verdict reproduce from generated CSV outputs.
12. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-019_PARENT_REPRESENTATION/experiment_019.py`, then remove any generated cache artifact.
13. Run `git diff --check` and baseline-relative allowlist validation.
14. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves only the eight allowlisted EXP-019 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.
