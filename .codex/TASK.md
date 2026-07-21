# Current Codex Task

- task_id: `EXP-032R1-ADA-ONLY-TEMPORAL-STRUCTURE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- allow_user_decision: `false`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-032R1 ADA-only temporal structure validation`

## Why this is R1

EXP-032 stopped at attempt 0 before scientific work because an older installed runtime allowed a false `USER_DECISION_REQUIRED` result. Its terminal report also displayed an unrelated EXP-031R4 report. EXP-032 produced no accepted scientific result.

R1 repeats the frozen ADA-only research question in a fresh output directory after runtime correction. It must not reuse any partial EXP-032 worktree output as evidence or implementation source.

`USER_DECISION_REQUIRED` is forbidden. Missing data, ambiguity, unavailable helpers, implementation defects, or insufficient evidence are technical outcomes: `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

## Objective

Determine whether ADAUSDT has a stable causal temporal structure describing the beginning, development, age, correction, and termination of its own movements across time.

The sole scientific question is:

> Can one frozen causal state language, calibrated only on ADAUSDT during 2023–2024, retain the same structural meaning on independent ADAUSDT data from calendar 2025?

## Market boundary

Use only:

- exchange: Bybit;
- instrument: ADAUSDT linear perpetual;
- primary data: OHLCV;
- primary scale: 4H;
- global ADA context: 1D closed bars;
- local ADA child scale: 1H closed bars.

BTC, ETH, and every other instrument are prohibited in feature construction, calibration, reference labels, null models, acceptance criteria, regimes, robustness claims, and scientific conclusions.

Do not substitute another instrument when ADA data are missing. Missing ADA coverage is a technical/data failure.

Funding and open interest are not primary features in this experiment.

## Temporal split

Use exact UTC boundaries:

- development/calibration: `2023-01-01T00:00:00Z` through `2024-12-31T23:59:59Z`;
- independent validation: `2025-01-01T00:00:00Z` through `2025-12-31T23:59:59Z`;
- protected holdout: every timestamp on or after `2026-01-01T00:00:00Z`.

The 2026 holdout must not be opened, read, counted, summarized, hashed, or inspected.

Freeze all definitions, quantile positions, windows, confirmation counts, reference segmentation, null procedures, and decision thresholds before calculating any 2025 validation metric. No parameter may change after inspecting 2025.

## Scientific language boundary

This is a market-language experiment, not a strategy experiment.

Do not calculate or discuss entries, exits, long/short positions, PnL, profit factor, returns, equity, drawdown, leverage, liquidation, fees, risk, execution, trade count, or win rate.

Permitted concepts are movement, direction, phase, start, age, progress, density, correction, termination, displacement, efficiency, hierarchy, stability, and temporal validation on ADA itself.

## Causal rules

Every emitted value must be available at the close of its timestamped bar:

1. closed bars only;
2. no centered windows;
3. no future extrema in model features;
4. no backward revision of emitted states;
5. no interpolation, synthetic bars, gap filling, or replacement data;
6. unavailable input produces `UNKNOWN`;
7. 1D context uses only the most recently closed daily bar;
8. 1H child states are computed independently and joined causally to 4H timestamps;
9. future-aware segmentation may exist only as isolated `REFERENCE_ONLY` evaluation labels.

## Required state language

Direction is one of `-1`, `0`, `+1`, `UNKNOWN`.

Phase is exactly one of:

- `DENSITY`;
- `EMERGING`;
- `DEVELOPING`;
- `CORRECTION`;
- `TERMINATING`;
- `UNKNOWN`.

Age is the number of completed 4H bars since the most recent `EMERGING` state in the current direction. It resets only when the parent terminates, becomes unknown, or an opposite confirmed `EMERGING` begins.

Use price-derived causal quantities including:

- EMA27 slope normalized by ATR;
- signed displacement over backward windows;
- directional efficiency ratio;
- candle/range overlap density;
- retracement from a causal running extreme;
- trailing volatility percentile from preceding closed bars;
- persistence/confirmation counts.

## Frozen parameter boundary

Use one deterministic rule specification, not a best-cell search.

Allowed development-only quantile positions: `0.30`, `0.50`, `0.70`.

Allowed backward windows:

- 4H: 3, 6, 12, 24 bars;
- 1H: 6, 12, 24, 48 bars;
- volatility percentile: preceding 96 closed bars;
- state confirmation: 2 consecutive closed bars.

When multiple development-only specifications are evaluated, choose by stability across development quarters, not the largest metric. Record every candidate and deterministic selection rule.

## Reference-only population

Construct one frozen ex-post 4H reference movement population solely for evaluation. It may use future information but must never enter feature construction or calibration.

For each reference movement record direction, start, end, duration, normalized displacement, and normalized progress for included bars. Do not tune the reference on 2025.

## Measurements

Report development and validation separately.

### Start correspondence

For each causal `EMERGING`, match a same-direction reference start within `±3` 4H bars. Report count, precision, reference recall, lead/lag distribution, and lift over a same-count quarterly circular-shift null.

### Age ordering

Within matched movements compare causal age with reference normalized progress. Report Spearman correlation, median progress by age quartile, ordering violations, direction, and half-year slices.

### Correction distinction

Within active same-direction reference movements compare `CORRECTION` and `DEVELOPING`. Use signed normalized displacement over the next 1 and 3 closed 4H bars only as evaluation outcomes. Report distributions, median differences, Cliff's delta, and development/validation sign agreement.

### Termination correspondence

For each causal `TERMINATING`, match a reference end within `±3` 4H bars. Report count, precision, reference recall, lead/lag distribution, and circular-shift lift.

### Parent-child hierarchy

Compute 1H child states independently. Measure child composition across 4H parent phases against a duration-preserving within-quarter shuffled null. Report hierarchy lift, child counts, and fraction of parent movements containing an aligned child development sequence.

### ADA-internal stability

Use only ADA-derived regimes:

- 1D direction: down, neutral, up;
- 4H trailing volatility: low/high by frozen development median;
- quarter and half-year.

No BTC-defined regime is allowed.

## Null models

Use deterministic seeds and at least:

1. same-count quarterly circular shifts of event timestamps;
2. duration-preserving phase-block shuffles within quarters;
3. naive EMA27-slope-only causal baseline with the same two-bar confirmation.

## 2025 acceptance criteria

The implementation/data gate must pass first: exact ADA identity and split, no 2026 access, causal joins, explicit UNKNOWN, no leakage, deterministic reruns, no non-ADA data, reopenable outputs, and no unresolved implementation failure.

Primary criteria:

1. start precision `>=0.50` and circular-shift lift `>=1.35`;
2. reference-start recall `>=0.40`;
3. age/progress Spearman `>=0.35`, same sign as development, nondecreasing median progress across age quartiles;
4. correction-vs-development absolute Cliff's delta `>=0.25` with expected counter-displacement sign at both 1- and 3-bar horizons;
5. termination precision `>=0.45` and circular-shift lift `>=1.35`;
6. parent-child hierarchy lift `>=1.35`.

Stability requirements:

- no primary relationship reverses sign between development and validation;
- at least four of six criteria pass separately in both halves of 2025 where sample size is adequate;
- no 2025 quarter contains more than 45% of matched start or termination events;
- subgroup count below 10 is `INSUFFICIENT_SAMPLE`, never PASS.

Verdict:

- `ACCEPT`: at least five of six pass, no sign reversal, all stability requirements pass;
- `PARTIAL`: three or four pass without sign reversal, or five pass with one stability failure;
- `REJECT`: two or fewer pass, a central sign reverses, or one ADA regime dominates;
- `DATA_FAILED`: required coverage, causal integrity, or deterministic implementation cannot be established.

## Required outputs

Create exactly the 19 paths in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-032R1_ADA_ONLY_TEMPORAL_STRUCTURE/`

The package must include:

- `REPORT.md` with one explicit verdict;
- `PROTOCOL.md` with frozen definitions and criteria;
- `experiment_032r1.py`;
- complete compressed 4H states, 1H child states, and reference movements;
- split summary and state definition;
- start, age, correction, termination, hierarchy, regime, and null metrics;
- deterministic counterexamples;
- two-run hashes;
- implementation audit and tests.

The script must support:

- `--self-test --temp-dir PATH`;
- `--run --output-dir PATH --temp-dir PATH`.

Run the complete experiment twice in separate clean external temporary directories and prove byte-identical substantive outputs. Deterministic gzip uses a fixed filename header and `mtime=0`.

Peak RSS must remain below `1,048,576 KiB`. Every output must reopen and remain below 95 MiB. No repository-local cache, bytecode, SQLite, journal, temporary, partial, shard, or log file may be created.

## Immutable state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including all EXP-032 failed-attempt paths.

Protected Pine:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Preserve tracked bytecode/cache paths. Do not modify `.codex/RESULT.md`. No task-created path may exist outside the allowlist.

## Role contract

Planner verifies ADA 2023–2025 availability, confirms 2026 remains unopened, and identifies committed helpers. Return PASS when technically actionable. Data or implementation defects are technical, never user decisions.

Implementer builds and runs the complete ADA-only experiment, never loads another market, never opens 2026, creates every output, and leaves changes unstaged.

Auditor independently checks instrument identity, temporal boundaries, causal alignment, frozen parameters, reference isolation, outputs, hashes, metrics, verdict, allowlist, and immutable state. PASS only when the verdict follows mechanically from the frozen criteria.

Corrector fixes only technical defects inside the allowlist. It may not change the research question, market boundary, split, metrics, thresholds, or decision rule.

On final auditor PASS, the orchestrator may stage, commit, and push exactly the allowlisted EXP-032R1 paths.
