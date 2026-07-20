# Current Codex Task

- task_id: `EXP-031R-TEMPORAL-VALIDATION-2025`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/readiness_manifest.csv`
- data_manifest_sha256: `14a43c01de55d3cb82349553ec3abf700a9e49137fba6eea9669d2c2cceba4b2`

## Objective

Create an independent calendar-2025 temporal validation diagnostic dataset using the frozen EXP-027 and EXP-029R protocol. Preserve the committed failed EXP-031 package unchanged. This task prepares evidence only; it must not test, rank, filter, confirm, or reject any of the 226 EXP-030R volatility cells and must not make a predictive claim.

## Mandatory data gate

Before any computation:

1. verify the committed readiness-manifest SHA-256 against the metadata above;
2. verify that the associated DATA-001 report contains `DATA_READY=YES`;
3. require exactly twelve manifest rows and require every row to have `source_status=READY`;
4. independently hash each canonical CSV and require equality with `canonical_sha256` in the manifest;
5. require the frozen interval `2025-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z` for BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT;
6. stop with a failed dataset status before protocol work if any gate fails.

The research task is read-only with respect to the persistent market-data root. Do not download, rewrite, repair, merge, or update canonical archives or metadata.

## Frozen protocol

Use the exact definitions and deterministic rules committed in:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`;
- `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py`;
- `experiments/EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py`.

Reproduce without tuning:

- symbols, event families, sides and 8H/24H episode views;
- funding, OI and JOINT event construction;
- representative-event selection and episode identities;
- exact matched-control strata, candidate eligibility, tie-breaking and unavailable-control handling;
- calendar-month and chronological-third fields for the declared 2025 interval;
- scales `15m` and `1H`;
- the five frozen representations from EXP-027;
- the thirteen frozen scalar fields from EXP-029R;
- explicit `UNKNOWN` states and reasons;
- equal-symbol conventions where protocol-level summaries are needed only for integrity validation.

Do not invoke a source experiment main function if it can write into an existing experiment directory. Import read-only helpers or reproduce the frozen logic inside the new script. No existing experiment file may change.

## Causal rules

- Use only bars fully closed at or before each observation timestamp.
- Use no future pivots, future bars or later episode information in a past state.
- Use no synthetic substitution, interpolation, forward fill, gap fill or cross-symbol replacement.
- The volatility regime must compare current ATR only with the preceding 96 closed bars, exactly as in EXP-029R/EXP-031.
- Missing history, missing controls or unavailable state must remain `UNKNOWN` with an explicit reason.
- Do not read EXP-030R outcome tables, qualifying-cell lists or cell pass/fail fields.

## 2025 dataset construction

Create a new isolated implementation at:

`experiments/EXP-031R_TEMPORAL_VALIDATION_2025/experiment_031r.py`

It must:

1. read the exact canonical paths from the readiness manifest, not discover arbitrary substitutes;
2. verify the twelve source hashes before use;
3. construct the complete 2025 episode and matched-control populations with frozen identities;
4. retain representative and non-representative episode rows as required by the EXP-027 schema;
5. emit one event and one control observation identity per representative episode, including unavailable controls as explicit UNKNOWN rows;
6. compute both scales, all five representations and all thirteen scalar fields;
7. emit volatility-state rows for the same event/control identities and scales;
8. preserve deterministic ascending ordering and unique compound identities;
9. use deterministic gzip for `validation_observations.csv.gz` with an empty filename and `mtime=0`.

Required observation-row invariant:

`representative_episode_count * 2 roles * 2 scales * 5 representations * 13 fields`

Required volatility-row invariant:

`representative_episode_count * 2 roles * 2 scales * 5 representations`

Unmatched controls remain part of both invariants and carry UNKNOWN values.

## Frozen overlap reconciliation

Before accepting the 2025 dataset, rerun the identical state path on:

`2024-10-01T00:00:00Z <= timestamp < 2024-11-01T00:00:00Z`

For every symbol, compare reconstructed rows directly with the committed EXP-029R `observations.csv` and `volatility_state.csv` slices. Use canonical sorting and tolerance `1e-09` for numeric values. Record expected/reconstructed row counts, missing identities, extra identities, numeric mismatches and canonical hashes in `protocol_reconciliation.csv`.

Every symbol must pass both observation and volatility reconciliation. Do not weaken this requirement based on the 2025 result.

## Required outputs

Create exactly these twelve new repository files:

- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/REPORT.md`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/data_provenance.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/episodes.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/matched_controls.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/validation_observations.csv.gz`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/validation_volatility_state.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/protocol_reconciliation.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/coverage_summary.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/validation_summary.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/counterexamples.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/run_hashes.csv`
- `experiments/EXP-031R_TEMPORAL_VALIDATION_2025/experiment_031r.py`

No other repository path may be created or changed.

## Output contracts

`data_provenance.csv` must contain the manifest path/hash and all twelve canonical paths, hashes, schemas, row counts and 2025 coverage bounds.

`episodes.csv` and `matched_controls.csv` must preserve the frozen EXP-027 schemas and expose enough identity fields to audit every event/control observation join.

`coverage_summary.csv` must include at least symbol, source kind, event family, side, episode view, representative status, control status, observation role, scale, representation, validity and volatility regime counts.

`counterexamples.csv` must retain every unavailable control, UNKNOWN state, protocol mismatch and failed invariant with explicit reason. When none exist for a category, do not invent rows.

`validation_summary.csv` must independently record PASS/FAIL for:

- readiness manifest and report;
- twelve canonical source hashes;
- exact 2025 coverage;
- episode identity uniqueness;
- representative identity uniqueness;
- event/control join completeness;
- observation-row invariant;
- observation compound-identity uniqueness;
- volatility-row invariant;
- volatility compound-identity uniqueness;
- closed-bar causality;
- UNKNOWN preservation;
- all-symbol overlap reconciliation;
- absence of EXP-030R cell access;
- deterministic two-run equality;
- output-size and allowlist boundaries.

`run_hashes.csv` must contain run-1 and run-2 SHA-256 values for the other eleven outputs and must not hash itself. All eleven pairs must match. Compute hashes after final writes and do not rewrite hashed files afterward.

## Status

`REPORT.md` must use exactly one overall status:

- `TEMPORAL_VALIDATION_DATASET_READY` when every required validation passes;
- `TEMPORAL_VALIDATION_DATASET_PARTIAL` when valid 2025 rows exist but a required integrity condition fails;
- `TEMPORAL_VALIDATION_DATASET_FAILED` when the dataset cannot be constructed honestly.

This task does not produce ACCEPT/REJECT and does not authorize EXP-032 unless the status is `TEMPORAL_VALIDATION_DATASET_READY`.

## Validation before PASS

1. Run the script twice from clean temporary output locations with bytecode redirected outside the repository.
2. Confirm byte-identical hashes for all eleven substantive outputs.
3. Reopen the final gzip and CSV outputs and independently recompute row counts, unique identities and invariants.
4. Confirm every canonical input hash still matches DATA-001 after both runs.
5. Run `git diff --check` on task-created files.
6. Confirm exactly the twelve allowlisted paths are task-created and unstaged.
7. Confirm every output is below 95 MiB.
8. Confirm no `__pycache__`, `.pyc`, temporary or partial file exists in the repository.
9. Confirm the protected Pine remains byte-identical and unstaged.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `PROJECT_INSTRUCTIONS.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, persistent market-data files, any existing DATA package, any existing experiment directory, or any EXP-009 file.

The protected dirty file:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

must remain byte-identical with SHA-256 `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`, dirty and unstaged.

Planner must treat absent outputs as normal. Implementer creates the twelve outputs. Auditor verifies them independently. Corrector changes only the twelve allowlisted files and leaves them unstaged.