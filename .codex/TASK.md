# Current Codex Task

- task_id: `EXP-032-ADA-ONLY-TEMPORAL-STRUCTURE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-032 ADA-only temporal structure validation`

## Objective

Determine whether ADAUSDT has a stable, causal temporal structure that describes the beginning, development, age, correction, and termination of its own movements across time.

This experiment returns the project to ADA as the primary research object. It does not test transfer from ADA to BTC, ETH, or any other asset.

## Research question

Can one frozen causal state language, calibrated only on ADAUSDT during 2023–2024, retain the same structural meaning on independent ADAUSDT data from calendar 2025?

The language must describe:

1. global ADA context;
2. primary 4H movement direction and phase;
3. local 1H child movement;
4. movement age;
5. correction inside an active movement;
6. termination of the active movement.

## Market boundary

The sole market under study is:

- exchange: Bybit;
- instrument: ADAUSDT linear perpetual;
- primary data: OHLCV;
- primary scale: 4H;
- global context: 1D, using closed bars only;
- local child scale: 1H, using closed bars only.

BTC, ETH, and every other instrument are excluded from:

- feature construction;
- calibration;
- reference labels;
- null models;
- acceptance criteria;
- robustness claims;
- scientific conclusions.

Do not load another instrument as a substitute when ADA data are missing. Missing ADA coverage is a technical/data failure.

## Temporal partition

Use UTC boundaries exactly:

- development/calibration: `2023-01-01T00:00:00Z` through `2024-12-31T23:59:59Z`;
- independent validation: `2025-01-01T00:00:00Z` through `2025-12-31T23:59:59Z`;
- protected holdout: every timestamp on or after `2026-01-01T00:00:00Z`.

The protected 2026 holdout must not be read, summarized, counted, inspected, or used in any way by this task.

All definitions, quantile positions, confirmation counts, matching windows, null procedures, and decision thresholds must be frozen from the task contract or development period before any validation metric is calculated.

No parameter may be changed after inspecting 2025 results.

## Scientific language boundary

This is a market-language experiment, not a strategy experiment.

Do not calculate or discuss:

- entries or exits;
- long or short positions;
- profit, loss, PnL, profit factor, return, equity, drawdown, leverage, liquidation, fees, or risk;
- portfolio construction;
- execution rules;
- trade count or win rate.

Permitted language includes movement, direction, phase, start, age, progress, density, correction, termination, displacement, efficiency, hierarchy, stability, and transfer through time on ADA itself.

## Causal requirements

Every model-side value must be available at the close of the timestamped bar.

Mandatory rules:

1. closed bars only;
2. no centered windows;
3. no future extrema;
4. no backward revision of an already emitted state;
5. no interpolation, synthetic bars, gap filling, or replacement data;
6. unavailable inputs produce `UNKNOWN`;
7. daily context at a 4H timestamp may use only the most recently closed daily bar;
8. 1H child states must be computed independently from closed 1H bars and then joined causally to 4H timestamps;
9. a symmetric or future-aware reference segmentation may be used only as `REFERENCE_ONLY` evaluation labels and must never enter state construction, calibration after the development split, or emitted features.

## Required causal state language

Represent direction separately as `-1`, `0`, `+1`, or `UNKNOWN`.

Represent phase using exactly these semantic classes:

- `DENSITY` — overlapping, low-efficiency movement without a stable direction;
- `EMERGING` — first confirmed causal appearance of a directional movement;
- `DEVELOPING` — directional movement remains structurally active;
- `CORRECTION` — counter-displacement inside the still-active parent direction;
- `TERMINATING` — causal weakening or opposing structure consistent with the end of the parent movement;
- `UNKNOWN` — insufficient or invalid causal history.

Age is the number of completed primary-scale bars since the most recent `EMERGING` state in the current direction. Age resets only when the parent direction terminates, becomes unknown, or a confirmed opposite `EMERGING` state begins.

The causal state engine must use price-derived quantities only. At minimum include and document:

- EMA27 slope normalized by ATR;
- signed displacement over fixed backward windows;
- directional efficiency ratio;
- candle/range overlap density;
- retracement from a causal running extreme;
- trailing volatility percentile using only preceding closed bars;
- persistence/confirmation counts.

Funding and open interest are not permitted as primary state features in EXP-032.

## Calibration contract

Use one deterministic rule specification, not a best-cell search.

Quantile thresholds may be estimated only from the 2023–2024 development population. Their quantile positions must be fixed in `PROTOCOL.md` before validation metrics are generated.

Permitted quantile positions are limited to the fixed set `0.30`, `0.50`, and `0.70`.

Permitted backward windows are limited to:

- primary 4H: 3, 6, 12, and 24 bars;
- child 1H: 6, 12, 24, and 48 bars;
- volatility percentile: preceding 96 closed bars;
- state confirmation: 2 consecutive closed bars.

Do not optimize combinations against 2025. If more than one development-only specification is technically evaluated, choose the specification with the most stable quarterly development behavior, not the largest single metric, and record every candidate and deterministic selection rule in `PROTOCOL.md` and `state_definition.csv`.

## Reference segmentation

Construct one frozen ex-post 4H reference movement population solely for evaluation.

Prefer a committed MSM reference helper already used for causal-vs-reference comparisons. The reference may use future information because it is not a model input, but it must be clearly isolated as `REFERENCE_ONLY`.

The reference output must provide for each movement:

- direction;
- start timestamp;
- end timestamp;
- duration in 4H bars;
- normalized displacement;
- normalized progress for each included 4H bar.

Do not tune the reference definition on 2025.

## Primary measurements

Calculate development and validation results separately. Never pool them for acceptance.

### 1. Start correspondence

For each causal `EMERGING` event, determine whether a same-direction reference start exists within `±3` primary 4H bars.

Report:

- event count;
- matched count;
- precision;
- reference-start recall;
- signed lead/lag distribution;
- lift over a same-count quarterly circular-shift null.

### 2. Age ordering

Within causally matched reference movements, compare causal age with ex-post normalized movement progress.

Report:

- Spearman correlation;
- median normalized progress by causal-age quartile;
- ordering violations;
- results by direction and by half-year.

### 3. Correction distinction

Within an active same-direction reference movement, compare bars labelled `CORRECTION` with bars labelled `DEVELOPING`.

Use signed normalized displacement over the next 1 and 3 closed 4H bars only as evaluation outcomes, never as features.

Report:

- distributions;
- median differences;
- Cliff's delta;
- whether the sign and ordering agree between development and validation.

### 4. Termination correspondence

For each causal `TERMINATING` event, determine whether a reference movement end exists within `±3` primary 4H bars.

Report:

- event count;
- matched count;
- precision;
- reference-end recall;
- signed lead/lag distribution;
- lift over a same-count quarterly circular-shift null.

### 5. Parent-child hierarchy

Build the 1H child state independently and join it causally to each 4H bar.

Measure whether child direction/phase composition differs systematically across 4H parent phases, compared with a duration-preserving within-quarter shuffled null.

Report hierarchy lift, child-count distributions, and the fraction of parent movements with at least one aligned child development sequence.

### 6. ADA-internal regime stability

Use only ADA-derived regimes:

- 1D direction: down, neutral, up;
- 4H trailing volatility: low or high by frozen development median;
- calendar quarter and half-year.

No BTC-defined regime is permitted.

Report each primary metric across these ADA-only regimes and concentration of events by regime.

## Null models

Use at least these three nulls:

1. same-count quarterly circular shifts of causal event timestamps;
2. duration-preserving phase-block shuffles within calendar quarters;
3. a naive EMA27-slope-only causal baseline with the same two-bar confirmation.

Use deterministic seeds and record them.

## Validation acceptance criteria

The data/implementation gate must pass before any scientific verdict:

- exact ADA-only instrument identity;
- exact temporal split;
- no access to 2026;
- complete causal joins and explicit `UNKNOWN` handling;
- no future leakage;
- deterministic rerun hashes;
- no non-ADA market data used;
- all outputs reopen successfully;
- no unresolved implementation test failure.

Primary 2025 criteria:

1. start precision at `±3` bars is at least `0.50` and circular-shift lift is at least `1.35`;
2. reference-start recall is at least `0.40`;
3. age/progress Spearman correlation is at least `0.35`, has the same sign as development, and age-quartile median progress is nondecreasing;
4. correction-vs-development Cliff's delta has absolute magnitude at least `0.25` with the expected counter-displacement sign at both 1-bar and 3-bar horizons;
5. termination precision at `±3` bars is at least `0.45` and circular-shift lift is at least `1.35`;
6. parent-child hierarchy lift is at least `1.35` against the duration-preserving shuffled null.

Stability requirements:

- no primary relationship may reverse sign between development and validation;
- at least four of the six primary criteria must also pass separately in both halves of 2025 where sample size is adequate;
- no single 2025 quarter may contain more than 45% of all matched start or termination events;
- report `INSUFFICIENT_SAMPLE` rather than passing a subgroup with fewer than 10 relevant events.

Scientific verdict:

- `ACCEPT` — at least five of six primary validation criteria pass, no sign reversal occurs, and all stability requirements pass;
- `PARTIAL` — three or four primary criteria pass without a sign reversal, or five pass but one stability requirement fails;
- `REJECT` — two or fewer primary criteria pass, any central relationship reverses sign, or the apparent result is dominated by one ADA regime;
- `DATA_FAILED` — required ADA coverage, causal integrity, or deterministic implementation cannot be established.

Do not reinterpret `PARTIAL` or `REJECT` as a trading conclusion.

## Required outputs

Create exactly the paths in `.codex/ALLOWLIST.txt` under:

`experiments/EXP-032_ADA_ONLY_TEMPORAL_STRUCTURE/`

Required contents:

- `REPORT.md` — complete human-readable result with one explicit scientific verdict;
- `PROTOCOL.md` — frozen definitions, temporal split, parameters, causal rules, reference-only boundary, nulls, and decision criteria;
- `experiment_032.py` — deterministic bounded-memory implementation;
- `ada_4h_states.csv.gz` — complete causal primary states for development and validation;
- `ada_1h_child_states.csv.gz` — complete independently computed child states;
- `reference_moves.csv.gz` — reference-only movement population and normalized progress;
- `temporal_split_summary.csv` — exact coverage, gaps, counts, and protected-holdout proof;
- `state_definition.csv` — frozen feature, window, threshold, and transition definitions;
- `start_metrics.csv`;
- `age_metrics.csv`;
- `correction_metrics.csv`;
- `termination_metrics.csv`;
- `hierarchy_metrics.csv`;
- `regime_metrics.csv`;
- `null_comparison.csv`;
- `counterexamples.csv` — representative false starts, late starts, age-order violations, false terminations, and regime failures selected deterministically;
- `run_hashes.csv` — hashes from two clean independent runs;
- `implementation_audit.csv`;
- `test_results.csv`.

## Implementation requirements

The script must support:

- `--self-test --temp-dir PATH`;
- `--run --output-dir PATH --temp-dir PATH`.

Run the complete experiment twice into separate clean temporary output directories and prove byte-identical substantive outputs. Deterministic gzip files must use a fixed filename header and `mtime=0`.

Use streaming, chunking, or disk-backed temporary storage outside the repository. Peak RSS must remain below `1,048,576 KiB`.

Do not create repository-local SQLite, journal, cache, bytecode, shard, temporary, partial, or log files.

Every CSV and gzip must reopen successfully. Every output must be below 95 MiB.

## Immutable repository state

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged.

The protected Pine must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Preserve all pre-existing tracked bytecode/cache paths. Do not modify `.codex/RESULT.md`.

No task-created path may exist outside the allowlist.

## Role contract

Planner:

- verify exact ADA data availability for 2023–2025;
- verify that 2026 can remain unopened;
- locate committed MSM helpers needed for ATR, EMA, causal joins, and reference-only segmentation;
- return `PASS` when technically actionable;
- use `TECHNICAL_CORRECTION_REQUIRED` or `FAILED` for data or implementation defects.

Implementer:

- implement and run the complete ADA-only experiment;
- create every required output;
- never load BTC, ETH, or another market;
- never inspect 2026;
- leave all task files unstaged.

Auditor:

- independently inspect code, data identity, time boundaries, causal alignment, frozen parameters, reference isolation, outputs, rerun hashes, metrics, verdict, allowlist boundary, and immutable paths;
- reject any claim based on another instrument, validation tuning, future leakage, missing UNKNOWN handling, or 2026 access;
- return `PASS` only when the reported verdict follows mechanically from the frozen criteria.

Corrector:

- correct only technical defects inside the allowlist;
- do not change the research question, market boundary, temporal split, metrics, thresholds, or decision rule;
- do not return `USER_DECISION_REQUIRED` for technical failures.

On final auditor `PASS`, the orchestrator may stage, commit, and push exactly the allowlisted EXP-032 paths.
