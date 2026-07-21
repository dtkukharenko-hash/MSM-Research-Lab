# Current Codex Task

- task_id: `DATA-002-ADAUSDT-2023-2025-READINESS`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `DATA`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `false`
- commit_message: `DATA-002 ADAUSDT 2023-2025 readiness`

## Objective

Acquire and independently validate the complete Bybit linear-perpetual ADAUSDT OHLCV history required by the ADA-only temporal-structure study.

This is a data-readiness task. It makes no market-structure, predictive, transfer, or trading claim.

The successful result must provide a committed manifest declaring `DATA_READY=YES` and persistent canonical ADA files from which closed 1H, 4H, and 1D bars can be reproduced exactly.

## Exact market boundary

Use only:

- exchange: Bybit;
- API: official Bybit V5 public market API;
- category: `linear`;
- symbol: `ADAUSDT`;
- source kind: kline/OHLCV only;
- native acquisition interval: `15` minutes;
- start inclusive: `2023-01-01T00:00:00Z`;
- end exclusive: `2026-01-01T00:00:00Z`.

Do not request, read, persist, count, summarize, or inspect any timestamp on or after `2026-01-01T00:00:00Z`.

BTC, ETH, SOL, XRP, every other symbol, funding, open interest, trades, order books, and third-party datasets are prohibited.

Do not substitute another market or synthesize missing ADA bars.

## Official source

Use the official endpoint:

`https://api.bybit.com/v5/market/kline`

Frozen request parameters:

- `category=linear`;
- `symbol=ADAUSDT`;
- `interval=15`;
- `limit<=1000`;
- every request must have explicit bounded `start` and `end` values inside the allowed interval;
- the largest permitted end value is `2025-12-31T23:59:59.999Z`.

Record every request window, attempt count, HTTP/API status, returned-row count, minimum returned timestamp, maximum returned timestamp, and whether any returned row fell outside its requested window.

Use bounded retries with deterministic maximum attempt counts and bounded backoff. Never loop indefinitely.

## Persistent canonical data

Use the writable directory supplied by `MSM_MARKET_DATA_ROOT`. Do not write market archives into the Git repository.

Create these canonical persistent files:

- `bybit/linear/ADAUSDT/ADAUSDT_15m_2023_2025.csv`;
- `bybit/linear/ADAUSDT/ADAUSDT_1h_2023_2025.csv`;
- `bybit/linear/ADAUSDT/ADAUSDT_4h_2023_2025.csv`;
- `bybit/linear/ADAUSDT/ADAUSDT_1d_2023_2025.csv`.

Create an adjacent deterministic metadata JSON for each canonical CSV. Each metadata file must include source endpoint, frozen request parameters, period bounds, interval, schema, row count, first and last timestamp, gap count, duplicate counts, SHA-256, creation program identity, and aggregation parent when applicable.

Canonical CSV schema:

`timestamp_utc,open,high,low,close,volume,turnover`

Timestamps identify bar opens and must use canonical UTC form `YYYY-MM-DDTHH:MM:SSZ`.

Preserve numeric values as deterministic decimal strings. Reject non-finite values. Prices must be positive; volume and turnover must be nonnegative; `high >= max(open, close, low)` and `low <= min(open, close, high)` must hold.

Write files atomically. A candidate file may replace a canonical file only after full validation passes. Never replace a valid canonical archive with a partial or invalid candidate.

## Expected complete grids

For the exact three-calendar-year interval, require:

- 15m: `105216` bars, first `2023-01-01T00:00:00Z`, last `2025-12-31T23:45:00Z`;
- 1H: `26304` bars, first `2023-01-01T00:00:00Z`, last `2025-12-31T23:00:00Z`;
- 4H: `6576` bars, first `2023-01-01T00:00:00Z`, last `2025-12-31T20:00:00Z`;
- 1D: `1096` bars, first `2023-01-01T00:00:00Z`, last `2025-12-31T00:00:00Z`.

Every expected timestamp must exist exactly once. Any missing timestamp, conflicting duplicate, off-grid timestamp, malformed row, invalid numeric value, or timestamp outside the frozen interval prevents `DATA_READY=YES`.

Identical duplicate rows must also prevent readiness and must be reported explicitly rather than silently deduplicated.

## Deterministic aggregation

Construct 1H, 4H, and 1D only from the validated 15m source.

UTC bar boundaries:

- 1H requires exactly 4 consecutive 15m children;
- 4H requires exactly 16 consecutive 15m children and opens at hours `00,04,08,12,16,20`;
- 1D requires exactly 96 consecutive 15m children and opens at `00:00:00Z`.

Aggregation rules:

- open: first child open;
- high: maximum child high;
- low: minimum child low;
- close: last child close;
- volume: exact decimal sum of child volumes;
- turnover: exact decimal sum of child turnovers.

Do not emit an aggregate bar when any expected child is missing, duplicated, conflicting, invalid, or off-grid. No interpolation or gap filling is allowed.

Validate every aggregate row independently against its children and record mismatch counts.

## Acquisition procedure

1. Verify that `MSM_MARKET_DATA_ROOT` exists or can be created and is writable.
2. Perform bounded official-API probes at the beginning and end of the frozen interval.
3. Acquire all 15m windows with no overlap ambiguity and no request outside the frozen interval.
4. Canonicalize and validate the complete 15m grid before publishing it.
5. Build and validate 1H, 4H, and 1D files.
6. Run two clean validation-only passes against the persisted canonical files.
7. Require equal row counts, first/last timestamps, issue counts, and SHA-256 results across the two validation passes.
8. Reopen every CSV and JSON artifact after writing.

The script must be restart-safe. Existing canonical data may be reused only after schema, period, identity, and SHA validation. Resume logic must never treat an unvalidated partial file as canonical.

## Required repository outputs

Create exactly the ten paths in `.codex/ALLOWLIST.txt` under:

`data/readiness/DATA-002_ADAUSDT_2023_2025/`

Required contents:

- `REPORT.md` — human-readable readiness result;
- `acquire_data_002.py` — complete deterministic acquisition and validation implementation;
- `readiness_manifest.csv` — one row per canonical interval with identity, path, hash, coverage, counts, and status;
- `gaps.csv` — every missing timestamp, duplicate, conflict, off-grid row, invalid row, aggregation-child defect, or out-of-range row; header-only when none;
- `request_summary.csv` — every official request/probe and bounded retry outcome;
- `aggregation_checks.csv` — child-count and OHLCV reconciliation for 1H/4H/1D;
- `source_provenance.csv` — endpoint, parameters, period, schema, persistent path, metadata path, and hashes;
- `run_hashes.csv` — the two independent validation-pass results;
- `implementation_audit.csv` — boundary, identity, persistence, atomic-write, memory, and repository-cleanliness checks;
- `test_results.csv` — self-tests and end-to-end acceptance checks.

No repository-local market archive, SQLite file, journal, cache, bytecode, shard, partial, temporary file, or log is permitted.

## Required script interface

`acquire_data_002.py` must support:

- `--self-test --temp-dir PATH`;
- `--acquire --temp-dir PATH`;
- `--validate-existing --temp-dir PATH`.

Self-tests must use local fixtures only and must cover at minimum:

- descending API response ordering;
- exact UTC grid construction;
- duplicate and conflicting-duplicate detection;
- missing-child aggregate rejection;
- OHLC and decimal-sum aggregation;
- out-of-range timestamp rejection;
- refusal to publish partial candidates;
- deterministic CSV/JSON bytes;
- atomic replacement behavior.

Use Python standard library where practical. Use streaming/chunking or disk-backed temporary state outside the repository. Peak RSS must remain below `1,048,576 KiB`. Every repository output must remain below 95 MiB.

## Readiness decision

`REPORT.md` may declare all of the following only when every mandatory check passes:

- `Overall status: READY`;
- `DATA_READY=YES`;
- `Instrument: ADAUSDT Bybit linear`;
- exact frozen interval and expected counts;
- no access to 2026;
- four canonical persistent files validated;
- two validation passes identical.

If any mandatory check fails, declare `Overall status: DATA_FAILED` and `DATA_READY=NO`. Never create a READY manifest from placeholders, empty tables, inferred coverage, another symbol, or incomplete acquisition.

The auditor returns `PASS` only for `DATA_READY=YES` with direct verification of all persistent files, metadata, request boundaries, counts, hashes, aggregate reconciliation, rerun identity, allowlist equality, and immutable repository state.

## Immutable repository state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including all EXP-031 and EXP-032 attempt paths.

The protected Pine must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md` or any pre-existing tracked bytecode/cache path.

## Role contract

Planner verifies official API reachability, exact ADAUSDT linear identity, writable persistent storage, the frozen interval, expected counts, and feasibility. It returns technical correction rather than creating evidence when acquisition is not actionable.

Implementer acquires and validates the data, creates all ten allowlisted evidence files, creates no repository path outside the allowlist, and leaves changes unstaged.

Auditor independently reopens persistent files and metadata, recalculates hashes and coverage, checks request boundaries and aggregate reconciliation, verifies two validation passes, and returns `PASS` only when `DATA_READY=YES` is justified mechanically.

Corrector fixes only technical defects inside the allowlist or reruns bounded acquisition/validation. It may not weaken coverage, identity, interval, gap, duplicate, aggregation, or readiness requirements.

No role may return `USER_DECISION_REQUIRED`. Missing data, API failure, storage failure, ambiguity, or implementation defects are technical outcomes.

On final auditor `PASS`, the orchestrator may stage, commit, and push exactly the ten allowlisted DATA-002 repository files. Persistent market files remain outside Git.
