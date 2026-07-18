# EXP-016 — Balance quality gate

Status: BALANCE_QUALITY_PARTIAL

## Hypothesis

Closed-bar quality of the detector-defined `BalanceOrOverlap` phase adds structural information beyond EXP-015 boundary preservation for ADAUSDT.

## Data, reconstruction, and causal definitions

The committed EXP-014 population is reconstructed exactly (425 rows), then the committed EXP-015 `BOUNDARY_THROUGH_REASSERTION` predicate is independently rebuilt and asserted against `gated_detections.csv` (369 rows). The balance phase is the detector's penultimate completed 4H child bar; hence duration is mechanically one in this fixed transition and adjacent-range overlap is deterministic self-IoU 1.0. Range/body use only that bar; compression uses the three preceding completed counter bars; drift and boundary change use its open/close and the pre-existing direction-aware boundary; setup distance is measured at balance close. No outcome or future bar enters membership.

## Measurement audit

- balance_duration_bars: missing=0 finite=369/369 q25/50/75=1.000000/1.000000/1.000000
- balance_range_atr: missing=0 finite=369/369 q25/50/75=0.700000/0.892786/1.168120
- balance_body_atr: missing=0 finite=369/369 q25/50/75=0.156761/0.348421/0.604224
- overlap_ratio: missing=0 finite=369/369 q25/50/75=1.000000/1.000000/1.000000
- compression_ratio: missing=0 finite=369/369 q25/50/75=0.416025/0.566265/0.812903
- directional_drift_atr: missing=0 finite=369/369 q25/50/75=-0.403150/-0.098505/0.238298
- boundary_distance_change_atr: missing=0 finite=369/369 q25/50/75=-0.403150/-0.098505/0.238298
- reassertion_setup_distance_atr: missing=0 finite=369/369 q25/50/75=-2.851852/-2.080734/-1.281356

Direction and exhaustive chronological-third splits are in `time_segment_summary.csv`. Pairwise Spearman rank correlations: balance_duration_bars~balance_range_atr=0.070, balance_duration_bars~balance_body_atr=0.049, balance_duration_bars~overlap_ratio=1.000, balance_duration_bars~compression_ratio=0.050, balance_duration_bars~directional_drift_atr=0.059, balance_duration_bars~boundary_distance_change_atr=0.059, balance_duration_bars~reassertion_setup_distance_atr=-0.061, balance_range_atr~balance_body_atr=0.616, balance_range_atr~overlap_ratio=0.070, balance_range_atr~compression_ratio=0.699, balance_range_atr~directional_drift_atr=-0.100, balance_range_atr~boundary_distance_change_atr=-0.100, balance_range_atr~reassertion_setup_distance_atr=0.036, balance_body_atr~overlap_ratio=0.049, balance_body_atr~compression_ratio=0.492, balance_body_atr~directional_drift_atr=-0.172, balance_body_atr~boundary_distance_change_atr=-0.172, balance_body_atr~reassertion_setup_distance_atr=0.016, overlap_ratio~compression_ratio=0.050, overlap_ratio~directional_drift_atr=0.059, overlap_ratio~boundary_distance_change_atr=0.059, overlap_ratio~reassertion_setup_distance_atr=-0.061, compression_ratio~directional_drift_atr=-0.011, compression_ratio~boundary_distance_change_atr=-0.011, compression_ratio~reassertion_setup_distance_atr=0.043, directional_drift_atr~boundary_distance_change_atr=1.000, directional_drift_atr~reassertion_setup_distance_atr=-0.305, boundary_distance_change_atr~reassertion_setup_distance_atr=-0.305. Duration and overlap are mechanically redundant under this committed fixed-length detector representation; they are retained rather than hidden.

## Gates, controls, and stability

All predeclared families and fixed thresholds are evaluated independently in `quality_comparison.csv`, including quality-only original-BASE support, boundary-plus-quality support, and deterministic support-size boundary controls. Controls are same-archive, deterministic, non-overlapping with every source detection, and disclose every residual mismatch in `matched_controls.csv`. Actual factor runs 0.8, 1.0, and 1.2 are in `threshold_stability.csv`. The largest fixed-factor contrast change is RANGE_COMPRESSION_050 (0.005420); it is not selected as a gate.

## Results and verdict

**BALANCE_QUALITY_PARTIAL** — no predeclared quality gate demonstrates robust independent separation beyond boundary preservation: mechanically fixed duration/overlap cannot discriminate, and remaining apparent differences fail the predeclared support-size, direction/time, or factor-stability checks recorded in the CSVs. This is descriptive structural evaluation only.

## Files produced

The seven CSV outputs and this report are regenerated deterministically by `experiment_016.py`.
