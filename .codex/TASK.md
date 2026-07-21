# Current Codex Task

- task_id: `EXP-031R5-TEMPORAL-VALIDATION-2025`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-031R5 bounded temporal validation dataset`

## Objective

Build an honest calendar-2025 temporal-validation diagnostic dataset using the frozen EXP-027 and EXP-029R market-state protocol. This is a technical repair of EXP-031R4, not a new scientific hypothesis and not a predictive experiment.

EXP-031R3 failed from global memory exhaustion. EXP-031R4 stayed within the memory budget and produced deterministic files, but independent audit rejected its READY claim for four specific implementation defects:

1. `counterexamples.csv` rows were accumulated in a Python list instead of being written incrementally;
2. overlap reconciliation compared serialized rows and identity presence rather than numeric values at tolerance `1e-09` under matching compound identities;
3. observation and volatility compound-identity invariants were not independently validated or reported;
4. the production path imported only EXP-027 and manually reproduced protocol logic instead of using committed deterministic helpers from EXP-027, EXP-029R, and EXP-031.

Correct exactly these defects while preserving the frozen protocol. EXP-031R4 files may be inspected read-only as failed implementation evidence, but they are not protocol evidence and must remain byte-identical, untracked, and unstaged. Do not read any earlier uncommitted EXP-031R, EXP-031R2, or EXP-031R3 directory as a protocol source.

## Mandatory data gate

Before computation:

1. verify the DATA-001 report SHA-256 above and require `DATA_READY=YES`;
2. verify `data/readiness/DATA-001_BYBIT_2025/readiness_manifest.csv` SHA-256 is `14a43c01de55d3cb82349553ec3abf700a9e49137fba6eea9669d2c2cceba4b2`;
3. require exactly twelve manifest rows and `source_status=READY` for every row;
4. read exact canonical paths from the manifest and verify every `canonical_sha256` before run 1, between runs, and after run 2;
5. independently verify complete 2025 grids for BTCUSDT, ETHUSDT, SOLUSDT, and XRPUSDT;
6. treat canonical files as combined archives: manifest 2025 bounds describe the validated slice and do not imply earlier rows are absent.

The persistent market-data root is read-only. Do not download, rewrite, merge, repair, replace, interpolate, forward-fill, gap-fill, or cross-symbol substitute canonical data.

## Frozen protocol sources

Use committed definitions and deterministic helpers from all three modules:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

The production path must import all three modules under distinct aliases after setting `sys.dont_write_bytecode = True`. It must call real deterministic helpers from each module in the actual dataset/reconciliation path, not merely import them or execute a smoke call. Small adapters may normalize arguments and stream outputs, but they must not duplicate protocol logic already available in a committed helper.

At minimum, the implementation must use:

- EXP-027 helpers for ATR, hourly aggregation, representations, and causal state generation;
- EXP-029R helpers/constants for canonical timestamp formatting, scalar fields, numeric formatting/tolerance, and volatility-state compatibility where applicable;
- EXP-031 helpers/constants for the overlap interval, field schemas, identity/reconciliation semantics, and temporal-validation conventions where applicable.

`data_provenance.csv` must include one helper-provenance row per used source module with source path, source SHA-256, helper names used, use site, and a positive production call count. Import-only evidence is FAIL. Calling any source experiment `main()` is forbidden.

Reproduce without tuning:

- symbols BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT;
- FUNDING, OI, and JOINT event families, frozen sides, and 8H/24H episode views;
- representative selection, episode identities, and exact matched-control rules;
- calendar month and chronological third for the declared interval;
- scales `15m` and `1H`;
- all five frozen representations and thirteen scalar fields;
- explicit `UNKNOWN` values and reasons;
- volatility state from current ATR versus the preceding 96 fully closed bars.

Use only bars fully closed at or before each observation timestamp. No future information and no outcome-based selection are permitted. Do not inspect, rank, filter, confirm, or reject EXP-030R cells.

## Required implementation

Create:

`experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/experiment_031r5.py`

The script must:

1. accept an explicit output directory and a worker/run mode;
2. execute run 1 and run 2 sequentially in separate clean temporary directories;
3. write deterministic gzip with empty filename and `mtime=0`;
4. verify byte-identical substantive outputs before copying one verified run into the repository output directory;
5. never parse an empty timestamp; unmatched controls keep an empty timestamp and explicit `UNKNOWN` state;
6. include `representation` in observation and volatility schemas, identities, and deterministic ordering;
7. use indexed timestamps or bisect-based lookup;
8. emit the complete package even when integrity checks fail: honest 2025 rows plus a failed check yield `TEMPORAL_VALIDATION_DATASET_PARTIAL`, not an absent package;
9. never rewrite a hashed output after final hash computation.

## Bounded-memory architecture

These are acceptance requirements:

1. process one symbol at a time in fixed order BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT;
2. release symbol-specific bars, events, controls, indexes, and reconciliation state before loading the next symbol;
3. stream `validation_observations.csv.gz`, `validation_volatility_state.csv`, and `counterexamples.csv` directly through open writers;
4. every counterexample must be written when discovered; a Python list, deque, dataframe, or equivalent population accumulator for counterexamples is forbidden;
5. stream committed EXP-029R observation and volatility inputs;
6. use compact counters and disk-backed temporary SQLite tables for identity joins, multiset comparison, uniqueness checks, and mismatch diagnostics;
7. never use `list(csv.DictReader(...))`, `readlines()`, whole-file `read_text()`, pandas, or equivalent full materialization for large canonical or generated CSV populations;
8. never retain run-1 and run-2 row objects simultaneously;
9. compare runs by streaming SHA-256 and row-count metadata;
10. canonical ordering must come from deterministic nested iteration or disk-backed external ordering, not sorting millions of dictionaries in RAM;
11. temporary shards and SQLite databases may exist only under clean temporary directories outside the repository and must be removed;
12. record peak RSS with `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`; each run must remain below `4,194,304 KiB`;
13. if the memory ceiling cannot be met, stop honestly with `TEMPORAL_VALIDATION_DATASET_FAILED` rather than consuming swap as working memory.

The auditor must reject any full-population `counters` or `counterexamples` list even if observed RSS is low.

## Required row invariants

- observations: `representative_episode_count * 2 roles * 2 scales * 5 representations * 13 fields`;
- volatility: `representative_episode_count * 2 roles * 2 scales * 5 representations`.

Unmatched controls remain present in both invariants as `UNKNOWN`.

## Compound-identity invariants

Validate generated rows independently from row counts.

Observation identity must contain every protocol identity column and at least:

`symbol, episode_view, episode_id, event_id, event_family, side, observation_role, observation_identity, observation_timestamp, scale, representation, field`.

Volatility identity must contain every protocol identity column and at least:

`symbol, episode_view, episode_id, event_id, event_family, side, observation_role, observation_identity, observation_timestamp, scale, representation`.

For each dataset:

1. insert identities into a temporary SQLite table with an explicit UNIQUE constraint;
2. record total rows, distinct identities, duplicate identities, and duplicate examples;
3. require `total_rows == distinct_identities`;
4. stream every duplicate into `counterexamples.csv` with its full identity and reason;
5. report separate checks named exactly `observation_compound_identity_unique` and `volatility_compound_identity_unique` in `validation_summary.csv`.

A matching aggregate row count does not satisfy the compound-identity invariant.

## Frozen overlap reconciliation

Use the half-open interval:

`2024-10-01T00:00:00Z <= observation_timestamp < 2024-11-01T00:00:00Z`

Empty timestamps have no interval coordinate and are excluded only from overlap selection.

### Observation reconciliation

For each symbol:

1. stream committed EXP-029R observation rows in the interval into a disk-backed SQLite expected table;
2. recompute rows through the same helper-backed state path used for 2025 and stream them into a reconstructed table;
3. key both tables by the full observation compound identity including `representation` and `field`;
4. diagnose missing and extra identities by SQL joins;
5. for matching identities, compare numeric `value` fields as numbers with `abs(expected - reconstructed) <= 1e-09`;
6. compare validity, reason, direction, origin, timestamps, and other nonnumeric fields exactly;
7. distinguish `MISSING_IDENTITY`, `EXTRA_IDENTITY`, `NUMERIC_VALUE_MISMATCH`, and `NONNUMERIC_VALUE_MISMATCH`;
8. stream every mismatch immediately to `counterexamples.csv`;
9. record expected count, reconstructed count, matched identity count, missing count, extra count, numeric mismatch count, nonnumeric mismatch count, maximum absolute numeric difference, tolerance, and canonical hashes.

Exact serialized-row equality is not a substitute for the tolerance comparison. Identity presence alone must never set `value_mismatches=0`.

### Volatility compatibility reconciliation

Committed EXP-029R `volatility_state.csv` is representation-blind because it emitted one row inside each five-representation loop but stored no `representation` column. Do not invent labels or modify EXP-029R.

For each symbol:

1. stream committed rows in the interval into a disk-backed multiset table preserving duplicate multiplicity;
2. recompute five representation-labelled rows per episode/role/scale through the helper-backed 2025 state path;
3. independently require the five reconstructed representation rows for each base identity to have identical `volatility_regime`, `regime_reason`, `atr_to_prior_96_median`, and `ohlc_closed_through`;
4. project reconstructed rows to the exact committed schema by dropping only `representation`;
5. compare committed and projected rows as multisets with duplicate multiplicity preserved;
6. compare `atr_to_prior_96_median` numerically at tolerance `1e-09` and nonnumeric fields exactly;
7. distinguish multiplicity, missing, extra, numeric, and nonnumeric mismatches and stream every mismatch immediately;
8. record all counts, maximum absolute difference, tolerance, and canonical hashes.

All four symbols must pass both reconciliation datasets for overall READY.

## Required outputs

Create exactly these twelve files:

- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/REPORT.md`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/data_provenance.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/episodes.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/matched_controls.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/validation_observations.csv.gz`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/validation_volatility_state.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/protocol_reconciliation.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/coverage_summary.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/validation_summary.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/counterexamples.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/run_hashes.csv`;
- `experiments/EXP-031R5_TEMPORAL_VALIDATION_2025/experiment_031r5.py`.

No other repository path may be created or changed.

## Validation contract

`validation_summary.csv` must independently report PASS/FAIL for:

- DATA-001 report and readiness manifest;
- all twelve canonical hashes before, between, and after runs;
- exact 2025 coverage;
- episode and representative identity uniqueness;
- event/control join completeness;
- observation row invariant;
- volatility row invariant;
- `observation_compound_identity_unique`;
- `volatility_compound_identity_unique`;
- closed-bar causality;
- UNKNOWN preservation;
- observation overlap reconciliation for every symbol;
- five-representation volatility invariance;
- volatility compatibility reconciliation for every symbol;
- actual production use of helpers from EXP-027, EXP-029R, and EXP-031;
- absence of EXP-030R cell access;
- deterministic two-run equality;
- peak RSS below 4 GiB for each run;
- output sizes and allowlist boundaries;
- absence of newly created cache, bytecode, temporary, partial, or SQLite files in the repository relative to baseline.

Pre-existing tracked cache/bytecode paths and all pre-existing untracked EXP-031R4 files are immutable baseline paths. Do not delete, modify, stage, rename, chmod, or count them as task-created violations.

`protocol_reconciliation.csv` must contain one row per symbol and dataset (`observations`, `volatility_compatibility`) with the required counts and mismatch diagnostics.

`counterexamples.csv` must include every unavailable control, UNKNOWN state, duplicate identity, reconciliation mismatch, failed invariant, helper-provenance failure, memory-budget failure, and out-of-boundary path with an explicit reason. It must be streamed and never reconstructed from an in-memory population.

`run_hashes.csv` must contain run-1 and run-2 SHA-256 values for the other eleven allowlisted outputs and exclude itself. Every pair must match. The script source may use the same immutable source SHA for both run labels.

## Status

`REPORT.md` must use exactly one status:

- `TEMPORAL_VALIDATION_DATASET_READY` when every required validation passes;
- `TEMPORAL_VALIDATION_DATASET_PARTIAL` when honest 2025 rows exist but one or more integrity requirements fail;
- `TEMPORAL_VALIDATION_DATASET_FAILED` when the dataset cannot be constructed honestly within the bounded-memory contract.

This task does not produce scientific ACCEPT/REJECT and does not authorize EXP-032 unless both conditions hold:

1. `REPORT.md` states `TEMPORAL_VALIDATION_DATASET_READY`;
2. the terminal Markdown reporter states `ORCHESTRATOR ACCEPTANCE: ACCEPTED`.

## Final checks

Reopen every final CSV and gzip by streaming and independently recompute counts and identities. Confirm all outputs are below 95 MiB, `git diff --check` passes, exactly the twelve R5 allowlisted paths are task-created and unstaged, peak RSS evidence is present, no temporary database remains in the repository, the R4 baseline is unchanged, and the protected Pine remains unchanged.

Never modify, stage, delete, rename, chmod, or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `PROJECT_INSTRUCTIONS.md`, `docs/DEFINITIONS.md`, `start.sh`, automation files, `.git` internals, persistent market data, any existing experiment directory, any tracked cache/bytecode path, any EXP-031R4 file, or any EXP-009 file.

The protected dirty file:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

must remain byte-identical with SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

and must remain dirty and unstaged.
