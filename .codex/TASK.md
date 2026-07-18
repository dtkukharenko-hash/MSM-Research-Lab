# Current Codex Task

- task_id: `EXP-024-ADA-COHERENT-LOWER-TIMEFRAME-TRANSFER`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-023-ADA-LOWER-TIMEFRAME-DATA`
- commit_message: `EXP-024 coherent Bybit lower timeframe transfer`

## Objective

Rerun the lower-timeframe structural transfer test on one internally coherent official Bybit ADAUSDT linear hierarchy: native 3m, 5m and 15m bars, with 1H deterministically derived from native 15m. Do not mix the committed EXP-011 1H archive into the primary analysis.

EXP-023 established zero missing bars and exact 3m→15m and 5m→15m equality over the frozen range. Its `DATA_NOT_READY` verdict was caused only by material disagreement between official Bybit-derived 1H and the older committed 1H archive. Treat that mismatch as a provenance conflict, not as evidence against the internally coherent Bybit hierarchy.

This is a descriptive causal representation test, not a trading rule, entry/exit study or threshold search.

## Data contract

Use only official Bybit V5 public linear ADAUSDT klines with the exact frozen range:

- `2023-07-01T00:00:00Z` through `2024-12-31T23:00:00Z`;
- native intervals `3`, `5`, `15`;
- endpoint `https://api.bybit.com/v5/market/kline`;
- `category=linear`, `symbol=ADAUSDT`.

First look for the exact EXP-023 hashes:

- 3m: `ac96daf57a4e118565db3d12f729173a3fd59fddd0b9fbcbda0cc4fefd93d87d`;
- 5m: `1caa68f3fa7ac3dd56b50e42173653fdd0a5d4c71223c0eef0811b5fb84049d6`;
- 15m: `0ddfb8ad29eee1b279e39c79dbf94a019392b162dd2117a9137e01f5fcff7954`.

Expected stable paths are `${HOME}/.local/share/msm-market-data/bybit/linear/ADAUSDT/ADAUSDT_{3m,5m,15m}.csv`. If files are absent or hashes differ, reacquire only from the same official endpoint using the EXP-023 acquisition conventions, validate fully and atomically replace the stable local files. Raw archives remain outside GitHub.

Derive 1H only from complete UTC-aligned native 15m components. Do not compare or merge primary measurements with the old committed 1H archive. Record the old-source conflict only in provenance notes.

## Frozen scale mappings

Evaluate independently:

1. child `15m` → parent `1H` derived from the same Bybit 15m source;
2. child `5m` → parent `15m` native Bybit;
3. child `3m` → parent `15m` native Bybit.

All bars must be complete, UTC-aligned and closed. Parent inputs must end strictly before counter start.

## Frozen detector

Transfer the committed causal detector without tuning:

- factors `0.8`, `1.0`, `1.2`;
- normalized ATR displacement, extension and boundary geometry;
- durations represented in bars first and clock time second;
- no future pivots, repainting, future returns, outcome labels or chart-selected thresholds.

Preserve the scale-independent constants:

- `FIXED_8`: 8 completed parent bars;
- maximum origin lookback: 32 parent bars;
- direction-change confirmation: 2 parent bars;
- `ATR_ORIGIN` threshold: 1.0 causal parent ATR.

## Frozen parent representations

Implement exactly:

1. `FIXED_8`;
2. `DIRECTION_RUN`;
3. `ATR_ORIGIN`;
4. `CONFIRMED_DIRECTION_CHANGE`;
5. `HYBRID_ORIGIN`.

Do not add or tune representations. Do not select one from downstream contrast.

## Required analysis

For every mapping, factor, detection and representation report:

- source hashes, native/derived intervals, bar coverage and exact overlap;
- detection support, UP/DOWN support, chronological-thirds and rate per 1,000 parent bars;
- factor overlap with factor 1.0 and collapse/concentration flags;
- validity and invalid reasons;
- age q25/q50/q75, unique ages and entropy;
- cap-hit, minimum-history and zero-denominator rates;
- origin disagreement from `FIXED_8` in parent bars and minutes;
- displacement, extension, efficiency, close location, range, boundary and extreme distances in ATR;
- recent and whole-window slopes;
- rank correlations among age, displacement, efficiency, boundary distance and extreme distance;
- direction, chronological-third and factor stability;
- deterministic source-excluded non-overlapping matched controls and equal-support comparisons with `FIXED_8`;
- repeated/overlapping detection concentration;
- agreement and disagreement between 3m and 5m mappings sharing the same 15m parent.

Compare normalized geometry across mappings using frozen families:

- age bins `1-2`, `3-4`, `5-8`, `9+`;
- efficiency bands `<0.25`, `[0.25,0.50)`, `[0.50,0.75)`, `>=0.75`;
- per-mapping displacement quartiles;
- per-mapping boundary-distance quartiles.

The older committed 4H→1H result may be shown only as an external descriptive reference where definitions match. It must not be used as a shared-source equality requirement or to select a representation.

## Counterexamples

Export causal examples of:

- lower-scale detection with no analogous parent geometry;
- variable origin collapsing to `FIXED_8`;
- apparent consistency caused by invalid-row removal or cap hits;
- reversal by scale, direction, time third or factor;
- 3m/5m disagreement with the same 15m parent;
- repeated overlapping high-frequency detections;
- disagreement between `ATR_ORIGIN` and `CONFIRMED_DIRECTION_CHANGE`.

## Decision

Select exactly one verdict:

- `COHERENT_LOWER_TIMEFRAME_TRANSFER_SUPPORTED` — the form and at least one non-fixed representation remain non-degenerate, causally valid and broadly stable on at least two mappings without support-selection, overlap or factor/direction/time artifacts;
- `COHERENT_LOWER_TIMEFRAME_TRANSFER_PARTIAL` — useful structure exists, but redundancy, validity, overlap, scale consistency or stability remains limited;
- `COHERENT_LOWER_TIMEFRAME_TRANSFER_REJECTED` — the form collapses, becomes mechanically redundant/noise-dominated, or reverses across mappings;
- `COHERENT_LOWER_TIMEFRAME_DATA_FAILED` — exact official archives cannot be validated or reacquired.

Do not force a positive verdict.

## Required outputs

Create exactly these nine committed files:

- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/REPORT.md`
- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/data_provenance.csv`
- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/detections.csv`
- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/representations.csv`
- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/scale_comparison.csv`
- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/matched_controls.csv`
- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/parameter_stability.csv`
- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/counterexamples.csv`
- `experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/experiment_024.py`

Do not commit raw archives or create any other repository path. Do not create `__pycache__` or `.pyc` files.

## Python and validation requirements

`experiment_024.py` must deterministically regenerate all eight report/data outputs, validate or reacquire the exact official archives, derive complete UTC 1H bars from 15m, implement the frozen detector and representations causally, preserve invalid rows explicitly, create deterministic non-overlapping controls, and derive the verdict entirely from generated fields.

Before PASS:

1. Validate source hashes, schemas, ordering, uniqueness, gaps, OHLCV, UTC alignment and closed bars.
2. Assert exact 3m→15m and 5m→15m equality over complete overlap.
3. Assert every derived 1H bar has four complete 15m components.
4. Run actual factors 0.8, 1.0 and 1.2.
5. Assert origins end before counter start and all 8/32/two-bar/1.0-ATR definitions.
6. Verify chronological thirds are deterministic and exhaustive.
7. Verify controls are deterministic, source-excluded and non-overlapping.
8. Quantify repeated detections and 3m/5m shared-parent dependence.
9. Verify no representation, threshold or mapping was selected from outcomes.
10. Run twice and verify identical SHA-256 hashes for all nine outputs.
11. Parse every CSV and reproduce REPORT values and verdict.
12. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/experiment_024.py`, remove cache artifacts, run `git diff --check`, and perform baseline-relative allowlist validation.
13. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 or EXP-013 through EXP-023 file, committed source datasets, or paths outside the nine EXP-024 outputs.

The only permitted non-repository writes are the three stable raw archive paths under `${HOME}/.local/share/msm-market-data/bybit/linear/ADAUSDT/` and temporary files beside them. Existing dirty files must remain byte-identical, unstaged and uncommitted.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-024 outputs unstaged. Raw market data remain outside the repository. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.