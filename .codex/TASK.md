# Current Codex Task

- task_id: `EXP-031R6A3R-BOUNDED-WORKER-ACCEPTANCE-CORRECTION`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `DATA`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-031R6A3R bounded worker acceptance correction`

## Objective

Resolve the blocked EXP-031R6A3 contract and independently accept or reject the bounded BTCUSDT worker implementation. Correct only the two remaining implementation defects: representation-labelled volatility identities and independent committed-population reconciliation. Do not run the full four-symbol calendar-2025 dataset and make no scientific claim.

## Resolved decisions

These decisions are fixed and require no further user judgment:

1. The orchestrator is authorized to stage, commit, and push exactly the allowlisted task outputs after a final auditor PASS. This task does not prohibit the orchestrator `commit_once()` path.
2. EXP-031R6A2 may be inspected read-only and its source may be manually adapted as an implementation seed into the new R6A3R file. It must not be imported or executed, and its generated outputs must not be used as expected evidence or scientific protocol evidence.
3. Scientific definitions and expected populations remain frozen to committed EXP-027, EXP-029R, and EXP-031 sources only.
4. `.codex/RESULT.md` is not required and must not be created or modified.

A role must not return `USER_DECISION_REQUIRED` for either resolved item. Any remaining implementation defect is `TECHNICAL_CORRECTION_REQUIRED`.

## Immutable baselines

All pre-existing EXP-031R4, EXP-031R5, EXP-031R6A, EXP-031R6A2, and EXP-031R6A3 paths are preserved runtime evidence. Keep them byte-identical, unstaged, and unmodified. R6A2 source may only be read while preparing the new implementation.

Keep the protected Pine byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not remove or rewrite pre-existing tracked cache or bytecode paths.

## Frozen committed sources

Use protocol definitions and expected evidence only from committed files:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/observations.csv.gz`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/volatility_state.csv`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

Set `sys.dont_write_bytecode = True` before imports. Import the three Python modules under distinct aliases and never call their `main()` functions. Record positive helper/constant use in `helper_provenance.csv`.

## Implementation

Create:

`experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/experiment_031r6a3r.py`

It must expose working modes:

1. `--self-test --temp-dir PATH`;
2. `--fixture-output-dir PATH --temp-dir PATH`;
3. `--worker-output-dir PATH --temp-dir PATH --symbol SYMBOL --start TIMESTAMP --end TIMESTAMP`.

Use BTCUSDT only. Run:

- October overlap: `2024-10-01T00:00:00Z <= observation_timestamp < 2024-11-01T00:00:00Z`;
- January construction: `2025-01-01T00:00:00Z <= timestamp < 2025-01-03T00:00:00Z`.

Run exact 15m OHLC, 15m OI, and 8H funding grid validation for both intervals. Preserve unmatched controls as explicit empty-timestamp `UNKNOWN` rows. Use both scales, all five representations, and all thirteen scalar fields.

## Mandatory volatility correction

Every generated volatility row must contain `representation`. Emit exactly five representation-labelled rows per episode, role, and scale. Include representation in deterministic ordering and compound identity:

`symbol, episode_view, episode_id, event_id, event_family, side, observation_role, observation_identity, observation_timestamp, scale, representation`.

Validate October and January volatility identities independently in SQLite. For each base identity after dropping only representation, independently query and require:

- five distinct frozen representation labels;
- identical volatility regime and reason;
- ATR ratio equality within `1e-09`;
- identical closed-through value.

Stream every identity or invariance failure immediately to `fixture_counterexamples.csv`.

## Independent reconciliation

For October observations, stream expected rows only from committed `observations.csv.gz` into external temporary SQLite. Stream independently reconstructed rows into a separate table. Join by the complete identity including representation and field. Diagnose duplicate, missing, extra, numeric, and nonnumeric mismatches separately. Numeric tolerance is `1e-09`.

For October volatility, stream expected rows only from committed `volatility_state.csv` into a duplicate-preserving SQLite multiset. Project independently validated generated rows by dropping only representation. Compare expected and projected rows as multisets, preserving multiplicity. Compare ATR ratio numerically at `1e-09` and all other fields exactly.

Self-reconstructed expected populations, count-only comparison, identity-only comparison, and collapsed duplicate multiplicity are automatic FAIL.

## Bounded-memory contract

Process one symbol per invocation. Stream canonical and generated row populations and all output writers. Use external caller-supplied temporary SQLite only, outside the repository and output directory. Do not use `INSERT OR REPLACE`. Do not materialize full row populations in Python containers. No pandas, polars, `readlines()`, or `list(csv.DictReader(...))`. Deterministic gzip uses empty filename and `mtime=0`. Record `ru_maxrss`; each fixture run must remain below `1,048,576 KiB`.

Execute the complete public fixture twice sequentially in separate external temporary roots. Both runs must include October and January and produce identical substantive hashes and row counts. Execute the public one-symbol worker separately.

## Required outputs

Create exactly the fifteen paths listed in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/`

No other repository path may be created or changed.

`fixture_identity_checks.csv` must separately report October observations, October volatility, January observations, and January volatility with total, distinct, duplicate count, and status.

`fixture_reconciliation.csv` must separately report committed observation and volatility comparisons with expected, reconstructed, matched, missing, extra, numeric mismatch, nonnumeric mismatch, duplicate/multiplicity mismatch, representation-invariance failure, maximum numeric difference, tolerance, hashes, status, and detail.

`fixture_counterexamples.csv` must be opened before processing and stream every UNKNOWN, duplicate, missing, extra, mismatch, invariance, grid, helper, memory, or boundary failure.

`fixture_run_hashes.csv` must report both runs, substantive outputs, row counts, SHA-256, and equality. `implementation_audit.csv` and `test_results.csv` must record every structural requirement and executed command.

## Status and acceptance

`REPORT.md` must use exactly one status:

- `BOUNDED_WORKER_REPRESENTATION_READY` when every requirement passes;
- `BOUNDED_WORKER_REPRESENTATION_FAILED` otherwise.

The report must state that no full four-symbol 2025 dataset was produced and no scientific confirmation, rejection, transfer, ranking, filtering, or predictive claim is made.

The auditor must inspect source and actual outputs directly. Reject missing representation, duplicate generated identities, inferred rather than queried invariance, non-committed expected populations, self-comparison, collapsed multiplicity, nondeterminism, RSS at or above 1 GiB, failed-attempt imports/execution, full-year execution, or any path outside the allowlist.

Before PASS, run `git diff --check`, stream-reopen every CSV/gzip, confirm each output is below 95 MiB, verify protected Pine and all baseline paths, and confirm no new cache, bytecode, SQLite, journal, temporary, partial, or shard path exists in the repository.

EXP-031R6B remains blocked until this task is accepted with `BOUNDED_WORKER_REPRESENTATION_READY`.
