# Current Codex Task

- task_id: `EXP-031R3-TEMPORAL-VALIDATION-2025`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`

## Objective

Build an honest calendar-2025 temporal-validation diagnostic dataset using the frozen EXP-027 and EXP-029R market-state protocol. Preserve all committed experiments and failed runtime attempts. Do not inspect, rank, filter, confirm, or reject EXP-030R cells and do not make a predictive claim.

EXP-031R and EXP-031R2 failed technically. Their uncommitted directories are not evidence and must not be read as protocol sources. This task corrects two contract defects discovered by those attempts:

1. committed EXP-029R `volatility_state.csv` has no `representation` column although EXP-029R emitted one volatility row inside each five-representation loop;
2. the repository already contains tracked cache/bytecode paths outside this task allowlist, so validation must detect newly created cache artifacts rather than demand their removal.

## Mandatory data gate

Before computation:

1. verify the DATA-001 report SHA-256 above and require `DATA_READY=YES`;
2. verify `data/readiness/DATA-001_BYBIT_2025/readiness_manifest.csv` SHA-256 is `14a43c01de55d3cb82349553ec3abf700a9e49137fba6eea9669d2c2cceba4b2`;
3. require exactly twelve manifest rows and `source_status=READY` for every row;
4. read the exact canonical paths from the manifest and independently verify every `canonical_sha256` before and after both runs;
5. independently verify complete 2025 grids for BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT;
6. treat canonical files as combined archives: manifest 2025 coverage fields describe the validated slice and do not imply earlier rows are absent.

The persistent market-data root is read-only. Do not download, rewrite, merge, repair, or replace canonical data.

## Frozen protocol

Use definitions and deterministic helpers committed in:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

Reproduce without tuning:

- symbols BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT;
- FUNDING, OI and JOINT event families, frozen sides and 8H/24H episode views;
- representative selection, episode identities and matched-control rules;
- calendar month and chronological third for the declared interval;
- scales `15m` and `1H`;
- all five frozen representations and thirteen scalar fields;
- explicit `UNKNOWN` values and reasons;
- volatility state from current ATR versus the preceding 96 fully closed bars.

Use only bars fully closed at or before each observation timestamp. No future information, synthetic substitution, interpolation, forward fill, gap fill, or cross-symbol replacement.

## Implementation

Create:

`experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/experiment_031r3.py`

The implementation must:

1. set `sys.dont_write_bytecode = True` before loading any source module;
2. never parse an empty timestamp; unmatched controls retain an empty timestamp and explicit `UNKNOWN` state;
3. include `representation` in both new observation and new volatility schemas, identities, and sort keys;
4. use indexed timestamps or bisect-based lookup instead of rescanning all bars for every observation;
5. accept an explicit output directory;
6. run twice in separate clean temporary directories;
7. write deterministic gzip with empty filename and `mtime=0`;
8. verify byte-identical substantive outputs between runs before copying one verified run into the repository directory;
9. emit the complete output package even when an integrity check fails. A failed reconciliation must yield `TEMPORAL_VALIDATION_DATASET_PARTIAL` with detailed counterexamples, not an absent package;
10. never call a source experiment `main()` if it can write into an existing experiment directory.

Required row invariants:

- observations: `representative_episode_count * 2 roles * 2 scales * 5 representations * 13 fields`;
- volatility: `representative_episode_count * 2 roles * 2 scales * 5 representations`.

Unmatched controls remain included in both invariants as `UNKNOWN`.

## Frozen overlap reconciliation

Use:

`2024-10-01T00:00:00Z <= observation_timestamp < 2024-11-01T00:00:00Z`

Empty timestamps have no interval coordinate and are excluded only from overlap selection.

### Observation reconciliation

For each symbol:

1. select committed EXP-029R observation rows in the interval;
2. recompute them through the same state code path used for 2025;
3. compare full compound identity including `representation` and `field`;
4. compare validity, reasons, string fields, and numeric values at tolerance `1e-09`;
5. record expected/reconstructed counts, missing identities, extra identities, mismatches, and canonical hashes.

### Volatility compatibility reconciliation

Committed EXP-029R volatility evidence is representation-blind by construction: `experiment_029r.py` appends volatility inside the representation loop but writes a schema without `representation`. Do not invent representation labels for committed rows and do not modify EXP-029R.

For each symbol:

1. select committed EXP-029R volatility rows in the interval using their committed schema;
2. recompute five representation-labelled rows per episode/role/scale through the same 2025 code path;
3. independently require all five reconstructed representation rows for each base identity to have identical volatility fields (`volatility_regime`, `regime_reason`, `atr_to_prior_96_median`, `ohlc_closed_through`); any disagreement is FAIL;
4. project reconstructed rows to the exact committed EXP-029R volatility schema by dropping only `representation`;
5. compare committed and projected rows as canonically sorted multisets, preserving duplicate multiplicity; do not deduplicate;
6. compare numeric values at tolerance `1e-09` and all nonnumeric fields exactly;
7. record expected/reconstructed row counts, multiplicity mismatches, missing rows, extra rows, value mismatches, and canonical hashes.

All four symbols must pass observation reconciliation and volatility compatibility reconciliation for overall READY.

## Required outputs

Create exactly these twelve files:

- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/REPORT.md`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/data_provenance.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/episodes.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/matched_controls.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/validation_observations.csv.gz`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/validation_volatility_state.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/protocol_reconciliation.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/coverage_summary.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/validation_summary.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/counterexamples.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/run_hashes.csv`
- `experiments/EXP-031R3_TEMPORAL_VALIDATION_2025/experiment_031r3.py`

No other repository path may be created or changed.

## Validation contract

`validation_summary.csv` must independently report PASS/FAIL for:

- DATA-001 report and readiness manifest;
- all twelve canonical source hashes before and after both runs;
- exact 2025 coverage;
- episode and representative identity uniqueness;
- event/control join completeness;
- both row invariants and both compound-identity invariants;
- closed-bar causality;
- UNKNOWN preservation;
- observation overlap reconciliation for all symbols;
- volatility five-representation invariance;
- volatility compatibility reconciliation for all symbols;
- absence of EXP-030R cell access;
- deterministic two-run equality;
- output sizes and allowlist boundaries;
- absence of newly created untracked cache, bytecode, temporary, or partial files relative to the task baseline.

Pre-existing tracked `__pycache__` or `.pyc` paths are immutable baseline paths: do not delete, modify, stage, or count them as task-created violations. Fail only if the task creates or changes a cache/bytecode path.

`protocol_reconciliation.csv` must contain one row per symbol and dataset (`observations`, `volatility_compatibility`) with counts and mismatch diagnostics.

`counterexamples.csv` must retain every unavailable control, UNKNOWN state, reconciliation mismatch, failed invariant, and newly created out-of-boundary path with an explicit reason.

`run_hashes.csv` must contain run-1 and run-2 SHA-256 values for the other eleven allowlisted outputs and must not hash itself. Every pair must match. Do not rewrite hashed files after final hash computation.

## Status

`REPORT.md` must use exactly one status:

- `TEMPORAL_VALIDATION_DATASET_READY` when every required validation passes;
- `TEMPORAL_VALIDATION_DATASET_PARTIAL` when honest 2025 rows exist but one or more integrity requirements fail;
- `TEMPORAL_VALIDATION_DATASET_FAILED` when the 2025 dataset itself cannot be constructed honestly.

This task does not produce ACCEPT/REJECT and does not authorize EXP-032 unless status is `TEMPORAL_VALIDATION_DATASET_READY`.

## Final checks

Reopen every final CSV and gzip and independently recompute counts and identities. Confirm all outputs are below 95 MiB, `git diff --check` passes, exactly the twelve allowlisted paths are task-created and unstaged, and no new cache or temporary path exists relative to baseline.

Never modify, stage, delete, rename, chmod, or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `PROJECT_INSTRUCTIONS.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, persistent market data, any existing experiment directory, any tracked cache/bytecode path, or any EXP-009 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical with SHA-256 `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`, dirty and unstaged.
