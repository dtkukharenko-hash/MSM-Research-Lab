# EXP-004B — F1 Start Structure

## Context

F1 case #29 produced a local movement-ending observation. Validation against confirmed F1 cases
`1, 4, 5, 7, 17, 22` gave:

- full repeat: 0 / 6;
- partial repeat: 5 / 6;
- match with expert end: 0 / 6.

Therefore this experiment does not search for a universal ending rule. It checks whether confirmed F1
cases share an observable start structure.

## Cases

- 1
- 4
- 5
- 7
- 17
- 22
- 29

## Main Question

Do confirmed F1 cases have a repeated observable start structure?

## Data

- ADA/USDT
- 2023
- Timeframe: 4H
- Source: Irobot/backtester artifacts and OHLC feature export, read-only.

## Method

For each case, use only:

- 10 bars before the accepted start;
- the first 10 bars after the accepted start.

Movement endings are not analyzed.

For each case describe the start using observable features:

1. Direction of the first 1-5 candles.
2. Body sizes relative to the previous 5 and 10 candles.
3. Sequence of closes.
4. Update of local extremes from the previous 10 bars.
5. Depth of counter candles.
6. Presence or absence of acceleration.
7. Presence or absence of preliminary compression.
8. EMA position only as additional description, not as proof.

## Fixed Feature Checks

The following checks must not be changed during analysis:

- `directional_bodies_1_5`: at least 4 of the first 5 candle bodies point in the movement direction.
- `directional_close_steps_1_5`: at least 3 of the 4 close-to-close steps inside the first 5 bars move in the movement direction.
- `updates_prev10_extreme_1_5`: at least one of the first 5 bars updates the previous 10-bar high for UP cases, or previous 10-bar low for DOWN cases.
- `acceleration_present`: at least one of the first 5 bodies is >= 1.5x the average body of the previous 10 bars.
- `pre_body_compression`: average body of the previous 5 bars is lower than average body of the previous 10 bars.
- `pre_range_compression`: average range of the previous 5 bars is lower than average range of the previous 10 bars.
- `common_start_candidate`: `directional_bodies_1_5`, `directional_close_steps_1_5`, and `updates_prev10_extreme_1_5` are all true.

## Constraints

- Do not analyze movement endings.
- Do not change the criteria during analysis.
- Do not use vague phrases without observable details.
- Do not change Irobot.
- Do not change `docs/DEFINITIONS.md`.
- Do not create a trading strategy.
- Pine Script is only visual markup, not automatic recognition.

## Required Outputs

- `REPORT.md`
- `artifacts/F1_start_features.csv`
- `artifacts/F1_START_MARKUP.pine`

## Report Questions

1. Which start features repeat in at least 5 of 7 cases?
2. Which features appear only in separate cases?
3. Is there one common start mechanism?
4. Should F1 be split by start?
5. Verdict:
   - `COMMON_START_FOUND`
   - `PARTIAL_COMMON_START`
   - `NO_COMMON_START`
