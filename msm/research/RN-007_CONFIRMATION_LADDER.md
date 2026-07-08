# RN-007 Confirmation Ladder

**Status:** REJECT  
**Linked hypothesis:** H-007_CONFIRMATION_LADDER  
**Linked experiment:** AR-003  
**Domain:** MSM / multi-timeframe confirmation / ZigZag / EMA slope pivots

## Research question

Can a multi-timeframe confirmation ladder provide a causal and useful confirmation sequence for market structure transitions?

The tested chain was:

```text
CONTEXT:   1D
REFERENCE: 4H ZigZag
CHAIN:     1H -> 15m -> 5m
```

The goal was not to prove profitability or define trading entries. The goal was to test whether the ladder of confirmations appears early enough and consistently enough to be useful compared with a reference ZigZag structure.

## Motivation

A visual multi-timeframe chart often appears to show that lower timeframes confirm a higher-timeframe move step by step. The MSM question was whether this visual sequence survives causal reconstruction:

- only closed bars;
- no future ZigZag pivots;
- no repainting;
- unknown states allowed where the model cannot know yet;
- explicit measurement of lag.

## Method

The experiment reused EMA27-slope ZigZag logic from `hms_zz.py::slope_pivots`.

Assets tested:

- ADA;
- BTC;
- ETH.

The chain tested whether the lower-timeframe sequence provides confirmation against the 4H reference structure.

## Causal constraints

The experiment enforced:

- closed bars only;
- no future pivots;
- no post-fact confirmation;
- UNKNOWN where causal state cannot be known;
- explicit lag measurement against the reference structure.

## Expected useful result

The confirmation ladder would be useful if it showed:

1. stable ordering across timeframes;
2. confirmation before or near the actionable phase of the reference move;
3. acceptable lag;
4. better information than simply observing the reference ZigZag/EMA state.

## Result

The confirmation ladder was rejected.

The ladder did not demonstrate a robust causal advantage. The confirmation sequence was too lagged relative to the reference structure and did not establish a reliable early signal.

## Verdict

**REJECT**

The confirmation ladder is not accepted as a predictive or decision-improving MSM component in its tested form.

## Implications

1. Visual multi-timeframe alignment is not enough.
2. Confirmation may arrive after the useful movement has already occurred.
3. A ladder can describe structure, but description is not edge.
4. Future work must compare any confirmation chain against simple baselines and null models.

## Deliverables recorded in project context

- `RN-007_CONFIRMATION_LADDER.md`
- `H-007_CONFIRMATION_LADDER.md`
- `msm/accelerator_research/AR-003/REPORT.md`
- `confirmation_ladders.csv`
- `confirmation_metrics.csv`
- `null_model_comparison.csv`
- `experiment_003.py`

Only the Markdown documents are reconstructed in this GitHub commit. The CSV and Python files are known deliverables from project context but were not available as raw file contents at commit time.
