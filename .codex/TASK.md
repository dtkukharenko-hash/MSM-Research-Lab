# Current Codex Task

- task_id: `EXP-031R6A3-BOUNDED-WORKER-REPRESENTATION-CORRECTION`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `DATA`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-031R6A3 bounded worker representation correction`

## Objective

Repair the two remaining bounded-worker defects found by the final EXP-031R6A2 audit without changing the frozen scientific protocol and without running the full four-symbol calendar-2025 dataset.

EXP-031R6A2 established useful implementation evidence: the one-symbol worker path exists, October and January fixtures are nonempty and deterministic, unmatched controls are preserved as empty-timestamp `UNKNOWN` rows, outputs reopen successfully, memory remains bounded, and repository boundaries remain clean. The final package was nevertheless rejected for two decisive defects:

1. volatility rows and volatility compound identities omitted `representation`, causing repeated identities and preventing independent five-representation validation;
2. reconciliation still did not independently compare the reconstructed population against the committed EXP-029R observation and volatility populations.

Correct only these technical defects and rerun the bounded BTCUSDT fixtures. This task produces implementation evidence only and makes no scientific claim.

## Explicit workflow waiver

This task explicitly waives any generic requirement to create or modify `.codex/RESULT.md`, commit generated experiment outputs, or push a result commit.

Do not create or modify `.codex/RESULT.md`. Do not stage, commit, or push generated experiment outputs. The terminal orchestrator envelope and independent auditor verdict are the acceptance record.

## Immutable failed baselines

All pre-existing EXP-031R4, EXP-031R5, EXP-031R6A, and EXP-031R6A2 worktree paths are failed runtime evidence. They must remain byte-identical, untracked, and unstaged.

They may be inspected read-only as failure evidence, but must not be imported, executed, copied as a module, modified, deleted, renamed, chmodded, staged, or used as protocol evidence.

The protected Pine must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Pre-existing tracked cache and bytecode paths are immutable baselines. Do not remove or rewrite them.

## Frozen committed protocol sources

Use protocol definitions and deterministic helpers only from committed files:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

Set `sys.dont_write_bytecode = True` before importing them. Import all three under distinct aliases. Never call a source experiment `main()`.

The actual fixture and reconciliation paths must use deterministic helpers or constants from all three modules. Record source path, source SHA-256, helper or constant, use site, and positive production call count in `helper_provenance.csv`.

Minimum production use:

- EXP-027: ATR, hourly aggregation, five representations, and causal state generation;
- EXP-029R: timestamp formatting, scalar field set, numeric formatting/tolerance, and committed overlap population conventions;
- EXP-031: overlap bounds, schemas, identities, interval rules, and comparison conventions.

## Required implementation

Create a fresh implementation:

`experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/experiment_031r6a3.py`

Do not import or execute any failed R6 implementation. The file must implement a real bounded one-symbol worker path, not a scaffold, header-only generator, self-comparison, or failure stub.

Required CLI modes:

1. `--self-test --temp-dir PATH` — execute the complete bounded suite and exit nonzero on any failure;
2. `--fixture-output-dir PATH --temp-dir PATH` — generate both October and January fixture evidence;
3. `--worker-output-dir PATH --temp-dir PATH --symbol SYMBOL --start TIMESTAMP --end TIMESTAMP` — execute the real one-symbol interval worker.

A full-year or all-symbol orchestration mode is intentionally deferred and must not be executed or added in this task.

## Fixture intervals

Use only BTCUSDT.

### October reconciliation fixture

Half-open interval:

`2024-10-01T00:00:00Z <= observation_timestamp < 2024-11-01T00:00:00Z`

Generate every representative episode selected by the frozen protocol and both EVENT and CONTROL roles. Unmatched controls must remain explicit empty-timestamp `UNKNOWN` observation and volatility rows.

### January construction fixture

Half-open interval:

`2025-01-01T00:00:00Z <= timestamp < 2025-01-03T00:00:00Z`

Use the same production path, both roles, both scales, all five representations, all thirteen scalar fields, and explicit UNKNOWN preservation.

Run exact interval grid validation for 15m OHLC, 15m OI, and 8H funding for both fixtures. Canonical files may contain rows outside the requested interval.

## Mandatory volatility representation correction

Every generated volatility row must contain an explicit `representation` column with one of the five frozen representation labels.

The volatility compound identity must include every protocol identity field and at least:

`symbol, episode_view, episode_id, event_id, event_family, side, observation_role, observation_identity, observation_timestamp, scale, representation`.

Requirements:

1. emit exactly five representation-labelled volatility rows per episode, role, and scale;
2. retain unmatched-control rows for all five representations with empty timestamps and explicit UNKNOWN values/reasons;
3. include `representation` in deterministic ordering and in the generated CSV schema;
4. validate October and January volatility identities independently using SQLite tables with explicit UNIQUE constraints;
5. report total rows, distinct identities, duplicate identities, and status separately for observations and volatility in each interval;
6. stream every duplicate identity immediately to `fixture_counterexamples.csv`;
7. require `total_rows == distinct_identities` for every generated population.

A correct aggregate row count without unique representation-labelled identities is FAIL.

## Five-representation volatility invariance

For each base volatility identity obtained by dropping only `representation`, independently query the five generated rows and require:

- exactly five distinct representation labels;
- identical `volatility_regime`;
- identical `regime_reason`;
- numerically equal `atr_to_prior_96_median` within `1e-09`;
- identical `ohlc_closed_through`.

Use disk-backed SQL grouping and joins. Do not infer invariance from construction code or counts. Stream every missing representation, duplicate representation, numeric mismatch, or nonnumeric mismatch immediately.

## Independent committed observation reconciliation

The October expected observation population must come only from the committed file:

`experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/observations.csv.gz`

It must not be regenerated by the R6A3 worker and must not come from an R6 failed attempt.

For BTCUSDT rows in the frozen overlap interval:

1. stream committed expected rows into an external temporary SQLite table;
2. preserve and diagnose expected duplicate identities rather than replacing them;
3. stream independently reconstructed R6A3 rows into a separate actual table;
4. join by the full observation compound identity including `representation` and `field`;
5. diagnose missing and extra identities using full SQL joins;
6. compare numeric values using `abs(expected - actual) <= 1e-09`;
7. compare validity, UNKNOWN reasons, direction, origin, timestamps, and all other nonnumeric fields exactly;
8. classify duplicate identity, missing identity, extra identity, numeric mismatch, and nonnumeric mismatch separately;
9. stream every mismatch immediately;
10. record expected count, reconstructed count, matched count, all mismatch counts, maximum numeric difference, tolerance, and canonical hashes.

A self-reconstructed expected population or self-comparison is automatic FAIL.

## Independent committed volatility compatibility reconciliation

The October expected volatility population must come only from the committed file:

`experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/volatility_state.csv`

The committed schema is representation-blind and contains duplicate multiplicity. Do not add labels to or modify the committed rows.

For BTCUSDT rows in the overlap interval:

1. stream committed rows into an external temporary SQLite multiset preserving duplicate multiplicity;
2. use the independently validated five representation-labelled R6A3 rows;
3. project actual rows by dropping only `representation`;
4. compare expected and projected rows as duplicate-preserving multisets;
5. compare ATR ratio numerically at `1e-09` and all other fields exactly;
6. classify missing multiplicity, extra multiplicity, numeric mismatch, nonnumeric mismatch, and representation-invariance failure separately;
7. stream every mismatch immediately;
8. record counts, maximum difference, tolerance, and canonical hashes.

A count-only comparison, identity-only comparison, or generated-expected comparison is automatic FAIL.

## Bounded-memory contract

1. Process one symbol per worker invocation.
2. Stream canonical and generated CSV/gzip populations.
3. Stream observations, volatility, and counterexamples through open writers.
4. Write every counterexample when discovered; do not accumulate the population.
5. Use disk-backed SQLite for identities, joins, invariance queries, and multiset comparison.
6. SQLite databases, journals, and shards may exist only below caller-supplied `--temp-dir`, outside the repository and every output directory.
7. Never use `INSERT OR REPLACE` for expected or actual populations.
8. Preserve duplicate multiplicity explicitly.
9. Use indexed or bisect-based closed-bar lookup.
10. Obtain deterministic ordering from fixed iteration or SQL `ORDER BY`, not whole-population Python sorting.
11. Deterministic gzip must use an empty filename and `mtime=0`.
12. Record `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`.
13. Each fixture run must remain below `1,048,576 KiB`.

Forbidden production patterns include whole-file row materialization, pandas/polars/dataframes, full output populations in Python containers, imports from failed attempts, SQLite below the repository/output directory, and intentional swap use as working memory.

A bounded one-symbol OHLC/ATR array and small fixed configuration collections are allowed.

## Required deterministic runs

Execute the complete public fixture twice, sequentially, in separate clean temporary roots outside the repository.

Each run must execute both October and January through `--fixture-output-dir`. Compare substantive outputs by streaming SHA-256 and row counts. Do not retain both populations in memory.

Also execute the public one-symbol worker CLI separately and record the command and exit code.

## Required outputs

Create exactly these fifteen files:

- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/REPORT.md`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/experiment_031r6a3.py`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_oct_observations.csv.gz`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_oct_volatility_state.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_jan_observations.csv.gz`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_jan_volatility_state.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_episode_control_summary.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_counterexamples.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_reconciliation.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_identity_checks.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/fixture_run_hashes.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/helper_provenance.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/memory_summary.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/implementation_audit.csv`;
- `experiments/EXP-031R6A3_BOUNDED_WORKER_REPRESENTATION/test_results.csv`.

No other repository path may be created or changed.

## Evidence contracts

`fixture_identity_checks.csv` must contain four independent rows at minimum:

- October observations;
- October volatility;
- January observations;
- January volatility.

Each row must report total rows, distinct identities, duplicate identities, and PASS/FAIL.

`fixture_reconciliation.csv` must contain independent committed-population rows for October observations and October volatility compatibility, including expected and reconstructed counts, matched count, missing/extra counts, numeric and nonnumeric mismatches, duplicate/multiplicity mismatches, representation-invariance failures, maximum absolute numeric difference, tolerance, expected/reconstructed canonical hashes, status, and detail.

`fixture_counterexamples.csv` must be opened before processing and streamed. It must contain every unmatched control, UNKNOWN state, duplicate identity, missing/extra identity, numeric/nonnumeric mismatch, multiplicity mismatch, representation-invariance failure, grid failure, helper-use failure, memory failure, and boundary failure with available identity fields.

`fixture_run_hashes.csv` must contain both runs, every substantive fixture output, row counts, SHA-256, and equality status. Exclude itself and `REPORT.md`.

`implementation_audit.csv` must explicitly report PASS/FAIL for:

- volatility schema contains representation;
- volatility identity contains representation;
- October and January volatility identities independently validated;
- five-representation volatility invariance independently queried;
- expected observation population read from committed EXP-029R;
- expected volatility population read from committed EXP-029R;
- no self-reconstructed expected population;
- duplicate multiplicity preserved;
- external temporary SQLite enforced and cleaned;
- public October and January fixture execution;
- public one-symbol worker execution;
- exact grid checks for both intervals;
- no failed-attempt import or execution;
- no prohibited full materialization;
- protected and baseline paths unchanged;
- no repository path outside the allowlist created or changed.

`test_results.csv` must list every executed command or test, exit code, and status.

## Status

`REPORT.md` must use exactly one implementation status:

- `BOUNDED_WORKER_REPRESENTATION_READY` when every required identity, invariance, independent reconciliation, determinism, provenance, memory, grid, and boundary check passes;
- `BOUNDED_WORKER_REPRESENTATION_FAILED` otherwise.

The report must state that no full four-symbol calendar-2025 dataset was produced and that this task makes no scientific confirmation, rejection, transfer, ranking, filtering, or predictive claim.

## Acceptance

The auditor must inspect source and actual fixture files directly. Reject the package when any of the following is true:

- a generated volatility file lacks `representation`;
- volatility identity omits `representation`;
- any generated observation or volatility identity is duplicated;
- five-way volatility invariance is inferred rather than independently queried;
- committed EXP-029R expected populations are not independently loaded;
- expected and actual populations originate from the same R6A3 reconstruction;
- duplicate multiplicity is collapsed;
- reconciliation is count-only or identity-only;
- either deterministic fixture run is absent or substantive hashes differ;
- fixture RSS reaches 1 GiB;
- a full-year or all-symbol run is attempted;
- any failed implementation is imported or executed;
- any repository path outside the fifteen-file allowlist changes.

Before PASS, run `git diff --check`, stream-reopen every generated CSV/gzip file, confirm every output is below 95 MiB, verify protected Pine hash and unstaged state, verify every pre-existing R4/R5/R6A/R6A2 baseline path is unchanged and unstaged, and confirm no new repository cache, bytecode, SQLite, journal, temporary, partial, or shard path exists.

EXP-031R6B remains blocked until this task is independently accepted with `BOUNDED_WORKER_REPRESENTATION_READY`.
