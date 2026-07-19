# EXP-026 — ADA derivatives event episodes

Status: DERIVATIVES_EVENT_STRUCTURE_PARTIAL

## Hypothesis and data

Official Bybit ADAUSDT funding and 15-minute open interest independently sample causal event states.  Funding uses a preceding 90-calendar-day empirical percentile; OI uses preceding 30-day changes, median and MAD.  Current and future observations are excluded.  The endpoint/provenance, hashes, coverage, gaps and unavailable suffix are in `data_provenance.csv`.

## Method

Event membership and the 8H/24H grouping use only derivatives family, side and timestamp.  JOINT_EVENT matching is backwards 60 minutes. OHLC is a post-selection description: complete native 15m bars and deterministic complete UTC 1H bars provide frozen 4/8/32-bar geometry and five EXP-024 origins at each 8H representative. EXP-024/025 overlap is annotation only.

## Controls and results

Controls exactly match month, UTC hour, chronological third and available-history status. They are excluded from every derivatives event ±24h and every 8H episode interval, with deterministic SHA-256 tie-breaking. `robustness_summary.csv` reports raw and episode support, time thirds, 8H/24H compression, validity and event/control KS distances for every frozen representation—none is selected. `counterexamples.csv` retains invalidity, missing exact-stratum support, and low-displacement independent events.

## Verdict

**DERIVATIVES_EVENT_STRUCTURE_PARTIAL**. Derivatives events are independently measurable, but this one-market descriptive audit retains material support/geometry/control limitations and reports both merge views; it does not establish stable transferable structural distinction or choose a representation.
