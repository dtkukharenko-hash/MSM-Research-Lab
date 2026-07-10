# EXP-005 — Precursors Of Major Moves

## Verdict

`PRECURSOR_CANDIDATES_FOUND`

The experiment found one strong candidate precursor state in the available ADAUSDT 4H data:

- `STATE-A-LONG`: before a major LONG movement, the 30-bar window slopes down and price is below EMA27 and EMA200.
- `STATE-A-SHORT`: before a major SHORT movement, the 30-bar window slopes up and price is above EMA27 and EMA200.

This is only a precursor candidate. The movement starts are retrospective candidate boundaries, not live detection points.

## Data

- Source: `/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv`
- Available period: `2023-07-01 00:00 UTC` to `2026-07-01 00:00 UTC`
- Asset/timeframe: ADAUSDT 4H
- Indicators used: EMA27, EMA200

No claims are made about a complete calendar year 2023.

## Movement Selection

Major movements were selected retrospectively from closing-price turning regions:

- local close extrema were searched in a 120-bar neighborhood;
- adjacent candidate extrema were kept only after a meaningful separation;
- a movement was accepted when close-to-close change was at least 25%;
- the previous EXP-004 50 local cases were not used as boundaries.

This is candidate markup, not proof of natural market objects.

## 1. Number Of Major Movements

Found: 21 major movements.

- LONG: 12
- SHORT: 9

Artifacts:

- `artifacts/major_moves.csv`
- `artifacts/MAJOR_MOVE_PRECURSORS_OVERVIEW.pdf`

## 2. Start Confidence

- HIGH: 10
- MEDIUM: 9
- LOW: 2

LOW-confidence starts:

- `M13` LONG, `2025-02-28 04:00`, short 17-bar expansion after a sharp prior move.
- `M20` LONG, `2025-12-31 16:00`, weaker total return and shorter structure than the main high-confidence cases.

All starts are retrospective.

## 3. Repeating Features Before LONG

In the 30-bar real windows before LONG starts:

- prior 30-bar price slope was negative in 12/12 cases;
- price was below EMA27 in 12/12 cases;
- price was below EMA200 in 12/12 cases;
- range expansion appeared in 7/12 cases;
- compression appeared in only 1/12 cases;
- last-5-bar acceleration appeared in 6/12 cases.

Candidate neutral state:

`STATE-A-LONG`: a downward 30-bar context with price below both EMA27 and EMA200 before a later major LONG movement.

## 4. Repeating Features Before SHORT

In the 30-bar real windows before SHORT starts:

- prior 30-bar price slope was positive in 9/9 cases;
- price was above EMA27 in 9/9 cases;
- price was above EMA200 in 9/9 cases;
- range expansion appeared in 4/9 cases;
- compression appeared in only 1/9 cases;
- last-5-bar acceleration appeared in 3/9 cases.

Candidate neutral state:

`STATE-A-SHORT`: an upward 30-bar context with price above both EMA27 and EMA200 before a later major SHORT movement.

## 5. Mirrored Features

The clearest mirrored pattern is opposite-direction preconditioning:

- LONG starts followed windows where price had moved down and sat below EMA27/EMA200.
- SHORT starts followed windows where price had moved up and sat above EMA27/EMA200.

This suggests a reversal-style precursor candidate, not a continuation precursor.

## 6. Features Not Different From Control

Control set:

- 3 control windows per movement;
- same window lengths as the real windows;
- not within 20 bars before a major movement start;
- volatility-nearest matches where possible.

On 30-bar windows:

- LONG opposite 30-bar slope: real 12/12, control 19/36.
- SHORT opposite 30-bar slope: real 9/9, control 14/27.
- LONG price below EMA27: real 12/12, control 17/36.
- SHORT price above EMA27: real 9/9, control 17/27.
- LONG price below EMA200: real 12/12, control 22/36.
- SHORT price above EMA200: real 9/9, control 16/27.

Less useful features:

- compression was not a precursor candidate: real 2/21, control 18/63.
- local extreme update in the last 5 bars was not useful: real 0/21, control 11/63.
- failed continuation attempt was not useful: real 1/21, control 18/63.
- last-5-bar acceleration was mixed: real 9/21, control 34/63.

## 7. Stable Precursors

One stable candidate was found:

`STATE-A`: major movement starts tend to occur after the prior 30-bar window moved in the opposite direction and price was on the opposite side of EMA27 and EMA200.

No stable `STATE-B` or `STATE-C` is justified yet.

## 8. Cases That Do Not Fit

All 21 cases fit the broad `STATE-A` slope/EMA-side pattern on the 30-bar window.

However, `M13` and `M20` remain structurally weaker because their starts have LOW confidence. They should be reviewed separately before being used as clean examples.

## 9. Can We Formulate A Precursor Hypothesis?

Yes, but only as a candidate hypothesis:

Major ADAUSDT 4H movements in the available period often begin after a 30-bar opposite-direction state where price is positioned beyond EMA27 and EMA200 against the later movement direction.

This must not be treated as a signal, entry rule, or strategy.

## 10. Open Questions

- Does `STATE-A` remain visible if movement boundaries are chosen by an independent reviewer?
- Does the pattern hold on other assets and other periods?
- Is EMA200 adding information beyond EMA27, or are both simply describing the same prior directional state?
- Are LOW-confidence cases `M13` and `M20` part of the same phenomenon or separate edge cases?
- Which part matters more: prior slope, EMA side, or the combination?

## Artifacts

- `artifacts/major_moves.csv`
- `artifacts/precursor_windows.csv`
- `artifacts/MAJOR_MOVE_PRECURSORS.pine`
- `artifacts/MAJOR_MOVE_PRECURSORS_OVERVIEW.pdf`

## Constraints Check

- Irobot was used read-only.
- `docs/DEFINITIONS.md` was not changed.
- The MSM model was not changed.
- ZigZag was not used as proof.
- No trading strategy, entries, profit search, or parameter optimization was performed.
