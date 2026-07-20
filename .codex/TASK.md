# Current Codex Task

- task_id: `EXP-029-DERIVATIVES-DIAGNOSTIC-DATASET`
- status: `READY`
- published_at: `2026-07-20`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-027-MULTI-MARKET-DERIVATIVES-TRANSFER`
- commit_message: `EXP-029 derivatives diagnostic dataset`

## Objective

Create the missing observation-level diagnostic dataset required to localise the partial transfer found in EXP-027. Keep the EXP-027 event definitions, panel, period, episodes, controls, representations, state fields and validity rules frozen. This experiment prepares auditable data; it does not search for a favourable factor and does not produce a trading rule.

## Frozen panel and period

Use exactly BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT over `2023-07-01T00:00:00Z` through `2024-12-31T23:00:00Z`.

Use committed EXP-027 outputs as authoritative for event identities, episode membership, matched-control identities and frozen parameters. Validated exact-symbol archives under `${HOME}/.local/share/msm-market-data/bybit/linear/` may be read only to calculate missing observation-level structural fields and the causal volatility label. Do not change event selection, controls, merge views, thresholds or source periods.

## Required observation-level dataset

Create one deterministic row for every valid or invalid observation in both roles:

- `EVENT`: every EXP-027 episode representative in both 8H and 24H views;
- `CONTROL`: every EXP-027 matched control attached to its event/episode stratum.

Each row must retain at minimum:

- stable `observation_id`, role, symbol, timestamp and source event/control identifiers;
- event family, funding side, OI side and joint-side combination;
- 8H/24H view, episode id and representative id;
- calendar month, UTC hour and frozen chronological third;
- representation and state-field name;
- structural value, validity flag, age, history status, origin disagreement and all invalid/cap/history reasons;
- control-match stratum and matched event identifier;
- causal volatility regime and percentile.

Do not aggregate away individual controls. Preserve missing and invalid values explicitly as `UNKNOWN` or reason-coded rows.

## Frozen structural reconstruction

Observation-level state values must reproduce the EXP-027 state definition exactly:

- complete closed native 15m bars and deterministic complete UTC 1H bars;
- frozen 4, 8 and 32 parent-bar windows;
- ATR-normalised displacement and range, efficiency, close location and direction-aware slopes;
- representations `FIXED_8`, `DIRECTION_RUN`, `ATR_ORIGIN`, `CONFIRMED_DIRECTION_CHANGE`, `HYBRID_ORIGIN`;
- only bars closed no later than the observation timestamp;
- no future pivots, returns, outcome labels, interpolation or forward filling.

Reconstruction is permitted only because EXP-027 did not persist observation-level control states. It must be verified against every comparable committed EXP-027 event-state and aggregate transfer row. Any mismatch must be recorded and must block `DATASET_READY`.

## Causal volatility label

At each observation timestamp:

1. use the latest complete closed 1H bar no later than the timestamp;
2. calculate `ATR14 / close`;
3. calculate its empirical percentile from only the preceding 90 calendar days, excluding the current bar;
4. require at least 1,000 prior valid 1H observations;
5. classify `LOW_VOL` at `<=0.25`, `MID_VOL` at `>0.25 and <0.75`, `HIGH_VOL` at `>=0.75`, otherwise `UNKNOWN`.

## Verification tables

Report:

- exact reconciliation of event, episode and control identifiers against EXP-027;
- row counts by symbol, role, family, side, view, representation, field, chronological third, volatility regime and validity;
- comparison of reconstructed event-state values with EXP-027 committed event_state.csv;
- reproduction of EXP-027 aggregate transfer contrasts wherever the committed outputs permit direct comparison;
- all mismatches, unavailable histories and invalid joins.

No localisation verdict is allowed in this experiment.

## Decision

Select exactly one:

- `DERIVATIVES_DIAGNOSTIC_DATASET_READY` — identifiers reconcile, reconstruction matches frozen EXP-027 values within declared exact/numeric tolerances, observation-level controls are retained, and deterministic validation passes;
- `DERIVATIVES_DIAGNOSTIC_DATASET_PARTIAL` — dataset is honest and useful but material unavailable history or non-critical reconciliation limitations remain;
- `DERIVATIVES_DIAGNOSTIC_DATASET_FAILED` — identifiers, frozen reconstruction or required coverage cannot be validated honestly.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/REPORT.md`
- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/data_provenance.csv`
- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/observations.csv`
- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/volatility_state.csv`
- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/reconciliation.csv`
- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/coverage_summary.csv`
- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/counterexamples.csv`
- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/validation_summary.csv`
- `experiments/EXP-029_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029.py`

Do not create or retain EXP-028, EXP-028R or EXP-028S directories.

## Deterministic validation

Before PASS:

1. Validate all EXP-027 source hashes and schemas.
2. Assert exact event, episode, control and view membership reconciliation.
3. Assert every observation uses only closed bars at or before its timestamp.
4. Compare reconstructed event states against committed EXP-027 event states and preserve every mismatch.
5. Reproduce directly comparable EXP-027 aggregate rows from observation-level data.
6. Parse every CSV and reproduce REPORT counts and verdict.
7. Run twice from identical inputs without redownloading archives.
8. Compute ordinary byte SHA-256 for all nine actual files after each run and require exact path-by-path equality.
9. Persist both manifests outside the repository under `${HOME}/.local/state/msm-orchestrator/evidence/EXP-029-DERIVATIVES-DIAGNOSTIC-DATASET/` as `run1.sha256` and `run2.sha256`; do not delete them before auditing.
10. The manifests must contain exactly the nine repository-relative output paths, sorted identically. They are external evidence and must not be committed.
11. Compile with `PYTHONDONTWRITEBYTECODE=1`, remove cache artifacts, run `git diff --check`, and perform baseline-relative allowlist validation.
12. Verify all protected and pre-existing dirty files remain byte-identical and unstaged.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 file, or any EXP-013 through EXP-028 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Only the nine EXP-029 outputs may change inside the repository. External validated archives may only be read. The only permitted external writes are temporary atomic files and the two persistent SHA-256 manifests under the stated evidence directory.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-029 outputs unstaged. The orchestrator performs final validation, commits once with the declared message and pushes to `main`.