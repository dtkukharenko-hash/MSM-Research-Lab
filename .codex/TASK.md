# Current Codex Task

- task_id: `EXP-011B-R5-STRUCTURAL-RESET`
- status: `READY`
- published_at: `2026-07-14`
- target_branch: `main`
- commit_message: `EXP-011B distinguish structural reset from internal recovery`

## Objective

Revise `experiments/EXP-011B_LONG_CONFLICT_WINDOWS` after R4 failed manual review.

R4 overclassified recoveries as strong because its components were highly correlated around EMA27. R5 must stop using a summed recovery-strength score to close sections.

Implement a causal hierarchy:

1. Detect recovery attempt using the existing R3/R4 rule.
2. Decide whether it creates a `STRUCTURAL_RESET` of the current disputed price area.
3. A structural reset uses short confirmation.
4. A recovery without structural reset remains internal and uses long persistence confirmation.
5. Failed confirmation keeps the current section open.
6. EMA27/EMA200 cross remains an internal event.

Final status: `AWAITING_TW_STRUCTURAL_RESET_REVIEW`.

## Scope

- ADAUSDT, 4H, LONG-context disputes only.
- Development period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`.
- Use the existing EXP-011 Binance spot 4H OHLC file.
- Do not use data after `2024-01-08`.
- Do not use Technical Ratings, ZigZag, clustering, BACKBONE_C, PnL, backtesting, Irobot, or trading logic.
- Preserve all V1/R2/R3/R4 artifacts and create R4 snapshots before writing R5 outputs.

## Keep unchanged

Keep the existing causal calculations for EMA27, EMA200, ATR14, DISPUTE_START, CORE_TRIGGER, episodes, base recovery-attempt detection, new-down-configuration confirmation, and open-time timestamps.

## Structural reference levels

For each open dispute section calculate only from already closed bars:

- `pre_dispute_reference_high`: maximum high from the last confirmed aligned run through the bar before DISPUTE_START; fallback to the prior 12 bars.
- `dispute_ceiling_before_bar`: maximum high from DISPUTE_START through bar `t-1`; do not include the current bar.
- `structural_reset_level`: maximum of those two values.

Store all values and the fallback/source used.

## Structural-reset candidate

At recovery-attempt detection create a candidate only if all hold:

- close is above the structural reset level;
- clearance is at least `0.15 ATR14`;
- at least 3 of the latest 4 closes are above EMA27;
- EMA27 is rising;
- EMA27 remains above EMA200.

Freeze the structural reset level at candidate detection. Later highs must not move it.

## Fast confirmation

Use `STRUCTURAL_RESET_PROBATION_BARS = 6`.

Confirm when, over the following six closed 4H bars:

- no new CORE_TRIGGER;
- no two consecutive bars have `discordance_score >= 2`;
- at least 5 of 6 closes stay above EMA27;
- at least 4 of 6 closes stay above the frozen reset level;
- EMA27 stays above EMA200;
- at least 4 of 6 bars have nonnegative EMA27 change.

On success:

- `resolution_kind = CONFIRMED_STRUCTURAL_RESET`;
- effective resolution time is the first close above the frozen reset level in the confirmed sequence;
- confirmation time is the sixth probation bar;
- close the section only after confirmation.

On failure:

- record `FAILED_STRUCTURAL_RESET` and the reason;
- keep the section open;
- continue or open the next episode inside the same section.

## Internal recovery

A recovery attempt that does not qualify as a structural-reset candidate is `INTERNAL_RECOVERY`.

It must not use the six-bar path. Use `INTERNAL_RECOVERY_PERSISTENCE_BARS = 24`.

It closes the section only if the full 24-bar persistence check passes:

- no new CORE_TRIGGER;
- no new dispute episode;
- EMA27 stays above EMA200;
- at least 18 of 24 closes above EMA27;
- at least 16 of 24 bars with nonnegative EMA27 change;
- at least 14 of 24 bars with nonnegative EMA-gap change;
- at least 3 of the final 4 bars fully aligned.

Otherwise record `FAILED_INTERNAL_RECOVERY` and keep the section open.

## New down configuration

Keep the existing R3/R4 causal logic:

- initial 3-of-4 pattern;
- 8-bar confirmation;
- EMA27 below EMA200 at least 7 of 8;
- close below EMA27 at least 6 of 8;
- nonpositive EMA27 change at least 6 of 8;
- no confirmed long recovery.

EMA200 need not slope downward.

## State machine

Build sections chronologically. Do not post-process by merging sections already causally confirmed closed.

A new dispute after confirmed structural reset, confirmed persistent recovery, or confirmed new-down configuration opens a new section. Unresolved state at the period end is `OPEN_AT_TRAIN_END`.

## Acceptance tests

Diagnostics only; never hardcode dates or section IDs.

- `NOVEMBER_CHAIN_PRESERVED`: the November chain remains one section.
- `DECEMBER_STRUCTURAL_RESET_SPLIT`: the early December dispute is separated from the later December dispute by a general structural-reset rule.
- `LATE_DECEMBER_CHAIN_PRESERVED`: the false R4 split around 21 December does not create a new section unless it genuinely passes the general rule.
- `EXPECTED_FOUR_SECTIONS`: manual review currently suggests four sections. Record PASS/FAIL honestly; do not force the count.
- `NO_DATE_HARDCODING`.
- `NO_SECTION_ID_HARDCODING`.
- `NO_FUTURE_PERIOD_USED`.

## Required artifacts

Create:

- `artifacts/long_dispute_sections_r5.csv`
- `artifacts/dispute_episodes_r5.csv`
- `artifacts/recovery_attempts_r5.csv`
- `artifacts/structural_reset_attempts_r5.csv`
- `artifacts/conflict_bar_features_r5.csv`
- `artifacts/r4_r5_section_mapping.csv`
- `artifacts/r5_acceptance_tests.csv`
- `artifacts/manual_structural_reset_review.csv`
- `artifacts/LONG_DISPUTE_STRUCTURAL_RESET_R5.pine`

Update `experiment_011b.py`, local `TASK.md`, `REPORT.md`, `REVIEW_INSTRUCTIONS.md`, and `PROJECT_QUEUE.md`.

The structural-reset attempts CSV must include the frozen level, its source, clearance ATR, candidate status, probation dates, counts above the reset level and EMA27, failure reason, effective resolution time, and confirmation time.

## Pine R5

Create Pine Script v6 indicator `EXP-011B Structural Reset Sections R5`.

- Use `indicator()`, never `strategy()`.
- Do not plot EMA27 or EMA200.
- Use Python timestamps and Python-computed price bounds.
- Yellow area: dispute start through effective resolution.
- Clearly different light cyan/gray area: effective resolution through confirmation.
- Distinct D, E, and C lines.
- First core trigger per episode shown by default; all core triggers only through an optional input defaulting false.
- Event marks: `I` internal recovery, `S?` structural-reset candidate, `SF` failed structural reset, `SR` confirmed structural reset, `N` new-down attempt.
- Add section selector ALL plus individual sections.

## Report and review

Explain why R4 scoring was rejected, how the frozen structural reset level is calculated causally, all R4-to-R5 mappings, event counts, section dates, acceptance results, and Binance spot versus Bybit perpetual warning.

Do not claim predictive or trading value.

## Safety and validation

- Never modify `docs/DEFINITIONS.md`, EXP-011, or EXP-011A.
- Preserve all prior outputs.
- Never stage or commit `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`.
- No date-specific or section-ID-specific exceptions.
- Verify the current bar is excluded from `dispute_ceiling_before_bar`.
- Verify the reset level is frozen at candidate detection.
- Verify no summed recovery-strength score closes sections.
- Verify structural reset uses 6 bars and internal recovery uses 24 bars.
- Verify failed attempts keep sections open.
- Verify effective resolution is not later than confirmation.
- Verify Pine/CSV timestamps match and Pine has no EMA plots or strategy declaration.

## Commit and result

Use implementation commit message:

`EXP-011B distinguish structural reset from internal recovery`

Follow `AGENTS.md`, including writing and separately committing `.codex/RESULT.md`.

The result must report implementation SHA, push status, R4/R5 counts and mappings, internal and failed internal recovery counts, structural-reset candidate/failed/confirmed counts, persistent-recovery count, new-down count, every acceptance result, artifact paths, final git status, and confirmation that the unrelated EXP009A Pine was not staged.

## Standard launch command

`Выполни текущую задачу из .codex/TASK.md согласно AGENTS.md`
