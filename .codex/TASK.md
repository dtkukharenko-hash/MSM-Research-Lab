# Current Codex Task

- task_id: `EXP-034A3-TEMPORAL-STATE-MACHINE-CONFORMANCE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `INFRASTRUCTURE`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `false`
- commit_message: `EXP-034A3 temporal state machine conformance`

## Purpose

Build and independently verify only the deterministic causal state machine that consumes the accepted temporal feature-core output.

The only permitted report line is exactly one of:

- `State machine status: STATE_MACHINE_READY`
- `State machine status: STATE_MACHINE_FAILED`

This task makes no statement about ADA or market structure. Event matching, null models, EMA baselines, stability metrics, scientific acceptance, and every real-market calculation remain excluded.

## Pinned accepted dependency

Use the accepted feature core only from:

`experiments/EXP-034A2R1_TEMPORAL_FEATURE_CORE_CONFORMANCE/temporal_feature_core.py`

Required provenance:

- implementation commit: `244f4ae95146fbe374e7b701167a72ce73d04049`
- Git blob SHA: `8f21d9073c66dbf19b9e2164b7e45b8d8166601a`
- file SHA-256: `29f2dd7cf5391b7df60fa9d9754f845581d472b77ec3cef74d22a3bb80b74521`

Planner and auditor must verify all three values. Do not copy, modify, replace, or regenerate the accepted feature core or its evidence. The new module consumes feature rows matching its output schema.

## Strict boundary

Use deterministic synthetic feature rows only.

Do not open:

- DATA-002 or any market-data path;
- API or network resources;
- files for ADA, BTC, ETH, or any real instrument;
- failed EXP-033, EXP-034A, or EXP-034A1 implementation/evidence files.

No trading concepts or metrics are permitted.

## Required module

Create `temporal_state_machine.py` as a Python standard-library importable module.

Expose:

`build_states(feature_rows, thresholds)`

### Input feature-row schema

Each row must contain:

- `timestamp`: strictly increasing UTC bar-open timestamp;
- `scale`: `4H` or `1H`;
- `normalized_slope`;
- `normalized_displacement`;
- `efficiency`;
- `overlap_density`;
- `retracement`.

`retracement` is a causal non-negative finite value supplied by the caller. The state module must not infer it from future rows.

A feature value may be the explicit string `UNKNOWN`. Invalid, non-finite, duplicate-timestamp, non-monotonic, mixed-scale, or malformed input must be rejected or emitted as specified below. Never substitute zero for unavailable data.

### Threshold schema

For the selected scale require finite non-negative:

- `S70`, `S50`, `D70`, `D50`, `E30`, `O70`.

Require `S70 >= S50`, `D70 >= D50`, and `0 <= E30 <= 1`, `0 <= O70 <= 1`.

### Output row schema

For every input row return an immutable row containing:

- `timestamp`;
- `raw_direction`: `-1`, `0`, `+1`, or `UNKNOWN`;
- `confirmed_direction`: `-1`, `0`, `+1`, or `UNKNOWN`;
- `direction`: `-1`, `0`, `+1`, or `UNKNOWN`;
- `phase`: exactly `UNKNOWN`, `DENSITY`, `EMERGING`, `DEVELOPING`, `CORRECTION`, or `TERMINATING`;
- `age`: non-negative integer;
- `density_gate`, `support_gate`, `correction_gate`, `weak_termination_gate` booleans or `UNKNOWN`.

No previously emitted output row may be revised.

## Deterministic state semantics

### 1. Invalid or unavailable row

If any required feature is `UNKNOWN`, emit:

- `raw_direction=UNKNOWN`;
- `confirmed_direction=UNKNOWN`;
- `direction=UNKNOWN`;
- `phase=UNKNOWN`;
- `age=0`.

Reset active direction, age, weak-termination count, raw-confirmation history, and pending opposite direction.

### 2. Raw direction

For a valid row:

- `+1` when slope `>= S70`, displacement `>= D70`, and efficiency `> E30`;
- `-1` when slope `<= -S70`, displacement `<= -D70`, and efficiency `> E30`;
- otherwise `0`.

The strict efficiency comparison is intentional. Equality to `E30` does not qualify.

### 3. Confirmation

A non-zero direction is confirmed only when the current and immediately preceding valid raw directions are equal and non-zero.

Otherwise `confirmed_direction=0`.

An `UNKNOWN` row clears confirmation history.

### 4. Inactive state

When no active parent exists:

- if a pending opposite direction exists after termination and the current raw direction equals it, emit `EMERGING`, activate it, and set age `0`;
- otherwise, if current `confirmed_direction` is non-zero, emit `EMERGING`, activate it, and set age `0`;
- otherwise emit `DENSITY` only when efficiency `<= E30` and overlap `>= O70`;
- otherwise emit `UNKNOWN` with direction `0` and age `0`, without inventing a phase.

### 5. Active-state priority

When an active direction exists, evaluate in this exact order:

1. confirmed opposite direction;
2. two-bar weak retracement termination;
3. correction;
4. developing fallback.

#### Confirmed opposite direction

If `confirmed_direction == -active_direction`, the current bar must emit `TERMINATING`, never `EMERGING`.

Output `direction` as the terminating parent direction, set age `0`, clear the active parent after emission, and store the opposite direction as pending. The next valid bar may emit opposite `EMERGING` only if its raw direction continues to equal that pending direction.

#### Weak retracement termination

`weak_termination_gate` is true when:

- `retracement >= 0.618`; and
- `abs(normalized_slope) < S50`.

Two consecutive valid bars with this gate true terminate the active parent on the second bar. The first weak bar does not terminate. Any valid false gate or `UNKNOWN` resets the weak count.

#### Correction

For active `+1`, correction gate is:

- displacement `<= -D50`; and
- retracement `< 0.618`.

For active `-1`, use the sign-symmetric condition:

- displacement `>= D50`; and
- retracement `< 0.618`.

When true, emit `CORRECTION` and retain the parent.

#### Developing

For active `+1`, support gate is slope `>= S50` or displacement `>= D50`.

For active `-1`, support gate is slope `<= -S50` or displacement `<= -D50`.

If no higher-priority termination or correction condition fired, emit `DEVELOPING`. Preserve the support-gate boolean even when false; this fallback prevents an active parent from disappearing without an explicit termination rule.

### 6. Age

- `EMERGING`: age `0`;
- every subsequent `DEVELOPING` or `CORRECTION` bar retaining the parent: previous age plus `1`;
- `TERMINATING`, `DENSITY`, and `UNKNOWN`: age `0`;
- opposite `EMERGING` begins a new parent at age `0`.

### 7. Prefix invariance

Appending later feature rows must leave every output field belonging to the original prefix byte-identical. Thresholds are input constants and must never be refit by this module.

## Mandatory independent tests

Use `unittest`. Expected values must be literals or independently calculated oracle logic that does not call `build_states` to create expectations.

Publish at least these 24 distinct substantive test methods and exactly one `test_results.csv` row per executed method:

1. pinned dependency commit/blob/SHA-256 verification;
2. positive raw direction including threshold equality;
3. negative sign symmetry;
4. efficiency equality to `E30` produces raw zero;
5. one non-zero raw bar does not confirm;
6. two equal consecutive non-zero raw bars confirm;
7. zero raw between candidates prevents confirmation;
8. `UNKNOWN` clears confirmation and all active state;
9. density exact threshold boundaries;
10. valid inactive non-density row emits `UNKNOWN` without activation;
11. positive `EMERGING` at second confirming bar;
12. negative `EMERGING` symmetry;
13. `EMERGING → DEVELOPING` age sequence `0 → 1`;
14. repeated developing ages increment exactly;
15. positive-parent correction literal case;
16. negative-parent correction sign symmetry;
17. correction retains parent and increments age;
18. confirmed opposite emits `TERMINATING`, not `EMERGING`;
19. terminating bar resets age and records pending opposite;
20. opposite direction emerges only on the following continuing raw bar;
21. one weak-retracement bar does not terminate;
22. two consecutive weak-retracement bars terminate and interruption resets the count;
23. prefix invariance and no retroactive revision;
24. invalid thresholds, non-finite values, mixed scale, duplicate timestamp, and non-monotonic timestamp rejection.

A test that only checks absence of exceptions is insufficient.

## Synthetic fixture

Create one deterministic valid fixture of at least 80 feature rows containing labelled segments for:

- initial `UNKNOWN`;
- `DENSITY`;
- positive `EMERGING`, `DEVELOPING`, `CORRECTION`, and recovery;
- weak-retracement `TERMINATING`;
- negative `EMERGING`, `DEVELOPING`, and `CORRECTION`;
- confirmed-opposite `TERMINATING` followed by delayed opposite `EMERGING`;
- alternating non-confirming raw directions;
- age resets and increments.

Store it as deterministic gzip with `mtime=0` and a fixed filename header.

`expected_state_results.json` must contain independently produced literal expected rows for the full fixture and explicit oracle cases for every mandatory transition. It must be generated without importing `temporal_state_machine.py`.

Invalid variants belong only inside tests and must not contaminate the valid fixture.

## Evidence generation

`test_temporal_state_machine.py` must support:

- `--self-test --temp-dir PATH`
- `--generate-evidence --output-dir PATH --temp-dir PATH`

Evidence generation must actually execute unittest. `test_results.csv` must be derived from executed test IDs and outcomes, never discovered names or blanket PASS rows.

Run two complete clean evidence generations in separate external directories. Compare every deterministic substantive output except `run_hashes.csv` and `resource_usage.csv`.

`run_hashes.csv` schema:

`path,run1_sha256,run2_sha256,equal`

Measure actual peak RSS for both complete runs in `resource_usage.csv`; each must remain below `262144 KiB`.

Use `/dev/shm` or supplied external temporary directories. Set `PYTHONDONTWRITEBYTECODE=1` and an external `PYTHONPYCACHEPREFIX`. Do not create repository-local cache, bytecode, logs, SQLite, journal, partial, coverage, or temporary files.

## Required outputs

Create exactly the 11 allowlisted files under:

`experiments/EXP-034A3_TEMPORAL_STATE_MACHINE_CONFORMANCE/`

- `REPORT.md`
- `PROTOCOL.md`
- `API_CONTRACT.md`
- `temporal_state_machine.py`
- `test_temporal_state_machine.py`
- `synthetic_state_fixture.csv.gz`
- `expected_state_results.json`
- `test_results.csv`
- `run_hashes.csv`
- `resource_usage.csv`
- `implementation_audit.csv`

`STATE_MACHINE_READY` is permitted only when the pinned dependency is verified, all mandatory tests pass, literal expected transitions are independent, opposite-direction termination semantics pass, two-bar weak termination passes, age semantics pass, prefix invariance passes, paired hashes match, measured RSS passes, all files reopen, and repository boundaries pass.

Otherwise report `STATE_MACHINE_FAILED` and return `TECHNICAL_CORRECTION_REQUIRED`.

## Immutable state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including all earlier EXP-033/EXP-034 attempts and the accepted feature core.

Preserve the protected Pine byte-identically and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md`.

## Role contract

Planner verifies the fresh A3 directory, exact 11-path allowlist, pinned dependency provenance, Python/unittest, external temp storage, synthetic-only boundary, and immutable baseline.

Implementer creates the complete state module and independently generated evidence. Missing or ambiguous semantics are technical failures, not user decisions.

Auditor independently verifies every state priority, direction confirmation, pending-opposite behavior, weak termination, correction symmetry, age rule, full expected fixture, deterministic runs, RSS, allowlist equality, dependency provenance, and immutable state.

Corrector modifies only A3 allowlisted files and regenerates the complete evidence package after any code or test change.

No role may return `USER_DECISION_REQUIRED`. Technical defects are `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

On final auditor PASS, orchestrator may commit and push exactly the 11 A3 files.
