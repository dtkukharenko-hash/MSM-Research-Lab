# Current Codex Task

- task_id: `EXP-033-ADA-ONLY-TEMPORAL-STRUCTURE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-002_ADAUSDT_2023_2025/REPORT.md`
- data_manifest_sha256: `8381b91af7af7f94890ad60c9fe954459540ebbd1bc9824d94aaf1b7f73075a4`
- commit_message: `EXP-033 ADA-only temporal structure validation`

## Purpose

Run the first substantive ADA-only temporal validation after DATA-002 established complete official Bybit ADAUSDT history for 2023–2025.

The question is:

> Can one frozen causal language, developed only on ADAUSDT during 2023–2024, retain the same structural meaning on independent ADAUSDT data from calendar 2025?

This is a market-language study, not a strategy study.

## Mandatory data source

Use only the persistent canonical DATA-002 files below the directory supplied by `MSM_MARKET_DATA_ROOT`:

- `bybit/linear/ADAUSDT/ADAUSDT_1h_2023_2025.csv`;
- `bybit/linear/ADAUSDT/ADAUSDT_4h_2023_2025.csv`;
- `bybit/linear/ADAUSDT/ADAUSDT_1d_2023_2025.csv`.

The 15m DATA-002 file may be opened only for independent reconciliation of an aggregate value. It must not become a model scale or an additional optimization source.

Before analysis:

1. verify `DATA_READY=YES` in the committed DATA-002 report;
2. verify the report SHA-256 against task metadata;
3. verify all required persistent files and metadata against `readiness_manifest.csv`;
4. require exact counts: 1H `26304`, 4H `6576`, 1D `1096`;
5. require exact interval `2023-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z`;
6. reject any gap, duplicate, off-grid row, invalid numeric value, identity mismatch, or hash mismatch.

Do not use BTC, ETH, SOL, XRP, another symbol, funding, open interest, trades, order books, or a third-party dataset. Do not substitute another market if ADA data cannot be verified.

## Temporal boundary

Use UTC boundaries exactly:

- development and calibration: `2023-01-01T00:00:00Z <= timestamp < 2025-01-01T00:00:00Z`;
- independent validation: `2025-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z`;
- protected future: every timestamp on or after `2026-01-01T00:00:00Z`.

No file, request, row, statistic, count, diagnostic, parameter, or helper may access the protected future.

All feature definitions, quantile positions, candidate-selection rules, confirmation counts, reference rules, null procedures, matching windows, and acceptance thresholds must be frozen before any 2025 scientific metric is calculated. No parameter may be changed after inspecting a 2025 result.

## Scales and causal alignment

- 1D: global ADA context, using only the most recently closed daily bar available at each 4H timestamp;
- 4H: primary movement scale;
- 1H: independently computed local child scale, joined to 4H only after the relevant 1H bar has closed.

Every emitted model-side value must be available at the close of its timestamped bar.

Mandatory causal rules:

1. closed bars only;
2. no centered windows;
3. no future extrema in model features;
4. no backward revision of an emitted state;
5. no interpolation, synthetic bars, gap filling, or replacement data;
6. unavailable history produces `UNKNOWN`;
7. reference-only future information never enters features, calibration, state transitions, or candidate selection.

## State language

Direction is separate and must be one of `-1`, `0`, `+1`, `UNKNOWN`.

Phase must be exactly one of:

- `DENSITY`: overlapping low-efficiency movement without stable direction;
- `EMERGING`: first confirmed causal appearance of a directional movement;
- `DEVELOPING`: the directional parent remains structurally active;
- `CORRECTION`: counter-displacement inside the still-active parent direction;
- `TERMINATING`: causal weakening or opposing structure consistent with ending the parent;
- `UNKNOWN`: insufficient or invalid causal history.

Age is the number of completed 4H bars since the latest `EMERGING` state in the current parent direction. It resets only on confirmed opposite `EMERGING`, termination followed by loss of the parent, or `UNKNOWN`.

## Required price-derived quantities

Compute and document at minimum, separately for 4H and where applicable 1H:

- EMA27 slope normalized by ATR14;
- signed close displacement over backward windows;
- directional efficiency ratio;
- consecutive-range overlap density;
- retracement from a causal running extreme established since the current parent began;
- ATR-to-close trailing volatility percentile using only the preceding 96 closed bars;
- two-consecutive-bar confirmation.

Permitted backward windows are frozen to:

- 4H: `3`, `6`, `12`, `24` bars;
- 1H: `6`, `12`, `24`, `48` bars;
- volatility percentile: preceding `96` closed bars;
- confirmation: exactly `2` consecutive closed bars.

Quantile positions are limited to `0.30`, `0.50`, and `0.70`, estimated only from the 2023–2024 development population.

Do not perform unrestricted parameter search. When more than one permitted development-only specification is evaluated, select deterministically by this order:

1. no quarterly sign reversal in the primary development relationships;
2. largest number of development quarters meeting the same directional ordering;
3. smallest dispersion of quarterly normalized metrics;
4. simplest specification by number of active conditions;
5. lexical parameter order as final tie-break.

Record every evaluated candidate and the selection calculation in `state_definition.csv`. The selected specification must be frozen before 2025 metrics are generated.

## Reference-only movement population

Construct one frozen ex-post 4H reference population only for evaluation. Prefer an already committed MSM helper previously used for causal-versus-reference movement comparisons. Record its repository path and blob/hash in `PROTOCOL.md` and `implementation_audit.csv`.

The reference may use future information only inside the bounded development or validation partition being labelled. It must never cross the `2024-12-31/2025-01-01` split and must never inspect 2026.

Each reference movement must provide:

- direction;
- start and end timestamps;
- duration in 4H bars;
- normalized displacement;
- normalized progress for every included 4H bar.

Freeze the reference definition using development data only. Do not tune it on 2025.

## Primary measurements

Calculate development and validation separately. Never pool them for acceptance.

### 1. Start correspondence

For each causal `EMERGING`, match a same-direction reference start within `±3` closed 4H bars. Report count, matches, precision, reference-start recall, signed lead/lag distribution, and lift over same-count quarterly circular shifts.

### 2. Age ordering

Within matched reference movements, compare causal age with reference normalized progress. Report Spearman correlation, median progress by age quartile, ordering violations, direction splits, half-year splits, and quarterly splits.

### 3. Correction distinction

Inside an active same-direction reference movement, compare `CORRECTION` with `DEVELOPING`. Use signed normalized displacement over the next `1` and `3` closed 4H bars only as evaluation outcomes. Report medians, distributions, Cliff's delta, sample counts, and development/validation sign agreement.

### 4. Termination correspondence

For each causal `TERMINATING`, match a reference end within `±3` closed 4H bars. Report count, matches, precision, reference-end recall, signed lead/lag distribution, and circular-shift lift.

### 5. Parent-child hierarchy

Build 1H states independently. Measure whether child direction/phase composition differs across 4H parent phases relative to a duration-preserving within-quarter shuffled null. Report hierarchy lift, child-count distributions, and the fraction of parent movements containing at least one aligned child development sequence.

### 6. ADA-internal stability

Use only ADA-derived partitions:

- 1D direction: down, neutral, up;
- 4H trailing volatility: low/high by the frozen development median;
- calendar quarter;
- half-year;
- parent direction.

No BTC-defined or cross-market regime is permitted.

## Null models

Use deterministic seeds and at least:

1. same-count quarterly circular shifts of causal event timestamps;
2. duration-preserving phase-block shuffles within calendar quarters;
3. a naive EMA27-slope-only causal baseline using the same two-bar confirmation.

## Scientific acceptance

The implementation gate must pass before a scientific verdict:

- exact ADAUSDT Bybit-linear identity;
- DATA-002 hashes and counts verified;
- exact temporal split;
- no protected-future access;
- complete causal joins and explicit `UNKNOWN` handling;
- no leakage from the reference population;
- no non-ADA input;
- deterministic rerun hashes;
- every output reopens successfully;
- no unresolved implementation test failure.

Primary 2025 criteria:

1. start precision at `±3` bars is at least `0.50` and circular-shift lift at least `1.35`;
2. reference-start recall is at least `0.40`;
3. age/progress Spearman is at least `0.35`, has the same sign as development, and age-quartile median progress is nondecreasing;
4. correction-versus-development absolute Cliff's delta is at least `0.25` with the expected counter-displacement sign at both 1-bar and 3-bar horizons;
5. termination precision at `±3` bars is at least `0.45` and circular-shift lift at least `1.35`;
6. parent-child hierarchy lift is at least `1.35`.

Stability requirements:

- no primary relationship reverses sign between development and validation;
- at least four of six criteria also pass separately in both halves of 2025 when sample size is adequate;
- no single 2025 quarter contains more than 45% of matched start or termination events;
- fewer than 10 relevant subgroup events is `INSUFFICIENT_SAMPLE`, never PASS.

Verdict:

- `ACCEPT`: at least five of six primary criteria pass, no sign reversal, and every stability requirement passes;
- `PARTIAL`: three or four criteria pass without sign reversal, or five pass with exactly one stability failure;
- `REJECT`: two or fewer criteria pass, any central relationship reverses sign, or the apparent result is dominated by one ADA regime;
- `DATA_FAILED`: DATA-002 identity, coverage, causality, deterministic implementation, or protected-future isolation cannot be established.

Do not interpret any verdict as a trading conclusion.

## Prohibited language and outputs

Do not calculate or discuss entries, exits, long/short positions, PnL, profit factor, return, equity, drawdown, leverage, liquidation, fees, portfolio construction, execution rules, trade count, or win rate.

## Required outputs

Create exactly the 19 paths in `.codex/ALLOWLIST.txt` below:

`experiments/EXP-033_ADA_ONLY_TEMPORAL_STRUCTURE/`

- `REPORT.md`: complete human-readable result and one explicit scientific verdict;
- `PROTOCOL.md`: frozen inputs, definitions, candidate selection, causal rules, reference boundary, nulls, metrics, and decision procedure;
- `experiment_033.py`: deterministic bounded-memory implementation;
- complete 4H and 1H causal state tables;
- reference-only movement table;
- temporal split and protected-future proof;
- frozen state and candidate definitions;
- start, age, correction, termination, hierarchy, regime, and null metrics;
- deterministic counterexamples;
- two clean-run hashes;
- implementation audit and test results.

The script must support:

- `--self-test --temp-dir PATH`;
- `--run --output-dir PATH --temp-dir PATH`.

Run the complete experiment twice into separate clean temporary output directories. Substantive outputs must be byte-identical. Deterministic gzip files must use fixed filename headers and `mtime=0`.

Use streaming, chunking, or disk-backed temporary storage outside the repository. Peak RSS must remain below `1,048,576 KiB`. Every output must remain below 95 MiB. Do not create repository-local cache, bytecode, SQLite, journal, shard, partial, temporary, or log files.

## Immutable repository state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including every EXP-031/EXP-032 attempt and all DATA-002 persistent archives.

The protected Pine must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md` or any pre-existing tracked bytecode/cache path. No task-created path may exist outside the allowlist.

## Role contract

Planner must verify DATA-002 persistent files, hashes, exact counts, split feasibility, helper provenance, and protected-future isolation. With DATA-002 valid, absence of experiment outputs is expected and must not trigger correction.

Implementer must execute the complete experiment and create all 19 substantive outputs. Empty or `DATA_FAILED` placeholder tables are prohibited when DATA-002 verification passes.

Auditor must independently verify data identity, hashes, counts, state causality, candidate freezing before 2025, reference isolation, metrics, verdict, two-run identity, allowlist equality, and immutable paths. It returns `PASS` only when the verdict follows mechanically from the frozen criteria.

Corrector may fix only technical defects inside the allowlist. It may not change the scientific question, data source, time split, scales, permitted windows, candidate selection order, primary metrics, thresholds, or verdict rule.

No role may return `USER_DECISION_REQUIRED`. Missing evidence, helper ambiguity, implementation defects, insufficient samples, or inability to satisfy the frozen contract are technical outcomes.

On final auditor `PASS`, the orchestrator may stage, commit, and push exactly the 19 allowlisted EXP-033 paths.
