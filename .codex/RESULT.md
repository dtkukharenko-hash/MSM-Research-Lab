# Latest Codex Result

- task_id: `EXP-012-R4-CAUSAL-PARENT-STATE-MACHINE`
- task_status: `AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW`
- implementation_commit_sha: `9ee608ab39791d4694e75a6f7a6e9cd5eb018438`
- implementation_push_status: `PUSHED origin/main`
- result_commit_status: `PUSHED origin/main`

## Summary

Implemented EXP-012 R4 as a chronological raw-bar state machine. The primary detector now builds parents from OHLC-derived causal start/boundary logic, tracks active price regimes and active EMA regimes, creates joint candidates from active-regime overlap, continues after failed joints, and maps R1/R2/R3/R5 artifacts only after R4 outputs are frozen.

Primary R4 produced 3 parents, 5 active price regimes, 6 primary EMA events, 5 joint candidates, 2 failed joints, and 3 confirmed parent resolutions.

## Created files

- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r4.py`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_disputed_zones_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/internal_phases_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/local_price_candidates_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/active_price_regimes_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/ema_departure_events_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/active_ema_regimes_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/ema_rearm_events_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/joint_parent_candidates_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_boundary_events_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_accepted_extensions_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/state_machine_events_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_zone_bar_features_r4.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/r4_historical_mapping.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/r4_model_comparison.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/r4_acceptance_tests.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/manual_causal_parent_review.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/LONG_CONTEXT_CAUSAL_PARENT_STATE_MACHINE_R4.pine`

## Modified files

- `PROJECT_QUEUE.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/TASK.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REPORT.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REVIEW_INSTRUCTIONS.md`

## Tests run

- `git pull --ff-only origin main`
- Read `AGENTS.md`, `PROJECT_INSTRUCTIONS.md`, and `.codex/TASK.md`; `.codex/TASK_ADDENDUM.md` treated as historical R2 documentation only.
- `python3 experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r4.py`
- Repeated R4 generator run produced identical SHA-256 hashes for R4 docs and artifacts.
- `python3 -m py_compile experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r4.py`
- Detector-only run without post-run mapping: `DETECTOR_ONLY_PARENTS 3`, `DETECTOR_ONLY_JOINTS 5`.
- R4 CSV timestamp cutoff scan: no timestamp at or after `2024-01-09 00:00:00`.
- Pine R4 scan: no `strategy(`, `plot(`, `ta.ema`, or `request.security`.
- Manual review CSV user-field emptiness check: PASS.
- Forbidden-path diff checks for `docs/DEFINITIONS.md`, EXP-011, EXP-011A, EXP-011B, and EXP009A Pine: empty for staged changes.
- R1/R2/R3 artifact diff check: no existing non-R4 artifact changed.
- `git diff --cached --check`

## Acceptance results

All 30 R4 acceptance tests passed:

- `DETECTION_USES_RAW_OHLC_NOT_R2_R3_LABELS`
- `NO_SOURCE_R5_GROUPING_IN_DETECTOR`
- `EXPECTED_THREE_PRIMARY_PARENTS`
- `FIRST_PARENT_COMPACT`
- `NOVEMBER_SINGLE_PARENT`
- `NOVEMBER_MULTIPLE_INTERNAL_PHASES`
- `DECEMBER_JANUARY_SINGLE_PARENT`
- `DECEMBER_MULTIPLE_INTERNAL_PHASES`
- `MID_DECEMBER_UP_REMAINS_INTERNAL`
- `MID_DECEMBER_EARLY_DOWN_REMAINS_INTERNAL`
- `FAILED_JOINT_PARENT_REMAINS_ACTIVE`
- `FAILED_JOINT_CONTINUES_FROM_NEXT_BAR`
- `LATER_LOCAL_CANDIDATE_AFTER_FAILED_JOINT`
- `LATER_JOINT_CANDIDATE_ALLOWED_AFTER_FAILED_JOINT`
- `PRIMARY_FIRST_PARENT_UP_RESOLUTION`
- `PRIMARY_NOVEMBER_UP_RESOLUTION`
- `PRIMARY_DECEMBER_DOWN_RESOLUTION`
- `DOWNSIDE_COMPARISON_FILTERS_DOWN_DIRECTION`
- `OPEN_PARENT_COVERS_ACTUAL_TRAIN_END`
- `ACTIVE_REGIME_OVERLAP_NOT_ARBITRARY_EVENT_AGE`
- `NO_DUPLICATE_EMA_EVENT_BEFORE_REARM`
- `NEW_BAND_WINDOW_STRICTLY_AFTER_PREVIOUS_CONFIRMATION`
- `NO_POST_DECISION_DATA_USED`
- `NO_WICK_ONLY_PARENT_BOUNDARY_UPDATE`
- `PRICE_ONLY_BASELINE_EXECUTED_INDEPENDENTLY`
- `INTERNAL_EMA12_BASELINE_EXECUTED_WITH_EMA_AND_PROBATION`
- `NO_DATE_HARDCODING`
- `NO_PRICE_HARDCODING`
- `NO_PARENT_PHASE_OR_LEGACY_ID_HARDCODING`
- `NO_FUTURE_PERIOD_USED`

## Metrics

Primary parents:

- `P001`: start `2023-10-31 12:00:00`, bounds `0.2875`-`0.3031`, phases `2`, `CONFIRMED_PARENT_UP_RESOLUTION`, confirmation `2023-11-04 16:00:00`
- `P002`: start `2023-11-12 16:00:00`, bounds `0.3568`-`0.3976`, phases `6`, `CONFIRMED_PARENT_UP_RESOLUTION`, confirmation `2023-12-06 16:00:00`
- `P003`: start `2023-12-11 00:00:00`, bounds `0.5328`-`0.6675`, phases `2`, `CONFIRMED_PARENT_DOWN_RESOLUTION`, confirmation `2024-01-08 08:00:00`

Primary counts:

- parent count: `3`
- active price regimes: `5`
- primary EMA events: `6`
- EMA event classes: `BOOTSTRAP_EMA12 UP away=1`, `BOOTSTRAP_EMA12 DOWN toward=1`, `PARENT_EMA24 UP away=3`, `PARENT_EMA24 DOWN toward=1`
- EMA rearm: `RETURN_REARM=2`, `NEW_BAND_REARM=1`
- joint candidates: `5`
- failed joints: `2`
- confirmed joints: `3`
- accepted extensions: `UP=3`, `DOWN=1`
- acceptance: `30 PASS`, `0 FAIL`

Joint trace:

- `JC001` P001 UP confirmed at `2023-11-04 16:00:00`
- `JC002` P002 UP failed at `2023-11-26 12:00:00`, reason `JOINT_12_BAR_CRITERIA_NOT_MET`
- `JC003` P002 UP failed at `2023-11-27 00:00:00`, reason `PRICE_DEEP_RECLAIM`
- `JC004` P002 UP confirmed at `2023-12-06 16:00:00`
- `JC005` P003 DOWN confirmed at `2024-01-08 08:00:00`

January continuation trace:

- first failed joint exists before final resolution flow;
- state-machine event log contains `FAILED_JOINT_CONTINUE_PARENT`;
- later local candidate after failed joint: yes;
- later joint candidate after failed joint: yes;
- final P003 outcome: `CONFIRMED_PARENT_DOWN_RESOLUTION`.

Model comparison:

- `R4_PRICE_PLUS_ACTIVE_PARENT_EMA`: parents `3`, UP `2`, DOWN `1`, open `0`, joints `5`, failed `2`
- `PRICE_ONLY_IMMEDIATE_CLOSE_BASELINE_R4`: parents `7`, UP `4`, DOWN `3`, open `0`, joints `0`, failed `0`
- `PRICE_PLUS_ACTIVE_INTERNAL_EMA12_BASELINE_R4`: parents `3`, UP `2`, DOWN `1`, open `0`, joints `5`, failed `2`

## Warnings

- Automatic OHLC outputs use Binance spot; manual review remains Bybit ADAUSDT Perpetual Contract 4H, so candle and boundary differences may exist.
- Post-run historical mappings are diagnostics only and are not detector inputs.
- The known unrelated EXP009A Pine modification remains unstaged and uncommitted.

## Final git status

After implementation push and before this result commit:

```text
 M experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
```

## Unrelated changes preserved

The unrelated local file below was not changed by the task, was not staged, and was not committed:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
