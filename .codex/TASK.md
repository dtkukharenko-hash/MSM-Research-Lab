# Current Codex Task

- task_id: `EXP-032R2-ADA-ONLY-TEMPORAL-STRUCTURE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- allow_user_decision: `false`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-032R2 ADA-only temporal structure validation`

## Why this is R2

EXP-032 and EXP-032R1 stopped at attempt 0 before scientific work because the previous orchestrator ignored the task-level prohibition on user-decision blocking. Their terminal reporter also attached an unrelated EXP-031R4 report. They produced no accepted scientific result.

R2 starts in a fresh output directory after three infrastructure corrections:

1. orchestrator normalizes forbidden `USER_DECISION_REQUIRED` to `TECHNICAL_CORRECTION_REQUIRED`;
2. launch verifies installed runtime files byte-for-byte against the repository before starting roles;
3. reporter may inspect only the current task's allowlisted artifacts.

Do not use any EXP-032 or EXP-032R1 worktree output as code, evidence, parameters, metrics, or scientific support.

## Decision boundary

`allow_user_decision` is `false`.

No role may return `USER_DECISION_REQUIRED`. Missing data, unavailable helpers, ambiguity, contradictory evidence, insufficient samples, implementation defects, or inability to meet the contract are technical outcomes: `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

## Objective

Determine whether ADAUSDT has a stable causal temporal structure describing the beginning, development, age, correction, and termination of its own movements through time.

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

BTC, ETH, SOL, XRP, and every other instrument are prohibited in:

- feature construction;
- calibration;
- reference labels;
- null models;
- regimes;
- acceptance criteria;
- robustness claims;
- scientific conclusions.

Do not substitute another instrument for missing ADA coverage. Missing ADA coverage is a technical/data failure. Funding and open interest are not primary features in this experiment.

## Temporal partition

Use UTC boundaries exactly:

- development/calibration: `2023-01-01T00:00:00Z` through `2024-12-31T23:59:59Z`;
- independent validation: `2025-01-01T00:00:00Z` through `2025-12-31T23:59:59Z`;
- protected holdout: every timestamp on or after `2026-01-01T00:00:00Z`.

The 2026 holdout must not be opened, scanned, counted, summarized, hashed, or used in any way.

All definitions, quantile positions, windows, confirmation counts, null procedures, and thresholds must be frozen before calculating any 2025 validation metric. No parameter may change after inspecting 2025.

## Scientific language boundary

This is a market-language experiment, not a strategy experiment.

Do not calculate or discuss entries, exits, positions, long/short, PnL, profit factor, returns, equity, drawdown, leverage, liquidation, fees, risk, portfolio construction, execution rules, trade count, or win rate.

Permitted terms include movement, direction, phase, start, age, progress, density, correction, termination, displacement, efficiency, hierarchy, stability, and temporal transfer on ADA itself.

## Causal requirements

Every emitted value must be available at the close of its timestamped bar.

Mandatory rules:

1. closed bars only;
2. no centered windows;
3. no future extrema in state construction;
4. no backward revision of emitted states;
5. no interpolation, synthetic bars, gap filling, or replacement data;
6. unavailable input produces `UNKNOWN`;
7. 1D context at a 4H timestamp uses only the most recently closed daily bar;
8. 1H child states are computed independently from closed 1H bars and joined causally to 4H;
9. future-aware segmentation is permitted only as isolated `REFERENCE_ONLY` evaluation labels;
10. reference-only values may never enter features, calibration after the development split, or emitted states.

## Required state language

Direction is one of `-1`, `0`, `+1`, `UNKNOWN`.

Phase is exactly one of:

- `DENSITY` — overlapping, low-efficiency movement without stable direction;
- `EMERGING` — first confirmed causal appearance of directional movement;
- `DEVELOPING` — directional movement remains structurally active;
- `CORRECTION` — counter-displacement inside an active parent direction;
- `TERMINATING` — causal weakening or opposing structure consistent with parent termination;
- `UNKNOWN` — insufficient or invalid causal history.

Age is the number of completed 4H bars since the most recent same-direction `EMERGING`. Reset age only when the parent terminates, becomes `UNKNOWN`, or a confirmed opposite `EMERGING` begins.

Use price-derived quantities only. At minimum document and calculate:

- EMA27 slope normalized by ATR;
- signed displacement over frozen backward windows;
- directional efficiency ratio;
- candle/range overlap density;
- retracement from a causal running extreme;
- trailing volatility percentile using only preceding closed bars;
- persistence and two-bar confirmation.

## Frozen calibration space

Use one deterministic rule specification, not a best-cell search.

Quantile positions may be estimated only on 2023–2024 and are limited to `0.30`, `0.50`, `0.70`.

Permitted windows:

- 4H: 3, 6, 12, 24 bars;
- 1H: 6, 12, 24, 48 bars;
- volatility percentile: preceding 96 closed bars;
- confirmation: 2 consecutive closed bars.

When more than one development-only specification is evaluated, select by the most stable quarterly development behaviour, never by the largest single metric. Record every candidate and the deterministic selection rule in `PROTOCOL.md` and `state_definition.csv`.

## Reference-only segmentation

Construct one frozen ex-post 4H ADA movement population solely for evaluation. Prefer an already committed MSM helper used for causal-versus-reference analysis.

For each reference movement provide:

- direction;
- start timestamp;
- end timestamp;
- duration in 4H bars;
- normalized displacement;
- normalized progress for every included 4H bar.

Do not tune reference segmentation on 2025.

## Primary measurements

Report development and validation separately. Never pool them for acceptance.

### Start correspondence

For every causal `EMERGING`, match a same-direction reference start within `±3` 4H bars. Report event count, matched count, precision, reference-start recall, lead/lag distribution, and lift over a same-count quarterly circular-shift null.

### Age ordering

Within matched reference movements, compare causal age with normalized reference progress. Report Spearman correlation, median progress by causal-age quartile, ordering violations, direction splits, and half-year splits.

### Correction distinction

Inside active same-direction reference movements, compare `CORRECTION` with `DEVELOPING` using signed normalized displacement over the next 1 and 3 closed 4H bars as evaluation outcomes only. Report distributions, median differences, Cliff's delta, and development/validation sign agreement.

### Termination correspondence

For every causal `TERMINATING`, match a reference end within `±3` 4H bars. Report event count, matched count, precision, reference-end recall, lead/lag distribution, and circular-shift lift.

### Parent-child hierarchy

Compute 1H child states independently and join them causally. Compare child direction/phase composition across 4H parent phases against a duration-preserving within-quarter shuffled null. Report hierarchy lift, child-count distributions, and the fraction of parent movements containing at least one aligned child-development sequence.

### ADA-internal stability

Use only ADA-derived regimes:

- 1D ADA direction: down, neutral, up;
- 4H trailing volatility: low/high using the frozen development median;
- quarter and half-year.

No BTC-defined or other-asset regime is permitted.

## Null models

Use deterministic seeds and at least:

1. same-count quarterly circular shifts of causal event timestamps;
2. duration-preserving phase-block shuffles within quarters;
3. naive EMA27-slope-only causal baseline with the same two-bar confirmation.

## Data and implementation gate

Before any scientific verdict, require:

- exact ADA-only identity;
- exact temporal split;
- proof of no 2026 access;
- complete causal joins and explicit `UNKNOWN` handling;
- no future leakage;
- deterministic rerun hashes;
- no non-ADA data use;
- all outputs reopen successfully;
- no unresolved implementation test failure;
- peak RSS below `1,048,576 KiB`;
- every output below 95 MiB.

Failure of this gate yields `DATA_FAILED`, not a user decision.

## Frozen 2025 criteria

1. start precision `>=0.50` and circular-shift lift `>=1.35`;
2. reference-start recall `>=0.40`;
3. age/progress Spearman `>=0.35`, same sign as development, and nondecreasing age-quartile median progress;
4. correction-versus-development absolute Cliff's delta `>=0.25` with expected counter-displacement sign at both 1-bar and 3-bar horizons;
5. termination precision `>=0.45` and circular-shift lift `>=1.35`;
6. parent-child hierarchy lift `>=1.35`.

Stability requirements:

- no primary relationship reverses sign between development and validation;
- at least four of six criteria pass separately in both halves of 2025 when sample size is adequate;
- no 2025 quarter contains more than 45% of matched start or termination events;
- subgroup sample below 10 is `INSUFFICIENT_SAMPLE`, never PASS.

Scientific verdict:

- `ACCEPT`: at least five of six criteria pass, no sign reversal, all stability requirements pass;
- `PARTIAL`: three or four criteria pass without sign reversal, or five pass with one stability failure;
- `REJECT`: two or fewer criteria pass, a central relationship reverses, or one ADA regime dominates the result;
- `DATA_FAILED`: data, causal integrity, determinism, or implementation gate fails.

The verdict is structural, not a trading conclusion.

## Required outputs

Create exactly the 19 paths in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-032R2_ADA_ONLY_TEMPORAL_STRUCTURE/`

Required files:

- `REPORT.md` with one explicit verdict line `Verdict: ACCEPT|PARTIAL|REJECT|DATA_FAILED`;
- `PROTOCOL.md` with frozen definitions and boundaries;
- `experiment_032r2.py`;
- complete causal 4H and 1H state tables;
- reference-only movement table;
- temporal coverage and protected-holdout proof;
- frozen state definitions;
- start, age, correction, termination, hierarchy, regime, and null metrics;
- deterministic counterexamples;
- two-run hashes;
- implementation audit;
- test results.

## Implementation contract

The script must support:

- `--self-test --temp-dir PATH`;
- `--run --output-dir PATH --temp-dir PATH`.

Run the complete experiment twice into separate clean external temporary directories and prove byte-identical substantive outputs. Deterministic gzip files must use a fixed filename header and `mtime=0`.

Use streaming, chunking, or disk-backed temporary storage outside the repository. Do not create repository-local SQLite, journal, cache, bytecode, shard, temporary, partial, or log files.

## Immutable repository state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including EXP-032 and EXP-032R1 failed evidence.

The protected Pine must remain dirty, unstaged, and byte-identical:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Preserve tracked cache/bytecode paths. Do not modify `.codex/RESULT.md`. No task-created path may exist outside the allowlist.

## Role contract

Planner verifies ADA 2023–2025 availability, protected 2026 non-access, committed helpers, exact runtime identity, and technical actionability. Missing requirements are technical outcomes.

Implementer performs the complete ADA-only experiment, creates all outputs, never reads another market or 2026, and leaves changes unstaged.

Auditor independently verifies data identity, boundaries, causal alignment, frozen parameters, reference isolation, outputs, deterministic hashes, metrics, mechanical verdict, allowlist, and immutable paths.

Corrector fixes only technical defects inside the allowlist. It may not alter the market boundary, temporal split, features, windows, thresholds, metrics, or decision rule.

On final auditor `PASS`, the orchestrator may stage, commit, and push exactly the 19 allowlisted EXP-032R2 files.
