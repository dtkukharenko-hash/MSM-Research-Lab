#!/usr/bin/env python3
"""EXP-009: causal movement age and one-entry state machine.

The script evaluates three fixed start detectors against EXP-008 reference
labels. It does not calculate PnL, does not use stop/exit logic, and does not
load data after 2024-12-31.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-009_CAUSAL_MOVE_AGE"
OUT = EXP / "artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")
EXP008 = ROOT / "experiments/EXP-008_MAJOR_MOVE_ENTRY_LABELING/artifacts"
EXP007_SIGNALS = ROOT / "experiments/EXP-007_TREND_ALIGNED_ENTRY/artifacts/all_entry_signals.csv"

START = pd.Timestamp("2023-07-01 00:00")
END = pd.Timestamp("2024-12-31 23:59")
FORBIDDEN = pd.Timestamp("2025-01-01 00:00")

DETECTORS = ["START_A", "START_B", "START_C"]
EARLY_ZONES = {"ZONE_1_BIRTH", "ZONE_2_FIRST_PULLBACK", "ZONE_3_EARLY_CONTINUATION"}
LATE_ZONES = {"ZONE_4_MATURE_MOVE", "ZONE_5_LATE_MOVE", "ZONE_6_EXHAUSTION_OR_CHOP"}


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df.sort_values("dt")
    df = df[(df["dt"] >= START) & (df["dt"] <= END)].copy().reset_index(drop=True)
    if df.empty or df["dt"].max() >= FORBIDDEN:
        raise RuntimeError("EXP-009 data window is empty or includes forbidden data.")
    prev_close = df["close"].shift(1).fillna(df["close"])
    df["tr"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(float),
            (df["high"] - prev_close).abs().to_numpy(float),
            (df["low"] - prev_close).abs().to_numpy(float),
        ]
    )
    df["body"] = (df["close"] - df["open"]).abs()
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["atr14"] = df["tr"].rolling(14, min_periods=1).mean()
    df["ema27_slope_5"] = df["ema27"] - df["ema27"].shift(5)
    df["ema27_slope_10"] = df["ema27"] - df["ema27"].shift(10)
    df["body_median_10"] = df["body"].rolling(10, min_periods=1).median().shift(1)
    df["high20_prev"] = df["high"].shift(1).rolling(20, min_periods=20).max()
    df["low20_prev"] = df["low"].shift(1).rolling(20, min_periods=20).min()
    df["high10_prev"] = df["high"].shift(1).rolling(10, min_periods=10).max()
    df["low10_prev"] = df["low"].shift(1).rolling(10, min_periods=10).min()
    df["range10_prev"] = df["high"].shift(1).rolling(10, min_periods=10).max() - df["low"].shift(1).rolling(10, min_periods=10).min()
    df["range20_before10"] = df["high"].shift(11).rolling(20, min_periods=20).max() - df["low"].shift(11).rolling(20, min_periods=20).min()
    df["move3_atr"] = (df["close"] - df["close"].shift(3)).abs() / df["atr14"].replace(0, np.nan)
    long_state = (df["ema27"] > df["ema200"]) & (df["close"] > df["ema200"]) & (df["ema27_slope_5"] > 0) & (df["ema27_slope_10"] >= 0)
    short_state = (df["ema27"] < df["ema200"]) & (df["close"] < df["ema200"]) & (df["ema27_slope_5"] < 0) & (df["ema27_slope_10"] <= 0)
    df["causal_state"] = np.where(long_state, "LONG_STATE", np.where(short_state, "SHORT_STATE", "NEUTRAL_STATE"))
    return df


def load_reference() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    moves = pd.read_csv(EXP008 / "major_moves.csv")
    zones = pd.read_csv(EXP008 / "move_zones.csv")
    approved = pd.read_csv(EXP008 / "approved_entries.csv")
    blocked = pd.read_csv(EXP008 / "blocked_entries.csv")
    exp007 = pd.read_csv(EXP008 / "exp007_signals_mapped_to_moves.csv")
    for frame, cols in [
        (moves, ["start_time", "end_time"]),
        (zones, ["start_time", "end_time"]),
        (approved, ["signal_time"]),
        (blocked, ["timestamp"]),
        (exp007, ["entry_time", "signal_time"]),
    ]:
        for col in cols:
            frame[col] = pd.to_datetime(frame[col])
    return moves, zones, approved, blocked, exp007


def side(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def directed_state(direction: str) -> str:
    return "LONG_STATE" if direction == "LONG" else "SHORT_STATE"


def detector_direction(df: pd.DataFrame, i: int, detector: str) -> str | None:
    for direction in ("LONG", "SHORT"):
        if detector_fires(df, i, detector, direction):
            return direction
    return None


def detector_fires(df: pd.DataFrame, i: int, detector: str, direction: str) -> bool:
    if i < 30:
        return False
    state = directed_state(direction)
    s = side(direction)
    row = df.loc[i]
    if detector == "START_A":
        return bool(row["causal_state"] == state and df.loc[i - 1, "causal_state"] == state and df.loc[i - 2, "causal_state"] != state)
    if detector == "START_B":
        in_state = row["causal_state"] == state
        if not in_state:
            return False
        if direction == "LONG":
            breakout = row["close"] > row["high20_prev"]
        else:
            breakout = row["close"] < row["low20_prev"]
        if not bool(breakout):
            return False
        body_limit = row["body"] <= 1.5 * row["body_median_10"] if row["body_median_10"] > 0 else False
        prev_big = df.loc[i - 1, "body"] > 1.5 * df.loc[i - 1, "body_median_10"] if df.loc[i - 1, "body_median_10"] > 0 else False
        confirms_prev = s * (row["close"] - df.loc[i - 1, "close"]) > 0
        near_ema = abs(row["close"] - row["ema27"]) <= 2 * row["atr14"]
        return bool((body_limit or (prev_big and confirms_prev)) and near_ema)
    if detector == "START_C":
        in_state = row["causal_state"] == state
        if not in_state:
            return False
        compressed = row["range10_prev"] < row["range20_before10"]
        if direction == "LONG":
            breaks_range = row["close"] > row["high10_prev"]
            slope_accel = row["ema27_slope_5"] > df.loc[i - 5, "ema27_slope_5"]
        else:
            breaks_range = row["close"] < row["low10_prev"]
            slope_accel = row["ema27_slope_5"] < df.loc[i - 5, "ema27_slope_5"]
        return bool(compressed and breaks_range and slope_accel)
    raise ValueError(detector)


def end_reason(df: pd.DataFrame, i: int, active: dict[str, object]) -> str | None:
    direction = str(active["direction"])
    s = side(direction)
    row = df.loc[i]
    if direction == "LONG":
        if row["ema27"] < row["ema200"] and row["close"] < row["ema200"]:
            return "END_A"
        if i >= 2 and (df.loc[i - 2 : i, "close"] < df.loc[i - 2 : i, "ema27"]).all() and row["ema27_slope_5"] <= 0:
            return "END_B"
    else:
        if row["ema27"] > row["ema200"] and row["close"] > row["ema200"]:
            return "END_A"
        if i >= 2 and (df.loc[i - 2 : i, "close"] > df.loc[i - 2 : i, "ema27"]).all() and row["ema27_slope_5"] >= 0:
            return "END_B"
    if int(active["age"]) > 120 and i - int(active["last_extreme_i"]) > 30:
        return "END_C"
    return None


def update_extreme(df: pd.DataFrame, i: int, active: dict[str, object]) -> None:
    direction = str(active["direction"])
    if direction == "LONG":
        if df.loc[i, "high"] > float(active["best_extreme"]):
            active["best_extreme"] = float(df.loc[i, "high"])
            active["last_extreme_i"] = i
            active["pulled_back_to_ema27"] = False
    else:
        if df.loc[i, "low"] < float(active["best_extreme"]):
            active["best_extreme"] = float(df.loc[i, "low"])
            active["last_extreme_i"] = i
            active["pulled_back_to_ema27"] = False


def update_pullback(df: pd.DataFrame, i: int, active: dict[str, object]) -> None:
    direction = str(active["direction"])
    if direction == "LONG" and df.loc[i, "low"] <= df.loc[i, "ema27"]:
        active["pulled_back_to_ema27"] = True
        active["pullback_i"] = i
    if direction == "SHORT" and df.loc[i, "high"] >= df.loc[i, "ema27"]:
        active["pulled_back_to_ema27"] = True
        active["pullback_i"] = i


def move_distance_atr(df: pd.DataFrame, i: int, active: dict[str, object]) -> float:
    atr = float(df.loc[i, "atr14"])
    if atr <= 0:
        return np.nan
    return side(str(active["direction"])) * (float(df.loc[i, "close"]) - float(active["start_price"])) / atr


def primary_candidate(df: pd.DataFrame, i: int, active: dict[str, object]) -> bool:
    age = int(active["age"])
    dist = move_distance_atr(df, i, active)
    row = df.loc[i]
    if not (1 <= age <= 12 and dist <= 3 and not bool(active["primary_used"])):
        return False
    if abs(row["close"] - row["ema27"]) > 1.5 * row["atr14"]:
        return False
    if row["body_median_10"] <= 0 or row["body"] > 1.5 * row["body_median_10"]:
        return False
    if i >= 3:
        directed_3 = side(str(active["direction"])) * (row["close"] - df.loc[i - 3, "close"]) / row["atr14"]
        if directed_3 > 1.5:
            return False
    return True


def secondary_candidate(df: pd.DataFrame, i: int, active: dict[str, object]) -> bool:
    age = int(active["age"])
    dist = move_distance_atr(df, i, active)
    direction = str(active["direction"])
    s = side(direction)
    if not (4 <= age <= 30 and dist <= 5 and bool(active["primary_used"]) and not bool(active["secondary_used"])):
        return False
    if not bool(active["pulled_back_to_ema27"]):
        return False
    pullback_i = int(active.get("pullback_i", i))
    if direction == "LONG":
        closed_back = df.loc[i, "close"] > df.loc[i, "ema27"]
        local_extreme = df.loc[i, "close"] > df.loc[max(pullback_i, i - 5) : i - 1, "high"].max() if i > pullback_i else False
    else:
        closed_back = df.loc[i, "close"] < df.loc[i, "ema27"]
        local_extreme = df.loc[i, "close"] < df.loc[max(pullback_i, i - 5) : i - 1, "low"].min() if i > pullback_i else False
    continuation = s * (df.loc[i, "close"] - df.loc[i - 1, "close"]) > 0
    return bool(closed_back and local_extreme and continuation)


def run_detector(df: pd.DataFrame, detector: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    active: dict[str, object] | None = None
    active_rows: list[dict[str, object]] = []
    entry_rows: list[dict[str, object]] = []
    timeline_rows: list[dict[str, object]] = []
    active_counter = 0

    for i, row in df.iterrows():
        state = row["causal_state"]
        start_fire = detector_direction(df, i, detector)
        late_block = False
        if active is not None:
            active["age"] = i - int(active["start_i"]) + 1
            update_extreme(df, i, active)
            update_pullback(df, i, active)
            reason = end_reason(df, i, active)
            if reason is not None:
                active["end_i"] = i
                active["end_time"] = row["dt"]
                active["end_reason"] = reason
                active_rows.append(active.copy())
                active = None
            else:
                dist = move_distance_atr(df, i, active)
                late_block = bool(int(active["age"]) > 30 or dist > 5 or (active["primary_used"] and active["secondary_used"]))
                if primary_candidate(df, i, active):
                    entry_rows.append(entry_record(df, i, detector, active, "PRIMARY_CAUSAL_ENTRY", late_block))
                    active["primary_used"] = True
                elif secondary_candidate(df, i, active):
                    entry_rows.append(entry_record(df, i, detector, active, "SECONDARY_CAUSAL_ENTRY", late_block))
                    active["secondary_used"] = True

        if active is None and start_fire is not None:
            active_counter += 1
            direction = start_fire
            active = {
                "detector": detector,
                "active_move_id": f"{detector}_AM{active_counter:03d}",
                "direction": direction,
                "start_i": i,
                "start_time": row["dt"],
                "start_price": float(row["close"]),
                "start_causal_state": state,
                "age": 1,
                "best_extreme": float(row["high"] if direction == "LONG" else row["low"]),
                "last_extreme_i": i,
                "primary_used": False,
                "secondary_used": False,
                "pulled_back_to_ema27": False,
                "pullback_i": -1,
            }
            late_block = False
            if primary_candidate(df, i, active):
                entry_rows.append(entry_record(df, i, detector, active, "PRIMARY_CAUSAL_ENTRY", late_block))
                active["primary_used"] = True

        timeline_rows.append(
            {
                "detector": detector,
                "time": row["dt"],
                "causal_state": state,
                "start_fired": start_fire or "",
                "active_move_id": "" if active is None else active["active_move_id"],
                "active_direction": "" if active is None else active["direction"],
                "move_age_bars": 0 if active is None else int(active["age"]),
                "move_distance_atr": np.nan if active is None else move_distance_atr(df, i, active),
                "primary_entry_used": False if active is None else bool(active["primary_used"]),
                "secondary_entry_used": False if active is None else bool(active["secondary_used"]),
                "late_block": late_block,
            }
        )

    if active is not None:
        active["end_i"] = len(df) - 1
        active["end_time"] = df.iloc[-1]["dt"]
        active["end_reason"] = "DATA_WINDOW_END"
        active_rows.append(active.copy())

    active_df = pd.DataFrame(active_rows)
    if not active_df.empty:
        active_df["duration_bars"] = active_df["end_i"] - active_df["start_i"] + 1
        active_df["primary_entry_used"] = active_df["primary_used"]
        active_df["secondary_entry_used"] = active_df["secondary_used"]
        active_df = active_df[
            [
                "detector",
                "active_move_id",
                "direction",
                "start_time",
                "end_time",
                "start_price",
                "duration_bars",
                "end_reason",
                "primary_entry_used",
                "secondary_entry_used",
                "start_i",
                "end_i",
            ]
        ]
    entries_df = pd.DataFrame(entry_rows)
    timeline_df = pd.DataFrame(timeline_rows)
    return active_df, entries_df, timeline_df


def entry_record(df: pd.DataFrame, i: int, detector: str, active: dict[str, object], label: str, late_block: bool) -> dict[str, object]:
    dist = move_distance_atr(df, i, active)
    return {
        "detector": detector,
        "active_move_id": active["active_move_id"],
        "entry_label": label,
        "direction": active["direction"],
        "signal_time": df.loc[i, "dt"],
        "move_age_bars": int(active["age"]),
        "move_distance_atr": dist,
        "price_distance_ema27_atr": abs(float(df.loc[i, "close"]) - float(df.loc[i, "ema27"])) / float(df.loc[i, "atr14"]),
        "primary_entry_used_before": bool(active["primary_used"]),
        "secondary_entry_used_before": bool(active["secondary_used"]),
        "late_block_at_signal": late_block,
    }


def zone_at(zones: pd.DataFrame, t: pd.Timestamp) -> tuple[str, str]:
    z = zones[(zones["start_time"] <= t) & (zones["end_time"] >= t)]
    if z.empty:
        return "OUTSIDE_REFERENCE", "OUTSIDE_REFERENCE"
    row = z.iloc[0]
    return str(row["move_id"]), str(row["zone"])


def nearest_label_delta(approved: pd.DataFrame, move_id: str, label: str, t: pd.Timestamp) -> float:
    labels = approved[(approved["move_id"] == move_id) & (approved["entry_label"] == label)]
    if labels.empty:
        return np.nan
    deltas = (labels["signal_time"] - t).dt.total_seconds().abs() / (4 * 3600)
    return float(deltas.min())


def evaluate(
    df: pd.DataFrame,
    active_moves: pd.DataFrame,
    entries: pd.DataFrame,
    timeline: pd.DataFrame,
    ref_moves: pd.DataFrame,
    zones: pd.DataFrame,
    approved: pd.DataFrame,
    blocked: pd.DataFrame,
    exp007: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ref_match_rows = []
    entry_match_rows = []
    blocked_rows = []
    repeated_rows = []
    metrics_rows = []

    exp007_inside = exp007[exp007["move_id"] != "OUTSIDE_MAJOR_MOVE"].copy()
    baseline_signals = len(exp007_inside)

    for detector in DETECTORS:
        am = active_moves[active_moves["detector"] == detector].copy()
        en = entries[entries["detector"] == detector].copy()
        detected_ids = set()

        for _, ref in ref_moves.iterrows():
            same_dir = am[am["direction"] == ref["direction"]]
            overlap = same_dir[(same_dir["start_time"] <= ref["end_time"]) & (same_dir["end_time"] >= ref["start_time"])]
            if overlap.empty:
                ref_match_rows.append(
                    {
                        "detector": detector,
                        "reference_move_id": ref["move_id"],
                        "reference_direction": ref["direction"],
                        "matched_active_move_id": "",
                        "detected": False,
                        "start_delay_bars": np.nan,
                        "start_before_primary": False,
                        "causal_move_covers_reference": False,
                    }
                )
                continue
            overlap = overlap.assign(abs_delay=(overlap["start_time"] - ref["start_time"]).abs())
            match = overlap.sort_values("abs_delay").iloc[0]
            detected_ids.add(match["active_move_id"])
            ref_start_i = int(df.index[df["dt"] == ref["start_time"]][0])
            active_start_i = int(df.index[df["dt"] == match["start_time"]][0])
            primary = approved[(approved["move_id"] == ref["move_id"]) & (approved["entry_label"] == "PRIMARY_ENTRY")]
            primary_time = primary.iloc[0]["signal_time"] if not primary.empty else ref["end_time"]
            ref_match_rows.append(
                {
                    "detector": detector,
                    "reference_move_id": ref["move_id"],
                    "reference_direction": ref["direction"],
                    "matched_active_move_id": match["active_move_id"],
                    "detected": True,
                    "start_delay_bars": active_start_i - ref_start_i,
                    "start_before_primary": match["start_time"] <= primary_time,
                    "causal_move_covers_reference": match["start_time"] <= ref["start_time"] and match["end_time"] >= ref["end_time"],
                }
            )

        for _, entry in en.iterrows():
            move_id, zone = zone_at(zones, entry["signal_time"])
            entry_match_rows.append(
                {
                    **entry.to_dict(),
                    "reference_move_id": move_id,
                    "reference_zone": zone,
                    "in_zone_1_2_3": zone in EARLY_ZONES,
                    "in_zone_4_5_6": zone in LATE_ZONES,
                    "bars_to_nearest_primary_exp008": nearest_label_delta(approved, move_id, "PRIMARY_ENTRY", entry["signal_time"]),
                    "bars_to_nearest_secondary_exp008": nearest_label_delta(approved, move_id, "OPTIONAL_SECONDARY_ENTRY", entry["signal_time"]),
                }
            )

        for _, b in blocked.iterrows():
            nearby = en[(en["signal_time"] >= b["timestamp"] - pd.Timedelta(hours=12)) & (en["signal_time"] <= b["timestamp"] + pd.Timedelta(hours=12))]
            blocked_rows.append(
                {
                    "detector": detector,
                    "blocked_move_id": b["move_id"],
                    "blocked_time": b["timestamp"],
                    "blocked_reason": b["blocked_reason"],
                    "rejected": nearby.empty,
                    "nearby_causal_entries": len(nearby),
                }
            )

        false_active = len(am[~am["active_move_id"].isin(detected_ids)])
        ref_detected = sum(1 for r in ref_match_rows if r["detector"] == detector and r["detected"])
        ref_rows = pd.DataFrame([r for r in ref_match_rows if r["detector"] == detector])
        entry_rows = pd.DataFrame([r for r in entry_match_rows if r["detector"] == detector])
        blocked_eval = pd.DataFrame([r for r in blocked_rows if r["detector"] == detector])
        primary_hits = approved[approved["entry_label"] == "PRIMARY_ENTRY"].apply(
            lambda r: bool(((en["signal_time"] - r["signal_time"]).abs() <= pd.Timedelta(hours=24)).any()), axis=1
        ).mean() if not en.empty else 0.0
        secondary_hits = approved[approved["entry_label"] == "OPTIONAL_SECONDARY_ENTRY"].apply(
            lambda r: bool(((en["signal_time"] - r["signal_time"]).abs() <= pd.Timedelta(hours=24)).any()), axis=1
        ).mean() if not en.empty else 0.0
        reduction = 1 - (len(en) / baseline_signals) if baseline_signals else np.nan
        repeated_rows.append(
            {
                "detector": detector,
                "exp007_reference_signals": baseline_signals,
                "causal_entries": len(en),
                "repeated_signal_reduction": reduction,
                "note": "diagnostic count only; no PnL or trade simulation",
            }
        )
        metrics_rows.append(
            {
                "detector": detector,
                "reference_moves_detected": ref_detected,
                "recall": ref_detected / len(ref_moves) if len(ref_moves) else np.nan,
                "false_active_moves": false_active,
                "median_start_delay_bars": ref_rows["start_delay_bars"].dropna().median(),
                "primary_entries_generated": int((en["entry_label"] == "PRIMARY_CAUSAL_ENTRY").sum()) if not en.empty else 0,
                "secondary_entries_generated": int((en["entry_label"] == "SECONDARY_CAUSAL_ENTRY").sum()) if not en.empty else 0,
                "signals_per_active_move": len(en) / len(am) if len(am) else 0,
                "entry_zone_1_2_3_share": entry_rows["in_zone_1_2_3"].mean() if not entry_rows.empty else 0.0,
                "entry_zone_4_5_6_share": entry_rows["in_zone_4_5_6"].mean() if not entry_rows.empty else 0.0,
                "primary_label_hit_pm6_bars": primary_hits,
                "secondary_label_hit_pm6_bars": secondary_hits,
                "blocked_example_rejection_rate": blocked_eval["rejected"].mean() if not blocked_eval.empty else np.nan,
                "repeated_signal_reduction": reduction,
                "unknown_rate": (entry_rows["reference_zone"] == "OUTSIDE_REFERENCE").mean() if not entry_rows.empty else 1.0,
                "max_entries_per_active_move": en.groupby("active_move_id").size().max() if not en.empty else 0,
            }
        )

    return (
        pd.DataFrame(ref_match_rows),
        pd.DataFrame(entry_match_rows),
        pd.DataFrame(blocked_rows),
        pd.DataFrame(repeated_rows),
        pd.DataFrame(metrics_rows),
    )


def choose_best(metrics: pd.DataFrame) -> tuple[str, str]:
    if metrics.empty:
        return "", "DATA_INSUFFICIENT"
    scored = metrics.copy()
    scored["score"] = (
        scored["reference_moves_detected"] * 3
        - scored["false_active_moves"]
        - scored["median_start_delay_bars"].abs().fillna(99) * 0.2
        + scored["entry_zone_1_2_3_share"].fillna(0) * 5
        + scored["blocked_example_rejection_rate"].fillna(0) * 3
        + scored["repeated_signal_reduction"].fillna(0) * 3
    )
    best = scored.sort_values("score", ascending=False).iloc[0]
    success = (
        best["reference_moves_detected"] >= 8
        and best["median_start_delay_bars"] <= 6
        and best["entry_zone_1_2_3_share"] >= 0.70
        and best["entry_zone_4_5_6_share"] <= 0.20
        and best["repeated_signal_reduction"] >= 0.80
        and best["blocked_example_rejection_rate"] >= 0.70
        and best["max_entries_per_active_move"] <= 2
    )
    if success:
        return str(best["detector"]), "CAUSAL_MOVE_AGE_FOUND"
    partial = (
        best["reference_moves_detected"] >= 4
        or best["repeated_signal_reduction"] >= 0.80
        or best["blocked_example_rejection_rate"] >= 0.70
    )
    return str(best["detector"]), "PARTIAL_CAUSAL_MOVE_AGE" if partial else "NO_CAUSAL_MOVE_AGE"


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_empty_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def write_report(metrics: pd.DataFrame, best: str, verdict: str, ref_match: pd.DataFrame, entry_match: pd.DataFrame, blocked_eval: pd.DataFrame) -> None:
    best_row = metrics[metrics["detector"] == best].iloc[0] if best else pd.Series(dtype=object)
    ambiguous = ref_match[(ref_match["detector"] == best) & (~ref_match["detected"])]["reference_move_id"].tolist() if best else []
    lines = [
        "# EXP-009 — Causal Move Age",
        "",
        "## Scope",
        "",
        "ADAUSDT 4H, 2023-07-01 00:00 UTC -> 2024-12-31 20:00 UTC. No 2025-2026 data was used.",
        "The experiment used only OHLC, EMA27, EMA200, ATR14, and closed bars. It did not calculate PnL and did not use stop or exit logic.",
        "",
        "## Required Answers",
        "",
        f"1. Causal active-move starts can be detected partially; best fixed detector: `{best}`.",
        f"2. Best START_A/B/C: `{best}`.",
        f"3. Reference moves found by best detector: {int(best_row.get('reference_moves_detected', 0))} of 12.",
        f"4. Median start delay: {best_row.get('median_start_delay_bars', np.nan)} bars.",
        f"5. False active moves: {int(best_row.get('false_active_moves', 0))}.",
        f"6. Primary entries: {int(best_row.get('primary_entries_generated', 0))}; secondary entries: {int(best_row.get('secondary_entries_generated', 0))}.",
        f"7. Entry zone share ZONE_1/2/3: {float(best_row.get('entry_zone_1_2_3_share', 0)):.1%}; ZONE_4/5/6: {float(best_row.get('entry_zone_4_5_6_share', 0)):.1%}.",
        f"8. Repeated-signal reduction vs EXP-007: {float(best_row.get('repeated_signal_reduction', 0)):.1%}.",
        f"9. BLOCKED_EXAMPLES rejected: {float(best_row.get('blocked_example_rejection_rate', 0)):.1%}.",
        f"10. Maximum one primary entry per active move was enforced by state; max total causal entries per active move: {int(best_row.get('max_entries_per_active_move', 0))}.",
        "11. Do not proceed to backtest as a trading system yet; the state machine is causal but only partially aligned with EXP-008 reference boundaries.",
        f"12. Ambiguous or missed reference moves for best detector: {', '.join(ambiguous) if ambiguous else 'none'}.",
        "",
        "## Start Detector Metrics",
        "",
        md_table(metrics),
        "",
        "## Best Detector Reference Matching",
        "",
        md_table(ref_match[ref_match["detector"] == best]),
        "",
        "## Best Detector Entry Zone Counts",
        "",
        md_table(entry_match[entry_match["detector"] == best].groupby(["entry_label", "reference_zone"]).size().reset_index(name="count")),
        "",
        "## Best Detector Blocked Examples",
        "",
        md_table(blocked_eval[blocked_eval["detector"] == best].groupby(["blocked_reason", "rejected"]).size().reset_index(name="count")),
        "",
        "## Verdict",
        "",
        verdict,
    ]
    (EXP / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ts_expr(t: pd.Timestamp) -> str:
    return f'timestamp("Etc/UTC", {t.year}, {t.month}, {t.day}, {t.hour}, {t.minute})'


def write_pine(active_moves: pd.DataFrame, entries: pd.DataFrame, approved: pd.DataFrame, timeline: pd.DataFrame) -> None:
    path = OUT / "EXP009_CAUSAL_MOVE_AGE.pine"
    am = active_moves.reset_index(drop=True).copy()
    am["local_move_no"] = am.groupby("detector").cumcount() + 1
    move_no_by_id = dict(zip(am["active_move_id"], am["local_move_no"]))
    en = entries.reset_index(drop=True).copy()
    en["local_move_no"] = en["active_move_id"].map(move_no_by_id).fillna(0).astype(int)
    late = timeline[(timeline["late_block"]) & (timeline["active_move_id"] != "")].copy()
    late["local_move_no"] = late["active_move_id"].map(move_no_by_id).fillna(0).astype(int)
    ref = approved.reset_index(drop=True)
    text = [
        "//@version=6",
        'indicator("EXP-009 Causal Move Age", overlay=true, max_lines_count=500, max_labels_count=500)',
        "",
        "// Visual research markup only. Not a strategy and not an auto-detector.",
        "// Use on ADAUSDT 4H. Recommended ticker: BYBIT:ADAUSDT.P; fallback: BINANCE:ADAUSDT.",
        'startDetector = input.string("START_A", "startDetector", options=["START_A", "START_B", "START_C"])',
        'showActiveMove = input.bool(true, "showActiveMove")',
        'showCausalEntries = input.bool(true, "showCausalEntries")',
        'showReferenceLabels = input.bool(false, "showReferenceLabels")',
        'showBlocked = input.bool(true, "showBlocked")',
        'moveFrom = input.int(1, "moveFrom", minval=1)',
        'moveTo = input.int(1, "moveTo", minval=1)',
        "",
        "ema27 = ta.ema(close, 27)",
        "ema200 = ta.ema(close, 200)",
        'plot(ema27, "EMA27", color=color.aqua, linewidth=1)',
        'plot(ema200, "EMA200", color=color.orange, linewidth=1)',
        "",
        "var string[] moveDetectors = array.from(" + ", ".join(f'"{x}"' for x in am["detector"]) + ")",
        "var int[] moveNos = array.from(" + ", ".join(str(int(x)) for x in am["local_move_no"]) + ")",
        "var string[] moveIds = array.from(" + ", ".join(f'"{x}"' for x in am["active_move_id"]) + ")",
        "var string[] moveDirs = array.from(" + ", ".join(f'"{x}"' for x in am["direction"]) + ")",
        "var int[] moveStarts = array.from(" + ", ".join(ts_expr(pd.Timestamp(x)) for x in am["start_time"]) + ")",
        "var int[] moveEnds = array.from(" + ", ".join(ts_expr(pd.Timestamp(x)) for x in am["end_time"]) + ")",
        "",
        "var string[] entryDetectors = array.from(" + ", ".join(f'"{x}"' for x in en["detector"]) + ")",
        "var string[] entryKinds = array.from(" + ", ".join(f'"{x}"' for x in en["entry_label"]) + ")",
        "var string[] entryMoveIds = array.from(" + ", ".join(f'"{x}"' for x in en["active_move_id"]) + ")",
        "var int[] entryMoveNos = array.from(" + ", ".join(str(int(x)) for x in en["local_move_no"]) + ")",
        "var int[] entryTimes = array.from(" + ", ".join(ts_expr(pd.Timestamp(x)) for x in en["signal_time"]) + ")",
        "var int[] entryAges = array.from(" + ", ".join(str(int(x)) for x in en["move_age_bars"]) + ")",
        "var float[] entryDist = array.from(" + ", ".join(f"{float(x):.3f}" for x in en["move_distance_atr"]) + ")",
        "",
        "var string[] lateDetectors = array.from(" + ", ".join(f'"{x}"' for x in late["detector"]) + ")",
        "var int[] lateMoveNos = array.from(" + ", ".join(str(int(x)) for x in late["local_move_no"]) + ")",
        "var int[] lateTimes = array.from(" + ", ".join(ts_expr(pd.Timestamp(x)) for x in late["time"]) + ")",
        "var int[] lateAges = array.from(" + ", ".join(str(int(x)) for x in late["move_age_bars"]) + ")",
        "var float[] lateDist = array.from(" + ", ".join(f"{float(x):.3f}" for x in late["move_distance_atr"]) + ")",
        "",
        "var string[] refKinds = array.from(" + ", ".join(f'"{x}"' for x in ref["entry_label"]) + ")",
        "var int[] refTimes = array.from(" + ", ".join(ts_expr(pd.Timestamp(x)) for x in ref["signal_time"]) + ")",
        "",
        "f_visible_move(det, n) =>",
        "    det == startDetector and n >= moveFrom and n <= moveTo",
        "",
        "var color bg = na",
        "bg := na",
        "for i = 0 to array.size(moveNos) - 1",
        "    string det = array.get(moveDetectors, i)",
        "    int n = array.get(moveNos, i)",
        "    if f_visible_move(det, n)",
        "        int st = array.get(moveStarts, i)",
        "        int enTime = array.get(moveEnds, i)",
        "        string mid = array.get(moveIds, i)",
        "        string dir = array.get(moveDirs, i)",
        "        if showActiveMove and time >= st and time <= enTime",
        "            bg := dir == \"LONG\" ? color.new(color.green, 90) : color.new(color.red, 90)",
        "        if time == st",
        "            line.new(st, low, st, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.lime, 0), width=2)",
        "            label.new(st, high, mid + \" START \" + dir, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.lime, 0), textcolor=color.black, size=size.tiny)",
        "        if time == enTime",
        "            line.new(enTime, low, enTime, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.white, 0), width=2, style=line.style_dotted)",
        "            label.new(enTime, low, mid + \" END\", xloc=xloc.bar_time, style=label.style_label_up, color=color.new(color.white, 0), textcolor=color.black, size=size.tiny)",
        "bgcolor(bg)",
        "",
        "for i = 0 to array.size(entryTimes) - 1",
        "    int enNo = array.get(entryMoveNos, i)",
        "    if showCausalEntries and array.get(entryDetectors, i) == startDetector and enNo >= moveFrom and enNo <= moveTo and time == array.get(entryTimes, i)",
        "        string kind = array.get(entryKinds, i)",
        "        bool primary = kind == \"PRIMARY_CAUSAL_ENTRY\"",
        "        color c = primary ? color.new(color.green, 0) : color.new(color.blue, 0)",
        "        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=c, width=2)",
        "        label.new(time, primary ? low : high, kind + \"\\nage=\" + str.tostring(array.get(entryAges, i)) + \"\\ndist=\" + str.tostring(array.get(entryDist, i), \"#.##\") + \" ATR\", xloc=xloc.bar_time, style=primary ? label.style_label_up : label.style_label_down, color=c, textcolor=color.white, size=size.tiny)",
        "",
        "for i = 0 to array.size(lateTimes) - 1",
        "    int lateNo = array.get(lateMoveNos, i)",
        "    if showBlocked and array.get(lateDetectors, i) == startDetector and lateNo >= moveFrom and lateNo <= moveTo and time == array.get(lateTimes, i)",
        "        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.red, 0), width=1, style=line.style_dashed)",
        "        label.new(time, low, \"LATE_BLOCK\\nage=\" + str.tostring(array.get(lateAges, i)) + \"\\ndist=\" + str.tostring(array.get(lateDist, i), \"#.##\") + \" ATR\", xloc=xloc.bar_time, style=label.style_label_up, color=color.new(color.red, 0), textcolor=color.white, size=size.tiny)",
        "",
        "for i = 0 to array.size(refTimes) - 1",
        "    if showReferenceLabels and time == array.get(refTimes, i)",
        "        string kind = array.get(refKinds, i)",
        "        color c = kind == \"PRIMARY_ENTRY\" ? color.new(color.yellow, 0) : color.new(color.purple, 0)",
        "        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=c, width=1, style=line.style_dashed)",
        "        label.new(time, high, \"REF \" + kind, xloc=xloc.bar_time, style=label.style_label_down, color=c, textcolor=color.black, size=size.tiny)",
    ]
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def pdf_escape(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(metrics: pd.DataFrame, best: str) -> None:
    lines = [
        "BT /F1 16 Tf 36 560 Td (EXP-009 Causal Move Age Overview) Tj ET",
        f"BT /F1 11 Tf 36 535 Td (Best detector: {pdf_escape(best)}) Tj ET",
    ]
    y = 505
    for _, row in metrics.iterrows():
        msg = (
            f"{row['detector']}: detected={int(row['reference_moves_detected'])}/12, "
            f"false={int(row['false_active_moves'])}, delay={row['median_start_delay_bars']}, "
            f"early={float(row['entry_zone_1_2_3_share']):.1%}, late={float(row['entry_zone_4_5_6_share']):.1%}, "
            f"reduction={float(row['repeated_signal_reduction']):.1%}"
        )
        lines.append(f"BT /F1 9 Tf 36 {y} Td ({pdf_escape(msg)}) Tj ET")
        y -= 22
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    ]
    content = "\n".join(lines).encode("latin-1", errors="replace")
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>")
    objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for idx, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    (OUT / "EXP009_CAUSAL_MOVE_AGE_OVERVIEW.pdf").write_bytes(bytes(out))


def main() -> None:
    ensure_dirs()
    df = load_ohlc()
    ref_moves, zones, approved, blocked, exp007 = load_reference()

    active_parts = []
    entry_parts = []
    timeline_parts = []
    for detector in DETECTORS:
        am, en, tl = run_detector(df, detector)
        active_parts.append(am)
        entry_parts.append(en)
        timeline_parts.append(tl)
    active_moves = pd.concat(active_parts, ignore_index=True) if active_parts else pd.DataFrame()
    entries = pd.concat(entry_parts, ignore_index=True) if entry_parts else pd.DataFrame()
    timeline = pd.concat(timeline_parts, ignore_index=True) if timeline_parts else pd.DataFrame()

    ref_match, entry_match, blocked_eval, repeated, metrics = evaluate(
        df, active_moves, entries, timeline, ref_moves, zones, approved, blocked, exp007
    )
    best, verdict = choose_best(metrics)

    active_moves.drop(columns=["start_i", "end_i"], errors="ignore").to_csv(OUT / "causal_active_moves.csv", index=False)
    entries.to_csv(OUT / "causal_entries.csv", index=False)
    metrics.to_csv(OUT / "start_detector_metrics.csv", index=False)
    ref_match.to_csv(OUT / "reference_move_matching.csv", index=False)
    entry_match.to_csv(OUT / "reference_entry_matching.csv", index=False)
    blocked_eval.to_csv(OUT / "blocked_example_results.csv", index=False)
    repeated.to_csv(OUT / "repeated_signal_reduction.csv", index=False)
    timeline.to_csv(OUT / "causal_state_timeline.csv", index=False)
    write_pine(active_moves, entries, approved, timeline)
    write_pdf(metrics, best)
    write_report(metrics, best, verdict, ref_match, entry_match, blocked_eval)
    print(f"EXP-009 complete: best={best}, verdict={verdict}")


if __name__ == "__main__":
    main()
