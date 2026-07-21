# Current Codex Task

- task_id: `EXP-031R4-TEMPORAL-VALIDATION-2025`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`

## Objective

Build the calendar-2025 temporal-validation diagnostic dataset using the frozen EXP-027 and EXP-029R market-state protocol, with bounded-memory streaming implementation. Preserve every committed experiment and every failed runtime attempt. Do not inspect, rank, filter, confirm, or reject EXP-030R cells and do not make a predictive claim.

EXP-031R3 failed technically because its implementation exhausted approximately 31 GiB RAM and all 32 GiB then-active swap, causing a global OOM kill. This is an implementation failure, not a data or scientific verdict. Do not read any uncommitted EXP-031R, EXP-031R2, or EXP-031R3 directory as a protocol source.

This task keeps the corrected R3 reconciliation contract and adds a mandatory bounded-memory architecture. The additional host swap is emergency protection only and must not be treated as working memory.

## Mandatory data gate

Before computation:

1. verify the DATA-001 report SHA-256 above and require `DATA_READY=YES`;
2. verify `data/readiness/DATA-001_BYBIT_2025/readiness_manifest.csv` SHA-256 is `14a43c01de55d3cb82349553ec3abf700a9e49137fba6eea9669d2c2cceba4b2`;
3. require exactly twelve manifest rows and `source_status=READY` for every row;
4. read exact canonical paths from the manifest and verify every `canonical_sha256` before run 1, between runs, and after run 2;
5. independently verify complete 2025 grids for BTCUSDT, ETHUSDT, SOLUSDT, and XRPUSDT;
6. treat canonical files as combined archives: manifest 2025 bounds describe the validated slice and do not imply earlier rows are absent.

The persistent market-data root is read-only. Do not download, rewrite, merge, repair, or replace canonical data.

## Frozen protocol

Use definitions and deterministic helpers committed in:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

Reproduce without tuning:

- BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT;
- FUNDING, OI, JOINT families, frozen sides, and 8H/24H episode views;
- representative selection, episode identities, and exact matched-control rules;
- calendar month and chronological third for the declared interval;
- scales `15m` and `1H`;
- all five frozen representations and thirteen scalar fields;
- explicit `UNKNOWN` values and reasons;
- volatility state from current ATR versus the preceding 96 fully closed bars.

Use only bars fully closed at or before each observation timestamp. No future information, synthetic substitution, interpolation, forward fill, gap fill, or cross-symbol replacement.

## Required implementation

Create:

`experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/experiment_031r4.py`

The implementation must:

1. set `sys.dont_write_bytecode = True` before importing source modules;
2. never call a source experiment `main()`;
3. never parse an empty timestamp; unmatched controls keep an empty timestamp and explicit `UNKNOWN` state;
4. include `representation` in new observation and volatility schemas, identities, and sort keys;
5. use indexed timestamps or bisect-based state lookup;
6. accept an explicit output directory and a worker/run mode;
7. execute run 1 and run 2 sequentially in separate clean temporary directories, never concurrently;
8. write deterministic gzip using an empty filename and `mtime=0`;
9. verify byte-identical substantive outputs before copying one verified run into the repository output directory;
10. emit the complete package even if reconciliation fails: honest 2025 data plus failed integrity checks must produce `TEMPORAL_VALIDATION_DATASET_PARTIAL`, not an absent package.

## Mandatory bounded-memory architecture

The following are acceptance requirements, not suggestions:

1. process one symbol at a time in fixed order `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `XRPUSDT`;
2. release symbol-specific bars, events, controls, observations, reconciliation rows, and indexes before loading the next symbol;
3. write large row populations incrementally to temporary files outside the repository; do not accumulate full observation, volatility, counterexample, or reconciliation populations as Python lists;
4. stream `validation_observations.csv.gz` directly through `csv.DictWriter` and deterministic `gzip.GzipFile`;
5. stream `validation_volatility_state.csv`, `counterexamples.csv`, and committed EXP-029R gzip/CSV inputs;
6. use compact counters, sets only for required uniqueness keys, or disk-backed temporary SQLite tables when identity comparison cannot fit compactly in memory;
7. never use `list(csv.DictReader(...))`, `readlines()`, whole-file `read_text()`, pandas, or equivalent full materialization for large canonical or generated CSV populations;
8. never retain run-1 and run-2 row objects simultaneously; after run 1, close files, delete in-memory objects, invoke garbage collection, then start run 2;
9. compare runs by streaming SHA-256 and row-count metadata, not by loading output bytes or rows into memory;
10. canonical ordering must be achieved by fixed symbol order and deterministic nested iteration, or by disk-backed external sorting outside the repository—not by sorting millions of dictionaries in RAM;
11. temporary shards may exist only in clean temporary directories outside the repository and must be removed after validation;
12. the worker must record peak RSS using `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`; each run must remain below `4,194,304 KiB` (4 GiB);
13. if the implementation cannot remain below the memory ceiling, stop honestly with a bounded failure and do not continue allocating memory or relying on swap;
14. no stage may intentionally consume swap as working storage.

The planner and auditor must inspect the implementation for prohibited full-materialization patterns before accepting it.

## Required row invariants

- observations: `representative_episode_count * 2 roles * 2 scales * 5 representations * 13 fields`;
- volatility: `representative_episode_count * 2 roles * 2 scales * 5 representations`.

Unmatched controls remain included in both invariants as `UNKNOWN`.

## Frozen overlap reconciliation

Use:

`2024-10-01T00:00:00Z <= observation_timestamp < 2024-11-01T00:00:00Z`

Empty timestamps have no interval coordinate and are excluded only from overlap selection.

### Observation reconciliation

For each symbol, stream committed EXP-029R observation rows in the interval, recompute them through the same state path used for 2025, and compare full compound identity including `representation` and `field`. Compare validity, reasons, string fields exactly and numeric values at tolerance `1e-09`. Record counts, missing identities, extra identities, mismatches, and canonical hashes.

### Volatility compatibility reconciliation

Committed EXP-029R `volatility_state.csv` is representation-blind: EXP-029R appended volatility inside the five-representation loop but wrote no `representation` column. Do not invent labels or modify EXP-029R.

For each symbol:

1. stream committed volatility rows in the interval using the committed schema;
2. recompute five representation-labelled rows per episode/role/scale;
3. require all five reconstructed rows for each base identity to have identical volatility fields;
4. project reconstructed rows to the exact committed schema by dropping only `representation`;
5. compare committed and projected rows as canonically sorted multisets, preserving duplicate multiplicity;
6. compare numeric values at tolerance `1e-09` and nonnumeric fields exactly;
7. record counts, multiplicity mismatches, missing rows, extra rows, value mismatches, and canonical hashes.

All four symbols must pass both reconciliation datasets for overall READY.

## Required outputs

Create exactly these twelve files:

- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/REPORT.md`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/data_provenance.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/episodes.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/matched_controls.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/validation_observations.csv.gz`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/validation_volatility_state.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/protocol_reconciliation.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/coverage_summary.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/validation_summary.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/counterexamples.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/run_hashes.csv`
- `experiments/EXP-031R4_TEMPORAL_VALIDATION_2025/experiment_031r4.py`

No other repository path may be created or changed.

## Validation contract

`validation_summary.csv` must independently report PASS/FAIL for:

- DATA-001 report and readiness manifest;
- all twelve canonical hashes before, between, and after runs;
- exact 2025 coverage;
- episode and representative identity uniqueness;
- event/control join completeness;
- both row invariants and compound-identity invariants;
- closed-bar causality and UNKNOWN preservation;
- observation overlap reconciliation for every symbol;
- five-representation volatility invariance;
- volatility compatibility reconciliation for every symbol;
- absence of EXP-030R cell access;
- deterministic two-run equality;
- peak RSS below 4 GiB for each run;
- output sizes and allowlist boundaries;
- absence of newly created cache, bytecode, temporary, or partial repository files relative to baseline.

Pre-existing tracked `__pycache__` or `.pyc` paths are immutable baseline paths: do not delete, modify, stage, or count them as task-created violations.

`protocol_reconciliation.csv` must contain one row per symbol and dataset (`observations`, `volatility_compatibility`) with counts and mismatch diagnostics.

`counterexamples.csv` must stream every unavailable control, UNKNOWN state, reconciliation mismatch, failed invariant, memory-budget failure, and out-of-boundary path with an explicit reason.

`run_hashes.csv` must contain run-1 and run-2 SHA-256 values for the other eleven allowlisted outputs and exclude itself. The script itself may use the same immutable source SHA for both run labels. Do not rewrite hashed outputs after final hash computation.

## Status

`REPORT.md` must use exactly one status:

- `TEMPORAL_VALIDATION_DATASET_READY` when every required validation passes;
- `TEMPORAL_VALIDATION_DATASET_PARTIAL` when honest 2025 rows exist but one or more integrity requirements fail;
- `TEMPORAL_VALIDATION_DATASET_FAILED` when the 2025 dataset itself cannot be constructed honestly within the bounded-memory contract.

This task does not produce ACCEPT/REJECT and does not authorize EXP-032 unless status is `TEMPORAL_VALIDATION_DATASET_READY`.

## Final checks

Reopen final CSV/gzip files by streaming and independently recompute counts and identities. Confirm every output is below 95 MiB, `git diff --check` passes, exactly the twelve allowlisted paths are task-created and unstaged, peak RSS evidence is present, and no new cache or temporary path exists relative to baseline.

Never modify, stage, delete, rename, chmod, or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `PROJECT_INSTRUCTIONS.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, persistent market data, any existing experiment directory, any tracked cache/bytecode path, or any EXP-009 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical with SHA-256 `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`, dirty and unstaged.
