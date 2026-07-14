# Current Codex Task

- task_id: `EXP-012-R2-ACCEPTED-BOUNDARY-STATE`
- status: `READY`
- published_at: `2026-07-14`
- target_branch: `main`
- commit_message: `EXP-012 model accepted boundary state causally`

## Objective

Revise:

`experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES`

R1 correctly changed the object from an EMA conflict window to a horizontal disputed price zone, but manual/code review found two major defects:

1. A failed exit attempt can use highs/lows from bars after the causal failure bar when expanding the boundary.
2. Initial and updated boundaries are based too strongly on single wick extremes. This absorbed the January downside move into Z003 instead of recognizing price acceptance below the disputed range.

R2 must model three distinct objects:

- `EXCURSION`: price temporarily moves beyond a boundary.
- `ACCEPTED_EXTENSION`: price forms an accepted shelf outside the old boundary but later returns to the larger disputed zone, so the zone boundary may expand.
- `ACCEPTED_EXIT`: price establishes a persistent outside state and the zone ends.

EMA27 and EMA200 remain context/diagnostics only. Price acceptance defines boundaries and zone resolution.

Final status:

`AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW`

## Scope

- ADAUSDT.
- 4H only.
- LONG-context disputed price zones only.
- Development period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`.
- Use the existing EXP-011 Binance spot 4H OHLC file.
- Do not use any bar after `2024-01-08`.
- Manual review remains Bybit ADAUSDT Perpetual 4H; report possible candle/boundary differences.
- Do not use Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, forecasts, or trading logic.
- Preserve all EXP-012 R1 outputs.

## Required reading

Before implementation read:

- `PROJECT_INSTRUCTIONS.md`
- `AGENTS.md`
- `.codex/TASK.md`
- EXP-012 R1 `REPORT.md`, code, zone CSV, boundary events, exit attempts, and Pine
- EXP-011B R5 only for historical comparison

## Snapshot R1

Create before R2 generation:

- `artifacts/long_context_disputed_zones_r1_snapshot.csv`
- `artifacts/zone_boundary_events_r1_snapshot.csv`
- `artifacts/zone_exit_attempts_r1_snapshot.csv`
- `artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES_R1_SNAPSHOT.pine`

Do not overwrite the snapshots.

## Keep unchanged

Keep the existing causal calculations for:

- EMA27 and EMA200;
- ATR14;
- LONG context;
- aligned run;
- zone start;
- core trigger as diagnostic only;
- open-time timestamps;
- chronological zone construction.

Do not reuse R1 boundary expansion or R1 six-bar exit-attempt implementation without the changes below.

## R2 principle

A horizontal zone boundary represents a price level accepted by repeated candle bodies/closes.

A single wick is an excursion, not an accepted boundary.

A failed break does not automatically expand a boundary.

An exit attempt must be evaluated bar by bar. Once it fails or confirms, later bars must not affect its excursion statistics or boundary decision.

## Robust initial boundaries

R1 used absolute highs/lows too directly. R2 must separate:

- `wick_extreme`;
- `accepted_body_boundary`.

For every candle define:

- `body_high = max(open, close)`
- `body_low = min(open, close)`

### Initial upper boundary

Use the same causal source interval as R1 upper seed:

- last confirmed aligned run through the bar before `ZONE_START`;
- fallback: previous 12 closed bars.

Calculate:

- `upper_wick_reference = max(high)`;
- `upper_body_candidates = the three highest body_high values in the interval`;
- `initial_upper_bound = median(upper_body_candidates)`.

If fewer than three bars exist, use the median of available body highs.

Store the wick reference, body candidates, and source interval.

### Initial lower boundary

Keep the R1 causal lower-reaction detection, but do not use the running minimum low as the final boundary.

From `ZONE_START` through `BOUNDS_CONFIRMED` calculate:

- `lower_wick_reference = min(low)`;
- `lower_body_candidates = the three lowest body_low values`;
- `initial_lower_bound = median(lower_body_candidates)`.

If fewer than three bars exist, use the median of available body lows.

Store:

- wick reference;
- body candidates;
- accepted body boundary;
- confirmation time;
- fallback status.

The wick reference is diagnostic only and must not define the active boundary by itself.

## Outside departure candidate

Use the current frozen active boundary and ATR at the current closed bar.

Keep:

`OUTSIDE_CLEARANCE_ATR = 0.15`

Up departure starts when:

`close > upper_bound + 0.15 * ATR14`

Down departure starts when:

`close < lower_bound - 0.15 * ATR14`

Freeze at candidate start:

- direction;
- active upper/lower boundaries;
- candidate boundary;
- ATR14;
- candidate time.

Only one active outside-state candidate may exist per zone.

## Bar-by-bar outside-state machine

Replace the R1 full-window function with a strictly sequential state machine.

Constants:

- `MIN_DECISION_BARS = 4`
- `MAX_DECISION_BARS = 12`
- `DEEP_RECLAIM_ATR = 0.15`
- `OUTSIDE_MAJORITY = 0.60`

For each newly closed bar after candidate start, update only using bars from candidate through the current bar:

- bars observed;
- outside-close count;
- inside-close count;
- consecutive outside closes;
- consecutive deep-inside closes;
- body highs/lows;
- wick highs/lows;
- current close position;
- EMA27 position diagnostics.

Do not inspect later bars.

### Outside/inside definitions

For an UP candidate:

- outside: `close > frozen_upper`;
- deep inside reclaim: `close < frozen_upper - 0.15 * ATR14`.

For a DOWN candidate:

- outside: `close < frozen_lower`;
- deep inside reclaim: `close > frozen_lower + 0.15 * ATR14`.

A shallow retest around the boundary is neither a deep reclaim nor immediate failure.

## Accepted exit

Starting from `MIN_DECISION_BARS`, confirm an accepted exit at the first bar where all general conditions hold.

### UP accepted exit

- observed bars >= 4;
- outside-close fraction >= 0.60;
- current close is above the frozen upper boundary;
- no run of 3 consecutive deep-inside reclaims;
- at least 60% of observed closes are above EMA27;
- EMA27 remains above EMA200.

### DOWN accepted exit

- observed bars >= 4;
- outside-close fraction >= 0.60;
- current close is below the frozen lower boundary, or no more than `0.10 ATR14` above it during a shallow retest;
- no run of 3 consecutive deep-inside reclaims;
- at least 60% of observed closes are below EMA27.

Do not require EMA200 to slope downward.

On confirmation:

- `resolution_kind = ACCEPTED_UPSIDE_EXIT_R2` or `ACCEPTED_DOWNSIDE_EXIT_R2`;
- `effective_exit_open_time = first outside close in the confirmed outside-state sequence`;
- `exit_confirmation_open_time = current bar`;
- close the zone causally at confirmation.

The confirmation may occur before 12 bars.

## Rejected excursion

Reject the outside candidate immediately when:

- 3 consecutive deep-inside reclaim closes occur before accepted exit; or
- the maximum 12 bars are reached without accepted exit.

At rejection, stop processing the attempt immediately.

All attempt statistics must use only:

candidate bar through rejection bar inclusive.

Never use a later bar's high, low, body, or close.

Record:

- rejection time;
- rejection reason;
- observed bars;
- outside fraction;
- longest consecutive outside run;
- longest deep-reclaim run;
- wick excursion;
- body excursion;
- close excursion.

## Accepted extension versus rejected wick

A rejected outside candidate does not automatically expand the zone.

Classify it after causal rejection.

### Accepted extension

A rejected attempt qualifies as `ACCEPTED_EXTENSION` only when all hold before or on the rejection bar:

1. At least 3 closes occurred outside the frozen boundary.
2. At least 2 outside closes were consecutive.
3. The median outside close is at least `0.10 ATR14` beyond the frozen boundary, using ATR frozen at candidate start.
4. The move was later reclaimed enough to reject the exit.

For an accepted UP extension:

- collect body highs for bars with outside closes;
- proposed upper boundary = median of the three highest outside body highs, or median of available values if fewer than three;
- new upper boundary = max(old upper, proposed upper).

For an accepted DOWN extension:

- collect body lows for bars with outside closes;
- proposed lower boundary = median of the three lowest outside body lows, or median of available values if fewer than three;
- new lower boundary = min(old lower, proposed lower).

Never update a boundary to a wick high/low.

### Rejected excursion only

If accepted-extension criteria are not met:

- classify `REJECTED_WICK_OR_SINGLE_EXCURSION`;
- do not change the boundary;
- preserve the zone.

Store wick extreme separately as diagnostic evidence.

## Boundary versioning

For every accepted extension record:

- old boundary;
- proposed body boundary;
- new boundary;
- direction;
- candidate and rejection times;
- outside closes used;
- body values used;
- wick extreme ignored;
- boundary version.

The opposite boundary must not change.

## Fixed-bound baseline

Create a deterministic diagnostic baseline using the same:

- zone starts;
- robust initial body boundaries;
- outside-state exit logic;

but never expand boundaries after rejected attempts.

Name it:

`FIXED_BODY_BOUNDS_BASELINE`

The primary R2 model is:

`ACCEPTED_EXTENSION_BODY_BOUNDS`

Generate a comparison CSV. Do not select a winner by manual fit; report both honestly.

## Expected manual structure and acceptance tests

Acceptance tests are diagnostics only. Never hardcode dates, prices, zone IDs, or expected outputs inside detection logic.

Required tests:

1. `EXPECTED_THREE_PRIMARY_ZONES`
   - manual review currently suggests three broad zones.

2. `FIRST_ZONE_COMPACT`
   - first zone remains independent and compact.

3. `NOVEMBER_SINGLE_ZONE`
   - November remains one horizontal disputed zone.

4. `DECEMBER_JANUARY_SINGLE_ZONE`
   - December-January remains one zone until accepted downside movement.

5. `DECEMBER_DOWNSIDE_EXIT_ACCEPTED`
   - primary R2 should test whether the December-January zone obtains an accepted DOWN exit before train end.
   - record PASS/FAIL honestly.

6. `DOWNSIDE_EXIT_EARLIER_THAN_R1`
   - compare only after the run.

7. `NO_POST_FAILURE_DATA_USED`
   - verify every rejected attempt's recorded extrema and body statistics end at its rejection bar.

8. `NO_WICK_ONLY_BOUNDARY_EXPANSION`
   - every boundary update must satisfy accepted-extension close/body criteria.

9. `NO_DATE_HARDCODING`
10. `NO_PRICE_HARDCODING`
11. `NO_ZONE_ID_HARDCODING`
12. `NO_FUTURE_PERIOD_USED`

## Required R2 artifacts

Create:

- `artifacts/long_context_disputed_zones_r2.csv`
- `artifacts/zone_boundary_events_r2.csv`
- `artifacts/zone_outside_state_attempts_r2.csv`
- `artifacts/zone_accepted_extensions_r2.csv`
- `artifacts/zone_bar_features_r2.csv`
- `artifacts/fixed_body_bounds_baseline.csv`
- `artifacts/r1_r2_zone_mapping.csv`
- `artifacts/r2_model_comparison.csv`
- `artifacts/r2_acceptance_tests.csv`
- `artifacts/manual_accepted_boundary_review.csv`
- `artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES_R2.pine`

Update:

- `experiment_012.py`
- local `TASK.md`
- `REPORT.md`
- `REVIEW_INSTRUCTIONS.md`
- `PROJECT_QUEUE.md`

## Zone CSV minimum fields

Include at minimum:

- zone_id;
- zone_start_open_time;
- bounds_confirmation_open_time;
- upper_wick_reference;
- upper_body_candidates;
- lower_wick_reference;
- lower_body_candidates;
- initial_upper_bound;
- initial_lower_bound;
- final_upper_bound;
- final_lower_bound;
- effective_exit_open_time;
- exit_confirmation_open_time;
- exit_direction;
- resolution_kind;
- accepted_extension_count;
- rejected_excursion_count;
- wick_only_rejection_count;
- close_inside_fraction;
- boundary_version_count;
- open_at_train_end;
- R1 mapping;
- Python-computed display bounds.

## Outside-state attempts CSV

One row per candidate with:

- zone_id;
- attempt_id;
- direction;
- frozen boundary;
- frozen ATR;
- candidate time;
- decision time;
- decision status;
- observed bars;
- outside-close count and fraction;
- inside-close count;
- longest outside run;
- longest deep-reclaim run;
- current/final close position;
- wick high/low;
- body high/low;
- median outside close;
- accepted-exit flag;
- accepted-extension flag;
- rejection reason;
- effective exit and confirmation times;
- last data timestamp used by the attempt.

## Bar-level CSV

Include R1 fields plus:

- body_high;
- body_low;
- active model;
- active candidate state;
- observed candidate bars;
- outside fraction so far;
- consecutive outside count;
- consecutive deep-reclaim count;
- accepted-extension decision;
- active body boundaries before current bar;
- wick references;
- boundary version;
- last attempt data timestamp.

## Pine R2

Create Pine Script v6 indicator:

`EXP-012 Accepted Boundary Price Zones R2`

Rules:

- use `indicator()`, never `strategy()`;
- do not plot EMA27 or EMA200;
- use Python timestamps and Python price bounds;
- yellow box: active disputed zone through effective exit;
- light cyan/gray: effective exit through causal confirmation;
- horizontal final body boundaries clearly visible;
- optional dotted wick-reference lines, disabled by default;
- mark accepted boundary extensions separately from wick-only rejected excursions;
- show outside candidate, accepted exit, rejected excursion, and boundary-update events;
- selector `ALL` plus individual zones;
- optional model selector: primary R2 versus fixed-body baseline;
- do not show every core trigger by default.

## Manual review

The review CSV and instructions must ask:

- does the body-based initial range match the visually accepted price area better than wick extremes;
- did a single wick incorrectly move a boundary;
- did accepted extensions represent repeated price acceptance;
- was the January downside move recognized as an accepted outside state;
- is effective exit separated from causal confirmation;
- does fixed-bound baseline or accepted-extension primary better preserve the same broad zone without swallowing the exit.

Do not analyze prediction or trading value.

## Report

Explain:

- the R1 lookahead defect;
- the exact causal fix;
- why wick extremes and accepted body boundaries are separated;
- initial boundary values for every zone;
- every outside-state candidate and decision;
- every accepted extension and rejected wick excursion;
- primary versus fixed-bound baseline comparison;
- all acceptance results;
- Binance spot versus Bybit perpetual warning.

Status:

`AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW`

Do not claim predictive or trading value.

## Validation

Before commit verify:

- all R1 snapshots exist;
- no attempt reads bars after its recorded decision/failure time;
- failure-bar extrema use only candidate through failure inclusive;
- no boundary is updated from a wick alone;
- initial boundaries use body-based robust estimators;
- accepted extensions use outside closes and body levels;
- the fixed-bound baseline uses identical starts and exit logic;
- no data after `2024-01-08` is used;
- Pine and CSV timestamps match;
- Pine contains no `strategy(` and no EMA plots;
- `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B are unchanged;
- existing unrelated EXP009A Pine is not staged or committed.

Known unrelated local file:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Preserve it unstaged and uncommitted.

## Commit and result

Implementation commit message:

`EXP-012 model accepted boundary state causally`

Follow `AGENTS.md`, including separately writing and committing `.codex/RESULT.md`.

The result must report:

- implementation SHA and push status;
- R1 and R2 zone counts;
- primary and fixed-bound baseline counts;
- every R2 zone with initial/final body bounds, exit direction, effective exit, confirmation, and resolution kind;
- outside candidate count;
- accepted exits by direction;
- accepted extensions by direction;
- rejected wick/single excursions;
- result of every acceptance test;
- whether December downside exit was accepted;
- R1/R2 mapping;
- artifact paths;
- final git status;
- confirmation that EXP009A Pine was not staged.

## Standard launch command

`Выполни текущую задачу из .codex/TASK.md согласно AGENTS.md`
