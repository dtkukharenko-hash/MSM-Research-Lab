# EXP-034A2R1 protocol

Status: infrastructure conformance only. This package uses deterministic synthetic rows only. Inputs are strictly increasing UTC bar opens and finite valid OHLC values; malformed inputs raise `ValueError`, while causal history that is not yet available is `UNKNOWN`.

Daily values close at `d+24h`; a 4H bar emits at `t+4h`. Children require the exact four opens in `[t,t+4h)`. ATR14 is a trailing simple mean, EMA27 is seeded from the first 27 closes then uses alpha `2/28`. The fixed 4H windows are 3/12/6 and 1H windows are 6/24/12 for slope, displacement/efficiency, and overlap pairs respectively. Volatility percentile uses 96 earlier ATR values only.

Thresholds are nearest-rank values over a supplied development feature prefix. The future-isolation test separately appends and mutates future rows, then freezes only the original prefix.
