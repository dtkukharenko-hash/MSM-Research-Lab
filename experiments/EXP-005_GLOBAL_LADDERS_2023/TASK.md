# EXP-005 — Global ADA 2023 Ladders

## Goal

Build a retrospective candidate map of global ADA/USDT 4H ladders for 2023 and locate the previous 50 local EXP-004 movements inside that broader context.

## Context

The EXP-004 sample of 50 movements contains short local segments of roughly 3-8 bars. It must not be treated as a complete map of global ADA 2023 movements.

Preliminary visual review suggested that 2023 may contain about 7 large ladders, with the last one possibly transitioning into 2024.

## Data

- Symbol: ADA/USDT.
- Timeframe: 4H.
- Period requested: 2023.
- Source: Irobot/backtester data, read-only.
- Local movement overlay: `experiments/EXP-004_MARCH_FEATURES/artifacts/exp004_movement_sample.csv`.

## Method

1. Use the full ADA/USDT 4H data available from the read-only Irobot source.
2. Do not use the existing 50 EXP-004 local cases as global movement boundaries.
3. First build a retrospective candidate markup of large ladders.
4. For each candidate ladder record:
   - ladder_id;
   - direction;
   - start_time;
   - end_time;
   - start_price;
   - end_price;
   - duration_bars;
   - total_return;
   - assumed march count;
   - assumed platform count;
   - which of the old 50 local cases fall inside it;
   - share of the global ladder covered by those local cases.
5. Create an overview chart for the available 2023 window and mark all candidate ladder boundaries.
6. Do not automatically mark internal marches.

## Constraints

- This is a retrospective map, not a live detector.
- Do not search for profit.
- Do not build a trading strategy.
- Do not change `docs/DEFINITIONS.md`.
- Use Irobot only as a read-only data source.
- Do not use ZigZag as final proof of boundaries.
- Do not continue clustering the old 50 cases as standalone global movements.

## Required Artifacts

- `REPORT.md`
- `artifacts/global_ladders_2023.csv`
- `artifacts/GLOBAL_LADDERS_2023.pine`
- `artifacts/GLOBAL_LADDERS_2023_OVERVIEW.pdf`

## Report Questions

1. How many global ladders were found?
2. Is the count really around 7?
3. What share of each ladder is covered by the old 50 movements?
4. Are the old 50 movements starts, middles, or ends of ladders?
5. Can the old sample be used further without global context?

## Verdict Options

- `GLOBAL_MAP_BUILT`
- `GLOBAL_BOUNDARIES_AMBIGUOUS`
- `DATA_INSUFFICIENT`
