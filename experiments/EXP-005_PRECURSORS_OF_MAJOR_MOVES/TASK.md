# EXP-005 — Precursors Of Major Moves

## Goal

Understand which market states regularly precede major ADAUSDT movements in the available historical backtester period.

## Scope

The available read-only backtester feature history starts at `2023-07-01 00:00 UTC` and ends at `2026-07-01 00:00 UTC`.

This experiment does not make claims about the full calendar year 2023. It uses only the available historical period.

## Data

- Asset: ADAUSDT
- Source: Irobot/backtester, read-only
- Timeframe: 4H
- Study period: full available data period found in the source

## Allowed Indicators

- EMA27
- EMA200

## Not Used

- ZigZag as proof
- Other indicators
- Profit
- Entries
- Trading strategy
- Parameter optimization

## Stage 1 — Major Movements

Find major directional movements across the available period.

Rules:

- Do not use the previous 50 local EXP-004 movements as ready-made markup.
- Use retrospective candidate boundaries.
- Include both LONG and SHORT movements.
- Do not predefine the number of movements.
- If a movement continues across a calendar boundary, keep it as one continuous movement.

For each movement save:

- move_id
- direction
- start_time
- end_time
- duration_bars
- total_return_pct
- confidence: HIGH / MEDIUM / LOW

If the start cannot be defined confidently, mark it as such.

## Stage 2 — Pre-Start Windows

For each movement take only windows before the accepted start:

- 50 bars
- 30 bars
- 20 bars
- 10 bars
- 5 bars

After the start, use price only to confirm that a major movement happened. Do not use post-start data to describe the precursor window.

## Stage 3 — Market State Before Start

Describe the state before the start.

Price:

- slope
- acceleration or deceleration
- range
- compression or expansion
- direction changes
- local extreme updates
- pullback depth

EMA27:

- direction
- slope change
- distance from price
- crossings

EMA200:

- price position
- distance
- EMA200 direction

Last 5 candles:

- body sizes
- sequence
- acceleration
- tempo change
- false attempts

## Stage 4 — Control

For each movement select at least 3 control windows of the same lengths that are not near a major movement start.

Compare real precursor windows with control windows.

## Stage 5 — Naming

Do not use predefined concepts as classifications:

- march
- ladder
- platform
- accumulation
- impulse

If recurring states appear, name them neutrally:

- STATE-A
- STATE-B
- STATE-C

## Required Artifacts

- `REPORT.md`
- `artifacts/major_moves.csv`
- `artifacts/precursor_windows.csv`
- `artifacts/MAJOR_MOVE_PRECURSORS.pine`
- `artifacts/MAJOR_MOVE_PRECURSORS_OVERVIEW.pdf`

## Pine Script

The Pine script must show:

- EMA27
- EMA200
- start of each major movement
- 30-bar window before start

The script is a visual verification tool only. It must not implement an automatic signal.

## Verdict Options

- `PRECURSOR_CANDIDATES_FOUND`
- `WEAK_PRECURSOR_EVIDENCE`
- `NO_STABLE_PRECURSORS`
- `GLOBAL_BOUNDARIES_AMBIGUOUS`
- `DATA_INSUFFICIENT`
