# EXP-013 — Three-case common invariant

Status: PARTIAL_COMMON_INVARIANT

## Evidence recovery

The protected EXP-009A Pine was read byte-for-byte and not modified. It explicitly defines UTC 4H move windows, primary/secondary marks, and START_A/B/C states; within this task interval it supplies move 1 (2023-10-19 to 2023-12-13), move 2 start (2023-12-28), and the three move-1 detector times 2023-10-22 16:00, 2023-10-23 16:00, 2023-11-01 20:00. EXP-011B/EXP-012 independently recover three parent/conflict processes P001–P003. No original screenshots or 15m archive is present, so all cases are RECONSTRUCTED and 1H is the complete permitted child fallback.

## Formal cases

|Case|Status/confidence|Parent/counter/conflict/resolution|Direction|
|---|---|---|---|
|CASE_1|RECONSTRUCTED / 0.82|2023-10-19 00:00:00 / 2023-10-31 12:00:00 / 2023-11-01 00:00:00 / 2023-11-04 16:00:00|UP|
|CASE_2|RECONSTRUCTED / 0.88|2023-11-05 00:00:00 / 2023-11-12 16:00:00 / 2023-11-24 16:00:00 / 2023-12-06 16:00:00|UP|
|CASE_3|RECONSTRUCTED / 0.79|2023-12-06 16:00:00 / 2023-12-11 00:00:00 / 2023-12-27 00:00:00 / 2024-01-03 08:00:00|DOWN|

All cases use: parent invalidation = adverse extreme before resolution; counter boundary = adverse child extreme; balance bounds = observed trailing child range. Ordered state sequence is `ParentIntact -> ChildCounterMotion -> CounterProgressDecay -> BalanceOrOverlap -> FailedCounterExtension -> ParentReassertion`.

## Feature definitions

ATR displacement is signed close-to-close displacement divided by trailing 14-bar true-range mean. Directional efficiency is net/path distance. Boundary updates are same-direction child close advances. Overlap is adjacent-range intersection/current range. Alternation counts sign switches. Wick rejection is wick length per ATR. Close location is final close within the trailing four-bar range. Contraction is last-four/first-four mean range. Failed extension is a positive counter advance followed by a closed reversal. Reassertion is the final closed parent-direction displacement. Ratios compare child range/duration with parent window; ages are elapsed 4H bars. Every value is calculated from bars ending at its row.

## Candidate models and ablation

|Model|Result|Ablation|
|---|---|---|
|M1_COUNTER_PROGRESS_DECAY|descriptive contrast|not necessary in all three cases|
|M2_FAILED_COUNTER_EXTENSION|descriptive contrast|not necessary in all three cases|
|M3_CONFLICT_COMPRESSION|overlap|not necessary in all three cases|
|M4_PARENT_REASSERTION|descriptive contrast|retained|
|M5_COMBINED_RESOLUTION|descriptive contrast|not necessary in all three cases|
|M6_COUNTER_BALANCE_CONTINUATION|descriptive contrast|not necessary in all three cases|
|M7_RELATIVE_SCALE_TRANSITION|descriptive contrast|not necessary in all three cases|

Ablation removes progress-decay, failed-extension, and compression in turn. They improve the descriptive narration but do not survive as necessary common discriminators in this n=3 reconstruction. The smallest retained observable rule is therefore `ParentIntact -> BalanceOrOverlap -> ParentReassertion`; failed extension is a frequent confirmatory annotation, not a required trigger.

## Controls, stability, and detections

Three duration/direction/ATR-phase matched non-target controls were constructed chronologically. Their overlap with cases is material; direction is reported in `candidate_models.csv`, but no predictive or large-sample claim is made. Threshold factors 0.8, 1.0, and 1.2 retain all three reconstructed state sequences. `8` additional past-only candidates are listed as PLAUSIBLE_UNCERTAIN, not validations.

## Causal rule and limits

**Final formal state rule:** on a closed 4H bar, retain `ParentIntact` when its adverse boundary has not been closed through; after a trailing overlapping/contraction child range, emit `ParentReassertion` when the current close moves at least the configured ATR-normalized local-noise amount in the established parent direction. This is causal. The labels ‘failed extension’ and the full resolution narrative are post-confirmation descriptions when they require observing subsequent closes.

Limitations: cases are reconstructed, not screenshot-exact; child scale is 1H because no 15m local data exists; controls are only three; and the rule has descriptive rather than predictive separation.

## Verdict

**PARTIAL_COMMON_INVARIANT** — a common, closed-bar structural transition is confirmed descriptively, while matched-control discrimination and exact visual provenance remain weak.
