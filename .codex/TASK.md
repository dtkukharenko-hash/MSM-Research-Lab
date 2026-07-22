# Current Codex Task

- task_id: `EXP-034A1-TEMPORAL-STATE-CORE-CONFORMANCE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `INFRASTRUCTURE`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `false`
- commit_message: `EXP-034A1 temporal state core conformance`

## Purpose

Build and independently verify only the deterministic causal state core needed by the later ADA experiment.

This task is intentionally smaller than EXP-034A. It does not implement event matching, null models, EMA baselines, stability splits, scientific acceptance, or any ADA calculation. Those belong to a separate future conformance task after this core is accepted.

EXP-034A and every EXP-033 attempt are failed technical evidence. Do not copy, import, repair, or use their code, fixtures, outputs, parameters, metrics, or verdicts. Preserve every earlier path byte-for-byte.

The only permitted result is:

- `ENGINE_CORE_READY=YES`; or
- `ENGINE_CORE_READY=NO`.

## Strict boundary

Use deterministic synthetic fixtures only.

Do not open:

- DATA-002 files;
- any market-data path;
- API or network resources;
- files for ADA, BTC, ETH, or any real instrument.

No trading concepts or metrics are permitted.

## Required module

Create `temporal_state_core.py` as an importable Python standard-library module.

It must expose documented deterministic functions with these contracts.

### 1. Closed daily join

`join_closed_daily(primary_rows, daily_rows)`

- timestamps identify bar opens;
- each primary row is a 4H bar opening at `t` and emitted at `t+4h`;
- each daily row opens at `d` and becomes available only at `d+24h`;
- select the latest daily row satisfying `d+24h <= t+4h`;
- return explicit `UNKNOWN` when no closed daily row exists;
- never use the current unclosed daily row.

### 2. Closed child join

`join_closed_children(primary_rows, child_rows)`

For a 4H row `[t,t+4h)`:

- require exactly four 1H children opening at `t`, `t+1h`, `t+2h`, and `t+3h`;
- every child must be valid and closed by `t+4h`;
- missing, duplicated, off-grid, or invalid children produce explicit `UNKNOWN` for that parent;
- never borrow a child from another parent window.

### 3. Causal feature calculation

`compute_features(rows, scale)`

Use only current and earlier closed bars. Implement:

- true range: `max(high-low, abs(high-prev_close), abs(low-prev_close))`;
- ATR14: simple trailing mean of 14 true ranges;
- EMA27: recursive EMA with alpha `2/28`, seeded by the first available 27-close SMA;
- normalized EMA slope: `(EMA27[t]-EMA27[t-k])/ATR14[t]`;
- normalized displacement: `(close[t]-close[t-w])/ATR14[t]`;
- efficiency: `abs(close[t]-close[t-w]) / sum(abs(close[i]-close[i-1]))` over the same window;
- overlap density: mean adjacent-candle range intersection divided by the smaller positive range, clipped to `[0,1]`;
- trailing volatility percentile: rank of current ATR14 against the preceding 96 completed ATR14 values, excluding current.

Fixed windows:

- 4H: `k=3`, `w=12`, overlap over 6 adjacent pairs;
- 1H: `k=6`, `w=24`, overlap over 12 adjacent pairs.

Insufficient or invalid history returns `UNKNOWN`, never zero-filled data.

### 4. Development-only thresholds

`freeze_thresholds(development_features)`

Calculate separately per scale:

- `S70=q70(abs(normalized_slope))`;
- `S50=q50(abs(normalized_slope))`;
- `D70=q70(abs(normalized_displacement))`;
- `D50=q50(abs(normalized_displacement))`;
- `E30=q30(efficiency)`;
- `O70=q70(overlap_density)`.

Use one documented deterministic quantile convention. Return exact values, valid-population counts, and a SHA-256 over the canonical development feature population.

Validation or appended future rows must never alter frozen thresholds.

### 5. State machine

`build_states(features, thresholds)`

Direction is separate from phase and must be `-1`, `0`, `+1`, or `UNKNOWN`.

Raw direction:

- `+1` when slope `>=S70`, displacement `>=D70`, and efficiency `>E30`;
- `-1` under sign-symmetric conditions;
- otherwise `0`;
- confirmed direction requires two consecutive equal nonzero raw directions.

Emit exactly:

- `UNKNOWN` — insufficient or invalid history;
- `DENSITY` — no confirmed direction, efficiency `<=E30`, overlap `>=O70`;
- `EMERGING` — first emitted bar of a newly confirmed nonzero direction different from the active parent;
- `DEVELOPING` — active direction remains supported by same-sign slope or displacement at magnitude `>=S50` or `D50`;
- `CORRECTION` — active parent remains intact, no confirmed opposite direction, counter-direction displacement magnitude `>=D50`, and causal retracement `<0.618`;
- `TERMINATING` — confirmed opposite raw direction, or retracement `>=0.618` together with `abs(slope)<S50` for two consecutive bars.

Age:

- starts at zero on `EMERGING`;
- increases by one per completed bar while the parent remains active;
- resets on `TERMINATING`, `UNKNOWN`, or opposite `EMERGING`;
- no previously emitted state may be revised.

### 6. Prefix invariance

`assert_prefix_invariance(prefix_rows, appended_rows, scale)`

Recomputing after appending later rows must leave every feature, threshold input, direction, phase, and age belonging to the original prefix byte-identical.

## Mandatory independent tests

Create `test_temporal_state_core.py` using `unittest`, not pytest.

The tests must independently calculate expected values rather than call the function under test to derive expectations.

At minimum test:

1. daily join at 00:00, 04:00, and 20:00 primary opens;
2. daily join across a year boundary;
3. refusal to use the same-day unclosed daily row;
4. exact four-child 1H join;
5. missing-child, duplicate-child, and off-grid-child rejection;
6. true range including gap cases;
7. ATR14 first-valid index and value;
8. EMA27 seed and recursive update;
9. normalized slope and displacement;
10. zero-denominator efficiency gives `UNKNOWN`;
11. overlap clipping and zero-range handling;
12. volatility percentile excludes the current observation;
13. deterministic quantile convention;
14. mutation of validation/future rows does not change development thresholds;
15. two-bar direction confirmation;
16. `UNKNOWN → DENSITY` behavior;
17. `EMERGING → DEVELOPING → CORRECTION → TERMINATING` fixture sequence;
18. age increment and every reset rule;
19. opposite emerging behavior;
20. prefix invariance;
21. invalid numeric and non-monotonic timestamp rejection;
22. deterministic bytes across two clean runs.

A test that merely checks that a function returns without exception is insufficient.

## Synthetic evidence

Create one deterministic fixture covering:

- at least 160 primary 4H bars;
- matching 1H children;
- matching daily rows;
- directional, density, correction, termination, and unknown segments;
- a year boundary;
- deliberate invalid variants used only by tests.

Store the valid fixture in `synthetic_state_fixture.csv.gz` with deterministic gzip bytes (`mtime=0`, fixed filename header).

Store independently calculated expected values and expected state transitions in `expected_state_results.json`.

## Outputs

Create exactly the 11 paths in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-034A1_TEMPORAL_STATE_CORE_CONFORMANCE/`

Required evidence:

- `REPORT.md` — declares `ENGINE_CORE_READY=YES` only when every mandatory test and audit passes;
- `PROTOCOL.md` — formulas, availability times, unknown handling, quantile convention, and state transition rules;
- `API_CONTRACT.md` — function signatures, input schemas, return schemas, and error behavior;
- `temporal_state_core.py` — complete implementation;
- `test_temporal_state_core.py` — independent test suite;
- `synthetic_state_fixture.csv.gz`;
- `expected_state_results.json`;
- `test_results.csv` — one row per mandatory test with PASS/FAIL and substantive evidence;
- `run_hashes.csv` — `path,run1_sha256,run2_sha256,equal` for deterministic outputs;
- `resource_usage.csv` — measured peak RSS for both runs;
- `implementation_audit.csv` — boundary, API completeness, test independence, determinism, allowlist, and immutable-state checks.

No placeholder rows or blanket PASS assertions are permitted.

## Script and test execution

`test_temporal_state_core.py` must support:

- `--self-test --temp-dir PATH`;
- `--generate-evidence --output-dir PATH --temp-dir PATH`.

Run two complete clean evidence generations in separate external directories. Compare hashes before publishing the allowlisted outputs.

Use `/dev/shm` or the supplied external temp directory. Set `PYTHONDONTWRITEBYTECODE=1` and an external `PYTHONPYCACHEPREFIX` for every run.

Peak RSS for each run must be measured and remain below `262144 KiB`.

Do not create repository-local cache, bytecode, log, SQLite, journal, temporary, partial, or coverage files.

## Immutable state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including all EXP-033, EXP-033R1, and EXP-034A paths.

Preserve the protected Pine byte-identically and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md`.

## Role contract

Planner verifies the synthetic-only boundary, fresh output directory, exact 11-path allowlist, Python/unittest availability, external temp storage, and immutable baseline.

Implementer creates the complete core and independent evidence. If any mandatory API or test is missing, return `TECHNICAL_CORRECTION_REQUIRED`, not PASS.

Auditor independently inspects every formula, test expectation, causal availability rule, threshold freeze, state transition, prefix-invariance proof, deterministic run pair, memory measurement, allowlist equality, and immutable path. It must run the test suite with all cache/temp paths outside the repository.

Corrector must complete missing core behavior and tests, regenerate all evidence, and remove every task-created path outside the allowlist without touching baseline paths.

No role may return `USER_DECISION_REQUIRED`. Technical defects are `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

On final auditor PASS, orchestrator may commit and push exactly the 11 allowlisted files.
