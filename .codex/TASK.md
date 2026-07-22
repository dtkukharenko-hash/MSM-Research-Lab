# Current Codex Task

- task_id: `EXP-034A2-TEMPORAL-FEATURE-CORE-CONFORMANCE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `INFRASTRUCTURE`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `false`
- commit_message: `EXP-034A2 temporal feature core conformance`

## Purpose

Build and independently verify only the deterministic causal joins, feature primitives, development-only threshold freezing, and prefix-invariance layer required by the later temporal-state engine.

This task deliberately excludes the state machine, movement phases, event matching, null models, baselines, stability metrics, scientific acceptance, and every real-market calculation.

EXP-034A, EXP-034A1, and every EXP-033 attempt are failed technical evidence. Do not copy, import, repair, inspect for implementation guidance, or use their code, fixtures, expected values, outputs, parameters, metrics, or verdicts. Preserve every earlier path byte-for-byte.

The only permitted result is one exact line in `REPORT.md`:

- `Feature core status: FEATURE_CORE_READY`; or
- `Feature core status: FEATURE_CORE_FAILED`.

## Strict boundary

Use deterministic synthetic fixtures only.

Do not open:

- DATA-002 files;
- any market-data path;
- API or network resources;
- files for ADA, BTC, ETH, or any real instrument;
- any EXP-033, EXP-034A, or EXP-034A1 implementation or evidence file.

No trading concepts or metrics are permitted.

## Required module

Create `temporal_feature_core.py` as an importable Python standard-library module. It must not execute evidence generation at import time.

Canonical row schema:

`timestamp_utc,open,high,low,close,volume,turnover`

Timestamps identify bar opens and must be strictly increasing canonical UTC values. Numeric inputs must be finite. Prices must be positive; volume and turnover must be nonnegative; OHLC ordering must be valid. Invalid rows raise a documented `ValueError`; insufficient but otherwise valid causal history returns `UNKNOWN` values.

The module must expose the following documented deterministic functions.

### 1. `join_closed_daily(primary_rows, daily_rows)`

For every primary 4H row opening at `t`, emission occurs at `t+4h`. A daily row opening at `d` becomes available only at `d+24h`. Select the latest daily row satisfying:

`d + 24h <= t + 4h`

Return explicit `UNKNOWN` when no closed daily row exists. Never select a same-day daily row before it closes.

### 2. `join_closed_children(primary_rows, child_rows)`

For a primary 4H row `[t,t+4h)`, require exactly four valid 1H children opening at `t`, `t+1h`, `t+2h`, and `t+3h`. All must be closed by the parent close. Missing, duplicate, off-grid, invalid, or borrowed children produce explicit `UNKNOWN` for that parent.

### 3. `compute_features(rows, scale)`

Use current and earlier closed bars only. The returned row must expose at least:

`timestamp_utc,true_range,atr14,ema27,normalized_slope,normalized_displacement,efficiency,overlap_density,volatility_percentile`

Implement exactly:

- true range: `max(high-low, abs(high-prev_close), abs(low-prev_close))`;
- first true range uses `high-low` because no previous close exists;
- ATR14: simple trailing mean of 14 true ranges, first valid at index 13;
- EMA27: alpha `2/28`, seeded at index 26 by the SMA of closes 0..26, then recursively updated;
- normalized EMA slope: `(EMA27[t]-EMA27[t-k])/ATR14[t]`;
- normalized displacement: `(close[t]-close[t-w])/ATR14[t]`;
- efficiency: `abs(close[t]-close[t-w]) / sum(abs(close[i]-close[i-1]))` for `i=t-w+1..t`; zero denominator is `UNKNOWN`;
- overlap density: mean over the configured adjacent pairs of `max(0,min(high_i,high_j)-max(low_i,low_j))/min(range_i,range_j)`; a nonpositive denominator makes that pair `UNKNOWN`, and any unknown required pair makes the feature `UNKNOWN`;
- trailing volatility percentile: deterministic rank of current ATR14 against exactly the preceding 96 completed ATR14 values, excluding current. Use `count(previous < current) + 0.5 * count(previous == current)`, divided by 96.

Fixed windows:

- scale `4H`: `k=3`, `w=12`, overlap over 6 adjacent pairs;
- scale `1H`: `k=6`, `w=24`, overlap over 12 adjacent pairs.

Reject every other scale.

### 4. `freeze_thresholds(development_features)`

Calculate separately for one supplied scale population:

- `S70=q70(abs(normalized_slope))`;
- `S50=q50(abs(normalized_slope))`;
- `D70=q70(abs(normalized_displacement))`;
- `D50=q50(abs(normalized_displacement))`;
- `E30=q30(efficiency)`;
- `O70=q70(overlap_density)`.

Use the explicit nearest-rank convention:

- sort finite values ascending;
- for quantile `q`, select one-based rank `ceil(q*n)`, clamped to `1..n`;
- return the value at zero-based index `rank-1`.

Return threshold values, valid population counts for every field, and SHA-256 over canonical UTF-8 rows of the exact development feature population used. Validation or appended future rows must never alter frozen thresholds.

### 5. `assert_prefix_invariance(prefix_rows, appended_rows, scale)`

Compute the prefix alone and the concatenated sequence. Freeze thresholds from prefix features only in both cases. Require byte-identical canonical representations for every prefix feature row and the threshold object. Mutating appended rows may alter only appended outputs, never prefix outputs or thresholds. Return a structured result and raise `AssertionError` on violation.

## Mandatory independent tests

Create `test_temporal_feature_core.py` with Python `unittest`, not pytest. Expected values must be literal hand-calculated constants or results of an independent oracle implemented in the test file. The test/evidence generator must never call the module under test to construct expected values.

Publish exactly one substantive `test_results.csv` row for each requirement below, with the same `test_id`, actual unittest name, status, and concrete observed-versus-expected evidence:

1. `DAILY_CLOSE_INTRADAY` — joins at primary opens 00:00, 04:00, and 20:00;
2. `DAILY_YEAR_BOUNDARY` — correct prior closed day across 31 December/1 January;
3. `DAILY_UNCLOSED_REFUSAL` — same-day unclosed row is never selected;
4. `CHILD_EXACT_FOUR` — exact four-child mapping;
5. `CHILD_INVALID_VARIANTS` — missing, duplicate, off-grid, and borrowed children rejected separately;
6. `ROW_VALIDATION` — invalid numeric, OHLC, duplicate timestamp, and non-monotonic timestamp rejected separately;
7. `TRUE_RANGE_GAPS` — high-low and both gap branches checked with literal values;
8. `ATR14` — first-valid index and hand-calculated value;
9. `EMA27` — seed and at least two recursive updates compared to literal values exposed by `compute_features`;
10. `NORMALIZED_SLOPE_DISPLACEMENT` — literal expected values for both 4H and 1H windows;
11. `EFFICIENCY_UNKNOWN` — zero denominator returns `UNKNOWN`, with a nonzero literal control;
12. `OVERLAP_DENSITY` — no overlap, partial overlap, full overlap, clipping, and zero-range rejection;
13. `VOLATILITY_PERCENTILE` — exactly 96 prior observations, current excluded, ties handled by the frozen formula;
14. `NEAREST_RANK_QUANTILES` — q30/q50/q70 on odd and even literal populations;
15. `THRESHOLD_FUTURE_ISOLATION` — drastically mutated appended rows do not change prefix-frozen thresholds or population hash;
16. `PREFIX_INVARIANCE` — every canonical prefix feature row remains byte-identical after appending at least 40 later rows;
17. `DETERMINISTIC_EVIDENCE` — two complete clean generations have equal hashes for every deterministic substantive output.

A test that only checks successful return is insufficient. The real unittest process exit code and parsed test names must determine `test_results.csv`; blanket PASS rows are prohibited.

## Synthetic evidence

Create a deterministic valid fixture containing:

- at least 180 primary 4H bars;
- the exact matching 1H child grid;
- sufficient daily rows crossing a year boundary;
- flat, monotonic, alternating, gap-up, gap-down, overlapping, and non-overlapping segments.

Store the valid fixture in `synthetic_feature_fixture.csv.gz` using deterministic gzip bytes with `mtime=0` and a fixed filename header.

Invalid variants used by tests must be constructed explicitly in the test file and must not contaminate the valid fixture.

`expected_feature_results.json` must contain literal/oracle expected values and explanatory formula inputs. It must be written without importing or calling `temporal_feature_core.py`.

## Required outputs

Create exactly the 11 paths in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-034A2_TEMPORAL_FEATURE_CORE_CONFORMANCE/`

Required evidence:

- `REPORT.md`;
- `PROTOCOL.md` with all formulas, availability rules, unknown handling, and quantile convention;
- `API_CONTRACT.md` with function signatures, input/return schemas, and error behavior;
- `temporal_feature_core.py`;
- `test_temporal_feature_core.py`;
- `synthetic_feature_fixture.csv.gz`;
- `expected_feature_results.json`;
- `test_results.csv` with exactly 17 requirement rows;
- `run_hashes.csv` with `path,run1_sha256,run2_sha256,equal` for every deterministic substantive output except itself and `resource_usage.csv`;
- `resource_usage.csv` with measured peak RSS for both complete runs;
- `implementation_audit.csv`.

No placeholders, blanket assertions, omitted rows, or contradictory PASS claims are permitted.

## Execution and acceptance

`test_temporal_feature_core.py` must support:

- `--self-test --temp-dir PATH`;
- `--generate-evidence --output-dir PATH --temp-dir PATH`.

Run two complete clean evidence generations in separate external directories. Each generation must run the complete unittest suite, generate all deterministic outputs except `run_hashes.csv` and `resource_usage.csv`, and fail nonzero on any failed/skipped/error test.

Compare hashes before publishing. Measure peak RSS for each generation and require each below `262144 KiB`.

Use `/dev/shm` or supplied external temporary directories. Set `PYTHONDONTWRITEBYTECODE=1` and an external `PYTHONPYCACHEPREFIX`. Do not create repository-local caches, bytecode, logs, SQLite, journals, coverage files, temporary files, or partial files.

`Feature core status: FEATURE_CORE_READY` is permitted only when:

- all 17 independently substantive tests pass;
- every API/formula and error behavior is documented;
- expected values are independent of the implementation under test;
- paired deterministic hashes all match;
- RSS evidence passes;
- allowlist and immutable-state checks pass;
- auditor independently executes the suite using external cache/temp paths and returns PASS.

Otherwise declare `Feature core status: FEATURE_CORE_FAILED` and return a technical correction verdict.

## Immutable state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including all EXP-033 and EXP-034 attempt paths.

Preserve the protected Pine byte-identically and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md`.

## Role contract

Planner verifies the synthetic-only boundary, fresh output directory, exact 11-path allowlist, Python/unittest availability, external temp storage, and immutable baseline.

Implementer creates the complete feature core and independent evidence. It returns `TECHNICAL_CORRECTION_REQUIRED` rather than PASS if any requirement is incomplete.

Auditor independently checks every formula, literal/oracle expectation, causal availability rule, threshold freeze, prefix-isolation proof, exact 17-row test evidence, paired hashes, RSS measurement, allowlist equality, and immutable state. It must execute the tests with all cache/temp paths outside the repository.

Corrector may repair only the 11 allowlisted outputs and external temporary run directories. It must remove task-created non-allowlisted paths without touching baseline paths.

No role may return `USER_DECISION_REQUIRED`. Technical defects are `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

On final auditor PASS, orchestrator may commit and push exactly the 11 allowlisted files.
