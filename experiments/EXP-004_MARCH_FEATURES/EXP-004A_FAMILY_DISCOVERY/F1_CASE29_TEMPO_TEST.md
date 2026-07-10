# F1 Case 29 — Tempo Candle Overlap Test

## Scope

This note continues only F1 case #29.

- Case: F1 #29
- Direction: DOWN
- Accepted technical retrospective window: 2023-08-02 00:00 — 2023-08-03 04:00 UTC
- The current end at 2023-08-03 04:00 UTC is treated here as a **technical retrospective boundary**, not as
  a confirmed movement end.
- No new markup boundary is created.
- No strategy rule is created.
- ZigZag is not used.

Observation being tested:

> During a downward movement, large DOWN candles set the tempo. If a subsequent UP move overlaps more than
> 50% of the body of the current tempo DOWN candle, this may indicate tempo violation.

## Tempo DOWN Candles

For this case, a possible tempo DOWN candle is a DOWN candle whose body is large relative to the previous
5 candle bodies. The check below uses the user observation as a visual test, not as a trading rule.

| timestamp UTC | open | close | body | vs previous 5 bodies | updated local low | continuation down after |
|---|---:|---:|---:|---:|---|---|
| 2023-08-02 00:00 | 0.3103 | 0.3072 | 0.0031 | 1.67x prev5 average | yes, first low of checked segment | yes |
| 2023-08-02 12:00 | 0.3078 | 0.3028 | 0.0050 | 2.03x prev5 average | yes | yes |
| 2023-08-03 04:00 | 0.2994 | 0.2953 | 0.0041 | 1.85x prev5 average | yes | yes |
| 2023-08-03 20:00 | 0.2953 | 0.2922 | 0.0031 | 2.54x prev5 average | yes | no clear continuation by close; later action tests the tempo |

The last active tempo candle before the key overlap checks is therefore:

- timestamp: 2023-08-03 20:00 UTC
- body: `0.2953 → 0.2922`
- body size: `0.0031`
- 50% body level: `0.29375`

## Overlap Definition

For a DOWN tempo candle:

- tempo body top = tempo open;
- tempo body bottom = tempo close;
- body size = `open - close`;
- 50% level = `close + 0.5 * body`.

Three overlap variants were checked:

1. **Wick/touch overlap**: UP candle high enters more than 50% into the DOWN tempo body.
2. **Close overlap**: UP candle close enters more than 50% into the DOWN tempo body.
3. **Body overlap**: UP candle body overlaps more than 50% of the DOWN tempo body.

`overlap_ratio = return depth into tempo body / tempo body size`.

## All `overlap_ratio > 0.5` Cases

| time UTC | active tempo candle | wick overlap | close overlap | body overlap | triggered variants | continued down after |
|---|---|---:|---:|---:|---|---|
| 2023-08-03 12:00 | 2023-08-03 04:00 | 0.610 | 0.220 | 0.098 | wick only | yes, later 2023-08-03 20:00 makes a new tempo DOWN candle |
| 2023-08-04 00:00 | 2023-08-03 20:00 | 0.613 | 0.516 | 0.516 | wick, close, body | partially: 2023-08-04 04:00 moves down, but does not restore a new low below the tempo low |
| 2023-08-04 08:00 | 2023-08-03 20:00 | 0.581 | 0.226 | 0.032 | wick only | no meaningful downside continuation before 2023-08-04 12:00 |
| 2023-08-04 12:00 | 2023-08-03 20:00 | 1.000 | 1.000 | 0.774 | wick, close, body | no clean restoration of prior down tempo; next candles stay choppy above the 2023-08-03 20:00 low |

## Why The First Similar Cases Did Not End The Movement

### 2023-08-03 12:00 UTC

This candle only triggers the wick/touch variant against the 2023-08-03 04:00 tempo candle.

- Wick overlap: 0.610
- Close overlap: 0.220
- Body overlap: 0.098

Why it did not end the move:

The body and close did not reclaim more than 50% of the tempo body. It was a wick probe, not a body/close
break of tempo. After it, the market produced a new large DOWN tempo candle at 2023-08-03 20:00.

### 2023-08-04 00:00 UTC

This candle triggers all three variants against the 2023-08-03 20:00 tempo candle.

- Wick overlap: 0.613
- Close overlap: 0.516
- Body overlap: 0.516

Why it did not fully end the move by itself:

It was the first real violation of the 2023-08-03 20:00 tempo body, but the next candle at 2023-08-04 04:00
was DOWN. That candle did not restore a fresh low below the 2023-08-03 20:00 tempo low, but it did make the
first violation ambiguous rather than final.

### 2023-08-04 08:00 UTC

This candle again triggers only the wick/touch variant.

- Wick overlap: 0.581
- Close overlap: 0.226
- Body overlap: 0.032

Why it did not fully end the move:

It did not close through the 50% level and its body barely entered the tempo candle. It is another probe,
not a decisive overlap.

## What Is Different About 2023-08-04 12:00 UTC

The 2023-08-04 12:00 candle differs from the earlier tests in three observable ways:

1. **All three overlap variants trigger strongly.**
   - Wick overlap: 1.000
   - Close overlap: 1.000
   - Body overlap: 0.774

2. **The close moves beyond the entire 2023-08-03 20:00 tempo body.**  
   The tempo candle body is `0.2953 → 0.2922`. The 2023-08-04 12:00 candle closes at `0.2958`, above the
   tempo candle open. That is stronger than merely touching or closing slightly past the 50% level.

3. **The UP candle itself is large relative to its local context.**  
   Its body is `0.0029`, about `2.16x` the average body of the previous 5 candles, with close near the high
   (`close_position_in_range = 0.857`).

So 2023-08-04 12:00 is not just another touch of the tempo candle. It is a broad body-and-close reclaim of
the active DOWN tempo candle.

## Interpretation

The technical retrospective end at 2023-08-03 04:00 is not sufficient as a confirmed movement ending under
the tempo-overlap observation. The stronger tempo violation appears later, especially at 2023-08-04 12:00.

This remains a visual research observation only. It is not an automatic detector, not a trading rule, and
not a change to the accepted F1 #29 markup.
