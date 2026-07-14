# EXP-012 R2 TradingView Review

Status: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

1. Open Bybit ADAUSDT Perpetual Contract on 4H.
2. Add `artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES_R2.pine`.
3. Select `PRIMARY_R2`, then optionally compare with `FIXED_BODY_BOUNDS_BASELINE`.
4. Review one zone at a time.
5. Fill `artifacts/manual_accepted_boundary_review.csv`.

Check whether body-based initial ranges match the visually accepted price area better than wick extremes, whether any single wick incorrectly moved a boundary, whether accepted extensions show repeated price acceptance, whether the January downside move is recognized as an accepted outside state, whether effective exit and causal confirmation are separated, and whether the fixed-bound baseline or accepted-extension primary better preserves the broad zone without swallowing the exit.

Do not analyze prediction, entries, exits, stops, forecasts, Technical Ratings, or PnL.
