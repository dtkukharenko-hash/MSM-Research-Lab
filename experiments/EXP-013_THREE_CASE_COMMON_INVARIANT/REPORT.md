# EXP-013 — Three-case common invariant

Status: PARTIAL_COMMON_INVARIANT

## Technical-repair result

All values were regenerated from completed 4H bars rebuilt from the saved 1H ADAUSDT archive. The three reconstructed intervals, evidence confidence, direction, source boundaries, date window, candidate family M1–M7, and descriptive verdict are unchanged. No chart review, future pivot, or future-derived label is used.

## Computed common invariant

`ChildCounterMotion -> BalanceOrOverlap -> ParentReassertion` is the intersection of the computed state flags in all three case rows. Its closed-bar reassertion contrast is 1.008322 ATR for cases versus 0.878669 ATR for controls (n=3 each); this is descriptive only, not predictive evidence.

Counter displacement, progress, boundary updates, update sizes, intervals, last extreme, and failed extension are measured only from `counter_start` through the resolution bar in the documented counter direction. Parent age is elapsed bars from `parent_start` through resolution; the duration ratio is counter elapsed bars / parent elapsed bars. Parent-boundary preservation is computed from the stated EXP-012 invalidation boundary and every closed counter-phase bar.

## Cases and controls

|Case|Direction|Computed ordered sequence|
|---|---|---|
|CASE_1|UP|ChildCounterMotion -> BalanceOrOverlap -> ParentReassertion|
|CASE_2|UP|ChildCounterMotion -> CounterProgressDecay -> BalanceOrOverlap -> FailedCounterExtension -> ParentReassertion|
|CASE_3|DOWN|ChildCounterMotion -> CounterProgressDecay -> BalanceOrOverlap -> FailedCounterExtension -> ParentReassertion|

Controls are deterministic, non-overlapping with all editable target intervals, and have exact duration where feasible; otherwise `duration_mismatch_bars` reports the nearest feasible shortfall. No control is described as exactly duration-matched when it is not.

## Candidate models, stability, and detections

`candidate_models.csv` recomputes presence, contrast direction, and ablation outcome from its state flag. `parameter_stability.csv` reruns the same detector at 0.8x, 1.0x, and 1.2x and records observed target-row predicate presence and non-target detections. Detections are causal candidates only; they do not validate the rule.

## Verdict

**PARTIAL_COMMON_INVARIANT** — the computed common closed-bar transition is descriptive. Reconstructed provenance, the small control set, and weak discrimination preclude predictive or profitability claims.
