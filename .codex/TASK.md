# Current Codex Task

- task_id: `EXP-031R6A-BOUNDED-WORKER-IMPLEMENTATION`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `DATA`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-031R6A bounded worker implementation`

## Objective

Build and independently validate the reusable bounded-memory worker required for the calendar-2025 temporal-validation dataset. This task produces implementation evidence only. It must not claim that the full 2025 dataset is ready and must not execute the full four-symbol calendar-year production run.

EXP-031R5 failed technically for concrete implementation reasons:

1. the attempted worker was host-terminated before the third symbol;
2. the committed task output was replaced by a deliberate failure stub;
3. production code imported uncommitted EXP-031R4 code;
4. production code used full CSV materialization;
5. dataset outputs were header-only despite verified available data;
6. validation and reconciliation outputs contained placeholders instead of executed checks.

Correct the implementation architecture before another full production attempt. Do not change the frozen scientific protocol.

## Immutable failed baselines

All pre-existing EXP-031R4 and EXP-031R5 paths in the worktree are failed runtime evidence. They must remain byte-identical, untracked, and unstaged. Do not import, execute, copy, modify, delete, rename, chmod, or use their source code as an implementation dependency.

Do not inspect any earlier uncommitted EXP-031R, EXP-031R2, or EXP-031R3 directory.

The protected Pine file must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Pre-existing tracked cache and bytecode paths are immutable baseline paths. Do not remove or rewrite them.

## Frozen protocol sources

The implementation may use protocol definitions only from committed files:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

Set `sys.dont_write_bytecode = True` before importing them. Import all three under distinct aliases. Never call a source experiment `main()`.

Actual fixture execution must call deterministic helpers or use protocol constants from every source module. Import-only evidence is insufficient. Record source path, SHA-256, helper or constant name, use site, and positive call count in `helper_provenance.csv`.

Minimum production uses:

- EXP-027: ATR construction, hourly aggregation, five representations, causal state generation;
- EXP-029R: timestamp formatting, scalar field set, numeric formatting and tolerance, volatility compatibility conventions;
- EXP-031: overlap bounds, observation and volatility schemas, identity fields, temporal-validation comparison conventions.

Small adapters may normalize arguments and stream rows. They must not duplicate an available protocol definition with a conflicting implementation.

## Required implementation artifact

Create:

`experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/experiment_031r6a.py`

The file must be the real reusable production worker, not a scaffold or failure package generator.

Required CLI modes:

1. `--self-test` — execute the bounded fixture suite and exit nonzero on any failure;
2. `--fixture-output-dir PATH` — generate all fixture evidence in an explicit clean directory;
3. `--worker-output-dir PATH --symbol SYMBOL --start TIMESTAMP --end TIMESTAMP` — process one symbol and interval using the production path;
4. `--full-output-dir PATH` — expose the future full-run entry point, but do not invoke this mode in this task.

The production path must contain working functions for:

- DATA-001 manifest and canonical hash validation;
- exact source-grid validation;
- one-symbol event and matched-control construction;
- closed-bar observation generation for 15m and 1H;
- five representations and thirteen scalar fields;
- explicit UNKNOWN preservation for unmatched controls and unavailable state;
- volatility state using the current ATR versus the preceding 96 fully closed bars;
- deterministic CSV and gzip writers;
- disk-backed compound-identity validation;
- observation reconciliation at numeric tolerance `1e-09`;
- representation-blind volatility multiset compatibility reconciliation;
- immediate counterexample writing;
- streaming SHA-256 and row counting;
- peak RSS measurement.

A `main()` that unconditionally emits FAILED, writes header-only production files, delegates to a failed attempt, or returns before the requested mode executes is forbidden.

## Bounded-memory contract

The implementation must be structurally bounded, not merely observed below a limit in the small fixture.

1. Process exactly one symbol per worker invocation.
2. Stream canonical CSV and gzip inputs through iterators.
3. Stream observation, volatility, and counterexample outputs through open writers.
4. Write every counterexample when discovered.
5. Use temporary SQLite databases for identity uniqueness, keyed reconciliation, and duplicate-preserving multiset comparison.
6. Keep SQLite files and all shards under a caller-supplied temporary directory outside the repository.
7. Close writers, connections, and source files deterministically.
8. Release symbol data and invoke garbage collection before exit.
9. Use indexed timestamps or bisect-based closed-bar lookup.
10. Obtain deterministic order from fixed nested iteration or SQL `ORDER BY`, not from sorting complete row populations in RAM.
11. Deterministic gzip must use an empty filename and `mtime=0`.
12. Record `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`.

Forbidden production patterns include:

- `list(csv.DictReader(...))`;
- `list(gzip...DictReader(...))`;
- `readlines()` on canonical or generated row files;
- pandas, polars, or dataframe materialization;
- a full observation, volatility, reconciliation, or counterexample population stored in a Python list, tuple, deque, or dictionary;
- importing any EXP-031R4 or EXP-031R5 module;
- intentional swap use as working memory.

Small fixed configuration lists and bounded one-symbol bar arrays are allowed. The audit must distinguish these from full output populations.

## Compound identities

Observation compound identity must contain every protocol identity field and at least:

`symbol, episode_view, episode_id, event_id, event_family, side, observation_role, observation_identity, observation_timestamp, scale, representation, field`.

Volatility compound identity must contain every protocol identity field and at least:

`symbol, episode_view, episode_id, event_id, event_family, side, observation_role, observation_identity, observation_timestamp, scale, representation`.

Implement SQLite tables with explicit UNIQUE constraints. The worker must report total rows, distinct identities, duplicate identities, and duplicate examples without retaining all identities in memory.

## Reconciliation semantics

Use the half-open committed overlap interval:

`2024-10-01T00:00:00Z <= observation_timestamp < 2024-11-01T00:00:00Z`.

Observation reconciliation must:

- stream expected EXP-029R rows into SQLite;
- reconstruct rows through the same production state path;
- join by full compound identity including representation and field;
- compare numeric values as numbers using `abs(expected - actual) <= 1e-09`;
- compare nonnumeric state, validity, reason, origin, direction, and timestamp fields exactly;
- classify missing, extra, numeric mismatch, and nonnumeric mismatch separately;
- stream every mismatch immediately.

Volatility compatibility reconciliation must:

- preserve committed duplicate multiplicity;
- reconstruct five representation-labelled rows;
- verify that the five volatility values are identical for each base identity;
- drop only representation when projecting to the committed schema;
- compare projected and committed rows as disk-backed multisets;
- compare the ATR ratio numerically at `1e-09` and other fields exactly;
- stream every mismatch immediately.

Never parse an empty timestamp. Empty unmatched-control timestamps have no interval coordinate and remain explicit UNKNOWN rows.

## Fixture suite

Run only a bounded real-data fixture in this task:

- symbol: BTCUSDT;
- reconciliation interval: the required October 2024 overlap;
- 2025 construction interval: `2025-01-01T00:00:00Z` through `2025-01-03T00:00:00Z`;
- both scales;
- all five representations;
- all thirteen scalar fields;
- event and control roles, including unmatched controls when present.

The fixture is implementation evidence, not a scientific result.

Execute the complete fixture twice, sequentially, in separate clean temporary directories outside the repository. Never run the two workers concurrently. Compare substantive fixture outputs by streaming SHA-256 and row counts. All paired hashes must match.

Fixture worker peak RSS must remain below `1,048,576 KiB` (1 GiB). This stricter fixture threshold does not replace the future full-run ceiling of `4,194,304 KiB`.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/REPORT.md`;
- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/experiment_031r6a.py`;
- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/implementation_audit.csv`;
- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/helper_provenance.csv`;
- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/fixture_reconciliation.csv`;
- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/fixture_identity_checks.csv`;
- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/fixture_run_hashes.csv`;
- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/memory_summary.csv`;
- `experiments/EXP-031R6A_BOUNDED_WORKER_IMPLEMENTATION/test_results.csv`.

No other repository path may be created or changed.

## Output contracts

`implementation_audit.csv` must report PASS or FAIL for at least:

- source compiles without repository bytecode creation;
- no failed-attempt import or execution;
- no unconditional failure stub;
- no prohibited full-materialization pattern;
- explicit streaming counterexample writer exists and is exercised;
- SQLite uniqueness and reconciliation paths exist and are exercised;
- all three committed helper modules are used in production fixture execution;
- full-run CLI entry point exists but was not invoked;
- no repository temp, SQLite, cache, bytecode, or partial file was created;
- all baseline paths remain unchanged.

`fixture_reconciliation.csv` must contain separate observation and volatility compatibility rows with expected count, reconstructed count, matched count, missing count, extra count, numeric mismatch count, nonnumeric mismatch count, maximum absolute numeric difference, tolerance, status, and detail.

`fixture_identity_checks.csv` must report observation and volatility total rows, distinct identities, duplicate count, and status.

`fixture_run_hashes.csv` must contain both fixture runs, substantive output names, row counts, SHA-256 values, and equality status.

`memory_summary.csv` must contain per-run peak RSS, threshold, and PASS or FAIL.

`test_results.csv` must contain every executed command or test name, exit code, and status.

## Status

`REPORT.md` must use exactly one implementation status:

- `BOUNDED_WORKER_IMPLEMENTATION_READY` when every required fixture, audit, determinism, identity, reconciliation, provenance, memory, and boundary check passes;
- `BOUNDED_WORKER_IMPLEMENTATION_FAILED` otherwise.

The report must clearly state that no full four-symbol calendar-2025 dataset was produced and that this task makes no scientific confirmation, rejection, transfer, ranking, filtering, or predictive claim.

## Acceptance

The auditor must inspect the source directly and reject the package when any of the following is true:

- the script is a stub or header-only generator;
- any failed attempt is imported or executed;
- any prohibited full-materialization pattern exists on a production path;
- counterexamples are accumulated rather than streamed;
- the numeric tolerance path is absent or unexercised;
- compound identities are checked only by aggregate row count;
- volatility duplicate multiplicity is not preserved;
- any helper module has zero production fixture calls;
- either fixture run is absent or hashes differ;
- fixture RSS is at or above 1 GiB;
- a full year or all-symbol production run was attempted;
- any repository path outside the nine-file allowlist changed.

Before PASS, run `git diff --check`, stream-reopen every generated CSV, confirm every output is below 95 MiB, verify the protected Pine hash and unstaged state, verify all pre-existing R4/R5 paths are unchanged and unstaged, and confirm there are no new repository cache, bytecode, temporary, partial, SQLite, or shard paths.
