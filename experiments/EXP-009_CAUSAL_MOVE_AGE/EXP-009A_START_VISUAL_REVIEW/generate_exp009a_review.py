#!/usr/bin/env python3
"""Generate EXP-009A visual review artifacts.

This is a descriptive audit of the fixed EXP-009 START_A/B/C outputs against
the EXP-008 reference moves. It does not create a new detector, calculate PnL,
or use data after 2024-12-31.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP008 = ROOT / "experiments/EXP-008_MAJOR_MOVE_ENTRY_LABELING/artifacts"
EXP009 = ROOT / "experiments/EXP-009_CAUSAL_MOVE_AGE/artifacts"
EXP009A = ROOT / "experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW"
OUT = EXP009A / "artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

START = pd.Timestamp("2023-07-01 00:00:00")
END = pd.Timestamp("2024-12-31 23:59:59")
FORBIDDEN = pd.Timestamp("2025-01-01 00:00:00")
DETECTORS = ["START_A", "START_B", "START_C"]


@dataclass(frozen=True)
class FirstChange:
    timestamp: pd.Timestamp
    observation_type: str
    description: str
    facts: str


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["time"] = pd.to_datetime(df["open_dt"])
    df = df[(df["time"] >= START) & (df["time"] <= END)].copy()
    if df.empty or df["time"].max() >= FORBIDDEN:
        raise RuntimeError("Data window is empty or includes forbidden 2025+ data.")
    df = df.sort_values("time").reset_index(drop=True)
    prev_close = df["close"].shift(1).fillna(df["close"])
    df["tr"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(float),
            (df["high"] - prev_close).abs().to_numpy(float),
            (df["low"] - prev_close).abs().to_numpy(float),
        ]
    )
    df["body"] = (df["close"] - df["open"]).abs()
    df["body_dir"] = np.sign(df["close"] - df["open"])
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["atr14"] = df["tr"].rolling(14, min_periods=1).mean()
    df["ema27_slope_5"] = df["ema27"] - df["ema27"].shift(5)
    df["ema27_slope_10"] = df["ema27"] - df["ema27"].shift(10)
    df["ema_gap"] = df["ema27"] - df["ema200"]
    df["ema_gap_abs"] = df["ema_gap"].abs()
    df["body_median_10"] = df["body"].rolling(10, min_periods=1).median().shift(1)
    df["high3_prev"] = df["high"].shift(1).rolling(3, min_periods=3).max()
    df["low3_prev"] = df["low"].shift(1).rolling(3, min_periods=3).min()
    df["high5_prev"] = df["high"].shift(1).rolling(5, min_periods=5).max()
    df["low5_prev"] = df["low"].shift(1).rolling(5, min_periods=5).min()
    df["high10_prev"] = df["high"].shift(1).rolling(10, min_periods=10).max()
    df["low10_prev"] = df["low"].shift(1).rolling(10, min_periods=10).min()
    df["high20_prev"] = df["high"].shift(1).rolling(20, min_periods=20).max()
    df["low20_prev"] = df["low"].shift(1).rolling(20, min_periods=20).min()
    df["range10_prev"] = df["high"].shift(1).rolling(10, min_periods=10).max() - df["low"].shift(1).rolling(10, min_periods=10).min()
    df["range20_before10"] = df["high"].shift(11).rolling(20, min_periods=20).max() - df["low"].shift(11).rolling(20, min_periods=20).min()
    long_state = (df["ema27"] > df["ema200"]) & (df["close"] > df["ema200"]) & (df["ema27_slope_5"] > 0) & (df["ema27_slope_10"] >= 0)
    short_state = (df["ema27"] < df["ema200"]) & (df["close"] < df["ema200"]) & (df["ema27_slope_5"] < 0) & (df["ema27_slope_10"] <= 0)
    df["causal_state"] = np.where(long_state, "LONG_STATE", np.where(short_state, "SHORT_STATE", "NEUTRAL_STATE"))
    return df


def load_artifacts() -> dict[str, pd.DataFrame]:
    frames = {
        "moves": pd.read_csv(EXP008 / "major_moves.csv"),
        "zones": pd.read_csv(EXP008 / "move_zones.csv"),
        "approved": pd.read_csv(EXP008 / "approved_entries.csv"),
        "blocked": pd.read_csv(EXP008 / "blocked_entries.csv"),
        "active": pd.read_csv(EXP009 / "causal_active_moves.csv"),
        "entries": pd.read_csv(EXP009 / "causal_entries.csv"),
        "matching": pd.read_csv(EXP009 / "reference_move_matching.csv"),
        "entry_matching": pd.read_csv(EXP009 / "reference_entry_matching.csv"),
        "timeline": pd.read_csv(EXP009 / "causal_state_timeline.csv"),
    }
    for name, frame in frames.items():
        for col in frame.columns:
            if col.endswith("_time") or col in {"time", "signal_time", "timestamp", "start_time", "end_time"}:
                frame[col] = pd.to_datetime(frame[col], errors="coerce")
        if name in {"active", "entries", "matching", "entry_matching", "timeline"}:
            time_cols = [c for c in frame.columns if pd.api.types.is_datetime64_any_dtype(frame[c])]
            for col in time_cols:
                if frame[col].dropna().ge(FORBIDDEN).any():
                    raise RuntimeError(f"{name}.{col} includes forbidden 2025+ data")
    return frames


def idx_at_or_after(df: pd.DataFrame, ts: pd.Timestamp) -> int:
    values = df["time"].to_numpy()
    idx = int(np.searchsorted(values, np.datetime64(ts), side="left"))
    return min(max(idx, 0), len(df) - 1)


def row_at(df: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    return df.loc[idx_at_or_after(df, ts)]


def direction_side(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def zone_at(zones: pd.DataFrame, move_id: str, ts: pd.Timestamp) -> str:
    subset = zones[(zones["move_id"] == move_id) & (zones["start_time"] <= ts) & (zones["end_time"] >= ts)]
    return "OUTSIDE_REFERENCE" if subset.empty else str(subset.iloc[0]["zone"])


def relation(row: pd.Series) -> tuple[str, str]:
    ema_rel = "EMA27_ABOVE_EMA200" if row["ema27"] > row["ema200"] else "EMA27_BELOW_EMA200"
    price_rel = "PRICE_ABOVE_EMA27" if row["close"] > row["ema27"] else "PRICE_BELOW_EMA27"
    return ema_rel, price_rel


def start_reason(detector: str, direction: str, row: pd.Series) -> str:
    if detector == "START_A":
        return "EMA context held for two closed bars"
    if detector == "START_B":
        if direction == "LONG":
            breakout = bool(row["close"] > row["high20_prev"])
        else:
            breakout = bool(row["close"] < row["low20_prev"])
        near = abs(row["close"] - row["ema27"]) <= 2 * row["atr14"]
        return f"directed expansion; break20={breakout}; near_ema27={near}"
    if detector == "START_C":
        if direction == "LONG":
            breaks_range = bool(row["close"] > row["high10_prev"])
        else:
            breaks_range = bool(row["close"] < row["low10_prev"])
        compressed = bool(row["range10_prev"] < row["range20_before10"])
        return f"breakout after compression; compressed={compressed}; break10={breaks_range}"
    return "fixed detector output"


def label_active_moves(moves: pd.DataFrame, active: pd.DataFrame, matching: pd.DataFrame) -> pd.DataFrame:
    matched_ids = set(matching["matched_active_move_id"].dropna().astype(str))
    by_move = []
    for _, am in active.iterrows():
        overlaps = moves[(moves["start_time"] <= am["end_time"]) & (moves["end_time"] >= am["start_time"])]
        overlap_ids = "|".join(overlaps["move_id"].astype(str).tolist()) if not overlaps.empty else ""
        by_move.append(
            {
                **am.to_dict(),
                "is_false_active_move": str(am["active_move_id"]) not in matched_ids,
                "overlap_reference_moves": overlap_ids,
            }
        )
    return pd.DataFrame(by_move)


def classify_false_move(am: pd.Series, moves: pd.DataFrame, df: pd.DataFrame) -> tuple[str, str]:
    direction = str(am["direction"])
    side = direction_side(direction)
    start = am["start_time"]
    end = am["end_time"]
    row = row_at(df, start)
    overlaps = moves[(moves["start_time"] <= end) & (moves["end_time"] >= start)].copy()
    if not overlaps.empty:
        overlaps["age_at_start"] = (start - overlaps["start_time"]) / pd.Timedelta(hours=4)
        overlaps["dist_at_start"] = [
            abs(row["close"] - mv["start_price"]) / max(row["atr14"], 1e-12)
            for _, mv in overlaps.iterrows()
        ]
        same_dir = overlaps[overlaps["direction"] == direction]
        if not same_dir.empty and (same_dir["age_at_start"] > 30).any():
            return "LATE_RESTART", "start occurred inside an existing same-direction reference move after the early window"
        if not same_dir.empty and (same_dir["dist_at_start"] > 5).any():
            return "CONTINUATION_OLD_MOVE", "start occurred after the reference move had already travelled more than 5 ATR"
        if (overlaps["direction"] != direction).any():
            return "COUNTERTREND_NOISE", "start direction opposed an overlapping reference move"
    duration = int(am["duration_bars"])
    if duration <= 12:
        return "SMALL_LOCAL_MOVE", "active move ended quickly and did not become a major reference move"
    close_slice = df[(df["time"] >= start) & (df["time"] <= end)]
    if close_slice.empty:
        return "UNKNOWN", "no local OHLC slice available"
    directional_change = side * (close_slice.iloc[-1]["close"] - row["close"]) / max(row["atr14"], 1e-12)
    if directional_change < 1.0:
        return "FALSE_BREAK", "triggered direction did not produce at least 1 ATR of closed-bar continuation"
    if duration <= 35:
        return "CHOP", "local continuation was short and fragmented compared with reference moves"
    return "UNKNOWN", "no matching reference move; local behavior does not fit a narrower audit bucket"


def first_observable_change(df: pd.DataFrame, move: pd.Series) -> FirstChange:
    start_i = idx_at_or_after(df, move["start_time"])
    end_i = idx_at_or_after(df, move["end_time"])
    side = direction_side(str(move["direction"]))
    before_start = max(0, start_i - 12)
    search_end = min(len(df) - 1, end_i, start_i + 36)
    candidates: list[tuple[int, str, str, str]] = []
    prev_slope = df.loc[start_i - 1, "ema27_slope_5"] if start_i > 0 else np.nan
    for i in range(start_i, search_end + 1):
        row = df.loc[i]
        prev = df.loc[i - 1] if i > 0 else row
        facts: list[str] = []
        if pd.notna(prev_slope) and side * prev_slope <= 0 and side * row["ema27_slope_5"] > 0:
            facts.append("EMA27 slope_5 flipped into move direction")
        if i > 0 and side * (row["ema_gap_abs"] - prev["ema_gap_abs"]) > 0 and side * row["ema27_slope_5"] > 0:
            facts.append("EMA27 began separating from EMA200 in move direction")
        if side == 1:
            local_break = bool(row["close"] > row["high5_prev"])
            first_hl = i >= before_start + 4 and row["low"] > df.loc[i - 3 : i - 1, "low"].min() and df.loc[i - 3 : i - 1, "low"].min() > df.loc[before_start : i - 4, "low"].min()
            price_cross_hold = bool(row["close"] > row["ema27"] and prev["close"] <= prev["ema27"])
        else:
            local_break = bool(row["close"] < row["low5_prev"])
            first_hl = i >= before_start + 4 and row["high"] < df.loc[i - 3 : i - 1, "high"].max() and df.loc[i - 3 : i - 1, "high"].max() < df.loc[before_start : i - 4, "high"].max()
            price_cross_hold = bool(row["close"] < row["ema27"] and prev["close"] >= prev["ema27"])
        if local_break:
            facts.append("closed-bar local structure break")
        if first_hl:
            facts.append("first higher low/lower high sequence visible on closed bars")
        if price_cross_hold:
            facts.append("price crossed and held beyond EMA27 on close")
        body_pickup = row["body"] > 1.25 * row["body_median_10"] and side * (row["close"] - row["open"]) > 0
        if body_pickup:
            facts.append("directional body expanded versus recent median")
        old_extreme_stopped = False
        if i >= start_i + 3:
            recent = df.loc[start_i:i]
            if side == 1:
                old_extreme_stopped = recent["low"].idxmin() <= start_i + 1 and row["close"] > df.loc[start_i, "close"]
            else:
                old_extreme_stopped = recent["high"].idxmax() <= start_i + 1 and row["close"] < df.loc[start_i, "close"]
        if old_extreme_stopped:
            facts.append("old-direction extreme stopped updating")
        if len(facts) >= 2:
            priority = "LOCAL_STRUCTURE_BREAK" if local_break else "EMA_SLOPE_SHIFT" if "EMA27 slope_5 flipped into move direction" in facts else "PRICE_EMA27_HOLD"
            candidates.append((i, priority, "; ".join(facts), facts[0]))
    if not candidates:
        i = min(start_i + 1, search_end)
        row = df.loc[i]
        facts = f"first descriptive change weak: close={row['close']:.4f}, ema27_slope_5={row['ema27_slope_5']:.6f}"
        return FirstChange(row["time"], "WEAK_OR_AMBIGUOUS_CHANGE", facts, facts)
    i, kind, facts, _ = candidates[0]
    return FirstChange(df.loc[i, "time"], kind, facts, facts)


def detector_miss_reason(det: str, move: pd.Series, df: pd.DataFrame, active: pd.DataFrame, matched_id: str | float) -> str:
    if isinstance(matched_id, str) and matched_id:
        return "detected"
    direction = str(move["direction"])
    start_i = idx_at_or_after(df, move["start_time"])
    end_i = idx_at_or_after(df, move["end_time"])
    side = direction_side(direction)
    window = df.loc[start_i:end_i]
    active_det = active[active["detector"] == det]
    overlaps = active_det[(active_det["start_time"] <= move["end_time"]) & (active_det["end_time"] >= move["start_time"])]
    opposite = overlaps[overlaps["direction"] != direction]
    if not opposite.empty:
        return f"overlapping active move was opposite direction ({opposite.iloc[0]['active_move_id']})"
    if det == "START_A":
        needed = "LONG_STATE" if direction == "LONG" else "SHORT_STATE"
        directed_state_bars = int((window["causal_state"] == needed).sum())
        if directed_state_bars < 2:
            return "EMA context did not hold for two closed bars inside reference window"
        return "EMA context appeared too late or was already consumed by a neighboring active move"
    if det == "START_B":
        if direction == "LONG":
            breaks = window["close"] > window["high20_prev"]
        else:
            breaks = window["close"] < window["low20_prev"]
        if not bool(breaks.fillna(False).any()):
            return "no 20-bar directed expansion break inside reference window"
        near = (window["close"] - window["ema27"]).abs() <= 2 * window["atr14"]
        if not bool(near.fillna(False).any()):
            return "expansion occurred too far from EMA27 for START_B"
        return "20-bar expansion criteria appeared only after the reference matching window"
    if det == "START_C":
        compressed = window["range10_prev"] < window["range20_before10"]
        if direction == "LONG":
            breaks = window["close"] > window["high10_prev"]
            accel = window["ema27_slope_5"] > window["ema27_slope_5"].shift(5)
        else:
            breaks = window["close"] < window["low10_prev"]
            accel = window["ema27_slope_5"] < window["ema27_slope_5"].shift(5)
        if not bool(compressed.fillna(False).any()):
            return "no prior compression condition before breakout"
        if not bool(breaks.fillna(False).any()):
            return "no 10-bar range break inside reference window"
        if not bool(accel.fillna(False).any()):
            return "no EMA27 slope acceleration in reference direction"
        return "compression breakout occurred outside the reference matching window"
    return "not detected"


def make_start_visual_audit(frames: dict[str, pd.DataFrame], df: pd.DataFrame) -> pd.DataFrame:
    moves, zones, approved, active, matching = frames["moves"], frames["zones"], frames["approved"], frames["active"], frames["matching"]
    rows = []
    for _, move in moves.iterrows():
        primary = approved[(approved["move_id"] == move["move_id"]) & (approved["entry_label"] == "PRIMARY_ENTRY")].iloc[0]
        secondary = approved[(approved["move_id"] == move["move_id"]) & (approved["entry_label"] == "OPTIONAL_SECONDARY_ENTRY")].iloc[0]
        ref_row = row_at(df, move["start_time"])
        ref_i = idx_at_or_after(df, move["start_time"])
        for det in DETECTORS:
            match = matching[(matching["detector"] == det) & (matching["reference_move_id"] == move["move_id"])].iloc[0]
            matched_id = match["matched_active_move_id"]
            if pd.notna(matched_id) and str(matched_id):
                am = active[active["active_move_id"] == matched_id].iloc[0]
                row = row_at(df, am["start_time"])
                start_i = idx_at_or_after(df, am["start_time"])
                ema_rel, price_rel = relation(row)
                delay_atr = abs(row["close"] - ref_row["close"]) / max(ref_row["atr14"], 1e-12)
                rows.append(
                    {
                        "move_id": move["move_id"],
                        "direction": move["direction"],
                        "detector": det,
                        "active_move_id": matched_id,
                        "detected": True,
                        "start_time": am["start_time"],
                        "delay_bars": start_i - ref_i,
                        "delay_atr_from_reference_start": delay_atr,
                        "before_primary": am["start_time"] <= primary["signal_time"],
                        "reference_zone": zone_at(zones, move["move_id"], am["start_time"]),
                        "ema27_vs_ema200": ema_rel,
                        "price_vs_ema27": price_rel,
                        "trigger_reason": start_reason(det, str(am["direction"]), row),
                        "reference_start": move["start_time"],
                        "reference_end": move["end_time"],
                        "primary_entry_time": primary["signal_time"],
                        "secondary_entry_time": secondary["signal_time"],
                    }
                )
            else:
                rows.append(
                    {
                        "move_id": move["move_id"],
                        "direction": move["direction"],
                        "detector": det,
                        "active_move_id": "",
                        "detected": False,
                        "start_time": pd.NaT,
                        "delay_bars": np.nan,
                        "delay_atr_from_reference_start": np.nan,
                        "before_primary": False,
                        "reference_zone": "NOT_DETECTED",
                        "ema27_vs_ema200": "",
                        "price_vs_ema27": "",
                        "trigger_reason": detector_miss_reason(det, move, df, active, ""),
                        "reference_start": move["start_time"],
                        "reference_end": move["end_time"],
                        "primary_entry_time": primary["signal_time"],
                        "secondary_entry_time": secondary["signal_time"],
                    }
                )
    return pd.DataFrame(rows)


def make_missed_analysis(frames: dict[str, pd.DataFrame], df: pd.DataFrame, first_changes: pd.DataFrame) -> pd.DataFrame:
    moves, matching, active = frames["moves"], frames["matching"], frames["active"]
    rows = []
    for _, move in moves.iterrows():
        first = first_changes[first_changes["move_id"] == move["move_id"]].iloc[0]
        row = {
            "move_id": move["move_id"],
            "direction": move["direction"],
            "first_causal_visible_change": first["timestamp"],
            "first_causal_visible_description": first["description"],
            "available_data_on_first_change_bar": first["available_data_on_bar"],
        }
        for det in DETECTORS:
            match = matching[(matching["detector"] == det) & (matching["reference_move_id"] == move["move_id"])].iloc[0]
            detected = bool(match["detected"])
            row[f"detected_{det[-1]}"] = detected
            row[f"delay_{det[-1]}"] = match["start_delay_bars"]
            row[f"why_{det[-1]}_not_fired"] = detector_miss_reason(det, move, df, active, match["matched_active_move_id"])
        rows.append(row)
    cols = [
        "move_id",
        "direction",
        "detected_A",
        "detected_B",
        "detected_C",
        "delay_A",
        "delay_B",
        "delay_C",
        "why_A_not_fired",
        "why_B_not_fired",
        "why_C_not_fired",
        "first_causal_visible_change",
        "first_causal_visible_description",
        "available_data_on_first_change_bar",
    ]
    return pd.DataFrame(rows)[cols]


def make_false_analysis(frames: dict[str, pd.DataFrame], df: pd.DataFrame, active_labeled: pd.DataFrame) -> pd.DataFrame:
    moves = frames["moves"]
    rows = []
    for _, am in active_labeled[active_labeled["is_false_active_move"]].iterrows():
        row = row_at(df, am["start_time"])
        bucket, why = classify_false_move(am, moves, df)
        rows.append(
            {
                "detector": am["detector"],
                "active_move_id": am["active_move_id"],
                "start_time": am["start_time"],
                "end_time": am["end_time"],
                "direction": am["direction"],
                "duration_bars": am["duration_bars"],
                "trigger_detail": start_reason(str(am["detector"]), str(am["direction"]), row),
                "why_not_major_move": why,
                "classification": bucket,
                "overlap_reference_moves": am["overlap_reference_moves"],
                "starts_after_reference_gt_5atr": starts_after_gt5atr(am, moves, df),
                "starts_with_unchanged_ema_context": unchanged_ema_context(am, df),
                "starts_near_reference_end": starts_near_reference_end(am, moves),
            }
        )
    return pd.DataFrame(rows)


def starts_after_gt5atr(am: pd.Series, moves: pd.DataFrame, df: pd.DataFrame) -> bool:
    start = am["start_time"]
    row = row_at(df, start)
    overlaps = moves[(moves["start_time"] <= start) & (moves["end_time"] >= start) & (moves["direction"] == am["direction"])]
    for _, move in overlaps.iterrows():
        if abs(row["close"] - move["start_price"]) / max(row["atr14"], 1e-12) > 5:
            return True
    return False


def unchanged_ema_context(am: pd.Series, df: pd.DataFrame) -> bool:
    i = idx_at_or_after(df, am["start_time"])
    if i < 6:
        return False
    needed = "LONG_STATE" if am["direction"] == "LONG" else "SHORT_STATE"
    return bool((df.loc[i - 6 : i - 1, "causal_state"] == needed).sum() >= 4)


def starts_near_reference_end(am: pd.Series, moves: pd.DataFrame) -> bool:
    start = am["start_time"]
    near = moves[(moves["end_time"] >= start - pd.Timedelta(hours=24)) & (moves["end_time"] <= start + pd.Timedelta(hours=24))]
    return not near.empty


def make_first_changes(frames: dict[str, pd.DataFrame], df: pd.DataFrame, audit: pd.DataFrame) -> pd.DataFrame:
    moves, approved = frames["moves"], frames["approved"]
    rows = []
    for _, move in moves.iterrows():
        fc = first_observable_change(df, move)
        start_i = idx_at_or_after(df, move["start_time"])
        fc_i = idx_at_or_after(df, fc.timestamp)
        primary = approved[(approved["move_id"] == move["move_id"]) & (approved["entry_label"] == "PRIMARY_ENTRY")].iloc[0]
        p_i = idx_at_or_after(df, primary["signal_time"])
        delays = {}
        earlier = []
        for det in DETECTORS:
            rec = audit[(audit["move_id"] == move["move_id"]) & (audit["detector"] == det)].iloc[0]
            delays[f"delay_{det}"] = rec["delay_bars"]
            if pd.notna(rec["delay_bars"]) and fc_i - start_i < rec["delay_bars"]:
                earlier.append(det)
        fc_row = row_at(df, fc.timestamp)
        rows.append(
            {
                "move_id": move["move_id"],
                "direction": move["direction"],
                "timestamp": fc.timestamp,
                "observation_type": fc.observation_type,
                "delay_bars_from_reference_start": fc_i - start_i,
                "distance_to_primary_bars": fc_i - p_i,
                "earlier_than_detectors": "|".join(earlier),
                "description": fc.description,
                "available_data_on_bar": (
                    f"OHLC closed; close={fc_row['close']:.4f}; EMA27={fc_row['ema27']:.4f}; "
                    f"EMA200={fc_row['ema200']:.4f}; ATR14={fc_row['atr14']:.4f}; "
                    f"ema27_slope_5={fc_row['ema27_slope_5']:.6f}"
                ),
                **delays,
            }
        )
    return pd.DataFrame(rows)


def make_summary(first_changes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for det in DETECTORS:
        rows.append(
            {
                "metric": f"first_observable_change_earlier_than_{det}",
                "value": int(first_changes["earlier_than_detectors"].str.contains(det, regex=False).sum()),
                "note": "count of 12 reference moves",
            }
        )
    counts = first_changes["observation_type"].value_counts()
    for kind, count in counts.items():
        rows.append(
            {
                "metric": f"observation_type_count_{kind}",
                "value": int(count),
                "note": "repeated descriptive observation; not a detector",
            }
        )
    repeated = ", ".join([f"{k}={v}" for k, v in counts.items() if v >= 8]) or "none"
    rows.append({"metric": "observations_repeated_at_least_8_of_12", "value": repeated, "note": "descriptive only"})
    rows.append(
        {
            "metric": "median_first_observable_delay_bars",
            "value": float(first_changes["delay_bars_from_reference_start"].median()),
            "note": "bars from EXP-008 retrospective reference start",
        }
    )
    return pd.DataFrame(rows)


def ts_expr(ts: pd.Timestamp) -> str:
    return f'timestamp("Etc/UTC", {ts.year}, {ts.month}, {ts.day}, {ts.hour}, {ts.minute})'


def pine_array(values: list, kind: str) -> str:
    if kind == "str":
        rendered = [
            '"' + str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
            for v in values
        ]
    elif kind == "int":
        rendered = [str(int(v)) for v in values]
    elif kind == "float":
        rendered = [f"{float(v):.4f}" for v in values]
    elif kind == "time":
        rendered = [ts_expr(pd.Timestamp(v)) for v in values]
    elif kind == "bool":
        rendered = ["true" if bool(v) else "false" for v in values]
    else:
        raise ValueError(kind)
    return "array.from(" + ", ".join(rendered) + ")"


def generate_pine(frames: dict[str, pd.DataFrame], audit: pd.DataFrame, active_labeled: pd.DataFrame, first_changes: pd.DataFrame) -> str:
    moves, approved = frames["moves"], frames["approved"]
    active_near = []
    for _, move in moves.iterrows():
        window_start = move["start_time"] - pd.Timedelta(hours=4 * 50)
        window_end = move["end_time"] + pd.Timedelta(hours=4 * 30)
        subset = active_labeled[(active_labeled["start_time"] <= window_end) & (active_labeled["end_time"] >= window_start)]
        for _, row in subset.iterrows():
            active_near.append({**row.to_dict(), "move_number": int(str(move["move_id"])[1:])})
    active_near_df = pd.DataFrame(active_near).drop_duplicates(["move_number", "active_move_id"])

    starts = audit[audit["detected"]].copy()
    starts["move_number"] = starts["move_id"].str[1:].astype(int)
    starts["label_text"] = starts.apply(
        lambda r: (
            f"{r['detector']}\\n"
            f"ts={pd.Timestamp(r['start_time']).strftime('%Y-%m-%d %H:%M')}\\n"
            f"delay={int(r['delay_bars'])} bars / {float(r['delay_atr_from_reference_start']):.2f} ATR\\n"
            f"{'before PRIMARY' if r['before_primary'] else 'after PRIMARY'}\\n"
            f"zone={r['reference_zone']}\\n"
            f"{r['ema27_vs_ema200']}\\n"
            f"{r['price_vs_ema27']}\\n"
            f"{r['trigger_reason']}"
        ),
        axis=1,
    )
    entries = frames["entries"].copy()
    entry_near = []
    for _, move in moves.iterrows():
        window_start = move["start_time"] - pd.Timedelta(hours=4 * 50)
        window_end = move["end_time"] + pd.Timedelta(hours=4 * 30)
        subset = entries[(entries["signal_time"] >= window_start) & (entries["signal_time"] <= window_end)]
        for _, row in subset.iterrows():
            entry_near.append({**row.to_dict(), "move_number": int(str(move["move_id"])[1:])})
    entry_near_df = pd.DataFrame(entry_near).drop_duplicates(["move_number", "detector", "active_move_id", "signal_time"])

    primary_times = []
    secondary_times = []
    for _, move in moves.iterrows():
        primary_times.append(approved[(approved["move_id"] == move["move_id"]) & (approved["entry_label"] == "PRIMARY_ENTRY")].iloc[0]["signal_time"])
        secondary_times.append(approved[(approved["move_id"] == move["move_id"]) & (approved["entry_label"] == "OPTIONAL_SECONDARY_ENTRY")].iloc[0]["signal_time"])
    first_label_values = (first_changes["observation_type"] + "\n" + first_changes["description"].str.slice(0, 80)).tolist()

    lines = [
        '//@version=6',
        'indicator("EXP-009A Start Visual Review", overlay=true, max_lines_count=500, max_labels_count=500)',
        '',
        '// Visual audit only. Not a strategy, not a new detector, and not a PnL tool.',
        'moveNumber = input.int(1, "moveNumber", minval=1, maxval=12)',
        'showEMA = input.bool(true, "showEMA")',
        'showActiveSpans = input.bool(true, "showActiveSpans")',
        'showFalseSpans = input.bool(true, "showFalseSpans")',
        'showCausalEntries = input.bool(true, "showCausalEntries")',
        '',
        'ema27 = ta.ema(close, 27)',
        'ema200 = ta.ema(close, 200)',
        'plot(showEMA ? ema27 : na, "EMA27", color=color.aqua, linewidth=1)',
        'plot(showEMA ? ema200 : na, "EMA200", color=color.orange, linewidth=1)',
        '',
        f'var string[] moveIds = {pine_array(moves["move_id"].tolist(), "str")}',
        f'var string[] moveDirs = {pine_array(moves["direction"].tolist(), "str")}',
        f'var int[] moveStarts = {pine_array(moves["start_time"].tolist(), "time")}',
        f'var int[] moveEnds = {pine_array(moves["end_time"].tolist(), "time")}',
        f'var int[] primaryTimes = {pine_array(primary_times, "time")}',
        f'var int[] secondaryTimes = {pine_array(secondary_times, "time")}',
        f'var int[] firstTimes = {pine_array(first_changes["timestamp"].tolist(), "time")}',
        f'var string[] firstLabels = {pine_array(first_label_values, "str")}',
        '',
    ]
    if not starts.empty:
        lines.extend(
            [
                f'var int[] startMoveNos = {pine_array(starts["move_number"].tolist(), "int")}',
                f'var string[] startDetectors = {pine_array(starts["detector"].tolist(), "str")}',
                f'var int[] startTimes = {pine_array(starts["start_time"].tolist(), "time")}',
                f'var string[] startLabels = {pine_array(starts["label_text"].tolist(), "str")}',
            ]
        )
    if not active_near_df.empty:
        lines.extend(
            [
                f'var int[] spanMoveNos = {pine_array(active_near_df["move_number"].tolist(), "int")}',
                f'var string[] spanDetectors = {pine_array(active_near_df["detector"].tolist(), "str")}',
                f'var string[] spanDirs = {pine_array(active_near_df["direction"].tolist(), "str")}',
                f'var int[] spanStarts = {pine_array(active_near_df["start_time"].tolist(), "time")}',
                f'var int[] spanEnds = {pine_array(active_near_df["end_time"].tolist(), "time")}',
                f'var bool[] spanFalse = {pine_array(active_near_df["is_false_active_move"].tolist(), "bool")}',
            ]
        )
    if not entry_near_df.empty:
        lines.extend(
            [
                f'var int[] entryMoveNos = {pine_array(entry_near_df["move_number"].tolist(), "int")}',
                f'var string[] entryDetectors = {pine_array(entry_near_df["detector"].tolist(), "str")}',
                f'var string[] entryKinds = {pine_array(entry_near_df["entry_label"].tolist(), "str")}',
                f'var int[] entryTimes = {pine_array(entry_near_df["signal_time"].tolist(), "time")}',
            ]
        )
    lines.extend(
        [
            '',
            'int idx = moveNumber - 1',
            'int refStart = array.get(moveStarts, idx)',
            'int refEnd = array.get(moveEnds, idx)',
            'bool inWindow = time >= refStart - 50 * 4 * 60 * 60 * 1000 and time <= refEnd + 30 * 4 * 60 * 60 * 1000',
            '',
            'color bg = na',
            'bg := na',
            'if showActiveSpans',
            '    for i = 0 to array.size(spanMoveNos) - 1',
            '        if array.get(spanMoveNos, i) == moveNumber and time >= array.get(spanStarts, i) and time <= array.get(spanEnds, i)',
            '            bool isFalse = array.get(spanFalse, i)',
            '            string dir = array.get(spanDirs, i)',
            '            color spanColor = isFalse and showFalseSpans ? color.new(color.gray, 84) : dir == "LONG" ? color.new(color.green, 92) : color.new(color.red, 92)',
            '            bg := spanColor',
            'bgcolor(inWindow ? bg : na)',
            '',
            'if inWindow and time == refStart',
            '    line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.white, width=4)',
            '    label.new(time, high, array.get(moveIds, idx) + " REF START " + array.get(moveDirs, idx), xloc=xloc.bar_time, style=label.style_label_down, color=color.white, textcolor=color.black, size=size.tiny)',
            'if inWindow and time == refEnd',
            '    line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.white, width=2, style=line.style_dotted)',
            '    label.new(time, low, array.get(moveIds, idx) + " REF END", xloc=xloc.bar_time, style=label.style_label_up, color=color.white, textcolor=color.black, size=size.tiny)',
            'if inWindow and time == array.get(primaryTimes, idx)',
            '    label.new(time, low, "PRIMARY_ENTRY", xloc=xloc.bar_time, style=label.style_label_up, color=color.green, textcolor=color.white, size=size.tiny)',
            'if inWindow and time == array.get(secondaryTimes, idx)',
            '    label.new(time, high, "OPTIONAL_SECONDARY_ENTRY", xloc=xloc.bar_time, style=label.style_label_down, color=color.blue, textcolor=color.white, size=size.tiny)',
            'if inWindow and time == array.get(firstTimes, idx)',
            '    line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.teal, 0), width=2, style=line.style_dashed)',
            '    label.new(time, high, "FIRST_OBSERVABLE_CHANGE\\n" + array.get(firstLabels, idx), xloc=xloc.bar_time, style=label.style_label_down, color=color.teal, textcolor=color.white, size=size.tiny)',
            '',
            'for i = 0 to array.size(startMoveNos) - 1',
            '    if inWindow and array.get(startMoveNos, i) == moveNumber and time == array.get(startTimes, i)',
            '        string det = array.get(startDetectors, i)',
            '        color c = det == "START_A" ? color.yellow : det == "START_B" ? color.red : color.purple',
            '        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=c, width=2)',
            '        label.new(time, high, array.get(startLabels, i), xloc=xloc.bar_time, style=label.style_label_down, color=c, textcolor=color.black, size=size.tiny)',
            '',
            'if showCausalEntries',
            '    for i = 0 to array.size(entryMoveNos) - 1',
            '        if inWindow and array.get(entryMoveNos, i) == moveNumber and time == array.get(entryTimes, i)',
            '            string det = array.get(entryDetectors, i)',
            '            string kind = array.get(entryKinds, i)',
            '            color c = det == "START_A" ? color.yellow : det == "START_B" ? color.red : color.purple',
            '            label.new(time, kind == "PRIMARY_CAUSAL_ENTRY" ? low : high, det + " " + kind, xloc=xloc.bar_time, style=kind == "PRIMARY_CAUSAL_ENTRY" ? label.style_label_up : label.style_label_down, color=c, textcolor=color.black, size=size.tiny)',
            '',
        ]
    )
    return "\n".join(lines)


def pdf_escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_text(x: float, y: float, text: str, size: int = 9, color: tuple[float, float, float] = (0, 0, 0)) -> str:
    r, g, b = color
    return f"BT /F1 {size} Tf {r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} Td ({pdf_escape(text)}) Tj ET\n"


def pdf_line(x1: float, y1: float, x2: float, y2: float, color: tuple[float, float, float], width: float = 1.0) -> str:
    r, g, b = color
    return f"{width:.2f} w {r:.3f} {g:.3f} {b:.3f} RG {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n"


def pdf_rect(x: float, y: float, w: float, h: float, color: tuple[float, float, float], fill: bool = True, alpha_note: bool = False) -> str:
    r, g, b = color
    op = "f" if fill else "S"
    return f"{r:.3f} {g:.3f} {b:.3f} {'rg' if fill else 'RG'} {x:.2f} {y:.2f} {w:.2f} {h:.2f} re {op}\n"


def write_simple_pdf(path: Path, pages: list[str], width: float = 842, height: float = 595) -> None:
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_ids = []
    for idx, content in enumerate(pages):
        page_id = 3 + idx * 2
        content_id = page_id + 1
        page_ids.append(page_id)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width:.0f} {height:.0f}] /Resources << /Font << /F1 {3 + len(pages) * 2} 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        stream = content.encode("utf-8", errors="replace")
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    pages_obj = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    font_obj = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    ordered: list[bytes] = [objects[0], pages_obj]
    ordered.extend(objects[1:])
    ordered.append(font_obj)
    offsets = []
    data = bytearray(b"%PDF-1.4\n")
    for i, obj in enumerate(ordered, start=1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode())
        data.extend(obj)
        data.extend(b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(ordered) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        data.extend(f"{off:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(ordered) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)


def plot_pdf(frames: dict[str, pd.DataFrame], df: pd.DataFrame, audit: pd.DataFrame, active_labeled: pd.DataFrame, first_changes: pd.DataFrame, false_analysis: pd.DataFrame) -> None:
    moves, approved, entries = frames["moves"], frames["approved"], frames["entries"]
    colors = {"START_A": (0.85, 0.72, 0.00), "START_B": (0.84, 0.15, 0.16), "START_C": (0.48, 0.17, 0.75)}
    pages: list[str] = []
    width, height = 842, 595
    chart_x, chart_y, chart_w, chart_h = 50, 210, 742, 310
    for _, move in moves.iterrows():
        window_start = move["start_time"] - pd.Timedelta(hours=4 * 50)
        window_end = move["end_time"] + pd.Timedelta(hours=4 * 30)
        chunk = df[(df["time"] >= window_start) & (df["time"] <= window_end)].copy().reset_index(drop=True)
        ymin = float(min(chunk["low"].min(), chunk["ema27"].min(), chunk["ema200"].min()))
        ymax = float(max(chunk["high"].max(), chunk["ema27"].max(), chunk["ema200"].max()))
        pad = max((ymax - ymin) * 0.06, 1e-5)
        ymin -= pad
        ymax += pad

        def x_at(ts: pd.Timestamp) -> float:
            if window_end == window_start:
                return chart_x
            return chart_x + ((pd.Timestamp(ts) - window_start) / (window_end - window_start)) * chart_w

        def y_at(price: float) -> float:
            return chart_y + ((float(price) - ymin) / (ymax - ymin)) * chart_h

        content = ""
        content += pdf_rect(0, 0, width, height, (1, 1, 1))
        content += pdf_text(45, 558, f"{move['move_id']} {move['direction']} | EXP-009A START_A/B/C visual audit", 14)
        content += pdf_rect(chart_x, chart_y, chart_w, chart_h, (0.97, 0.97, 0.97), True)
        for frac in np.linspace(0, 1, 6):
            y = chart_y + frac * chart_h
            content += pdf_line(chart_x, y, chart_x + chart_w, y, (0.86, 0.86, 0.86), 0.4)
            price = ymin + frac * (ymax - ymin)
            content += pdf_text(8, y - 3, f"{price:.4f}", 7, (0.25, 0.25, 0.25))

        spans = active_labeled[(active_labeled["start_time"] <= window_end) & (active_labeled["end_time"] >= window_start)]
        for _, span in spans.iterrows():
            if bool(span["is_false_active_move"]):
                sx = max(chart_x, x_at(span["start_time"]))
                ex = min(chart_x + chart_w, x_at(span["end_time"]))
                content += pdf_rect(sx, chart_y, max(ex - sx, 1.0), chart_h, (0.83, 0.83, 0.83), True)

        for _, bar in chunk.iterrows():
            bx = x_at(bar["time"])
            c = (0.17, 0.62, 0.25) if bar["close"] >= bar["open"] else (0.84, 0.15, 0.16)
            content += pdf_line(bx, y_at(bar["low"]), bx, y_at(bar["high"]), c, 0.5)
            y0 = y_at(min(bar["open"], bar["close"]))
            y1 = y_at(max(bar["open"], bar["close"]))
            content += pdf_rect(bx - 1.2, y0, 2.4, max(y1 - y0, 0.8), c, True)

        for col, c in [("ema27", (0, 0.74, 0.83)), ("ema200", (1, 0.50, 0.00))]:
            pts = [(x_at(r["time"]), y_at(r[col])) for _, r in chunk.iterrows()]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                content += pdf_line(x1, y1, x2, y2, c, 0.8)

        ref_start = move["start_time"]
        ref_end = move["end_time"]
        primary = approved[(approved["move_id"] == move["move_id"]) & (approved["entry_label"] == "PRIMARY_ENTRY")].iloc[0]
        secondary = approved[(approved["move_id"] == move["move_id"]) & (approved["entry_label"] == "OPTIONAL_SECONDARY_ENTRY")].iloc[0]
        fc = first_changes[first_changes["move_id"] == move["move_id"]].iloc[0]
        markers = [
            (ref_start, (0, 0, 0), 2.4, "REF START"),
            (ref_end, (0, 0, 0), 1.2, "REF END"),
            (primary["signal_time"], (0.10, 0.62, 0.25), 1.4, "PRIMARY"),
            (secondary["signal_time"], (0.12, 0.47, 0.71), 1.4, "SECONDARY"),
            (fc["timestamp"], (0, 0.59, 0.53), 1.6, "FIRST"),
        ]
        for ts, c, lw, label in markers:
            xx = x_at(ts)
            content += pdf_line(xx, chart_y, xx, chart_y + chart_h, c, lw)
            content += pdf_text(xx + 2, chart_y + chart_h - 12, label, 7, c)

        for _, st in audit[(audit["move_id"] == move["move_id"]) & (audit["detected"])].iterrows():
            xx = x_at(st["start_time"])
            c = colors[st["detector"]]
            content += pdf_line(xx, chart_y, xx, chart_y + chart_h, c, 1.8)
            content += pdf_text(xx + 2, chart_y + chart_h - 28, f"{st['detector']} {int(st['delay_bars'])}b", 7, c)

        near_entries = entries[(entries["signal_time"] >= window_start) & (entries["signal_time"] <= window_end)]
        for _, ce in near_entries.iterrows():
            point = row_at(df, ce["signal_time"])
            xx, yy = x_at(ce["signal_time"]), y_at(point["close"])
            c = colors.get(ce["detector"], (0, 0, 0))
            content += pdf_rect(xx - 2, yy - 2, 4, 4, c, True)

        content += pdf_text(590, 558, "gray spans = false active moves", 8, (0.35, 0.35, 0.35))
        delays = audit[audit["move_id"] == move["move_id"]].set_index("detector")
        delay_line = "; ".join(
            f"{det}: {'miss' if not bool(delays.loc[det, 'detected']) else str(int(delays.loc[det, 'delay_bars'])) + ' bars'}"
            for det in DETECTORS
        )
        false_near = false_analysis[(false_analysis["start_time"] >= window_start) & (false_analysis["start_time"] <= window_end)]
        false_summary = false_near["classification"].value_counts().to_dict()
        explanation = [
            f"{move['move_id']} delays: {delay_line}",
            f"FIRST_OBSERVABLE_CHANGE: {fc['timestamp']} ({fc['observation_type']}) - {fc['description']}",
            f"What was visible earlier: {fc['available_data_on_bar']}",
            f"Nearby false starts: {false_summary if false_summary else 'none'}",
            "Detector timing is descriptive only; no PnL, no new detector, no parameter change.",
        ]
        y_text = 178
        for paragraph in explanation:
            for line in textwrap.wrap(str(paragraph), width=150):
                content += pdf_text(50, y_text, line, 8)
                y_text -= 11
        pages.append(content)
    write_simple_pdf(OUT / "EXP009A_START_REVIEW.pdf", pages, width=width, height=height)


def make_report(
    audit: pd.DataFrame,
    missed: pd.DataFrame,
    false_analysis: pd.DataFrame,
    first_changes: pd.DataFrame,
    summary: pd.DataFrame,
) -> str:
    false_counts = false_analysis.groupby("detector").size().to_dict()
    class_counts = false_analysis.groupby(["detector", "classification"]).size().unstack(fill_value=0)
    closest = audit[audit["detected"]].sort_values("delay_bars").groupby("detector").head(3)
    failed = missed[
        (~missed["detected_A"].astype(bool))
        | (~missed["detected_B"].astype(bool))
        | (~missed["detected_C"].astype(bool))
    ]
    best_first = first_changes["observation_type"].value_counts()
    repeated = summary[summary["metric"] == "observations_repeated_at_least_8_of_12"].iloc[0]["value"]
    start_b = audit[(audit["detector"] == "START_B") & (audit["detected"])]
    start_b_zones = start_b["reference_zone"].value_counts().to_dict()
    return f"""# EXP-009A — START Visual Review

## Status

REPORT_READY

## Scope

ADAUSDT 4H, 2023-07-01 00:00 UTC -> 2024-12-31 20:00 UTC. Irobot was used read-only for OHLC, EMA27, EMA200, and ATR14 reconstruction. Existing EXP-008 and EXP-009 artifacts were used as fixed inputs.

No PnL, stop, exit, parameter optimization, new start detector, or 2025-2026 data was used.

## Method

The audit compares the fixed `START_A`, `START_B`, and `START_C` active moves from EXP-009 against the 12 EXP-008 reference moves. `FIRST_OBSERVABLE_CHANGE` is a descriptive closed-bar annotation only: it records the first visible change found from allowed facts such as EMA27 slope, local structure break, closed-bar price/EMA27 behavior, directional body expansion, and halt of old-direction extremes. It is not a detector and is not used as a predictor.

## Required Answers

1. `START_B` has median delay 83 bars because its directed-expansion condition usually waits for an EMA-aligned 20-bar breakout near EMA27. In the matched references, its starts land mostly in `ZONE_3_EARLY_CONTINUATION`, `ZONE_4_MATURE_MOVE`, or later: {start_b_zones}. It is selective, so it rejects many early or ambiguous starts, but the surviving starts often occur after the reference birth and after PRIMARY_ENTRY.
2. `START_A` creates {false_counts.get('START_A', 0)} false moves because a two-bar EMA context hold is too sensitive to local EMA regime flips. The false-move classification mix is `{class_counts.loc['START_A'].to_dict() if 'START_A' in class_counts.index else {}}`; many are small local moves, old-move continuations, or late restarts rather than new major moves.
3. `START_C` creates {false_counts.get('START_C', 0)} false moves because compression-breakout patterns recur inside chop and inside already-running movements. The false-move classification mix is `{class_counts.loc['START_C'].to_dict() if 'START_C' in class_counts.index else {}}`.
4. Closest detector hits by delay: {closest[['detector', 'move_id', 'delay_bars', 'reference_zone']].to_dict('records')}.
5. Full or partial failures are listed in `artifacts/missed_move_analysis.csv`. The weakest cases remain short/ambiguous reversals and transitions where EMA context lags the retrospective boundary, especially M02, M03, M06, M09, and M12 for `START_B`.
6. The most frequent `FIRST_OBSERVABLE_CHANGE` type is `{best_first.index[0]}` ({int(best_first.iloc[0])}/12). Observations repeated in at least 8 of 12 moves: {repeated}.

## Key Tables

- `artifacts/start_visual_audit.csv` records detected START_A/B/C lines, delays, zone, EMA context, price-vs-EMA27, and trigger description for each reference move.
- `artifacts/missed_move_analysis.csv` records detected/missed status and descriptive miss reasons per move and detector.
- `artifacts/false_active_move_analysis.csv` classifies unmatched active moves as CHOP, CONTINUATION_OLD_MOVE, SMALL_LOCAL_MOVE, FALSE_BREAK, LATE_RESTART, COUNTERTREND_NOISE, or UNKNOWN.
- `artifacts/first_observable_changes.csv` records the descriptive first visible change per reference move.
- `artifacts/observable_change_summary.csv` summarizes repeated observations.
- `artifacts/EXP009A_START_REVIEW.pine` is the TradingView viewer.
- `artifacts/EXP009A_START_REVIEW.pdf` has 12 pages, one per reference move.

## Verdict

VISUAL_REVIEW_READY
"""


def make_task() -> str:
    return """# EXP-009A — START Visual Review

## Goal

Visually audit fixed EXP-009 `START_A`, `START_B`, and `START_C` against the 12 EXP-008 reference moves.

## Restrictions

- Do not create a new detector.
- Do not calculate PnL.
- Do not use stop or exit logic.
- Do not change parameters.
- Do not choose a detector from one aggregate metric.
- Do not use 2025-2026 data.
- Do not modify Irobot.
- Do not modify `docs/DEFINITIONS.md`.

## Inputs

Use existing EXP-008/EXP-009 artifacts plus read-only ADAUSDT 4H OHLC from Irobot for charting and descriptive closed-bar facts.

## Required Artifacts

- `REPORT.md`
- `artifacts/start_visual_audit.csv`
- `artifacts/missed_move_analysis.csv`
- `artifacts/false_active_move_analysis.csv`
- `artifacts/first_observable_changes.csv`
- `artifacts/observable_change_summary.csv`
- `artifacts/EXP009A_START_REVIEW.pine`
- `artifacts/EXP009A_START_REVIEW.pdf`
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_ohlc()
    frames = load_artifacts()
    active_labeled = label_active_moves(frames["moves"], frames["active"], frames["matching"])
    audit = make_start_visual_audit(frames, df)
    first_changes = make_first_changes(frames, df, audit)
    missed = make_missed_analysis(frames, df, first_changes)
    false_analysis = make_false_analysis(frames, df, active_labeled)
    summary = make_summary(first_changes)

    audit.to_csv(OUT / "start_visual_audit.csv", index=False)
    missed.to_csv(OUT / "missed_move_analysis.csv", index=False)
    false_analysis.to_csv(OUT / "false_active_move_analysis.csv", index=False)
    first_changes.to_csv(OUT / "first_observable_changes.csv", index=False)
    summary.to_csv(OUT / "observable_change_summary.csv", index=False)
    (OUT / "EXP009A_START_REVIEW.pine").write_text(generate_pine(frames, audit, active_labeled, first_changes), encoding="utf-8")
    plot_pdf(frames, df, audit, active_labeled, first_changes, false_analysis)
    (EXP009A / "TASK.md").write_text(make_task(), encoding="utf-8")
    (EXP009A / "REPORT.md").write_text(make_report(audit, missed, false_analysis, first_changes, summary), encoding="utf-8")


if __name__ == "__main__":
    main()
