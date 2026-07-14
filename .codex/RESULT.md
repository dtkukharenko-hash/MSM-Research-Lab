# Latest Codex Result

- task_id: `EXP-012-R3-HIERARCHICAL-PARENT-ZONES`
- task_status: `AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW`
- implementation_commit_sha: `b06910c81e76c7c4c824caf7ce57c79304be6e99`
- implementation_push_status: `PUSHED origin/main`
- result_commit_status: `PUSHED origin/main`

## Summary

Implemented EXP-012 R3 as a hierarchical LONG-context model: broad parent disputed zones remain open through local accepted departures until a fresh same-direction parent EMA27 event and a joint 12-bar persistence probation both confirm. R3 preserves R1/R2 outputs, adds an exact R2 snapshot, and writes all R3 outputs separately.

Primary R3 produced 3 parent zones, 13 internal phases, 1 joint parent-resolution candidate, 0 confirmed parent resolutions, and 1 failed joint candidate. The model comparison baselines each produced 6 parent zones.

## Created files

- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r2_snapshot.py`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r3.py`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_disputed_zones_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/internal_phases_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_price_departures_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_joint_resolution_candidates_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_boundary_events_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_accepted_extensions_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/internal_ema27_departures_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_ema27_departures_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_ema27_rearm_events_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/price_parent_ema_alignment_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/r2_phase_parent_mapping_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/r3_model_comparison.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/r3_acceptance_tests.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/parent_zone_bar_features_r3.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/manual_hierarchical_parent_review.csv`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/LONG_CONTEXT_HIERARCHICAL_PARENT_ZONES_R3.pine`

## Modified files

- `PROJECT_QUEUE.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/TASK.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REPORT.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REVIEW_INSTRUCTIONS.md`

## Tests run

- `git pull --ff-only origin main`
- Read `AGENTS.md`, `PROJECT_INSTRUCTIONS.md`, and `.codex/TASK.md`; `.codex/TASK_ADDENDUM.md` was treated as historical R2 documentation only.
- `python3 experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r3.py`
- Repeated generator run produced identical SHA-256 hashes for R3 docs and artifacts.
- `python3 -m py_compile experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r3.py experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r2_snapshot.py`
- `cmp -s experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012.py experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r2_snapshot.py`
- R3 CSV timestamp cutoff scan: no timestamp at or after `2024-01-09 00:00:00`.
- Pine R3 scan: no `strategy(`, `plot(`, `ta.ema`, or `request.security`.
- Manual review CSV user-field emptiness check: PASS.
- Forbidden-path diff checks for `docs/DEFINITIONS.md`, EXP-011, EXP-011A, EXP-011B, and EXP009A Pine: empty for staged changes.
- `git diff --cached --check`

## Acceptance results

- `EXPECTED_THREE_PARENT_ZONES`: `PASS`
- `FIRST_PARENT_COMPACT`: `PASS`
- `NOVEMBER_SINGLE_PARENT`: `PASS`
- `NOVEMBER_HAS_MULTIPLE_INTERNAL_PHASES`: `PASS`
- `DECEMBER_JANUARY_SINGLE_PARENT`: `PASS`
- `DECEMBER_HAS_MULTIPLE_INTERNAL_PHASES`: `PASS`
- `NOVEMBER_PARENT_UP_WITH_FRESH_EMA_UP_AWAY`: `FAIL`
- `DECEMBER_PARENT_DOWN_WITH_FRESH_EMA_DOWN_TOWARD`: `FAIL`
- `MID_DECEMBER_UP_REMAINS_INTERNAL`: `PASS`
- `MID_DECEMBER_EARLY_DOWN_REMAINS_INTERNAL`: `PASS`
- `FINAL_DOWNSIDE_COMPARISON_FILTERS_DIRECTION`: `FAIL`
- `NO_PARENT_CLOSE_FROM_PRICE_ONLY`: `PASS`
- `NO_PARENT_CLOSE_FROM_EMA_ONLY`: `PASS`
- `NO_STALE_EMA_ASSOCIATION`: `PASS`
- `NO_DUPLICATE_PARENT_EMA_BEFORE_REARM`: `PASS`
- `NO_POST_DECISION_DATA_USED`: `PASS`
- `NO_WICK_ONLY_PARENT_BOUNDARY_UPDATE`: `PASS`
- `NO_DATE_HARDCODING`: `PASS`
- `NO_PRICE_HARDCODING`: `PASS`
- `NO_PARENT_OR_PHASE_ID_HARDCODING`: `PASS`
- `NO_FUTURE_PERIOD_USED`: `PASS`

## Metrics

- Primary parent zones: `3`
- Price-only immediate-close baseline parent zones: `6`
- Price plus internal EMA12 baseline parent zones: `6`
- Internal phases: `13`
- Local price departures: `13`
- Joint candidates: `1`; failed `1`; confirmed `0`
- Parent EMA events: `5`
- Parent EMA classifications: `PARENT_EMA_UP_AWAY_FROM_EMA200=3`, `PARENT_EMA_DOWN_TOWARD_EMA200=2`
- Suppressed parent EMA duplicates: `1`
- EMA rearm counts: `RETURN_REARM=2`, `NEW_BAND_REARM=3`
- Price/parent EMA association counts: `FRESH_SAME_DIRECTION=4`, `STALE=9`
- Parent accepted extensions: `UP=3`, `DOWN=1`
- Acceptance tests: `18 PASS`, `3 FAIL`

Primary parents:

- `P001`: start `2023-10-31 12:00:00`, final body bounds `0.2875`-`0.3031`, internal phases `2`, resolution `OPEN_AT_TRAIN_END`, R2 mapping `Z001`
- `P002`: start `2023-11-12 16:00:00`, final body bounds `0.3568`-`0.3976`, internal phases `6`, resolution `OPEN_AT_TRAIN_END`, R2 mapping `Z002;Z003`
- `P003`: start `2023-12-11 00:00:00`, final body bounds `0.5328`-`0.6615`, internal phases `5`, resolution `OPEN_AT_TRAIN_END`, R2 mapping `Z004;Z005;Z006`

Internal phase type counts:

- `INTERNAL_UP_DEPARTURE=4`
- `INTERNAL_DOWN_DEPARTURE=1`
- `INTERNAL_ACCEPTED_UP_EXTENSION=3`
- `INTERNAL_ACCEPTED_DOWN_EXTENSION=1`
- `INTERNAL_REJECTED_UP_EXCURSION=2`
- `INTERNAL_REJECTED_DOWN_EXCURSION=1`
- `INTERNAL_FAILED_JOINT_DOWN_RESOLUTION=1`

Local price departure counts:

- `UP / ACCEPTED_UPSIDE_EXIT_R2=4`
- `DOWN / ACCEPTED_DOWNSIDE_EXIT_R2=2`
- `UP / ACCEPTED_EXTENSION=3`
- `DOWN / ACCEPTED_EXTENSION=1`
- `UP / REJECTED_WICK_OR_SINGLE_EXCURSION=2`
- `DOWN / REJECTED_WICK_OR_SINGLE_EXCURSION=1`

Corrected DOWN-only comparison:

- Implemented explicit DOWN filter for downside comparisons.
- R3 has no confirmed DOWN parent resolution, so `FINAL_DOWNSIDE_COMPARISON_FILTERS_DIRECTION` is recorded as `FAIL` rather than using an UP or stale event.

## Warnings

- No parent resolution confirmed under the R3 joint probation rules; all three primary parent zones remain `OPEN_AT_TRAIN_END`.
- The manual expectations that November resolves upward with fresh parent EMA geometry and December-January resolves downward with fresh parent EMA geometry failed under the implemented causal freshness and probation rules.
- Binance spot OHLC was used for automatic outputs; manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so individual candle boundaries may differ.
- The known unrelated EXP009A Pine modification remains unstaged and uncommitted.

## Final git status

After implementation push and before this result commit:

```text
 M experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
```

## Unrelated changes preserved

The unrelated local file below was not changed by the task, was not staged, and was not committed:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
