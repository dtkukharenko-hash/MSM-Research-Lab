# Current Codex Task

- task_id: `EXP-025-ADA-LOWER-TIMEFRAME-DEOVERLAP`
- status: `READY`
- published_at: `2026-07-19`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-024-ADA-COHERENT-LOWER-TIMEFRAME-TRANSFER`
- commit_message: `EXP-025 ADA lower timeframe de-overlap`

## Objective

Determine whether the lower-timeframe structural form observed in EXP-024 survives after repeated and overlapping detections are collapsed into independent causal episodes.

This is a robustness and dependence audit. Do not change the detector, thresholds, parent representations, source hierarchy or normalized geometry. Do not use future outcomes, returns, labels or downstream contrast to define episodes.

## Fixed data and source hierarchy

Use the same official Bybit ADAUSDT linear hierarchy and frozen range as EXP-024:

- native 3m, 5m and 15m archives with the exact EXP-023 hashes;
- derived 1H from complete UTC-aligned groups of four native 15m bars;
- range `2023-07-01T00:00:00Z` through `2024-12-31T23:00:00Z`;
- mappings `15m→1H`, `5m→15m`, `3m→15m`;
- factors `0.8`, `1.0`, `1.2`;
- representations `FIXED_8`, `DIRECTION_RUN`, `ATR_ORIGIN`, `CONFIRMED_DIRECTION_CHANGE`, `HYBRID_ORIGIN`.

Read EXP-024 outputs as frozen source measurements. Recompute from the same raw archives only when necessary for validation. Do not modify EXP-024 files or raw data.

## Frozen episode construction

Construct episodes independently for each mapping and factor from EXP-024 detections using only information available at detection time.

Represent every detection by its closed child-time interval `[counter_start, counter_end]` and direction.

Create three predeclared episode views:

1. `STRICT_NONOVERLAP`
   - sort detections by `counter_start`, then `counter_end`, then deterministic source id;
   - retain the first detection;
   - reject every later detection whose interval overlaps any retained interval;
   - touching intervals where the next start equals the retained end are non-overlapping.

2. `CONNECTED_COMPONENT`
   - build interval-overlap connected components within the same mapping, factor and direction;
   - two detections are connected when their closed-open intervals `[start,end)` overlap directly or transitively;
   - one component is one episode;
   - episode start is the minimum start, episode end the maximum end;
   - representative detection is the earliest start, then earliest end, then deterministic source id.

3. `PARENT_WINDOW_COMPONENT`
   - group detections within the same mapping, factor and direction when their source windows share at least one completed parent bar;
   - use transitive connected components;
   - representative selection is identical to `CONNECTED_COMPONENT`.

Do not merge opposite directions. Do not use price similarity, geometry, representation validity, contrast or later behaviour to merge or split episodes.

## Shared-parent cross-mapping audit

For `3m→15m` and `5m→15m`, construct a separate cross-mapping dependence table at each factor:

- match episodes when they share direction and at least one 15m parent bar in their source windows;
- report one-to-one, one-to-many and unmatched components;
- preserve both mapping identities;
- do not collapse them into a preferred scale.

## Required measurements

For each mapping, factor and episode view report:

- raw detection count;
- episode count and compression ratio;
- retained/rejected counts;
- episode duration in child bars and minutes;
- detections per episode q25/q50/q75/max;
- overlap depth and maximum simultaneous detections;
- UP/DOWN and chronological-third support;
- rate per 1,000 parent bars;
- factor overlap with factor 1.0 using episode representatives;
- concentration by calendar day and parent bar;
- representation validity and invalid reasons on representative detections;
- age q25/q50/q75, unique ages and entropy;
- cap-hit and minimum-history rates;
- origin disagreement from `FIXED_8`;
- normalized displacement, efficiency, boundary distance and extreme distance;
- direction and chronological-third stability;
- paired comparison between raw detections and episode representatives.

For every representation, preserve the representative detection’s original causal measurements. Do not average origins across detections in an episode.

## Primary robustness questions

Answer explicitly:

1. Does at least one non-fixed representation remain non-degenerate after de-overlap on at least two mappings?
2. Does `CONFIRMED_DIRECTION_CHANGE` retain broad age support and high validity after compression?
3. Are EXP-024 similarities driven mainly by repeated detections from the same episode?
4. Do 3m and 5m remain descriptively consistent after accounting for their shared 15m parent dependence?
5. Do conclusions reverse across factors, directions, chronological thirds or episode views?
6. Is any apparent robustness caused by selecting only valid origins or by a few dense calendar periods?

## Frozen stability criteria

A representation is episode-robust on a mapping only when all are true in both `STRICT_NONOVERLAP` and `CONNECTED_COMPONENT` views at factor 1.0:

- at least 300 valid representative episodes;
- at least 5 unique parent ages;
- age entropy at least 1.0 bit;
- invalid rate no greater than 5%;
- no single chronological third contains more than 45% of support;
- both directions contain at least 25% of support;
- median age-bin ordering and the signs of the principal rank relationships do not reverse between the two views.

Factor stability requires the same representation to satisfy the support, entropy and invalidity rules at factors 0.8 and 1.2, with no systematic direction or time-third reversal.

Do not lower these thresholds after observing results.

## Controls and counterexamples

Use deterministic source-excluded, non-overlapping controls inherited from EXP-024 where compatible. Rebuild controls against episode representatives only if needed, preserving the same causal rules.

Export examples of:

- a dense raw cluster collapsing to one episode;
- a representation that appears variable in raw detections but collapses after de-overlap;
- factor-specific episode fragmentation;
- opposite conclusions between strict and connected-component views;
- 3m/5m shared-parent duplication;
- validity-selected apparent robustness;
- direction or chronological-third reversal;
- a stable independent episode with clearly distinct non-fixed origins.

## Decision

Select exactly one verdict:

- `EPISODE_ROBUST_TRANSFER_SUPPORTED` — at least one non-fixed representation is episode-robust and factor-stable on at least two mappings, including one of `3m→15m` or `5m→15m`, without shared-parent duplication, validity selection or temporal concentration explaining the result.
- `EPISODE_ROBUST_TRANSFER_PARTIAL` — non-degenerate independent structure remains, but only one mapping or one episode view is robust, or shared-parent/factor/time dependence remains material.
- `EPISODE_ROBUST_TRANSFER_REJECTED` — the lower-timeframe form largely disappears, becomes redundant, reverses or fails frozen support/stability criteria after de-overlap.
- `EPISODE_AUDIT_FAILED` — frozen EXP-024 measurements or exact raw sources cannot be validated reproducibly.

Do not force a positive verdict and do not select a preferred representation from downstream contrast.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/REPORT.md`
- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/episode_membership.csv`
- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/episode_summary.csv`
- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/representation_robustness.csv`
- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/factor_stability.csv`
- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/shared_parent_dependence.csv`
- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/raw_vs_episode.csv`
- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/counterexamples.csv`
- `experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/experiment_025.py`

Do not create or modify any other repository path. Do not commit raw archives, temporary extracts, `__pycache__` or `.pyc` files.

## Python and validation requirements

`experiment_025.py` must deterministically regenerate all eight data/report outputs from frozen EXP-024 outputs and validated source data; implement all three episode views exactly; preserve membership of every raw detection; reproduce representative selection and all report values; and derive the verdict entirely from generated fields.

Before PASS:

1. Validate all required EXP-024 input files, schemas and hashes or document reproducible source validation.
2. Verify every raw detection belongs to exactly one component in component views and is retained or rejected explicitly in strict view.
3. Verify opposite directions are never merged.
4. Verify connected components are invariant to input row order.
5. Verify representative selection is deterministic.
6. Verify touching intervals follow the declared closed-open rule.
7. Verify parent-window components use completed parent-bar identities only.
8. Verify 3m/5m shared-parent matching is independent of downstream geometry.
9. Verify all frozen support, entropy, invalidity, direction and time thresholds.
10. Verify raw-versus-episode comparisons use identical fields and bins.
11. Verify controls are causal, source-excluded and non-overlapping.
12. Verify no representation, factor, mapping or episode view is selected from outcomes.
13. Run twice and verify identical SHA-256 hashes for all nine outputs.
14. Parse every CSV and reproduce REPORT values and verdict.
15. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/experiment_025.py`, remove cache artifacts, run `git diff --check`, and perform baseline-relative allowlist validation.
16. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 or EXP-013 through EXP-024 file, committed source datasets, raw market data or any path outside the nine EXP-025 outputs. Existing dirty files must remain byte-identical, unstaged and uncommitted.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-025 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.
