# MSM Research Lab

MSM Research Lab is a research repository for the Multi Scale Market Model: a disciplined framework for studying market movement across multiple degrees of structure.

The project is not a collection of ready-made trading signals. It is a laboratory for formulating hypotheses, testing them causally, rejecting weak ideas, and preserving research history in a reproducible form.

## Core philosophy

1. Markets must be studied as multi-scale structure, not as isolated candles.
2. The basic objects are impulse, counter-impulse, correction, density, rejection, and degree.
3. A visual pattern is not an edge until it survives causal reproduction, controls, and out-of-sample validation.
4. ZigZag, EMA, pivots, density zones, and confirmation ladders are descriptive tools, not proof of predictability by themselves.
5. Every research note must be falsifiable: it must define what would count as failure.
6. Rejected hypotheses are first-class results. They protect the project from repeating attractive but false ideas.
7. The model must avoid lookahead, repainting, hindsight selection, and manual cherry-picking.
8. The project prioritizes causal market understanding over curve-fitted profitability.
9. When OHLC-derived structure fails, the next research path should search for non-OHLC sources of information: funding, open interest, liquidations, order flow, order book structure, long/short ratio, listings, unlocks, and narrative catalysts.

## Key definitions

### Impulse

A directional movement that creates displacement relative to the preceding local structure. An impulse can exist at different degrees: global, local, and micro-local.

### Counter-impulse

A movement against the current impulse. It may be a correction, reversal attempt, liquidity sweep, or transition into uncertainty.

### Density

A zone where price compresses or overlaps relative to a previous impulse/correction structure. Density is treated as uncertainty, not as an automatic entry signal.

### Rejection

A visible failure of price to accept a level, zone, or density area. Rejection must be tested causally and cannot be assumed predictive from charts alone.

### Degree

The scale of the market structure being described. A global degree can contain local impulses; a local impulse can contain smaller internal impulses.

## Repository structure

```text
MSM-Research-Lab/
├── README.md
├── PROJECT_INSTRUCTIONS.md
└── msm/
    ├── research/
    │   ├── INDEX.md
    │   ├── RN-007_CONFIRMATION_LADDER.md
    │   ├── H-007_CONFIRMATION_LADDER.md
    │   ├── RN-008_SAACLOUD_DENSITY_BREAKOUT/
    │   │   └── README.md
    │   └── RN-009_LIQUIDITY_SWEEP_DENSITY/
    │       └── README.md
    └── accelerator_research/
        └── AR-003/
            └── REPORT.md
```

## Current research status

| ID | Topic | Status |
|---|---|---|
| RN-007 | Confirmation Ladder | REJECT |
| H-007 | Confirmation Ladder hypothesis | REJECT |
| AR-003 | Confirmation ladders experiment | REJECT |
| RN-008 | SaaCloud Density Breakout | REJECT |
| RN-009 | Liquidity Sweep Density | REJECT / BLOCKED for liquidation-native version |

## Out of scope

The project does not include:

- discretionary chart predictions without causal testing;
- signal selling;
- claims of guaranteed profitability;
- repainting indicators as proof;
- manual selection of only successful chart examples;
- optimization without out-of-sample checks;
- strategies that cannot be reproduced from closed historical data.
