# Current Codex Task

- task_id: `EXP-028R-TRANSFER-FAILURE-LOCALIZATION`
- status: `READY`
- published_at: `2026-07-20`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-027-MULTI-MARKET-DERIVATIVES-TRANSFER`
- commit_message: `EXP-028R transfer failure localization`

## Objective

Correctly localise why EXP-027 produced only partial multi-market transfer. Reuse the frozen EXP-027 panel, period, events, episodes, controls, state fields, representations and transfer criteria. Do not tune thresholds, select favourable cells, redefine events, or introduce outcome labels.

The previous EXP-028 attempt is invalid because it evaluated combined `family × side × volatility` cells and duplicated those results across factor labels. This retry must evaluate three independent predeclared partitions.

## Frozen inputs

Use exactly the committed EXP-027 outputs and validated external archives for `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, and `XRPUSDT`, over `2023-07-01T00:00:00Z` through `2024-12-31T23:00:00Z`.

Do not modify EXP-027. Recompute only when necessary to verify provenance or derive the causal volatility label.

## Three independent localisation tests

### Test A — event-family localisation

Evaluate event families independently while pooling across their legitimate frozen sides:

- `FUNDING_EXTREME`;
- `OI_SHOCK`;
- `JOINT_EVENT`.

Do not condition this test on volatility regime. Do not split or duplicate results by volatility. Preserve side composition and report side concentration as a diagnostic.

### Test B — side localisation

Evaluate frozen sides independently within their applicable event family:

- funding: `LOW`, `HIGH`;
- OI: `EXPANSION`, `CONTRACTION`;
- joint: every frozen funding-side × OI-side combination.

Do not condition this test on volatility regime. Do not collapse opposite sides. Do not copy family-level rows into side rows.

### Test C — causal volatility-regime localisation

Assign each representative timestamp exactly one causal regime using only complete closed 1H bars available at or before that timestamp:

1. compute `ATR14 / close` on closed 1H bars;
2. form the empirical percentile using only the preceding 90 calendar days, excluding the current bar;
3. require at least 1,000 prior valid 1H observations;
4. classify `LOW_VOL` at percentile `<= 0.25`, `MID_VOL` at `>0.25 and <0.75`, and `HIGH_VOL` at `>=0.75`;
5. unavailable history remains `UNKNOWN` and is never imputed.

Evaluate volatility regimes while pooling across event families and sides with equal-family safeguards. Do not condition this test on a specific family or side. Report family and side concentration separately.

## Independence requirement

Each localisation test must have its own grouping key, support table, contrast calculation, leave-one-symbol-out calculation, concentration test, time-third stability test, 8H/24H comparison and verdict field.

Rows from one test must not be duplicated or relabelled as results of another test. Add machine-checkable assertions proving that the three test result key spaces differ and that no result row is reused across tests.

## Frozen structural evaluation

For every applicable partition, representation and state field, retain the EXP-027 event-versus-control contrast definition and frozen transfer requirements:

1. sufficient matched support in at least three symbols;
2. same contrast sign in at least three symbols;
3. no symbol contributes more than 50% of equal-symbol pooled absolute contrast;
4. sign survives every feasible leave-one-symbol-out calculation;
5. sign agrees in both 8H and 24H views;
6. validity/history exclusions remove no more than 50% of independent episodes in supporting symbols.

A localisation factor is explanatory only if at least one predeclared cell passes all six requirements and also preserves the sign in at least two of three chronological thirds in at least three symbols.

Do not select the strongest cell after inspection. Report every frozen cell and all failures.

## Decision

Select exactly one verdict:

- `TRANSFER_FAILURE_LOCALIZED_FAMILY`;
- `TRANSFER_FAILURE_LOCALIZED_SIDE`;
- `TRANSFER_FAILURE_LOCALIZED_VOLATILITY`;
- `TRANSFER_FAILURE_LOCALIZED_MULTIPLE`;
- `TRANSFER_FAILURE_NOT_LOCALIZED`;
- `TRANSFER_FAILURE_LOCALIZATION_DATA_FAILED`.

Use `MULTIPLE` only when two or more independently evaluated tests each contain at least one fully qualifying predeclared cell. Do not force a positive verdict.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/REPORT.md`
- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/data_provenance.csv`
- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/volatility_state.csv`
- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/family_localization.csv`
- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/side_localization.csv`
- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/volatility_localization.csv`
- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/localization_summary.csv`
- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/counterexamples.csv`
- `experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/experiment_028r.py`

Do not create or retain the old `EXP-028_TRANSFER_FAILURE_LOCALIZATION` directory.

## Deterministic validation

Before PASS:

1. Parse and validate all EXP-027 source CSVs and provenance.
2. Verify volatility labels use only closed prior 1H bars and exclude the current bar.
3. Verify Test A has no volatility conditioning, Test B has no volatility conditioning, and Test C has no family/side conditioning in its primary result keys.
4. Verify all three tests calculate their own support, contrasts, LOSO, concentration, time-third and 8H/24H checks.
5. Verify no result row or result identifier is duplicated across factor outputs.
6. Reproduce all summary rows and the report verdict directly from CSV outputs.
7. Run the experiment once, record SHA-256 for all nine outputs, run it a second time without changing inputs or redownloading archives, and require all nine hashes to be identical. The script file itself may not rewrite itself; hash comparison must cover its stable content as well.
8. Save the two-run hash evidence in `localization_summary.csv` or REPORT.md in machine-readable form.
9. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-028R_TRANSFER_FAILURE_LOCALIZATION/experiment_028r.py`, remove cache files, run `git diff --check`, and perform baseline-relative allowlist validation.
10. Verify protected and pre-existing dirty files remain byte-identical and unstaged.

A corrector must return `TECHNICAL_CORRECTION_REQUIRED` unless the independent-partition assertions and two-run identical-hash validation both pass.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 file, or any EXP-013 through EXP-027 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Only the nine EXP-028R outputs may change inside the repository. External validated archives may only be read from `${HOME}/.local/share/msm-market-data/bybit/linear/`.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-028R outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.
