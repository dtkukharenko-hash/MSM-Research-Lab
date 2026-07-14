# EXP-012 R2 - ACCEPTED BOUNDARY STATE

Status: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

Goal: revise EXP-012 so horizontal disputed price zones use robust body-based boundaries and a strictly causal accepted-boundary state machine.

R2 separates wick `EXCURSION`, body/close-based `ACCEPTED_EXTENSION`, and persistent `ACCEPTED_EXIT`. EMA27 and EMA200 remain context/diagnostics only. There is no trading, prediction, PnL, or backtest claim.
