# Current Codex Task

- task_id: `DATA-001-BYBIT-2025-READINESS`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `DATA`
- data_ready: `false`

## Objective

Perform data acquisition and mandatory readiness validation for the exact 2025 source panel required by EXP-031. This is a data-only task. Do not calculate EXP-031 observations, inspect EXP-030R cell outcomes, or perform any research test.

The task must finish with an explicit `DATA_READY=YES` or `DATA_READY=NO`. No later research task may start from this package unless every mandatory source row is `READY` and the package reports `DATA_READY=YES`.

## Frozen requirements

Use exactly:

- symbols: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `XRPUSDT`;
- market category: Bybit V5 `linear`;
- UTC interval: `2025-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z`;
- source kinds: trade-price `15m` kline, funding history, and open interest at `15min` cadence;
- persistent root: environment variable `MSM_MARKET_DATA_ROOT`, expected production value `/home/nnv/.local/share/msm-market-data`.

Use only official Bybit V5 public endpoints:

- `https://api.bybit.com/v5/market/kline` with `category=linear` and `interval=15`;
- `https://api.bybit.com/v5/market/funding/history` with `category=linear`;
- `https://api.bybit.com/v5/market/open-interest` with `category=linear` and `intervalTime=15min`.

Do not use unofficial mirrors, synthetic values, interpolation, forward fill, gap fill, cross-symbol replacement, or reconstructed OI/funding.

## Phase 1: cheap preflight before bulk work

Before downloading full files:

1. inspect all existing persistent archives and the exact source paths/hashes recorded by committed EXP-031 `data_provenance.csv`;
2. verify whether each of the twelve symbol/source combinations already covers the complete 2025 interval;
3. perform one bounded official API probe for the beginning and end of 2025 for each source kind;
4. stop bulk acquisition for a source immediately if the official endpoint cannot return records in the requested period;
5. persist the probe result in `request_summary.csv`.

This phase must run first. Bulk acquisition is permitted only for source combinations whose official probe succeeds and whose local archive is incomplete.

## Phase 2: acquisition and canonical persistence

Create `data_001.py` using only the Python standard library.

For each incomplete but available source:

1. download bounded, deterministic UTC windows with documented endpoint limits;
2. retry transient failures with bounded backoff and record final request counts/status;
3. parse decimal strings without rounding them through binary formatting when writing canonical CSV;
4. sort strictly ascending by timestamp and deduplicate only byte-equivalent duplicate timestamps;
5. treat conflicting duplicate timestamps as `INVALID`;
6. merge the validated 2025 rows with the byte-validated pre-2025 archive identified by EXP-031 provenance;
7. atomically write the canonical combined file under:
   - `$MSM_MARKET_DATA_ROOT/bybit/linear/<SYMBOL>/<SYMBOL>_15m.csv`
   - `$MSM_MARKET_DATA_ROOT/bybit/linear/<SYMBOL>/<SYMBOL>_funding.csv`
   - `$MSM_MARKET_DATA_ROOT/bybit/linear/<SYMBOL>/<SYMBOL>_oi.csv`
8. write an adjacent deterministic `.meta.json` containing endpoint, frozen request parameters, schema, row count, first/last timestamp, gap count and SHA-256. Do not include volatile retrieval timestamps in canonical metadata.

Canonical schemas must remain compatible with EXP-027/EXP-031:

- kline: preserve the existing canonical header; when no valid base exists use `timestamp_utc,open,high,low,close,volume,turnover`;
- funding: preserve the existing canonical header; when no valid base exists use `timestamp_utc,funding_rate`;
- OI: preserve the existing canonical header; when no valid base exists use `timestamp_utc,open_interest`.

Never overwrite a valid canonical file until the replacement has passed all checks and is fsync-complete. Preserve the previous file on any failure.

## Readiness validation

Validate the 2025 slice independently from the combined archive.

For every symbol/source combination record:

- official endpoint;
- canonical persistent path;
- canonical SHA-256;
- schema;
- requested first/last timestamps;
- actual first/last timestamp;
- 2025 row count;
- expected row count;
- duplicate count;
- conflicting duplicate count;
- gap count;
- off-grid count;
- non-finite/invalid numeric count;
- source status and reason.

Fixed expectations:

- each `15m` kline file: 35,040 rows, first `2025-01-01T00:00:00Z`, last `2025-12-31T23:45:00Z`, exact 15-minute grid;
- each `15min` OI file: 35,040 rows with the same first/last timestamps and grid;
- each funding file: 1,095 rows, first `2025-01-01T00:00:00Z`, last `2025-12-31T16:00:00Z`, exact 8-hour grid required by the frozen EXP-027 protocol.

A source is `READY` only when all expectations pass, the schema is compatible, every numeric value is finite, and the canonical SHA-256 is recorded. Otherwise use `PARTIAL`, `MISSING`, `UNAVAILABLE` or `INVALID` with an explicit reason.

`DATA_READY=YES` requires exactly twelve `READY` source rows. Any other result is `DATA_READY=NO`. Do not force a positive status.

## Required outputs

Create exactly these six repository files:

- `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- `data/readiness/DATA-001_BYBIT_2025/readiness_manifest.csv`
- `data/readiness/DATA-001_BYBIT_2025/gaps.csv`
- `data/readiness/DATA-001_BYBIT_2025/request_summary.csv`
- `data/readiness/DATA-001_BYBIT_2025/run_hashes.csv`
- `data/readiness/DATA-001_BYBIT_2025/data_001.py`

Raw/canonical market archives and their `.meta.json` files belong only under the persistent market-data root and must not be added to Git.

## Output contracts

`readiness_manifest.csv` must contain exactly twelve rows, one per symbol/source combination, plus columns sufficient to prove every readiness check listed above.

`gaps.csv` must contain one row per missing expected timestamp or conflicting duplicate. When no gaps exist, retain the header with zero data rows.

`request_summary.csv` must record local-preflight status, beginning/end API probe status, whether bulk acquisition ran, request count, records received and final endpoint status for each of the twelve combinations.

`REPORT.md` must state the exact overall status, summarize all failures, and print `DATA_READY=YES` only when all twelve rows are `READY`.

`run_hashes.csv` must record SHA-256 for the other five repository outputs and for all twelve canonical persistent CSV files. It must not hash itself. Hashes must be computed after final writes; no hashed file may be rewritten afterward.

## Validation

Before returning PASS:

1. compile with bytecode redirected outside the repository;
2. confirm no `__pycache__`, `.pyc`, temporary download, or partial file exists in the repository;
3. run `git diff --check` on task-created files;
4. verify exactly the six allowlisted repository paths are task-created;
5. verify all canonical archives are outside Git and under the persistent root;
6. independently reopen every canonical CSV and recompute all manifest counts and hashes;
7. ensure the protected EXP-009 Pine remains byte-identical and unstaged.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `PROJECT_INSTRUCTIONS.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any existing experiment file, or any EXP-009 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Planner must treat absent outputs as normal. Implementer creates the six outputs. Auditor verifies them and the persistent archives. Corrector changes only the six allowlisted files and external persistent archives, leaving repository files unstaged.
