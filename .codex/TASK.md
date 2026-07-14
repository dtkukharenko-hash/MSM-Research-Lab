# Current Codex Task

- task_id: `EXP-012-R3-HIERARCHICAL-PARENT-ZONES`
- status: `READY`
- published_at: `2026-07-14`
- target_branch: `main`
- commit_message: `EXP-012 model hierarchical parent zones and internal phases`

## Instruction precedence

This file is the only active task specification.

`.codex/TASK_ADDENDUM.md` applied only to `EXP-012-R2-ACCEPTED-BOUNDARY-STATE`. Treat it as historical R2 documentation, not as a separate active instruction. R3 incorporates and revises the useful EMA27 logic below.

## Objective

Revise:

`experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES`

R2 fixed the R1 causality and wick-boundary defects, but it incorrectly treated every accepted local price departure as the end of a full disputed zone. It produced six zones instead of the three broad processes visible in manual review:

- R2 `Z001` is the first compact parent process;
- R2 `Z002` and `Z003` are internal phases of one November parent process;
- R2 `Z004`, `Z005`, and `Z006` are internal phases of one December-January parent process.

R3 must model a hierarchy:

1. `PARENT_DISPUTED_ZONE` — the broad price-acceptance process.
2. `INTERNAL_PHASE` — a local accepted departure, extension, reversal, or renewed dispute inside the still-open parent.
3. `PARENT_RESOLUTION_CANDIDATE` — price and EMA27 geometry align in the same direction.
4. `CONFIRMED_PARENT_RESOLUTION` — the joint outside state persists causally.

A local accepted price departure must not irreversibly close the parent zone. It first becomes an internal phase event. The parent closes only after a fresh same-direction EMA27 departure and a joint persistence probation both confirm.

Final status:

`AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW`

## Scope

- Symbol: ADAUSDT.
- Timeframe: 4H only.
- LONG-context parent disputed zones only.
- Development period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`.
- Use the existing EXP-011 Binance spot 4H OHLC file.
- Do not use any bar after `2024-01-08`.
- Manual review remains Bybit ADAUSDT Perpetual 4H; report possible candle and boundary differences.
- Do not use Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtesting, forecasts, entries, exits, stops, position sizing, or trading logic.
- Preserve every R1 and R2 output.
- Never modify `docs/DEFINITIONS.md`, EXP-011, EXP-011A, or EXP-011B.

## Required reading

Before implementation read:

- `PROJECT_INSTRUCTIONS.md`
- `AGENTS.md`
- `.codex/TASK.md`
- EXP-012 R1 and R2 `TASK.md`, `REPORT.md`, `REVIEW_INSTRUCTIONS.md`
- R1 and R2 zone, attempt, extension, EMA27-departure, alignment, and Pine artifacts
- EXP-011B R5 only as historical mapping context

## Preserve R2 implementation

Do not overwrite the R2 implementation or R2 artifacts.

Create before R3 work:

- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r2_snapshot.py`

Copy the current R2 generator exactly into that file if the snapshot does not already exist. Do not modify it afterward.

Implement R3 in a new file:

- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/experiment_012_r3.py`

R3 may import stable feature helpers from the R2 snapshot only if doing so does not regenerate or overwrite R2 outputs. Prefer explicit local R3 logic where state-machine behavior differs.

## Keep from R2

Keep the validated causal foundations:

- complete-history warm-up before development slicing;
- EMA27, EMA200, ATR14, and open-time timestamps;
- LONG-context and initial parent-zone start logic;
- body-based robust initial boundaries;
- wick references as diagnostics only;
- sequential bar-by-bar price attempt processing;
- no data after an attempt decision bar;
- accepted body extensions, never wick-only boundary updates;
- core trigger as diagnostic only;
- chronological construction;
- no future-period access.

Do not keep the R2 rule that immediately consumes the timeline and starts a new full zone after every local accepted price departure.

## Core hierarchy

### Parent zone

A `PARENT_DISPUTED_ZONE` begins with the existing causal R2 zone-start and robust initial body-boundary construction.

It remains open through:

- accepted local departures without fresh matching EMA geometry;
- failed joint parent-resolution candidates;
- local reversals;
- accepted boundary extensions;
- repeated EMA27 crossings;
- temporary price movement above or below EMA27;
- EMA27/EMA200 crossing or approach by itself.

### Internal phase

Every R2-style outside-state decision becomes an `INTERNAL_PHASE_EVENT` first.

Required phase classifications:

- `INTERNAL_UP_DEPARTURE`
- `INTERNAL_DOWN_DEPARTURE`
- `INTERNAL_ACCEPTED_UP_EXTENSION`
- `INTERNAL_ACCEPTED_DOWN_EXTENSION`
- `INTERNAL_REJECTED_UP_EXCURSION`
- `INTERNAL_REJECTED_DOWN_EXCURSION`
- `INTERNAL_FAILED_JOINT_UP_RESOLUTION`
- `INTERNAL_FAILED_JOINT_DOWN_RESOLUTION`

An internal phase records local price behavior but does not itself close the parent.

## Parent price boundaries

Use R2 robust initial body boundaries:

- upper boundary from the median of the three highest causal `body_high` values in the aligned source interval;
- lower boundary from the median of the three lowest causal `body_low` values through lower-reaction confirmation;
- wick references stored separately.

Parent boundaries are frozen between accepted extension events.

### Parent accepted extension

A local price departure that does not confirm parent resolution may expand the parent only after it is causally reclaimed and qualifies as an accepted body shelf.

Use the validated R2 accepted-extension requirements:

- at least 3 closes outside the frozen parent boundary;
- at least 2 consecutive outside closes;
- median outside close at least `0.10 ATR14` beyond the frozen boundary, using candidate ATR;
- the move is later reclaimed enough to reject parent resolution;
- proposed boundary uses the median of up to three relevant outside body values;
- no wick-only update;
- all statistics end at the causal rejection bar.

A local price departure that later becomes a failed joint parent-resolution candidate can also become an accepted extension, but only using bars through the joint failure bar and only if the same body/close criteria pass.

## Local price departure state machine

Reuse the R2 sequential price state machine as a local departure detector:

- `OUTSIDE_CLEARANCE_ATR = 0.15`
- `MIN_DECISION_BARS = 4`
- `MAX_DECISION_BARS = 12`
- `DEEP_RECLAIM_ATR = 0.15`
- `OUTSIDE_MAJORITY = 0.60`

A local departure may become price-accepted using the same R2 directional conditions, but label it:

- `PRICE_ACCEPTED_UP_DEPARTURE`
- `PRICE_ACCEPTED_DOWN_DEPARTURE`

Do not close the parent at this step.

## EMA27 geometry: two scales

R2 showed that EMA27 compact-band departures are informative but its 12-bar events were too local and could duplicate one continuous move.

R3 must retain two separate EMA layers.

### Internal EMA layer

Keep the R2 12-bar compact-band departure detector only as an internal-phase diagnostic:

- `INTERNAL_EMA_LOOKBACK = 12`
- current bar excluded with `shift(1)` or equivalent causal indexing;
- same R2 compactness and departure thresholds;
- label events `INTERNAL_EMA_DEPARTURE`;
- never use this layer alone to close a parent.

### Parent EMA layer

Create a slower parent-resolution EMA detector:

- `PARENT_EMA_LOOKBACK = 24` closed 4H bars;
- prior source window excludes the current bar;
- `parent_ema_band_low_before_bar = min(EMA27[t-24:t-1])`;
- `parent_ema_band_high_before_bar = max(EMA27[t-24:t-1])`;
- `parent_ema_band_mid_before_bar = median(EMA27[t-24:t-1])`;
- `parent_ema_band_width_atr = (high-low)/ATR14[t]`;
- `parent_ema_net_change_atr = (EMA27[t-1]-EMA27[t-24])/ATR14[t]`;
- `ema_gap_atr = (EMA27-EMA200)/ATR14`;
- `ema_gap_change_6_atr` as in R2.

A prior parent EMA band is compact when both hold:

- `parent_ema_band_width_atr <= 0.90`;
- `abs(parent_ema_net_change_atr) <= 0.50`.

These are preregistered R3 constants. Do not tune them by date, zone, or expected output.

### Parent EMA departure candidate

Use:

- `PARENT_EMA_DEPARTURE_ATR = 0.10`

UP candidate:

- prior parent EMA band is compact;
- current EMA27 is above the frozen prior band high by at least `0.10 ATR14`;
- EMA27 change is positive.

DOWN candidate:

- prior parent EMA band is compact;
- current EMA27 is below the frozen prior band low by at least `0.10 ATR14`;
- EMA27 change is negative.

Freeze the parent EMA band at candidate detection.

Confirm after two consecutive closed bars remain beyond the frozen edge.

Classify:

- `PARENT_EMA_UP_AWAY_FROM_EMA200` when direction is UP and `ema_gap_change_6_atr > 0`;
- `PARENT_EMA_DOWN_TOWARD_EMA200` when direction is DOWN and `ema_gap_change_6_atr < 0`;
- `PARENT_EMA_UP_GAP_NOT_EXPANDING`;
- `PARENT_EMA_DOWN_GAP_NOT_SHRINKING`.

Only the first two classifications are directionally qualified for parent resolution.

## EMA rearm rule

Prevent duplicate events from one continuous EMA movement.

After a confirmed parent EMA departure, no new parent EMA candidate may be created until either:

1. `RETURN_REARM`: EMA27 closes inside the previous frozen band for two consecutive bars; or
2. `NEW_BAND_REARM`: at least 24 bars have elapsed after the previous confirmation and every bar used by the new 24-bar compact band is strictly later than the previous confirmation.

Record the rearm kind and time.

A repeated event before either rearm condition is a suppressed duplicate, not a new departure.

## Fresh price/EMA association

Do not associate a price departure with an arbitrarily old EMA event.

A parent EMA departure is fresh for a local price departure only when its confirmation occurs within this causal window:

- no earlier than 3 bars before the price candidate bar;
- no later than the local price-departure confirmation bar.

Use:

- `EMA_ASSOCIATION_PRE_BARS = 3`

Do not use the “most recent event anywhere earlier in the parent” rule from R2.

Record event age in bars and whether it is fresh, stale, opposite-direction, or absent.

## Parent-resolution candidate

Create a `PARENT_RESOLUTION_CANDIDATE` only when all hold:

1. A local price departure has reached `PRICE_ACCEPTED_UP_DEPARTURE` or `PRICE_ACCEPTED_DOWN_DEPARTURE`.
2. A fresh confirmed parent EMA departure exists in the same direction.
3. EMA geometry is directionally qualified:
   - UP requires `PARENT_EMA_UP_AWAY_FROM_EMA200`;
   - DOWN requires `PARENT_EMA_DOWN_TOWARD_EMA200`.

At candidate creation freeze:

- parent upper and lower boundaries;
- relevant parent boundary for the direction;
- price candidate and local confirmation times;
- parent EMA event and frozen EMA band;
- ATR14 at joint-candidate creation;
- first outside price close of the local accepted departure.

EMA alone never creates a parent-resolution candidate. Price alone never confirms parent resolution.

## Joint persistence probation

Use:

- `JOINT_PROBATION_BARS = 12`
- `JOINT_MIN_OUTSIDE_FRACTION = 0.67`
- `JOINT_MIN_EMA_BEYOND_FRACTION = 0.67`
- `JOINT_DEEP_RECLAIM_ATR = 0.15`

Evaluate strictly bar by bar from the first bar after local price-departure confirmation. Stop at the first causal success or failure. Never inspect later bars.

Maintain:

- observed bars;
- price closes outside the frozen parent boundary;
- price deep reclaims;
- EMA27 values beyond the frozen parent EMA edge;
- EMA27 returns inside the frozen band;
- EMA-gap directional changes;
- body and wick excursions;
- last timestamp used.

### Early failure

Fail immediately if either occurs before confirmation:

- 3 consecutive price closes deeply reclaim the frozen parent boundary;
- 3 consecutive EMA27 values return inside the frozen parent EMA band.

### Confirmation

At the 12th probation bar confirm only when all hold.

For UP:

- at least 8 of 12 price closes are above the frozen parent upper boundary;
- final close is above the frozen parent upper boundary;
- no 3-consecutive deep price reclaim run;
- at least 8 of 12 EMA27 values are above the frozen parent EMA upper edge;
- final EMA27 is above the frozen parent EMA upper edge;
- EMA27 remains above EMA200;
- final EMA gap is greater than the gap at joint-candidate creation.

For DOWN:

- at least 8 of 12 price closes are below the frozen parent lower boundary;
- final close is below the frozen parent lower boundary or no more than `0.10 ATR14` above it during a shallow retest;
- no 3-consecutive deep price reclaim run;
- at least 8 of 12 EMA27 values are below the frozen parent EMA lower edge;
- final EMA27 is below the frozen parent EMA lower edge;
- final EMA gap is smaller than the gap at joint-candidate creation.

Do not require EMA200 to slope downward for DOWN confirmation.

On success:

- `resolution_kind = CONFIRMED_PARENT_UP_RESOLUTION` or `CONFIRMED_PARENT_DOWN_RESOLUTION`;
- `effective_resolution_open_time = first outside price close of the successful local departure`;
- `local_price_confirmation_open_time = local accepted-departure confirmation`;
- `parent_resolution_confirmation_open_time = 12th joint probation bar`;
- close the parent only at parent-resolution confirmation.

Effective resolution must not be later than either confirmation time.

### Joint failure

On early failure or failure of the 12-bar criteria:

- label `FAILED_PARENT_UP_RESOLUTION` or `FAILED_PARENT_DOWN_RESOLUTION`;
- keep the same parent open;
- create an internal failed-joint phase;
- causally classify the price shelf as accepted extension or rejected excursion;
- update a parent boundary only if the accepted-extension body criteria pass;
- continue from the bar after the causal failure decision.

## Parent and phase chronology

Build parent zones in strict chronological order.

Within one open parent:

- internal phases may alternate direction;
- internal phases may overlap a local EMA diagnostic but must not overlap each other in decision state;
- a new local price candidate begins only after the prior local or joint candidate has ended;
- a confirmed parent resolution consumes the timeline through its confirmation;
- only a later fresh loss of agreement may start a new parent;
- unresolved parent at development end is `OPEN_AT_TRAIN_END`.

Do not post-process by manually merging parent zones or phases.

## Required baselines

Generate three deterministic models using identical parent starts and initial body boundaries:

1. `R3_HIERARCHICAL_PRICE_PLUS_PARENT_EMA` — primary hierarchy described above.
2. `PRICE_ONLY_IMMEDIATE_CLOSE_BASELINE` — R2-style immediate parent close after local accepted price departure.
3. `PRICE_PLUS_INTERNAL_EMA12_BASELINE` — parent close after local accepted price departure plus fresh same-direction 12-bar internal EMA event, using the same 3-bar freshness window and 12-bar joint probation.

Do not select a winner by manual fit. Report all three.

## Correct the prior diagnostic bug

Any comparison called “downside exit earlier than R1/R2” must filter explicitly for a DOWN parent resolution. Never use the first LC003-mapped event regardless of direction.

Add a validation test proving the compared event direction is DOWN.

## Expected manual structure

Acceptance tests are diagnostics only. Never hardcode dates, prices, parent IDs, phase IDs, R2 zone IDs, or expected counts inside detection logic.

Manual review currently suggests:

- one compact first parent;
- one November parent containing multiple internal phases;
- one December-January parent containing multiple internal phases;
- the November parent resolves upward with fresh parent EMA up-away geometry;
- the December-January parent does not resolve on the mid-December local up/down departures;
- its final candidate resolves downward with fresh parent EMA down-toward geometry.

## Required acceptance tests

Record PASS/FAIL honestly:

1. `EXPECTED_THREE_PARENT_ZONES`
2. `FIRST_PARENT_COMPACT`
3. `NOVEMBER_SINGLE_PARENT`
4. `NOVEMBER_HAS_MULTIPLE_INTERNAL_PHASES`
5. `DECEMBER_JANUARY_SINGLE_PARENT`
6. `DECEMBER_HAS_MULTIPLE_INTERNAL_PHASES`
7. `NOVEMBER_PARENT_UP_WITH_FRESH_EMA_UP_AWAY`
8. `DECEMBER_PARENT_DOWN_WITH_FRESH_EMA_DOWN_TOWARD`
9. `MID_DECEMBER_UP_REMAINS_INTERNAL`
10. `MID_DECEMBER_EARLY_DOWN_REMAINS_INTERNAL`
11. `FINAL_DOWNSIDE_COMPARISON_FILTERS_DIRECTION`
12. `NO_PARENT_CLOSE_FROM_PRICE_ONLY`
13. `NO_PARENT_CLOSE_FROM_EMA_ONLY`
14. `NO_STALE_EMA_ASSOCIATION`
15. `NO_DUPLICATE_PARENT_EMA_BEFORE_REARM`
16. `NO_POST_DECISION_DATA_USED`
17. `NO_WICK_ONLY_PARENT_BOUNDARY_UPDATE`
18. `NO_DATE_HARDCODING`
19. `NO_PRICE_HARDCODING`
20. `NO_PARENT_OR_PHASE_ID_HARDCODING`
21. `NO_FUTURE_PERIOD_USED`

The mid-December diagnostics may use post-run overlap with R2 local events for evaluation only. They must not influence the detector.

## Required R3 artifacts

Create without overwriting R1/R2 files:

- `artifacts/parent_disputed_zones_r3.csv`
- `artifacts/internal_phases_r3.csv`
- `artifacts/parent_price_departures_r3.csv`
- `artifacts/parent_joint_resolution_candidates_r3.csv`
- `artifacts/parent_boundary_events_r3.csv`
- `artifacts/parent_accepted_extensions_r3.csv`
- `artifacts/internal_ema27_departures_r3.csv`
- `artifacts/parent_ema27_departures_r3.csv`
- `artifacts/parent_ema27_rearm_events_r3.csv`
- `artifacts/price_parent_ema_alignment_r3.csv`
- `artifacts/r2_phase_parent_mapping_r3.csv`
- `artifacts/r3_model_comparison.csv`
- `artifacts/r3_acceptance_tests.csv`
- `artifacts/parent_zone_bar_features_r3.csv`
- `artifacts/manual_hierarchical_parent_review.csv`
- `artifacts/LONG_CONTEXT_HIERARCHICAL_PARENT_ZONES_R3.pine`

Update:

- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/TASK.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REPORT.md`
- `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/REVIEW_INSTRUCTIONS.md`
- `PROJECT_QUEUE.md`

Do not overwrite R1/R2 CSV or Pine artifacts.

## Parent-zone CSV minimum fields

Include at minimum:

- parent zone ID and model;
- display start;
- parent start;
- first core trigger;
- bounds confirmation;
- initial/final upper and lower body boundaries;
- wick references;
- boundary version count;
- accepted extension count by direction;
- internal phase count by direction/type;
- price departure count;
- joint candidate count;
- failed joint candidate count;
- effective resolution time;
- local price confirmation time;
- parent resolution confirmation time;
- resolution direction and kind;
- associated parent EMA event ID and classification;
- EMA event age in bars;
- open-at-train-end flag;
- R1/R2/R5 mappings;
- Python-computed display bounds.

## Internal-phase CSV minimum fields

One row per internal phase with:

- parent and phase IDs;
- phase type and direction;
- start, effective, decision, and end timestamps;
- price candidate/attempt ID;
- local price decision status;
- related internal EMA event IDs;
- related parent EMA event ID if fresh;
- fresh/stale/opposite/absent EMA relationship;
- whether a joint candidate was created;
- joint candidate result;
- whether the phase expanded a parent boundary;
- old/proposed/new boundary;
- last timestamp used;
- mapped R2 zone/attempt IDs.

## Joint-candidate CSV minimum fields

One row per parent-resolution candidate with:

- parent and joint candidate IDs;
- direction;
- frozen parent boundaries;
- frozen parent EMA band and edge;
- price candidate/effective/local-confirmation times;
- EMA candidate/confirmation times and classification;
- EMA association age in bars;
- joint probation start/end/decision times;
- bars observed;
- price outside count/fraction;
- longest price deep-reclaim run;
- EMA beyond count/fraction;
- longest EMA inside-return run;
- gap at candidate and decision;
- success/failure status and reason;
- effective parent resolution and final confirmation times;
- accepted-extension decision after failure;
- last timestamp used.

## Bar-level CSV

Include OHLC, body values, EMA27, EMA200, ATR14, internal and parent EMA bands, parent zone ID, phase ID, active parent boundaries before current bar, boundary version, local price-candidate state, parent joint-candidate state, price outside/reclaim counts, EMA beyond/return counts, fresh EMA association state, rearm state, event IDs, phase, and last timestamp used.

## Pine R3

Create Pine Script v6 indicator:

`EXP-012 Hierarchical Parent Zones R3`

Rules:

- use `indicator()`, never `strategy()`;
- do not calculate or plot EMA27/EMA200;
- use Python timestamps and Python-computed bounds/events;
- yellow box: parent disputed zone from start through effective resolution;
- light cyan/gray box: effective resolution through parent confirmation;
- parent body boundaries clearly visible;
- internal phases shown as optional lighter sub-boxes or bands, disabled by default;
- parent joint candidates marked separately from internal price departures;
- optional parent EMA event markers:
  - `PEU` parent EMA up-away;
  - `PED` parent EMA down-toward;
  - `PEG` other parent EMA geometry;
- optional internal EMA markers disabled by default;
- mark failed joint candidates and accepted parent extensions distinctly;
- selector `ALL` plus individual parent zones;
- model selector for the three required models;
- do not show all core triggers by default;
- no `strategy(`, `ta.ema`, `request.security`, or EMA plots.

## Manual review

The review CSV and instructions must ask:

- whether each parent box represents one broad accepted price process;
- whether R2 local zones are better interpreted as internal phases;
- whether November remains one parent until the true upward resolution;
- whether mid-December up/down departures remain internal;
- whether January downside movement becomes the parent resolution;
- whether the fresh parent EMA event is visually the long horizontal-band departure described by the user;
- whether EMA rearm prevents duplicate events;
- whether price effective resolution, local price confirmation, and parent confirmation are visually distinct;
- whether Binance spot versus Bybit perpetual differences could explain any boundary mismatch.

Do not ask for prediction or trading assessment.

## Report

Explain:

- why R2 segmentation was rejected despite its causal fixes;
- the parent-zone/internal-phase hierarchy;
- how a local accepted price departure differs from parent resolution;
- the 12-bar internal EMA layer versus 24-bar parent EMA layer;
- freshness and rearm rules;
- every parent, phase, joint candidate, parent EMA event, and boundary update;
- every R2-to-R3 mapping;
- primary versus both baselines;
- all acceptance results;
- Binance spot versus Bybit perpetual warning.

Do not claim predictive or trading value.

## Validation

Before commit verify:

- R2 generator snapshot exists and matches the pre-R3 R2 generator;
- all R1/R2 artifacts remain unchanged;
- parent construction is chronological and not post-merged;
- no local price departure closes a parent without a fresh directionally qualified parent EMA event and successful joint probation;
- EMA alone never closes a parent;
- every EMA association is within the 3-bar freshness window;
- duplicate parent EMA departures are suppressed until rearm;
- parent EMA prior bands exclude the current bar;
- no price, EMA, extension, or joint attempt reads after its decision timestamp;
- no boundary update uses wick-only evidence;
- failed joint candidates keep the parent open;
- effective resolution is not later than local or parent confirmation;
- the downside comparison filters direction explicitly;
- no data after `2024-01-08` is used;
- Pine and CSV timestamps match;
- Pine contains no strategy declaration or EMA calculations/plots;
- `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B are unchanged;
- the unrelated EXP009A Pine is not staged or committed.

Known unrelated local file:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Preserve it unstaged and uncommitted.

## Commit and result

Implementation commit message:

`EXP-012 model hierarchical parent zones and internal phases`

Follow `AGENTS.md`, including separately writing and committing `.codex/RESULT.md`.

The result must report:

- implementation SHA and push status;
- primary and baseline parent-zone counts;
- every primary parent with start, body bounds, internal-phase count, resolution direction, effective time, local price confirmation, parent confirmation, parent EMA event, and resolution kind;
- every internal phase and mapping from R2 zones/attempts;
- local price departure count by direction/status;
- joint candidate count, failed count, and confirmed count by direction;
- parent EMA event count by classification;
- suppressed duplicate count and rearm counts by kind;
- fresh/stale/opposite/no-EMA association counts;
- parent accepted-extension count by direction;
- result of every acceptance test;
- corrected DOWN-only comparison;
- artifact paths;
- final git status;
- confirmation that R1/R2 outputs were preserved;
- confirmation that EXP009A Pine was not staged.

## Standard launch command

`Выполни текущую задачу из .codex/TASK.md согласно AGENTS.md. .codex/TASK_ADDENDUM.md относится только к завершённому R2 и не является активной инструкцией для R3.`