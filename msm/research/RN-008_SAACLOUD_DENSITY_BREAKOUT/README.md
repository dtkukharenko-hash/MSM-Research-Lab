# RN-008 SaaCloud Density Breakout

**Status:** REJECT  
**Domain:** MSM / density / breakout / impulse / SaaCloud zones

## Research question

Does SaaCloud-style density identify zones from which breakouts produce a statistically useful impulse?

The tested idea was:

```text
density -> breakout -> impulse
```

## Motivation

Visually, price often appears to compress inside a cloud/density region and then break out into an impulse. The research question was whether this behavior is causal and statistically better than simple breakout logic.

## Hypothesis

A density zone should improve breakout quality. If the hypothesis is true, breakouts from density should show higher probability of positive follow-through and lower fake-breakout rate than simple Donchian or basic breakout references.

## Method summary

The experiment implemented a causal Python reproduction of the density-breakout logic.

The test compared density breakout behavior against:

- Donchian/simple breakout logic;
- random volume/direction control;
- compression variants;
- higher-timeframe filter variants.

## Key findings

The density breakout did not show a robust edge.

Recorded project result:

```text
P(ret > 0) for density breakout: approximately 0.42–0.49
```

This was not better than Donchian/simple breakout references.

Additional findings:

- random volume/direction control was equal to or better than density;
- compression worsened results;
- compression increased fake rate;
- higher-timeframe filter did not rescue the signal;
- SaaCloud zones behaved mostly like lagging SMA200 trend channels.

## Verdict

**REJECT**

The hypothesis `density -> breakout -> impulse` is rejected for the tested OHLC/SaaCloud implementation.

## Implications

1. SaaCloud density is not accepted as a predictive breakout source.
2. The visual appeal of density zones does not imply statistical edge.
3. If density is useful, it may need to be searched outside OHLC-derived cloud logic.
4. Future density research should prioritize non-OHLC data.

## Suggested next research direction

Search for density in non-OHLC sources:

- liquidations;
- order flow;
- order book structure;
- open interest clustering;
- funding extremes;
- long/short positioning;
- forced squeeze conditions.

## Final status

```text
RN-008: REJECT
```
