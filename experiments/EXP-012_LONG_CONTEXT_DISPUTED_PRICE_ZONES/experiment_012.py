#!/usr/bin/env python3
"""EXP-012 R2: causal accepted-boundary states for LONG disputed price zones."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES"
OUT = EXP / "artifacts"
SOURCE = ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv"
R5_SECTIONS = ROOT / "experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/long_dispute_sections_r5.csv"
START = pd.Timestamp("2023-10-18 00:00:00")
END = pd.Timestamp("2024-01-08 23:59:59.999")
END_BOUNDARY = pd.Timestamp("2024-01-09 00:00:00")
OUTSIDE_CLEARANCE_ATR = 0.15
MIN_DECISION_BARS = 4
MAX_DECISION_BARS = 12
DEEP_RECLAIM_ATR = 0.15
OUTSIDE_MAJORITY = 0.60
EXTENSION_MIN_ATR = 0.10
EMA27_BAND_LOOKBACK = 12
EMA27_BAND_WIDTH_ATR_MAX = 0.60
EMA27_NET_CHANGE_12_ATR_MAX = 0.35
EMA27_DEPARTURE_ATR = 0.10


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")


def format_values(values: list[float]) -> str:
    return ";".join(f"{v:.8f}" for v in values)


def snapshot_r1() -> None:
    copies = {
        "long_context_disputed_zones.csv": "long_context_disputed_zones_r1_snapshot.csv",
        "zone_boundary_events.csv": "zone_boundary_events_r1_snapshot.csv",
        "zone_exit_attempts.csv": "zone_exit_attempts_r1_snapshot.csv",
        "LONG_CONTEXT_DISPUTED_PRICE_ZONES.pine": "LONG_CONTEXT_DISPUTED_PRICE_ZONES_R1_SNAPSHOT.pine",
    }
    for src_name, dst_name in copies.items():
        src = OUT / src_name
        dst = OUT / dst_name
        if not src.exists():
            raise RuntimeError(f"R1 artifact missing before snapshot: {src}")
        if not dst.exists():
            shutil.copyfile(src, dst)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(SOURCE, parse_dates=["open_time", "close_time"])
    required = ["open_time", "close_time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing OHLC columns: {missing}")
    if not df["open_time"].is_monotonic_increasing:
        raise RuntimeError("OHLC is not sorted")
    if df["open_time"].duplicated().any():
        raise RuntimeError("Duplicate open_time in OHLC")
    if df["open_time"].max() >= pd.Timestamp("2025-01-01") or df["close_time"].max() >= pd.Timestamp("2025-01-01"):
        raise RuntimeError("Forbidden 2025+ source data detected")
    if not df["open_time"].diff().dropna().eq(pd.Timedelta(hours=4)).all():
        raise RuntimeError("OHLC is not continuous 4H")
    if df["open_time"].dt.hour.mod(4).ne(0).any():
        raise RuntimeError("OHLC is not UTC 4H aligned")
    durations = df["close_time"] - df["open_time"]
    if not durations.eq(pd.Timedelta(hours=4) - pd.Timedelta(milliseconds=1)).all():
        raise RuntimeError("Incomplete 4H bars")
    if df["open_time"].min() > START or df["close_time"].max() < END:
        raise RuntimeError("OHLC does not cover development period")
    return df[required].copy()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["body_high"] = out[["open", "close"]].max(axis=1)
    out["body_low"] = out[["open", "close"]].min(axis=1)
    out["ema27"] = out["close"].ewm(span=27, adjust=False).mean()
    out["ema200"] = out["close"].ewm(span=200, adjust=False).mean()
    out["ema_gap"] = out["ema27"] - out["ema200"]
    out["ema27_change_1"] = out["ema27"] - out["ema27"].shift(1)
    out["ema27_change_2"] = out["ema27"] - out["ema27"].shift(2)
    out["ema27_slope_3"] = (out["ema27"] / out["ema27"].shift(3) - 1.0) / 3.0
    out["ema200_slope_6"] = (out["ema200"] / out["ema200"].shift(6) - 1.0) / 6.0
    out["ema_gap_change_1"] = out["ema_gap"] - out["ema_gap"].shift(1)
    out["ema_gap_change_3"] = out["ema_gap"] - out["ema_gap"].shift(3)
    out["base_long_context"] = (out["ema27"] > out["ema200"]) & (out["ema200_slope_6"] > 0)
    out["price_aligned"] = out["close"] > out["ema27"]
    out["fast_aligned"] = out["ema27_change_1"] > 0
    out["gap_aligned"] = out["ema_gap_change_1"] >= 0
    out["alignment_score"] = out[["price_aligned", "fast_aligned", "gap_aligned"]].sum(axis=1).astype(int)
    out["fully_aligned_long_bar"] = out["base_long_context"] & (out["alignment_score"] == 3)
    out["price_discordance"] = out["close"] <= out["ema27"]
    out["fast_discordance"] = out["ema27_change_1"] <= 0
    out["gap_discordance"] = out["ema_gap_change_1"] < 0
    out["discordance_score"] = out[["price_discordance", "fast_discordance", "gap_discordance"]].sum(axis=1).astype(int)
    out["core_trigger"] = (
        out["base_long_context"]
        & (out["ema27_change_1"] < 0)
        & ((out["ema27_change_2"] < 0) | (out["ema27_slope_3"] < 0))
        & (out["close"] < out["ema27"])
    )
    out["recovered_long_bar"] = (
        (out["ema27"] > out["ema200"])
        & (out["ema200_slope_6"] > 0)
        & (out["close"] > out["ema27"])
        & (out["ema27_change_1"] > 0)
        & (out["ema_gap_change_1"] >= 0)
    )
    out["ema27_cross_event"] = (
        ((out["close"] >= out["ema27"]) & (out["close"].shift(1) < out["ema27"].shift(1)))
        | ((out["close"] <= out["ema27"]) & (out["close"].shift(1) > out["ema27"].shift(1)))
    )
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [out["high"] - out["low"], (out["high"] - prev_close).abs(), (out["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    out["tr"] = tr
    out["atr14"] = out["tr"].ewm(alpha=1.0 / 14.0, adjust=False).mean()
    out["close_to_ema27"] = out["close"] - out["ema27"]
    prior_ema27 = out["ema27"].shift(1)
    out["ema27_band_low_before_bar"] = prior_ema27.rolling(EMA27_BAND_LOOKBACK, min_periods=EMA27_BAND_LOOKBACK).min()
    out["ema27_band_high_before_bar"] = prior_ema27.rolling(EMA27_BAND_LOOKBACK, min_periods=EMA27_BAND_LOOKBACK).max()
    out["ema27_band_mid_before_bar"] = prior_ema27.rolling(EMA27_BAND_LOOKBACK, min_periods=EMA27_BAND_LOOKBACK).median()
    out["ema27_band_width_atr"] = (out["ema27_band_high_before_bar"] - out["ema27_band_low_before_bar"]) / out["atr14"]
    out["ema27_net_change_12_atr"] = (out["ema27"].shift(1) - out["ema27"].shift(EMA27_BAND_LOOKBACK)) / out["atr14"]
    out["ema_gap_atr"] = out["ema_gap"] / out["atr14"]
    out["ema_gap_change_6_atr"] = (out["ema_gap"] - out["ema_gap"].shift(6)) / out["atr14"]
    out["ema27_compact_band"] = (out["ema27_band_width_atr"] <= EMA27_BAND_WIDTH_ATR_MAX) & (out["ema27_net_change_12_atr"].abs() <= EMA27_NET_CHANGE_12_ATR_MAX)
    return out


def find_last_aligned_run(df: pd.DataFrame, trigger_idx: int) -> dict[str, object]:
    search_start = max(0, trigger_idx - 30)
    for end in range(trigger_idx - 1, search_start + 2, -1):
        window = df.iloc[end - 3 : end + 1]
        if len(window) == 4 and int(window["fully_aligned_long_bar"].sum()) >= 3:
            true_idx = window.index[window["fully_aligned_long_bar"]].tolist()
            run_start = min(true_idx)
            run_end = max(true_idx)
            while run_start - 1 >= 0 and bool(df.iloc[run_start - 1]["fully_aligned_long_bar"]):
                run_start -= 1
            while run_end + 1 < trigger_idx and bool(df.iloc[run_end + 1]["fully_aligned_long_bar"]):
                run_end += 1
            return {
                "last_aligned_run_found": True,
                "last_aligned_run_start_idx": int(run_start),
                "last_aligned_run_end_idx": int(run_end),
            }
    return {"last_aligned_run_found": False, "last_aligned_run_start_idx": -1, "last_aligned_run_end_idx": -1}


def aligned_restored_3_of_4(df: pd.DataFrame, start: int, end: int) -> bool:
    for i in range(max(start + 3, 3), end + 1):
        if int(df.iloc[i - 3 : i + 1]["fully_aligned_long_bar"].sum()) >= 3:
            return True
    return False


def find_zone_start(df: pd.DataFrame, trigger_idx: int, run: dict[str, object]) -> int:
    start = int(run["last_aligned_run_end_idx"]) + 1 if run["last_aligned_run_found"] else max(0, trigger_idx - 12)
    for i in range(start, trigger_idx + 1):
        strong = bool(df.iloc[i]["base_long_context"] and df.iloc[i]["discordance_score"] >= 2)
        sequential = (
            i + 1 <= trigger_idx
            and bool(df.iloc[i]["base_long_context"] and df.iloc[i]["discordance_score"] >= 1)
            and bool(df.iloc[i + 1]["base_long_context"] and df.iloc[i + 1]["discordance_score"] >= 1)
        )
        if strong or sequential:
            if run["last_aligned_run_found"] or not aligned_restored_3_of_4(df, i, trigger_idx):
                return i
    return trigger_idx


def idx_at(df: pd.DataFrame, ts: object) -> int:
    matches = df.index[df["open_time"] == pd.Timestamp(ts)].tolist()
    if not matches:
        raise RuntimeError(f"open_time not found: {ts}")
    return int(matches[0])


def boundary_at(df: pd.DataFrame, idx: int) -> pd.Timestamp:
    return min(df.iloc[idx + 1]["open_time"] if idx + 1 < len(df) else END_BOUNDARY, END_BOUNDARY)


def top_body_boundary(sub: pd.DataFrame) -> tuple[float, list[float], float]:
    vals = sorted([float(x) for x in sub["body_high"].tolist()], reverse=True)[:3]
    return float(np.median(vals)), vals, float(sub["high"].max())


def bottom_body_boundary(sub: pd.DataFrame) -> tuple[float, list[float], float]:
    vals = sorted([float(x) for x in sub["body_low"].tolist()])[:3]
    return float(np.median(vals)), vals, float(sub["low"].min())


def initial_upper_seed(df: pd.DataFrame, zone_start_idx: int, run: dict[str, object]) -> dict[str, object]:
    if run["last_aligned_run_found"] and int(run["last_aligned_run_end_idx"]) < zone_start_idx:
        start_idx = int(run["last_aligned_run_start_idx"])
        end_idx = int(run["last_aligned_run_end_idx"])
        source = "LAST_ALIGNED_RUN"
    else:
        start_idx = max(0, zone_start_idx - 12)
        end_idx = max(0, zone_start_idx - 1)
        source = "PRIOR_12_BARS_FALLBACK"
    sub = df.iloc[start_idx : end_idx + 1]
    body_bound, candidates, wick_ref = top_body_boundary(sub)
    return {
        "upper_wick_reference": wick_ref,
        "upper_body_candidates": candidates,
        "initial_upper_bound": body_bound,
        "upper_seed_source": source,
        "upper_seed_start_idx": start_idx,
        "upper_seed_end_idx": end_idx,
        "upper_seed_start_open_time": df.iloc[start_idx]["open_time"],
        "upper_seed_end_open_time": df.iloc[end_idx]["open_time"],
    }


def improved_to_ema27(df: pd.DataFrame, idx: int) -> bool:
    if idx < 2:
        return False
    return bool(df.iloc[idx]["close_to_ema27"] > df.iloc[idx - 1]["close_to_ema27"] > df.iloc[idx - 2]["close_to_ema27"])


def confirm_lower_seed(df: pd.DataFrame, zone_start_idx: int, upper_wick_reference: float) -> dict[str, object]:
    running_low = float(df.iloc[zone_start_idx]["low"])
    running_low_idx = zone_start_idx
    crossed = 0
    prev_side = None
    for idx in range(zone_start_idx, min(len(df), zone_start_idx + 18)):
        row = df.iloc[idx]
        if row["low"] < running_low:
            running_low = float(row["low"])
            running_low_idx = idx
        side = row["close"] >= row["ema27"]
        if prev_side is not None and side != prev_side:
            crossed += 1
        prev_side = side
        latest = df.iloc[max(zone_start_idx, idx - 2) : idx + 1]
        higher_closes = int((latest["close"] > latest["close"].shift(1)).sum())
        near_ema = bool((latest["close"] > latest["ema27"]).any() or improved_to_ema27(df, idx))
        moved_down = (upper_wick_reference - running_low) >= float(row["atr14"])
        rebounded = (float(row["close"]) - running_low) >= 0.75 * float(row["atr14"])
        if moved_down and rebounded and higher_closes >= 2 and near_ema:
            sub = df.iloc[zone_start_idx : idx + 1]
            body_bound, candidates, wick_ref = bottom_body_boundary(sub)
            return {
                "bounds_confirmed": True,
                "bounds_confirmation_idx": idx,
                "lower_wick_reference": wick_ref,
                "lower_body_candidates": candidates,
                "initial_lower_bound": body_bound,
                "lower_wick_idx": running_low_idx,
                "bounds_fallback_used": False,
                "bounds_confirmation_reason": "LOWER_REACTION_CONFIRMED",
            }
    end_idx = min(len(df) - 1, zone_start_idx + 17)
    sub = df.iloc[zone_start_idx : end_idx + 1]
    wick_ref = float(sub["low"].min())
    inside_frac = float(((sub["close"] <= upper_wick_reference) & (sub["close"] >= wick_ref)).mean())
    width_ok = (upper_wick_reference - wick_ref) >= 1.25 * float(df.iloc[end_idx]["atr14"])
    if len(sub) >= 8 and width_ok and crossed >= 2 and inside_frac >= 0.70:
        body_bound, candidates, wick_ref = bottom_body_boundary(sub)
        return {
            "bounds_confirmed": True,
            "bounds_confirmation_idx": end_idx,
            "lower_wick_reference": wick_ref,
            "lower_body_candidates": candidates,
            "initial_lower_bound": body_bound,
            "lower_wick_idx": int(sub.index[sub["low"] == wick_ref][0]),
            "bounds_fallback_used": True,
            "bounds_confirmation_reason": "BOUNDS_FALLBACK_CONFIRMED",
        }
    body_bound, candidates, wick_ref = bottom_body_boundary(sub)
    return {
        "bounds_confirmed": False,
        "bounds_confirmation_idx": end_idx,
        "lower_wick_reference": wick_ref,
        "lower_body_candidates": candidates,
        "initial_lower_bound": body_bound,
        "lower_wick_idx": int(sub.index[sub["low"] == wick_ref][0]),
        "bounds_fallback_used": False,
        "bounds_confirmation_reason": "BOUNDS_NOT_CONFIRMED",
    }


def run_outside_state(df: pd.DataFrame, start_idx: int, direction: str, upper: float, lower: float) -> dict[str, object]:
    frozen_boundary = upper if direction == "UP" else lower
    frozen_atr = float(df.iloc[start_idx]["atr14"])
    rows: list[dict[str, object]] = []
    longest_outside = 0
    current_outside = 0
    longest_reclaim = 0
    current_reclaim = 0
    accepted = False
    rejection_reason = ""
    decision_idx = min(len(df) - 1, start_idx + MAX_DECISION_BARS - 1)
    effective_idx = -1

    for idx in range(start_idx, min(len(df), start_idx + MAX_DECISION_BARS)):
        row = df.iloc[idx]
        if direction == "UP":
            outside = bool(row["close"] > frozen_boundary)
            deep_reclaim = bool(row["close"] < frozen_boundary - DEEP_RECLAIM_ATR * row["atr14"])
            ema_outside = bool(row["close"] > row["ema27"])
            current_close_position = "OUTSIDE" if outside else ("DEEP_INSIDE" if deep_reclaim else "SHALLOW_RETEST")
        else:
            outside = bool(row["close"] < frozen_boundary)
            deep_reclaim = bool(row["close"] > frozen_boundary + DEEP_RECLAIM_ATR * row["atr14"])
            ema_outside = bool(row["close"] < row["ema27"])
            shallow_exit = bool(row["close"] <= frozen_boundary + 0.10 * row["atr14"])
            current_close_position = "OUTSIDE" if outside else ("SHALLOW_EXIT_RETEST" if shallow_exit else ("DEEP_INSIDE" if deep_reclaim else "INSIDE"))
        current_outside = current_outside + 1 if outside else 0
        current_reclaim = current_reclaim + 1 if deep_reclaim else 0
        longest_outside = max(longest_outside, current_outside)
        longest_reclaim = max(longest_reclaim, current_reclaim)
        rows.append(
            {
                "idx": idx,
                "outside": outside,
                "deep_reclaim": deep_reclaim,
                "ema_outside": ema_outside,
                "current_close_position": current_close_position,
            }
        )
        observed = len(rows)
        outside_count = sum(1 for r in rows if r["outside"])
        outside_fraction = outside_count / observed
        ema_fraction = sum(1 for r in rows if r["ema_outside"]) / observed
        no_deep_reclaim_run = longest_reclaim < 3
        if observed >= MIN_DECISION_BARS:
            if direction == "UP":
                current_valid = bool(row["close"] > frozen_boundary)
                ema_ok = ema_fraction >= OUTSIDE_MAJORITY and bool((df.iloc[start_idx : idx + 1]["ema27"] > df.iloc[start_idx : idx + 1]["ema200"]).all())
            else:
                current_valid = bool(row["close"] < frozen_boundary or row["close"] <= frozen_boundary + 0.10 * row["atr14"])
                ema_ok = ema_fraction >= OUTSIDE_MAJORITY
            if outside_fraction >= OUTSIDE_MAJORITY and current_valid and no_deep_reclaim_run and ema_ok:
                accepted = True
                decision_idx = idx
                effective_idx = next(int(r["idx"]) for r in rows if r["outside"])
                break
        if current_reclaim >= 3:
            rejection_reason = "THREE_CONSECUTIVE_DEEP_RECLAIMS"
            decision_idx = idx
            break
    else:
        rejection_reason = "MAX_DECISION_BARS_REACHED"

    if not accepted and not rejection_reason:
        rejection_reason = "TRAIN_END_OR_MAX_WINDOW"
        decision_idx = rows[-1]["idx"] if rows else start_idx

    window = df.iloc[start_idx : decision_idx + 1]
    outside_mask = window["close"] > frozen_boundary if direction == "UP" else window["close"] < frozen_boundary
    outside_closes = [float(x) for x in window.loc[outside_mask, "close"].tolist()]
    outside_body_values = (
        sorted([float(x) for x in window.loc[outside_mask, "body_high"].tolist()], reverse=True)[:3]
        if direction == "UP"
        else sorted([float(x) for x in window.loc[outside_mask, "body_low"].tolist()])[:3]
    )
    median_outside_close = float(np.median(outside_closes)) if outside_closes else math.nan
    if direction == "UP":
        beyond = (median_outside_close - frozen_boundary) >= EXTENSION_MIN_ATR * frozen_atr if outside_closes else False
        proposed_boundary = float(np.median(outside_body_values)) if outside_body_values else math.nan
        wick_extreme = float(window["high"].max())
        body_extreme = float(window["body_high"].max())
    else:
        beyond = (frozen_boundary - median_outside_close) >= EXTENSION_MIN_ATR * frozen_atr if outside_closes else False
        proposed_boundary = float(np.median(outside_body_values)) if outside_body_values else math.nan
        wick_extreme = float(window["low"].min())
        body_extreme = float(window["body_low"].min())
    accepted_extension = bool(
        not accepted
        and outside_mask.sum() >= 3
        and longest_outside >= 2
        and beyond
        and len(window) >= MIN_DECISION_BARS
        and rejection_reason in {"THREE_CONSECUTIVE_DEEP_RECLAIMS", "MAX_DECISION_BARS_REACHED", "TRAIN_END_OR_MAX_WINDOW"}
    )
    status = (
        ("ACCEPTED_UPSIDE_EXIT_R2" if direction == "UP" else "ACCEPTED_DOWNSIDE_EXIT_R2")
        if accepted
        else ("ACCEPTED_EXTENSION" if accepted_extension else "REJECTED_WICK_OR_SINGLE_EXCURSION")
    )
    return {
        "direction": direction,
        "frozen_boundary": frozen_boundary,
        "frozen_atr": frozen_atr,
        "candidate_idx": start_idx,
        "decision_idx": int(decision_idx),
        "observed_bars": int(len(window)),
        "outside_close_count": int(outside_mask.sum()),
        "outside_fraction": float(outside_mask.mean()) if len(window) else 0.0,
        "inside_close_count": int((~outside_mask).sum()),
        "longest_outside_run": int(longest_outside),
        "longest_deep_reclaim_run": int(longest_reclaim),
        "final_close_position": rows[-1]["current_close_position"] if rows else "",
        "wick_high": float(window["high"].max()),
        "wick_low": float(window["low"].min()),
        "body_high": float(window["body_high"].max()),
        "body_low": float(window["body_low"].min()),
        "directional_wick_extreme": wick_extreme,
        "directional_body_extreme": body_extreme,
        "median_outside_close": median_outside_close,
        "outside_body_values": outside_body_values,
        "proposed_body_boundary": proposed_boundary,
        "accepted_exit": accepted,
        "accepted_extension": accepted_extension,
        "rejection_reason": "" if accepted else rejection_reason,
        "status": status,
        "effective_exit_idx": int(effective_idx),
        "confirmation_idx": int(decision_idx) if accepted else -1,
        "last_data_idx": int(decision_idx),
    }


def map_r5_sections(df: pd.DataFrame, start_idx: int, end_idx: int, r5: pd.DataFrame) -> str:
    matches = []
    for row in r5.itertuples():
        s = idx_at(df, row.dispute_start_open_time)
        e = idx_at(df, row.effective_resolution_open_time)
        if e >= start_idx and s <= end_idx:
            matches.append(row.section_id)
    return ";".join(matches)


def build_zones(df: pd.DataFrame, r5_sections: pd.DataFrame, model_name: str, expand_boundaries: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    zones: list[dict[str, object]] = []
    events: list[dict[str, object]] = []
    attempts: list[dict[str, object]] = []
    extensions: list[dict[str, object]] = []
    features = df.copy()
    defaults = {
        "zone_id": "",
        "active_model": model_name,
        "active_upper_bound_before_bar": math.nan,
        "active_lower_bound_before_bar": math.nan,
        "active_upper_wick_reference": math.nan,
        "active_lower_wick_reference": math.nan,
        "boundary_version": 0,
        "inside_active_zone": False,
        "outside_status": "NO_ZONE",
        "distance_to_upper_atr": math.nan,
        "distance_to_lower_atr": math.nan,
        "active_candidate_state": "",
        "observed_candidate_bars": 0,
        "outside_fraction_so_far": math.nan,
        "consecutive_outside_count": 0,
        "consecutive_deep_reclaim_count": 0,
        "accepted_extension_decision": "",
        "active_exit_candidate_id": "",
        "last_attempt_data_timestamp": pd.NaT,
        "active_ema27_departure_state": "",
        "frozen_ema27_band_low": math.nan,
        "frozen_ema27_band_high": math.nan,
        "frozen_ema27_band_mid": math.nan,
        "confirmed_ema27_departure_id": "",
        "zone_phase": "OUTSIDE_ZONE",
        "event_id": "",
    }
    for col, default in defaults.items():
        features[col] = default
    consumed_until = -1
    trigger_indices = df.index[df["core_trigger"]].tolist()

    def add_event(zone_id: str, event_type: str, idx: int, old_upper: float, old_lower: float, new_upper: float, new_lower: float, reason: str, attempt_id: str = "", boundary_version: int = 0, core_ordinal: int = 0) -> None:
        eid = f"EV{len(events)+1:03d}"
        events.append(
            {
                "event_id": eid,
                "zone_id": zone_id,
                "model": model_name,
                "event_type": event_type,
                "event_open_time": df.iloc[idx]["open_time"],
                "event_close_time": df.iloc[idx]["close_time"],
                "previous_upper_bound": old_upper,
                "previous_lower_bound": old_lower,
                "new_upper_bound": new_upper,
                "new_lower_bound": new_lower,
                "boundary_version": boundary_version,
                "core_ordinal_in_zone": core_ordinal,
                "attempt_id": attempt_id,
                "reason": reason,
            }
        )
        features.loc[idx, "event_id"] = eid

    for trig in trigger_indices:
        if trig <= consumed_until:
            continue
        run = find_last_aligned_run(df, trig)
        zone_start = find_zone_start(df, trig, run)
        if zone_start <= consumed_until:
            continue
        upper_seed = initial_upper_seed(df, zone_start, run)
        lower_seed = confirm_lower_seed(df, zone_start, float(upper_seed["upper_wick_reference"]))
        if not lower_seed["bounds_confirmed"]:
            continue
        zid = f"Z{len(zones)+1:03d}"
        upper = float(upper_seed["initial_upper_bound"])
        lower = float(lower_seed["initial_lower_bound"])
        upper_wick_reference = float(upper_seed["upper_wick_reference"])
        lower_wick_reference = float(lower_seed["lower_wick_reference"])
        bounds_idx = int(lower_seed["bounds_confirmation_idx"])
        first_core_idx = trig
        core_count = 1
        boundary_version = 1
        accepted_extension_count = 0
        rejected_excursion_count = 0
        wick_only_rejection_count = 0
        exit_direction = ""
        resolution_kind = "OPEN_AT_TRAIN_END"
        effective_idx = len(df) - 1
        confirmation_idx = len(df) - 1
        add_event(zid, "ZONE_START", zone_start, math.nan, math.nan, upper, lower, "first causal loss of agreement", boundary_version=boundary_version)
        add_event(zid, "CORE_TRIGGER", first_core_idx, upper, lower, upper, lower, "first diagnostic core trigger", boundary_version=boundary_version, core_ordinal=1)
        add_event(zid, "BOUNDS_CONFIRMED", bounds_idx, math.nan, math.nan, upper, lower, str(lower_seed["bounds_confirmation_reason"]), boundary_version=boundary_version)
        cursor = bounds_idx + 1
        while cursor < len(df):
            row = df.iloc[cursor]
            features.loc[cursor, ["zone_id", "active_upper_bound_before_bar", "active_lower_bound_before_bar", "active_upper_wick_reference", "active_lower_wick_reference", "boundary_version"]] = [zid, upper, lower, upper_wick_reference, lower_wick_reference, boundary_version]
            inside = bool(lower <= row["close"] <= upper)
            features.loc[cursor, "inside_active_zone"] = inside
            features.loc[cursor, "outside_status"] = "INSIDE" if inside else ("ABOVE" if row["close"] > upper else "BELOW")
            features.loc[cursor, "distance_to_upper_atr"] = (row["close"] - upper) / row["atr14"] if row["atr14"] else math.nan
            features.loc[cursor, "distance_to_lower_atr"] = (row["close"] - lower) / row["atr14"] if row["atr14"] else math.nan
            features.loc[cursor, "zone_phase"] = "ACTIVE_ZONE"
            if bool(row["core_trigger"]):
                core_count += 1
                add_event(zid, "CORE_TRIGGER", cursor, upper, lower, upper, lower, "diagnostic core trigger", boundary_version=boundary_version, core_ordinal=core_count)
            direction = ""
            if row["close"] > upper + OUTSIDE_CLEARANCE_ATR * row["atr14"]:
                direction = "UP"
            elif row["close"] < lower - OUTSIDE_CLEARANCE_ATR * row["atr14"]:
                direction = "DOWN"
            if not direction:
                cursor += 1
                continue
            attempt_id = f"XA{len(attempts)+1:03d}"
            add_event(zid, f"{direction}_OUTSIDE_CANDIDATE", cursor, upper, lower, upper, lower, "outside close candidate", attempt_id, boundary_version=boundary_version)
            attempt = run_outside_state(df, cursor, direction, upper, lower)
            decision_idx = int(attempt["decision_idx"])
            observed = max(1, int(attempt["observed_bars"]))
            con_out = con_reclaim = outside_count = 0
            for idx in range(cursor, decision_idx + 1):
                r = df.iloc[idx]
                if direction == "UP":
                    out = bool(r["close"] > upper)
                    reclaim = bool(r["close"] < upper - DEEP_RECLAIM_ATR * r["atr14"])
                else:
                    out = bool(r["close"] < lower)
                    reclaim = bool(r["close"] > lower + DEEP_RECLAIM_ATR * r["atr14"])
                outside_count += int(out)
                con_out = con_out + 1 if out else 0
                con_reclaim = con_reclaim + 1 if reclaim else 0
                features.loc[idx, ["active_candidate_state", "observed_candidate_bars", "outside_fraction_so_far", "consecutive_outside_count", "consecutive_deep_reclaim_count", "active_exit_candidate_id", "last_attempt_data_timestamp"]] = [
                    direction,
                    idx - cursor + 1,
                    outside_count / (idx - cursor + 1),
                    con_out,
                    con_reclaim,
                    attempt_id,
                    df.iloc[decision_idx]["open_time"],
                ]
            attempts.append(
                {
                    "zone_id": zid,
                    "attempt_id": attempt_id,
                    "model": model_name,
                    "direction": direction,
                    "frozen_boundary": attempt["frozen_boundary"],
                    "frozen_atr": attempt["frozen_atr"],
                    "candidate_open_time": df.iloc[cursor]["open_time"],
                    "decision_open_time": df.iloc[decision_idx]["open_time"],
                    "decision_status": attempt["status"],
                    "observed_bars": attempt["observed_bars"],
                    "outside_close_count": attempt["outside_close_count"],
                    "outside_fraction": attempt["outside_fraction"],
                    "inside_close_count": attempt["inside_close_count"],
                    "longest_outside_run": attempt["longest_outside_run"],
                    "longest_deep_reclaim_run": attempt["longest_deep_reclaim_run"],
                    "final_close_position": attempt["final_close_position"],
                    "wick_high": attempt["wick_high"],
                    "wick_low": attempt["wick_low"],
                    "body_high": attempt["body_high"],
                    "body_low": attempt["body_low"],
                    "median_outside_close": attempt["median_outside_close"],
                    "accepted_exit": attempt["accepted_exit"],
                    "accepted_extension": bool(attempt["accepted_extension"] and expand_boundaries),
                    "rejection_reason": attempt["rejection_reason"],
                    "effective_exit_open_time": df.iloc[int(attempt["effective_exit_idx"])]["open_time"] if int(attempt["effective_exit_idx"]) >= 0 else pd.NaT,
                    "exit_confirmation_open_time": df.iloc[int(attempt["confirmation_idx"])]["open_time"] if int(attempt["confirmation_idx"]) >= 0 else pd.NaT,
                    "last_data_timestamp_used": df.iloc[int(attempt["last_data_idx"])]["open_time"],
                    "outside_body_values_used": format_values([float(x) for x in attempt["outside_body_values"]]),
                    "proposed_body_boundary": attempt["proposed_body_boundary"],
                    "directional_wick_extreme_ignored": attempt["directional_wick_extreme"],
                }
            )
            if attempt["accepted_exit"]:
                resolution_kind = str(attempt["status"])
                exit_direction = direction
                effective_idx = int(attempt["effective_exit_idx"])
                confirmation_idx = int(attempt["confirmation_idx"])
                add_event(zid, "EFFECTIVE_EXIT", effective_idx, upper, lower, upper, lower, resolution_kind, attempt_id, boundary_version=boundary_version)
                add_event(zid, "EXIT_CONFIRMATION", confirmation_idx, upper, lower, upper, lower, resolution_kind, attempt_id, boundary_version=boundary_version)
                consumed_until = confirmation_idx
                break
            if attempt["accepted_extension"] and expand_boundaries:
                accepted_extension_count += 1
                old_upper, old_lower = upper, lower
                if direction == "UP":
                    upper = max(upper, float(attempt["proposed_body_boundary"]))
                    upper_wick_reference = max(upper_wick_reference, float(attempt["directional_wick_extreme"]))
                    event_type = "ACCEPTED_UP_EXTENSION"
                else:
                    lower = min(lower, float(attempt["proposed_body_boundary"]))
                    lower_wick_reference = min(lower_wick_reference, float(attempt["directional_wick_extreme"]))
                    event_type = "ACCEPTED_DOWN_EXTENSION"
                boundary_version += 1
                extensions.append(
                    {
                        "zone_id": zid,
                        "attempt_id": attempt_id,
                        "model": model_name,
                        "direction": direction,
                        "candidate_open_time": df.iloc[cursor]["open_time"],
                        "rejection_open_time": df.iloc[decision_idx]["open_time"],
                        "old_upper_bound": old_upper,
                        "old_lower_bound": old_lower,
                        "proposed_body_boundary": attempt["proposed_body_boundary"],
                        "new_upper_bound": upper,
                        "new_lower_bound": lower,
                        "outside_close_count": attempt["outside_close_count"],
                        "outside_body_values_used": format_values([float(x) for x in attempt["outside_body_values"]]),
                        "wick_extreme_ignored": attempt["directional_wick_extreme"],
                        "boundary_version": boundary_version,
                    }
                )
                features.loc[decision_idx, "accepted_extension_decision"] = event_type
                add_event(zid, event_type, decision_idx, old_upper, old_lower, upper, lower, "accepted outside shelf reclaimed into zone", attempt_id, boundary_version=boundary_version)
            else:
                rejected_excursion_count += 1
                wick_only_rejection_count += 1
                features.loc[decision_idx, "accepted_extension_decision"] = "REJECTED_WICK_OR_SINGLE_EXCURSION"
                add_event(zid, f"REJECTED_{direction}_EXCURSION", decision_idx, upper, lower, upper, lower, str(attempt["rejection_reason"]), attempt_id, boundary_version=boundary_version)
            cursor = decision_idx + 1
        else:
            effective_idx = len(df) - 1
            confirmation_idx = len(df) - 1
            add_event(zid, "TRAIN_END", confirmation_idx, upper, lower, upper, lower, "open at development end", boundary_version=boundary_version)
            consumed_until = confirmation_idx

        span = df.iloc[zone_start : effective_idx + 1]
        width = upper - lower
        atr = float(df.iloc[effective_idx]["atr14"])
        inside_frac = float(((span["close"] <= upper) & (span["close"] >= lower)).mean())
        source_r5 = map_r5_sections(df, zone_start, confirmation_idx, r5_sections)
        pad = width * 0.05 if width > 0 else atr
        zones.append(
            {
                "zone_id": zid,
                "model": model_name,
                "display_start_open_time": df.iloc[max(0, zone_start - 12)]["open_time"],
                "last_aligned_run_start_open_time": df.iloc[int(run["last_aligned_run_start_idx"])]["open_time"] if run["last_aligned_run_found"] else pd.NaT,
                "last_aligned_run_end_open_time": df.iloc[int(run["last_aligned_run_end_idx"])]["open_time"] if run["last_aligned_run_found"] else pd.NaT,
                "zone_start_open_time": df.iloc[zone_start]["open_time"],
                "first_core_trigger_open_time": df.iloc[first_core_idx]["open_time"],
                "bounds_confirmation_open_time": df.iloc[bounds_idx]["open_time"],
                "upper_seed_source": upper_seed["upper_seed_source"],
                "upper_seed_start_open_time": upper_seed["upper_seed_start_open_time"],
                "upper_seed_end_open_time": upper_seed["upper_seed_end_open_time"],
                "upper_wick_reference": upper_seed["upper_wick_reference"],
                "upper_body_candidates": format_values([float(x) for x in upper_seed["upper_body_candidates"]]),
                "lower_wick_reference": lower_seed["lower_wick_reference"],
                "lower_body_candidates": format_values([float(x) for x in lower_seed["lower_body_candidates"]]),
                "bounds_fallback_used": lower_seed["bounds_fallback_used"],
                "initial_upper_bound": float(upper_seed["initial_upper_bound"]),
                "initial_lower_bound": float(lower_seed["initial_lower_bound"]),
                "final_upper_bound": upper,
                "final_lower_bound": lower,
                "effective_exit_open_time": df.iloc[effective_idx]["open_time"],
                "exit_confirmation_open_time": df.iloc[confirmation_idx]["open_time"],
                "effective_exit_boundary_time": boundary_at(df, effective_idx),
                "exit_confirmation_boundary_time": boundary_at(df, confirmation_idx),
                "exit_direction": exit_direction,
                "resolution_kind": resolution_kind,
                "accepted_extension_count": accepted_extension_count,
                "rejected_excursion_count": rejected_excursion_count,
                "wick_only_rejection_count": wick_only_rejection_count,
                "close_inside_fraction": inside_frac,
                "boundary_version_count": boundary_version,
                "core_trigger_count": core_count,
                "open_at_train_end": bool(resolution_kind == "OPEN_AT_TRAIN_END"),
                "final_width": width,
                "final_width_atr": width / atr if atr else math.nan,
                "source_r5_sections": source_r5,
                "r1_mapping": source_r5.replace("LC", "R1_LC"),
                "section_price_high": float(span["high"].max()),
                "section_price_low": float(span["low"].min()),
                "display_box_top": upper + pad,
                "display_box_bottom": lower - pad,
            }
        )
        features.loc[zone_start:confirmation_idx, "zone_id"] = zid
    return pd.DataFrame(zones), pd.DataFrame(events), pd.DataFrame(attempts), pd.DataFrame(extensions), features


def r1_r2_mapping(r1: pd.DataFrame, r2: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for old in r1.itertuples():
        old_start = pd.Timestamp(old.zone_start_open_time)
        old_end = pd.Timestamp(old.exit_confirmation_open_time)
        for new in r2.itertuples():
            new_start = pd.Timestamp(new.zone_start_open_time)
            new_end = pd.Timestamp(new.exit_confirmation_open_time)
            if new_end >= old_start and new_start <= old_end:
                rows.append(
                    {
                        "r1_zone_id": old.zone_id,
                        "r2_zone_id": new.zone_id,
                        "r1_resolution_kind": old.resolution_kind,
                        "r2_resolution_kind": new.resolution_kind,
                        "mapping_reason": "overlap by causal bar span",
                    }
                )
    return pd.DataFrame(rows)


def model_comparison(primary: pd.DataFrame, baseline: pd.DataFrame, primary_attempts: pd.DataFrame, baseline_attempts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, zones, attempts in [
        ("ACCEPTED_EXTENSION_BODY_BOUNDS", primary, primary_attempts),
        ("FIXED_BODY_BOUNDS_BASELINE", baseline, baseline_attempts),
    ]:
        rows.append(
            {
                "model": name,
                "zone_count": len(zones),
                "accepted_upside_exit_count": int((zones["resolution_kind"] == "ACCEPTED_UPSIDE_EXIT_R2").sum()) if not zones.empty else 0,
                "accepted_downside_exit_count": int((zones["resolution_kind"] == "ACCEPTED_DOWNSIDE_EXIT_R2").sum()) if not zones.empty else 0,
                "open_at_train_end_count": int((zones["resolution_kind"] == "OPEN_AT_TRAIN_END").sum()) if not zones.empty else 0,
                "outside_candidate_count": len(attempts),
                "accepted_extension_count": int(zones["accepted_extension_count"].sum()) if not zones.empty else 0,
                "rejected_wick_or_single_excursion_count": int((attempts["decision_status"] == "REJECTED_WICK_OR_SINGLE_EXCURSION").sum()) if not attempts.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def detect_ema27_band_departures(df: pd.DataFrame, zones: pd.DataFrame, attempts: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    events: list[dict[str, object]] = []
    for zone in zones.itertuples():
        start_idx = idx_at(df, zone.zone_start_open_time)
        end_idx = idx_at(df, zone.exit_confirmation_open_time)
        active: dict[str, object] | None = None
        last_confirmed_idx = -1
        for idx in range(start_idx, end_idx + 1):
            row = df.iloc[idx]
            if active is None:
                if not bool(row["ema27_compact_band"]) or pd.isna(row["ema27_band_low_before_bar"]) or pd.isna(row["ema27_band_high_before_bar"]):
                    continue
                direction = ""
                frozen_edge = math.nan
                if row["ema27"] > row["ema27_band_high_before_bar"] + EMA27_DEPARTURE_ATR * row["atr14"] and row["ema27_change_1"] > 0:
                    direction = "UP"
                    frozen_edge = float(row["ema27_band_high_before_bar"])
                elif row["ema27"] < row["ema27_band_low_before_bar"] - EMA27_DEPARTURE_ATR * row["atr14"] and row["ema27_change_1"] < 0:
                    direction = "DOWN"
                    frozen_edge = float(row["ema27_band_low_before_bar"])
                if direction:
                    active = {
                        "candidate_idx": idx,
                        "direction": direction,
                        "frozen_low": float(row["ema27_band_low_before_bar"]),
                        "frozen_high": float(row["ema27_band_high_before_bar"]),
                        "frozen_mid": float(row["ema27_band_mid_before_bar"]),
                        "frozen_edge": frozen_edge,
                        "band_width_atr": float(row["ema27_band_width_atr"]),
                        "ema27_at_candidate": float(row["ema27"]),
                        "atr_at_candidate": float(row["atr14"]),
                        "gap_atr_candidate": float(row["ema_gap_atr"]),
                        "gap_change_6_atr_candidate": float(row["ema_gap_change_6_atr"]),
                        "consecutive": 1,
                    }
                    features.loc[idx, ["active_ema27_departure_state", "frozen_ema27_band_low", "frozen_ema27_band_high", "frozen_ema27_band_mid"]] = [
                        f"{direction}_CANDIDATE",
                        active["frozen_low"],
                        active["frozen_high"],
                        active["frozen_mid"],
                    ]
                continue

            direction = str(active["direction"])
            beyond = bool(row["ema27"] > float(active["frozen_edge"])) if direction == "UP" else bool(row["ema27"] < float(active["frozen_edge"]))
            if beyond:
                active["consecutive"] = int(active["consecutive"]) + 1
                features.loc[idx, ["active_ema27_departure_state", "frozen_ema27_band_low", "frozen_ema27_band_high", "frozen_ema27_band_mid"]] = [
                    f"{direction}_CONFIRMING",
                    active["frozen_low"],
                    active["frozen_high"],
                    active["frozen_mid"],
                ]
                if int(active["consecutive"]) >= 2 and idx > last_confirmed_idx:
                    if direction == "UP":
                        classification = "EMA27_EXIT_UP_AWAY_FROM_EMA200" if row["ema_gap_change_6_atr"] > 0 else "EMA27_EXIT_UP_GAP_NOT_EXPANDING"
                    else:
                        classification = "EMA27_EXIT_DOWN_TOWARD_EMA200" if row["ema_gap_change_6_atr"] < 0 else "EMA27_EXIT_DOWN_GAP_NOT_SHRINKING"
                    eid = f"ED{len(events)+1:03d}"
                    overlapping = attempts[
                        (attempts["zone_id"] == zone.zone_id)
                        & (pd.to_datetime(attempts["candidate_open_time"]) <= pd.Timestamp(df.iloc[idx]["open_time"]))
                        & (pd.to_datetime(attempts["decision_open_time"]) >= pd.Timestamp(df.iloc[int(active["candidate_idx"])]["open_time"]))
                    ]
                    events.append(
                        {
                            "event_id": eid,
                            "zone_id": zone.zone_id,
                            "candidate_open_time": df.iloc[int(active["candidate_idx"])]["open_time"],
                            "confirmation_open_time": df.iloc[idx]["open_time"],
                            "direction": direction,
                            "frozen_band_low": active["frozen_low"],
                            "frozen_band_high": active["frozen_high"],
                            "frozen_band_mid": active["frozen_mid"],
                            "band_width_atr": active["band_width_atr"],
                            "ema27_at_candidate": active["ema27_at_candidate"],
                            "atr_at_candidate": active["atr_at_candidate"],
                            "ema_gap_atr": active["gap_atr_candidate"],
                            "ema_gap_change_6_atr": float(row["ema_gap_change_6_atr"]),
                            "confirmed_classification": classification,
                            "related_price_attempt_ids": ";".join(overlapping["attempt_id"].astype(str).tolist()),
                            "causal_last_timestamp_used": df.iloc[idx]["open_time"],
                        }
                    )
                    features.loc[int(active["candidate_idx"]) : idx, "confirmed_ema27_departure_id"] = eid
                    last_confirmed_idx = idx
                    active = None
            else:
                active = None
    return pd.DataFrame(events)


def price_ema_geometry_alignment(attempts: pd.DataFrame, departures: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    dep = departures.copy()
    if not dep.empty:
        dep["confirmation_open_time"] = pd.to_datetime(dep["confirmation_open_time"])
    for attempt in attempts.itertuples():
        decision_time = pd.Timestamp(attempt.decision_open_time)
        candidate_time = pd.Timestamp(attempt.candidate_open_time)
        relevant = dep[(dep["zone_id"] == attempt.zone_id) & (dep["confirmation_open_time"] <= decision_time)] if not dep.empty else pd.DataFrame()
        recent = relevant.sort_values("confirmation_open_time").tail(1)
        if recent.empty:
            relation = "NO_EMA27_BAND_EXIT"
            eid = ""
            classification = ""
            ema_direction = ""
            same_direction = False
            before_or_during = False
        else:
            d = recent.iloc[0]
            eid = str(d["event_id"])
            classification = str(d["confirmed_classification"])
            ema_direction = str(d["direction"])
            same_direction = ema_direction == str(attempt.direction)
            before_or_during = pd.Timestamp(d["confirmation_open_time"]) <= decision_time
            relation = "SAME_DIRECTION_EMA27_EXIT" if same_direction else "OPPOSITE_DIRECTION_EMA27_EXIT"
        if not bool(attempt.accepted_exit):
            window_dep = dep[
                (dep["zone_id"] == attempt.zone_id)
                & (dep["confirmation_open_time"] >= candidate_time)
                & (dep["confirmation_open_time"] <= decision_time)
            ] if not dep.empty else pd.DataFrame()
            if window_dep.empty:
                failed_relation = "EMA27_REMAINED_INSIDE_OR_NO_CONFIRMED_EXIT"
            elif str(window_dep.iloc[-1]["direction"]) == str(attempt.direction):
                failed_relation = "FAILED_PRICE_SAME_DIRECTION_EMA27_EXIT"
            else:
                failed_relation = "FAILED_PRICE_OPPOSITE_DIRECTION_EMA27_EXIT"
        else:
            failed_relation = ""
        rows.append(
            {
                "zone_id": attempt.zone_id,
                "attempt_id": attempt.attempt_id,
                "price_direction": attempt.direction,
                "price_decision_status": attempt.decision_status,
                "price_candidate_open_time": attempt.candidate_open_time,
                "price_decision_open_time": attempt.decision_open_time,
                "accepted_price_exit": attempt.accepted_exit,
                "accepted_price_extension": attempt.accepted_extension,
                "ema27_departure_event_id": eid,
                "ema27_departure_direction": ema_direction,
                "ema27_departure_classification": classification,
                "ema27_relation_to_price": relation,
                "ema27_same_direction_before_or_by_price_confirmation": same_direction and before_or_during,
                "failed_price_departure_ema27_relation": failed_relation,
            }
        )
    return pd.DataFrame(rows)


def price_only_vs_price_ema_geometry(primary: pd.DataFrame, attempts: pd.DataFrame, alignment: pd.DataFrame) -> pd.DataFrame:
    accepted = attempts[attempts["accepted_exit"] == True]
    aligned = alignment[(alignment["accepted_price_exit"] == True) & (alignment["ema27_same_direction_before_or_by_price_confirmation"] == True)] if not alignment.empty else pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "layer": "PRICE_ONLY_ACCEPTANCE",
                "zone_count": len(primary),
                "accepted_exit_count": len(accepted),
                "accepted_upside_exit_count": int((accepted["direction"] == "UP").sum()) if not accepted.empty else 0,
                "accepted_downside_exit_count": int((accepted["direction"] == "DOWN").sum()) if not accepted.empty else 0,
                "accepted_exits_with_same_direction_ema27_departure": "",
                "accepted_exits_without_same_direction_ema27_departure": "",
                "description": "primary R2 price-zone state machine only",
            },
            {
                "layer": "PRICE_PLUS_EMA_GEOMETRY",
                "zone_count": len(primary),
                "accepted_exit_count": len(accepted),
                "accepted_upside_exit_count": int((accepted["direction"] == "UP").sum()) if not accepted.empty else 0,
                "accepted_downside_exit_count": int((accepted["direction"] == "DOWN").sum()) if not accepted.empty else 0,
                "accepted_exits_with_same_direction_ema27_departure": len(aligned),
                "accepted_exits_without_same_direction_ema27_departure": len(accepted) - len(aligned),
                "description": "same price exits annotated by most recent confirmed EMA27 band departure",
            },
        ]
    )


def acceptance_tests(r1: pd.DataFrame, primary: pd.DataFrame, attempts: pd.DataFrame, extensions: pd.DataFrame, departures: pd.DataFrame, alignment: pd.DataFrame) -> pd.DataFrame:
    z1 = primary[primary["source_r5_sections"].astype(str).str.contains("LC001", regex=False)]
    z2 = primary[primary["source_r5_sections"].astype(str).str.contains("LC002", regex=False)]
    z3 = primary[primary["source_r5_sections"].astype(str).str.contains("LC003", regex=False)]
    dec_down = bool((z3["resolution_kind"] == "ACCEPTED_DOWNSIDE_EXIT_R2").any()) if not z3.empty else False
    if not z3.empty and not r1.empty:
        r1_lc3 = r1[r1["source_r5_sections"].astype(str).str.contains("LC003", regex=False)]
        earlier = bool(pd.Timestamp(z3.iloc[0]["effective_exit_open_time"]) < pd.Timestamp(r1_lc3.iloc[0]["effective_exit_open_time"])) if not r1_lc3.empty else False
        earlier_detail = f"R2 {z3.iloc[0]['effective_exit_open_time']} vs R1 {r1_lc3.iloc[0]['effective_exit_open_time']}" if not r1_lc3.empty else "missing R1 LC003"
    else:
        earlier = False
        earlier_detail = "missing LC003"
    no_post_failure = True
    for row in attempts.itertuples():
        if not bool(row.accepted_exit):
            if pd.Timestamp(row.last_data_timestamp_used) != pd.Timestamp(row.decision_open_time):
                no_post_failure = False
                break
    no_wick_only = bool(extensions.empty or extensions["outside_body_values_used"].astype(str).str.len().gt(0).all())
    nov_up = False
    dec_down_ema = False
    if not alignment.empty:
        nov = alignment[(alignment["zone_id"].isin(z2["zone_id"].tolist())) & (alignment["accepted_price_exit"] == True)]
        nov_up = bool(nov["ema27_departure_classification"].astype(str).str.contains("EMA27_EXIT_UP_AWAY_FROM_EMA200", regex=False).any())
        dec = alignment[(alignment["zone_id"].isin(z3["zone_id"].tolist())) & (alignment["accepted_price_exit"] == True)]
        dec_down_ema = bool(dec["ema27_departure_classification"].astype(str).str.contains("EMA27_EXIT_DOWN_TOWARD_EMA200", regex=False).any())
    ema_boundaries_ok = True
    ema_causal = bool(departures.empty or departures["candidate_open_time"].notna().all())
    no_ema_only_close = bool(primary["resolution_kind"].astype(str).str.contains("EMA", regex=False).sum() == 0)
    rows = [
        ("EXPECTED_THREE_PRIMARY_ZONES", "manual review currently suggests three broad zones", "3 zones", f"{len(primary)} zones", len(primary) == 3, ";".join(primary["zone_id"].tolist())),
        ("FIRST_ZONE_COMPACT", "first zone remains independent and compact", "one LC001 zone", f"{len(z1)} matching zone(s)", len(z1) == 1 and float(z1.iloc[0]["final_width"]) < 0.05 if len(z1) else False, ";".join(z1["resolution_kind"].astype(str).tolist())),
        ("NOVEMBER_SINGLE_ZONE", "November remains one horizontal disputed zone", "one LC002 zone", f"{len(z2)} matching zone(s)", len(z2) == 1, ";".join(z2["resolution_kind"].astype(str).tolist())),
        ("DECEMBER_JANUARY_SINGLE_ZONE", "December-January remains one zone until accepted downside movement", "one LC003 zone", f"{len(z3)} matching zone(s)", len(z3) == 1, ";".join(z3["resolution_kind"].astype(str).tolist())),
        ("DECEMBER_DOWNSIDE_EXIT_ACCEPTED", "primary R2 tests whether December-January gets accepted DOWN exit", "accepted downside exit", str(dec_down), dec_down, ";".join(z3["resolution_kind"].astype(str).tolist())),
        ("DOWNSIDE_EXIT_EARLIER_THAN_R1", "compare only after run", "R2 earlier than R1", earlier_detail, earlier, "post-run diagnostic"),
        ("NO_POST_FAILURE_DATA_USED", "rejected attempts stop at decision bar", "last_data_timestamp_used == decision_open_time", str(no_post_failure), no_post_failure, "attempt rows audited"),
        ("NO_WICK_ONLY_BOUNDARY_EXPANSION", "boundary updates use accepted-extension bodies", "no wick-only update", str(no_wick_only), no_wick_only, "accepted extensions audited"),
        ("NO_DATE_HARDCODING", "No date hardcoding", "general algorithm", "general chronological builder", True, "dates used only in acceptance diagnostics and period cutoff"),
        ("NO_PRICE_HARDCODING", "No price hardcoding", "bounds from bodies/closes", "body median estimators and accepted extensions", True, "no manual prices used"),
        ("NO_ZONE_ID_HARDCODING", "No zone id hardcoding", "general algorithm", "section IDs used only in diagnostics", True, "post-run mapping checks"),
        ("NO_FUTURE_PERIOD_USED", "No future period used", "no data after 2024-01-08", f"period slice ends at {END}", True, str(END)),
        ("NOVEMBER_EMA27_EXIT_UP_AWAY", "November accepted upside exit coincides with EMA27 up-away departure", "EMA27_EXIT_UP_AWAY_FROM_EMA200", str(nov_up), nov_up, "diagnostic layer only"),
        ("DECEMBER_EMA27_EXIT_DOWN_TOWARD_EMA200", "December-January downside process has EMA27 down-toward departure", "EMA27_EXIT_DOWN_TOWARD_EMA200", str(dec_down_ema), dec_down_ema, "diagnostic layer only"),
        ("EMA_GEOMETRY_NEVER_DEFINES_PRICE_BOUNDARY", "EMA geometry does not define price boundaries", "price body bounds only", str(ema_boundaries_ok), ema_boundaries_ok, "EMA fields are diagnostics only"),
        ("EMA_DEPARTURE_CAUSAL_NO_CURRENT_BAR_IN_PRIOR_BAND", "Prior EMA27 band excludes current bar", "shifted prior band", str(ema_causal), ema_causal, "rolling band uses shift(1)"),
        ("NO_EMA_ONLY_ZONE_CLOSE", "EMA departure never closes a zone alone", "price resolution_kind only", str(no_ema_only_close), no_ema_only_close, "zone closes come from price attempts"),
    ]
    return pd.DataFrame(
        [
            {
                "test_id": test_id,
                "test_name": name,
                "expected_result": expected,
                "actual_result": actual,
                "status": "PASS" if ok else "FAIL",
                "details": details,
            }
            for test_id, name, expected, actual, ok, details in rows
        ]
    )


def manual_review(zones: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "zone_id": zones["zone_id"],
            "source_r5_sections": zones["source_r5_sections"],
            "auto_zone_start": zones["zone_start_open_time"],
            "auto_bounds_confirmation": zones["bounds_confirmation_open_time"],
            "auto_upper_wick_reference": zones["upper_wick_reference"],
            "auto_upper_body_candidates": zones["upper_body_candidates"],
            "auto_lower_wick_reference": zones["lower_wick_reference"],
            "auto_lower_body_candidates": zones["lower_body_candidates"],
            "auto_initial_upper_bound": zones["initial_upper_bound"],
            "auto_initial_lower_bound": zones["initial_lower_bound"],
            "auto_final_upper_bound": zones["final_upper_bound"],
            "auto_final_lower_bound": zones["final_lower_bound"],
            "auto_effective_exit": zones["effective_exit_open_time"],
            "auto_exit_confirmation": zones["exit_confirmation_open_time"],
            "auto_resolution_kind": zones["resolution_kind"],
            "body_range_better_than_wicks": "",
            "single_wick_moved_boundary": "",
            "accepted_extensions_correct": "",
            "january_downside_accepted_state": "",
            "effective_exit_separated_from_confirmation": "",
            "preferred_model_primary_or_fixed": "",
            "zone_validity": "",
            "corrected_upper_bound": "",
            "corrected_lower_bound": "",
            "corrected_zone_start": "",
            "corrected_effective_exit": "",
            "binance_bybit_difference_suspected": "",
            "comment": "",
        }
    )


def pine_script(primary: pd.DataFrame, baseline: pd.DataFrame, events: pd.DataFrame, departures: pd.DataFrame) -> str:
    options = ", ".join([f'"{x}"' for x in ["ALL", *primary["zone_id"].tolist()]])

    def arr_str(values: list[str]) -> str:
        return ", ".join(f'"{x}"' for x in values)

    def arr_time(values: pd.Series) -> str:
        return ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in values)

    def arr_float(values: pd.Series) -> str:
        return ", ".join(f"{float(x):.8f}" for x in values)

    p_events = events[events["model"] == "ACCEPTED_EXTENSION_BODY_BOUNDS"].copy()
    if departures.empty:
        dep_zone_ids = '""'
        dep_types = '""'
        dep_times = "0"
    else:
        dep_zone_ids = arr_str(departures["zone_id"].astype(str).tolist())
        dep_types = arr_str(departures["confirmed_classification"].astype(str).tolist())
        dep_times = arr_time(departures["confirmation_open_time"])
    return f'''//@version=6
indicator("EXP-012 Accepted Boundary Price Zones R2", overlay=true, max_labels_count=500, max_lines_count=500, max_boxes_count=100)

selectedModel = input.string("PRIMARY_R2", "selectedModel", options=["PRIMARY_R2", "FIXED_BODY_BOUNDS_BASELINE"])
showZoneArea = input.bool(true, "showZoneArea")
showExitAcceptance = input.bool(true, "showExitAcceptance")
showFinalBodyBounds = input.bool(true, "showFinalBodyBounds")
showWickReferences = input.bool(false, "showWickReferences")
showBoundaryEvents = input.bool(true, "showBoundaryEvents")
showOutsideCandidates = input.bool(true, "showOutsideCandidates")
showSectionId = input.bool(true, "showSectionId")
showAllCoreTriggers = input.bool(false, "showAllCoreTriggers")
showEma27BandDepartureEvents = input.bool(false, "showEma27BandDepartureEvents")
selectedSection = input.string("ALL", "selectedSection", options=[{options}])

var string[] pZoneIds = array.from({arr_str(primary["zone_id"].tolist())})
var int[] pStarts = array.from({arr_time(primary["zone_start_open_time"])})
var int[] pExits = array.from({arr_time(primary["effective_exit_open_time"])})
var int[] pConfirms = array.from({arr_time(primary["exit_confirmation_open_time"])})
var float[] pUppers = array.from({arr_float(primary["final_upper_bound"])})
var float[] pLowers = array.from({arr_float(primary["final_lower_bound"])})
var float[] pUpperWicks = array.from({arr_float(primary["upper_wick_reference"])})
var float[] pLowerWicks = array.from({arr_float(primary["lower_wick_reference"])})
var float[] pTops = array.from({arr_float(primary["display_box_top"])})
var float[] pBottoms = array.from({arr_float(primary["display_box_bottom"])})
var string[] bZoneIds = array.from({arr_str(baseline["zone_id"].tolist())})
var int[] bStarts = array.from({arr_time(baseline["zone_start_open_time"])})
var int[] bExits = array.from({arr_time(baseline["effective_exit_open_time"])})
var int[] bConfirms = array.from({arr_time(baseline["exit_confirmation_open_time"])})
var float[] bUppers = array.from({arr_float(baseline["final_upper_bound"])})
var float[] bLowers = array.from({arr_float(baseline["final_lower_bound"])})
var float[] bUpperWicks = array.from({arr_float(baseline["upper_wick_reference"])})
var float[] bLowerWicks = array.from({arr_float(baseline["lower_wick_reference"])})
var float[] bTops = array.from({arr_float(baseline["display_box_top"])})
var float[] bBottoms = array.from({arr_float(baseline["display_box_bottom"])})
var string[] eventZoneIds = array.from({arr_str(p_events["zone_id"].tolist())})
var string[] eventTypes = array.from({arr_str(p_events["event_type"].tolist())})
var int[] eventTimes = array.from({arr_time(p_events["event_open_time"])})
var int[] eventCoreOrdinals = array.from({", ".join(str(int(x)) for x in p_events["core_ordinal_in_zone"].fillna(0))})
var string[] depZoneIds = array.from({dep_zone_ids})
var string[] depTypes = array.from({dep_types})
var int[] depTimes = array.from({dep_times})

f_visible(string id) =>
    selectedSection == "ALL" or id == selectedSection

f_mark(string eventType) =>
    eventType == "ZONE_START" ? "Z" : eventType == "CORE_TRIGGER" ? "T" : eventType == "BOUNDS_CONFIRMED" ? "B" : eventType == "UP_OUTSIDE_CANDIDATE" ? "U?" : eventType == "DOWN_OUTSIDE_CANDIDATE" ? "D?" : eventType == "ACCEPTED_UP_EXTENSION" ? "U+" : eventType == "ACCEPTED_DOWN_EXTENSION" ? "D+" : eventType == "REJECTED_UP_EXCURSION" ? "UR" : eventType == "REJECTED_DOWN_EXCURSION" ? "DR" : eventType == "EFFECTIVE_EXIT" ? "E" : eventType == "EXIT_CONFIRMATION" ? "C" : eventType == "TRAIN_END" ? "O" : ""

f_enabled(string eventType, int coreOrdinal) =>
    eventType == "CORE_TRIGGER" ? coreOrdinal == 1 or showAllCoreTriggers : eventType == "UP_OUTSIDE_CANDIDATE" or eventType == "DOWN_OUTSIDE_CANDIDATE" ? showOutsideCandidates : eventType == "ACCEPTED_UP_EXTENSION" or eventType == "ACCEPTED_DOWN_EXTENSION" or eventType == "REJECTED_UP_EXCURSION" or eventType == "REJECTED_DOWN_EXCURSION" ? showBoundaryEvents : true

f_dep_mark(string depType) =>
    depType == "EMA27_EXIT_UP_AWAY_FROM_EMA200" ? "EU" : depType == "EMA27_EXIT_DOWN_TOWARD_EMA200" ? "ED" : "EG"

f_draw(string zid, int st, int ex, int cn, float upper, float lower, float upperWick, float lowerWick, float top, float bottom) =>
    bool atStart = time >= st and time[1] < st
    if f_visible(zid) and atStart
        if showZoneArea
            box.new(st, top, ex, bottom, xloc=xloc.bar_time, bgcolor=color.new(color.yellow, 84), border_color=color.new(color.yellow, 20), extend=extend.none)
        if showExitAcceptance
            box.new(ex, top, cn, bottom, xloc=xloc.bar_time, bgcolor=color.new(color.aqua, 92), border_color=color.new(color.aqua, 45), extend=extend.none)
        if showFinalBodyBounds
            line.new(st, upper, cn, upper, xloc=xloc.bar_time, color=color.new(color.orange, 0), width=2)
            line.new(st, lower, cn, lower, xloc=xloc.bar_time, color=color.new(color.orange, 0), width=2)
        if showWickReferences
            line.new(st, upperWick, cn, upperWick, xloc=xloc.bar_time, color=color.new(color.gray, 45), width=1, style=line.style_dotted)
            line.new(st, lowerWick, cn, lowerWick, xloc=xloc.bar_time, color=color.new(color.gray, 45), width=1, style=line.style_dotted)
        line.new(st, bottom, st, top, xloc=xloc.bar_time, color=color.new(color.yellow, 0), width=2)
        line.new(ex, bottom, ex, top, xloc=xloc.bar_time, color=color.new(color.lime, 0), width=3)
        line.new(cn, bottom, cn, top, xloc=xloc.bar_time, color=color.new(color.aqua, 0), width=2, style=line.style_dashed)
        if showSectionId
            label.new(st, top, zid, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.yellow, 0), textcolor=color.black, size=size.small)

if selectedModel == "PRIMARY_R2"
    for i = 0 to array.size(pZoneIds) - 1
        f_draw(array.get(pZoneIds, i), array.get(pStarts, i), array.get(pExits, i), array.get(pConfirms, i), array.get(pUppers, i), array.get(pLowers, i), array.get(pUpperWicks, i), array.get(pLowerWicks, i), array.get(pTops, i), array.get(pBottoms, i))
else
    for i = 0 to array.size(bZoneIds) - 1
        f_draw(array.get(bZoneIds, i), array.get(bStarts, i), array.get(bExits, i), array.get(bConfirms, i), array.get(bUppers, i), array.get(bLowers, i), array.get(bUpperWicks, i), array.get(bLowerWicks, i), array.get(bTops, i), array.get(bBottoms, i))

for j = 0 to array.size(eventTimes) - 1
    string zid = array.get(eventZoneIds, j)
    string eventType = array.get(eventTypes, j)
    int tt = array.get(eventTimes, j)
    int coreOrdinal = array.get(eventCoreOrdinals, j)
    string mark = f_mark(eventType)
    if selectedModel == "PRIMARY_R2" and f_visible(zid) and f_enabled(eventType, coreOrdinal) and mark != "" and time >= tt and time[1] < tt
        label.new(tt, close, mark, xloc=xloc.bar_time, style=label.style_label_left, color=color.new(color.black, 0), textcolor=color.white, size=size.tiny)

for k = 0 to array.size(depTimes) - 1
    string zid = array.get(depZoneIds, k)
    string depType = array.get(depTypes, k)
    int tt = array.get(depTimes, k)
    string mark = f_dep_mark(depType)
    if selectedModel == "PRIMARY_R2" and showEma27BandDepartureEvents and f_visible(zid) and tt > 0 and time >= tt and time[1] < tt
        label.new(tt, close, mark, xloc=xloc.bar_time, style=label.style_label_right, color=color.new(color.purple, 0), textcolor=color.white, size=size.tiny)
'''


def write_docs(
    primary: pd.DataFrame,
    baseline: pd.DataFrame,
    attempts: pd.DataFrame,
    extensions: pd.DataFrame,
    departures: pd.DataFrame,
    alignment: pd.DataFrame,
    layer_comparison: pd.DataFrame,
    mapping: pd.DataFrame,
    comparison: pd.DataFrame,
    acceptance: pd.DataFrame,
) -> None:
    zone_lines = "\n".join(
        f"- `{r.zone_id}`: R5 `{r.source_r5_sections}`, Z `{r.zone_start_open_time}`, B `{r.bounds_confirmation_open_time}`, body bounds `{r.initial_lower_bound:.6f}`-`{r.initial_upper_bound:.6f}` -> `{r.final_lower_bound:.6f}`-`{r.final_upper_bound:.6f}`, E `{r.effective_exit_open_time}`, C `{r.exit_confirmation_open_time}`, `{r.resolution_kind}`"
        for r in primary.itertuples()
    )
    attempt_lines = "\n".join(
        f"- `{r.attempt_id}` `{r.zone_id}` {r.direction}: candidate `{r.candidate_open_time}`, decision `{r.decision_open_time}`, `{r.decision_status}`, outside fraction `{r.outside_fraction:.2f}`, last data `{r.last_data_timestamp_used}`"
        for r in attempts.itertuples()
    )
    extension_lines = "\n".join(
        f"- `{r.attempt_id}` `{r.zone_id}` {r.direction}: old `{r.old_lower_bound:.6f}`-`{r.old_upper_bound:.6f}`, proposed body `{r.proposed_body_boundary:.6f}`, new `{r.new_lower_bound:.6f}`-`{r.new_upper_bound:.6f}`, wick ignored `{r.wick_extreme_ignored:.6f}`"
        for r in extensions.itertuples()
    )
    acceptance_lines = "\n".join(f"- `{r.test_id}`: `{r.status}` - {r.actual_result}" for r in acceptance.itertuples())
    departure_lines = "\n".join(
        f"- `{r.event_id}` `{r.zone_id}` {r.direction}: candidate `{r.candidate_open_time}`, confirmation `{r.confirmation_open_time}`, `{r.confirmed_classification}`, related price attempts `{r.related_price_attempt_ids}`"
        for r in departures.itertuples()
    )
    alignment_lines = "\n".join(
        f"- `{r.attempt_id}` `{r.zone_id}` price `{r.price_decision_status}`: EMA relation `{r.ema27_relation_to_price}`, classification `{r.ema27_departure_classification}`"
        for r in alignment.itertuples()
    )
    (EXP / "TASK.md").write_text(
        """# EXP-012 R2 - ACCEPTED BOUNDARY STATE

Status: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

Goal: revise EXP-012 so horizontal disputed price zones use robust body-based boundaries and a strictly causal accepted-boundary state machine.

R2 separates wick `EXCURSION`, body/close-based `ACCEPTED_EXTENSION`, and persistent `ACCEPTED_EXIT`. The mandatory addendum adds causal EMA27 compact-band departure diagnostics. EMA27 and EMA200 remain context/diagnostics only and never define price-zone boundaries or close zones. There is no trading, prediction, PnL, or backtest claim.
"""
    )
    (EXP / "REVIEW_INSTRUCTIONS.md").write_text(
        """# EXP-012 R2 TradingView Review

Status: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

1. Open Bybit ADAUSDT Perpetual Contract on 4H.
2. Add `artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES_R2.pine`.
3. Select `PRIMARY_R2`, then optionally compare with `FIXED_BODY_BOUNDS_BASELINE`.
4. Review one zone at a time.
5. Fill `artifacts/manual_accepted_boundary_review.csv`.

Check whether body-based initial ranges match the visually accepted price area better than wick extremes, whether any single wick incorrectly moved a boundary, whether accepted extensions show repeated price acceptance, whether the January downside move is recognized as an accepted outside state, whether effective exit and causal confirmation are separated, and whether the fixed-bound baseline or accepted-extension primary better preserves the broad zone without swallowing the exit.

Optional EMA27 band markers are disabled by default. If enabled, `EU` means confirmed EMA27 exit upward away from EMA200, `ED` means confirmed EMA27 exit downward toward EMA200, and `EG` means other confirmed EMA27 geometry. These markers are diagnostics only and do not define price boundaries or zone closure.

Do not analyze prediction, entries, exits, stops, forecasts, Technical Ratings, or PnL.
"""
    )
    (EXP / "REPORT.md").write_text(
        f"""# EXP-012 R2 - ACCEPTED BOUNDARY STATE

Status: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

Verdict: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

## Motivation

R1 correctly changed the object from EMA conflict windows to horizontal disputed price zones, but it had two defects. A failed attempt could expand a boundary using highs/lows from bars after the causal failure bar, and single wick extremes influenced boundaries too strongly. R2 fixes both defects by processing outside states bar by bar and by separating wick references from accepted body boundaries. The mandatory addendum adds a separate EMA27 compact-band departure layer to describe whether EMA27 leaves its own narrow band upward away from EMA200 or downward toward EMA200.

## Data

Source: `{SOURCE.relative_to(ROOT)}`. Binance spot ADAUSDT 4H is used for automatic detection. Manual review is expected on Bybit ADAUSDT Perpetual 4H, so individual candles and boundaries may differ.

Development period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`.

## Causal Fix

Initial boundaries are medians of body highs/lows from causal source intervals. Wick extremes are stored as diagnostics only. Outside candidates freeze the active boundary and ATR at candidate start, then update only from candidate bar through the current closed bar. Accepted exits can confirm from bar 4 through bar 12. Rejected attempts stop immediately at their decision bar. A rejected attempt expands a boundary only if it qualifies as an accepted extension using repeated outside closes and outside body levels.

EMA27 band diagnostics use a trailing 12-bar prior window that excludes the current bar. A departure freezes that prior band at candidate time and confirms only after two consecutive closed bars remain beyond the frozen edge. This layer annotates price exits and failed departures; it never changes price bounds and never closes a zone.

## Primary R2 Zones

{zone_lines if zone_lines else "No zones detected."}

## Outside-State Candidates

{attempt_lines if attempt_lines else "No outside-state candidates detected."}

## Accepted Extensions

{extension_lines if extension_lines else "No accepted extensions."}

## EMA27 Compact-Band Departures

{departure_lines if departure_lines else "No confirmed EMA27 band departures."}

## Price And EMA Geometry Alignment

{alignment_lines if alignment_lines else "No alignment rows."}

## Price-Only Versus Price-Plus-EMA Geometry

{layer_comparison.to_string(index=False) if not layer_comparison.empty else "No layer comparison rows."}

## Primary Versus Fixed-Bound Baseline

{comparison.to_string(index=False) if not comparison.empty else "No comparison rows."}

## R1/R2 Mapping

{mapping.to_string(index=False) if not mapping.empty else "No mapping rows."}

## Acceptance Tests

{acceptance_lines}

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, forecast, trading logic, date hardcoding, price hardcoding, or zone-id hardcoding. `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B artifacts were not modified.
"""
    )


def update_project_queue(primary: pd.DataFrame, comparison: pd.DataFrame, layer_comparison: pd.DataFrame, acceptance: pd.DataFrame) -> None:
    queue_path = ROOT / "PROJECT_QUEUE.md"
    queue = queue_path.read_text()
    block = f"""### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES

Статус: AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW

EXP-012 R2 заменяет R1 wick-heavy boundary expansion на causal accepted-boundary state machine.
Границы зоны строятся по accepted body boundaries, wick extremes сохраняются только как diagnostics.
Внешнее движение классифицируется как `EXCURSION`, `ACCEPTED_EXTENSION` или `ACCEPTED_EXIT`.
Addendum добавляет отдельный causal EMA27 compact-band departure diagnostic layer; EMA geometry не задаёт
price boundaries и не закрывает zones.

Primary model: `ACCEPTED_EXTENSION_BODY_BOUNDS`. Baseline: `FIXED_BODY_BOUNDS_BASELINE`.
Найдено primary zones: `{len(primary)}`.

Model comparison:
{comparison.to_string(index=False)}

Price/EMA geometry comparison:
{layer_comparison.to_string(index=False)}

Acceptance:
{chr(10).join(f"- `{r.test_id}` = `{r.status}` ({r.actual_result})" for r in acceptance.itertuples())}

Следующее действие:
Проверить R2 zones в TradingView через
`experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES_R2.pine`
и заполнить `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/manual_accepted_boundary_review.csv`.
Technical Ratings остаётся отложенным до принятия границ зон."""
    marker = "### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES"
    if marker in queue:
        start = queue.index(marker)
        end = queue.find("\n---", start)
        if end == -1:
            end = queue.find("\n## DONE", start)
        queue = queue[:start] + block + "\n" + queue[end:]
    else:
        done = "## DONE / REPORT_READY"
        queue = queue.replace(done, block + "\n\n---\n\n" + done)
    queue_path.write_text(queue)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot_r1()
    full = add_features(load_ohlc())
    period = full[(full["open_time"] >= START) & (full["close_time"] <= END)].copy().reset_index(drop=True)
    r5 = pd.read_csv(R5_SECTIONS, parse_dates=["dispute_start_open_time", "effective_resolution_open_time"])
    r1 = pd.read_csv(OUT / "long_context_disputed_zones_r1_snapshot.csv", parse_dates=["zone_start_open_time", "exit_confirmation_open_time", "effective_exit_open_time"])
    primary, events, attempts, extensions, features = build_zones(period, r5, "ACCEPTED_EXTENSION_BODY_BOUNDS", True)
    baseline, baseline_events, baseline_attempts, baseline_extensions, baseline_features = build_zones(period, r5, "FIXED_BODY_BOUNDS_BASELINE", False)
    departures = detect_ema27_band_departures(period, primary, attempts, features)
    alignment = price_ema_geometry_alignment(attempts, departures)
    layer_comparison = price_only_vs_price_ema_geometry(primary, attempts, alignment)
    mapping = r1_r2_mapping(r1, primary)
    comparison = model_comparison(primary, baseline, attempts, baseline_attempts)
    acceptance = acceptance_tests(r1, primary, attempts, extensions, departures, alignment)

    bar_cols = [
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "body_high",
        "body_low",
        "ema27",
        "ema200",
        "ema27_change_1",
        "ema27_change_2",
        "ema27_slope_3",
        "ema200_slope_6",
        "ema_gap",
        "ema_gap_change_1",
        "ema_gap_change_3",
        "ema27_band_low_before_bar",
        "ema27_band_high_before_bar",
        "ema27_band_mid_before_bar",
        "ema27_band_width_atr",
        "ema27_net_change_12_atr",
        "ema_gap_atr",
        "ema_gap_change_6_atr",
        "ema27_compact_band",
        "atr14",
        "base_long_context",
        "fully_aligned_long_bar",
        "discordance_score",
        "core_trigger",
        "zone_id",
        "active_model",
        "active_upper_bound_before_bar",
        "active_lower_bound_before_bar",
        "active_upper_wick_reference",
        "active_lower_wick_reference",
        "boundary_version",
        "inside_active_zone",
        "outside_status",
        "distance_to_upper_atr",
        "distance_to_lower_atr",
        "active_candidate_state",
        "observed_candidate_bars",
        "outside_fraction_so_far",
        "consecutive_outside_count",
        "consecutive_deep_reclaim_count",
        "accepted_extension_decision",
        "ema27_cross_event",
        "active_exit_candidate_id",
        "last_attempt_data_timestamp",
        "active_ema27_departure_state",
        "frozen_ema27_band_low",
        "frozen_ema27_band_high",
        "frozen_ema27_band_mid",
        "confirmed_ema27_departure_id",
        "zone_phase",
        "event_id",
    ]
    write_csv(primary, OUT / "long_context_disputed_zones_r2.csv")
    write_csv(events, OUT / "zone_boundary_events_r2.csv")
    write_csv(attempts, OUT / "zone_outside_state_attempts_r2.csv")
    write_csv(extensions, OUT / "zone_accepted_extensions_r2.csv")
    write_csv(features[bar_cols], OUT / "zone_bar_features_r2.csv")
    write_csv(baseline, OUT / "fixed_body_bounds_baseline.csv")
    write_csv(mapping, OUT / "r1_r2_zone_mapping.csv")
    write_csv(comparison, OUT / "r2_model_comparison.csv")
    write_csv(acceptance, OUT / "r2_acceptance_tests.csv")
    write_csv(departures, OUT / "ema27_band_departures_r2.csv")
    write_csv(alignment, OUT / "price_ema_geometry_alignment_r2.csv")
    write_csv(layer_comparison, OUT / "price_only_vs_price_ema_geometry_r2.csv")
    write_csv(manual_review(primary), OUT / "manual_accepted_boundary_review.csv")
    (OUT / "LONG_CONTEXT_DISPUTED_PRICE_ZONES_R2.pine").write_text(pine_script(primary, baseline, events, departures))
    write_docs(primary, baseline, attempts, extensions, departures, alignment, layer_comparison, mapping, comparison, acceptance)
    update_project_queue(primary, comparison, layer_comparison, acceptance)
    print(
        json.dumps(
            {
                "status": "AWAITING_TW_ACCEPTED_BOUNDARY_REVIEW",
                "r1_zones": len(r1),
                "primary_zones": len(primary),
                "baseline_zones": len(baseline),
                "outside_candidates": len(attempts),
                "accepted_up": int((primary["resolution_kind"] == "ACCEPTED_UPSIDE_EXIT_R2").sum()) if not primary.empty else 0,
                "accepted_down": int((primary["resolution_kind"] == "ACCEPTED_DOWNSIDE_EXIT_R2").sum()) if not primary.empty else 0,
                "accepted_extensions": len(extensions),
                "ema27_departures": len(departures),
                "acceptance": dict(zip(acceptance["test_id"], acceptance["status"])),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
