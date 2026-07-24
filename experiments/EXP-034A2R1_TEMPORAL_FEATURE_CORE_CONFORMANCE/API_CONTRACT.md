# API contract

`join_closed_daily(primary_rows, daily_rows)` returns one timestamped daily join per primary row, or `UNKNOWN` before a closed daily bar exists. `join_closed_children(primary_rows, child_rows)` returns the ordered exact four 1H children, otherwise `UNKNOWN`.

`compute_features(rows, scale)` supports exactly `4H` and `1H`; every result exposes true range, ATR14, EMA27, normalized slope/displacement, efficiency, overlap density, and volatility percentile. `clip_unit` rejects non-finite values. `nearest_rank` uses one-based `ceil(p*n)`. `freeze_thresholds` returns S70, S50, D70, D50, E30, O70, per-feature valid counts, and a canonical SHA-256 population hash.
