# EXP-004 — Batch Clustering Report

## Scope

Batch feature map for all 50 strong directional ADA/USDT 4H movements from EXP-004. Irobot/backtester was used read-only. ZigZag was not used as proof. No MSM definition is changed and no trading strategy is built.

Artifacts:

- `artifacts/all_50_features.csv`
- `artifacts/cluster_assignments.csv`
- `artifacts/contact_sheets/`

## Method

For each movement, one fixed feature set was computed for start, development, and ending. Numeric clustering used z-score normalized features and deterministic k-means with `k = 6`, constrained to the requested 5-8 group range. The normalized clustering inputs are stored as `norm_*` columns in `artifacts/all_50_features.csv`. Cluster names are numeric only.

Contact sheets use a fixed visual window of 28 bars per case: 10 bars before accepted start, then 18 bars from the accepted start. This covers the full selected movement because EXP-004 movements are 3-8 bars long, plus at least 10 post-start bars. Within each cluster sheet, panels share one relative price scale normalized to the accepted start open. Labels are limited to `case_id` and direction.

## Groups

| group | size | cases | avg duration | avg abs return % | start dir share | start body / prev10 | avg pullbacks | tempo change | end overlap | borderline |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 2 | 1, 3 | 8.00 | 27.63 | 0.90 | 2.58 | 1.00 | 0.78 | 2.38 | none |
| 2 | 1 | 2 | 8.00 | 26.21 | 0.60 | 4.35 | 1.00 | 9.53 | 9.57 | none |
| 3 | 16 | 4, 8, 9, 10, 15, 25, 26, 28, 29, 31, 35, 39, 40, 43, 45, 46 | 8.00 | 6.09 | 0.76 | 1.18 | 1.19 | 1.33 | 1.57 | 8, 29, 39 |
| 4 | 7 | 5, 6, 17, 18, 19, 20, 22 | 7.43 | 8.24 | 0.74 | 1.29 | 1.57 | 1.38 | 1.32 | none |
| 5 | 13 | 7, 14, 21, 23, 24, 27, 30, 32, 33, 34, 41, 47, 49 | 7.23 | 5.71 | 0.69 | 0.86 | 1.46 | 1.59 | 7.05 | 14, 21, 33 |
| 6 | 11 | 11, 12, 13, 16, 36, 37, 38, 42, 44, 48, 50 | 7.55 | 5.53 | 0.60 | 1.47 | 1.82 | 2.23 | 2.19 | none |

## Key Differences

- Group 1: larger net movement, directional first-five start, larger early bodies, tempo contracts later, strong post-end reference overlap. Cases: 1, 3.
- Group 2: larger net movement, mixed first-five start, larger early bodies, tempo expands later, strong post-end reference overlap. Cases: 2.
- Group 3: directional first-five start, tempo expands later, strong post-end reference overlap. Cases: 4, 8, 9, 10, 15, 25, 26, 28, 29, 31, 35, 39, 40, 43, 45, 46.
- Group 4: larger net movement, mixed first-five start, tempo expands later, strong post-end reference overlap. Cases: 5, 6, 17, 18, 19, 20, 22.
- Group 5: mixed first-five start, tempo expands later, strong post-end reference overlap. Cases: 7, 14, 21, 23, 24, 27, 30, 32, 33, 34, 41, 47, 49.
- Group 6: mixed first-five start, tempo expands later, strong post-end reference overlap. Cases: 11, 12, 13, 16, 36, 37, 38, 42, 44, 48, 50.

## Borderline Cases

#8, #14, #21, #29, #33, #39

These cases have a small distance margin to the next nearest centroid and should be visually reviewed before treating the group assignment as stable.

## Visual Stability

- Group 1: likely artificial or too small until visual review confirms it. Contact sheet: `artifacts/contact_sheets/cluster_01_contact_sheet.pdf`.
- Group 2: likely artificial or too small until visual review confirms it. Contact sheet: `artifacts/contact_sheets/cluster_02_contact_sheet.pdf`.
- Group 3: visually reviewable as a relatively stable batch group. Contact sheet: `artifacts/contact_sheets/cluster_03_contact_sheet.pdf`.
- Group 4: visually reviewable as a relatively stable batch group. Contact sheet: `artifacts/contact_sheets/cluster_04_contact_sheet.pdf`.
- Group 5: visually reviewable as a relatively stable batch group. Contact sheet: `artifacts/contact_sheets/cluster_05_contact_sheet.pdf`.
- Group 6: visually reviewable as a relatively stable batch group. Contact sheet: `artifacts/contact_sheets/cluster_06_contact_sheet.pdf`.

## Notes

- Grouping is a rough review map, not a model decision.
- Ending features are descriptive only and did not produce a universal ending rule.
- Cluster labels are numeric to avoid inventing semantic class names at this stage.
