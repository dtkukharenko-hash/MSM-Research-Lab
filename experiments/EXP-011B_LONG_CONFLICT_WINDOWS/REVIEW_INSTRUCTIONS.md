# EXP-011B R3 Episode Chain Review

Status: AWAITING_TW_EPISODE_CHAIN_REVIEW

## Workflow

1. Open Bybit ADAUSDT Perpetual Contract.
2. Select 4H.
3. Add your own EMA27 and EMA200.
4. Add `artifacts/LONG_DISPUTE_EPISODE_CHAINS_R3.pine`.
5. Select one R3 `LC` at a time.
6. Review the chain `D -> episode -> R -> possible F -> next episode -> final E -> C`.
7. Fill `artifacts/manual_episode_chain_review.csv`.

## Event Legend

- `D`: DISPUTE_START.
- `T`: CORE_TRIGGER.
- `R`: RECOVERY_ATTEMPT.
- `F`: FAILED_RECOVERY.
- `N`: NEW_CONFIGURATION_ATTEMPT.
- `X`: EMA27/EMA200 cross down.
- `E`: EFFECTIVE_EXIT.
- `C`: EXIT_CONFIRMATION.
- `O`: OPEN_AT_TRAIN_END.

## Check Each R3 LC

- Are internal episodes merged correctly?
- Was the section closed on a real exit rather than a local bounce?
- Are failed recoveries marked at the right return of dispute?
- Is dispute absent after `E` through `C`?
- Does the new clear state persist through `C`?
- Should this section merge with a neighboring LC?
- Should it split into separate sections?

## Do Not Analyze Yet

- Causes of later movement.
- Technical Ratings.
- Forecasts.
- Trading actions.
- Final conflict classification.

## Source Note

Automatic windows use EXP-011 Binance spot 4H OHLC. Manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so some candles and boundaries may differ by one or more bars.
