# Current Codex Task

- task_id: `EXP-034A2R1-TEMPORAL-FEATURE-CORE-CONFORMANCE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `INFRASTRUCTURE`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `false`
- commit_message: `EXP-034A2R1 focused temporal feature core correction`

## Purpose

Produce a focused, independently auditable correction of the deterministic temporal feature core after EXP-034A2 failed technical audit.

EXP-034A2 established that 17 tests execute, two external runs can be deterministic, and memory is bounded, but acceptance failed because future isolation was not substantively tested, overlap coverage was incomplete, even-population quantiles were absent, and the fixture omitted flat and alternating segments.

This task makes no statement about ADA or market structure. Its only permitted report line is exactly one of:

- `Feature core status: FEATURE_CORE_READY`
- `Feature core status: FEATURE_CORE_FAILED`

## Reuse boundary

The implementer may inspect these EXP-034A2 files only as an implementation starting point:

- `temporal_feature_core.py`
- `test_temporal_feature_core.py`
- `PROTOCOL.md`
- `API_CONTRACT.md`

It may copy and correct code into the new R1 directory.

Do not use EXP-034A2 `REPORT.md`, expected results, test-results rows, hashes, resource records, audit assertions, PASS claims, or verdict as evidence. All R1 evidence must be regenerated independently in clean external directories.

Preserve every EXP-034A2 and earlier path byte-for-byte.

## Strict boundary

Use deterministic synthetic fixtures only. Do not open DATA-002, market-data paths, APIs, network resources, or any real instrument file. No trading concepts or metrics are permitted.

The state machine, movement phases, event matching, null models, baselines, stability metrics, scientific acceptance, and real-market calculation remain excluded.

## Required module

Create `temporal_feature_core.py` as an importable Python standard-library module implementing:

1. `join_closed_daily(primary_rows, daily_rows)`
   - timestamps are bar opens;
   - a 4H primary row at `t` emits at `t+4h`;
   - a daily row at `d` is available only at `d+24h`;
   - select the latest daily row satisfying `d+24h <= t+4h`;
   - return explicit `UNKNOWN` when unavailable;
   - never use the current unclosed daily row.

2. `join_closed_children(primary_rows, child_rows)`
   - for `[t,t+4h)`, require exactly four valid 1H children at `t`, `t+1h`, `t+2h`, `t+3h`;
   - missing, duplicate, off-grid, invalid, or borrowed children produce `UNKNOWN`.

3. `compute_features(rows, scale)`
   - true range: `max(high-low, abs(high-prev_close), abs(low-prev_close))`;
   - ATR14: simple trailing mean of 14 true ranges;
   - EMA27: alpha `2/28`, seeded by the first 27-close SMA, then recursive;
   - normalized slope: `(EMA27[t]-EMA27[t-k])/ATR14[t]`;
   - normalized displacement: `(close[t]-close[t-w])/ATR14[t]`;
   - efficiency: `abs(close[t]-close[t-w]) / sum(abs(close[i]-close[i-1]))`;
   - overlap density: mean adjacent range intersection divided by the smaller positive range, clipped to `[0,1]`;
   - volatility percentile: rank current ATR14 against the preceding 96 completed ATR14 values, excluding current;
   - expose EMA27 and every primitive required for literal audit.

Fixed windows:

- 4H: slope `k=3`, displacement/efficiency `w=12`, overlap over 6 adjacent pairs;
- 1H: slope `k=6`, displacement/efficiency `w=24`, overlap over 12 adjacent pairs.

4. `clip_unit(value)`
   - finite input below zero returns `0.0`;
   - finite input above one returns `1.0`;
   - otherwise return the value;
   - non-finite input is rejected.

5. `nearest_rank(values, probability)`
   - sort finite values ascending;
   - rank is `ceil(probability * n)`, one-based;
   - return the value at zero-based index `rank-1`;
   - reject empty input and probability outside `(0,1]`.

6. `freeze_thresholds(development_features)`
   - separately per scale calculate `S70`, `S50`, `D70`, `D50`, `E30`, `O70`;
   - return exact values, valid population counts, and SHA-256 of the canonical development feature population;
   - validation/appended future rows may never enter the population.

All functions must reject non-monotonic timestamps, duplicate timestamps, invalid OHLC relations, non-finite numbers, and invalid scales. Insufficient history returns explicit `UNKNOWN`, never zero-filled data.

## Mandatory independent tests

Use `unittest`. Expected values must be literals or independently calculated oracle expressions that do not call the function under test to create expectations.

Publish at least these 22 distinct substantive test methods and exactly one `test_results.csv` row per executed method:

1. daily join at 00:00 primary open;
2. daily join at 04:00 and 20:00 primary opens;
3. year-boundary daily join and refusal of same-day unclosed row;
4. exact four-child join;
5. missing child rejection;
6. duplicate and off-grid child rejection;
7. true range with upward and downward gaps;
8. ATR14 first-valid index and literal value;
9. EMA27 seed value;
10. EMA27 first recursive update;
11. normalized slope and displacement literals;
12. zero-denominator efficiency returns `UNKNOWN`;
13. no-overlap literal result `0.0`;
14. full-overlap literal result `1.0`;
15. `clip_unit` literal clipping below zero and above one;
16. zero-range overlap handling;
17. volatility percentile excludes current observation;
18. nearest-rank odd-population literals;
19. nearest-rank even-population literals, including `[1,2,3,4]` at `0.30`, `0.50`, and `0.70`;
20. future isolation: freeze a development prefix, append future rows, mutate only appended rows to extreme values, recompute the full feature series, freeze the same prefix again, and prove every threshold, population count, and population SHA-256 is identical;
21. prefix feature invariance: appended rows leave every feature of the original prefix byte-identical;
22. invalid numeric, invalid OHLC, duplicate timestamp, and non-monotonic timestamp rejection.

Passing without an assertion against a substantive expected value is insufficient. Combining the required overlap or quantile cases into undocumented blanket checks is insufficient.

## Synthetic fixture

Create one deterministic valid fixture containing clearly labelled segments:

- rising trend;
- falling trend;
- gap-up and gap-down cases;
- a flat segment with repeated closes and positive candle ranges;
- an alternating up/down close segment;
- daily rows crossing a year boundary;
- complete 1H children for valid 4H parents.

Deliberate invalid variants must be constructed separately inside tests and must not contaminate the valid fixture.

Store the valid fixture in deterministic gzip with `mtime=0` and a fixed filename header.

`expected_feature_results.json` must contain literal oracle values for every mandatory formula/case, including full overlap, clipping, odd and even quantiles, EMA seed/update, future-isolation hashes, flat-segment behavior, and alternating-segment behavior. It must be produced without importing `temporal_feature_core.py`.

## Evidence generation

`test_temporal_feature_core.py` must support:

- `--self-test --temp-dir PATH`
- `--generate-evidence --output-dir PATH --temp-dir PATH`

`--generate-evidence` must actually execute the unittest suite. `test_results.csv` must be derived from executed test IDs and outcomes, not from discovered names or unconditional PASS rows. Published test-row count must equal the executed test count.

Run two complete clean evidence generations in separate external directories. Compare every deterministic substantive output except `run_hashes.csv` and `resource_usage.csv`. `run_hashes.csv` schema:

`path,run1_sha256,run2_sha256,equal`

Measure peak RSS for both complete runs and record actual values in `resource_usage.csv`; each must remain below `262144 KiB`.

Use `/dev/shm` or supplied external temporary directories. Set `PYTHONDONTWRITEBYTECODE=1` and an external `PYTHONPYCACHEPREFIX`. Do not create repository-local cache, bytecode, log, SQLite, journal, partial, coverage, or temporary files.

## Required outputs

Create exactly the 11 paths in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-034A2R1_TEMPORAL_FEATURE_CORE_CONFORMANCE/`

Required files:

- `REPORT.md`
- `PROTOCOL.md`
- `API_CONTRACT.md`
- `temporal_feature_core.py`
- `test_temporal_feature_core.py`
- `synthetic_feature_fixture.csv.gz`
- `expected_feature_results.json`
- `test_results.csv`
- `run_hashes.csv`
- `resource_usage.csv`
- `implementation_audit.csv`

`FEATURE_CORE_READY` is permitted only when every mandatory test passed, all expected values are independent, the future-isolation test performs real append and mutation, fixture labels include flat and alternating segments, paired-run hashes match, measured RSS passes, all files reopen, and repository boundaries pass.

Otherwise report `FEATURE_CORE_FAILED` and return `TECHNICAL_CORRECTION_REQUIRED`.

## Immutable state

Preserve all pre-existing dirty, tracked, and untracked paths byte-for-byte and unstaged, including every EXP-033/EXP-034 attempt and the protected Pine:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required Pine SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md`.

## Role contract

Planner verifies the exact fresh R1 directory, 11-path allowlist, synthetic boundary, A2 source availability, Python/unittest, external temp storage, and immutable baseline.

Implementer may copy A2 implementation code but must independently repair and regenerate all R1 evidence. It must not copy A2 evidence files.

Auditor independently executes the suite, inspects literal/oracle expectations, verifies all 22 cases, checks real future append/mutation isolation, flat/alternating fixture labels, full-overlap/clipping/even-quantile coverage, paired runs, RSS, allowlist, and immutable state.

Corrector fixes only R1 allowlisted files and external temporary output. It must regenerate the complete evidence package after any code or test change.

No role may return `USER_DECISION_REQUIRED`. Technical defects are `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

On final auditor PASS, orchestrator may commit and push exactly the 11 R1 allowlisted files.
