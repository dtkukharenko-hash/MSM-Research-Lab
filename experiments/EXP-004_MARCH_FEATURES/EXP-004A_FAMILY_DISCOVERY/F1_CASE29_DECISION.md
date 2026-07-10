# F1 Case 29 — Exit Selection Decision

## Scope

This note explains only the already accepted end candle for F1 case 29.

- case_id: 29
- start_time: 2023-08-02 00:00 UTC
- end_time: 2023-08-03 04:00 UTC
- direction: DOWN
- markup file unchanged: `artifacts/F1_MARKUP.pine`

No new boundaries, no new markup, no strategy logic, no ZigZag.

## Why The End Was Put On 2023-08-03 04:00

The end was selected by a combination of criteria, in this order of importance:

1. **It is the last down candle inside the accepted case window that closes near the lower side of its own range.**  
   The candle at 2023-08-03 04:00 is a DOWN body and closes at `0.2953`, near the low `0.2941`
   (`close_position_in_range = 0.2264`). This matches the recorded EXP-004A end pattern:
   `directional_edge_end`.

2. **It makes the final downside extension of the accepted movement window.**  
   Earlier down-edge candles were followed by later candles that pushed the movement lower. The 2023-08-03
   04:00 candle is the last such push in the already accepted 8-bar window.

3. **The next two candles stop extending down.**  
   After 2023-08-03 04:00, the next candles are UP bodies:
   - 2023-08-03 08:00: close `0.2958`
   - 2023-08-03 12:00: close `0.2962`

   Both closes are above the selected end close `0.2953`. This is the recorded `pause_or_reversal_after`
   condition.

So the decisive reason is not merely "a down candle near the low". It is the last down-edge candle in the
accepted movement window, followed by loss of downside continuation.

## Previous Candles That Met The Same Primary End-Candle Criterion

Primary end-candle criterion:

- body direction = DOWN;
- close near the lower part of the candle range (`close_position_in_range <= 0.30`).

Previous candles in the same accepted movement that met this primary criterion:

### 2023-08-02 00:00 UTC

- Direction: DOWN.
- Close: `0.3072`.
- Low: `0.3072`.
- `close_position_in_range = 0.0000`.

Why it was not chosen as the end:

The movement had just started. Later candles continued below it: 2023-08-02 04:00 closed at `0.3055`,
2023-08-02 12:00 closed at `0.3028`, and later candles pushed still lower. This candle satisfies the
end-candle shape, but it is not the last downside extension.

### 2023-08-02 04:00 UTC

- Direction: DOWN.
- Close: `0.3055`.
- Low: `0.3052`.
- `close_position_in_range = 0.1304`.

Why it was not chosen as the end:

The next candle pauses upward, but the accepted movement then resumes downward. 2023-08-02 12:00 closes at
`0.3028`, 2023-08-02 20:00 closes at `0.2992`, and 2023-08-03 04:00 closes at `0.2953`. Because lower closes
come later inside the same accepted window, this candle is an intermediate downside edge, not the end.

### 2023-08-02 12:00 UTC

- Direction: DOWN.
- Close: `0.3028`.
- Low: `0.3010`.
- `close_position_in_range = 0.2571`.

Why it was not chosen as the end:

It is followed by continued downside pressure inside the accepted movement. 2023-08-02 20:00 closes at
`0.2992`, and 2023-08-03 04:00 closes at `0.2953`. It satisfies the candle-shape criterion, but not the
"final downside extension before pause/reversal" criterion.

### 2023-08-02 20:00 UTC

- Direction: DOWN.
- Close: `0.2992`.
- Low: `0.2983`.
- `close_position_in_range = 0.2250`.

Why it was not chosen as the end:

The following candle at 2023-08-03 00:00 is a small UP pause, but the movement then makes one more lower
down-edge candle at 2023-08-03 04:00, closing at `0.2953`. Therefore 2023-08-02 20:00 is a pre-final pause
area, not the accepted end.

## Candles That Did Not Meet The Primary End-Candle Criterion

- 2023-08-02 08:00: UP body, not a DOWN end candle.
- 2023-08-02 16:00: DOWN body, but close is not near the lower side (`close_position_in_range = 0.6935`).
- 2023-08-03 00:00: UP body, not a DOWN end candle.

## Short Answer

The end was placed on 2023-08-03 04:00 because it is the last DOWN candle in the accepted case window that
closes near the lower side of its range, and the next two candles stop extending down. Earlier candles had
the same down-edge shape, but each was followed by lower closes later in the same accepted movement.
