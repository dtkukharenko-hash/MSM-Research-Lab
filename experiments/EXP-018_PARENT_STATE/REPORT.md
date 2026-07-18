# EXP-018 — Parent state

Status: PARENT_STATE_REJECTED

## Hypothesis

The causal state of the established parent movement immediately before `ChildCounterMotion` adds stable structural separation.

## Reconstruction and causal constraints

EXP-014's **425** factor-1.0 rows and EXP-015's **369** strict-boundary rows are independently reconstructed and identity-asserted. Each state timestamp is the last completed 4H parent bar strictly before counter start. No future pivots, returns, labels, or outcome-derived thresholds are used.

## Measurement audit

- parent_age_bars: finite=425/425 missing=0 q25/q50/q75=8.0/8.0/8.0; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_displacement_atr: finite=425/425 missing=0 q25/q50/q75=0.439521136555562/0.9621993127147773/1.6777178103315358; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_efficiency: finite=425/425 missing=0 q25/q50/q75=0.0636645962732918/0.13237639553429056/0.20795660036166236; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_extension_from_origin_atr: finite=425/425 missing=0 q25/q50/q75=1.2046976182636413/1.7458202388435005/2.468228085779227; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_close_location: finite=425/425 missing=0 q25/q50/q75=0.5919282511210746/0.7335958005249341/0.8480392156862747; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_recent_slope_atr: finite=425/425 missing=0 q25/q50/q75=-0.025772009756546574/0.15792706762718475/0.3290633446938541; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_slope_change_atr: finite=425/425 missing=0 q25/q50/q75=-0.2796196350552571/0.018039784166866024/0.31068885872800495; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_range_expansion_ratio: finite=425/425 missing=0 q25/q50/q75=0.7747440273037548/1.0192307692307672/1.333333333333338; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_body_efficiency: finite=425/425 missing=0 q25/q50/q75=-0.12446351931330538/0.5/0.8529411764705888; UP=192 DOWN=233; thirds=[142, 142, 141]
- distance_to_parent_boundary_atr: finite=425/425 missing=0 q25/q50/q75=1.2979885440255827/1.7682548632647321/2.6083018867924515; UP=192 DOWN=233; thirds=[142, 142, 141]
- distance_from_parent_extreme_atr: finite=425/425 missing=0 q25/q50/q75=0.37266924767186155/0.6611146043193172/1.1011328285496305; UP=192 DOWN=233; thirds=[142, 142, 141]
- parent_maturity_fraction: finite=425/425 missing=0 q25/q50/q75=1.0/1.0/1.0; UP=192 DOWN=233; thirds=[142, 142, 141]

Pairwise Spearman rank correlations (finite paired rows; tied ranks averaged): parent_age_bars/parent_displacement_atr=undefined; parent_age_bars/parent_efficiency=undefined; parent_age_bars/parent_extension_from_origin_atr=undefined; parent_age_bars/parent_close_location=undefined; parent_age_bars/parent_recent_slope_atr=undefined; parent_age_bars/parent_slope_change_atr=undefined; parent_age_bars/parent_range_expansion_ratio=undefined; parent_age_bars/parent_body_efficiency=undefined; parent_age_bars/distance_to_parent_boundary_atr=undefined; parent_age_bars/distance_from_parent_extreme_atr=undefined; parent_age_bars/parent_maturity_fraction=undefined; parent_displacement_atr/parent_efficiency=0.958; parent_displacement_atr/parent_extension_from_origin_atr=0.806; parent_displacement_atr/parent_close_location=0.503; parent_displacement_atr/parent_recent_slope_atr=0.417; parent_displacement_atr/parent_slope_change_atr=0.007; parent_displacement_atr/parent_range_expansion_ratio=0.121; parent_displacement_atr/parent_body_efficiency=0.297; parent_displacement_atr/distance_to_parent_boundary_atr=0.817; parent_displacement_atr/distance_from_parent_extreme_atr=-0.122; parent_displacement_atr/parent_maturity_fraction=undefined; parent_efficiency/parent_extension_from_origin_atr=0.698; parent_efficiency/parent_close_location=0.556; parent_efficiency/parent_recent_slope_atr=0.412; parent_efficiency/parent_slope_change_atr=0.014; parent_efficiency/parent_range_expansion_ratio=0.094; parent_efficiency/parent_body_efficiency=0.334; parent_efficiency/distance_to_parent_boundary_atr=0.720; parent_efficiency/distance_from_parent_extreme_atr=-0.244; parent_efficiency/parent_maturity_fraction=undefined; parent_extension_from_origin_atr/parent_close_location=-0.003; parent_extension_from_origin_atr/parent_recent_slope_atr=0.115; parent_extension_from_origin_atr/parent_slope_change_atr=-0.200; parent_extension_from_origin_atr/parent_range_expansion_ratio=0.148; parent_extension_from_origin_atr/parent_body_efficiency=-0.023; parent_extension_from_origin_atr/distance_to_parent_boundary_atr=0.640; parent_extension_from_origin_atr/distance_from_parent_extreme_atr=0.415; parent_extension_from_origin_atr/parent_maturity_fraction=undefined; parent_close_location/parent_recent_slope_atr=0.654; parent_close_location/parent_slope_change_atr=0.383; parent_close_location/parent_range_expansion_ratio=0.016; parent_close_location/parent_body_efficiency=0.620; parent_close_location/distance_to_parent_boundary_atr=0.613; parent_close_location/distance_from_parent_extreme_atr=-0.852; parent_close_location/parent_maturity_fraction=undefined; parent_recent_slope_atr/parent_slope_change_atr=0.823; parent_recent_slope_atr/parent_range_expansion_ratio=0.349; parent_recent_slope_atr/parent_body_efficiency=0.857; parent_recent_slope_atr/distance_to_parent_boundary_atr=0.559; parent_recent_slope_atr/distance_from_parent_extreme_atr=-0.474; parent_recent_slope_atr/parent_maturity_fraction=undefined; parent_slope_change_atr/parent_range_expansion_ratio=0.357; parent_slope_change_atr/parent_body_efficiency=0.731; parent_slope_change_atr/distance_to_parent_boundary_atr=0.162; parent_slope_change_atr/distance_from_parent_extreme_atr=-0.386; parent_slope_change_atr/parent_maturity_fraction=undefined; parent_range_expansion_ratio/parent_body_efficiency=0.204; parent_range_expansion_ratio/distance_to_parent_boundary_atr=0.120; parent_range_expansion_ratio/distance_from_parent_extreme_atr=0.045; parent_range_expansion_ratio/parent_maturity_fraction=undefined; parent_body_efficiency/distance_to_parent_boundary_atr=0.392; parent_body_efficiency/distance_from_parent_extreme_atr=-0.529; parent_body_efficiency/parent_maturity_fraction=undefined; distance_to_parent_boundary_atr/distance_from_parent_extreme_atr=-0.149; distance_to_parent_boundary_atr/parent_maturity_fraction=undefined; distance_from_parent_extreme_atr/parent_maturity_fraction=undefined.\n\nThe committed detector supplies an eight-bar executable parent window: age and maturity are mechanically fixed and explicitly flagged; zero or missing denominators remain invalid rather than imputed. `parent_state.csv` records all invalidity and redundancy flags.

## States, controls, and stability

All required fixed families, source quartiles, and five joint states are in `state_comparison.csv`. Controls are deterministic, source-excluded, non-overlapping with every detected source interval, and disclose direction, duration, ATR, range, and time mismatches. Equal-support BASE and boundary subsets, exhaustive chronological thirds, and actual 0.8/1.0/1.2 detector runs with factor-specific contrasts are recorded.

## Verdict

**PARENT_STATE_REJECTED** — the largest equal-support contrast change is EXTENDED_NEAR_EXTREME (0.052632); it is not promoted because support, direction/time cells, factor rows, and boundary/redundancy disclosures do not establish stable independent separation. This is descriptive structural evaluation only.

## Files produced

All seven CSV files and this report regenerate deterministically from `experiment_018.py`.
