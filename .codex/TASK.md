# Current Codex Task

- task_id: `EXP-031R6A2-BOUNDED-WORKER-CORE-CORRECTION`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `DATA`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-031R6A2 bounded worker core correction`

## Objective

Build and independently validate a fresh bounded-memory one-symbol worker core for the frozen EXP-027/EXP-029R temporal-validation protocol.

This is a narrow technical correction after EXP-031R6A. It must not execute the full four-symbol calendar-2025 run and must not make a scientific claim.

EXP-031R6A failed for seven concrete reasons:

1. unmatched controls were skipped instead of being emitted as explicit empty-timestamp `UNKNOWN` rows;
2. observation reconciliation collapsed duplicate evidence and inferred differences from counts instead of full joins;
3. volatility compatibility was count-only rather than a duplicate-preserving SQLite multiset comparison;
4. the public fixture mode omitted the January 2025 construction interval;
5. exact source-grid checks were bypassed for the October 2024 fixture;
6. SQLite files were placed below output directories instead of an external temporary root;
7. the source exposed no working production worker path beyond the fixture/failure behavior.

Correct these defects without changing the frozen scientific protocol.

## Explicit workflow waiver

This task explicitly waives any generic requirement to create or modify `.codex/RESULT.md`, commit generated experiment outputs, or push a result commit.

Do not create or modify `.codex/RESULT.md`. Do not stage, commit, or push generated experiment outputs. The terminal orchestrator envelope and independent auditor verdict are the acceptance record for this task. This waiver resolves the RESULT.md/allowlist contradiction reported by the EXP-031R6A planner.

## Immutable failed baselines

All pre-existing EXP-031R4, EXP-031R5, and EXP-031R6A worktree paths are failed runtime evidence. They must remain byte-identical, untracked, and unstaged.

They may be inspected read-only as failure evidence, but must not be imported, executed, copied as a module, modified, deleted, renamed, chmodded, staged, or used as protocol evidence.

The protected Pine must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Pre-existing tracked cache and bytecode paths are immutable baselines. Do not remove or rewrite them.

## Frozen committed sources

Use protocol definitions only from committed files:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

Set `sys.dont_write_bytecode = True` before imports. Import all three under distinct aliases. Never call a source experiment `main()`.

Actual worker and reconciliation execution must use deterministic helpers or constants from all three sources. Record source path, source SHA-256, helper/constant, use site, and positive production call count in `helper_provenance.csv`.

Minimum production use:

- EXP-027: ATR, hourly aggregation, five representations, causal state generation;
- EXP-029R: timestamp formatting, scalar field set, numeric formatting/tolerance, volatility compatibility conventions;
- EXP-031: overlap bounds, schemas, identities, interval and comparison conventions.

## Required implementation

Create a fresh implementation:

`experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/experiment_031r6a2.py`

It must be a real one-symbol production worker core, not a scaffold, report generator, or failure stub.

Required CLI modes:

1. `--self-test --temp-dir PATH` — execute the complete bounded suite and return nonzero on any failed check;
2. `--fixture-output-dir PATH --temp-dir PATH` — generate the complete October and January fixture evidence;
3. `--worker-output-dir PATH --temp-dir PATH --symbol SYMBOL --start TIMESTAMP --end TIMESTAMP` — execute the real one-symbol interval worker path.

A full-year or all-symbol orchestration mode is intentionally deferred. Do not add or execute it in this task.

The worker path must implement:

- DATA-001 manifest and canonical hash validation;
- exact interval grid validation for 15m OHLC, 15m OI, and 8H funding;
- one-symbol event and matched-control construction;
- explicit preservation of unmatched controls with empty timestamp and `UNKNOWN` values/reasons;
- 15m and 1H closed-bar observations;
- all five representations and thirteen scalar fields;
- volatility state from current ATR versus the preceding 96 fully closed bars;
- deterministic CSV and gzip writers;
- disk-backed compound-identity checks;
- observation reconciliation at numeric tolerance `1e-09`;
- representation-blind volatility compatibility reconciliation preserving multiplicity;
- immediate counterexample writing;
- streaming SHA-256 and row counts;
- peak RSS recording.

Never parse an empty timestamp. Empty control timestamps remain empty and have no interval coordinate.

## Fixture intervals

Use only BTCUSDT in this task.

### October reconciliation fixture

Half-open interval:

`2024-10-01T00:00:00Z <= observation_timestamp < 2024-11-01T00:00:00Z`

Build every representative episode selected by the frozen protocol for this interval. Emit both EVENT and CONTROL roles for every representative episode. When a control is unmatched, emit all required control observation and volatility rows as explicit `UNKNOWN` with an empty timestamp.

Empty-timestamp rows remain in the generated fixture datasets and identity checks, but are excluded from overlap reconciliation because they have no interval coordinate.

### January construction fixture

Half-open interval:

`2025-01-01T00:00:00Z <= timestamp < 2025-01-03T00:00:00Z`

Use the same production path, both roles, both scales, all five representations, all thirteen fields, and explicit UNKNOWN preservation.

### Exact source-grid checks

Run exact interval source-grid validation for both fixtures. Do not gate validation on `start.year == 2025` or any equivalent shortcut.

Validate the expected timestamp cadence and uniqueness for each required source, while allowing the canonical files to contain rows outside the requested interval.

## Bounded-memory contract

1. Process one symbol per worker invocation.
2. Stream canonical and generated CSV/gzip row populations.
3. Stream observation, volatility, and counterexample outputs through open writers.
4. Write every counterexample immediately when discovered.
5. Use disk-backed SQLite for identities, joins, and multiset comparison.
6. SQLite, shards, journals, and temporary files may exist only below the caller-supplied `--temp-dir`, which must be outside the repository and outside every output directory.
7. Reject a `--temp-dir` located inside the repository or output path.
8. Never use `INSERT OR REPLACE` for expected or actual reconciliation rows.
9. Preserve duplicate multiplicity explicitly.
10. Close files/connections deterministically and remove temporary databases before success.
11. Use indexed/bisect closed-bar lookup.
12. Use fixed iteration or SQL `ORDER BY`, not whole-population Python sorting.
13. Deterministic gzip must use empty filename and `mtime=0`.
14. Record `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`.

Forbidden production patterns:

- `list(csv.DictReader(...))` or gzip equivalent;
- `readlines()` or whole-file `read_text()` for row populations;
- pandas/polars/dataframes;
- full observation, volatility, reconciliation, identity, or counterexample populations in Python containers;
- imports from EXP-031R4, EXP-031R5, or EXP-031R6A;
- SQLite under the repository or output directory;
- intentional swap use as working memory.

A bounded one-symbol OHLC/ATR array and small fixed configuration collections are allowed.

## Compound identities

Observation identity must include all protocol identity fields and at least:

`symbol, episode_view, episode_id, event_id, event_family, side, observation_role, observation_identity, observation_timestamp, scale, representation, field`.

Volatility identity must include all protocol identity fields and at least:

`symbol, episode_view, episode_id, event_id, event_family, side, observation_role, observation_identity, observation_timestamp, scale, representation`.

Use SQLite tables with explicit UNIQUE constraints for generated identity validation. Report total rows, distinct identities, duplicate count, and duplicate examples. Stream duplicate examples to `fixture_counterexamples.csv`.

## Observation reconciliation

For each October expected/reconstructed observation population:

1. stream committed EXP-029R overlap rows into a disk-backed expected table;
2. insert without replacement semantics and detect any expected duplicate identity explicitly;
3. reconstruct through the same worker state path;
4. join by full observation compound identity including representation and field;
5. diagnose missing and extra identities by full SQL joins, not aggregate subtraction;
6. compare numeric value fields as numbers with `abs(expected - actual) <= 1e-09`;
7. compare validity, reasons, direction, origin, timestamps, and other nonnumeric fields exactly;
8. classify `MISSING_IDENTITY`, `EXTRA_IDENTITY`, `NUMERIC_VALUE_MISMATCH`, `NONNUMERIC_VALUE_MISMATCH`, and duplicate-identity failures separately;
9. stream every mismatch immediately to `fixture_counterexamples.csv`;
10. report counts, maximum absolute numeric difference, tolerance, canonical hashes, and status.

## Volatility compatibility reconciliation

Committed EXP-029R volatility rows do not contain `representation` and preserve duplicate multiplicity.

For October:

1. stream committed rows into a disk-backed duplicate-preserving expected multiset;
2. reconstruct five representation-labelled rows per base identity;
3. independently require identical volatility regime, reason, ATR ratio, and closed-through value across the five representations;
4. stream any representation-invariance failure immediately;
5. project reconstructed rows by dropping only `representation`;
6. compare expected/projected rows as SQLite multisets with exact multiplicity;
7. compare ATR ratios numerically at `1e-09` and all nonnumeric fields exactly;
8. classify missing multiplicity, extra multiplicity, numeric mismatch, nonnumeric mismatch, and representation-invariance failure separately;
9. report counts, maximum difference, tolerance, canonical hashes, and status.

A count-only comparison is an automatic FAIL.

## Required deterministic runs

Execute the complete fixture twice, sequentially, in separate clean temporary roots outside the repository.

Each run must execute both October and January construction through the public `--fixture-output-dir` path. Do not hide January execution only inside `self_test()`.

Compare actual substantive fixture files by streaming SHA-256 and row counts. Never retain both runs' row populations in memory.

Fixture peak RSS for each run must remain below `1,048,576 KiB`.

## Required outputs

Create exactly these fifteen files:

- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/REPORT.md`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/experiment_031r6a2.py`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_oct_observations.csv.gz`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_oct_volatility_state.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_jan_observations.csv.gz`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_jan_volatility_state.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_episode_control_summary.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_counterexamples.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_reconciliation.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_identity_checks.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/fixture_run_hashes.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/helper_provenance.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/memory_summary.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/implementation_audit.csv`;
- `experiments/EXP-031R6A2_BOUNDED_WORKER_CORE/test_results.csv`.

No other repository path may be created or changed.

## Evidence contracts

`fixture_episode_control_summary.csv` must separately report October and January representative counts, EVENT counts, matched controls, unmatched controls, expected UNKNOWN observation rows, generated UNKNOWN observation rows, expected UNKNOWN volatility rows, generated UNKNOWN volatility rows, and PASS/FAIL.

`fixture_reconciliation.csv` must contain separate observation and volatility compatibility rows with expected count, reconstructed count, matched count, missing count, extra count, numeric mismatch count, nonnumeric mismatch count, duplicate/multiplicity mismatch count, representation-invariance failures, maximum absolute numeric difference, tolerance, expected/reconstructed canonical hashes, status, and detail.

`fixture_identity_checks.csv` must report dataset/interval, total rows, distinct identities, duplicate identities, and status.

`fixture_counterexamples.csv` must be created before processing and streamed. It must contain every unmatched control, UNKNOWN state, duplicate identity, reconciliation mismatch, representation-invariance failure, grid failure, helper-use failure, memory failure, and boundary failure with explicit reason and available identity fields.

`fixture_run_hashes.csv` must contain both runs, every substantive fixture output, row counts, SHA-256, and equality status. Exclude itself and `REPORT.md`.

`implementation_audit.csv` must report PASS/FAIL for every structural requirement, including the absence of `INSERT OR REPLACE`, no failed-attempt import, external temp enforcement, public January fixture execution, real worker CLI execution, exact grid checks for both intervals, and cleanup of SQLite/temp artifacts.

`test_results.csv` must list every executed CLI command/test, exit code, and status.

## Status

`REPORT.md` must use exactly one status:

- `BOUNDED_WORKER_CORE_READY` when every fixture, identity, UNKNOWN-preservation, reconciliation, provenance, deterministic, memory, source-grid, and boundary check passes;
- `BOUNDED_WORKER_CORE_FAILED` otherwise.

The report must state that no full four-symbol calendar-2025 dataset was produced and no scientific confirmation, rejection, transfer, ranking, filtering, or predictive claim is made.

## Acceptance

The auditor must inspect source and generated fixture rows directly. Reject when any of these holds:

- unmatched controls are absent or do not generate explicit UNKNOWN rows;
- any fixture mode omits October or January;
- October exact-grid validation is bypassed;
- observation differences are inferred only from aggregate counts;
- expected rows use replacement semantics;
- volatility compatibility is count-only or multiplicity-blind;
- five-representation volatility invariance is not executed;
- mismatches are accumulated rather than streamed;
- SQLite/temp artifacts occur inside repository/output paths;
- the one-symbol worker CLI is absent, a stub, or unexercised;
- either deterministic fixture run is absent or hashes differ;
- RSS reaches or exceeds 1 GiB;
- a full-year or all-symbol run is attempted;
- `.codex/RESULT.md` is created or changed;
- any path outside the fifteen-file allowlist is created or changed.

Before PASS, run `git diff --check`, stream-reopen every generated CSV/gzip, verify every output is below 95 MiB, verify all immutable R4/R5/R6A baselines and the protected Pine, and confirm no new cache, bytecode, SQLite, journal, temporary, partial, or shard file exists anywhere in the repository.
