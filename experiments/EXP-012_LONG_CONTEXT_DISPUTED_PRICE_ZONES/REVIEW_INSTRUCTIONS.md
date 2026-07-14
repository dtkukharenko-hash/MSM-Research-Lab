# EXP-012 TradingView Review

Status: AWAITING_TW_PRICE_ZONE_REVIEW

1. Open Bybit ADAUSDT Perpetual Contract on 4H.
2. Add your own EMA27 and EMA200 if desired.
3. Add `artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES.pine`.
4. Review one zone at a time.
5. Fill `artifacts/manual_zone_review.csv`.

Check whether the yellow box represents one accepted horizontal price area, whether repeated EMA27 crossings remain inside the same zone, whether failed breakouts correctly expand the boundary, and whether the zone ends at the first accepted outside move. The cyan confirmation area should be visually separate from the yellow disputed zone.

For the December-January zone, specifically check whether it ends at the accepted break of the lower horizontal boundary rather than at a later EMA confirmation.

Do not analyze Technical Ratings, forecasts, entries, exits, stops, or PnL.
