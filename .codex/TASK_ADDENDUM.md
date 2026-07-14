# Mandatory Addendum to Current Codex Task

- applies_to: `EXP-012-R2-ACCEPTED-BOUNDARY-STATE`
- status: `REQUIRED`
- published_at: `2026-07-14`

## New observation

In the disputed price zones, EMA27 itself often spends a long time inside a narrow, almost horizontal band and then leaves that band.

The direction of that EMA27 departure relative to EMA200 appears informative:

- In the November zone, EMA27 leaves its prior horizontal band upward and moves away from EMA200. This is consistent with an accepted upside resolution.
- In the December-January zone, EMA27 leaves its prior horizontal band downward and moves toward EMA200. This is consistent with deterioration of the LONG-context state and a downside resolution process.

EMA27/EMA200 must still not define the horizontal price-zone boundaries. Price acceptance remains the primary definition of the zone and its accepted exit. EMA geometry is a second causal layer describing how the fast mean leaves its own accepted band and whether the EMA27-EMA200 gap expands or contracts.

## Required EMA27 band diagnostics

Add causal features computed only from closed bars.

Use a trailing prior window that excludes the current bar:

- `EMA27_BAND_LOOKBACK = 12` 4H bars.
- `ema27_band_low_before_bar = min(EMA27[t-12:t-1])`.
- `ema27_band_high_before_bar = max(EMA27[t-12:t-1])`.
- `ema27_band_mid_before_bar = median(EMA27[t-12:t-1])`.
- `ema27_band_width_atr = (band_high - band_low) / ATR14[t]`.
- `ema27_net_change_12_atr = (EMA27[t-1] - EMA27[t-12]) / ATR14[t]`.
- `ema_gap_atr = (EMA27 - EMA200) / ATR14`.
- `ema_gap_change_6_atr = ((EMA27-EMA200)[t] - (EMA27-EMA200)[t-6]) / ATR14[t]`.

Define a prior EMA27 band as `EMA27_COMPACT_BAND` when both hold:

- `ema27_band_width_atr <= 0.60`;
- `abs(ema27_net_change_12_atr) <= 0.35`.

These constants are preregistered diagnostics. Do not tune them by zone ID or date.

## EMA27 band-departure events

A causal upward departure candidate occurs when:

- the prior 12-bar EMA27 band is compact;
- current EMA27 is above `ema27_band_high_before_bar + 0.10 * ATR14`;
- EMA27 change is positive.

A causal downward departure candidate occurs when:

- the prior 12-bar EMA27 band is compact;
- current EMA27 is below `ema27_band_low_before_bar - 0.10 * ATR14`;
- EMA27 change is negative.

Confirm a departure after two consecutive closed bars remain beyond the frozen prior band edge.

At candidate time freeze the prior EMA27 band. Do not move the frozen band during confirmation.

Classify confirmed departures:

- `EMA27_EXIT_UP_AWAY_FROM_EMA200` when EMA27 exits upward and `ema_gap_change_6_atr > 0`;
- `EMA27_EXIT_DOWN_TOWARD_EMA200` when EMA27 exits downward and `ema_gap_change_6_atr < 0`;
- `EMA27_EXIT_UP_GAP_NOT_EXPANDING`;
- `EMA27_EXIT_DOWN_GAP_NOT_SHRINKING`.

EMA200 slope is diagnostic only. Do not require EMA200 to turn downward.

## Relation to price-zone resolution

Keep the primary R2 price-only state machine exactly as specified in `.codex/TASK.md`.

Additionally build a diagnostic comparison layer:

1. `PRICE_ONLY_ACCEPTANCE` — the primary R2 result.
2. `PRICE_PLUS_EMA_GEOMETRY` — the same price-zone events annotated by the most recent confirmed EMA27 band departure.

Do not close a zone from EMA27 alone.

For each accepted price exit report whether, before or by causal confirmation, there was:

- an EMA27 exit in the same direction;
- movement toward or away from EMA200;
- no EMA27 band exit;
- an opposite-direction EMA27 exit.

For every failed price departure also report whether EMA27 remained inside its compact band or departed in the same/opposite direction.

The main research questions are:

- Does the November accepted upside exit coincide with `EMA27_EXIT_UP_AWAY_FROM_EMA200`?
- Does the December-January downside process show `EMA27_EXIT_DOWN_TOWARD_EMA200` before or during accepted downside price movement?
- Does EMA27 geometry help distinguish accepted exit from a temporary price excursion without redefining zone boundaries?

Record PASS/FAIL honestly. Never hardcode dates, prices, or zone IDs in detection logic.

## Required additional artifacts

Create:

- `artifacts/ema27_band_departures_r2.csv`
- `artifacts/price_ema_geometry_alignment_r2.csv`
- `artifacts/price_only_vs_price_ema_geometry_r2.csv`

Add the EMA27-band fields and active/frozen departure state to `zone_bar_features_r2.csv`.

At minimum `ema27_band_departures_r2.csv` must include:

- event ID and zone ID;
- candidate and confirmation open times;
- direction;
- frozen band low/high/mid;
- band width in ATR;
- EMA27 value and ATR at candidate;
- EMA27-EMA200 gap in ATR;
- six-bar gap change in ATR;
- confirmed classification;
- related price exit/extension/failed excursion IDs;
- causal last timestamp used.

## Pine addition

Do not plot EMA27 or EMA200.

Add optional markers, disabled by default:

- `EU` — confirmed EMA27 departure upward away from EMA200;
- `ED` — confirmed EMA27 departure downward toward EMA200;
- `EG` — other confirmed EMA27 departure geometry.

Add input:

- `showEma27BandDepartureEvents = false`.

## Report and acceptance additions

Add acceptance diagnostics:

- `NOVEMBER_EMA27_EXIT_UP_AWAY`
- `DECEMBER_EMA27_EXIT_DOWN_TOWARD_EMA200`
- `EMA_GEOMETRY_NEVER_DEFINES_PRICE_BOUNDARY`
- `EMA_DEPARTURE_CAUSAL_NO_CURRENT_BAR_IN_PRIOR_BAND`
- `NO_EMA_ONLY_ZONE_CLOSE`

The report must distinguish clearly:

- horizontal price-zone acceptance;
- EMA27 compact-band departure;
- direction of EMA27 relative to EMA200;
- causal confirmation time for each layer.

This addendum is mandatory and must be read together with `.codex/TASK.md` before implementation.
