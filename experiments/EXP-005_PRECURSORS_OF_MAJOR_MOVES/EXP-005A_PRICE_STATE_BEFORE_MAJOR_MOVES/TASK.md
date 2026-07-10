# EXP-005A — Price State Before Major Moves

## Goal

Check which OHLC-only price states precede major ADAUSDT 4H movements while fully excluding the last 12 calendar months of available data as holdout.

## Period Rule

Compute the period from the data:

- `data_end` = maximum ADAUSDT 4H timestamp in the backtester source.
- `research_end` = `data_end` minus 12 calendar months.
- Research includes only bars with `timestamp <= research_end`.
- Holdout includes `research_end < timestamp <= data_end`.

The holdout period must not be used for:

- major movement search;
- boundary definition;
- feature calculation;
- threshold selection;
- control windows;
- visual review;
- intermediate decisions.

## Data

- Asset: ADAUSDT
- Timeframe: 4H
- Source: Irobot/backtester, read-only
- Inputs allowed: OHLC and time only

## Not Used

- EMA27
- EMA200
- any other indicators
- ZigZag
- volume
- funding
- open interest
- profit
- trade entries
- strategy logic

## Stage 1 — Major Movements

Within the research period only, find major directional movements.

Rules:

- Do not import the 21 movement boundaries from the parent EXP-005 report.
- Do not use the previous 50 local movements.
- Boundaries are retrospective candidate boundaries.
- If a candidate movement reaches the research boundary without independent confirmation inside research, mark it as `CENSORED` and exclude it from precursor statistics.

For each movement save:

- move_id
- direction
- start_time
- end_time
- start_price
- end_price
- duration_bars
- return_pct
- confidence: HIGH / MEDIUM / LOW
- start basis
- end basis

## Stage 2 — Price State Before Start

Primary window:

- 30 closed bars immediately before `start_time`.

Additional windows:

- 50 bars
- 20 bars
- 10 bars
- 5 bars

No bars after `start_time` may be used to describe precursor state.

## Stage 3 — OHLC Features

For each window calculate:

- net_return
- absolute price path
- efficiency_ratio
- up candle share
- down candle share
- direction change count
- maximum directional close series
- high-low range
- last close position inside range
- average body change from first third to last third
- average true range change from first third to last third
- new high count
- new low count
- max pullback depth
- failed previous-direction attempt
- last 5 bars: directions, bodies, extremes, acceleration

## Working State Labels

Use only these working labels:

- `OPPOSITE_TREND`
- `SAME_TREND`
- `RANGE`
- `CHOP`
- `TRANSITION`
- `UNKNOWN`

These are comparison labels, not MSM model objects.

## Control

For each real start select at least 5 control 30-bar windows:

- only from the research period;
- not closer than 50 bars to any major start;
- not intersecting a major movement;
- volatility-nearest where possible;
- no holdout use.

Classify controls with the same rules.

## Stability

Check whether the 30-bar state class changes when `start_time` is shifted by ±1–3 bars.

## Required Artifacts

- `REPORT.md`
- `artifacts/major_moves_research_period.csv`
- `artifacts/price_state_windows.csv`
- `artifacts/control_windows.csv`
- `artifacts/start_shift_stability.csv`
- `artifacts/PRICE_STATE_PRECURSORS.pine`
- `artifacts/PRICE_STATE_PRECURSORS_OVERVIEW.pdf`

## Pine

Pine Script v6 must:

- use no EMA;
- mark research-period major movement starts;
- highlight 30 bars before each start;
- label move_id, direction, and assigned state;
- shade holdout and label it `HOLDOUT - NOT USED`;
- avoid any trading signal.

## Verdict Options

- `OPPOSITE_STATE_CANDIDATE_FOUND`
- `MULTIPLE_PRECURSOR_STATES_FOUND`
- `WEAK_PRICE_STATE_EVIDENCE`
- `NO_STABLE_PRICE_STATE`
- `GLOBAL_BOUNDARIES_AMBIGUOUS`
- `DATA_INSUFFICIENT`
