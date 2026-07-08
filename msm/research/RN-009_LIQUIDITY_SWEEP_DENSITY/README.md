# RN-009 Liquidity Sweep Density

**Status:** REJECT for fallback version; BLOCKED for liquidation-native version  
**Domain:** MSM / liquidity sweep / density / liquidations / order flow

## Research question

Can liquidity-sweep density identify market zones where a sweep leads to a useful directional impulse?

The intended native hypothesis required liquidation/orderbook/positioning data. Because historical data coverage was insufficient, a fallback version was tested.

## Hypothesis

Liquidity sweep density should identify zones where forced positioning, liquidation clusters, or orderbook imbalance create a better-than-random probability of impulse after a sweep.

## Data inventory problem

The liquidation-native version could not be tested honestly because required historical data was missing or insufficient.

Recorded project data inventory:

- open interest: only 4H;
- funding: 8H from 2023-09;
- liquidations: only about 11 days from 2026;
- historical liquidation/orderbook/long-short-ratio coverage: insufficient.

## Fallback test

A fallback version was tested using available proxy data. The fallback did not establish a robust edge.

## Result

The fallback version was rejected.

The liquidation-native version remains blocked because the correct data required to test the real hypothesis is not available in sufficient historical depth.

## Verdict

```text
Fallback version: REJECT
Liquidation-native version: BLOCKED
```

## Interpretation

The rejection of the fallback does not fully reject the deeper liquidity-native idea. It rejects only the proxy implementation that could be tested with available data.

The native version requires historical data that captures forced positioning directly:

- liquidation prints or liquidation heatmaps;
- orderbook depth and imbalance;
- long/short ratio;
- open interest changes at sufficient resolution;
- funding regimes;
- sweep events with causal timestamps.

## Next actions

1. Acquire historical liquidation data with enough depth.
2. Acquire orderbook or depth snapshots.
3. Acquire long/short ratio history.
4. Rebuild the hypothesis as a liquidation-native experiment.
5. Keep the fallback rejection separate from the blocked native hypothesis.

## Final status

```text
RN-009: REJECT / BLOCKED
```
