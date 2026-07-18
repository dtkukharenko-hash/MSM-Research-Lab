# Current Codex Task

- task_id: `EXP-023-ADA-LOWER-TIMEFRAME-DATA`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-022-ADA-LOWER-TIMEFRAME-TRANSFER`
- commit_message: `EXP-023 ADA lower timeframe data`

## Objective

Obtain a content-verifiable official ADAUSDT linear kline archive at 3m, 5m and 15m, audit its integrity, and freeze a local-data manifest suitable for rerunning EXP-022.

This is data acquisition and validation only. Do not run the parent/counter detector, representation comparison or any downstream structural analysis.

## Authorised external source

Use the official Bybit V5 public REST endpoint only:

- `GET https://api.bybit.com/v5/market/kline`
- `category=linear`
- `symbol=ADAUSDT`
- intervals exactly `3`, `5`, `15`

Do not use mark-price, index-price, premium-index, spot or third-party candles. Do not use authenticated endpoints. Record the endpoint, request parameters, retrieval time and every response error/retry.

## Storage contract

Raw candle archives are intentionally not committed to GitHub.

Store them under exactly:

- `${HOME}/.local/share/msm-market-data/bybit/linear/ADAUSDT/ADAUSDT_3m.csv`
- `${HOME}/.local/share/msm-market-data/bybit/linear/ADAUSDT/ADAUSDT_5m.csv`
- `${HOME}/.local/share/msm-market-data/bybit/linear/ADAUSDT/ADAUSDT_15m.csv`

Write through temporary files and atomically replace the final file only after validation. Never modify committed ADA 1H/4H archives.

CSV schema must be deterministic:

`timestamp_utc,open,high,low,close,volume,turnover`

Use UTC ISO-8601 timestamps, ascending order and canonical decimal text. Exclude the currently open terminal candle.

## Frozen acquisition range

Read the committed ADA 1H source selected by EXP-021 and use its exact first and last complete timestamps as the target comparison range.

For each requested interval:

1. retrieve all available closed bars covering that range;
2. paginate deterministically with API limit 1000;
3. deduplicate by start timestamp;
4. sort ascending;
5. preserve only bars whose full interval is closed;
6. do not fabricate bars outside Bybit availability;
7. record any unavailable prefix/suffix explicitly.

Use bounded retries with exponential backoff for transient HTTP, timeout and non-zero API return codes. Fail closed on malformed responses or non-monotonic pagination.

## Required audit

For each 3m, 5m and 15m archive measure:

- first/last timestamp and row count;
- expected versus observed timestamps;
- missing-bar count and contiguous gap episodes;
- duplicate and non-monotonic timestamps;
- numeric parsing and finite values;
- OHLC relationships and non-positive prices;
- negative volume/turnover;
- UTC alignment;
- incomplete terminal bars;
- SHA-256 and byte size.

No interpolation, forward fill or synthetic candles are allowed.

## Cross-interval validation

Using only complete UTC-aligned components:

- aggregate 3m → 15m and compare field-by-field against native 15m;
- aggregate 5m → 15m and compare field-by-field against native 15m;
- aggregate native 15m → 1H and compare OHLC field-by-field against the committed EXP-021 selected 1H archive over exact overlap;
- volume and turnover are audited but not compared with committed 1H when those fields are absent there.

Report exact-match counts, mismatch counts, maximum absolute/relative differences and mismatch timestamp samples. Do not choose a source based on downstream results.

## Readiness rule

Assign each interval exactly one status:

- `READY` — adequate coverage, zero internal missing bars in the frozen usable range, valid OHLCV and no unresolved conflicts;
- `PARTIAL` — valid data exist but coverage or gaps prevent full use;
- `CONFLICTED` — native and independently aggregated values materially disagree without a documented precision-only explanation;
- `UNAVAILABLE` — no usable official data were retrieved;
- `FAILED` — acquisition or validation failed.

Set `EXP022_RERUN_READY=true` only when:

1. native 3m, 5m and 15m archives are all `READY`;
2. they share a frozen overlap of at least 180 consecutive days;
3. there are zero missing component bars inside that overlap;
4. 3m→15m and 5m→15m match native 15m after canonical decimal tolerance;
5. 15m→1H matches the committed 1H OHLC archive over overlap;
6. exact source paths, hashes, schemas, endpoint and overlap are frozen.

Otherwise set false and list explicit blockers.

## Required outputs

Create exactly these seven committed files:

- `experiments/EXP-023_ADA_LOWER_TIMEFRAME_DATA/REPORT.md`
- `experiments/EXP-023_ADA_LOWER_TIMEFRAME_DATA/acquisition_log.csv`
- `experiments/EXP-023_ADA_LOWER_TIMEFRAME_DATA/integrity_summary.csv`
- `experiments/EXP-023_ADA_LOWER_TIMEFRAME_DATA/gap_episodes.csv`
- `experiments/EXP-023_ADA_LOWER_TIMEFRAME_DATA/cross_interval_validation.csv`
- `experiments/EXP-023_ADA_LOWER_TIMEFRAME_DATA/data_manifest.json`
- `experiments/EXP-023_ADA_LOWER_TIMEFRAME_DATA/experiment_023.py`

Do not commit raw candle archives or create any other repository path.

## Python requirements

`experiment_023.py` must:

- use Python standard library plus already-installed dependencies only;
- download and paginate the official Bybit public kline endpoint reproducibly;
- support safe resume by validating existing local archives before requesting missing ranges;
- write raw archives atomically outside the repository;
- regenerate all six audit/report outputs deterministically from the frozen raw archives;
- hash every raw archive;
- perform all integrity and cross-interval checks;
- derive verdict and `EXP022_RERUN_READY` from measured fields;
- print a compact summary of interval status, coverage, gaps, equality checks, raw paths, hashes, readiness and report path.

The report must distinguish API acquisition facts from local validation results and must not contain strategy language or predictive claims.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 or EXP-013 through EXP-022 file, or any committed source dataset.

The only permitted non-repository writes are the three exact raw archive paths under `${HOME}/.local/share/msm-market-data/bybit/linear/ADAUSDT/` and temporary files beside them. Existing local dirty files must remain byte-identical, unstaged and uncommitted.

## Required validation

Before PASS:

1. Verify the official endpoint response identifies `category=linear`, `symbol=ADAUSDT` and the requested interval.
2. Verify pagination has no loops, overlaps after deduplication or skipped requested ranges.
3. Verify all final rows are closed, ascending, unique and UTC-aligned.
4. Verify all OHLCV/turnover values are finite and relationships are valid.
5. Verify all gaps and unavailable prefixes/suffixes are explicit.
6. Re-read the final raw CSVs and reproduce their hashes and audit metrics.
7. Verify deterministic 3m→15m, 5m→15m and 15m→1H construction from complete components only.
8. Verify mismatch summaries reproduce from source rows and tolerances are declared before results.
9. Verify `data_manifest.json`, REPORT values, verdict and readiness reproduce from CSV outputs.
10. Run the audit generation twice without redownloading and verify identical SHA-256 hashes for all seven committed outputs.
11. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-023_ADA_LOWER_TIMEFRAME_DATA/experiment_023.py`, then remove generated cache artifacts.
12. Run `git diff --check` and baseline-relative allowlist validation.
13. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the seven allowlisted EXP-023 outputs unstaged. Raw data remain outside the repository. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.
