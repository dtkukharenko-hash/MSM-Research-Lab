# EXP-020 — Parent representation transfer

Status: REPRESENTATION_TRANSFER_PARTIAL

## Scope and causal constraints

This is a representation audit, not a trading rule. Origins use only completed 4H bars ending strictly before the counter start; frozen 32-bar caps, two-bar confirmation, and 1.0 ATR origin threshold are imported unchanged from EXP-019. No pivots, future returns, outcome labels, or outcome-selected representation are used.

## Availability and reconstruction

ADAUSDT is the only committed complete local archive (3300 aggregated 4H bars with the committed 1H fallback). BTCUSDT, ETHUSDT, SOLUSDT, and XRPUSDT are explicitly `UNAVAILABLE`; no substitute data were used. The factor-1.0 ADA detector exactly identities all 425 committed EXP-014 BASE rows and the applicable EXP-019 measurement implementation.

## Results

`symbol_summary.csv` reports validity, invalid reasons, age quantiles/entropy, cap hits, origin disagreement, redundancy, and the availability limitation. `representation_transfer.csv` retains every valid and invalid row, fields for displacement, extension, efficiency, close location, boundary/extreme distance, slopes, minimum-history, cap and zero-denominator flags, and exhaustive chronological thirds. `distribution_comparison.csv` uses only fixed age and efficiency bins plus deterministic controls; cross-symbol distance/rank cells honestly state that one symbol cannot establish them. `parameter_stability.csv` is generated from actual factor 0.8, 1.0 and 1.2 detector runs.

## Verdict

**REPRESENTATION_TRANSFER_PARTIAL** — ADA reproduces the frozen representations and their non-degenerate alternatives, but core BTC/ETH coverage is unavailable. Therefore cross-symbol invariance, rank agreement, and stable transfer cannot be established. Descriptive controls are secondary evidence only and do not select a representation.
