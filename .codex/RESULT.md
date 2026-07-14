# Latest Codex Result

- task_id: `EXP-011B-R5-STRUCTURAL-RESET`
- task_status: `AWAITING_TW_STRUCTURAL_RESET_REVIEW`
- implementation_commit_sha: `b495da12511b46261c58707ffb210b2430c9d1ea`
- implementation_push_status: `PUSHED origin/main`
- result_commit_status: `PUSHED origin/main`

## Summary

Implemented EXP-011B R5 structural-reset hierarchy for LONG dispute sections. R5 preserves R4 snapshots, rejects summed recovery-strength section closing, separates `STRUCTURAL_RESET_CANDIDATE` from `INTERNAL_RECOVERY`, uses 6-bar structural reset confirmation and 24-bar internal recovery persistence, and generates the R5 CSV/Pine/manual-review artifacts.

R5 produced 3 sections. It preserved the November chain and the late-December chain, but did not split early December under the general frozen structural-reset rule. This failure is recorded honestly in acceptance results.

## Created files

- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/LONG_DISPUTE_ADAPTIVE_RECOVERY_R4_SNAPSHOT.pine`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/LONG_DISPUTE_STRUCTURAL_RESET_R5.pine`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/conflict_bar_features_r5.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/dispute_episodes_r4_snapshot.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/dispute_episodes_r5.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/long_dispute_events_r5.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/long_dispute_sections_r4_snapshot.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/long_dispute_sections_r5.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/manual_structural_reset_review.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/new_configuration_attempts_r5.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/r4_r5_section_mapping.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/r5_acceptance_tests.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/recovery_attempts_r4_snapshot.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/recovery_attempts_r5.csv`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/structural_reset_attempts_r5.csv`

## Modified files

- `PROJECT_QUEUE.md`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/REPORT.md`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/REVIEW_INSTRUCTIONS.md`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/TASK.md`
- `experiments/EXP-011B_LONG_CONFLICT_WINDOWS/experiment_011b.py`

## Tests run

- `git pull --ff-only origin main`
- `python3 experiments/EXP-011B_LONG_CONFLICT_WINDOWS/experiment_011b.py`
- `python3 -m py_compile experiments/EXP-011B_LONG_CONFLICT_WINDOWS/experiment_011b.py`
- R5 artifact cutoff scan: no timestamp after `2024-01-09 00:00:00`
- Pine R5 scan: no `strategy(`, `plot(`, `ema27`, `ema200`, or `showEMA`
- Manual review CSV user-field emptiness check: PASS
- R4 snapshot existence check: PASS
- `git diff --cached --check`
- Cached forbidden-path diff check for `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP009A Pine: empty

## Acceptance results

- `NOVEMBER_CHAIN_PRESERVED`: `PASS` — `1 matching section(s): LC002`
- `DECEMBER_STRUCTURAL_RESET_SPLIT`: `FAIL` — `1 section(s): LC003`
- `LATE_DECEMBER_CHAIN_PRESERVED`: `PASS` — `1 matching section(s): LC003`
- `EXPECTED_FOUR_SECTIONS`: `FAIL` — `3 R5 sections`
- `NO_DATE_HARDCODING`: `PASS`
- `NO_SECTION_ID_HARDCODING`: `PASS`
- `NO_FUTURE_PERIOD_USED`: `PASS`

## Metrics

- R4 sections: `6`
- R5 sections: `3`
- Episodes: `10`
- Internal recoveries: `8`
- Failed internal recoveries: `7`
- Confirmed persistent internal recoveries: `1`
- Structural-reset candidates: `1`
- Failed structural resets: `0`
- Confirmed structural resets: `1`
- Confirmed new down configurations: `1`

R5 sections:

- `LC001`: R4 `LC001`, R3 `LC001`, R2 `LC001`, D `2023-10-31 12:00:00`, E `2023-11-02 00:00:00`, C `2023-11-03 00:00:00`, `CONFIRMED_STRUCTURAL_RESET`
- `LC002`: R4 `LC002;LC003`, R3 `LC002`, R2 `LC002;LC003;LC004`, D `2023-11-12 16:00:00`, E `2023-12-01 16:00:00`, C `2023-12-06 04:00:00`, `CONFIRMED_PERSISTENT_INTERNAL_RECOVERY`
- `LC003`: R4 `LC004;LC005;LC006`, R3 `LC003`, R2 `LC005;LC006;LC007`, D `2023-12-11 00:00:00`, E `2024-01-06 16:00:00`, C `2024-01-08 08:00:00`, `CONFIRMED_NEW_DOWN_CONFIGURATION`

## Warnings

- `DECEMBER_STRUCTURAL_RESET_SPLIT` failed under the general R5 frozen reset-level rule. The early December recovery did not clear the structural reset level because the pre-dispute reference high dominated the reset level.
- `EXPECTED_FOUR_SECTIONS` failed because R5 produced 3 sections, not 4.
- Binance spot OHLC was used for automatic outputs; manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so individual candle boundaries may differ.
- Existing unrelated EXP009A Pine modification remains unstaged and uncommitted.

## Final git status

After implementation push and before this result commit:

```text
 M experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
```

## Unrelated changes preserved

The unrelated local file below was not changed by the task, was not staged, and was not committed:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
