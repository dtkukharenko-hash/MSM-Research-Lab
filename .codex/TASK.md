# Current Codex Task

- task_id: `EXP-031R2-TEMPORAL-VALIDATION-2025`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`

## Objective

Build the calendar-2025 temporal validation diagnostic dataset with the frozen EXP-027 and EXP-029R protocol. Preserve all committed prior experiments. Do not inspect, rank, filter, confirm or reject EXP-030R cells and do not make a predictive claim.

## Mandatory data gate

Before computation:

1. verify the DATA-001 report hash above and require `DATA_READY=YES`;
2. verify `data/readiness/DATA-001_BYBIT_2025/readiness_manifest.csv` SHA-256 is `14a43c01de55d3cb82349553ec3abf700a9e49137fba6eea9669d2c2cceba4b2`;
3. require exactly twelve rows and `source_status=READY` for every row;
4. hash every canonical CSV and require equality with its manifest hash;
5. independently verify the complete 2025 grids for BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT;
6. treat the canonical files as combined archives: the manifest reports the validated 2025 slice but does not imply that earlier rows are absent.

The persistent market-data root is read-only for this task.

## Frozen protocol

Use the definitions and deterministic helpers committed in:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

Reproduce without tuning:

- symbols, FUNDING/OI/JOINT families, sides and 8H/24H episode views;
- representative selection, identities and matched-control rules;
- calendar month and chronological third;
- scales `15m` and `1H`;
- all five representations and thirteen scalar fields;
- explicit `UNKNOWN` values and reasons;
- volatility state from current ATR versus the preceding 96 closed bars.

Use only fully closed bars. No future information, synthetic substitution, interpolation, forward fill, gap fill or cross-symbol replacement.

## Required implementation corrections

Create `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/experiment_031r2.py`.

The implementation must:

1. set `sys.dont_write_bytecode = True` before loading any source module and leave no `__pycache__` or `.pyc` anywhere in the repository;
2. read exact canonical paths from the readiness manifest;
3. verify all input hashes before and after both deterministic runs;
4. never parse an empty timestamp; unmatched controls must retain an empty timestamp and explicit `UNKNOWN` state;
5. include `representation` in both observation and volatility schemas, identities and sort keys;
6. use indexed timestamps or bisect-based lookup rather than rescanning all bars for every observation;
7. support an explicit output directory so the same computation can run twice in clean temporary directories;
8. produce deterministic gzip with empty filename and `mtime=0`;
9. copy only a byte-verified final run into the repository output directory.

Required row invariants:

- observations: `representative_episode_count * 2 roles * 2 scales * 5 representations * 13 fields`;
- volatility: `representative_episode_count * 2 roles * 2 scales * 5 representations`.

Unmatched controls remain included in both invariants as `UNKNOWN`.

## Required overlap reconciliation

Use the 2024 rows already present in the combined canonical 15-minute files. Do not infer absence from the 2025 bounds recorded in the readiness manifest.

For `2024-10-01T00:00:00Z <= timestamp < 2024-11-01T00:00:00Z`:

1. select the committed EXP-029R observation and volatility identities in that interval;
2. recompute their state through the same code path used for 2025 using only canonical bars closed by each observation timestamp;
3. compare canonical identities, validity fields, reasons, string fields and numeric values at tolerance `1e-09`;
4. record expected/reconstructed counts, missing identities, extra identities, numeric mismatches and canonical hashes for each symbol and both datasets;
5. require PASS for all four symbols and both datasets.

Empty committed control timestamps are excluded from timestamp interval selection only because they have no time coordinate; they remain represented and audited in their parent dataset.

## Required outputs

Create exactly these twelve files:

- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/REPORT.md`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/data_provenance.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/episodes.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/matched_controls.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/validation_observations.csv.gz`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/validation_volatility_state.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/protocol_reconciliation.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/coverage_summary.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/validation_summary.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/counterexamples.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/run_hashes.csv`
- `experiments/EXP-031R2_TEMPORAL_VALIDATION_2025/experiment_031r2.py`

No other repository path may be created or changed.

## Validation contract

`validation_summary.csv` must independently report PASS/FAIL for the data gate, source hashes, exact coverage, identity uniqueness, joins, both row invariants, both compound-identity invariants, closed-bar causality, UNKNOWN preservation, all-symbol overlap reconciliation, absence of EXP-030R access, deterministic two-run equality, output sizes and allowlist boundaries.

`run_hashes.csv` must contain run-1 and run-2 SHA-256 values for the other eleven outputs and exclude itself. Every pair must match. Hashed files must not be rewritten afterward.

`REPORT.md` must use exactly one status:

- `TEMPORAL_VALIDATION_DATASET_READY` when every required validation passes;
- `TEMPORAL_VALIDATION_DATASET_PARTIAL` when honest 2025 rows exist but an integrity requirement fails;
- `TEMPORAL_VALIDATION_DATASET_FAILED` when construction cannot complete honestly.

This task does not authorize EXP-032 unless the status is `TEMPORAL_VALIDATION_DATASET_READY`.

## Final checks

Run twice from clean temporary output directories. Reopen every final CSV and gzip and recompute counts and identities. Confirm all outputs are below 95 MiB, `git diff --check` passes, exactly the twelve allowlisted paths are task-created and unstaged, and no cache or temporary file exists in the repository.

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `PROJECT_INSTRUCTIONS.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, persistent market data, any existing experiment directory or any EXP-009 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical with SHA-256 `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`, dirty and unstaged.
