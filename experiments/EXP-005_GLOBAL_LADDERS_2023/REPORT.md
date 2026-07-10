# EXP-005 — Global ADA 2023 Ladders

## Verdict

`DATA_INSUFFICIENT`

Reason: the read-only Irobot 4H feature source found for ADA/USDT starts at `2023-07-01 00:00 UTC`. A full-year January-December 2023 global ladder claim cannot be made from this source alone. A retrospective candidate map was built for the available 2023 window, with the last candidate ladder extending into the January 2024 transition.

## Data Used

- Read-only source: `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv`
- Available ADA/USDT 4H window used: `2023-07-01 00:00 UTC` to `2024-01-08 00:00 UTC`
- Previous local sample: `experiments/EXP-004_MARCH_FEATURES/artifacts/exp004_movement_sample.csv`

The old 50 EXP-004 cases were not used to define global ladder boundaries. They were overlaid only after the candidate boundaries were selected.

## Candidate Ladders

| ladder_id | direction | start_time | end_time | bars | return | local cases | coverage |
|---|---:|---|---|---:|---:|---:|---:|
| L1 | UP | 2023-07-06 12:00 | 2023-07-14 00:00 | 46 | 27.9490% | 2 | 0.3478 |
| L2 | DOWN | 2023-07-14 00:00 | 2023-08-17 20:00 | 210 | -29.4297% | 8 | 0.2952 |
| L3 | UP | 2023-08-17 20:00 | 2023-10-02 08:00 | 274 | 4.6685% | 9 | 0.2628 |
| L4 | DOWN | 2023-10-02 08:00 | 2023-10-19 00:00 | 101 | -9.8201% | 1 | 0.0792 |
| L5 | UP | 2023-10-19 00:00 | 2023-11-16 08:00 | 171 | 63.3416% | 11 | 0.4737 |
| L6 | DOWN | 2023-11-16 08:00 | 2023-11-28 08:00 | 73 | -3.8422% | 4 | 0.4384 |
| L7 | UP | 2023-11-28 08:00 | 2024-01-08 00:00 | 245 | 25.4565% | 13 | 0.3878 |

Detailed rows are stored in `artifacts/global_ladders_2023.csv`.

## Is The Count Around 7?

For the available July-December 2023 window plus the January 2024 transition, the candidate map contains 7 large ladders. This supports the preliminary visual estimate only for the available window.

It does not prove that the full 2023 year contains exactly or approximately 7 ladders, because January-June 2023 were not available in the source used here.

## Coverage By The Old 50 Movements

The old local movements cover only slices of the candidate global ladders:

- L1: 34.78%
- L2: 29.52%
- L3: 26.28%
- L4: 7.92%
- L5: 47.37%
- L6: 43.84%
- L7: 38.78%

Two local cases are outside the candidate ladder map:

- case 47: `2023-07-02 20:00` to `2023-07-04 00:00`
- case 33: `2023-07-04 12:00` to `2023-07-05 12:00`

Both occur before the first accepted candidate ladder boundary in the available window.

## Position Of Old Local Movements

The 48 local movements that fall inside candidate ladders are distributed across starts, middles, and ends:

- L1: start 1, middle 0, end 1
- L2: start 3, middle 3, end 2
- L3: start 2, middle 4, end 3
- L4: start 0, middle 1, end 0
- L5: start 3, middle 5, end 3
- L6: start 1, middle 2, end 1
- L7: start 3, middle 9, end 1

The old sample is therefore not a clean sample of ladder starts, ladder middles, or ladder endings. It is a mixed local slice sample.

## Can The Old Sample Be Used Without Context?

No. The 50 local movements should not be used further as standalone global movements.

They can still be useful as local fragments, but every further analysis should attach each case to its enclosing global ladder or explicitly mark it as outside/ambiguous. Without that context, short local segments can be mistaken for complete movements.

## Artifacts

- `artifacts/global_ladders_2023.csv`
- `artifacts/GLOBAL_LADDERS_2023.pine`
- `artifacts/GLOBAL_LADDERS_2023_OVERVIEW.pdf`

## Notes

- The Pine script is fixed visual markup only.
- No live detection was implemented.
- No strategy or profit search was performed.
- ZigZag was not used as final proof of boundaries.
- `docs/DEFINITIONS.md` was not changed.
