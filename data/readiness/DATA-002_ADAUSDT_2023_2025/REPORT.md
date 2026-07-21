# DATA-002 ADAUSDT 2023–2025 readiness

Overall status: READY

DATA_READY=YES

Instrument: ADAUSDT Bybit linear

Frozen interval: 2023-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z. No timestamp on or after 2026-01-01T00:00:00Z was requested, read, persisted, counted, or inspected. Native source is official Bybit V5 kline at 15 minutes.

Expected counts: 15m 105216; 1H 26304; 4H 6576; 1D 1096. Four canonical persistent files and adjacent metadata are listed in `readiness_manifest.csv`. The 1H/4H/1D archives are deterministic aggregations of validated 15m children; reconciliation is in `aggregation_checks.csv`. Two independent persisted-file validation passes are identical in `run_hashes.csv`.

Request windows and every retry outcome are in `request_summary.csv`; data defects are in `gaps.csv`.
