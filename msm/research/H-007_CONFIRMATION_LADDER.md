# H-007 Confirmation Ladder

**Status:** REJECT  
**Linked research note:** RN-007_CONFIRMATION_LADDER  
**Linked experiment:** AR-003

## Hypothesis

A causal multi-timeframe confirmation ladder can confirm market structure transitions in a useful sequence:

```text
1D context -> 4H reference ZigZag -> 1H -> 15m -> 5m confirmation
```

The expected value of the ladder is not necessarily direct profitability, but a measurable reduction in structural uncertainty and a confirmation sequence that arrives early enough to be actionable.

## Null hypothesis

The apparent confirmation ladder is mostly a lagging description of already visible price movement. It does not provide useful information beyond the reference structure and simple trend/pivot baselines.

## Test requirements

To accept the hypothesis, the ladder must show:

1. causal availability on closed bars;
2. stable confirmation order;
3. acceptable lag relative to 4H reference structure;
4. better information than simple baselines;
5. robustness across ADA, BTC, and ETH.

## Failure conditions

Reject the hypothesis if:

- the ladder confirms too late;
- the order is unstable;
- UNKNOWN states dominate practical use;
- the ladder only restates the reference trend;
- the result does not survive null/baseline comparison.

## Result

The hypothesis failed.

The confirmation sequence did not provide a sufficiently early or robust causal improvement over the reference structure.

## Verdict

**REJECT**

The tested confirmation ladder should not be used as a validated MSM component.

## Notes

The rejection does not mean multi-timeframe context is useless. It means this specific ladder, with this causal construction and this reference, did not demonstrate enough value to be accepted.
