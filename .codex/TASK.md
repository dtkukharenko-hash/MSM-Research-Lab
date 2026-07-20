# Current Codex Task

- task_id: `EXP-031-TEMPORAL-HOLDOUT-DIAGNOSTIC-DATASET`
- status: `READY`
- published_at: `2026-07-20`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-030R-TRANSFER-FAILURE-LOCALIZATION`
- commit_message: `EXP-031 temporal holdout diagnostic dataset`

## Objective

Create a genuinely untouched temporal holdout diagnostic dataset for calendar year 2025 using the exact frozen EXP-027/EXP-029R causal protocol. This experiment prepares data only. It must not test, rank, select, confirm or reject the 226 volatility-conditioned cells found in EXP-030R; that confirmation belongs to a later preregistered experiment.

## Frozen panel and period

Use exactly:

- symbols: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `XRPUSDT`;
- half-open UTC interval: `2025-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z`;
- official Bybit V5 linear-market data or byte-validated existing local archives derived from that source.

No synthetic substitution, interpolation, forward filling, gap filling, cross-symbol replacement or unofficial source is allowed. Missing or invalid required source data remains explicit and may force a partial or failed dataset status.

## Frozen protocol

Reproduce without modification the committed EXP-027 and EXP-029R definitions for:

1. funding-extreme, OI-shock and joint-event detection;
2. independent episode construction and representative timestamps;
3. matched-control selection and matching strata;
4. 8H and 24H episode views;
5. scales, representations, structural fields and validity/history rules;
6. closed-bar causal timing and explicit `UNKNOWN` reasons;
7. chronological thirds, recalculated only as equal chronological thirds of the new 2025 holdout interval;
8. causal volatility state and regime assignment exactly as persisted by EXP-029R, including diagnostic `UNKNOWN`.

Do not tune thresholds, alter event definitions, add fields, remove failed fields, redefine controls, use future bars, inspect EXP-030R qualifying signs while building the dataset, or introduce outcome labels.

## Mandatory protocol reconciliation

Before accepting 2025 output, prove that the implementation reproduces the committed protocol on a frozen overlap probe:

- probe interval: `2024-10-01T00:00:00Z <= timestamp < 2024-11-01T00:00:00Z`;
- symbols: all four frozen symbols;
- source reference: committed EXP-029R `observations.csv.gz` and `volatility_state.csv`;
- regenerate the probe with the same code path used for 2025;
- compare canonical sorted rows by full identity key, schema, validity, `UNKNOWN` reason and numeric value with tolerance `1e-09`;
- compare volatility-state identities and labels exactly;
- persist per-symbol expected/reconstructed counts, canonical SHA-256 values, missing counts, extra counts, numeric mismatches and status in `protocol_reconciliation.csv`.

`READY` is forbidden unless all four symbols have zero missing, zero extra and zero mismatched comparable rows in the overlap probe.

## Holdout dataset contract

`holdout_observations.csv.gz` must contain one scalar row per 2025 event representative and matched control with the same committed schema as EXP-029R observations, including:

- symbol, episode view and identities;
- event family and side;
- calendar month and chronological third;
- event/control role and timestamp;
- available-history status;
- scale, representation, field and value;
- validity and explicit `UNKNOWN` reason;
- causal bar-closure evidence.

The gzip file must be deterministic: no original filename, zero timestamp in the gzip header, stable row ordering, UTF-8, LF line endings and stable CSV formatting.

`holdout_volatility_state.csv` must preserve the same identity key, causal state fields, regime labels and explicit reasons as EXP-029R. `UNKNOWN` is never imputed.

## Validation gates

Require all of the following for `TEMPORAL_HOLDOUT_DATASET_READY`:

1. exact frozen schemas and unique identities;
2. all source hashes and provenance recorded;
3. no future leakage and every OHLC dependency closed by the observation timestamp;
4. every event/control join is internally consistent;
5. chronological thirds cover the declared 2025 interval without overlap;
6. all four volatility regimes, including `UNKNOWN`, are retained where present;
7. overlap-probe reconciliation passes for all four symbols;
8. coverage, exclusions, gaps and reason counts are derived from output files rather than hard-coded;
9. no 2025 cell is filtered using EXP-030R pass/fail status or sign;
10. every repository output is below 95 MiB.

## Decision

Select exactly one dataset status:

- `TEMPORAL_HOLDOUT_DATASET_READY` — complete 2025 dataset and all validation gates pass;
- `TEMPORAL_HOLDOUT_DATASET_PARTIAL` — usable data exist, but explicit source limitations remain and are fully retained;
- `TEMPORAL_HOLDOUT_DATASET_DATA_FAILED` — source integrity, reconciliation or causal construction is insufficient.

Do not force a positive status.

## Required outputs

Create exactly these ten files:

- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/REPORT.md`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/data_provenance.csv`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/holdout_observations.csv.gz`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/holdout_volatility_state.csv`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/protocol_reconciliation.csv`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/coverage_summary.csv`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/validation_summary.csv`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/counterexamples.csv`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/run_hashes.csv`
- `experiments/EXP-031_TEMPORAL_HOLDOUT_DIAGNOSTIC_DATASET/experiment_031.py`

Do not create result files for EXP-032 and do not create or retain failed EXP-031 retry directories.

## Deterministic validation without external manifest paths

1. Generate the nine substantive files other than `run_hashes.csv` from stable `experiment_031.py`.
2. Compute ordinary SHA-256 over the actual bytes of those nine files, including the unchanged script, after run 1.
3. Run the experiment a second time from identical inputs without redownloading or modifying source archives.
4. Compute the same nine actual-byte hashes after run 2 and require exact path-by-path equality.
5. Write both hash sets and an equality field to `run_hashes.csv`; this file must not contain its own hash.
6. Do not rewrite any of the nine compared files after the second hash capture.
7. The auditor independently hashes the current nine files and verifies them against both columns in `run_hashes.csv`.
8. Compile with `PYTHONDONTWRITEBYTECODE=1`, remove cache files, run `git diff --check`, verify every output is below 95 MiB, and perform baseline-relative allowlist validation.

Any nondeterminism, self-referential hashing, missing compared path or output larger than 95 MiB requires `TECHNICAL_CORRECTION_REQUIRED`.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 file, or any EXP-013 through EXP-030R file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Only the ten EXP-031 outputs may change inside the repository. Downloaded or validated market archives must remain outside the repository.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the ten allowlisted EXP-031 outputs unstaged. The orchestrator performs final baseline-relative validation, commits once with the declared commit message and pushes to `main`.