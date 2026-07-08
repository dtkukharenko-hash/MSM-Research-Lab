# PROJECT_INSTRUCTIONS.md

This document defines the operating rules for MSM Research Lab.

## Purpose

MSM Research Lab exists to study market structure with strict research discipline. The goal is not to defend an idea, but to determine whether an idea survives causal testing.

## Mandatory rules

1. No lookahead.
2. No repainting logic in final conclusions.
3. No using future pivots to make past decisions.
4. No manually selected examples as evidence of edge.
5. No optimization result is valid without out-of-sample validation.
6. Every hypothesis must have a rejection condition.
7. Every experiment must include a null/control model when possible.
8. Every reported edge must be tested against simple baselines.
9. Every result must record whether it is ACCEPT, REJECT, BLOCKED, or OPEN.
10. Rejected results must remain in the repository.

## Status vocabulary

### OPEN

The hypothesis is formulated but not yet tested.

### ACCEPT

The hypothesis survived the pre-defined criteria, out-of-sample checks, and relevant controls. ACCEPT does not mean production-ready.

### REJECT

The hypothesis failed the pre-defined criteria, failed controls, or did not show a robust edge.

### BLOCKED

The hypothesis cannot be tested honestly because required data, tooling, or methodology is missing.

## Required research format

Each research note should include:

- title;
- status;
- hypothesis;
- motivation;
- data used;
- causal constraints;
- method;
- baselines/null models;
- results;
- verdict;
- next actions.

## Required experiment format

Each accelerator/research experiment should include:

- experiment ID;
- linked RN/H documents;
- universe;
- timeframe;
- data sources;
- exact execution assumptions;
- metrics;
- controls;
- results;
- verdict;
- files produced.

## MSM concepts

### Multi-scale structure

Price movement is treated as nested structure. A global impulse may contain local impulses; local impulses may contain micro-impulses.

### Density

Density is a compression/overlap zone that may represent uncertainty, absorption, or delayed reaction. Density is not automatically predictive.

### Rejection

Rejection is a failed attempt to accept a level or zone. It is meaningful only if it can be detected causally and tested statistically.

### Confirmation ladder

A proposed chain where higher-timeframe context is followed by lower-timeframe confirmation. It must be measured for causality and lag, not assumed useful from visual alignment.

## Prohibited conclusions

Do not conclude that a signal works because:

- it looks good on a chart;
- it aligns with a known indicator;
- it works on one asset only;
- it works only before costs;
- it works only after removing failed examples;
- it depends on future pivots;
- it beats no null model.

## Research direction after rejected OHLC structure

If a structure derived only from OHLC data fails, the next path should consider non-OHLC data:

- funding;
- open interest;
- liquidations;
- order book imbalance;
- long/short ratio;
- listings;
- unlocks;
- narrative shocks;
- forced positioning and squeeze conditions.
