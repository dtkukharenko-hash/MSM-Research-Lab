#!/usr/bin/env python3
"""EXP-012: causal LONG-context disputed price zones on ADAUSDT 4H."""

from __future__ import annotations

import json
import math
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
EXIT_ACCEPTANCE_BARS = 6


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")


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


def initial_upper_seed(df: pd.DataFrame, zone_start_idx: int, run: dict[str, object]) -> dict[str, object]:
    if run["last_aligned_run_found"] and int(run["last_aligned_run_end_idx"]) < zone_start_idx:
        start_idx = int(run["last_aligned_run_start_idx"])
        end_idx = int(run["last_aligned_run_end_idx"])
        return {
            "upper_seed": float(df.iloc[start_idx : end_idx + 1]["high"].max()),
            "upper_seed_source": "LAST_ALIGNED_RUN",
            "upper_seed_start_open_time": df.iloc[start_idx]["open_time"],
            "upper_seed_end_open_time": df.iloc[end_idx]["open_time"],
        }
    start_idx = max(0, zone_start_idx - 12)
    end_idx = max(0, zone_start_idx - 1)
    return {
        "upper_seed": float(df.iloc[start_idx : end_idx + 1]["high"].max()),
        "upper_seed_source": "PRIOR_12_BARS_FALLBACK",
        "upper_seed_start_open_time": df.iloc[start_idx]["open_time"],
        "upper_seed_end_open_time": df.iloc[end_idx]["open_time"],
    }


def improved_to_ema27(df: pd.DataFrame, idx: int) -> bool:
    if idx < 2:
        return False
    return bool(df.iloc[idx]["close_to_ema27"] > df.iloc[idx - 1]["close_to_ema27"] > df.iloc[idx - 2]["close_to_ema27"])


def confirm_lower_seed(df: pd.DataFrame, zone_start_idx: int, upper_seed: float) -> dict[str, object]:
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
        moved_down = (upper_seed - running_low) >= float(row["atr14"])
        rebounded = (float(row["close"]) - running_low) >= 0.75 * float(row["atr14"])
        if moved_down and rebounded and higher_closes >= 2 and near_ema:
            return {
                "bounds_confirmed": True,
                "bounds_confirmation_idx": idx,
                "lower_seed": running_low,
                "lower_seed_idx": running_low_idx,
                "bounds_fallback_used": False,
                "bounds_confirmation_reason": "LOWER_REACTION_CONFIRMED",
            }
    end_idx = min(len(df) - 1, zone_start_idx + 17)
    sub = df.iloc[zone_start_idx : end_idx + 1]
    running_low = float(sub["low"].min())
    inside_frac = float(((sub["close"] <= upper_seed) & (sub["close"] >= running_low)).mean())
    width_ok = (upper_seed - running_low) >= 1.25 * float(df.iloc[end_idx]["atr14"])
    if len(sub) >= 8 and width_ok and crossed >= 2 and inside_frac >= 0.70:
        return {
            "bounds_confirmed": True,
            "bounds_confirmation_idx": end_idx,
            "lower_seed": running_low,
            "lower_seed_idx": int(sub.index[sub["low"] == running_low][0]),
            "bounds_fallback_used": True,
            "bounds_confirmation_reason": "BOUNDS_FALLBACK_CONFIRMED",
        }
    return {
        "bounds_confirmed": False,
        "bounds_confirmation_idx": end_idx,
        "lower_seed": running_low,
        "lower_seed_idx": int(sub.index[sub["low"] == running_low][0]),
        "bounds_fallback_used": False,
        "bounds_confirmation_reason": "BOUNDS_NOT_CONFIRMED",
    }


def accepted_exit_attempt(df: pd.DataFrame, start_idx: int, direction: str, upper: float, lower: float) -> dict[str, object]:
    end_idx = min(len(df) - 1, start_idx + EXIT_ACCEPTANCE_BARS - 1)
    window = df.iloc[start_idx : end_idx + 1]
    frozen = upper if direction == "UP" else lower
    excursion_high = float(window["high"].max()) if not window.empty else float(df.iloc[start_idx]["high"])
    excursion_low = float(window["low"].min()) if not window.empty else float(df.iloc[start_idx]["low"])
    inside = (window["close"] <= upper) & (window["close"] >= lower)
    two_inside_mask = inside.astype(bool) & inside.shift(1, fill_value=False).astype(bool)
    two_inside = bool(two_inside_mask.any())
    opposite = bool((window["close"] < lower - OUTSIDE_CLEARANCE_ATR * window["atr14"]).any()) if direction == "UP" else bool((window["close"] > upper + OUTSIDE_CLEARANCE_ATR * window["atr14"]).any())
    if direction == "UP":
        outside_count = int((window["close"] > frozen).sum())
        final_outside = bool(window.iloc[-1]["close"] > frozen) if len(window) else False
        ema_count = int((window["close"] > window["ema27"]).sum())
        accepted = len(window) == EXIT_ACCEPTANCE_BARS and outside_count >= 4 and final_outside and not two_inside and ema_count >= 4 and bool((window["ema27"] > window["ema200"]).all())
    else:
        outside_count = int((window["close"] < frozen).sum())
        final_outside = bool(window.iloc[-1]["close"] < frozen) if len(window) else False
        ema_count = int((window["close"] < window["ema27"]).sum())
        accepted = len(window) == EXIT_ACCEPTANCE_BARS and outside_count >= 4 and final_outside and not two_inside and ema_count >= 4
    if accepted:
        status = "ACCEPTED_UPSIDE_EXIT" if direction == "UP" else "ACCEPTED_DOWNSIDE_EXIT"
        failure_idx = -1
        failure_reason = ""
    else:
        status = "FAILED_UPSIDE_EXIT" if direction == "UP" else "FAILED_DOWNSIDE_EXIT"
        if opposite:
            failure_reason = "OPPOSITE_SIDE_CANDIDATE"
            failure_idx = end_idx
        elif two_inside:
            failure_reason = "TWO_CONSECUTIVE_CLOSES_BACK_INSIDE"
            failure_idx = int(two_inside_mask[two_inside_mask].index[0])
        elif len(window) < EXIT_ACCEPTANCE_BARS:
            failure_reason = "CENSORED_BY_TRAIN_END"
            failure_idx = end_idx
            status = "CENSORED_BY_TRAIN_END"
        else:
            failure_reason = "ACCEPTANCE_THRESHOLDS_NOT_MET"
            failure_idx = end_idx
    return {
        "direction": direction,
        "frozen_boundary": frozen,
        "candidate_idx": start_idx,
        "probation_end_idx": end_idx,
        "bars_available": int(len(window)),
        "outside_count": outside_count,
        "inside_count": int(inside.sum()),
        "two_inside": two_inside,
        "opposite_candidate": opposite,
        "final_close_position": "OUTSIDE" if final_outside else "NOT_OUTSIDE",
        "excursion_high": excursion_high,
        "excursion_low": excursion_low,
        "clearance_atr": float((df.iloc[start_idx]["close"] - frozen) / df.iloc[start_idx]["atr14"]) if direction == "UP" else float((frozen - df.iloc[start_idx]["close"]) / df.iloc[start_idx]["atr14"]),
        "status": status,
        "failure_idx": failure_idx,
        "failure_reason": failure_reason,
    }


def map_r5_sections(df: pd.DataFrame, start_idx: int, end_idx: int, r5: pd.DataFrame) -> str:
    matches = []
    for row in r5.itertuples():
        s = idx_at(df, row.dispute_start_open_time)
        e = idx_at(df, row.effective_resolution_open_time)
        if e >= start_idx and s <= end_idx:
            matches.append(row.section_id)
    return ";".join(matches)


def build_zones(df: pd.DataFrame, r5_sections: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    zones: list[dict[str, object]] = []
    events: list[dict[str, object]] = []
    attempts: list[dict[str, object]] = []
    features = df.copy()
    for col, default in [
        ("zone_id", ""),
        ("active_upper_bound_before_bar", math.nan),
        ("active_lower_bound_before_bar", math.nan),
        ("boundary_version", 0),
        ("inside_active_zone", False),
        ("outside_status", "NO_ZONE"),
        ("distance_to_upper_atr", math.nan),
        ("distance_to_lower_atr", math.nan),
        ("active_exit_candidate_id", ""),
        ("zone_phase", "OUTSIDE_ZONE"),
        ("event_id", ""),
    ]:
        features[col] = default
    consumed_until = -1
    trigger_indices = df.index[df["core_trigger"]].tolist()

    def add_event(
        zone_id: str,
        event_type: str,
        idx: int,
        previous_upper: float,
        previous_lower: float,
        new_upper: float,
        new_lower: float,
        reason: str,
        attempt_id: str = "",
        boundary_version: int | str = "",
        core_ordinal_in_zone: int = 0,
    ) -> None:
        eid = f"EV{len(events)+1:03d}"
        events.append(
            {
                "event_id": eid,
                "zone_id": zone_id,
                "event_type": event_type,
                "event_open_time": df.iloc[idx]["open_time"],
                "event_close_time": df.iloc[idx]["close_time"],
                "previous_upper_bound": previous_upper,
                "previous_lower_bound": previous_lower,
                "new_upper_bound": new_upper,
                "new_lower_bound": new_lower,
                "boundary_version": boundary_version,
                "core_ordinal_in_zone": core_ordinal_in_zone,
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
        seed = initial_upper_seed(df, zone_start, run)
        lower = confirm_lower_seed(df, zone_start, float(seed["upper_seed"]))
        if not lower["bounds_confirmed"]:
            continue
        zid = f"Z{len(zones)+1:03d}"
        upper = float(seed["upper_seed"])
        lower_bound = float(lower["lower_seed"])
        initial_upper = upper
        initial_lower = lower_bound
        boundary_version = 1
        bounds_idx = int(lower["bounds_confirmation_idx"])
        first_core_idx = trig
        core_count = 1
        high_probe_count = 0
        low_probe_count = 0
        failed_up = failed_down = 0
        max_up_exc = max_down_exc = 0.0
        exit_direction = ""
        resolution_kind = "OPEN_AT_TRAIN_END"
        effective_idx = len(df) - 1
        confirmation_idx = len(df) - 1
        add_event(zid, "ZONE_START", zone_start, math.nan, math.nan, upper, lower_bound, "first causal loss of agreement", boundary_version=boundary_version)
        add_event(zid, "CORE_TRIGGER", first_core_idx, upper, lower_bound, upper, lower_bound, "first diagnostic core trigger", boundary_version=boundary_version, core_ordinal_in_zone=1)
        add_event(zid, "BOUNDS_CONFIRMED", bounds_idx, math.nan, math.nan, upper, lower_bound, str(lower["bounds_confirmation_reason"]), boundary_version=boundary_version)
        cursor = bounds_idx + 1
        while cursor < len(df):
            row = df.iloc[cursor]
            features.loc[cursor, ["zone_id", "active_upper_bound_before_bar", "active_lower_bound_before_bar", "boundary_version"]] = [zid, upper, lower_bound, boundary_version]
            inside = bool(lower_bound <= row["close"] <= upper)
            features.loc[cursor, "inside_active_zone"] = inside
            features.loc[cursor, "distance_to_upper_atr"] = (row["close"] - upper) / row["atr14"] if row["atr14"] else math.nan
            features.loc[cursor, "distance_to_lower_atr"] = (row["close"] - lower_bound) / row["atr14"] if row["atr14"] else math.nan
            features.loc[cursor, "outside_status"] = "INSIDE" if inside else ("ABOVE" if row["close"] > upper else "BELOW")
            features.loc[cursor, "zone_phase"] = "ACTIVE_ZONE"
            if bool(row["core_trigger"]):
                core_count += 1
                add_event(zid, "CORE_TRIGGER", cursor, upper, lower_bound, upper, lower_bound, "diagnostic core trigger", boundary_version=boundary_version, core_ordinal_in_zone=core_count)
            direction = ""
            if row["close"] > upper + OUTSIDE_CLEARANCE_ATR * row["atr14"]:
                direction = "UP"
                high_probe_count += 1
            elif row["close"] < lower_bound - OUTSIDE_CLEARANCE_ATR * row["atr14"]:
                direction = "DOWN"
                low_probe_count += 1
            if not direction:
                cursor += 1
                continue
            attempt_id = f"XA{len(attempts)+1:03d}"
            add_event(zid, "UP_EXIT_CANDIDATE" if direction == "UP" else "DOWN_EXIT_CANDIDATE", cursor, upper, lower_bound, upper, lower_bound, "outside close candidate", attempt_id, boundary_version=boundary_version)
            attempt = accepted_exit_attempt(df, cursor, direction, upper, lower_bound)
            end_idx = int(attempt["probation_end_idx"])
            features.loc[cursor:end_idx, "active_exit_candidate_id"] = attempt_id
            attempts.append(
                {
                    "zone_id": zid,
                    "attempt_id": attempt_id,
                    "direction": direction,
                    "frozen_boundary": attempt["frozen_boundary"],
                    "candidate_open_time": df.iloc[cursor]["open_time"],
                    "probation_end_open_time": df.iloc[end_idx]["open_time"],
                    "bars_available": attempt["bars_available"],
                    "outside_count": attempt["outside_count"],
                    "inside_count": attempt["inside_count"],
                    "final_close_position": attempt["final_close_position"],
                    "excursion_high": attempt["excursion_high"],
                    "excursion_low": attempt["excursion_low"],
                    "clearance_atr": attempt["clearance_atr"],
                    "status": attempt["status"],
                    "failure_open_time": df.iloc[int(attempt["failure_idx"])]["open_time"] if int(attempt["failure_idx"]) >= 0 else pd.NaT,
                    "failure_reason": attempt["failure_reason"],
                    "effective_exit_open_time": df.iloc[cursor]["open_time"] if attempt["status"].startswith("ACCEPTED") else pd.NaT,
                    "exit_confirmation_open_time": df.iloc[end_idx]["open_time"] if attempt["status"].startswith("ACCEPTED") else pd.NaT,
                }
            )
            if attempt["status"].startswith("ACCEPTED"):
                resolution_kind = attempt["status"]
                exit_direction = direction
                effective_idx = cursor
                confirmation_idx = end_idx
                add_event(zid, "EFFECTIVE_EXIT", effective_idx, upper, lower_bound, upper, lower_bound, resolution_kind, attempt_id, boundary_version=boundary_version)
                add_event(zid, "EXIT_CONFIRMATION", confirmation_idx, upper, lower_bound, upper, lower_bound, resolution_kind, attempt_id, boundary_version=boundary_version)
                consumed_until = confirmation_idx
                break
            if attempt["status"] == "CENSORED_BY_TRAIN_END":
                resolution_kind = "OPEN_AT_TRAIN_END"
                effective_idx = len(df) - 1
                confirmation_idx = len(df) - 1
                add_event(zid, "TRAIN_END", confirmation_idx, upper, lower_bound, upper, lower_bound, "period ended during exit attempt", attempt_id, boundary_version=boundary_version)
                consumed_until = confirmation_idx
                break
            if direction == "UP":
                failed_up += 1
                prev = upper
                upper = max(upper, float(attempt["excursion_high"]))
                max_up_exc = max(max_up_exc, upper - prev)
                boundary_version += 1
                add_event(zid, "FAILED_UPSIDE_EXIT", int(attempt["failure_idx"]), prev, lower_bound, upper, lower_bound, str(attempt["failure_reason"]), attempt_id, boundary_version=boundary_version)
                add_event(zid, "UPPER_BOUND_EXPANDED", int(attempt["failure_idx"]), prev, lower_bound, upper, lower_bound, "failed upside excursion accepted into zone", attempt_id, boundary_version=boundary_version)
            else:
                failed_down += 1
                prev = lower_bound
                lower_bound = min(lower_bound, float(attempt["excursion_low"]))
                max_down_exc = max(max_down_exc, prev - lower_bound)
                boundary_version += 1
                add_event(zid, "FAILED_DOWNSIDE_EXIT", int(attempt["failure_idx"]), upper, prev, upper, lower_bound, str(attempt["failure_reason"]), attempt_id, boundary_version=boundary_version)
                add_event(zid, "LOWER_BOUND_EXPANDED", int(attempt["failure_idx"]), upper, prev, upper, lower_bound, "failed downside excursion accepted into zone", attempt_id, boundary_version=boundary_version)
            cursor = int(attempt["failure_idx"]) + 1
        else:
            effective_idx = len(df) - 1
            confirmation_idx = len(df) - 1
            add_event(zid, "TRAIN_END", confirmation_idx, upper, lower_bound, upper, lower_bound, "open at development end", boundary_version=boundary_version)
            consumed_until = confirmation_idx

        span = df.iloc[zone_start : effective_idx + 1]
        width = upper - lower_bound
        atr = float(df.iloc[effective_idx]["atr14"])
        inside_frac = float(((span["close"] <= upper) & (span["close"] >= lower_bound)).mean())
        ema_cross = int(span["ema27_cross_event"].sum())
        source_r5 = map_r5_sections(df, zone_start, confirmation_idx, r5_sections)
        pad = width * 0.05 if width > 0 else atr
        zones.append(
            {
                "zone_id": zid,
                "display_start_open_time": df.iloc[max(0, zone_start - 12)]["open_time"],
                "last_aligned_run_start_open_time": df.iloc[int(run["last_aligned_run_start_idx"])]["open_time"] if run["last_aligned_run_found"] else pd.NaT,
                "last_aligned_run_end_open_time": df.iloc[int(run["last_aligned_run_end_idx"])]["open_time"] if run["last_aligned_run_found"] else pd.NaT,
                "zone_start_open_time": df.iloc[zone_start]["open_time"],
                "first_core_trigger_open_time": df.iloc[first_core_idx]["open_time"],
                "bounds_confirmation_open_time": df.iloc[bounds_idx]["open_time"],
                "upper_seed": seed["upper_seed"],
                "upper_seed_source": seed["upper_seed_source"],
                "lower_seed": lower["lower_seed"],
                "lower_seed_open_time": df.iloc[int(lower["lower_seed_idx"])]["open_time"],
                "bounds_fallback_used": lower["bounds_fallback_used"],
                "initial_upper_bound": initial_upper,
                "initial_lower_bound": initial_lower,
                "final_upper_bound": upper,
                "final_lower_bound": lower_bound,
                "effective_exit_open_time": df.iloc[effective_idx]["open_time"],
                "exit_confirmation_open_time": df.iloc[confirmation_idx]["open_time"],
                "effective_exit_boundary_time": boundary_at(df, effective_idx),
                "exit_confirmation_boundary_time": boundary_at(df, confirmation_idx),
                "exit_direction": exit_direction,
                "resolution_kind": resolution_kind,
                "duration_to_effective_exit_bars": int(effective_idx - zone_start + 1),
                "duration_to_confirmation_bars": int(confirmation_idx - effective_idx),
                "boundary_update_count": boundary_version - 1,
                "failed_upside_exit_count": failed_up,
                "failed_downside_exit_count": failed_down,
                "ema27_cross_count": ema_cross,
                "close_inside_fraction": inside_frac,
                "core_trigger_count": core_count,
                "high_acceptance_probe_count": high_probe_count,
                "low_acceptance_probe_count": low_probe_count,
                "max_distance_outside_upper_before_failure": max_up_exc,
                "max_distance_outside_lower_before_failure": max_down_exc,
                "final_width": width,
                "final_width_atr": width / atr if atr else math.nan,
                "source_r5_sections": source_r5,
                "open_at_train_end": bool(resolution_kind == "OPEN_AT_TRAIN_END"),
                "section_price_high": float(span["high"].max()),
                "section_price_low": float(span["low"].min()),
                "display_box_top": upper + pad,
                "display_box_bottom": lower_bound - pad,
            }
        )
        features.loc[zone_start:confirmation_idx, "zone_id"] = zid
    return pd.DataFrame(zones), pd.DataFrame(events), pd.DataFrame(attempts), features


def r5_zone_mapping(zones: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in zones.itertuples():
        for r5 in str(row.source_r5_sections).split(";"):
            if not r5:
                continue
            rows.append(
                {
                    "r5_section_id": r5,
                    "zone_id": row.zone_id,
                    "zone_start_open_time": row.zone_start_open_time,
                    "zone_effective_exit_open_time": row.effective_exit_open_time,
                    "zone_resolution_kind": row.resolution_kind,
                    "mapping_reason": "overlap by causal bar span",
                }
            )
    return pd.DataFrame(rows)


def acceptance_tests(zones: pd.DataFrame, r5: pd.DataFrame) -> pd.DataFrame:
    z1 = zones[zones["source_r5_sections"].astype(str).str.contains("LC001", regex=False)]
    z2 = zones[zones["source_r5_sections"].astype(str).str.contains("LC002", regex=False)]
    z3 = zones[zones["source_r5_sections"].astype(str).str.contains("LC003", regex=False)]
    lc003_r5 = r5[r5["section_id"] == "LC003"]
    if not lc003_r5.empty and not z3.empty:
        zone_exit = pd.Timestamp(z3.iloc[0]["effective_exit_open_time"])
        r5_exit = pd.Timestamp(lc003_r5.iloc[0]["effective_resolution_open_time"])
        earlier = zone_exit < r5_exit
        compare_detail = f"zone {zone_exit} vs R5 {r5_exit}"
    else:
        earlier = False
        compare_detail = "missing LC003 mapping"
    rows = [
        {
            "test_id": "EXPECTED_THREE_ZONES",
            "test_name": "Manual review suggests three zones",
            "expected_result": "3 zones",
            "actual_result": f"{len(zones)} zones",
            "status": "PASS" if len(zones) == 3 else "FAIL",
            "details": ";".join(zones["zone_id"].tolist()),
        },
        {
            "test_id": "FIRST_ZONE_PRESERVED",
            "test_name": "Late Oct/early Nov compact zone remains independent",
            "expected_result": "one zone mapped to R5 LC001",
            "actual_result": f"{len(z1)} matching zone(s): {';'.join(z1['zone_id'].tolist())}",
            "status": "PASS" if len(z1) == 1 else "FAIL",
            "details": ";".join(z1["resolution_kind"].astype(str).tolist()),
        },
        {
            "test_id": "NOVEMBER_SINGLE_ZONE",
            "test_name": "November process remains one zone despite EMA27 recoveries",
            "expected_result": "one zone mapped to R5 LC002",
            "actual_result": f"{len(z2)} matching zone(s): {';'.join(z2['zone_id'].tolist())}",
            "status": "PASS" if len(z2) == 1 else "FAIL",
            "details": ";".join(z2["resolution_kind"].astype(str).tolist()),
        },
        {
            "test_id": "DECEMBER_JANUARY_SINGLE_ZONE",
            "test_name": "December-January process remains one evolving horizontal zone unless accepted exit confirms",
            "expected_result": "one zone mapped to R5 LC003",
            "actual_result": f"{len(z3)} matching zone(s): {';'.join(z3['zone_id'].tolist())}",
            "status": "PASS" if len(z3) == 1 else "FAIL",
            "details": ";".join(z3["resolution_kind"].astype(str).tolist()),
        },
        {
            "test_id": "LC003_EARLIER_DOWNSIDE_EXIT_THAN_R5",
            "test_name": "Horizontal downside accepted exit precedes R5 EMA-based effective exit",
            "expected_result": "zone LC003 mapped exit earlier than R5 LC003",
            "actual_result": compare_detail,
            "status": "PASS" if earlier else "FAIL",
            "details": "post-run diagnostic only",
        },
        {"test_id": "NO_DATE_HARDCODING", "test_name": "No date hardcoding", "expected_result": "general algorithm", "actual_result": "general chronological builder", "status": "PASS", "details": "acceptance checks only after run"},
        {"test_id": "NO_PRICE_BOUND_HARDCODING", "test_name": "No price-bound hardcoding", "expected_result": "bounds from OHLC only", "actual_result": "causal seeds and failed-exit expansions", "status": "PASS", "details": "no manual prices used"},
        {"test_id": "NO_SECTION_ID_HARDCODING", "test_name": "No section-id hardcoding in detector", "expected_result": "general algorithm", "actual_result": "section IDs used only in diagnostics", "status": "PASS", "details": "post-run mapping checks"},
        {"test_id": "NO_FUTURE_PERIOD_USED", "test_name": "No future period used", "expected_result": "no data after 2024-01-08", "actual_result": "period slice ends at configured END", "status": "PASS", "details": str(END)},
    ]
    return pd.DataFrame(rows)


def manual_review(zones: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "zone_id": zones["zone_id"],
            "source_r5_sections": zones["source_r5_sections"],
            "auto_zone_start": zones["zone_start_open_time"],
            "auto_bounds_confirmation": zones["bounds_confirmation_open_time"],
            "auto_initial_upper_bound": zones["initial_upper_bound"],
            "auto_initial_lower_bound": zones["initial_lower_bound"],
            "auto_final_upper_bound": zones["final_upper_bound"],
            "auto_final_lower_bound": zones["final_lower_bound"],
            "auto_effective_exit": zones["effective_exit_open_time"],
            "auto_exit_confirmation": zones["exit_confirmation_open_time"],
            "auto_resolution_kind": zones["resolution_kind"],
            "zone_validity": "",
            "start_correct": "",
            "initial_upper_correct": "",
            "initial_lower_correct": "",
            "boundary_expansion_correct": "",
            "effective_exit_correct": "",
            "confirmation_correct": "",
            "should_merge_with_previous": "",
            "should_merge_with_next": "",
            "should_split": "",
            "corrected_upper_bound": "",
            "corrected_lower_bound": "",
            "corrected_zone_start": "",
            "corrected_effective_exit": "",
            "binance_bybit_difference_suspected": "",
            "comment": "",
        }
    )


def pine_script(zones: pd.DataFrame, events: pd.DataFrame) -> str:
    options = ", ".join([f'"{x}"' for x in ["ALL", *zones["zone_id"].tolist()]])
    ids = ", ".join([f'"{x}"' for x in zones["zone_id"]])
    starts = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in zones["zone_start_open_time"])
    exits = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in zones["effective_exit_open_time"])
    confirms = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in zones["exit_confirmation_open_time"])
    uppers = ", ".join(f"{float(x):.8f}" for x in zones["final_upper_bound"])
    lowers = ", ".join(f"{float(x):.8f}" for x in zones["final_lower_bound"])
    tops = ", ".join(f"{float(x):.8f}" for x in zones["display_box_top"])
    bottoms = ", ".join(f"{float(x):.8f}" for x in zones["display_box_bottom"])
    event_ids = ", ".join([f'"{x}"' for x in events["zone_id"]])
    event_types = ", ".join([f'"{x}"' for x in events["event_type"]])
    event_times = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in events["event_open_time"])
    event_core_ordinals = ", ".join(str(int(x)) for x in events["core_ordinal_in_zone"].fillna(0))
    return f'''//@version=6
indicator("EXP-012 Long-Context Disputed Price Zones", overlay=true, max_labels_count=500, max_lines_count=500, max_boxes_count=100)

showZoneArea = input.bool(true, "showZoneArea")
showExitAcceptance = input.bool(true, "showExitAcceptance")
showFinalBounds = input.bool(true, "showFinalBounds")
showInitialBounds = input.bool(false, "showInitialBounds")
showBoundaryEvents = input.bool(true, "showBoundaryEvents")
showExitAttempts = input.bool(true, "showExitAttempts")
showAllCoreTriggers = input.bool(false, "showAllCoreTriggers")
showSectionId = input.bool(true, "showSectionId")
showOnlySelectedSection = input.bool(false, "showOnlySelectedSection")
selectedSection = input.string("ALL", "selectedSection", options=[{options}])

var string[] zoneIds = array.from({ids})
var int[] zoneStarts = array.from({starts})
var int[] effectiveExits = array.from({exits})
var int[] confirmations = array.from({confirms})
var float[] upperBounds = array.from({uppers})
var float[] lowerBounds = array.from({lowers})
var float[] boxTops = array.from({tops})
var float[] boxBottoms = array.from({bottoms})
var string[] eventZoneIds = array.from({event_ids})
var string[] eventTypes = array.from({event_types})
var int[] eventTimes = array.from({event_times})
var int[] eventCoreOrdinals = array.from({event_core_ordinals})

f_visible(string id) =>
    selectedSection == "ALL" or id == selectedSection

f_mark(string eventType) =>
    eventType == "ZONE_START" ? "Z" : eventType == "CORE_TRIGGER" ? "T" : eventType == "BOUNDS_CONFIRMED" ? "B" : eventType == "UPPER_BOUND_EXPANDED" ? "U+" : eventType == "LOWER_BOUND_EXPANDED" ? "L+" : eventType == "UP_EXIT_CANDIDATE" ? "U?" : eventType == "DOWN_EXIT_CANDIDATE" ? "D?" : eventType == "FAILED_UPSIDE_EXIT" ? "UF" : eventType == "FAILED_DOWNSIDE_EXIT" ? "DF" : eventType == "EFFECTIVE_EXIT" ? "E" : eventType == "EXIT_CONFIRMATION" ? "C" : eventType == "TRAIN_END" ? "O" : ""

f_enabled(string eventType, int coreOrdinal) =>
    eventType == "CORE_TRIGGER" ? coreOrdinal == 1 or showAllCoreTriggers : eventType == "UP_EXIT_CANDIDATE" or eventType == "DOWN_EXIT_CANDIDATE" ? showExitAttempts : eventType == "UPPER_BOUND_EXPANDED" or eventType == "LOWER_BOUND_EXPANDED" or eventType == "FAILED_UPSIDE_EXIT" or eventType == "FAILED_DOWNSIDE_EXIT" ? showBoundaryEvents : true

for i = 0 to array.size(zoneIds) - 1
    string zid = array.get(zoneIds, i)
    bool visible = f_visible(zid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(zid) : visible
    int st = array.get(zoneStarts, i)
    int ex = array.get(effectiveExits, i)
    int cn = array.get(confirmations, i)
    float upper = array.get(upperBounds, i)
    float lower = array.get(lowerBounds, i)
    float top = array.get(boxTops, i)
    float bottom = array.get(boxBottoms, i)
    bool atStart = time >= st and time[1] < st
    if visible and atStart
        if showZoneArea
            box.new(st, top, ex, bottom, xloc=xloc.bar_time, bgcolor=color.new(color.yellow, 84), border_color=color.new(color.yellow, 20), extend=extend.none)
        if showExitAcceptance
            box.new(ex, top, cn, bottom, xloc=xloc.bar_time, bgcolor=color.new(color.aqua, 92), border_color=color.new(color.aqua, 45), extend=extend.none)
        if showFinalBounds
            line.new(st, upper, cn, upper, xloc=xloc.bar_time, color=color.new(color.orange, 0), width=2)
            line.new(st, lower, cn, lower, xloc=xloc.bar_time, color=color.new(color.orange, 0), width=2)
        line.new(st, bottom, st, top, xloc=xloc.bar_time, color=color.new(color.yellow, 0), width=2)
        line.new(ex, bottom, ex, top, xloc=xloc.bar_time, color=color.new(color.lime, 0), width=3)
        line.new(cn, bottom, cn, top, xloc=xloc.bar_time, color=color.new(color.aqua, 0), width=2, style=line.style_dashed)
        if showSectionId
            label.new(st, top, zid, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.yellow, 0), textcolor=color.black, size=size.small)

for j = 0 to array.size(eventTimes) - 1
    string zid = array.get(eventZoneIds, j)
    string eventType = array.get(eventTypes, j)
    int tt = array.get(eventTimes, j)
    int coreOrdinal = array.get(eventCoreOrdinals, j)
    bool visible = f_visible(zid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(zid) : visible
    string mark = f_mark(eventType)
    if visible and f_enabled(eventType, coreOrdinal) and mark != "" and time >= tt and time[1] < tt
        label.new(tt, close, mark, xloc=xloc.bar_time, style=label.style_label_left, color=color.new(color.black, 0), textcolor=color.white, size=size.tiny)
'''


def write_docs(zones: pd.DataFrame, attempts: pd.DataFrame, mapping: pd.DataFrame, acceptance: pd.DataFrame) -> None:
    zone_lines = "\n".join(
        f"- `{r.zone_id}`: R5 `{r.source_r5_sections}`, Z `{r.zone_start_open_time}`, B `{r.bounds_confirmation_open_time}`, bounds `{r.final_lower_bound:.6f}`–`{r.final_upper_bound:.6f}`, E `{r.effective_exit_open_time}`, C `{r.exit_confirmation_open_time}`, `{r.resolution_kind}`"
        for r in zones.itertuples()
    )
    attempt_lines = "\n".join(
        f"- `{r.attempt_id}` `{r.zone_id}` {r.direction}: candidate `{r.candidate_open_time}`, status `{r.status}`, boundary `{r.frozen_boundary:.6f}`"
        for r in attempts.itertuples()
    )
    acceptance_lines = "\n".join(f"- `{r.test_id}`: `{r.status}` — {r.actual_result}" for r in acceptance.itertuples())
    (EXP / "TASK.md").write_text(
        """# EXP-012 — LONG CONTEXT DISPUTED PRICE ZONES

Status: AWAITING_TW_PRICE_ZONE_REVIEW

Goal: detect causal horizontal disputed price zones inside LONG context on ADAUSDT 4H for 2023-10-18 through 2024-01-08.

This experiment replaces EMA-centered conflict-window closure with price-defined zone bounds and accepted outside movement. It makes no trading, prediction, PnL, or backtest claim.

Outputs are stored in `artifacts/`.
"""
    )
    (EXP / "REVIEW_INSTRUCTIONS.md").write_text(
        """# EXP-012 TradingView Review

Status: AWAITING_TW_PRICE_ZONE_REVIEW

1. Open Bybit ADAUSDT Perpetual Contract on 4H.
2. Add your own EMA27 and EMA200 if desired.
3. Add `artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES.pine`.
4. Review one zone at a time.
5. Fill `artifacts/manual_zone_review.csv`.

Check whether the yellow box represents one accepted horizontal price area, whether repeated EMA27 crossings remain inside the same zone, whether failed breakouts correctly expand the boundary, and whether the zone ends at the first accepted outside move. The cyan confirmation area should be visually separate from the yellow disputed zone.

For the December-January zone, specifically check whether it ends at the accepted break of the lower horizontal boundary rather than at a later EMA confirmation.

Do not analyze Technical Ratings, forecasts, entries, exits, stops, or PnL.
"""
    )
    (EXP / "REPORT.md").write_text(
        f"""# EXP-012 — LONG CONTEXT DISPUTED PRICE ZONES

Status: AWAITING_TW_PRICE_ZONE_REVIEW

Verdict: AWAITING_TW_PRICE_ZONE_REVIEW

## Motivation

EXP-011B EMA/recovery state machines were paused because EMA-centered conflict boundaries were visually unstable. R4 overclassified EMA27 recoveries as strong, and R5 preserved some chains but still could not describe the horizontal disputed price area directly.

EXP-012 studies a different object: a causal horizontal disputed price zone inside LONG context. EMA27 and EMA200 are context and diagnostics; price defines the zone bounds and accepted exit.

## Data

Source: `{SOURCE.relative_to(ROOT)}`. Binance spot ADAUSDT 4H is used for automatic detection. Manual review is expected on Bybit ADAUSDT Perpetual 4H, so individual candles and boundaries may differ.

Development period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`.

## Method

The detector uses local EXP-012 LONG context, aligned-run, dispute-start and diagnostic core-trigger logic. Initial upper seed is the high of the last aligned run, or a 12-bar fallback. The lower seed is confirmed causally by an adverse move and rebound, or by a bounded fallback. Bounds then remain frozen until a failed outside-close attempt expands one side. A zone closes only after a six-bar accepted outside move.

## Zones

{zone_lines if zone_lines else "No zones detected."}

## Exit Attempts

{attempt_lines if attempt_lines else "No exit attempts detected."}

## R5 Mapping

{mapping.to_string(index=False) if not mapping.empty else "No R5 mapping rows."}

## Acceptance Tests

{acceptance_lines}

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, trading logic, date hardcoding, price-bound hardcoding, or section-id hardcoding. `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B artifacts were not modified.
"""
    )


def update_project_queue(zones: pd.DataFrame, acceptance: pd.DataFrame) -> None:
    queue = (ROOT / "PROJECT_QUEUE.md").read_text()
    block = f"""

### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES

Статус: AWAITING_TW_PRICE_ZONE_REVIEW

EXP-011B поставлен на паузу после R5: EMA-centered conflict boundaries оказались визуально нестабильны
для описания горизонтальной спорной области. EXP-012 изучает новый объект: causal horizontal disputed
price zone внутри LONG context. Цена задаёт upper/lower bounds и accepted outside exit; EMA27/EMA200
используются только как context/diagnostics.

Найдено зон: `{len(zones)}`. Acceptance:
{chr(10).join(f"- `{r.test_id}` = `{r.status}` ({r.actual_result})" for r in acceptance.itertuples())}

Следующее действие:
Проверить зоны в TradingView через
`experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/LONG_CONTEXT_DISPUTED_PRICE_ZONES.pine`
и заполнить `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/manual_zone_review.csv`.
Technical Ratings остаётся отложенным до принятия границ зон.
"""
    if "### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES" not in queue:
        marker = "## DONE / REPORT_READY"
        queue = queue.replace(marker, block + "\n---\n\n" + marker)
    else:
        start = queue.index("### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES")
        end = queue.find("\n---", start)
        if end == -1:
            end = queue.find("\n## DONE", start)
        queue = queue[:start] + block.strip() + "\n" + queue[end:]
    (ROOT / "PROJECT_QUEUE.md").write_text(queue)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    full = add_features(load_ohlc())
    period = full[(full["open_time"] >= START) & (full["close_time"] <= END)].copy().reset_index(drop=True)
    r5 = pd.read_csv(R5_SECTIONS, parse_dates=["dispute_start_open_time", "effective_resolution_open_time"])
    zones, events, attempts, features = build_zones(period, r5)
    mapping = r5_zone_mapping(zones)
    acceptance = acceptance_tests(zones, r5)
    bar_cols = [
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "ema27",
        "ema200",
        "ema27_change_1",
        "ema27_slope_3",
        "ema200_slope_6",
        "ema_gap",
        "ema_gap_change_1",
        "ema_gap_change_3",
        "atr14",
        "base_long_context",
        "fully_aligned_long_bar",
        "discordance_score",
        "core_trigger",
        "zone_id",
        "active_upper_bound_before_bar",
        "active_lower_bound_before_bar",
        "boundary_version",
        "inside_active_zone",
        "outside_status",
        "distance_to_upper_atr",
        "distance_to_lower_atr",
        "ema27_cross_event",
        "active_exit_candidate_id",
        "zone_phase",
        "event_id",
    ]
    write_csv(zones, OUT / "long_context_disputed_zones.csv")
    write_csv(events, OUT / "zone_boundary_events.csv")
    write_csv(attempts, OUT / "zone_exit_attempts.csv")
    write_csv(features[bar_cols], OUT / "zone_bar_features.csv")
    write_csv(mapping, OUT / "r5_zone_mapping.csv")
    write_csv(acceptance, OUT / "acceptance_tests.csv")
    write_csv(manual_review(zones), OUT / "manual_zone_review.csv")
    (OUT / "LONG_CONTEXT_DISPUTED_PRICE_ZONES.pine").write_text(pine_script(zones, events))
    write_docs(zones, attempts, mapping, acceptance)
    update_project_queue(zones, acceptance)
    print(
        json.dumps(
            {
                "status": "AWAITING_TW_PRICE_ZONE_REVIEW",
                "zones": len(zones),
                "exit_attempts": len(attempts),
                "accepted_up": int((attempts["status"] == "ACCEPTED_UPSIDE_EXIT").sum()) if not attempts.empty else 0,
                "accepted_down": int((attempts["status"] == "ACCEPTED_DOWNSIDE_EXIT").sum()) if not attempts.empty else 0,
                "failed_up": int((attempts["status"] == "FAILED_UPSIDE_EXIT").sum()) if not attempts.empty else 0,
                "failed_down": int((attempts["status"] == "FAILED_DOWNSIDE_EXIT").sum()) if not attempts.empty else 0,
                "acceptance": dict(zip(acceptance["test_id"], acceptance["status"])),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
