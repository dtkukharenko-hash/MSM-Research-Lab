# Current Codex Task

- task_id: `EXP-013-R2-EXECUTABLE-METRIC-AND-STABILITY-REPAIR`
- status: `READY`
- published_at: `2026-07-17`
- target_branch: `main`
- infrastructure_maintenance: `false`
- original_task_id: `EXP-013-THREE-CASE-COMMON-INVARIANT`
- correction_attempt: `2`
- supersedes_task_id: `EXP-013-R1-TECHNICAL-METRIC-AND-STABILITY-REPAIR`
- commit_message: `EXP-013 R2 executable metric and stability repair`

## Objective

Complete the still-unimplemented purely technical repairs from EXP-013 R1. The prior R1 result changed some generated text/CSV values but left the executable generator with the original hardcoded and incorrectly scoped calculations. Repair the generator first, regenerate all outputs from it, and prove that no required result is manually prefilled.

This is the second and final automatic correction attempt for original task `EXP-013-THREE-CASE-COMMON-INVARIANT`. Do not alter the research question, definitions, three reconstructed case intervals, evidence confidence, hypotheses M1-M7, date window, instrument, holdout policy, selected model family, or any visual/research judgment.

## Confirmed remaining technical defects

1. `metrics()` still receives only one interval and computes parent and counter quantities from the same whole counter-to-resolution window. Refactor it to receive the documented parent, counter, balance, and resolution boundaries and calculate each feature only on its correct causal phase and direction.
2. `parent_boundary_preserved` is still literal `1`. Derive it from the fixed parent invalidation boundary and all closed bars through the documented resolution.
3. `parent_age_bars` still stores the absolute source-array index `a`, and `child_parent_duration_ratio` divides by that index. Compute elapsed bar counts within the reconstructed parent and child intervals.
4. `cases.csv` ordered sequences are still prefilled identically with `FailedCounterExtension` for all three cases. Construct each sequence from computed state flags, preserving chronological order.
5. M4 `cases_present` is still forced to `3`, and model selection/ablation strings are preassigned. Compute presence and summaries from generated features. Keep the existing candidate family and selection policy; do not force a pass.
6. `parameter_stability.csv` is still entirely hardcoded (`target_cases_present=3`, `additional_detections=2`, `stable=YES`). Execute the same detector independently at factors 0.8, 1.0, and 1.2 and record observed target presence and observed additional detections.
7. Controls must include an explicit duration mismatch column and must be chosen deterministically without overlap with any target case. Exact duration is preferred; otherwise record the nearest feasible mismatch transparently.
8. The final invariant string, case/control contrast, detection counts, report statements, and Pine rule must all be generated from the same executable result and agree numerically.
9. Pine must implement the same direction-aware rule for both UP and DOWN parents, use closed bars only, mark each full editable case interval distinctly, and remain visual-only.

## Fixed research constraints

- Instrument: ADAUSDT.
- Analysis window: `2023-10-19 00:00:00 UTC` through `2024-01-03 23:59:59 UTC`, inclusive.
- Primary scale: `4H`; child scale remains the existing documented `1H` fallback.
- Keep the three current reconstructed case intervals and evidence confidence unchanged.
- Use only closed past bars; no future pivots, lookahead, repainting, future returns, or future-derived labels.
- No predictive, trading, profitability, entry, exit, long, short, PnL, or risk claims.
- Stop without changing outputs if any repair requires chart interpretation, a new holdout, revised definitions, revised hypotheses, replacement case windows, or subjective research judgment.

## Required outputs

Modify only these existing nine paths:

- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/REPORT.md`
- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/cases.csv`
- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/case_features.csv`
- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/matched_controls.csv`
- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/candidate_models.csv`
- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/detections.csv`
- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/parameter_stability.csv`
- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/experiment_013.py`
- `experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/artifacts/EXP013_THREE_CASE_REVIEW.pine`

Do not create or modify any other path.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite:

- `docs/DEFINITIONS.md`;
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`;
- `.codex/RESULT.md`;
- `.codex/TASK.md`;
- `.codex/ALLOWLIST.txt`;
- `.git` internals;
- any file outside the nine allowlisted EXP-013 paths.

The protected EXP009A Pine may already be dirty before task start. Preserve it byte-identically and leave it unstaged and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_013.py` twice from a clean output baseline and verify identical SHA-256 hashes for all eight generated report/data/Pine outputs.
2. Verify all seven CSV files parse and contain their documented columns.
3. Add executable assertions proving phase boundaries and directions used by every counter feature.
4. Add executable assertions proving elapsed parent/child durations are not absolute source indices.
5. Add executable assertions proving `parent_boundary_preserved`, model presence, sequence membership, stability counts, and additional detections are derived values rather than constants.
6. Verify every control is non-overlapping and report `duration_mismatch_bars` explicitly.
7. Verify every ordered sequence agrees exactly with computed flags for that case.
8. Verify the reported minimal invariant equals the computed intersection of required states across all three cases and its case/control contrast is reproducible from CSV values.
9. Verify each stability row comes from an actual detector invocation at its stated factor.
10. Verify Pine has no `strategy`, order, future-pivot, lookahead, or repainting commands; supports both parent directions; and shades/marks all three full editable intervals.
11. Run `python3 -m py_compile`, `git diff --check`, and a baseline-relative allowlist check.
12. Verify the protected EXP009A Pine hash is unchanged from task start and no files are staged.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves only the nine allowed outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.