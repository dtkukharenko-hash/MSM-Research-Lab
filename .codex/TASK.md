# Current Codex Task

- task_id: `EXP-034A-ADA-TEMPORAL-ENGINE-CONFORMANCE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `INFRASTRUCTURE`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `false`
- commit_message: `EXP-034A ADA temporal engine conformance`

## Purpose

Build and independently verify a reusable deterministic temporal-state and evaluation engine before any further ADA scientific run.

EXP-033 and EXP-033R1 failed technical audit because the implementation used missing or fake hierarchy nulls, a relabelled rather than independently calculated EMA-only baseline, direction-agnostic event matching, incomplete split metrics, skeletal reports, and contradictory PASS assertions. Those outputs are failed technical evidence only.

Do not copy, import, repair, or use code, outputs, parameters, metrics, or verdicts from EXP-033 or EXP-033R1. Preserve every earlier path byte-for-byte.

This task makes no statement about ADA market structure. It uses synthetic fixtures only and may declare only `ENGINE_READY=YES` or `ENGINE_READY=NO`.

## Boundary

Do not open market-data files, DATA-002 canonical CSV files, API endpoints, network resources, BTC, ETH, ADA, or any real instrument data.

All fixtures must be generated deterministically inside the task implementation from explicit constants and written only to the allowlisted fixture file or external temporary directories.

No trading concepts or metrics are permitted.

## Required reusable API

Implement `temporal_engine.py` as an importable standard-library module with documented deterministic functions equivalent to the following contracts:

1. `join_closed_daily(primary_rows, daily_rows)`
   - timestamps identify bar opens;
   - a primary 4H row opening at `t` emits at `t+4h`;
   - a daily row opening at `d` becomes available only at `d+24h`;
   - choose the latest daily row satisfying `d+24h <= t+4h`;
   - never use the current unclosed daily row.

2. `join_closed_children(parent_rows, child_rows)`
   - for a 4H parent `[t,t+4h)`, require exactly the four 1H children opening at `t,t+1h,t+2h,t+3h`;
   - all children must be valid and closed by the parent close;
   - a missing, duplicate, conflicting, invalid, or off-grid child produces `UNKNOWN`, never interpolation.

3. `fit_thresholds(development_rows, fixed_spec)`
   - deterministic quantile convention documented in `API_CONTRACT.md`;
   - calculate only from the supplied development rows;
   - return threshold values plus population hashes;
   - changing validation rows must not change thresholds.

4. `compute_features(rows, fixed_spec)`
   - true range, ATR14, EMA27, normalized EMA slope, normalized displacement, efficiency, overlap density, trailing volatility percentile excluding current, and causal retracement;
   - unavailable inputs are explicit `UNKNOWN`/null values;
   - no centered windows or future extrema.

5. `emit_states(feature_rows, thresholds, fixed_spec)`
   - direction separate from phase;
   - phases exactly `UNKNOWN,DENSITY,EMERGING,DEVELOPING,CORRECTION,TERMINATING`;
   - two-bar directional confirmation;
   - age begins at zero on `EMERGING` and resets only on termination, unknown, or opposite emerging;
   - no backward revision.

6. `match_events_same_direction(events, references, window_bars)`
   - match only equal directions;
   - one reference event may be used at most once;
   - deterministic nearest-lag assignment with documented tie-break;
   - an opposite-direction reference inside the window must never count as a match.

7. `circular_shift_null(events, references, quarters, replications, seed)`
   - preserve event count separately inside each calendar quarter;
   - use deterministic independent within-quarter circular shifts;
   - produce replicate-level precision, recall, and lift inputs.

8. `phase_block_permutation_null(phases, quarters, replications, seed)`
   - identify maximal contiguous phase blocks;
   - preserve every block label and duration;
   - permute whole blocks only within the same quarter;
   - preserve quarter lengths and block multiset exactly;
   - return replicate-level hierarchy statistics.

9. `ema_only_baseline(rows, thresholds, fixed_spec)`
   - use only normalized EMA27 slope, the same frozen slope threshold, and the same two-bar confirmation;
   - generate its own events and metrics independently;
   - never relabel full-engine metrics as baseline metrics.

10. Metric functions for:
   - start and termination correspondence;
   - age/progress Spearman, age-quartile medians, and ordering violations;
   - correction versus development quartiles, medians, Cliff's delta, expected sign, and development/validation sign agreement;
   - hierarchy observed statistic, null distribution, and lift;
   - direction, half-year, quarter, daily-context, and volatility splits;
   - quarterly event concentration;
   - `INSUFFICIENT_SAMPLE` for fewer than 10 relevant events.

11. `evaluate_verdict(criteria, stability, implementation_gate)`
   - mechanically implement the frozen ACCEPT/PARTIAL/REJECT/DATA_FAILED decision table;
   - return `DATA_FAILED` whenever the implementation gate is false.

Function names may differ only if `API_CONTRACT.md` maps every required contract to the exact implemented symbol.

## Synthetic fixture design

Create deterministic fixtures containing at least:

- 40 daily bars crossing a year boundary;
- corresponding 4H bars and 1H child bars;
- directional, density, correction, termination, unknown, and opposite-direction episodes;
- reference starts and ends of both directions;
- at least two calendar quarters;
- enough rows for all rolling features;
- deliberate missing-child, duplicate-child, opposite-direction-nearby-reference, and unclosed-daily traps.

Persist the canonical fixture as deterministic `synthetic_bars.csv.gz` with fixed gzip filename header and `mtime=0`. Persist exact expected outputs in `expected_results.json`.

## Mandatory tests

`test_temporal_engine.py` must use only Python's standard library and execute all tests without pytest. Every test must independently assert values rather than only checking that a function returns.

At minimum test:

1. Daily close causality at parent openings `00:00`, `04:00`, `20:00`, and across `2024-12-31/2025-01-01`.
2. A same-day unclosed daily bar is never joined.
3. Exact four-child 1H join and `UNKNOWN` on missing/duplicate/conflicting child.
4. Development-only threshold isolation: mutate all validation values and prove threshold bytes/hashes unchanged.
5. EMA27, ATR14, displacement, efficiency, overlap, volatility-rank, and retracement against hand-calculated fixture values.
6. Every state transition, two-bar confirmation, age increment, and age reset.
7. No backward revision when later rows are appended.
8. Same-direction start/termination matching; opposite-direction references are rejected.
9. Deterministic nearest-lag tie-break and one-to-one reference usage.
10. Circular-shift null has exactly 1000 replicates, preserves per-quarter event counts, and is byte-deterministic for seed `340034`.
11. Phase-block null has exactly 1000 replicates and every replicate preserves quarter boundaries, each block label, each duration, block multiset, and total length.
12. Hierarchy statistic is calculated from permuted sequences, not a constant; fixture replicate values must contain at least two distinct values.
13. EMA-only baseline is generated independently and differs from the full engine on at least one explicitly identified fixture event.
14. Age metric direction/half-year/quarter splits and ordering violations.
15. Correction quartiles, Cliff's delta, and sign-agreement calculation.
16. Daily-context, volatility, direction, half-year, and quarter stability splits.
17. Quarterly concentration calculation.
18. `INSUFFICIENT_SAMPLE` behavior below 10 events.
19. Every branch of ACCEPT/PARTIAL/REJECT/DATA_FAILED decision logic.
20. Deterministic CSV, JSON, and gzip bytes.
21. Importing and running the module creates no repository cache or bytecode.

A test that contains a hard-coded PASS without verifying the underlying calculation is itself a failure.

## Required interfaces

`temporal_engine.py` must support:

- `--self-test --temp-dir PATH`;
- `--fixture-run --output-dir PATH --temp-dir PATH`.

`test_temporal_engine.py` must support:

- `--run --engine PATH --output-dir PATH --temp-dir PATH`.

Both commands must return nonzero on any failed assertion.

## Required outputs

Create exactly the 12 paths in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-034A_ADA_TEMPORAL_ENGINE_CONFORMANCE/`

- `REPORT.md` — explicit `ENGINE_READY=YES` or `ENGINE_READY=NO`; no ADA verdict;
- `PROTOCOL.md` — fixture and audit procedure;
- `API_CONTRACT.md` — exact mapping of every required API contract to implemented functions;
- `temporal_engine.py` — reusable implementation;
- `test_temporal_engine.py` — independent executable conformance tests;
- `synthetic_bars.csv.gz` — deterministic fixture;
- `expected_results.json` — hand-defined expected outputs and invariants;
- `null_fixture_results.csv` — observed and 1000-replicate null summaries, distinct-value counts, preservation checks;
- `test_results.csv` — one row per mandatory test with actual evidence field and PASS/FAIL;
- `run_hashes.csv` — `path,run1_sha256,run2_sha256,equal`;
- `resource_usage.csv` — peak RSS for both clean runs;
- `implementation_audit.csv` — API completeness, placeholder scan, repository boundary, deterministic and resource checks.

## Determinism and repository safety

Run the full fixture generation and test suite twice into separate clean directories outside the repository. Every substantive output except `run_hashes.csv` and `resource_usage.csv` must be byte-identical.

Use fixed seed `340034`. Peak RSS for each run must be measured and below `1,048,576 KiB`.

All temporary, cache, bytecode, logs, and generated run directories must be outside the repository. Set `PYTHONDONTWRITEBYTECODE=1` and an external `PYTHONPYCACHEPREFIX`. Do not use pytest.

All outputs must reopen successfully and remain below 95 MiB. Leave task outputs unstaged. No task-created path may exist outside the allowlist.

Preserve all pre-existing dirty, tracked, and untracked paths byte-for-byte, including every EXP-033 and EXP-033R1 path. Preserve the protected Pine byte-identically, dirty and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md` or pre-existing tracked cache/bytecode paths.

## Acceptance

`ENGINE_READY=YES` is permitted only when:

- all 12 outputs exist;
- all mandatory tests PASS with concrete evidence;
- real 1000-replicate hierarchy and circular-shift nulls are present;
- the EMA-only baseline is independently generated;
- all API contracts are mapped and tested;
- two clean runs are byte-identical;
- peak RSS evidence passes;
- no placeholder, constant-null, relabelled-baseline, skipped calculation, or contradictory PASS assertion exists;
- repository boundary and immutable-state checks pass.

Otherwise declare `ENGINE_READY=NO` and return `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

## Role contract

Planner verifies the fresh output directory, exact allowlist, external temp capability, and that the task is fully synthetic and technically actionable.

Implementer creates the complete reusable module, independent tests, fixtures, and all evidence. It must run the full suite twice before returning PASS. It may not use failed EXP-033 code.

Auditor reads the complete implementation and test code, reruns both commands in external clean directories, inspects replicate-level invariants and baseline independence, verifies every test has concrete evidence, scans for placeholder constants and copied EXP-033 code, and checks repository state against baseline.

Corrector must regenerate any incomplete allowlisted implementation or evidence and rerun the entire suite. It may not decline correction merely because several allowlisted files need regeneration. It may not weaken tests or replace calculations with descriptive text.

No role may return `USER_DECISION_REQUIRED`. Technical defects are `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

On final auditor PASS, the orchestrator may commit and push exactly the 12 allowlisted EXP-034A paths.
