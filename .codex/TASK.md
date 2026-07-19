# Current Codex Task

- task_id: `EXP-026-ADA-DERIVATIVES-EVENT-EPISODES`
- status: `READY`
- published_at: `2026-07-19`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-025-ADA-LOWER-TIMEFRAME-DEOVERLAP`
- commit_message: `EXP-026 ADA derivatives event episodes`

## Objective

Test whether independently sampled ADAUSDT derivatives-market events define causal structural episodes that are not created by the OHLC parent/counter detector.

EXP-025 rejected episode-robust transfer of the lower-timeframe OHLC detector. Therefore event membership in EXP-026 must be determined only from funding-rate and open-interest histories. OHLC may describe the already selected event state, but may not create, remove, merge or rank events.

This is a descriptive causal research experiment. It is not a trading rule, entry/exit study, threshold search or outcome optimisation.

## Authorised data sources

Use official Bybit V5 public endpoints only:

- funding history: `GET https://api.bybit.com/v5/market/funding/history`;
- open interest: `GET https://api.bybit.com/v5/market/open-interest`;
- instrument metadata: `GET https://api.bybit.com/v5/market/instruments-info` only to verify the funding interval;
- `category=linear`, `symbol=ADAUSDT`.

For open interest use `intervalTime=15min`. Use the exact EXP-023/EXP-024 range `2023-07-01T00:00:00Z` through `2024-12-31T23:00:00Z`. Store raw funding and OI archives outside GitHub under `${HOME}/.local/share/msm-market-data/bybit/linear/ADAUSDT/`, using deterministic CSV schemas and atomic writes. Existing validated OHLC archives remain unchanged.

Record endpoint, parameters, retrieval time, pagination, retries, hashes, schema, coverage, gaps, duplicates, ordering, numeric validity and unavailable prefixes/suffixes. Do not fabricate, interpolate or forward-fill observations.

## Frozen independent event definitions

All thresholds are fixed before measurement and use past data only.

### A. Funding extreme

At each settled funding timestamp, compute its causal empirical percentile from the preceding 90 calendar days of settled ADAUSDT funding observations, excluding the current observation.

- `FUNDING_LOW`: percentile `<= 0.05`;
- `FUNDING_HIGH`: percentile `>= 0.95`.

Require at least 90 prior funding observations; otherwise mark `INSUFFICIENT_HISTORY`.

### B. OI shock

For each closed 15m OI observation compute `delta_log_oi = log(OI_t / OI_{t-1})`. Using only the preceding 30 calendar days, compute the causal median and MAD of `delta_log_oi`.

Use robust score `z_mad = 0.67448975 * (x - median) / MAD`.

- `OI_EXPANSION_SHOCK`: `z_mad >= 4.0`;
- `OI_CONTRACTION_SHOCK`: `z_mad <= -4.0`.

Require at least 1,000 prior valid 15m changes and positive MAD; otherwise mark the reason explicitly.

### C. Joint event

A `JOINT_EVENT` occurs when a funding extreme has an OI shock at the same timestamp or within the preceding 60 minutes. This is backward-looking only. Preserve the funding side and OI shock side as separate fields; do not invent directional equivalence.

## Frozen episode construction

Construct episodes independently within each event family and side:

1. sort events by timestamp;
2. merge events separated by less than 8 hours into one episode;
3. opposite funding sides and opposite OI shock sides never merge;
4. episode start is the first event timestamp and episode end is eight hours after the last member event;
5. representative event is earliest timestamp, then deterministic event id.

Also create a strict sensitivity view using a 24-hour merge distance. Do not choose between 8h and 24h from downstream measurements.

## OHLC state description

Use the exact validated Bybit ADAUSDT 15m archive from EXP-023 and derive complete UTC 1H bars as in EXP-024. At each independently selected representative event timestamp, describe only information closed by that timestamp:

- 15m and 1H ATR-normalised displacement and range over frozen windows 4, 8 and 32 parent bars;
- efficiency, close location and direction-aware slopes;
- the five frozen parent representations from EXP-024 (`FIXED_8`, `DIRECTION_RUN`, `ATR_ORIGIN`, `CONFIRMED_DIRECTION_CHANGE`, `HYBRID_ORIGIN`) evaluated at the event timestamp, not used for event selection;
- representation validity, age, origin disagreement, cap/history reasons and normalised geometry;
- whether an EXP-024 or EXP-025 detection/episode is already active, as an overlap annotation only.

No future bars, future pivots, future returns or outcome labels are allowed.

## Controls and analysis

Create deterministic matched controls from timestamps with no funding extreme or OI shock in the surrounding 24 hours. Match exactly on:

- calendar month;
- UTC hour bucket;
- chronological third;
- available-history status.

Controls must be source-excluded and non-overlapping with event episodes. Use equal support and deterministic hashing for tie-breaking.

Report:

- raw event and independent episode support by family, side, month and chronological third;
- 8h versus 24h compression and concentration;
- funding/OI joint-event support;
- representation validity, age variability and origin disagreement at independently sampled event times;
- event-versus-control distribution distances and rank relationships for frozen OHLC geometry;
- factor-free direction/time stability because event thresholds are fixed;
- overlap with EXP-024 detections and EXP-025 episodes, clearly separated from independent support;
- sensitivity to the 8h/24h episode rule;
- counterexamples where an independent derivatives event has no distinctive OHLC state, or apparent distinction is caused by time concentration/history selection.

No representation, event family or episode rule may be selected because it gives the largest contrast.

## Decision

Select exactly one verdict:

- `DERIVATIVES_EVENT_STRUCTURE_SUPPORTED` — at least one independently sampled event family has non-concentrated episode support, stable event-versus-control structural distinction across time thirds, and non-degenerate valid representation geometry under both 8h and 24h episode views;
- `DERIVATIVES_EVENT_STRUCTURE_PARTIAL` — independent events are measurable and some structural distinction exists, but support, concentration, history, representation validity or episode sensitivity limits transfer;
- `DERIVATIVES_EVENT_STRUCTURE_REJECTED` — independent event episodes show no stable structural distinction from controls or any distinction collapses under episode/time/history checks;
- `DERIVATIVES_EVENT_DATA_FAILED` — official funding or OI histories cannot support an honest test.

Do not force a positive verdict.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/REPORT.md`
- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/data_provenance.csv`
- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/events.csv`
- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/episodes.csv`
- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/event_state.csv`
- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/matched_controls.csv`
- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/robustness_summary.csv`
- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/counterexamples.csv`
- `experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/experiment_026.py`

Do not commit raw market archives or modify any other repository path. Do not create `__pycache__` or `.pyc` files.

## Validation

Before PASS:

1. Validate official endpoint identity, pagination and response schema.
2. Verify all funding/OI observations are closed, UTC-aligned, unique, ordered and numeric.
3. Reproduce source hashes and all gap/coverage metrics.
4. Assert every percentile, median and MAD window excludes the current and future observations.
5. Assert event grouping uses only event family/side/timestamps and never OHLC geometry.
6. Assert OHLC state inputs end no later than the event timestamp.
7. Verify 8h and 24h episode views preserve all raw event ids exactly once.
8. Verify matched controls are source-excluded, non-overlapping and deterministic.
9. Preserve insufficient-history and zero-MAD cases explicitly.
10. Run twice and verify identical SHA-256 hashes for all nine committed outputs without redownloading validated raw archives.
11. Parse all CSVs and reproduce REPORT values and verdict.
12. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-026_ADA_DERIVATIVES_EVENT_EPISODES/experiment_026.py`, remove cache artifacts, run `git diff --check`, and perform baseline-relative allowlist validation.
13. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 or EXP-013 through EXP-025 file, committed source datasets, or paths outside the nine EXP-026 outputs.

The only permitted non-repository writes are deterministic raw funding/OI archive files and temporary files under `${HOME}/.local/share/msm-market-data/bybit/linear/ADAUSDT/`. Existing dirty files must remain byte-identical, unstaged and uncommitted.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-026 outputs unstaged. Raw market data remain outside the repository. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.