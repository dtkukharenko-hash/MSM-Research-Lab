# DATA-001 Bybit 2025 readiness

Overall status: READY

DATA_READY=YES

Frozen panel: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT; Bybit V5 linear; 2025-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z.

READY sources: 12/12.

## Failures

- None

The manifest independently validates the 2025 slice; gaps.csv lists every missing expected timestamp and conflicting duplicate. request_summary.csv records the mandatory preflight probes and acquisition outcomes.
