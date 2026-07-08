# AR-003 Confirmation Ladders Report

**Status:** REJECT  
**Linked RN:** `msm/research/RN-007_CONFIRMATION_LADDER.md`  
**Linked H:** `msm/research/H-007_CONFIRMATION_LADDER.md`

## Objective

Test whether a causal confirmation ladder across timeframes provides useful structural confirmation relative to a 4H ZigZag reference.

This experiment was not designed as a direct trading strategy. It was designed to test causality, ordering, and lag.

## Configuration

```text
CONTEXT:   1D
REFERENCE: 4H ZigZag
CHAIN:     1H -> 15m -> 5m
ASSETS:    ADA, BTC, ETH
```

The experiment reused EMA27-slope ZigZag logic from `hms_zz.py::slope_pivots`.

## Causal rules

- Use only closed bars.
- Do not use future pivots.
- Do not repaint past state.
- Mark state as UNKNOWN where a causal decision is not possible.
- Measure lag against the reference structure.

## Recorded deliverables from project context

```text
msm/accelerator_research/AR-003/REPORT.md
msm/accelerator_research/AR-003/experiment_003.py
msm/accelerator_research/AR-003/confirmation_ladders.csv
msm/accelerator_research/AR-003/confirmation_metrics.csv
msm/accelerator_research/AR-003/null_model_comparison.csv
```

Only this Markdown report is currently committed. The Python and CSV artifacts are listed as known deliverables but are not reconstructed here because their raw file contents were not available.

## Result summary

The confirmation ladder failed as a validated component.

The ladder did not establish a robust early confirmation sequence. Its signal was too lagged relative to the reference ZigZag and did not provide enough improvement over simpler reference-state descriptions.

## Verdict

**REJECT**

AR-003 rejects H-007 in its tested form.

## Research implication

The result supports a stricter MSM rule: multi-timeframe visual agreement must be treated as descriptive until it survives causal timing and null-model tests.
