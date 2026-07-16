# Current Codex Task

- task_id: `EXP-013-R1-TECHNICAL-METRIC-AND-STABILITY-REPAIR`
- status: `READY`
- published_at: `2026-07-16`
- target_branch: `main`
- infrastructure_maintenance: `false`
- original_task_id: `EXP-013-THREE-CASE-COMMON-INVARIANT`
- correction_attempt: `1`
- commit_message: `EXP-013 R1 technical metric and stability repair`

## Objective

Correct purely technical defects in the existing EXP-013 implementation and regenerate its nine allowlisted outputs. Preserve the original research question, date window, reconstructed case intervals, evidence sources, candidate mechanisms M1-M7, holdout policy, and prohibition on visual or research judgment.

Do not introduce new definitions, hypotheses, case windows, instruments, data after `2024-01-03 23:59:59 UTC`, visual judgments, or manual-review requirements.

## Defects to correct

1. `matched_controls.csv` is not actually duration-matched: the implementation truncates every control to at most 18 bars while claiming duration matching. Select deterministic non-target controls with the same duration as their matched case, or report a transparent nearest feasible duration and its mismatch. Do not claim a match that was not computed.
2. `parent_age_bars` currently stores an absolute array index, and `child_parent_duration_ratio` divides by that index. Compute both from elapsed bars within the relevant reconstructed parent and child intervals.
3. Counter features currently reuse parent-direction progress over the whole counter-to-resolution window. Compute counter displacement, progress, boundary updates, update sizes, update intervals, last counter extreme, and failed extension in the actual counter direction and over the documented counter phase, using only closed past bars.
4. `parent_boundary_preserved` is hardcoded to `1`. Derive it from the stated parent invalidation boundary and closed bars through resolution.
5. `candidate_models.csv` hardcodes `cases_present=3`, generic effect labels, and ablation outcomes. Recompute presence and summaries from generated case/control features. Do not force a model to pass.
6. `parameter_stability.csv` hardcodes all three cases present and two additional detections. Re-run the actual detector at factors `0.8`, `1.0`, and `1.2`, recording observed target-case presence and observed additional detections.
7. `cases.csv` hardcodes the full sequence including `FailedCounterExtension` for every case although generated features show it absent in some cases. Make each ordered sequence agree with its computed causal states. The selected minimal invariant must be the actual common intersection, not a prefilled string.
8. The Pine artifact must implement the same direction-aware minimal rule as Python. It must support both UP and DOWN parents, mark each full editable case interval distinctly, use closed-bar logic, and remain visual-only. Do not alter the protected EXP009A Pine.
9. Ensure `REPORT.md`, terminal summary, CSV files, and Pine describe the same computed result without contradictory counts or claims.

## Fixed research constraints

- Instrument: ADAUSDT.
- Analysis window: `2023-10-19 00:00:00 UTC` through `2024-01-03 23:59:59 UTC`, inclusive.
- Primary scale: `4H`; child scale remains the documented available fallback used by the existing implementation.
- Use only closed bars; no future pivots, lookahead, repainting, future returns, or future-derived labels.
- Keep the three existing reconstructed case intervals and evidence confidence unchanged unless a timestamp is proven to be a simple serialization error. Any change requiring visual interpretation or research judgment must stop with `USER_DECISION_REQUIRED` rather than being made automatically.
- No predictive or profitability claims.

## Required outputs

Modify only the existing nine allowlisted paths:

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
- any existing file outside the nine allowlisted EXP-013 paths.

The protected EXP009A Pine may already be dirty before task start. Preserve it byte-identically and leave it unstaged and uncommitted.

## Validation

Before PASS:

1. Run `experiment_013.py` successfully twice and verify deterministic hashes for all generated outputs.
2. Verify all seven CSV files parse and contain expected columns.
3. Assert controls do not overlap target cases and report actual duration mismatch for every control.
4. Assert all counter features use the counter phase and counter direction.
5. Assert parent ages and duration ratios are elapsed-duration quantities, not absolute source indices.
6. Assert model presence, ablation summaries, stability counts, and detection counts are computed rather than constants.
7. Assert every `cases.csv` ordered sequence agrees with computed state flags.
8. Assert the final invariant is present in all three cases and its reported case/control contrast is numerically reproducible.
9. Assert Pine contains no strategy/order commands or future pivots, handles both directions, and marks all three editable intervals.
10. Run `git diff --check` and verify only the nine allowlisted paths differ from baseline.
11. Verify the protected EXP009A Pine hash is unchanged from task start and no files are staged.

## Stop conditions

Return `USER_DECISION_REQUIRED` without changing research outputs if correction would require visual chart interpretation, a new holdout, a definition or hypothesis change, replacement of the reconstructed cases, or any subjective research decision.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves the nine allowed outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.