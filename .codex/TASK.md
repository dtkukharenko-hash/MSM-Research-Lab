# Current Codex Task

- task_id: `EXP-021-LOCAL-DATA-AUDIT`
- status: `READY`
- published_at: `2026-07-18`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-020-PARENT-REPRESENTATION-TRANSFER`
- commit_message: `EXP-021 local data audit`

## Objective

Audit all existing local market-data sources relevant to ADAUSDT, BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT, determine whether comparable causal 1H and 4H archives can be constructed, and publish a frozen machine-readable readiness manifest for rerunning EXP-020.

This is a data audit and preparation experiment. Do not download external data, fabricate missing bars, forward-fill OHLC, substitute symbols, or run a new representation comparison.

## Fixed scope

- Search only inside the repository and existing local data locations already used by committed experiments.
- Core symbols: ADAUSDT, BTCUSDT, ETHUSDT.
- Optional symbols: SOLUSDT, XRPUSDT.
- Required target intervals: native or causally aggregatable 1H and 4H.
- Preserve source files unchanged. Derived audit outputs may contain metadata and compact gap summaries only; do not copy full candle archives into the experiment folder.
- Use UTC timestamps and closed bars only.

## Required audit

### A. Source discovery

For each candidate dataset record:

- symbol, source path, storage format and schema;
- interval or inferred interval;
- first and last timestamp;
- row count, duplicate count and ordering;
- timestamp timezone evidence;
- OHLCV field availability and numeric validity;
- whether the file is committed, ignored or external to the repository.

Do not treat filename alone as proof of symbol or interval; inspect content and record confidence.

### B. Integrity

For each symbol/interval report:

- expected versus observed timestamps;
- missing-bar count and contiguous gap episodes;
- duplicate timestamps;
- non-monotonic timestamps;
- invalid OHLC relationships;
- zero/negative prices;
- incomplete terminal bars;
- overlap and consistency when multiple sources cover the same timestamps.

No imputation is allowed.

### C. Causal aggregation readiness

When valid lower-interval data exist, test deterministic UTC-aligned aggregation to 1H and 4H using only complete component bars. Report:

- source interval and alignment rule;
- expected component count per aggregate bar;
- complete and incomplete aggregate counts;
- first/last complete aggregate timestamp;
- dropped incomplete aggregates and reasons;
- equality checks against any existing native 1H/4H archive over overlapping timestamps.

Do not write a permanent derived candle archive. The experiment must only prove whether deterministic reconstruction is possible.

### D. EXP-020 readiness

For every symbol assign exactly one status:

- `READY_NATIVE` — complete comparable native 1H and 4H archives exist;
- `READY_DERIVABLE` — comparable archives can be deterministically built from valid lower-interval data;
- `PARTIAL` — usable data exist but coverage, gaps, fields or aggregation completeness are insufficient;
- `UNAVAILABLE` — no usable local source exists;
- `CONFLICTED` — multiple local sources materially disagree and no frozen source can be selected without a new decision.

Predeclare minimum rerun requirements:

1. ADA, BTC and ETH must each be `READY_NATIVE` or `READY_DERIVABLE`;
2. each must have a common overlap interval containing at least 2,500 complete 4H bars;
3. no unresolved duplicate/conflict episodes inside the common interval;
4. missing complete 4H bars inside the common interval must be zero;
5. the manifest must freeze exact source path, source hash, schema, interval, aggregation rule and common interval.

If these conditions are not met, do not rerun EXP-020.

### E. Frozen manifest

Create a deterministic manifest containing:

- selected source per symbol and reason;
- SHA-256 of each selected source;
- schema mapping;
- timezone and timestamp-unit interpretation;
- native/derived interval status;
- aggregation rule;
- valid range and complete-bar counts;
- gap/conflict status;
- common core-symbol overlap;
- final `EXP020_RERUN_READY=true|false` and explicit blockers.

No source may be selected because it improves downstream research results.

## Decision

Select exactly one verdict:

- `DATA_READY_FOR_TRANSFER` — ADA, BTC and ETH satisfy every frozen rerun requirement;
- `DATA_PARTIALLY_READY` — useful additional data exist, but at least one core requirement remains unresolved;
- `DATA_NOT_READY` — BTC/ETH remain unavailable or local data cannot support a comparable causal archive.

## Required outputs

Create exactly these seven files:

- `experiments/EXP-021_LOCAL_DATA_AUDIT/REPORT.md`
- `experiments/EXP-021_LOCAL_DATA_AUDIT/source_inventory.csv`
- `experiments/EXP-021_LOCAL_DATA_AUDIT/integrity_summary.csv`
- `experiments/EXP-021_LOCAL_DATA_AUDIT/gap_episodes.csv`
- `experiments/EXP-021_LOCAL_DATA_AUDIT/aggregation_readiness.csv`
- `experiments/EXP-021_LOCAL_DATA_AUDIT/data_manifest.json`
- `experiments/EXP-021_LOCAL_DATA_AUDIT/experiment_021.py`

Do not create or modify any other path. Do not create `__pycache__` or `.pyc` files.

## Python requirements

`experiment_021.py` must regenerate all six data/report outputs deterministically; inspect candidate files without modifying them; calculate SHA-256 hashes; validate schemas and OHLC relationships; detect gaps and conflicts; prove causal aggregation readiness; generate the frozen manifest and verdict from measured fields; and print a compact summary of source availability, core-symbol readiness, common overlap, blockers, verdict and report path.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, any EXP-009 or EXP-013 through EXP-020 file, `start.sh`, `.git` internals, source datasets, or any path outside the seven EXP-021 outputs. Existing local dirty files must remain byte-identical, unstaged and uncommitted.

## Required validation

Before PASS:

1. Run `experiment_021.py` twice and verify identical SHA-256 hashes for all seven outputs.
2. Parse every CSV and JSON output and verify documented fields.
3. Verify every discovered source path exists and every recorded source hash reproduces.
4. Verify no source dataset changed during execution.
5. Verify gaps, duplicates, ordering, timestamp units, timezone and OHLC validity were measured from content.
6. Verify 1H/4H aggregation uses UTC-aligned complete closed components only and performs no imputation.
7. Verify native-versus-derived overlap checks and conflicts are explicit.
8. Verify the common overlap and rerun readiness reproduce from `data_manifest.json`.
9. Verify unavailable and partial symbols remain explicit and no external download occurred.
10. Verify REPORT values and verdict reproduce from generated outputs.
11. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-021_LOCAL_DATA_AUDIT/experiment_021.py`, then remove generated cache artifacts.
12. Run `git diff --check` and baseline-relative allowlist validation.
13. Verify protected and pre-existing dirty files remain byte-identical and no files are staged.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the seven allowlisted EXP-021 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.
