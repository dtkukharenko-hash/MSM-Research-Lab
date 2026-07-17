# Current Codex Task

- task_id: `EXP-015-PARENT-BOUNDARY-GATE`
- status: `READY`
- published_at: `2026-07-17`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-014-COMMON-INVARIANT-TRANSFER`
- commit_message: `EXP-015 parent boundary gate`

## Objective

Test whether explicit preservation of the established parent invalidation boundary is a necessary structural gate for the fixed closed-bar transition:

`ChildCounterMotion -> BalanceOrOverlap -> ParentReassertion`

EXP-014 found 369 accepted rows, 56 diagnostic rows, weak case-control separation, and parent-boundary failure as the explicit structural reason in the strongest failed rows. This task tests that gate only. Do not revise EXP-013 or EXP-014 outputs, definitions, source intervals, or verdicts.

Use only existing local data. The task runs entirely from fixed executable rules and requires no interactive approval. Missing datasets are recorded as `UNAVAILABLE` and do not stop execution.

## Fixed scope

- Instrument: ADAUSDT only, because it is the available local archive established by EXP-014.
- Data interval: maximum contiguous local interval used by EXP-014, excluding the original EXP-013 source interval `2023-10-19 00:00:00 UTC` through `2024-01-03 23:59:59 UTC`.
- Parent scale: completed `4H` UTC bars.
- Child scale: existing documented `1H` fallback.
- Closed past bars only.
- No future pivots, lookahead, repainting, future returns, outcome-derived labels, chart interpretation, predictive claims, or strategy language.
- Reuse the executable EXP-013/EXP-014 detector conventions and default factor `1.0` before evaluating rows.

## Gate definitions

Evaluate the same base transition under these executable variants:

1. `BASE`: source transition only.
2. `BOUNDARY_AT_COUNTER_END`: parent invalidation boundary preserved through the counter phase.
3. `BOUNDARY_THROUGH_BALANCE`: boundary preserved through the balance phase.
4. `BOUNDARY_THROUGH_REASSERTION`: boundary preserved on every completed parent bar through the reassertion bar.
5. `BOUNDARY_MARGIN`: variant 4 plus minimum normalized distance from the invalidation boundary at reassertion.

The invalidation boundary, direction-aware sign, phase boundaries, and normalized margin must be derived from existing executable definitions. Do not hardcode row labels or force any gate to pass.

## Required analysis

### A. Reconstruct base rows

Regenerate the EXP-014 ADA transfer rows from source logic and assert agreement with the committed EXP-014 outputs for interval identity, direction, phase timestamps, and base component flags.

### B. Gate comparison

For every gate variant calculate:

- support count and rate per 1,000 parent bars;
- retained fraction from BASE;
- diagnostic-row retention and removal;
- median and mean reassertion ATR;
- matched-control median and mean;
- paired rank contrast;
- fraction above matched control;
- distribution overlap;
- direction split;
- time-segment split;
- sample-collapse flag.

### C. Matched controls

Choose deterministic, non-overlapping controls from the same ADA interval, matched as closely as feasible on duration, ATR or realized range, parent direction, parent age, and time location. Record all mismatch columns. Exclude base detections and the original EXP-013 intervals.

### D. Boundary-margin stability

Evaluate fixed normalized boundary-margin thresholds at:

- `0.0 ATR`;
- `0.1 ATR`;
- `0.2 ATR`;
- `0.3 ATR`.

Also rerun detector parameter factors `0.8`, `1.0`, and `1.2`. Record support, detection overlap with factor 1.0, control contrast direction, diagnostic reduction, and verdict stability.

### E. Time stability

Split the available ADA transfer interval into deterministic chronological thirds. Report gate support and contrast separately for each third and parent direction. A result dependent on one third must be marked as time-concentrated.

### F. Counterexamples

Export the strongest rows where the base transition appears but the parent boundary fails, and the strongest rows where the strict gate passes without improved control separation. Record explicit causal structural reasons only.

## Decision

Select exactly one verdict:

- `BOUNDARY_GATE_SUPPORTED` — preservation through reassertion removes most boundary-failure rows, retains adequate support, improves control separation in the same direction across chronological thirds and parameter factors, and is not dependent on one direction or a tiny subset.
- `BOUNDARY_GATE_PARTIAL` — the gate removes structural failures but improvement, support, or stability is limited.
- `BOUNDARY_GATE_REJECTED` — the gate causes severe sample collapse, fails to improve separation, or is unstable across time or parameters.

Do not force a positive verdict. This is descriptive structural evaluation only.

## Required outputs

Create exactly these eight files:

- `experiments/EXP-015_PARENT_BOUNDARY_GATE/REPORT.md`
- `experiments/EXP-015_PARENT_BOUNDARY_GATE/gated_detections.csv`
- `experiments/EXP-015_PARENT_BOUNDARY_GATE/matched_controls.csv`
- `experiments/EXP-015_PARENT_BOUNDARY_GATE/gate_comparison.csv`
- `experiments/EXP-015_PARENT_BOUNDARY_GATE/parameter_stability.csv`
- `experiments/EXP-015_PARENT_BOUNDARY_GATE/time_segment_summary.csv`
- `experiments/EXP-015_PARENT_BOUNDARY_GATE/counterexamples.csv`
- `experiments/EXP-015_PARENT_BOUNDARY_GATE/experiment_015.py`

Do not create or modify any other path. Do not create `__pycache__` or `.pyc` files.

## Python requirements

`experiment_015.py` must:

- import or reuse EXP-013 and EXP-014 executable logic where practical;
- regenerate all seven CSV files and REPORT.md deterministically;
- assert exclusion of the original EXP-013 interval;
- assert phase ordering and direction-aware boundary calculations;
- assert gate membership is derived from bar data and not constants;
- assert controls do not overlap detections;
- assert report counts, contrasts, and verdict reproduce from CSV rows;
- print a compact summary with support, diagnostic reduction, contrasts, time stability, parameter stability, verdict, and report path.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite:

- `.codex/TASK.md`;
- `.codex/ALLOWLIST.txt`;
- `.codex/RESULT.md`;
- `docs/DEFINITIONS.md`;
- any EXP-009, EXP-013, or EXP-014 file;
- `start.sh`;
- `.git` internals;
- any path outside the eight EXP-015 outputs.

Existing local dirty files must remain byte-identical, unstaged, and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_015.py` twice and verify identical SHA-256 hashes for all eight outputs.
2. Parse all seven CSV files and verify documented columns.
3. Verify regenerated BASE rows agree with committed EXP-014 ADA rows.
4. Verify gate variants and margin thresholds are executable predicates rather than labels.
5. Verify every control is non-overlapping and all mismatch fields are explicit.
6. Verify chronological thirds are deterministic and exhaustive over evaluated rows.
7. Verify parameter rows come from actual runs at `0.8`, `1.0`, and `1.2`.
8. Verify REPORT values and verdict reproduce from generated CSV outputs.
9. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-015_PARENT_BOUNDARY_GATE/experiment_015.py`.
10. Run `git diff --check` and baseline-relative allowlist validation.
11. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves only the eight allowlisted EXP-015 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.
