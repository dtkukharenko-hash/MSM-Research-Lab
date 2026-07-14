# EXP-012 R4 TradingView Review

Status: AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW

1. Open Bybit ADAUSDT Perpetual Contract on 4H.
2. Add `artifacts/LONG_CONTEXT_CAUSAL_PARENT_STATE_MACHINE_R4.pine`.
3. Review parent boxes, optional internal phases, joint candidates, failed joints, retries, and accepted extensions.
4. Fill `artifacts/manual_causal_parent_review.csv`.

Check whether each parent box is one broad accepted price process, whether internal phases are reasonable, whether failed joint candidates leave the parent active, whether later candidates after failed joints are visible, and whether Binance spot versus Bybit perpetual differences could explain boundary mismatch.

Do not assess prediction or trading value.
