# Current Codex Task

- task_id: `EXP-032R3-ADA-ONLY-TEMPORAL-STRUCTURE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-032R3 ADA-only temporal structure validation`

## Why this is R3

EXP-032, EXP-032R1, and EXP-032R2 ended at attempt zero before scientific work. The feeder incorrectly inferred a user-decision requirement from ordinary prose in TASK.md. Their terminal reports are technical evidence only and contain no accepted ADA result.

R3 starts after the feeder was changed to:

1. ignore scientific prose when deciding whether to create an envelope;
2. use explicit metadata only;
3. require a one-time launch token created by the dashboard Start action;
4. treat data and implementation defects as technical outcomes, not user-decision outcomes.

Do not use files from EXP-032, EXP-032R1, or EXP-032R2 as code, evidence, parameters, metrics, or scientific support.

## Objective

Determine whether ADAUSDT has a stable causal temporal structure describing the beginning, development, age, correction, and termination of its own movements through time.

The sole scientific question is:

> Can one frozen causal state language, calibrated only on ADAUSDT during 2023–2024, retain the same structural meaning on independent ADAUSDT data from calendar 2025?

## Market boundary

Use only:

- exchange: Bybit;
- instrument: ADAUSDT linear perpetual;
- primary data: OHLCV;
- global scale: 1D closed bars;
- primary scale: 4H closed bars;
- local child scale: 1H closed bars.

BTC, ETH, SOL, XRP, and every other instrument are prohibited in feature construction, calibration, reference labels, null models, acceptance criteria, regimes, robustness claims, and scientific conclusions.

Do not substitute another instrument when ADA data are missing. Missing ADA coverage is a technical data failure.

Funding and open interest are not primary features in this experiment.

## Temporal partition

Use UTC boundaries exactly:

- development/calibration: `2023-01-01T00:00:00Z` through `2024-12-31T23:59:59Z`;
- independent validation: `2025-01-01T00:00:00Z` through `2025-12-31T23:59:59Z`;
- protected holdout: every timestamp on or after `2026-01-01T00:00:00Z`.

The 2026 holdout must not be read, counted, summarized, inspected, or used.

All state definitions, windows, thresholds, confirmation counts, reference rules, null procedures, and acceptance thresholds must be frozen before calculating any 2025 validation metric. No parameter may be changed after inspecting 2025 results.

## Scientific language boundary

This is a market-language experiment, not a strategy experiment.

Do not calculate or discuss entries, exits, positions, PnL, profit factor, return, equity, drawdown, leverage, liquidation, fees, portfolio construction, execution, trade count, or win rate.

Permitted language includes movement, direction, phase, start, age, progress, density, correction, termination, displacement, efficiency, hierarchy, stability, and transfer through time on ADA itself.

## Causal requirements

Every model-side value must be available at the close of the timestamped bar.

Mandatory rules:

1. closed bars only;
2. no centered windows;
3. no future extrema in model features;
4. no backward revision of an emitted state;
5. no interpolation, synthetic bars, gap filling, or replacement data;
6. unavailable input produces `UNKNOWN`;
7. 1D context at a 4H timestamp uses only the most recently closed daily bar;
8. 1H child states are computed independently from closed 1H bars and joined causally to 4H timestamps;
9. future-aware reference segmentation is `REFERENCE_ONLY` and never enters model features or calibration.

## Required state language

Direction must be represented separately as `-1`, `0`, `+1`, or `UNKNOWN`.

Phase must use exactly:

- `DENSITY` — overlapping low-efficiency movement without stable direction;
- `EMERGING` — first confirmed causal appearance of directional movement;
- `DEVELOPING` — directional movement remains structurally active;
- `CORRECTION` — counter-displacement inside an active parent direction;
- `TERMINATING` — causal weakening or opposing structure consistent with ending the parent movement;
- `UNKNOWN` — insufficient or invalid causal history.

Age is the number of completed 4H bars since the most recent `EMERGING` state in the current direction. It resets only when the parent terminates, becomes unknown, or a confirmed opposite `EMERGING` begins.

The engine must use price-derived quantities only. Include and document at minimum:

- EMA27 slope normalized by ATR;
- signed displacement over backward windows;
- directional efficiency ratio;
- candle/range overlap density;
- retracement from a causal running extreme;
- trailing volatility percentile using only the preceding 96 closed bars;
- persistence with two consecutive closed bars.

Permitted backward windows:

- 4H: 3, 6, 12, and 24 bars;
- 1H: 6, 12, 24, and 48 bars;
- volatility percentile: preceding 96 closed bars;
- confirmation: exactly 2 consecutive closed bars.

Quantile positions may be estimated only on 2023–2024 and are limited to `0.30`, `0.50`, and `0.70`.

Use one deterministic specification. Do not perform a best-cell search. When several development-only candidates are technically compared, choose by quarterly stability rather than the best single metric and record all candidates and the deterministic selection rule.

## Reference-only segmentation

Construct one frozen ex-post 4H movement population only for evaluation. It may use future information but must remain isolated from state construction.

For each reference movement provide:

- direction;
- start timestamp;
- end timestamp;
- duration in 4H bars;
- normalized displacement;
- normalized progress for included bars.

Do not tune the reference definition on 2025.

## Measurements

Calculate development and validation separately. Never pool them for acceptance.

### Start correspondence

Match each causal `EMERGING` event to a same-direction reference start within `±3` 4H bars. Report event count, matched count, precision, reference-start recall, lead/lag distribution, and lift over a same-count quarterly circular-shift null.

### Age ordering

Within matched reference movements, compare causal age with normalized reference progress. Report Spearman correlation, median progress by causal-age quartile, ordering violations, direction splits, and half-year splits.

### Correction distinction

Within an active same-direction reference movement, compare `CORRECTION` with `DEVELOPING`. Use signed normalized displacement over the next 1 and 3 closed 4H bars only as evaluation outcomes. Report distributions, median differences, Cliff's delta, and development/validation sign agreement.

### Termination correspondence

Match each causal `TERMINATING` event to a reference end within `±3` 4H bars. Report event count, matched count, precision, reference-end recall, lead/lag distribution, and circular-shift lift.

### Parent-child hierarchy

Build 1H states independently and join them causally to 4H. Compare child direction/phase composition across 4H parent phases with a duration-preserving within-quarter shuffled null. Report hierarchy lift, child-count distributions, and the fraction of parent movements containing at least one aligned child development sequence.

### ADA-internal stability

Use only ADA-derived regimes:

- 1D direction: down, neutral, up;
- 4H trailing volatility: low or high using the frozen development median;
- calendar quarter and half-year.

No BTC-defined regime is permitted.

## Null models

Use at least:

1. same-count quarterly circular shifts of causal event timestamps;
2. duration-preserving phase-block shuffles within calendar quarters;
3. a naive EMA27-slope-only causal baseline using the same two-bar confirmation.

Use deterministic seeds and record them.

## Acceptance criteria

The implementation gate must pass first:

- exact ADAUSDT instrument identity;
- exact temporal split;
- no access to 2026;
- causal joins and explicit `UNKNOWN` handling;
- no future leakage;
- deterministic rerun hashes;
- no non-ADA market data;
- every output reopens successfully;
- no unresolved implementation test failure.

Primary 2025 criteria:

1. start precision at `±3` bars at least `0.50` and circular-shift lift at least `1.35`;
2. reference-start recall at least `0.40`;
3. age/progress Spearman at least `0.35`, same sign as development, with nondecreasing age-quartile median progress;
4. correction-versus-development absolute Cliff's delta at least `0.25` with the expected counter-displacement sign at both 1-bar and 3-bar horizons;
5. termination precision at `±3` bars at least `0.45` and circular-shift lift at least `1.35`;
6. parent-child hierarchy lift at least `1.35`.

Stability requirements:

- no primary relationship reverses sign between development and validation;
- at least four of six criteria pass separately in both halves of 2025 when sample size is adequate;
- no single 2025 quarter contains more than 45% of matched start or termination events;
- a subgroup with fewer than 10 relevant events is `INSUFFICIENT_SAMPLE`, never PASS.

Scientific verdict:

- `ACCEPT` — at least five of six criteria pass, no sign reversal, and all stability requirements pass;
- `PARTIAL` — three or four criteria pass without sign reversal, or five pass with one stability failure;
- `REJECT` — two or fewer criteria pass, a central relationship reverses sign, or the result is dominated by one ADA regime;
- `DATA_FAILED` — required ADA coverage, causal integrity, or deterministic implementation cannot be established.

Do not reinterpret any verdict as a trading conclusion.

## Required outputs

Create exactly the 19 paths in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-032R3_ADA_ONLY_TEMPORAL_STRUCTURE/`

Required outputs:

- `REPORT.md` — complete result with one explicit scientific verdict;
- `PROTOCOL.md` — frozen definitions and decision procedure;
- `experiment_032r3.py` — deterministic bounded-memory implementation;
- complete 4H and 1H state tables;
- reference-only movement table;
- temporal split and protected-holdout proof;
- frozen state definitions;
- start, age, correction, termination, hierarchy, regime, and null metrics;
- deterministic counterexamples;
- two-run hashes;
- implementation audit and test results.

The script must support:

- `--self-test --temp-dir PATH`;
- `--run --output-dir PATH --temp-dir PATH`.

Run the complete experiment twice into separate clean temporary output directories and prove byte-identical substantive outputs. Deterministic gzip files must have fixed filename headers and `mtime=0`.

Use streaming, chunking, or disk-backed temporary storage outside the repository. Peak RSS must remain below `1,048,576 KiB`. Every output must be below 95 MiB.

Do not create repository-local SQLite, journal, cache, bytecode, shard, temporary, partial, or log files.

## Immutable repository state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including all EXP-032, EXP-032R1, and EXP-032R2 paths.

The protected Pine must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md` or any pre-existing tracked bytecode/cache path.

## Role contract

Planner verifies ADA data availability for 2023–2025, confirms 2026 remains unopened, locates committed helpers, and returns `PASS` when technically actionable. Data, helper, or implementation defects are technical outcomes.

Implementer creates all allowlisted outputs, loads no non-ADA market, does not inspect 2026, and leaves all task files unstaged.

Auditor independently checks data identity, time boundaries, causality, frozen parameters, reference isolation, rerun hashes, metrics, verdict, allowlist, and immutable paths. It returns `PASS` only when the verdict follows mechanically from the frozen criteria.

Corrector fixes only technical defects inside the allowlist and may not change the research question, market boundary, temporal split, metrics, thresholds, or decision rule.

No role may return `USER_DECISION_REQUIRED`. Such a result must be normalized to `TECHNICAL_CORRECTION_REQUIRED`.

On final auditor `PASS`, the orchestrator may stage, commit, and push exactly the allowlisted EXP-032R3 paths.
