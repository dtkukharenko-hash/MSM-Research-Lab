# Current Codex Task

- task_id: `EXP-012-LONG-CONTEXT-DISPUTED-PRICE-ZONES`
- status: `READY`
- published_at: `2026-07-14`
- target_branch: `main`
- commit_message: `EXP-012 detect causal disputed price zones`

## Objective

Create a new experiment:

`experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES`

The object of study is no longer an EMA conflict window. The new object is a causal horizontal disputed price zone inside a LONG context.

Working interpretation:

aligned long movement
→ loss of directional agreement
→ price begins accepting both directions inside a horizontal range
→ EMA27 may cross through the range repeatedly
→ temporary recoveries remain inside the same range
→ the zone ends only after price is accepted outside one of its horizontal boundaries.

EMA27 and EMA200 provide context and diagnostics. Price defines the disputed zone boundaries and the accepted exit.

Final status: `AWAITING_TW_PRICE_ZONE_REVIEW`.

## Scope

- Symbol: ADAUSDT.
- Timeframe: 4H only.
- LONG-context disputed zones only.
- Development period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`.
- Use the existing EXP-011 Binance spot 4H OHLC file.
- Do not use data after `2024-01-08`.
- Manual visual review is on Bybit ADAUSDT Perpetual 4H; report possible candle differences.
- Do not use Technical Ratings, ZigZag, clustering, BACKBONE_C, PnL, backtesting, Irobot, or trading logic.
- Do not modify EXP-011B R1–R5 outputs. EXP-012 is a new experiment.

## Required reading

Before implementation read:

- `PROJECT_INSTRUCTIONS.md`
- `AGENTS.md`
- `.codex/TASK.md`
- EXP-011B R5 report and artifacts
- EXP-011 source OHLC metadata

Use EXP-011B only as diagnostic history and for mapping. Do not copy its section-closing state machine as the new model.

## Data source

Use:

`experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv`

Calculate EMA27, EMA200, EMA slopes, and ATR14 from the complete available warm-up history before slicing the development period.

All event timestamps used by Pine must be 4H bar `open_time`.

## Core conceptual rules

1. The disputed zone is a price range, not an EMA state.
2. EMA27 may rise, fall, or be crossed repeatedly while the same price zone remains active.
3. A move above EMA27 does not end the zone.
4. EMA27/EMA200 cross does not end the zone.
5. A new local high inside the active range does not automatically end the zone.
6. A failed move outside a boundary may expand that boundary and remain part of the same zone.
7. A zone ends only after accepted price movement outside a frozen boundary.
8. All detection and boundary updates must be causal.

## LONG context and zone start

Reuse the causal LONG-context and early-dispute logic conceptually from EXP-011B, but implement it locally in EXP-012.

Base LONG context:

- `ema27 > ema200`
- `ema200_slope_6 > 0`

A zone candidate starts at the first causal loss of agreement after a confirmed aligned run.

Use the existing R2/R5 dispute-start approach:

- identify the last aligned run;
- detect the first persistent discordance after it;
- `ZONE_START` must be no later than the first strict core trigger;
- store `last_aligned_run_start`, `last_aligned_run_end`, `zone_start`, and `first_core_trigger`.

The strict core trigger remains a diagnostic event only.

## Initial zone construction

Build the initial range causally in two stages.

### Upper seed

At `ZONE_START`, define:

`upper_seed = max(high)` from the last confirmed aligned run through the bar before `ZONE_START`.

Fallback if no aligned run is available:

maximum high of the previous 12 closed 4H bars.

Freeze the source and value used.

### Lower seed

From `ZONE_START`, track the running adverse low.

Confirm the first lower reaction when all hold:

- price has moved at least `1.0 ATR14` below `upper_seed`;
- after the running low, price rebounds at least `0.75 ATR14` from that low;
- at least 2 of the latest 3 closes are higher than their previous close;
- at least one of the latest 3 closes is above EMA27 or the close-to-EMA27 distance improved on 2 consecutive bars.

At confirmation:

- `lower_seed = running minimum low since ZONE_START`;
- `initial_upper_bound = upper_seed`;
- `initial_lower_bound = lower_seed`;
- `BOUNDS_CONFIRMED` timestamp is the detection bar.

If no lower reaction is confirmed within 18 bars, use a fallback only when all hold:

- zone age at least 8 bars;
- width from upper seed to running low at least `1.25 ATR14`;
- price crossed EMA27 at least twice;
- at least 70% of closes lie between upper seed and running low.

Record whether fallback was used.

## Active evolving zone

After bounds confirmation, maintain:

- `active_upper_bound`
- `active_lower_bound`
- `boundary_version`

Boundaries do not move continuously with every new extreme.

They change only after a failed accepted-exit attempt.

At every bar save the active frozen bounds before evaluating the current close.

## Outside-close candidate

Use:

`OUTSIDE_CLEARANCE_ATR = 0.15`

An upward exit candidate begins when:

`close > active_upper_bound + 0.15 * ATR14`

A downward exit candidate begins when:

`close < active_lower_bound - 0.15 * ATR14`

Freeze at candidate start:

- direction;
- boundary value;
- ATR14;
- first outside-close time;
- excursion high/low.

Do not move the candidate boundary during probation.

Only one exit candidate may be active at a time.

## Accepted exit

Use:

`EXIT_ACCEPTANCE_BARS = 6`

### Accepted upward exit

Confirm after six closed bars when all hold:

- at least 4 of 6 closes are above the frozen upper boundary;
- final close is above the frozen upper boundary;
- no two consecutive closes are back inside the range;
- at least 4 of 6 closes are above EMA27;
- EMA27 remains above EMA200.

### Accepted downward exit

Confirm after six closed bars when all hold:

- at least 4 of 6 closes are below the frozen lower boundary;
- final close is below the frozen lower boundary;
- no two consecutive closes are back inside the range;
- at least 4 of 6 closes are below EMA27.

Do not require EMA200 to slope downward.

On success:

- `exit_direction = UP` or `DOWN`;
- `effective_exit_open_time = first outside close of the successful sequence`;
- `exit_confirmation_open_time = sixth probation bar`;
- `resolution_kind = ACCEPTED_UPSIDE_EXIT` or `ACCEPTED_DOWNSIDE_EXIT`;
- close the zone only at confirmation.

## Failed exit and boundary expansion

An exit candidate fails when either:

- two consecutive closes return inside the frozen range before confirmation;
- the six-bar acceptance criteria fail;
- an opposite-side candidate appears before confirmation.

On failed upward exit:

- record `FAILED_UPSIDE_EXIT`;
- update `active_upper_bound` to the maximum high reached during that failed attempt;
- increment `boundary_version`;
- keep the same zone open.

On failed downward exit:

- record `FAILED_DOWNSIDE_EXIT`;
- update `active_lower_bound` to the minimum low reached during that failed attempt;
- increment `boundary_version`;
- keep the same zone open.

This boundary expansion represents acceptance of the failed excursion as part of the existing disputed zone.

Do not change the opposite boundary.

## Open zone at development end

If no accepted exit is confirmed by the last bar of the development period:

- `resolution_kind = OPEN_AT_TRAIN_END`;
- do not read later data;
- use the last development bar as the visible endpoint.

## Zone diagnostics

For every zone calculate:

- duration to effective exit;
- duration to confirmation;
- initial and final bounds;
- final width and width in ATR;
- boundary update count;
- failed upside exits;
- failed downside exits;
- close-inside fraction;
- EMA27 crossing count;
- core-trigger count;
- high and low acceptance-probe counts;
- maximum distance outside each boundary before failure;
- exit direction;
- source EXP-011B R5 section mapping.

Do not interpret these as predictive features yet.

## Required acceptance tests

Acceptance tests are diagnostic only. Never hardcode dates, prices, section IDs, or manual bounds in the algorithm.

1. `EXPECTED_THREE_ZONES`
   - Current manual review suggests three zones in the development period.
   - Record PASS/FAIL honestly; do not force the count.

2. `FIRST_ZONE_PRESERVED`
   - The short late-October/early-November zone should remain a compact independent zone.

3. `NOVEMBER_SINGLE_ZONE`
   - The November disputed process corresponding broadly to EXP-011B R5 LC002 should remain one zone despite repeated EMA27 recoveries.

4. `DECEMBER_JANUARY_SINGLE_ZONE`
   - The process corresponding broadly to EXP-011B R5 LC003 should remain one evolving horizontal zone despite the mid-December rally and new local high, unless the general accepted-exit rule genuinely closes it.

5. `LC003_EARLIER_DOWNSIDE_EXIT_THAN_R5`
   - The accepted downside exit should occur earlier than the R5 EMA-based effective exit if price is accepted below the horizontal lower boundary.
   - This comparison is post-run only and must not be used inside the detector.

6. `NO_DATE_HARDCODING`
7. `NO_PRICE_BOUND_HARDCODING`
8. `NO_SECTION_ID_HARDCODING`
9. `NO_FUTURE_PERIOD_USED`

## Required experiment structure

Create:

`experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/`

with:

- `TASK.md`
- `experiment_012.py`
- `REPORT.md`
- `REVIEW_INSTRUCTIONS.md`
- `artifacts/long_context_disputed_zones.csv`
- `artifacts/zone_boundary_events.csv`
- `artifacts/zone_exit_attempts.csv`
- `artifacts/zone_bar_features.csv`
- `artifacts/r5_zone_mapping.csv`
- `artifacts/acceptance_tests.csv`
- `artifacts/manual_zone_review.csv`
- `artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES.pine`

## Zone CSV fields

At minimum include:

- `zone_id`
- `display_start_open_time`
- `last_aligned_run_start_open_time`
- `last_aligned_run_end_open_time`
- `zone_start_open_time`
- `first_core_trigger_open_time`
- `bounds_confirmation_open_time`
- `initial_upper_bound`
- `initial_lower_bound`
- `final_upper_bound`
- `final_lower_bound`
- `effective_exit_open_time`
- `exit_confirmation_open_time`
- `exit_direction`
- `resolution_kind`
- `duration_to_effective_exit_bars`
- `duration_to_confirmation_bars`
- `boundary_update_count`
- `failed_upside_exit_count`
- `failed_downside_exit_count`
- `ema27_cross_count`
- `close_inside_fraction`
- `source_r5_sections`
- `open_at_train_end`
- Python-computed display price bounds.

## Boundary-events CSV

One row per event:

- `ZONE_START`
- `BOUNDS_CONFIRMED`
- `UPPER_BOUND_EXPANDED`
- `LOWER_BOUND_EXPANDED`
- `UP_EXIT_CANDIDATE`
- `DOWN_EXIT_CANDIDATE`
- `FAILED_UPSIDE_EXIT`
- `FAILED_DOWNSIDE_EXIT`
- `EFFECTIVE_EXIT`
- `EXIT_CONFIRMATION`
- `TRAIN_END`

Include previous and new bound values and the causal reason.

## Exit-attempts CSV

One row per outside-close attempt with:

- zone and attempt IDs;
- direction;
- frozen boundary;
- candidate time;
- probation end;
- bars available;
- counts outside/inside;
- final close position;
- excursion high/low;
- clearance ATR;
- status;
- failure time and reason;
- effective exit and confirmation times.

## Bar-level CSV

Include OHLC, EMA27, EMA200, ATR14, slopes, active zone ID, active bounds before current bar, boundary version, inside/outside status, distance to each boundary in ATR, EMA27 crossing flag, active exit-candidate state, zone phase, and event IDs.

## Pine visualization

Create Pine Script v6 indicator:

`EXP-012 Long-Context Disputed Price Zones`

Rules:

- use `indicator()`, never `strategy()`;
- do not plot EMA27 or EMA200;
- use only Python-generated timestamps and bounds;
- yellow rectangle: `ZONE_START` through `EFFECTIVE_EXIT` using final accepted zone bounds;
- clearly different cyan/gray rectangle: `EFFECTIVE_EXIT` through `EXIT_CONFIRMATION`;
- draw final horizontal upper and lower zone boundaries;
- optionally show initial bounds and each boundary revision;
- default markers:
  - `Z` zone start;
  - `B` bounds confirmed;
  - `U+` upper expansion;
  - `L+` lower expansion;
  - `U?` upward exit candidate;
  - `D?` downward exit candidate;
  - `UF`/`DF` failed exit;
  - `E` effective exit;
  - `C` confirmation;
- show only first core trigger per zone by default;
- all core triggers behind an input defaulting false;
- section selector `ALL` plus individual zone IDs;
- use Python-computed box top/bottom, never current TradingView bar high/low.

## Manual review CSV

Create empty user fields for:

- zone validity;
- start correctness;
- initial upper/lower correctness;
- boundary expansion correctness;
- effective exit correctness;
- confirmation correctness;
- should merge/split;
- corrected bounds/times;
- Binance/Bybit source difference suspected;
- comments.

## Review instructions

Explain that the user checks:

- whether the box represents one accepted horizontal price area;
- whether repeated EMA27 crossings remain inside the same zone;
- whether a failed breakout correctly expands the boundary;
- whether the zone ends at the first accepted outside move;
- whether the cyan probation is visually separate from the yellow disputed zone;
- whether the December–January zone ends at the accepted break of its lower horizontal boundary rather than at a later EMA confirmation.

## Report

Report:

- why EXP-011B EMA/recovery state machines were stopped;
- the new price-zone object;
- causal seed construction;
- boundary-update logic;
- all zones and final bounds;
- all exit attempts;
- R5-to-zone mapping;
- acceptance results;
- Binance spot versus Bybit perpetual warning;
- no predictive or trading claim.

Status: `AWAITING_TW_PRICE_ZONE_REVIEW`.

## Project queue

Update `PROJECT_QUEUE.md`:

- EXP-011B is paused after R5 because EMA-centered conflict boundaries were not visually stable.
- EXP-012 studies causal horizontal disputed price zones in LONG context.
- Next action is TradingView validation of zone starts, bounds, boundary expansions, effective exits, and confirmations.
- Technical Ratings remains postponed until the zone boundaries are accepted.

## Safety and validation

- Never modify `docs/DEFINITIONS.md`.
- Never modify EXP-011 or EXP-011A.
- Preserve EXP-011B R1–R5 artifacts.
- Never stage or commit:
  `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`
- No date-specific, price-specific, or zone-ID-specific exceptions.
- Verify the current bar is excluded from all pre-bar boundary calculations.
- Verify candidate boundaries are frozen during probation.
- Verify boundaries only expand after failed outside attempts.
- Verify accepted exit uses six closed bars.
- Verify no data after `2024-01-08` is used.
- Verify Pine/CSV timestamps and bounds match.
- Verify Pine contains no EMA plots and no `strategy()`.
- Run `python3 -m py_compile` and deterministic rerun checks.

## Commit and result

Use implementation commit message:

`EXP-012 detect causal disputed price zones`

Follow `AGENTS.md`, including separately writing, committing, and pushing `.codex/RESULT.md`.

The result must report:

- implementation SHA and push status;
- task status;
- number of zones;
- every zone start, bounds-confirmation time, initial/final bounds, effective exit, confirmation, and exit direction;
- boundary update counts;
- failed/confirmed exit-attempt counts by direction;
- every acceptance result;
- R5 mapping;
- Pine and manual-review paths;
- final git status;
- confirmation that the unrelated EXP009A Pine remained unstaged.

## Standard launch command

`Выполни текущую задачу из .codex/TASK.md согласно AGENTS.md`
