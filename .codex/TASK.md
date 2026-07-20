# Current Codex Task

- task_id: `EXP-030-TRANSFER-FAILURE-LOCALIZATION`
- status: `READY`
- published_at: `2026-07-20`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-029R-DERIVATIVES-DIAGNOSTIC-DATASET`
- commit_message: `EXP-030 transfer failure localization`

## Objective

Localise why EXP-027 achieved only partial multi-market transfer, using committed EXP-029R as the authoritative observation-level source. Do not rebuild structural states, redefine events or controls, tune thresholds, select favourable cells, or introduce outcome labels.

Read `experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/observations.csv.gz` directly. Verify EXP-029R provenance, validation status, reconciliation totals and schemas before analysis.

## Frozen scope

Use exactly BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT over the frozen EXP-027 period, event representatives, matched controls, 8H/24H views, representations, state fields, validity rules and chronological thirds.

For each tested cell require all frozen gates:

1. matched support in at least three symbols;
2. same contrast sign in at least three symbols;
3. no symbol above 50% equal-symbol pooled absolute-contrast concentration;
4. sign survives every feasible leave-one-symbol-out calculation;
5. sign agrees in 8H and 24H views;
6. exclusions remove no more than 50% of independent episodes in supporting symbols;
7. sign persists in at least two chronological thirds in at least three symbols.

Preserve every predeclared cell and every failure.

## Test A — family

Evaluate `FUNDING_EXTREME`, `OI_SHOCK`, and `JOINT_EVENT` independently. Pool only legitimate frozen sides within each family. Do not condition on volatility.

## Test B — side

Evaluate each frozen side independently within its family: funding `LOW` and `HIGH`; OI `EXPANSION` and `CONTRACTION`; and every frozen joint side combination. Do not condition on volatility, collapse opposite sides, or copy family rows.

## Test C — volatility

Use the causal volatility regime already persisted by EXP-029R. Do not recalculate it and do not read market archives. Evaluate `LOW_VOL`, `MID_VOL`, and `HIGH_VOL`; retain `UNKNOWN` as excluded diagnostic support.

Pool families and sides with equal-family safeguards. Primary Test C keys must not contain family or side. Report family and side concentration separately.

## Independence

Each test must independently compute grouping keys, support, symbol contrasts, equal-symbol pooled contrast, concentration, LOSO, time-third stability, 8H/24H agreement, exclusion fraction and verdict.

Rows or identifiers from one factor output must not be duplicated or relabelled in another. Add machine-checkable key-space and identifier assertions. Preserve UNKNOWN and invalid reasons; never impute values.

## Decision

Select exactly one:

- `TRANSFER_FAILURE_LOCALIZED_FAMILY`;
- `TRANSFER_FAILURE_LOCALIZED_SIDE`;
- `TRANSFER_FAILURE_LOCALIZED_VOLATILITY`;
- `TRANSFER_FAILURE_LOCALIZED_MULTIPLE`;
- `TRANSFER_FAILURE_NOT_LOCALIZED`;
- `TRANSFER_FAILURE_LOCALIZATION_DATA_FAILED`.

A factor qualifies only when at least one predeclared cell passes all seven gates. Use `MULTIPLE` only when at least two independent tests qualify.

## Required outputs

Create exactly:

- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/REPORT.md`
- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/data_provenance.csv`
- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/family_localization.csv`
- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/side_localization.csv`
- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/volatility_localization.csv`
- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/localization_summary.csv`
- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/counterexamples.csv`
- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/validation_summary.csv`
- `experiments/EXP-030_TRANSFER_FAILURE_LOCALIZATION/experiment_030.py`

## Validation

1. Verify hashes, schemas and READY status of committed EXP-029R inputs.
2. Stream-decompress `observations.csv.gz`; do not create an uncompressed repository copy.
3. Reproduce the frozen unpartitioned aggregate comparator before localisation; zero unexplained mismatches are required.
4. Verify independent factor key spaces and unique result identifiers.
5. Derive summary counts and REPORT verdict directly from localisation CSVs.
6. Verify all predeclared cells and failures are retained.
7. Run twice from identical inputs. Save ordinary SHA-256 manifests for all nine outputs at `/tmp/EXP030_run1.sha256` and `/tmp/EXP030_run2.sha256`; retain them through audit and require exact equality.
8. Compile without retained cache files, run `git diff --check`, and perform baseline-relative allowlist validation.
9. No output may exceed 90 MB. Use deterministic gzip for a large tabular output only if necessary and keep the allowlist consistent.
10. Protected and pre-existing dirty files must remain byte-identical and unstaged.

Return `TECHNICAL_CORRECTION_REQUIRED` unless all validation gates pass.

## Hard protections

Never modify or stage `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 file, or any EXP-013 through EXP-029R file.

The protected dirty Pine file under EXP-009 must remain byte-identical and unstaged.

Only the nine EXP-030 outputs may change inside the repository.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-030 outputs unstaged. The orchestrator performs final validation, commits once with the declared commit message and pushes to `main`.