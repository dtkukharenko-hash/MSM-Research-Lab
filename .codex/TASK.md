# Current Codex Task

- task_id: `EXP-027-MULTI-MARKET-DERIVATIVES-TRANSFER`
- status: `READY`
- published_at: `2026-07-19`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-026-ADA-DERIVATIVES-EVENT-EPISODES`
- commit_message: `EXP-027 multi-market derivatives transfer`

## Objective

Test whether the fully frozen EXP-026 derivatives-event protocol transfers from ADAUSDT to independent linear perpetual markets without changing thresholds, history windows, episode rules, controls, OHLC windows or parent representations.

This is a strict external-transfer experiment. Do not tune per symbol, choose favourable markets, optimise contrasts, or redefine events after observing results. It is descriptive causal research, not a trading-rule or outcome study.

## Frozen market panel and period

Use exactly these Bybit linear perpetual symbols:

- `BTCUSDT`
- `ETHUSDT`
- `SOLUSDT`
- `XRPUSDT`

Use the exact common target range `2023-07-01T00:00:00Z` through `2024-12-31T23:00:00Z`. A symbol may have an unavailable prefix or suffix, but observations must never be fabricated, interpolated or forward-filled. Preserve all availability limitations explicitly.

## Authorised data

Use official Bybit V5 public endpoints only:

- funding history: `GET https://api.bybit.com/v5/market/funding/history`;
- open interest: `GET https://api.bybit.com/v5/market/open-interest`, `intervalTime=15min`;
- instrument metadata: `GET https://api.bybit.com/v5/market/instruments-info` only to verify contract and funding interval;
- kline: `GET https://api.bybit.com/v5/market/kline`, `interval=15`, only when no already validated exact-symbol local archive exists.

Store raw archives outside GitHub under `${HOME}/.local/share/msm-market-data/bybit/linear/<SYMBOL>/` using deterministic schemas and atomic writes. Reuse validated archives when hashes and provenance pass. Record endpoint, parameters, retrieval time, pagination, retries, hashes, schema, coverage, gaps, duplicates, ordering, numeric validity and unavailable prefixes/suffixes.

## Frozen EXP-026 event definitions

Apply unchanged, independently for each symbol.

### Funding extremes

At each settled funding timestamp, calculate the causal empirical percentile from settled observations in the preceding 90 calendar days, excluding the current observation.

- `FUNDING_LOW`: percentile `<= 0.05`;
- `FUNDING_HIGH`: percentile `>= 0.95`;
- require at least 90 prior funding observations.

### OI shocks

For each closed 15m OI observation calculate `delta_log_oi = log(OI_t / OI_{t-1})`. From only the preceding 30 calendar days calculate causal median and MAD.

`z_mad = 0.67448975 * (x - median) / MAD`

- `OI_EXPANSION_SHOCK`: `z_mad >= 4.0`;
- `OI_CONTRACTION_SHOCK`: `z_mad <= -4.0`;
- require at least 1,000 prior valid changes and positive MAD.

### Joint events

A `JOINT_EVENT` is a funding extreme with an OI shock at the same timestamp or within the preceding 60 minutes. Preserve funding side and OI side separately.

## Frozen episode construction

Within each symbol, event family and side:

1. sort by timestamp;
2. produce both 8-hour and 24-hour merge views;
3. opposite funding sides and opposite OI sides never merge;
4. episode start is first event; episode end is merge distance after last member;
5. representative is earliest timestamp, then deterministic event id.

Do not select between merge views from measured contrasts.

## Frozen OHLC state description

Use complete closed native 15m bars and deterministic complete UTC 1H bars. At each independently selected representative timestamp calculate exactly the EXP-026 state fields:

- ATR-normalised displacement and range for frozen 4, 8 and 32 parent-bar windows on 15m and 1H;
- efficiency, close location and direction-aware slopes;
- five frozen EXP-024 representations: `FIXED_8`, `DIRECTION_RUN`, `ATR_ORIGIN`, `CONFIRMED_DIRECTION_CHANGE`, `HYBRID_ORIGIN`;
- validity, age, origin disagreement, cap/history reasons and normalised geometry.

OHLC may describe already selected events only. It may not create, remove, merge, rank or weight events. No future bars, pivots, returns or outcome labels.

## Frozen controls

For every symbol and event family create deterministic matched controls with no funding extreme or OI shock in the surrounding 24 hours. Match exactly on:

- symbol;
- calendar month;
- UTC hour;
- chronological third within that symbol's available range;
- available-history status.

Controls must be source-excluded, outside all event episodes, equal-support where possible, and selected by deterministic SHA-256 tie-breaking. Preserve unmatched strata explicitly.

## Transfer analysis

Report without selecting a winner:

- raw events and 8H/24H episode support by symbol, family, side, month and chronological third;
- support concentration and compression by symbol;
- event-versus-control distribution distances and rank relationships for every frozen state field and representation;
- representation validity, age variability and origin disagreement;
- sign consistency and rank consistency of event-control contrasts across the four symbols;
- leave-one-symbol-out stability;
- pooled results only after symbol-level results, using equal-symbol weighting rather than event-count weighting;
- sensitivity to 8H versus 24H episodes;
- counterexamples where a contrast is driven by one symbol, one time third, history availability or invalid representation support.

No symbol, event family, representation, field or episode view may be selected because it gives the largest result.

## Frozen transfer criteria

For each event-family/side/representation/field cell, call a structural distinction transferable only when all are true:

1. at least three of four symbols have sufficient matched support;
2. at least three symbols have the same contrast sign;
3. no single symbol contributes more than 50% of the equal-symbol pooled absolute contrast;
4. the sign survives every feasible leave-one-symbol-out calculation;
5. the sign is the same in both 8H and 24H views;
6. validity and history exclusions do not remove more than 50% of independent episodes in the supporting symbols.

These criteria are frozen and must not be relaxed.

## Decision

Select exactly one verdict:

- `MULTI_MARKET_DERIVATIVES_TRANSFER_SUPPORTED` — at least one predeclared event-family/side structural distinction satisfies every frozen transfer criterion, with non-concentrated support and no contradictory broad result;
- `MULTI_MARKET_DERIVATIVES_TRANSFER_PARTIAL` — independent events transfer operationally and some cross-symbol consistency exists, but no distinction fully satisfies all criteria or material support/history/episode sensitivity remains;
- `MULTI_MARKET_DERIVATIVES_TRANSFER_REJECTED` — distinctions are symbol-specific, unstable, contradictory or collapse under frozen controls and leave-one-symbol-out checks;
- `MULTI_MARKET_DERIVATIVES_DATA_FAILED` — official histories cannot support an honest common-panel test.

Do not force a positive verdict.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/REPORT.md`
- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/data_provenance.csv`
- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/events.csv`
- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/episodes.csv`
- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/event_state.csv`
- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/matched_controls.csv`
- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/transfer_summary.csv`
- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/counterexamples.csv`
- `experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`

Do not commit raw market archives or create cache files.

## Validation

Before PASS:

1. Verify exact symbol panel, endpoint identity, parameters, pagination and schemas.
2. Verify all observations are closed, UTC-aligned, ordered, unique and numeric.
3. Reproduce hashes, coverage, gaps and unavailable intervals.
4. Assert all rolling calculations exclude current and future observations.
5. Assert event membership and grouping never use OHLC.
6. Assert OHLC inputs end no later than event timestamp.
7. Verify every raw event id belongs exactly once to each applicable 8H and 24H view.
8. Verify controls are symbol-matched, source-excluded, non-overlapping and deterministic.
9. Preserve insufficient-history, zero-MAD, missing-bar and unmatched-control cases explicitly.
10. Verify transfer criteria directly from output rows, including leave-one-symbol-out and equal-symbol weighting.
11. Run twice without redownloading validated archives and require identical SHA-256 hashes for all nine outputs.
12. Parse every CSV and reproduce REPORT values and verdict.
13. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py`, remove cache artifacts, run `git diff --check`, and perform baseline-relative allowlist validation.
14. Verify all protected and pre-existing dirty files remain byte-identical and unstaged.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 file, or any EXP-013 through EXP-026 file. The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Only the nine EXP-027 outputs may change inside the repository. The only permitted non-repository writes are deterministic raw archives and temporary files under `${HOME}/.local/share/msm-market-data/bybit/linear/<SYMBOL>/`.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-027 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.