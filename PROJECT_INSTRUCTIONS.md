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
11. No research experiment may enter READY state before its required data pass the mandatory data-readiness preflight.
12. Data acquisition and data-readiness validation must be completed separately from hypothesis testing.

## Mandatory data-readiness preflight

Before creating or launching any research experiment, verify every required dataset for the exact frozen universe and interval. The preflight must finish before planner, implementer, auditor, or analytical code is allowed to spend time on the experiment.

The persisted readiness manifest must record, for every symbol and source kind:

- official source and endpoint or archive identity;
- requested half-open UTC interval;
- actual first and last timestamp;
- row count and expected row count where the cadence is fixed;
- schema and numeric validity;
- timestamp ordering, duplicates, gaps and off-grid rows;
- SHA-256 of the exact source bytes;
- explicit status: `READY`, `PARTIAL`, `MISSING`, or `INVALID`.

`DATA_READY=YES` is permitted only when every mandatory source is `READY` for the complete declared interval. A filename, directory, previous successful experiment, or recent modification time is not evidence of readiness.

If any mandatory source is absent, truncated, invalid or not independently verifiable:

1. stop the research experiment before expensive orchestration;
2. mark the research as `BLOCKED` by data readiness;
3. create a separate acquisition/repair task;
4. rerun the same preflight after acquisition;
5. launch the research only after the persisted manifest reports `DATA_READY=YES`.

No synthetic substitution, interpolation, forward filling, cross-symbol replacement or silent gap filling may turn failed readiness into `READY`.

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

Every experiment must also link to the exact data-readiness manifest used at launch and record its SHA-256.

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
