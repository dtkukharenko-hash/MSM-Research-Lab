# Current Codex Task

- task_id: `EXP-013-THREE-CASE-COMMON-INVARIANT`
- status: `READY`
- published_at: `2026-07-16`
- target_branch: `main`
- infrastructure_maintenance: `false`
- commit_message: `EXP-013 three-case common invariant`

## Objective

On ADAUSDT, using only the period from `2023-10-19 00:00:00 UTC` through `2024-01-03 23:59:59 UTC`, reconstruct the three visual cases previously supplied by the user, describe all three with one formal MSM language, and find the smallest causal structural invariant shared by all three.

This is a research task, not infrastructure work and not a trading-strategy task. A positive solution means a common observable structural mechanism. It does not require profitability or a predictive edge.

Do not stop after the first rejected candidate. Continue through feature analysis, ablation, matched controls, and parameter-neighbour checks until one strongest common structural invariant is identified and honestly bounded.

## Required evidence recovery

1. Read `PROJECT_INSTRUCTIONS.md`, `README.md`, and relevant research documents and experiment reports.
2. Read, but never modify, the current working-tree version of:
   - `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
3. Treat that protected Pine as primary evidence for the three user-marked cases. Extract every explicit timestamp, input time, label, window, boundary, and state definition it contains.
4. Search the full repository and readable Git history for:
   - `EXP-011`, `EXP-011B`, `EXP-012`;
   - `conflict`, `window`, `disputed`, `parent`, `child`;
   - `counter`, `balance`, `density`, `rejection`;
   - `19.10.2023`, `03.01.2024`, `three cases`, `три случая`.
5. Cross-reference the protected Pine, research notes, CSV files, Markdown reports, JSON files, and existing artifacts.
6. Do not stop merely because the original screenshots are absent. Reconstruct the three most strongly evidenced cases and mark each as `EXACT` or `RECONSTRUCTED` with a confidence score and an evidence note.
7. Use ADAUSDT unless repository evidence proves that one or more cases used another instrument. Record any such proof explicitly.

## Data and causal constraints

- Analysis window is strictly `2023-10-19` through `2024-01-03` inclusive.
- Primary scale: `4H`.
- Internal structure: `15m`.
- `1H` may be used only if the available data are complete enough for the specific case.
- Use existing project loaders and local data sources. Do not create a second incompatible data pipeline when an existing one works.
- Use only closed bars.
- No future pivots, lookahead, repainting, or future-derived labels.
- Any state that cannot be known on the current closed bar must be `UNKNOWN`.
- Do not use data after `2024-01-03` for feature selection, thresholds, ranking, or evaluation.
- Do not infer a case from outcome alone.

## Formal description of each case

For each of the three cases record at minimum:

- `case_id`;
- `case_status`: `EXACT` or `RECONSTRUCTED`;
- `confidence`;
- `instrument`;
- `primary_timeframe` and `child_timeframe`;
- `case_start`;
- `parent_start`;
- `counter_start`;
- `balance_or_conflict_start`;
- `resolution_time`;
- `case_end`;
- parent direction;
- parent invalidation boundary;
- counter direction;
- counter boundary;
- balance or conflict boundaries;
- ordered state sequence;
- evidence source.

Describe all three using the same definitions and the same feature calculations.

## Required features

Calculate causally for each case and for controls:

- parent displacement normalized by ATR;
- parent directional efficiency;
- counter displacement normalized by ATR;
- counter progress per bar;
- number of counter-boundary updates;
- size of successive counter-boundary updates;
- time between successive boundary updates;
- bars since the last counter extreme;
- overlap ratio;
- alternation rate;
- wick rejection relative to the counter boundary;
- close location in the local range;
- range contraction or expansion;
- failed counter extension;
- first renewed displacement in the parent direction;
- parent-boundary preservation;
- child-to-parent amplitude ratio;
- child-to-parent duration ratio;
- age of the parent and counter motions.

## Candidate mechanisms

Test all of the following with common definitions and common parameters:

### M1 — Counter-progress decay

The counter motion remains present, but each new advance is smaller, slower, or both.

### M2 — Failed counter extension

A new counter-boundary attempt is not retained by subsequent closes and price returns inside the prior child range.

### M3 — Conflict compression

Overlap and alternation rise while counter directional efficiency falls.

### M4 — Parent reassertion

A new closed-bar displacement in the parent direction exceeds local noise while the parent invalidation boundary remains intact.

### M5 — Combined resolution

`ParentIntact` plus at least two of `CounterProgressDecay`, `FailedCounterExtension`, and `ConflictCompression`, followed by `ParentReassertion`.

### M6 — Counter to balance to continuation

A counter motion transitions into balance, then a renewed parent-direction displacement occurs without requiring a failed extension.

### M7 — Relative scale transition

The common structure is explained by counter-to-parent amplitude and duration ratios rather than candle shape or one absolute threshold.

Do not accept M5 in advance. Compare all models, perform ablation, and select the smallest model that still describes all three cases.

## Common-invariant requirement

Find one minimal state sequence that is present in all three cases using the same definitions and parameters.

The primary candidate to test is:

`ParentIntact -> ChildCounterMotion -> CounterProgressDecay -> BalanceOrOverlap -> FailedCounterExtension -> ParentReassertion`

The final solution may be simpler or different. Prefer relative, ATR-normalized, and past-only percentile features over case-specific absolute thresholds.

A valid common invariant must:

1. describe all three cases;
2. use one parameter set;
3. be observable from closed bars;
4. not depend on a future pivot;
5. remain present when key thresholds are varied by approximately `±20%`;
6. be stronger in the three cases than in matched controls on at least one predeclared composite or component measure;
7. identify additional plausible cases in the same date window, with false or ambiguous detections documented.

If discriminative contrast is weak, do not invent predictive strength. The positive result may be a confirmed descriptive transition with only partial separation from controls.

## Matched controls

Within the same date window, construct control windows matched as closely as possible on:

- duration;
- ATR or realized range;
- parent direction;
- parent age;
- phase of the parent movement.

Exclude bars belonging to the three target cases from controls.

Because there are only three marked cases, do not claim large-sample certainty. Report effect direction, rank contrast, overlap with controls, and uncertainty.

## Iteration and stopping rule

Do not stop at the first negative or ambiguous candidate.

Proceed through:

1. reconstruction of the three cases;
2. common feature extraction;
3. M1–M7 comparison;
4. ablation;
5. threshold normalization;
6. parameter-neighbour checks;
7. matched-control comparison;
8. search for additional detections;
9. counterexample review.

Stop only after identifying the strongest minimal shared mechanism and documenting exactly which parts are causal, which are confirmatory, and which fail to separate from controls.

The report must always state the strongest positive structural knowledge found. It must not convert weak control separation into a claim of predictive power.

## Required outputs

Create exactly these files:

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

## REPORT.md requirements

The report must contain:

1. how each case was recovered and the evidence confidence;
2. a separate formal description of Case 1, Case 2, and Case 3;
3. one comparison table showing shared and differing properties;
4. definitions of every measured feature;
5. results for M1–M7;
6. ablation results;
7. the selected minimal common invariant;
8. causal versus post-confirmation components;
9. matched-control contrast;
10. parameter-neighbour stability;
11. additional detections;
12. counterexamples and ambiguous cases;
13. one final formal state rule;
14. limitations;
15. verdict: `CONFIRMED_COMMON_INVARIANT` or `PARTIAL_COMMON_INVARIANT`.

`PARTIAL_COMMON_INVARIANT` is appropriate when the shared transition is clear but matched-control separation or causal timing is weak.

## Python requirements

`experiment_013.py` must:

- reproduce all CSV outputs from the available local data;
- use deterministic settings;
- validate the requested date interval;
- fail loudly on missing required columns or insufficient data;
- contain no future-dependent detection logic;
- print a compact terminal summary with:
  - all three recovered case intervals;
  - the selected invariant;
  - matched-control contrast;
  - parameter stability;
  - number of additional detections;
  - report path;
  - Pine path.

## Pine requirements

`EXP013_THREE_CASE_REVIEW.pine` must:

- be visual only;
- contain no strategy or order commands;
- use closed-bar causal state logic;
- contain no future pivots;
- display `ParentIntact`, `CounterMotion`, `BalanceOrConflict`, `ProgressDecay`, `FailedExtension`, and `Resolution`;
- mark the three recovered cases distinctly;
- expose the three case intervals as editable time inputs;
- allow manual comparison with TradingView without changing the protected EXP-009A Pine.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite:

- `docs/DEFINITIONS.md`;
- `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`;
- `.codex/RESULT.md`;
- `.codex/TASK.md`;
- `.codex/ALLOWLIST.txt`;
- `.git` internals;
- any existing research file or artifact.

The protected Pine may already be modified before this task begins. Read it as evidence, preserve it byte-identically, and leave it unstaged and uncommitted.

## Validation

Before returning PASS:

- run `experiment_013.py` successfully;
- verify all seven CSV files exist, are parseable, and contain the expected columns;
- verify all three cases appear in `cases.csv`;
- verify `REPORT.md` contains one explicit final invariant and one verdict;
- verify the Pine file exists and contains no future-pivot or strategy commands;
- run `git diff --check`;
- verify only the nine allowlisted paths differ from the captured baseline;
- verify the protected Pine hash is unchanged from task start;
- verify no files are staged.

## Result contract

Planner, implementer, auditor, and corrector use the required JSON role contract. The implementer leaves the nine allowed outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message, and pushes to `main`.
