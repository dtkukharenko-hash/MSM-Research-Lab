# Current Codex Task

- task_id: `EXP-016-BALANCE-QUALITY-GATE`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-015-PARENT-BOUNDARY-GATE`
- commit_message: `EXP-016 balance quality gate`

## Objective

Test whether measurable quality of the closed-bar `BalanceOrOverlap` phase provides an independent structural gate on top of the EXP-015 parent-boundary gate for the fixed transition:

`ChildCounterMotion -> BalanceOrOverlap -> ParentReassertion`

EXP-015 established `BOUNDARY_GATE_PARTIAL`: boundary preservation removed all 56 documented boundary-failure rows while retaining 369 of 425 BASE rows, but improved matched-control separation only modestly and boundary margin added no discrimination. This task must hold the accepted EXP-015 boundary predicate fixed and test only balance-phase quality. Do not resume boundary-margin tuning.

Use only existing local data. Missing datasets are recorded as `UNAVAILABLE` and do not stop execution.

## Fixed scope

- Instrument: ADAUSDT only.
- Data interval and source exclusion: exactly as committed in EXP-015.
- Parent scale: completed `4H` UTC bars.
- Child scale: existing documented `1H` fallback.
- Closed past bars only.
- Starting population: rows passing the committed EXP-015 boundary-through-reassertion predicate at detector factor `1.0`.
- No future pivots, lookahead, repainting, future returns, outcome-derived labels, chart interpretation, predictive claims, or strategy language.
- Reuse committed EXP-014 and EXP-015 executable logic where practical and assert row identity before quality analysis.

## Balance-quality measurements

For each accepted EXP-015 row derive only from completed bars inside the balance phase:

1. `balance_duration_bars`: number of completed child bars in balance.
2. `balance_range_atr`: balance high-low range normalized by parent ATR available at balance end.
3. `balance_body_atr`: sum of absolute child candle bodies normalized by parent ATR.
4. `overlap_ratio`: intersection-over-union of consecutive child-bar ranges, aggregated deterministically.
5. `compression_ratio`: balance realized range divided by the preceding counter-phase realized range.
6. `directional_drift_atr`: signed balance start-to-end displacement against or with parent direction, normalized by ATR.
7. `boundary_distance_change_atr`: change in direction-aware distance from the parent invalidation boundary across balance.
8. `reassertion_setup_distance_atr`: direction-aware distance from balance close to the reassertion threshold using only information available at balance end.

Definitions must be executable, direction-aware, causal, and documented. Do not derive a composite score from outcome statistics.

## Predeclared gate families

Evaluate each family independently before any combination:

1. `DURATION`: balance duration bins `1`, `2`, `3`, `4+` child bars.
2. `RANGE_COMPRESSION`: fixed compression thresholds `<=0.50`, `<=0.75`, `<=1.00`.
3. `OVERLAP`: fixed overlap thresholds `>=0.25`, `>=0.50`, `>=0.75`.
4. `LOW_DRIFT`: absolute directional drift thresholds `<=0.10`, `<=0.25`, `<=0.50 ATR`.
5. `BOUNDARY_RECOVERY`: boundary-distance change `>=0.0`, `>=0.10`, `>=0.25 ATR`.
6. `COMPACT_BALANCE`: predeclared conjunction `compression_ratio <=0.75` and `overlap_ratio >=0.50` and `abs(directional_drift_atr) <=0.25`.

Do not search arbitrary thresholds. Do not select a best gate solely from aggregate separation. Every reported candidate must include support, stability, and direction/time decomposition.

## Required analysis

### A. Reconstruct source population

Regenerate EXP-015 accepted rows and assert exact agreement with committed `gated_detections.csv` for interval identity, direction, phase timestamps, boundary flags, and accepted-row count.

### B. Measurement audit

For every balance-quality field report missingness, finite-value checks, quantiles, direction split, chronological-third split, and pairwise rank correlations. Flag mechanically redundant measurements.

### C. Gate comparison

For every predeclared gate and threshold calculate:

- support count and retained fraction from the EXP-015 accepted population;
- rate per 1,000 parent bars;
- median and mean reassertion ATR;
- matched-control median and mean;
- paired rank contrast;
- fraction above matched control;
- distribution overlap;
- UP and DOWN support and contrast;
- chronological-third support and contrast;
- sample-collapse flag;
- improvement relative to the fixed EXP-015 boundary-only baseline.

### D. Matched controls

Use deterministic non-overlapping controls from the same ADA interval. Match as closely as feasible on parent direction, parent age, counter duration, balance duration, ATR or realized range, and time location. Exclude every source detection and the original EXP-013 interval. Record all mismatch columns.

### E. Stability

Rerun detector factors `0.8`, `1.0`, and `1.2` without changing the fixed gate thresholds. Report detection overlap with factor `1.0`, support, contrast direction, time stability, direction stability, and verdict stability.

### F. Incremental independence

For each quality gate measure whether it adds information beyond boundary preservation by comparing:

- boundary-only accepted rows;
- quality gate without boundary condition on the original BASE population;
- boundary plus quality gate;
- matched support-size controls sampled deterministically from boundary-only rows.

A quality gate is not independent if its apparent effect is fully explained by support reduction, direction imbalance, time concentration, or direct duplication of boundary-distance variables.

### G. Counterexamples

Export strongest causal counterexamples:

- compact/high-overlap balances with no improvement over matched control;
- loose/low-overlap balances with strong reassertion;
- quality-gate passes concentrated near boundary failure;
- cases where direction or one chronological third reverses the aggregate contrast.

Record structural reasons only.

## Decision

Select exactly one verdict:

- `BALANCE_QUALITY_SUPPORTED` — at least one predeclared balance-quality gate adds stable separation beyond the fixed boundary gate, retains adequate support, has the same contrast direction across chronological thirds and parent directions, survives detector factors, and is not reducible to support shrinkage or boundary duplication.
- `BALANCE_QUALITY_PARTIAL` — balance measurements contain incremental structural information, but effect size, support, transfer, direction, time, or factor stability is limited.
- `BALANCE_QUALITY_REJECTED` — no predeclared quality gate adds robust information beyond boundary preservation, or apparent improvements arise from sample collapse, concentration, or redundancy.

Do not force a positive verdict. This is descriptive structural evaluation only.

## Required outputs

Create exactly these eight files:

- `experiments/EXP-016_BALANCE_QUALITY_GATE/REPORT.md`
- `experiments/EXP-016_BALANCE_QUALITY_GATE/qualified_detections.csv`
- `experiments/EXP-016_BALANCE_QUALITY_GATE/matched_controls.csv`
- `experiments/EXP-016_BALANCE_QUALITY_GATE/quality_comparison.csv`
- `experiments/EXP-016_BALANCE_QUALITY_GATE/threshold_stability.csv`
- `experiments/EXP-016_BALANCE_QUALITY_GATE/time_segment_summary.csv`
- `experiments/EXP-016_BALANCE_QUALITY_GATE/counterexamples.csv`
- `experiments/EXP-016_BALANCE_QUALITY_GATE/experiment_016.py`

Do not create or modify any other path. Do not create `__pycache__` or `.pyc` files.

## Python requirements

`experiment_016.py` must:

- import or reuse EXP-014 and EXP-015 executable logic where practical;
- regenerate all seven CSV files and `REPORT.md` deterministically;
- assert exact reconstruction of the EXP-015 accepted population;
- assert all measurements use bars complete by balance end or reassertion as explicitly documented;
- assert gate membership is computed from bar data and fixed thresholds, not labels or outcomes;
- assert controls do not overlap detections;
- assert report counts, contrasts, and verdict reproduce from CSV rows;
- print a compact summary with source support, gate support, incremental contrasts, time/direction/factor stability, verdict, and report path.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite:

- `.codex/TASK.md`;
- `.codex/ALLOWLIST.txt`;
- `.codex/RESULT.md`;
- `docs/DEFINITIONS.md`;
- any EXP-009, EXP-013, EXP-014, or EXP-015 file;
- `start.sh`;
- `.git` internals;
- any path outside the eight EXP-016 outputs.

Existing local dirty files must remain byte-identical, unstaged, and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_016.py` twice and verify identical SHA-256 hashes for all eight outputs.
2. Parse all seven CSV files and verify documented columns.
3. Verify exact reconstruction of committed EXP-015 accepted rows.
4. Verify all quality fields and gates are executable causal predicates rather than labels.
5. Verify no outcome-derived threshold selection or arbitrary grid search occurred.
6. Verify every control is non-overlapping and all mismatch fields are explicit.
7. Verify chronological thirds are deterministic and exhaustive.
8. Verify factor rows come from actual runs at `0.8`, `1.0`, and `1.2`.
9. Verify incremental-independence comparisons include deterministic support-size controls.
10. Verify REPORT values and verdict reproduce from generated CSV outputs.
11. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-016_BALANCE_QUALITY_GATE/experiment_016.py`.
12. Run `git diff --check` and baseline-relative allowlist validation.
13. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves only the eight allowlisted EXP-016 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.