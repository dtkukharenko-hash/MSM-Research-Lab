# EXP-004B — F1 Start Structure Report

## Scope

This report checks only the start structure of confirmed F1 cases:

- 1
- 4
- 5
- 7
- 17
- 22
- 29

For each case, the analyzed window is exactly 10 bars before the accepted start and the first 10 bars
after the accepted start. Movement endings are not analyzed.

Source data:

- F1 case list: `experiments/EXP-004_MARCH_FEATURES/EXP-004A_FAMILY_DISCOVERY/artifacts/F1_cases.csv`
- Read-only OHLC feature export from Irobot/backtester:
  `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv`

Detailed artifact:

- `artifacts/F1_start_features.csv`
- `artifacts/F1_START_MARKUP.pine`

## Fixed Checks

The checks were fixed before comparing cases:

| Feature | Meaning |
|---|---|
| `directional_bodies_1_5` | At least 4 of the first 5 candle bodies point in the movement direction. |
| `directional_close_steps_1_5` | At least 3 of the 4 close-to-close steps inside the first 5 bars move in the movement direction. |
| `updates_prev10_extreme_1_5` | At least one of the first 5 bars updates the previous 10-bar high for UP cases, or previous 10-bar low for DOWN cases. |
| `acceleration_present` | At least one of the first 5 bodies is >= 1.5x the average body of the previous 10 bars. |
| `pre_body_compression` | Average body of the previous 5 bars is lower than average body of the previous 10 bars. |
| `pre_range_compression` | Average range of the previous 5 bars is lower than average range of the previous 10 bars. |
| `common_start_candidate` | `directional_bodies_1_5`, `directional_close_steps_1_5`, and `updates_prev10_extreme_1_5` are all true. |

EMA20 is recorded only as context and is not used as proof.

## Feature Counts

| Feature | Repeated | Counterexamples |
|---|---:|---|
| At least 4 of first 5 bodies in movement direction | 6 / 7 | case #22 |
| At least 3 of first 4 close steps in movement direction | 6 / 7 | case #22 |
| Previous 10-bar extreme updated in first 5 bars | 5 / 7 | cases #22, #29 |
| At least one first-5 body >= 1.5x previous 10-bar average body | 6 / 7 | case #7 |
| Previous 5-bar average body lower than previous 10-bar average body | 5 / 7 | cases #1, #7 |
| Previous 5-bar average range lower than previous 10-bar average range | 5 / 7 | cases #7, #22 |
| Start close on directional side of EMA20 | 5 / 7 | cases #5, #7 |
| `common_start_candidate` | 5 / 7 | cases #22, #29 |

## Case Summary

| case_id | direction | first 5 bodies | close steps | prev10 extreme update | acceleration | pre-body compression | pre-range compression | common candidate |
|---:|---|---|---:|---|---|---|---|---|
| 1 | UP | UP, UP, UP, UP, DOWN | 3 / 4 | yes, bar 1 | yes | no | yes | yes |
| 4 | UP | UP, UP, UP, UP, DOWN | 3 / 4 | yes, bar 3 | yes | yes | yes | yes |
| 5 | UP | UP, UP, UP, UP, DOWN | 3 / 4 | yes, bar 3 | yes | yes | yes | yes |
| 7 | UP | UP, UP, DOWN, UP, UP | 3 / 4 | yes, bar 4 | no | no | no | yes |
| 17 | UP | UP, UP, UP, DOWN, UP | 3 / 4 | yes, bar 3 | yes | yes | yes | yes |
| 22 | UP | UP, DOWN, UP, UP, DOWN | 2 / 4 | no | yes | yes | no | no |
| 29 | DOWN | DOWN, DOWN, UP, DOWN, DOWN | 3 / 4 | no | yes | yes | yes | no |

## Features Repeating In At Least 5 Of 7 Cases

1. Directional body majority in the first 5 bars: 6 / 7.
   The first five candles usually contain at least four bodies in the accepted movement direction.

2. Directional close-step majority in the first 5 bars: 6 / 7.
   The first five-bar window usually has at least three close-to-close steps in the movement direction.

3. Early update of previous 10-bar extreme: 5 / 7.
   In most cases, the start window takes out the previous local high for UP cases, or the previous local
   low for DOWN cases.

4. At least one larger body inside the first 5 bars: 6 / 7.
   The start is not always a large first candle, but one of the first five bodies usually reaches at
   least 1.5x the previous 10-bar average body.

5. Preliminary body compression: 5 / 7.
   In most cases, the previous 5 bars have a lower average body than the previous 10 bars.

6. Preliminary range compression: 5 / 7.
   In most cases, the previous 5 bars have a lower average range than the previous 10 bars.

## Features Appearing Only In Separate Cases

- Large first candle is not common. The accepted start candle itself ranges from `0.04x` to `1.67x` of
  the previous 5-bar average body, so the first candle is not a stable standalone start marker.
- Immediate previous-10-bar breakout on bar 1 appears in case #1, but not in most cases.
- EMA20 alignment is mixed: 5 / 7 start closes are on the directional side of EMA20, but cases #5 and
  #7 start against that context. EMA remains descriptive only.
- A completely clean first-five directional sequence is absent. Every checked case has at least one
  counter body inside the first five bars.

## Counterexamples

### Case #22

Case #22 is the strongest counterexample to a single common start structure:

- only 3 of the first 5 bodies are in the UP direction;
- only 2 of 4 close-to-close steps move in the UP direction;
- no previous 10-bar high is updated in the first 5 bars;
- previous range compression is absent.

It still has acceleration and body compression, but it does not match the common candidate structure.

### Case #29

Case #29 matches directional bodies and close steps, but does not update the previous 10-bar low in the
first five bars. It is also the only DOWN case among the confirmed set, so it may represent either a
directional asymmetry or a separate start subtype.

## Is There One Common Mechanism?

There is a partial common mechanism:

> after a relatively compressed local context, the start usually forms a five-bar directional cluster:
> at least four bodies and at least three close steps point in the movement direction, and in most cases
> this cluster updates the previous 10-bar local extreme.

This is not a complete mechanism for all confirmed F1 cases. It fails on #22 and partially fails on #29.

## Should F1 Be Split By Start?

Yes, F1 should remain split-worthy by start until more cases are checked.

Candidate split suggested by the observed data:

- F1-S1: directional cluster with early previous-10-bar extreme update. Cases: #1, #4, #5, #7, #17.
- F1-S2: directional cluster without early previous-10-bar extreme update. Case: #29.
- F1-S3: choppy start with weaker first-five directional agreement. Case: #22.

This is only a descriptive split proposal for future review. It is not a trading rule and not a model
definition.

## Answers

1. Features repeating in at least 5 of 7:
   directional body majority, directional close-step majority, early previous-10-bar extreme update,
   first-five acceleration, preliminary body compression, preliminary range compression.

2. Features appearing only in separate cases:
   large first candle, immediate bar-1 breakout, clean first-five direction without a counter body, and
   EMA20 alignment.

3. One common start mechanism:
   partially yes, but not universal.

4. Need to split F1 by start:
   yes, at least provisionally, because #22 and #29 are meaningful counterexamples.

## Verdict

# PARTIAL_COMMON_START
