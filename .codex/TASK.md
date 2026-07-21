# Current Codex Task

- task_id: `EXP-033R1-ADA-ONLY-TEMPORAL-STRUCTURE`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `RESEARCH`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-002_ADAUSDT_2023_2025/REPORT.md`
- data_manifest_sha256: `8381b91af7af7f94890ad60c9fe954459540ebbd1bc9824d94aaf1b7f73075a4`
- commit_message: `EXP-033R1 clean ADA-only temporal structure validation`

## Purpose

Perform a clean, independently auditable ADA-only temporal validation after EXP-033 failed technical audit.

EXP-033's reported `REJECT` is not scientific evidence. Its implementation used an unclosed daily bar, a constant candidate score, placeholder null models, incomplete stability metrics, incomplete metadata verification, and incomplete rerun/resource evidence. Do not copy, import, repair, or use any EXP-033 output, code, parameter, metric, or verdict. Preserve every EXP-033 path byte-for-byte as pre-existing state.

The research question is:

> Can one frozen causal language, defined only from ADAUSDT during 2023–2024, retain the same structural meaning on independent ADAUSDT data from calendar 2025?

This is a market-language study, not a strategy study.

## Mandatory ADA data

Use only the persistent DATA-002 canonical files below `MSM_MARKET_DATA_ROOT`:

- `bybit/linear/ADAUSDT/ADAUSDT_1h_2023_2025.csv`;
- `bybit/linear/ADAUSDT/ADAUSDT_4h_2023_2025.csv`;
- `bybit/linear/ADAUSDT/ADAUSDT_1d_2023_2025.csv`.

The 15m file may be opened only for deterministic reconciliation of selected aggregates and must not become a model scale.

Before analysis, directly verify:

1. committed DATA-002 `REPORT.md` has the task-declared SHA-256 and `DATA_READY=YES`;
2. `readiness_manifest.csv` and every manifest-listed metadata JSON reopen successfully;
3. persistent CSV and metadata hashes, identity, schema, interval, first/last timestamp, row counts, gap counts, duplicate counts, and aggregation parent bindings;
4. exact counts: 1H `26304`, 4H `6576`, 1D `1096`;
5. exact half-open interval `2023-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z`;
6. zero rows, requests, statistics, or diagnostics on or after `2026-01-01T00:00:00Z`.

Record this verification in `data_verification.csv`. Any mismatch makes the scientific result `DATA_FAILED`.

BTC, ETH, SOL, XRP, every other instrument, funding, open interest, trades, order books, and third-party data are prohibited.

## Frozen temporal split

- development/calibration: `2023-01-01T00:00:00Z <= timestamp < 2025-01-01T00:00:00Z`;
- independent validation: `2025-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z`;
- protected future: `timestamp >= 2026-01-01T00:00:00Z`, never accessed.

No definition, threshold, reference parameter, null procedure, matching window, or decision threshold may change after any 2025 scientific metric is inspected.

## Exact causal alignment

All timestamps identify bar opens.

For a 4H bar opening at `t`, the model state is emitted at its close `t+4h`.

A 1D row opening at `d` becomes available only at `d+24h`. At a 4H close time `c`, join the latest daily row satisfying `d+24h <= c`. Never join a same-day daily row before that daily bar closes. Persist a test covering 00:00, 04:00, 20:00, and the year boundary.

Compute 1H states independently. For a 4H bar `[t,t+4h)`, use only the four 1H children opening at `t`, `t+1h`, `t+2h`, and `t+3h`; each must have closed by `t+4h`.

No centered windows, future extrema, backward state revision, interpolation, gap filling, synthetic bars, or substitute data are permitted. Unavailable inputs produce `UNKNOWN`.

## One fixed causal specification

There is no candidate search and no best-cell selection. `candidate_selection_metrics.csv` must contain one row declaring `FIXED_SPEC`, candidate count `1`, validation-used-for-selection `NO`, and the development-only threshold hashes. A constant or fabricated score is forbidden.

For each scale, use only closed bars and calculate:

- true range: `max(high-low, abs(high-prev_close), abs(low-prev_close))`;
- ATR14: simple trailing mean of 14 true ranges;
- EMA27: recursive EMA seeded by the first available 27-close SMA;
- normalized EMA slope: `(EMA27[t]-EMA27[t-k])/ATR14[t]`;
- normalized displacement: `(close[t]-close[t-w])/ATR14[t]`;
- efficiency: `abs(close[t]-close[t-w]) / sum(abs(close[i]-close[i-1]))` over the same window; zero denominator is `UNKNOWN`;
- overlap density: mean adjacent-candle price-range intersection divided by the smaller positive range, clipped to `[0,1]`;
- trailing volatility percentile: rank of current ATR14 against the preceding 96 completed ATR14 values, excluding current;
- causal retracement from the running extreme of the active parent movement.

Use fixed windows:

- 4H: slope `k=3`, displacement/efficiency `w=12`, overlap over 6 adjacent pairs;
- 1H: slope `k=6`, displacement/efficiency `w=24`, overlap over 12 adjacent pairs.

Estimate only these thresholds from the 2023–2024 population separately for 4H and 1H:

- `S70=q70(abs(normalized_slope))`;
- `S50=q50(abs(normalized_slope))`;
- `D70=q70(abs(normalized_displacement))`;
- `D50=q50(abs(normalized_displacement))`;
- `E30=q30(efficiency)`;
- `O70=q70(overlap_density)`.

Use a deterministic documented quantile convention and persist exact values and population hashes in `state_definition.csv`.

Raw direction is `+1` when slope `>=S70`, displacement `>=D70`, and efficiency `>E30`; `-1` under the sign-symmetric conditions; otherwise `0`. A directional confirmation requires two consecutive equal nonzero raw directions.

Emit exactly these phases:

- `UNKNOWN`: insufficient/invalid causal history;
- `DENSITY`: no confirmed direction, efficiency `<=E30`, overlap `>=O70`;
- `EMERGING`: first bar of a newly confirmed nonzero direction different from the active parent;
- `DEVELOPING`: active parent direction remains supported by same-sign slope or displacement at magnitude `>=S50` or `D50`;
- `CORRECTION`: active parent remains intact, no confirmed opposite direction, counter-direction displacement has magnitude `>=D50`, and causal retracement is `<0.618`;
- `TERMINATING`: confirmed opposite raw direction, or retracement `>=0.618` together with `abs(slope)<S50` for two consecutive bars.

After `TERMINATING`, clear the parent for the next bar unless a confirmed opposite direction emits `EMERGING`. Age is completed bars since `EMERGING`, begins at zero, and resets only on termination, unknown, or opposite emerging. Record every transition rule explicitly.

## Reference-only evaluation

Use the committed reference helper:

`experiments/EXP-008_MAJOR_MOVE_ENTRY_LABELING/experiment_008.py`

Verify and record Git blob `a4acb9da80dac9197fdbc32470cdaa4ebe7d5e20` in `helper_provenance.csv`. If the blob does not match, return `DATA_FAILED`; do not silently replace the helper.

The reference may be retrospective only for evaluation. Freeze its parameters from development and apply unchanged to 2025. It must never enter causal features or thresholds. Reference segmentation for 2025 may use only timestamps before 2026.

## Required measurements

Report development and validation separately; never pool them for acceptance.

1. Start correspondence: causal `EMERGING` versus same-direction reference start within `±3` 4H bars; counts, precision, recall, lead/lag distribution, and circular-shift lift.
2. Age ordering: Spearman age versus normalized reference progress; age-quartile medians and ordering violations, split by direction, half-year, and quarter.
3. Correction distinction: `CORRECTION` versus `DEVELOPING` signed normalized displacement over the next 1 and 3 closed 4H bars as evaluation outcomes only; count, median, quartiles, Cliff's delta, expected sign, and development/validation sign agreement.
4. Termination correspondence: causal `TERMINATING` versus reference end within `±3` 4H bars; counts, precision, recall, lead/lag, and circular-shift lift.
5. Parent-child hierarchy: independently computed 1H direction/phase composition within 4H phases; child counts, aligned child sequences, observed statistic, null distribution, and lift.
6. ADA-internal stability: split by ADA 1D direction, 4H volatility below/above frozen development median, direction, half-year, and quarter. No BTC-defined regime.

Persist all required half-year tests and quarterly event-concentration tests in `stability_metrics.csv`. Subgroups with fewer than 10 relevant events are `INSUFFICIENT_SAMPLE`, never PASS.

## Real null models and baseline

Use deterministic seed `330033` and `1000` replications for each stochastic null.

- start/termination null: same-count circular shifts independently within each calendar quarter;
- hierarchy null: preserve every contiguous phase-block label and duration, then permute whole blocks within the same quarter;
- EMA-only baseline: EMA27 normalized-slope direction using the same `S70` and two-bar confirmation, with actual start/termination metrics.

Store replicate-level values in `null_distributions.csv.gz` and summaries in `null_comparison.csv`. Placeholder text without calculated distributions is a technical failure.

## Scientific acceptance

The implementation/data gate must pass before a scientific verdict: exact ADA identity and hashes, correct temporal split, no protected-future access, exact causal daily/child joins, no leakage, frozen thresholds, real nulls/baseline, deterministic reruns, complete outputs, and no unresolved tests.

Primary 2025 criteria:

1. start precision `>=0.50` and circular-shift lift `>=1.35`;
2. reference-start recall `>=0.40`;
3. age/progress Spearman `>=0.35`, same sign as development, with nondecreasing age-quartile median progress;
4. correction-versus-development `abs(Cliff delta)>=0.25` with expected counter-displacement sign at both 1-bar and 3-bar horizons;
5. termination precision `>=0.45` and circular-shift lift `>=1.35`;
6. hierarchy lift `>=1.35`.

Stability requirements: no central sign reversal; at least four of six criteria pass in both halves of 2025 where adequately sampled; no 2025 quarter contains more than 45% of matched starts or terminations.

Verdict:

- `ACCEPT`: at least five of six criteria and all stability requirements pass;
- `PARTIAL`: three or four criteria pass without reversal, or five pass with one stability failure;
- `REJECT`: two or fewer pass, a central relationship reverses, or one ADA regime dominates;
- `DATA_FAILED`: implementation/data gate cannot be established.

A verdict is a statement about the ADA market-language hypothesis, not a trading conclusion.

## Determinism and resources

The script must support:

- `--self-test --temp-dir PATH`;
- `--run --output-dir PATH --temp-dir PATH`.

Run the complete experiment twice into separate clean directories outside the repository. `run_hashes.csv` must contain `path,run1_sha256,run2_sha256,equal` for every deterministic substantive output except `run_hashes.csv` and `resource_usage.csv`. Gzip must have fixed filename headers and `mtime=0`.

Measure each run's peak RSS and record it in `resource_usage.csv`; each must be below `1,048,576 KiB`. Do not infer memory compliance.

Use only standard-library or already committed project dependencies. All audit reruns and temporary files must use `/dev/shm` or the supplied external temp directory with `PYTHONDONTWRITEBYTECODE=1` and an external `PYTHONPYCACHEPREFIX`. Do not invoke pytest or any command that may create `.pytest_cache`, `__pycache__`, logs, SQLite, journals, partials, or temporary files inside the repository.

## Required outputs and repository boundary

Create exactly the 25 paths in `.codex/ALLOWLIST.txt` under `experiments/EXP-033R1_ADA_ONLY_TEMPORAL_STRUCTURE/`.

All files must reopen successfully and be below 95 MiB. Leave them unstaged. No task-created repository path may exist outside the allowlist.

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including EXP-033 and all earlier failed attempts. Preserve the protected Pine byte-identically, dirty and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not modify `.codex/RESULT.md` or any pre-existing tracked cache/bytecode path.

## Role contract

Planner verifies DATA-002 files, metadata, helper blob, clean fresh output directory, causal join feasibility, and the exact allowlist. Return `PASS` only when actionable.

Implementer writes a new implementation from the frozen contract, creates all 25 outputs, uses no EXP-033 implementation/evidence, and performs both clean runs.

Auditor must independently inspect formulas, timestamps, daily-close joins, 1H joins, development-only thresholds, helper isolation, all split metrics, replicate-level nulls, EMA baseline, rerun hashes, RSS evidence, allowlist, and immutable paths. Audit commands must be read-only with all temporary/cache paths outside the repository. Before returning, run `git status --porcelain=v1 -z --untracked-files=all`, compare with the captured baseline, and remove only task-created non-allowlisted temporary/cache paths if any; never modify baseline paths.

Corrector may fix only technical defects within the 25 allowlisted outputs and external temporary run directories. It may not change the research question, fixed state specification, split, metrics, thresholds, null counts, seed, or acceptance rules.

No role may return `USER_DECISION_REQUIRED`. Technical or evidentiary defects are `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

On final auditor `PASS`, the orchestrator may stage, commit, and push exactly the allowlisted EXP-033R1 paths.
