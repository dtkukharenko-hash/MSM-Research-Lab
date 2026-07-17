# Current Codex Task

- task_id: `EXP-014A-COMMON-INVARIANT-TRANSFER`
- status: `READY`
- published_at: `2026-07-17`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-013-THREE-CASE-COMMON-INVARIANT`
- commit_message: `EXP-014 common invariant transfer`

## Objective

Test whether the descriptive closed-bar transition identified in EXP-013 transfers beyond the three reconstructed ADAUSDT cases.

The fixed source rule is:

`ChildCounterMotion -> BalanceOrOverlap -> ParentReassertion`

This task evaluates transfer only. Do not revise the EXP-013 case intervals, definitions, source verdict, or source outputs. Do not introduce strategy, profitability, entry, exit, long, short, PnL, or risk language.

Use only existing local market data already accessible through project loaders. Missing data for a requested instrument or period must be recorded as `UNAVAILABLE` and excluded transparently; it must not block the task.

This task runs only on fixed executable metrics and requires no interactive approval. Borderline rows must be marked `DIAGNOSTIC_FLAG`, handled automatically, and folded into the most conservative allowed verdict supported by the generated metrics.

## Fixed definitions

1. Reuse the executable causal definitions and default parameters from `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/experiment_013.py`.
2. Primary scale: `4H`.
3. Child scale: use `15m` when complete local data exist; otherwise use the same documented `1H` fallback used by EXP-013 and mark the selected child scale.
4. Closed bars only.
5. No future pivots, lookahead, repainting, future returns, outcome-derived labels, or chart interpretation.
6. Preserve the same direction-aware UP/DOWN logic.
7. Default parameter set must be fixed before evaluating transfer rows.

## Evaluation universe

Attempt the following instruments using existing local data:

- ADAUSDT;
- BTCUSDT;
- ETHUSDT;
- SOLUSDT;
- XRPUSDT.

For ADAUSDT, evaluate available bars outside the original EXP-013 interval `2023-10-19 00:00:00 UTC` through `2024-01-03 23:59:59 UTC`. The original three target intervals must not be included as transfer detections or controls.

For every instrument, use the maximum contiguous locally available interval that supports the required scales and causal warm-up. Record exact start/end, bar counts, child scale, gaps, and availability status before calculating results.

Do not fetch external data and do not request additional periods.

## Required analysis

### A. Causal detections

Run the fixed EXP-013 detector across each available instrument-period and record every complete source-rule occurrence:

`ChildCounterMotion -> BalanceOrOverlap -> ParentReassertion`

Each detection must include:

- instrument;
- child scale;
- parent direction;
- parent start;
- counter start;
- balance start;
- reassertion time;
- end time;
- parent invalidation boundary;
- component flags;
- ParentReassertion displacement normalized by ATR;
- counter displacement normalized by ATR;
- counter efficiency;
- overlap ratio;
- alternation rate;
- parent and child elapsed bars;
- child-to-parent amplitude ratio;
- child-to-parent duration ratio;
- parameter factor;
- `DIAGNOSTIC_FLAG` reason, if any.

### B. Matched controls

For each accepted detection, select deterministic non-overlapping controls from the same instrument matched as closely as feasible on:

- duration;
- ATR or realized range;
- parent direction;
- parent age;
- phase location within the available interval.

Exclude all target detections and the original EXP-013 case intervals. Record mismatch columns explicitly. Do not label an inexact match as exact.

### C. Transfer contrasts

At minimum calculate per instrument and pooled:

- number of accepted detections;
- number of `DIAGNOSTIC_FLAG` detections;
- detection rate per 1,000 4H bars;
- median and mean ParentReassertion ATR for detections and controls;
- rank-biserial or equivalent rank contrast;
- fraction of detections above matched-control value;
- overlap between detection and control distributions;
- direction split;
- child-scale split;
- uncertainty appropriate to the available sample size.

This is descriptive structural evaluation. Do not claim prediction.

### D. Component ablation

Evaluate whether the additional EXP-013 components improve separation while keeping the source rule fixed:

- base rule only;
- base plus `CounterProgressDecay`;
- base plus `FailedCounterExtension`;
- base plus both.

For each variant record support, instrument coverage, control contrast, false/`DIAGNOSTIC_FLAG` reduction, and whether any apparent improvement is caused by severe sample collapse.

Do not replace the base invariant merely because a stricter variant has a larger point estimate.

### E. Parameter-neighbour stability

Rerun the same detector at factors:

- `0.8`;
- `1.0`;
- `1.2`.

Record per instrument and pooled:

- detection count;
- detection rate;
- overlap of detected intervals with the 1.0 set;
- component support;
- control contrast direction;
- verdict stability.

### F. Counterexamples

Inspect programmatically the strongest false detections and `DIAGNOSTIC_FLAG` rows and document why the source transition is insufficient there. Prefer explicit structural reasons such as parent-boundary failure, unstable balance, weak reassertion, phase overlap, or scale mismatch.

## Transfer decision

Select exactly one verdict:

- `CONFIRMED_TRANSFERABLE_INVARIANT` — the same causal rule is present across at least three instruments including ADA outside the source interval, has consistent effect direction against matched controls, and remains directionally stable at 0.8/1.0/1.2 without dependence on one instrument or a tiny subset.
- `PARTIAL_TRANSFER` — the rule transfers descriptively but coverage, control separation, parameter stability, or instrument breadth is limited.
- `REJECT_TRANSFER` — the rule does not reproduce beyond the source cases or its contrast is inconsistent and indistinguishable from matched controls.

Do not force a positive verdict. Report unavailable instruments separately from negative instruments.

## Required outputs

Create exactly these eight files:

- `experiments/EXP-014_COMMON_INVARIANT_TRANSFER/REPORT.md`
- `experiments/EXP-014_COMMON_INVARIANT_TRANSFER/transfer_cases.csv`
- `experiments/EXP-014_COMMON_INVARIANT_TRANSFER/matched_controls.csv`
- `experiments/EXP-014_COMMON_INVARIANT_TRANSFER/instrument_summary.csv`
- `experiments/EXP-014_COMMON_INVARIANT_TRANSFER/component_ablation.csv`
- `experiments/EXP-014_COMMON_INVARIANT_TRANSFER/parameter_stability.csv`
- `experiments/EXP-014_COMMON_INVARIANT_TRANSFER/detections.csv`
- `experiments/EXP-014_COMMON_INVARIANT_TRANSFER/experiment_014.py`

Do not create or modify any other path.

## REPORT.md requirements

The report must contain:

1. exact reuse map from EXP-013 definitions and parameters;
2. data inventory and actual evaluated intervals by instrument;
3. transfer detection counts and rates;
4. matched-control methodology and mismatch disclosure;
5. per-instrument results;
6. pooled results;
7. component ablation;
8. parameter-neighbour stability;
9. strongest counterexamples and `DIAGNOSTIC_FLAG` cases;
10. dependence on instrument, direction, scale, and time segment;
11. limitations;
12. one final verdict from the allowed set;
13. strongest positive structural knowledge retained even if transfer is rejected.

## Python requirements

`experiment_014.py` must:

- import or reuse EXP-013 executable logic where practical instead of duplicating incompatible definitions;
- discover existing local data through project loaders;
- record unavailable instruments without failing the complete experiment;
- fail loudly on malformed required columns for an available dataset;
- use deterministic settings;
- generate all seven CSV outputs and REPORT.md;
- assert no evaluated ADA transfer row overlaps the original three EXP-013 intervals;
- assert controls do not overlap accepted detections;
- assert all reported counts and contrasts reproduce from generated CSV rows;
- assert all detector states use closed past bars only;
- print a compact summary containing evaluated instruments, unavailable instruments, detection counts, control contrast, ablation result, stability result, verdict, and report path.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite:

- `.codex/TASK.md`;
- `.codex/ALLOWLIST.txt`;
- `.codex/RESULT.md`;
- `docs/DEFINITIONS.md`;
- any EXP-013 file;
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`;
- `start.sh`;
- `.git` internals;
- any path outside the eight EXP-014 outputs.

Existing local dirty files must remain byte-identical, unstaged, and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_014.py` twice and verify identical SHA-256 hashes for all eight outputs.
2. Verify all seven CSV files parse and contain documented columns.
3. Verify instrument inventory agrees with actual loader results.
4. Verify the original three EXP-013 intervals are excluded from transfer detections and controls.
5. Verify every control is non-overlapping and mismatch fields are explicit.
6. Verify base and ablation variants are generated from executable predicates, not hardcoded labels.
7. Verify stability rows come from actual detector invocations at 0.8, 1.0, and 1.2.
8. Verify REPORT values and verdict reproduce from CSV outputs.
9. Run `python3 -m py_compile`, `git diff --check`, and baseline-relative allowlist validation.
10. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves only the eight allowlisted EXP-014 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.
