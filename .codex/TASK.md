# Current Codex Task

- task_id: `EXP-020-PARENT-REPRESENTATION-TRANSFER`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-019-PARENT-REPRESENTATION`
- commit_message: `EXP-020 parent representation transfer`

## Objective

Test whether the causal parent representations that restored non-degenerate age/origin variability in EXP-019 transfer beyond the original ADA sample. This task evaluates the representation itself, not a trading rule and not another outcome-selected filter.

EXP-019 returned `PARENT_REPRESENTATION_PARTIAL`: `ATR_ORIGIN` and `CONFIRMED_DIRECTION_CHANGE` restored meaningful variability, while `DIRECTION_RUN` and `HYBRID_ORIGIN` remained strongly redundant with displacement and boundary distance. No representation may be selected from aggregate outcome statistics.

Use only existing local data. Missing symbol or interval data must be recorded as `UNAVAILABLE` and must not stop available analyses.

## Fixed scope

- Primary symbols: ADAUSDT, BTCUSDT, ETHUSDT. Include SOLUSDT and XRPUSDT only when the committed local dataset supports the same complete interval and conventions.
- Parent scale: 4H; child fallback and closed-bar conventions exactly as committed in EXP-014 through EXP-019.
- Reconstruct the same causal transition detector independently for every available symbol at factors `0.8`, `1.0`, and `1.2`.
- For ADA factor `1.0`, assert exact identity with the committed 425 EXP-014 BASE rows and applicable EXP-019 representation fields.
- No future pivots, lookahead, repainting, future returns, outcome-derived labels, chart interpretation, predictive claims, or strategy language.

## Frozen representations

Implement unchanged from EXP-019:

1. `FIXED_8` — reference only.
2. `DIRECTION_RUN` — backward same-direction close run, maximum 32 bars.
3. `ATR_ORIGIN` — backward origin reaching at least `1.0 ATR` causal displacement, maximum 32 bars; invalid if not reached.
4. `CONFIRMED_DIRECTION_CHANGE` — first completed bar after the most recent causal two-bar direction change, maximum 32 bars.
5. `HYBRID_ORIGIN` — later of `DIRECTION_RUN` and `ATR_ORIGIN`.

Do not tune thresholds, confirmation length, or maximum lookback. Do not create new representations.

## Required measurements

For every symbol, detection, factor, and representation preserve:

- origin/end timestamps, age bars, duration hours;
- displacement, extension, efficiency and close location;
- representation-derived boundary and extreme distances;
- recent and whole-window slopes;
- validity, minimum-history, cap-hit, zero-denominator and origin-reason fields.

All measurements must use only bars completed before counter start.

## Required analysis

### A. Reconstruction and availability

Report symbol availability, intervals, bar counts, exclusions and detector support. Assert exact ADA reconstruction and document any unavailable symbol without substituting data.

### B. Representation invariance

For every symbol and representation report:

- valid support and invalid reasons;
- age quantiles, unique ages, entropy or equivalent non-degeneracy measure, and cap-hit rate;
- origin disagreement from `FIXED_8`;
- pairwise rank correlations among age, displacement, efficiency, boundary distance and extreme distance;
- direction and chronological-third splits.

A representation is structurally transferable only if restored variability is not confined to ADA, one direction, one time segment, or invalid-row removal.

### C. Cross-symbol geometry

Using fixed physical definitions rather than outcome-selected bins, compare normalized distributions across symbols:

- age bins `1-2`, `3-4`, `5-8`, `9+`;
- displacement quartiles calculated separately per symbol;
- efficiency bands `<0.25`, `[0.25,0.50)`, `[0.50,0.75)`, `>=0.75`;
- boundary-distance quartiles calculated separately per symbol.

Report distribution distances, rank-order agreement, support concentration, and direction/time stability. Separate representational invariance from any downstream reassertion contrast.

### D. Descriptive structural contrast

For every symbol and fixed family report closed reassertion ATR, deterministic non-overlapping matched controls, paired rank contrast, fraction above control and overlap. Include equal-support comparisons against `FIXED_8`.

No representation is supported merely because one symbol or one bin has the largest contrast.

### E. Transfer and factor stability

For factors `0.8`, `1.0`, and `1.2`, report:

- detector support and overlap with factor `1.0`;
- representation validity and age variability;
- origin agreement;
- distribution-rank agreement across symbols;
- contrast direction by symbol, direction and chronological third;
- invalidity and cap stability.

### F. Representation selection rule

Selection must be based first on causal and representational properties:

1. non-degenerate age/origin variability across at least ADA, BTC and ETH when available;
2. acceptable validity without material support selection;
3. low mechanical redundancy relative to displacement and boundary fields;
4. stable definitions across directions, time thirds and factors;
5. only then use descriptive structural contrast as secondary evidence.

If multiple representations satisfy these conditions, retain all as unresolved rather than selecting from the best aggregate contrast.

### G. Counterexamples

Export causal examples of:

- representation valid on ADA but invalid or degenerate on another symbol;
- origin disagreement without downstream structural difference;
- apparent transfer caused by invalid-row removal or support collapse;
- cross-symbol rank reversal;
- direction, time-third or factor reversal;
- disagreement between `ATR_ORIGIN` and `CONFIRMED_DIRECTION_CHANGE`.

## Decision

Select exactly one verdict:

- `REPRESENTATION_TRANSFER_SUPPORTED` — at least one frozen representation restores non-degenerate upstream variability across available core symbols, remains causally valid and non-redundant across directions/time/factors, and shows stable secondary structural evidence without support-selection artifacts.
- `REPRESENTATION_TRANSFER_PARTIAL` — variability transfers, but validity, redundancy, symbol coverage, direction/time/factor stability, or secondary structural evidence remains limited.
- `REPRESENTATION_TRANSFER_REJECTED` — restored variability is ADA-specific, mechanically redundant, unstable, invalidity-driven, or fails cross-symbol reconstruction.

Do not force a positive verdict.

## Required outputs

Create exactly these eight files:

- `experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/REPORT.md`
- `experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/representation_transfer.csv`
- `experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/symbol_summary.csv`
- `experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/distribution_comparison.csv`
- `experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/matched_controls.csv`
- `experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/parameter_stability.csv`
- `experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/counterexamples.csv`
- `experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/experiment_020.py`

Do not create or modify any other path. Do not create `__pycache__` or `.pyc` files.

## Python requirements

`experiment_020.py` must regenerate all seven CSV files and `REPORT.md` deterministically; assert exact ADA reconstruction; implement all frozen representations from completed bars; preserve unavailable symbols and invalid rows explicitly; assert factor runs and non-overlapping controls; reproduce report values and verdict from generated CSV rows; and print a compact summary of symbol support, representation validity, age variability, redundancy, cross-symbol agreement, factor stability, verdict and report path.

## Hard protections

Never modify, stage, delete, rename, chmod, or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, any EXP-009 or EXP-013 through EXP-019 file, `start.sh`, `.git` internals, or any path outside the eight EXP-020 outputs. Existing local dirty files must remain byte-identical, unstaged and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_020.py` twice and verify identical SHA-256 hashes for all eight outputs.
2. Parse all seven CSV files and verify documented columns.
3. Assert exact ADA factor-1.0 reconstruction and agreement with applicable EXP-019 fields.
4. Verify every representation uses only completed bars before counter start and retains the frozen 32-bar cap.
5. Verify unavailable symbols, invalid rows, minimum history, zero denominators and cap hits are explicit.
6. Verify no representation or threshold was selected from outcome statistics.
7. Verify controls are deterministic, source-excluded and non-overlapping.
8. Verify chronological thirds are deterministic and exhaustive per symbol.
9. Verify parameter rows come from actual factor runs `0.8`, `1.0`, and `1.2`.
10. Verify equal-support comparisons against `FIXED_8` and cross-symbol distribution comparisons.
11. Verify REPORT values and verdict reproduce from generated outputs.
12. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-020_PARENT_REPRESENTATION_TRANSFER/experiment_020.py`, then remove generated cache artifacts.
13. Run `git diff --check` and baseline-relative allowlist validation.
14. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the eight allowlisted EXP-020 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.