# EXP-023 — ADA lower-timeframe data

Status: DATA_NOT_READY

## Data used

Official Bybit V5 public linear ADAUSDT kline responses only; frozen comparison range is 2023-07-01T00:00:00Z through 2024-12-31T23:00:00Z from the committed EXP-021-selected 1H archive. No detector, representation comparison, or downstream analysis was run.

## API acquisition facts

Endpoint: `https://api.bybit.com/v5/market/kline`. Parameters: category=linear, symbol=ADAUSDT, intervals 3/5/15, limit=1000. Full request/retry history is in `acquisition_log.csv`. Raw archives are local-only at the paths frozen in `data_manifest.json`.

## Local validation results

- 3m: READY; 263981/263981 expected rows; missing 0; SHA-256 `ac96daf57a4e118565db3d12f729173a3fd59fddd0b9fbcbda0cc4fefd93d87d`.
- 5m: READY; 158389/158389 expected rows; missing 0; SHA-256 `1caa68f3fa7ac3dd56b50e42173653fdd0a5d4c71223c0eef0811b5fb84049d6`.
- 15m: CONFLICTED; 52797/52797 expected rows; missing 0; SHA-256 `0ddfb8ad29eee1b279e39c79dbf94a019392b162dd2117a9137e01f5fcff7954`.

Cross-interval results use complete UTC-aligned components and tolerance 0.00000001.

- 3m_to_15m: 52796/52796 exact, 0 mismatches; max absolute 0; max relative 0.
- 5m_to_15m: 52796/52796 exact, 0 mismatches; max absolute 0; max relative 0.
- 15m_to_1H: 27/13199 exact, 13172 mismatches; max absolute 0.0047; max relative 0.0085657007472207034809549845088390741753234918899216.

## Verdict and next actions

**DATA_NOT_READY** — `EXP022_RERUN_READY=false`.
Blockers:
- One or more native intervals are not READY or cross-interval equality does not meet the declared tolerance.
