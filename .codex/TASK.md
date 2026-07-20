# Current Codex Task

- task_id: `EXP-028S-TRANSFER-FAILURE-LOCALIZATION`
- status: `READY`
- published_at: `2026-07-20`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-027-MULTI-MARKET-DERIVATIVES-TRANSFER`
- commit_message: `EXP-028S transfer failure localization`

## Objective

Complete the frozen transfer-failure localisation correctly. Treat the committed EXP-027 CSV outputs as authoritative for events, episodes, controls, representations, validity and structural state fields. Do not recompute EXP-027 structural states from OHLC and do not call EXP-027 state-building functions.

Only the causal volatility-regime label may be newly calculated. No threshold tuning, favourable-cell selection, event redefinition or outcome labels.

## Frozen inputs

Read and validate the committed outputs under `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/`, especially `events.csv`, `episodes.csv`, `event_state.csv`, `matched_controls.csv`, `transfer_summary.csv`, `counterexamples.csv` and `data_provenance.csv`.

Use exactly BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT over the frozen EXP-027 period. Do not modify EXP-027.

## Independent tests

### Test A — family

Evaluate `FUNDING_EXTREME`, `OI_SHOCK` and `JOINT_EVENT` independently, pooling only legitimate frozen sides. Do not condition on volatility.

### Test B — side

Evaluate each frozen side independently within its family: funding LOW/HIGH, OI EXPANSION/CONTRACTION, and every frozen joint side combination. Do not condition on volatility and do not copy family rows.

### Test C — causal volatility

For each frozen representative timestamp, use only complete closed 1H bars available no later than that timestamp. Calculate ATR14/close, then its empirical percentile from the preceding 90 calendar days excluding the current bar, requiring at least 1,000 prior observations. Classify LOW_VOL at percentile <=0.25, MID_VOL at >0.25 and <0.75, HIGH_VOL at >=0.75, otherwise UNKNOWN. Evaluate regimes while pooling families and sides with equal-family safeguards. Primary Test C keys must not contain family or side.

## Frozen criteria

For each partition, representation and state field require: support in at least three symbols; same sign in at least three symbols; no symbol above 50% concentration; every feasible leave-one-symbol-out sign survives; 8H and 24H signs agree; exclusions remove no more than 50% of episodes; sign persists in at least two chronological thirds in at least three symbols.

Each test must independently calculate support, contrast, LOSO, concentration, time-third stability, view agreement and verdict. No result row or identifier may be reused between tests. Report all cells and failures.

## Decision

Select exactly one: `TRANSFER_FAILURE_LOCALIZED_FAMILY`, `TRANSFER_FAILURE_LOCALIZED_SIDE`, `TRANSFER_FAILURE_LOCALIZED_VOLATILITY`, `TRANSFER_FAILURE_LOCALIZED_MULTIPLE`, `TRANSFER_FAILURE_NOT_LOCALIZED`, or `TRANSFER_FAILURE_LOCALIZATION_DATA_FAILED`.

## Required outputs

Create exactly:

- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/REPORT.md`
- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/data_provenance.csv`
- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/volatility_state.csv`
- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/family_localization.csv`
- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/side_localization.csv`
- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/volatility_localization.csv`
- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/localization_summary.csv`
- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/counterexamples.csv`
- `experiments/EXP-028S_TRANSFER_FAILURE_LOCALIZATION/experiment_028s.py`

Do not create or retain EXP-028 or EXP-028R directories.

## Deterministic validation

The previous retry is invalid because it used normalised hashes and rebuilt EXP-027 states.

1. Generate the eight report/data files from stable `experiment_028s.py`.
2. Compute ordinary SHA-256 over the actual bytes of all eight generated files and the unchanged script.
3. Save the first run manifest outside the repository.
4. Run the experiment again from identical inputs.
5. Compute actual SHA-256 again and require exact path-by-path equality for all nine files.
6. Never include a file's own hash inside that file and never rewrite an output after its final compared hash is captured.
7. Record only a non-self-referential machine-checkable assertion such as `two_run_actual_sha256_equal=1` and compared path count.
8. The auditor must independently verify the actual files and both manifests.

Also validate EXP-027 joins without rebuilding state, assert the three key spaces are independent, reproduce the report verdict from CSVs, compile the script without retaining cache files, run `git diff --check`, and perform baseline-relative allowlist validation.

A corrector or auditor must return `TECHNICAL_CORRECTION_REQUIRED` unless authoritative EXP-027 reuse and actual two-run SHA-256 equality are directly demonstrated.

## Hard protections

Never modify or stage protected project files or any EXP-009 and EXP-013 through EXP-027 file. The existing dirty `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Only the nine EXP-028S outputs may change inside the repository. External validated market archives may only be read. Temporary hash manifests must remain outside the repository and must not be committed.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted outputs unstaged. The orchestrator performs final validation, commits once with the declared message and pushes to `main`.
