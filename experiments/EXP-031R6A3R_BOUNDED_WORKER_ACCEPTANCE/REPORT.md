# EXP-031R6A3R bounded worker acceptance

Status: BOUNDED_WORKER_REPRESENTATION_READY

The BTCUSDT bounded worker completed the October 2024 reconciliation overlap and the January 1-3, 2025 construction fixture. It validates 15-minute OHLC and OI grids and the 8-hour funding grid, emits both scales, all five frozen representations, and all thirteen scalar fields.

October observations were independently streamed from committed EXP-029R evidence into external SQLite and matched on the complete compound identity including representation and field. October volatility was compared to committed EXP-029R as a duplicate-preserving multiset after projecting generated rows by dropping only representation. Separate external SQLite checks for October and January confirmed full generated identities and exactly five frozen representation labels with identical regime, reason, ATR ratio and closed-through value for every base volatility identity.

Two sequential external fixture runs produced equal hashes and row counts for all substantive outputs. The separate BTCUSDT worker invocation completed, and measured self-test RSS was below 1 GiB. Explicit empty-timestamp UNKNOWN control rows are retained where controls are unmatched.

No full four-symbol calendar-2025 dataset was produced. This task makes no scientific confirmation, rejection, transfer, ranking, filtering, or predictive claim.
