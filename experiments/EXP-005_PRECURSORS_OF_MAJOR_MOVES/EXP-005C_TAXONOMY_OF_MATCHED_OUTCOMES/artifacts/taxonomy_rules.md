# EXP-005C Rule-Based Outcome Taxonomy

Rules are post-hoc interpretations of cluster profiles. They are not optimized for prediction and do not force every event into a class.

1. `DELAYED_MAJOR_MOVE`: `delayed_major_move_flag == 1`.
2. `WEAK_REVERSAL`: `signed_efficiency > 0.22` and `signed_close_return_atr > 1.0`.
3. `TREND_CONTINUATION`: `signed_efficiency < -0.12` or `signed_close_return_atr < -1.0`.
4. `RANGE_WHIPSAW`: `net_to_path_ratio < 0.12` and `return_sign_changes >= 8`.
5. `COMPRESSION`: `ATR_decay < 0.75` and `range_expansion_vs_pre_event < 0.85`.
6. Otherwise `UNCLASSIFIED`.
