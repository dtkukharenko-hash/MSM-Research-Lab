# EXP-021 — Local data audit

Status: DATA_NOT_READY

## Hypothesis and motivation

Existing local sources can support an honest, comparable causal 1H/4H rerun of EXP-020 for ADAUSDT, BTCUSDT, and ETHUSDT. This audit tests availability and integrity only; it does not test or select a market representation.

## Data used and causal constraints

Read-only audit of every local OHLC candidate documented by committed experiments: two committed EXP-011 ADAUSDT archives and the existing external ADA feature archive. Timestamps, ordering, duplicates, OHLC/OHLCV availability and numeric validity, gaps, terminal closure, overlaps, and SHA-256 hashes were measured from content. Timestamps are interpreted in UTC and aggregation requires UTC-aligned, complete closed component bars. No data were downloaded, copied, imputed, forward-filled, substituted, or used for a representation comparison.

## Method, baselines, and controls

The null availability control is explicit `UNAVAILABLE` for symbols with no content-verified local source. The committed native 4H archive is compared field-by-field with the deterministic 4H construction from committed 1H bars and, separately, with the external feature archive wherever timestamps overlap. Source choice is based on provenance and equality checks, never downstream results.

## Results

ADAUSDT has a committed UTC 1H archive with 13200 rows and a deterministic UTC 4H reconstruction with 3300 complete bars. Its committed native 4H equality is 3300/3300; the external 4H archive materially disagrees and is not selected. The candidate archives have no volume column, which is recorded rather than fabricated. BTCUSDT and ETHUSDT have no usable local source in the documented locations; SOLUSDT and XRPUSDT are likewise explicitly `UNAVAILABLE`.

## Verdict and next actions

**DATA_NOT_READY** — EXP-020 must not be rerun. The rejection condition is met: the required three core symbols cannot satisfy a frozen common 2,500-complete-4H-bar overlap with zero missing bars and no unresolved conflicts. Exact source hashes, schema mappings, aggregation evidence, and blockers are frozen in `data_manifest.json`. Obtain content-verifiable BTCUSDT and ETHUSDT 1H or 4H archives before a new audit; do not substitute symbols or fill gaps.
