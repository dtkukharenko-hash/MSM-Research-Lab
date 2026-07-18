# Current Codex Task

- task_id: `EXP-022-ADA-LOWER-TIMEFRAME-TRANSFER`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-019-PARENT-REPRESENTATION`
- commit_message: `EXP-022 ADA lower timeframe transfer`

## Objective

Test whether the same causal parent/counter structure and parent-origin representations studied on ADAUSDT 4H/1H remain meaningful on lower ADAUSDT scales centred on 15m, 5m and 3m.

This is a descriptive structural transfer test. It is not a trading rule, not an entry/exit study and not a threshold search. Lower-timeframe definitions must be frozen before downstream measurements are inspected.

## Data gate

Use only existing local ADAUSDT data. First audit all documented local sources that may contain native or causally derivable 3m, 5m and 15m OHLC bars.

For every requested timeframe assign one status:

- `READY_NATIVE` — complete native bars are available;
- `READY_DERIVABLE` — bars can be deterministically aggregated from a smaller valid interval;
- `PARTIAL` — data exist but gaps, range or schema are insufficient;
- `UNAVAILABLE` — no usable local source exists;
- `CONFLICTED` — candidate sources materially disagree.

Do not download, fabricate, forward-fill, interpolate or substitute data. Do not silently replace 3m with 1m, 5m or another interval. Unavailable timeframes remain explicit and do not block analysis of ready timeframes.

## Frozen scale mappings

Evaluate each ready child timeframe independently with these predeclared parent mappings:

1. child `15m` → parent `1H`;
2. child `5m` → parent `15m`;
3. child `3m` → parent `15m`.

The 15m→1H mapping is the bridge to the committed 4H→1H research. The 5m and 3m mappings test whether the same form appears one scale lower while sharing a 15m parent.

All aggregate bars must be UTC-aligned, complete and closed. A source event may use only parent bars completed strictly before its counter start.

## Frozen detector transfer

Transfer the causal transition detector from EXP-014 through EXP-020 by scale, preserving its dimensionless conventions:

- use the same detector factors `0.8`, `1.0`, `1.2`;
- ATR, displacement, extension and boundary distances remain normalized in ATR units;
- durations and lookbacks are represented in bars first, clock time second;
- no future pivots, repainting, future returns, outcome labels or chart-selected examples;
- do not tune separate thresholds for 15m, 5m or 3m after observing results.

If a committed definition cannot be transferred mechanically because it embeds a 4H-specific constant, document the conflict and use the predeclared scale conversion below rather than outcome-based tuning:

- an eight-parent-bar reference remains `FIXED_8` at every parent scale;
- maximum origin lookback remains 32 parent bars;
- two-parent-bar direction-change confirmation remains two parent bars;
- `ATR_ORIGIN` threshold remains `1.0 ATR` measured causally at counter start.

## Frozen parent representations

Implement unchanged in parent-bar units:

1. `FIXED_8` — eight completed parent bars before counter start; reference only.
2. `DIRECTION_RUN` — backward same-direction close run, maximum 32 parent bars.
3. `ATR_ORIGIN` — backward origin whose cumulative direction-aware displacement reaches at least `1.0 ATR`, maximum 32 bars; invalid if never reached.
4. `CONFIRMED_DIRECTION_CHANGE` — first completed parent bar after the latest causal two-bar direction change, maximum 32 bars.
5. `HYBRID_ORIGIN` — later origin from `DIRECTION_RUN` and `ATR_ORIGIN`.

Do not add new representations and do not select one from downstream contrast.

## Required measurements

For every ready timeframe, detector factor, source detection and representation preserve:

- child timeframe, parent timeframe and source identity;
- counter start/end and all parent origin/end timestamps;
- age in parent bars and duration in minutes;
- direction-aware displacement and extension in ATR;
- efficiency, close location and representation range;
- distance to representation boundary and from representation extreme in ATR;
- recent and whole-window direction-aware slopes;
- validity, insufficient history, cap hit, zero denominator and origin reason;
- chronological third and parent direction.

Every measurement must use only bars closed before the relevant timestamp.

## Required analysis

### A. Data readiness and integrity

For 3m, 5m and 15m report source path, hash, schema, first/last timestamp, row count, duplicates, gaps, invalid OHLC, alignment and native/derived status. For derived bars report component completeness and equality against any overlapping native archive.

### B. Detector support by scale

For every ready child/parent mapping and factor report:

- parent and child bar coverage;
- source detection count and rate per 1,000 parent bars;
- UP/DOWN support;
- chronological-third support;
- overlap of factors 0.8 and 1.2 with factor 1.0;
- collapse or concentration flags.

### C. Representation invariance by scale

For every representation and ready mapping report:

- valid support and invalid reasons;
- age q25/q50/q75, unique ages and entropy or equivalent non-degeneracy;
- cap-hit and minimum-history rates;
- origin disagreement from `FIXED_8` in bars and minutes;
- pairwise rank correlations among age, displacement, efficiency, boundary distance and extreme distance;
- direction and chronological-third stability.

The key question is whether restored parent-origin variability persists below 4H/1H without becoming mechanically redundant or invalidity-selected.

### D. Cross-scale geometry

Compare normalized distributions across the ready mappings using frozen physical families:

- age bins `1-2`, `3-4`, `5-8`, `9+` parent bars;
- efficiency bands `<0.25`, `[0.25,0.50)`, `[0.50,0.75)`, `>=0.75`;
- per-scale displacement quartiles;
- per-scale boundary-distance quartiles.

Report distribution distances, rank-order agreement, direction/time stability and support concentration. Compare 15m→1H directly with the committed 4H→1H ADA result where fields are definition-compatible, while keeping samples and clock horizons separate.

### E. Descriptive structural contrast

Using deterministic source-excluded, non-overlapping controls, report closed reassertion ATR and paired rank contrast for every frozen family. Include equal-support comparisons against `FIXED_8`.

These fields are secondary evidence only. No representation or timeframe is supported merely because it has the largest aggregate contrast.

### F. Scale consistency

A structural form is scale-consistent only when:

1. detector support is non-collapsed on at least two requested child scales;
2. at least one non-fixed representation restores non-degenerate age/origin variability on those scales;
3. validity and cap behaviour are acceptable without material support selection;
4. rank relationships and normalized geometry do not reverse systematically by direction, chronological third or factor;
5. any similarity to the 4H/1H result is not caused only by shared 1H parent bars or duplicated source intervals.

If only one requested scale is ready, report partial evidence and do not claim multi-scale transfer.

### G. Counterexamples

Export causal examples of:

- lower-scale detection with no analogous parent geometry;
- variable origin collapsing to `FIXED_8` geometry;
- apparent consistency caused by invalid-row removal or cap hits;
- reversal by child scale, direction, time third or factor;
- 3m and 5m disagreement while sharing the same 15m parent;
- high-frequency noise producing repeated overlapping detections.

Record structural reasons only.

## Decision

Select exactly one verdict:

- `LOWER_TIMEFRAME_TRANSFER_SUPPORTED` — the same causal structural form and at least one non-fixed parent representation remain non-degenerate, valid and broadly stable on at least two of 15m, 5m and 3m, including factor/direction/time checks, without overlap or support-selection artifacts.
- `LOWER_TIMEFRAME_TRANSFER_PARTIAL` — useful lower-scale structure or variability is present, but data availability, overlap, redundancy, validity or scale stability remains limited.
- `LOWER_TIMEFRAME_TRANSFER_REJECTED` — the form collapses, becomes mechanically redundant/noise-dominated, or reverses across available lower scales.
- `LOWER_TIMEFRAME_DATA_UNAVAILABLE` — no requested mapping has sufficient local data for an honest test.

Do not force a positive verdict.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/REPORT.md`
- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/data_readiness.csv`
- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/detections.csv`
- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/representations.csv`
- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/scale_comparison.csv`
- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/matched_controls.csv`
- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/parameter_stability.csv`
- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/counterexamples.csv`
- `experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/experiment_022.py`

Do not create or modify any other path. Do not create `__pycache__`, `.pyc` or permanent derived candle archives.

## Python requirements

`experiment_022.py` must regenerate all eight data/report outputs deterministically; discover and hash local data without modifying it; construct only complete UTC-aligned closed aggregates; implement the frozen detector and five parent representations causally; preserve unavailable scales and invalid rows explicitly; create deterministic non-overlapping controls; reproduce all report values and verdict from generated outputs; and print a compact summary of readiness, support by scale, representation variability, cross-scale agreement, factor stability, verdict and report path.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, any EXP-009 or EXP-013 through EXP-021 file, `start.sh`, `.git` internals, source datasets or any path outside the nine EXP-022 outputs. Existing local dirty files must remain byte-identical, unstaged and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_022.py` twice and verify identical SHA-256 hashes for all nine outputs.
2. Parse every CSV and verify documented columns.
3. Verify every selected source path and recorded SHA-256 hash.
4. Verify no source dataset changed.
5. Verify every aggregate uses complete UTC-aligned closed component bars without imputation.
6. Verify each representation ends before counter start and respects frozen 8/32/two-bar/1.0-ATR definitions.
7. Verify unavailable, partial, invalid, insufficient-history, cap-hit and zero-denominator cases are explicit.
8. Verify factors 0.8, 1.0 and 1.2 are actual detector runs.
9. Verify chronological thirds are deterministic and exhaustive per mapping.
10. Verify controls are deterministic, source-excluded and non-overlapping.
11. Verify 3m/5m shared-parent overlap and repeated-detection concentration are quantified.
12. Verify no thresholds, representations or scales were selected from outcomes.
13. Verify REPORT values and verdict reproduce from generated outputs.
14. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-022_ADA_LOWER_TIMEFRAME_TRANSFER/experiment_022.py`, then remove generated cache artifacts.
15. Run `git diff --check` and baseline-relative allowlist validation.
16. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-022 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.
