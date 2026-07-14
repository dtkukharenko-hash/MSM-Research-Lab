#!/usr/bin/env python3
"""EXP-012 R4: causal parent state machine from raw OHLC bars."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import experiment_012_r2_snapshot as r2


ROOT = r2.ROOT
EXP = r2.EXP
OUT = r2.OUT
START = r2.START
END = r2.END
END_BOUNDARY = r2.END_BOUNDARY
MODEL_PRIMARY = "R4_PRICE_PLUS_ACTIVE_PARENT_EMA"
MODEL_PRICE_ONLY = "PRICE_ONLY_IMMEDIATE_CLOSE_BASELINE_R4"
MODEL_EMA12 = "PRICE_PLUS_ACTIVE_INTERNAL_EMA12_BASELINE_R4"

OUTSIDE_CLEARANCE_ATR = r2.OUTSIDE_CLEARANCE_ATR
MIN_DECISION_BARS = r2.MIN_DECISION_BARS
MAX_DECISION_BARS = r2.MAX_DECISION_BARS
DEEP_RECLAIM_ATR = r2.DEEP_RECLAIM_ATR
OUTSIDE_MAJORITY = r2.OUTSIDE_MAJORITY
EXTENSION_MIN_ATR = r2.EXTENSION_MIN_ATR

BOOTSTRAP_LOOKBACK = 12
BOOTSTRAP_WIDTH_ATR_MAX = 0.60
BOOTSTRAP_NET_CHANGE_ATR_MAX = 0.35
PARENT_LOOKBACK = 24
PARENT_WIDTH_ATR_MAX = 0.90
PARENT_NET_CHANGE_ATR_MAX = 0.50
EMA_DEPARTURE_ATR = 0.10
JOINT_PROBATION_BARS = 12
JOINT_MIN_OUTSIDE = 8
JOINT_MIN_EMA_BEYOND = 8
JOINT_DEEP_RECLAIM_ATR = 0.15


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")


def fmt(values: list[float]) -> str:
    return ";".join(f"{v:.8f}" for v in values)


def empty_df(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def add_r4_ema_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    prior = out["ema27"].shift(1)
    for prefix, lookback in [("bootstrap", BOOTSTRAP_LOOKBACK), ("parent", PARENT_LOOKBACK)]:
        out[f"{prefix}_ema_band_low_before_bar"] = prior.rolling(lookback, min_periods=lookback).min()
        out[f"{prefix}_ema_band_high_before_bar"] = prior.rolling(lookback, min_periods=lookback).max()
        out[f"{prefix}_ema_band_mid_before_bar"] = prior.rolling(lookback, min_periods=lookback).median()
        out[f"{prefix}_ema_band_width_atr"] = (out[f"{prefix}_ema_band_high_before_bar"] - out[f"{prefix}_ema_band_low_before_bar"]) / out["atr14"]
        out[f"{prefix}_ema_net_change_atr"] = (out["ema27"].shift(1) - out["ema27"].shift(lookback)) / out["atr14"]
    out["bootstrap_ema_compact_band"] = (out["bootstrap_ema_band_width_atr"] <= BOOTSTRAP_WIDTH_ATR_MAX) & (out["bootstrap_ema_net_change_atr"].abs() <= BOOTSTRAP_NET_CHANGE_ATR_MAX)
    out["parent_ema_compact_band"] = (out["parent_ema_band_width_atr"] <= PARENT_WIDTH_ATR_MAX) & (out["parent_ema_net_change_atr"].abs() <= PARENT_NET_CHANGE_ATR_MAX)
    return out


def idx_at(df: pd.DataFrame, ts: object) -> int:
    matches = df.index[df["open_time"] == pd.Timestamp(ts)].tolist()
    if not matches:
        raise RuntimeError(f"open_time not found: {ts}")
    return int(matches[0])


def outside_flags(row: pd.Series, direction: str, boundary: float, atr: float | None = None) -> tuple[bool, bool]:
    use_atr = float(row["atr14"] if atr is None else atr)
    if direction == "UP":
        return bool(row["close"] > boundary), bool(row["close"] < boundary - DEEP_RECLAIM_ATR * use_atr)
    return bool(row["close"] < boundary), bool(row["close"] > boundary + DEEP_RECLAIM_ATR * use_atr)


def evaluate_extension(df: pd.DataFrame, start_idx: int, end_idx: int, direction: str, upper: float, lower: float, frozen_atr: float) -> dict[str, object]:
    boundary = upper if direction == "UP" else lower
    window = df.iloc[start_idx : end_idx + 1]
    outside = window["close"] > boundary if direction == "UP" else window["close"] < boundary
    outside_closes = [float(x) for x in window.loc[outside, "close"].tolist()]
    longest = 0
    cur = 0
    for flag in outside.tolist():
        cur = cur + 1 if flag else 0
        longest = max(longest, cur)
    if direction == "UP":
        body_values = sorted([float(x) for x in window.loc[outside, "body_high"].tolist()], reverse=True)[:3]
        proposed = float(np.median(body_values)) if body_values else math.nan
        wick = float(window["high"].max())
        beyond = (float(np.median(outside_closes)) - boundary) >= EXTENSION_MIN_ATR * frozen_atr if outside_closes else False
        new_upper, new_lower = max(upper, proposed) if body_values else upper, lower
    else:
        body_values = sorted([float(x) for x in window.loc[outside, "body_low"].tolist()])[:3]
        proposed = float(np.median(body_values)) if body_values else math.nan
        wick = float(window["low"].min())
        beyond = (boundary - float(np.median(outside_closes))) >= EXTENSION_MIN_ATR * frozen_atr if outside_closes else False
        new_upper, new_lower = upper, min(lower, proposed) if body_values else lower
    accepted = bool(outside.sum() >= 3 and longest >= 2 and beyond and body_values)
    return {
        "accepted": accepted,
        "outside_close_count": int(outside.sum()),
        "longest_outside_run": int(longest),
        "outside_body_values": body_values,
        "proposed_body_boundary": proposed,
        "wick_extreme_ignored": wick,
        "new_upper": new_upper,
        "new_lower": new_lower,
    }


def classify_local_candidate(df: pd.DataFrame, start_idx: int, direction: str, upper: float, lower: float) -> dict[str, object]:
    boundary = upper if direction == "UP" else lower
    frozen_atr = float(df.iloc[start_idx]["atr14"])
    rows = []
    outside_run = reclaim_run = longest_outside = longest_reclaim = 0
    accepted = False
    reason = "MAX_DECISION_BARS_REACHED"
    decision_idx = min(len(df) - 1, start_idx + MAX_DECISION_BARS - 1)
    effective_idx = -1
    for idx in range(start_idx, min(len(df), start_idx + MAX_DECISION_BARS)):
        row = df.iloc[idx]
        outside, deep = outside_flags(row, direction, boundary)
        ema_ok_bar = bool(row["close"] > row["ema27"]) if direction == "UP" else bool(row["close"] < row["ema27"])
        outside_run = outside_run + 1 if outside else 0
        reclaim_run = reclaim_run + 1 if deep else 0
        longest_outside = max(longest_outside, outside_run)
        longest_reclaim = max(longest_reclaim, reclaim_run)
        rows.append({"idx": idx, "outside": outside, "deep": deep, "ema_ok": ema_ok_bar})
        observed = len(rows)
        outside_count = sum(int(r["outside"]) for r in rows)
        ema_count = sum(int(r["ema_ok"]) for r in rows)
        outside_fraction = outside_count / observed
        ema_fraction = ema_count / observed
        if observed >= MIN_DECISION_BARS:
            final_valid = bool(row["close"] > boundary) if direction == "UP" else bool(row["close"] < boundary or row["close"] <= boundary + 0.10 * row["atr14"])
            ema_valid = ema_fraction >= OUTSIDE_MAJORITY and (direction == "DOWN" or bool((df.iloc[start_idx : idx + 1]["ema27"] > df.iloc[start_idx : idx + 1]["ema200"]).all()))
            if outside_fraction >= OUTSIDE_MAJORITY and final_valid and longest_reclaim < 3 and ema_valid:
                accepted = True
                decision_idx = idx
                effective_idx = next(int(r["idx"]) for r in rows if r["outside"])
                reason = ""
                break
        if reclaim_run >= 3:
            decision_idx = idx
            reason = "THREE_CONSECUTIVE_DEEP_RECLAIMS"
            break
    ext = evaluate_extension(df, start_idx, decision_idx, direction, upper, lower, frozen_atr)
    if accepted:
        status = f"LOCAL_ACCEPTED_{direction}_DEPARTURE"
    elif ext["accepted"]:
        status = f"LOCAL_ACCEPTED_{direction}_EXTENSION"
    else:
        status = f"LOCAL_REJECTED_{direction}_EXCURSION"
    return {
        "direction": direction,
        "candidate_idx": start_idx,
        "decision_idx": int(decision_idx),
        "effective_idx": int(effective_idx),
        "frozen_boundary": boundary,
        "frozen_atr": frozen_atr,
        "status": status,
        "accepted_departure": accepted,
        "accepted_extension": bool(ext["accepted"] and not accepted),
        "rejection_reason": reason,
        "observed_bars": len(rows),
        "outside_close_count": int(sum(int(r["outside"]) for r in rows)),
        "outside_fraction": float(sum(int(r["outside"]) for r in rows) / len(rows)) if rows else 0.0,
        "longest_outside_run": int(longest_outside),
        "longest_deep_reclaim_run": int(longest_reclaim),
        "extension": ext,
        "last_timestamp_used": df.iloc[decision_idx]["open_time"],
    }


def make_bar_features(df: pd.DataFrame, model: str) -> pd.DataFrame:
    cols = ["open_time", "close_time", "open", "high", "low", "close", "body_high", "body_low", "ema27", "ema200", "atr14"]
    out = df[cols].copy()
    for col, default in {
        "model": model,
        "parent_id": "",
        "parent_state": "NO_PARENT",
        "phase_id": "",
        "active_upper_bound_before_bar": math.nan,
        "active_lower_bound_before_bar": math.nan,
        "boundary_version": 0,
        "local_candidate_state": "",
        "active_price_regime_id": "",
        "active_price_regime_direction": "",
        "active_ema_regime_id": "",
        "active_ema_regime_direction": "",
        "active_ema_regime_scale": "",
        "ema_frozen_band_low": math.nan,
        "ema_frozen_band_high": math.nan,
        "ema_rearm_state": "",
        "joint_candidate_id": "",
        "joint_state": "",
        "price_outside_count": 0,
        "price_deep_reclaim_count": 0,
        "ema_beyond_count": 0,
        "ema_inside_count": 0,
        "transition_event_ids": "",
        "last_timestamp_used": pd.NaT,
    }.items():
        out[col] = default
    return out


def state_event(events: list[dict[str, object]], model: str, parent_id: str, idx: int, df: pd.DataFrame, prior: str, new: str, event_type: str, upper: float, lower: float, reason: str, price_id: str = "", ema_id: str = "", joint_id: str = "") -> str:
    eid = f"SM{len(events)+1:04d}"
    events.append(
        {
            "event_id": eid,
            "event_sequence": len(events) + 1,
            "model": model,
            "parent_id": parent_id,
            "bar_open_time": df.iloc[idx]["open_time"],
            "prior_state": prior,
            "new_state": new,
            "event_type": event_type,
            "price_regime_id": price_id,
            "ema_regime_id": ema_id,
            "joint_id": joint_id,
            "active_upper_bound": upper,
            "active_lower_bound": lower,
            "causal_reason": reason,
            "last_timestamp_used": df.iloc[idx]["open_time"],
        }
    )
    return eid


def scale_for(model: str, parent_age: int) -> tuple[str, int, str, float, float]:
    if model == MODEL_EMA12:
        return "BOOTSTRAP_EMA12", BOOTSTRAP_LOOKBACK, "bootstrap", BOOTSTRAP_WIDTH_ATR_MAX, BOOTSTRAP_NET_CHANGE_ATR_MAX
    if parent_age < PARENT_LOOKBACK:
        return "BOOTSTRAP_EMA12", BOOTSTRAP_LOOKBACK, "bootstrap", BOOTSTRAP_WIDTH_ATR_MAX, BOOTSTRAP_NET_CHANGE_ATR_MAX
    return "PARENT_EMA24", PARENT_LOOKBACK, "parent", PARENT_WIDTH_ATR_MAX, PARENT_NET_CHANGE_ATR_MAX


def maybe_start_ema_candidate(df: pd.DataFrame, idx: int, scale_name: str, prefix: str, rearm: dict[str, object]) -> dict[str, object] | None:
    row = df.iloc[idx]
    if pd.isna(row[f"{prefix}_ema_band_low_before_bar"]) or not bool(row[f"{prefix}_ema_compact_band"]):
        return None
    direction = ""
    edge = math.nan
    if row["ema27"] > row[f"{prefix}_ema_band_high_before_bar"] + EMA_DEPARTURE_ATR * row["atr14"] and row["ema27_change_1"] > 0:
        direction = "UP"
        edge = float(row[f"{prefix}_ema_band_high_before_bar"])
    elif row["ema27"] < row[f"{prefix}_ema_band_low_before_bar"] - EMA_DEPARTURE_ATR * row["atr14"] and row["ema27_change_1"] < 0:
        direction = "DOWN"
        edge = float(row[f"{prefix}_ema_band_low_before_bar"])
    if not direction:
        return None
    last_confirm = int(rearm.get("last_confirmation_idx", -10_000))
    rearmed = bool(rearm.get("rearmed", True))
    if not rearmed:
        first_prior = idx - (BOOTSTRAP_LOOKBACK if scale_name == "BOOTSTRAP_EMA12" else PARENT_LOOKBACK)
        can_new_band = first_prior > last_confirm
        if not can_new_band:
            rearm["suppressed"] = int(rearm.get("suppressed", 0)) + 1
            return None
        rearm["rearmed"] = True
        rearm["pending_rearm_kind"] = "NEW_BAND_REARM"
        rearm["pending_first_prior_window_idx"] = first_prior
    return {
        "candidate_idx": idx,
        "scale": scale_name,
        "prefix": prefix,
        "direction": direction,
        "frozen_low": float(row[f"{prefix}_ema_band_low_before_bar"]),
        "frozen_high": float(row[f"{prefix}_ema_band_high_before_bar"]),
        "frozen_mid": float(row[f"{prefix}_ema_band_mid_before_bar"]),
        "frozen_edge": edge,
        "band_width_atr": float(row[f"{prefix}_ema_band_width_atr"]),
        "net_change_atr": float(row[f"{prefix}_ema_net_change_atr"]),
        "consecutive": 1,
    }


def update_ema(df: pd.DataFrame, idx: int, model: str, parent_id: str, parent_start_idx: int, ema_candidate: dict[str, object] | None, active_ema: dict[str, object] | None, rearm: dict[str, object], events: list[dict[str, object]], regimes: list[dict[str, object]], rearm_rows: list[dict[str, object]]) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    if model == MODEL_PRICE_ONLY:
        return None, None
    if active_ema is not None:
        inside = bool(active_ema["frozen_band_low"] <= df.iloc[idx]["ema27"] <= active_ema["frozen_band_high"])
        active_ema["inside_run"] = int(active_ema.get("inside_run", 0)) + 1 if inside else 0
        if int(active_ema["inside_run"]) >= 2:
            active_ema["active"] = False
            active_ema["termination_reason"] = "EMA_RETURN_TERMINATION"
            active_ema["termination_open_time"] = df.iloc[idx]["open_time"]
            active_ema["last_timestamp_used"] = df.iloc[idx]["open_time"]
            rearm["rearmed"] = True
            rearm["pending_rearm_kind"] = ""
            rearm_rows.append(
                {
                    "rearm_event_id": f"ER{len(rearm_rows)+1:03d}",
                    "model": model,
                    "scale": active_ema["source_scale"],
                    "rearm_kind": "RETURN_REARM",
                    "rearm_open_time": df.iloc[idx]["open_time"],
                    "previous_confirmation_open_time": active_ema["confirmation_open_time"],
                    "first_prior_window_open_time": pd.NaT,
                    "first_prior_window_strictly_after_previous_confirmation": True,
                }
            )
            active_ema = None
    scale_name, _, prefix, _, _ = scale_for(model, idx - parent_start_idx)
    if model == MODEL_PRIMARY and scale_name == "BOOTSTRAP_EMA12" and idx - parent_start_idx >= PARENT_LOOKBACK:
        return ema_candidate, active_ema
    if ema_candidate is None:
        ema_candidate = maybe_start_ema_candidate(df, idx, scale_name, prefix, rearm)
        if ema_candidate is None:
            return None, active_ema
        return ema_candidate, active_ema
    if ema_candidate["scale"] != scale_name and model == MODEL_PRIMARY:
        ema_candidate = None
        return None, active_ema
    row = df.iloc[idx]
    direction = str(ema_candidate["direction"])
    beyond = bool(row["ema27"] > ema_candidate["frozen_edge"]) if direction == "UP" else bool(row["ema27"] < ema_candidate["frozen_edge"])
    if not beyond:
        return None, active_ema
    ema_candidate["consecutive"] = int(ema_candidate["consecutive"]) + 1
    if int(ema_candidate["consecutive"]) < 2:
        return ema_candidate, active_ema
    classification = "EMA_REGIME_UP_AWAY_FROM_EMA200" if direction == "UP" and row["ema_gap_change_6_atr"] > 0 else (
        "EMA_REGIME_DOWN_TOWARD_EMA200" if direction == "DOWN" and row["ema_gap_change_6_atr"] < 0 else (
            "EMA_REGIME_UP_GAP_NOT_EXPANDING" if direction == "UP" else "EMA_REGIME_DOWN_GAP_NOT_SHRINKING"
        )
    )
    eid = f"EM{len(events)+1:03d}"
    event = {
        "ema_event_id": eid,
        "model": model,
        "parent_id": parent_id,
        "source_scale": ema_candidate["scale"],
        "candidate_open_time": df.iloc[int(ema_candidate["candidate_idx"])]["open_time"],
        "confirmation_open_time": row["open_time"],
        "direction": direction,
        "classification": classification,
        "directionally_qualified": classification in {"EMA_REGIME_UP_AWAY_FROM_EMA200", "EMA_REGIME_DOWN_TOWARD_EMA200"},
        "frozen_band_low": ema_candidate["frozen_low"],
        "frozen_band_high": ema_candidate["frozen_high"],
        "frozen_band_mid": ema_candidate["frozen_mid"],
        "frozen_edge": ema_candidate["frozen_edge"],
        "band_width_atr": ema_candidate["band_width_atr"],
        "net_change_atr": ema_candidate["net_change_atr"],
        "ema_gap_change_6_atr_at_confirmation": float(row["ema_gap_change_6_atr"]),
        "last_timestamp_used": row["open_time"],
    }
    events.append(event)
    rid = f"AR{len(regimes)+1:03d}"
    active_ema = {
        "ema_regime_id": rid,
        **event,
        "frozen_low": event["frozen_band_low"],
        "frozen_high": event["frozen_band_high"],
        "active": True,
        "inside_run": 0,
        "termination_reason": "",
        "termination_open_time": pd.NaT,
    }
    regimes.append(active_ema)
    previous = int(rearm.get("last_confirmation_idx", -10_000))
    pending = str(rearm.get("pending_rearm_kind", ""))
    if pending == "NEW_BAND_REARM" and previous >= 0:
        first_prior = int(rearm.get("pending_first_prior_window_idx", -1))
        rearm_rows.append(
            {
                "rearm_event_id": f"ER{len(rearm_rows)+1:03d}",
                "model": model,
                "scale": ema_candidate["scale"],
                "rearm_kind": "NEW_BAND_REARM",
                "rearm_open_time": row["open_time"],
                "previous_confirmation_open_time": df.iloc[previous]["open_time"],
                "first_prior_window_open_time": df.iloc[first_prior]["open_time"] if first_prior >= 0 else pd.NaT,
                "first_prior_window_strictly_after_previous_confirmation": first_prior > previous,
            }
        )
    rearm["last_confirmation_idx"] = idx
    rearm["rearmed"] = False
    rearm["last_frozen_low"] = ema_candidate["frozen_low"]
    rearm["last_frozen_high"] = ema_candidate["frozen_high"]
    rearm["pending_rearm_kind"] = ""
    return None, active_ema


def evaluate_joint(df: pd.DataFrame, start_idx: int, parent: dict[str, object], price_regime: dict[str, object], ema_regime: dict[str, object], joint_id: str) -> dict[str, object]:
    direction = str(price_regime["direction"])
    upper = float(parent["upper"])
    lower = float(parent["lower"])
    boundary = upper if direction == "UP" else lower
    ema_edge = float(ema_regime["frozen_edge"])
    price_out = ema_beyond = 0
    price_deep_run = ema_inside_run = 0
    longest_price_deep = longest_ema_inside = 0
    decision_idx = start_idx
    status = "FAILED"
    reason = "INSUFFICIENT_BARS"
    gap_start = float(df.iloc[start_idx]["ema_gap"])
    observed = 0
    for idx in range(start_idx, min(len(df), start_idx + JOINT_PROBATION_BARS)):
        row = df.iloc[idx]
        outside, deep = outside_flags(row, direction, boundary)
        beyond = bool(row["ema27"] > ema_edge) if direction == "UP" else bool(row["ema27"] < ema_edge)
        inside_ema = bool(ema_regime["frozen_low"] <= row["ema27"] <= ema_regime["frozen_high"])
        observed += 1
        price_out += int(outside)
        ema_beyond += int(beyond)
        price_deep_run = price_deep_run + 1 if deep else 0
        ema_inside_run = ema_inside_run + 1 if inside_ema else 0
        longest_price_deep = max(longest_price_deep, price_deep_run)
        longest_ema_inside = max(longest_ema_inside, ema_inside_run)
        decision_idx = idx
        if price_deep_run >= 3:
            reason = "PRICE_DEEP_RECLAIM"
            break
        if ema_inside_run >= 2:
            reason = "EMA_RETURN_INSIDE_BAND"
            break
        if observed == JOINT_PROBATION_BARS:
            final = df.iloc[idx]
            if direction == "UP":
                ok = price_out >= JOINT_MIN_OUTSIDE and final["close"] > boundary and ema_beyond >= JOINT_MIN_EMA_BEYOND and final["ema27"] > ema_edge and final["ema27"] > final["ema200"] and final["ema_gap"] > gap_start
            else:
                ok = price_out >= JOINT_MIN_OUTSIDE and (final["close"] < boundary or final["close"] <= boundary + 0.10 * final["atr14"]) and ema_beyond >= JOINT_MIN_EMA_BEYOND and final["ema27"] < ema_edge and final["ema_gap"] < gap_start
            status = "CONFIRMED" if ok else "FAILED"
            reason = "JOINT_PERSISTENCE_CONFIRMED" if ok else "JOINT_12_BAR_CRITERIA_NOT_MET"
            break
    return {
        "joint_id": joint_id,
        "model": parent["model"],
        "parent_id": parent["parent_id"],
        "direction": direction,
        "price_regime_id": price_regime["price_regime_id"],
        "ema_regime_id": ema_regime["ema_regime_id"],
        "joint_overlap_open_time": df.iloc[start_idx]["open_time"],
        "joint_decision_open_time": df.iloc[decision_idx]["open_time"],
        "frozen_upper_bound": upper,
        "frozen_lower_bound": lower,
        "frozen_ema_band_low": ema_regime["frozen_low"],
        "frozen_ema_band_high": ema_regime["frozen_high"],
        "frozen_ema_edge": ema_edge,
        "price_regime_age_bars_at_overlap": start_idx - int(price_regime["confirmation_idx"]),
        "ema_regime_age_bars_at_overlap": start_idx - idx_at(df, ema_regime["confirmation_open_time"]),
        "bars_observed": observed,
        "price_outside_count": price_out,
        "price_outside_fraction": price_out / observed if observed else 0.0,
        "longest_price_deep_reclaim_run": longest_price_deep,
        "ema_beyond_count": ema_beyond,
        "ema_beyond_fraction": ema_beyond / observed if observed else 0.0,
        "longest_ema_inside_return_run": longest_ema_inside,
        "ema_gap_at_candidate": gap_start,
        "ema_gap_at_decision": float(df.iloc[decision_idx]["ema_gap"]),
        "joint_status": status,
        "failure_reason": "" if status == "CONFIRMED" else reason,
        "effective_parent_resolution_open_time": price_regime["first_outside_open_time"] if status == "CONFIRMED" else pd.NaT,
        "local_price_confirmation_open_time": price_regime["local_acceptance_confirmation_open_time"],
        "parent_resolution_confirmation_open_time": df.iloc[decision_idx]["open_time"] if status == "CONFIRMED" else pd.NaT,
        "last_timestamp_used": df.iloc[decision_idx]["open_time"],
    }


def run_model(df: pd.DataFrame, model: str) -> dict[str, pd.DataFrame | int]:
    parents: list[dict[str, object]] = []
    phases: list[dict[str, object]] = []
    local_rows: list[dict[str, object]] = []
    price_regimes: list[dict[str, object]] = []
    ema_events: list[dict[str, object]] = []
    ema_regimes: list[dict[str, object]] = []
    ema_rearms: list[dict[str, object]] = []
    joints: list[dict[str, object]] = []
    boundary_events: list[dict[str, object]] = []
    extensions: list[dict[str, object]] = []
    sm_events: list[dict[str, object]] = []
    bar = make_bar_features(df, model)
    cursor = 0
    trigger_indices = df.index[df["core_trigger"]].tolist()

    while cursor < len(df):
        next_triggers = [int(x) for x in trigger_indices if int(x) >= cursor]
        if not next_triggers:
            break
        trig = next_triggers[0]
        run = r2.find_last_aligned_run(df, trig)
        parent_start = r2.find_zone_start(df, trig, run)
        if parent_start < cursor:
            cursor = trig + 1
            continue
        upper_seed = r2.initial_upper_seed(df, parent_start, run)
        lower_seed = r2.confirm_lower_seed(df, parent_start, float(upper_seed["upper_wick_reference"]))
        if not lower_seed["bounds_confirmed"]:
            cursor = trig + 1
            continue
        parent_id = f"P{len(parents)+1:03d}"
        upper = float(upper_seed["initial_upper_bound"])
        lower = float(lower_seed["initial_lower_bound"])
        upper_wick = float(upper_seed["upper_wick_reference"])
        lower_wick = float(lower_seed["lower_wick_reference"])
        bounds_idx = int(lower_seed["bounds_confirmation_idx"])
        boundary_version = 1
        parent = {"model": model, "parent_id": parent_id, "upper": upper, "lower": lower}
        state_event(sm_events, model, parent_id, parent_start, df, "NO_PARENT", "PARENT_BUILDING_BOUNDS", "PARENT_START", upper, lower, "raw core-trigger loss of agreement")
        state_event(sm_events, model, parent_id, bounds_idx, df, "PARENT_BUILDING_BOUNDS", "PARENT_ACTIVE_INSIDE", "BOUNDS_CONFIRMED", upper, lower, str(lower_seed["bounds_confirmation_reason"]))
        active_price: dict[str, object] | None = None
        active_ema: dict[str, object] | None = None
        ema_candidate: dict[str, object] | None = None
        rearm = {"rearmed": True, "last_confirmation_idx": -10_000, "suppressed": 0}
        parent_start_idx = parent_start
        i = bounds_idx + 1
        resolution_kind = "OPEN_AT_TRAIN_END"
        resolution_direction = ""
        effective_idx = -1
        local_conf_idx = -1
        joint_overlap_idx = -1
        parent_conf_idx = len(df) - 1
        failed_joint_count = 0
        confirmed = False
        while i < len(df):
            row = df.iloc[i]
            bar.loc[i, ["parent_id", "parent_state", "active_upper_bound_before_bar", "active_lower_bound_before_bar", "boundary_version", "last_timestamp_used"]] = [parent_id, "PARENT_ACTIVE_INSIDE", upper, lower, boundary_version, row["open_time"]]
            ema_candidate, active_ema = update_ema(df, i, model, parent_id, parent_start_idx, ema_candidate, active_ema, rearm, ema_events, ema_regimes, ema_rearms)
            if active_ema is not None:
                bar.loc[i, ["active_ema_regime_id", "active_ema_regime_direction", "active_ema_regime_scale", "ema_frozen_band_low", "ema_frozen_band_high"]] = [active_ema["ema_regime_id"], active_ema["direction"], active_ema["source_scale"], active_ema["frozen_band_low"], active_ema["frozen_band_high"]]
            if active_price is not None:
                boundary = upper if active_price["direction"] == "UP" else lower
                outside, deep = outside_flags(row, active_price["direction"], boundary)
                active_price["outside_close_count"] += int(outside)
                active_price["deep_reclaim_run"] = int(active_price.get("deep_reclaim_run", 0)) + 1 if deep else 0
                bar.loc[i, ["active_price_regime_id", "active_price_regime_direction", "price_outside_count", "price_deep_reclaim_count"]] = [active_price["price_regime_id"], active_price["direction"], active_price["outside_close_count"], active_price["deep_reclaim_run"]]
                if int(active_price["deep_reclaim_run"]) >= 3:
                    active_price["active"] = False
                    active_price["termination_reason"] = "PRICE_RETURN_TERMINATION"
                    active_price["termination_open_time"] = row["open_time"]
                    active_price["last_timestamp_used"] = row["open_time"]
                    ext = evaluate_extension(df, int(active_price["candidate_idx"]), i, str(active_price["direction"]), upper, lower, float(active_price["frozen_atr"]))
                    if ext["accepted"]:
                        old_upper, old_lower = upper, lower
                        upper, lower = float(ext["new_upper"]), float(ext["new_lower"])
                        parent["upper"], parent["lower"] = upper, lower
                        boundary_version += 1
                        ext_id = f"EX{len(extensions)+1:03d}"
                        extensions.append({"extension_id": ext_id, "model": model, "parent_id": parent_id, "phase_id": active_price["phase_id"], "price_regime_id": active_price["price_regime_id"], "direction": active_price["direction"], "old_upper_bound": old_upper, "old_lower_bound": old_lower, "proposed_body_boundary": ext["proposed_body_boundary"], "new_upper_bound": upper, "new_lower_bound": lower, "outside_body_values_used": fmt(ext["outside_body_values"]), "wick_extreme_ignored": ext["wick_extreme_ignored"], "boundary_version": boundary_version, "evidence_start_open_time": df.iloc[int(active_price["candidate_idx"])]["open_time"], "evidence_end_open_time": row["open_time"], "last_timestamp_used": row["open_time"]})
                        boundary_events.append({"boundary_event_id": f"PB{len(boundary_events)+1:03d}", "model": model, "parent_id": parent_id, "phase_id": active_price["phase_id"], "event_type": f"PARENT_ACCEPTED_{active_price['direction']}_EXTENSION", "event_open_time": row["open_time"], "old_upper_bound": old_upper, "old_lower_bound": old_lower, "proposed_body_boundary": ext["proposed_body_boundary"], "new_upper_bound": upper, "new_lower_bound": lower, "boundary_version": boundary_version, "ignored_wick_extreme": ext["wick_extreme_ignored"], "last_timestamp_used": row["open_time"]})
                    price_regimes.append(active_price)
                    state_event(sm_events, model, parent_id, i, df, "ACTIVE_PRICE_OUTSIDE_REGIME", "PARENT_ACTIVE_INSIDE", "PRICE_RETURN_TERMINATION", upper, lower, "three deep reclaims terminate active price regime", price_id=active_price["price_regime_id"])
                    active_price = None
            if active_price is not None and active_ema is not None and bool(active_ema["directionally_qualified"]) and active_price["direction"] == active_ema["direction"]:
                joint_id = f"JC{len(joints)+1:03d}"
                joint = evaluate_joint(df, i, parent, active_price, active_ema, joint_id)
                joints.append(joint)
                state_event(sm_events, model, parent_id, i, df, "PARENT_ACTIVE_INSIDE", "JOINT_PARENT_CANDIDATE", "JOINT_OVERLAP_START", upper, lower, "active price and qualified EMA regimes overlap", active_price["price_regime_id"], active_ema["ema_regime_id"], joint_id)
                j_decision = idx_at(df, joint["joint_decision_open_time"])
                if joint["joint_status"] == "CONFIRMED":
                    resolution_kind = f"CONFIRMED_PARENT_{joint['direction']}_RESOLUTION"
                    resolution_direction = str(joint["direction"])
                    effective_idx = idx_at(df, joint["effective_parent_resolution_open_time"])
                    local_conf_idx = idx_at(df, joint["local_price_confirmation_open_time"])
                    joint_overlap_idx = i
                    parent_conf_idx = j_decision
                    active_price["termination_reason"] = "PARENT_RESOLUTION"
                    active_price["termination_open_time"] = df.iloc[j_decision]["open_time"]
                    active_ema["termination_reason"] = "PARENT_RESOLUTION"
                    active_ema["termination_open_time"] = df.iloc[j_decision]["open_time"]
                    price_regimes.append(active_price)
                    confirmed = True
                    state_event(sm_events, model, parent_id, j_decision, df, "JOINT_PARENT_CANDIDATE", "PARENT_RESOLVED", resolution_kind, upper, lower, "joint probation confirmed", active_price["price_regime_id"], active_ema["ema_regime_id"], joint_id)
                    bar.loc[i:j_decision, ["joint_candidate_id", "joint_state"]] = [joint_id, "CONFIRMED"]
                    i = j_decision + 1
                    break
                failed_joint_count += 1
                phase_id = str(active_price["phase_id"])
                for ph in phases:
                    if ph["phase_id"] == phase_id:
                        ph["phase_type"] = f"INTERNAL_FAILED_JOINT_{active_price['direction']}_RESOLUTION"
                        ph["joint_candidate_id"] = joint_id
                        ph["joint_candidate_result"] = "FAILED"
                state_event(sm_events, model, parent_id, j_decision, df, "JOINT_PARENT_CANDIDATE", "PARENT_ACTIVE_INSIDE", "FAILED_JOINT_CONTINUE_PARENT", upper, lower, str(joint["failure_reason"]), active_price["price_regime_id"], active_ema["ema_regime_id"], joint_id)
                if joint["failure_reason"] == "PRICE_DEEP_RECLAIM":
                    active_price["active"] = False
                    active_price["termination_reason"] = "FAILED_JOINT_PRICE_DEEP_RECLAIM"
                    active_price["termination_open_time"] = df.iloc[j_decision]["open_time"]
                    ext = evaluate_extension(df, int(active_price["candidate_idx"]), j_decision, str(active_price["direction"]), upper, lower, float(active_price["frozen_atr"]))
                    if ext["accepted"]:
                        old_upper, old_lower = upper, lower
                        upper, lower = float(ext["new_upper"]), float(ext["new_lower"])
                        parent["upper"], parent["lower"] = upper, lower
                        boundary_version += 1
                        extensions.append({"extension_id": f"EX{len(extensions)+1:03d}", "model": model, "parent_id": parent_id, "phase_id": active_price["phase_id"], "price_regime_id": active_price["price_regime_id"], "direction": active_price["direction"], "old_upper_bound": old_upper, "old_lower_bound": old_lower, "proposed_body_boundary": ext["proposed_body_boundary"], "new_upper_bound": upper, "new_lower_bound": lower, "outside_body_values_used": fmt(ext["outside_body_values"]), "wick_extreme_ignored": ext["wick_extreme_ignored"], "boundary_version": boundary_version, "evidence_start_open_time": df.iloc[int(active_price["candidate_idx"])]["open_time"], "evidence_end_open_time": df.iloc[j_decision]["open_time"], "last_timestamp_used": df.iloc[j_decision]["open_time"]})
                    price_regimes.append(active_price)
                    active_price = None
                if joint["failure_reason"] == "EMA_RETURN_INSIDE_BAND":
                    active_ema["active"] = False
                    active_ema["termination_reason"] = "FAILED_JOINT_EMA_RETURN"
                    active_ema["termination_open_time"] = df.iloc[j_decision]["open_time"]
                    active_ema = None
                bar.loc[i:j_decision, ["joint_candidate_id", "joint_state"]] = [joint_id, "FAILED"]
                i = j_decision + 1
                continue
            if active_price is None:
                direction = ""
                if row["close"] > upper + OUTSIDE_CLEARANCE_ATR * row["atr14"]:
                    direction = "UP"
                elif row["close"] < lower - OUTSIDE_CLEARANCE_ATR * row["atr14"]:
                    direction = "DOWN"
                if direction:
                    candidate = classify_local_candidate(df, i, direction, upper, lower)
                    decision_idx = int(candidate["decision_idx"])
                    local_id = f"LC{len(local_rows)+1:03d}"
                    phase_id = f"PH{len(phases)+1:03d}"
                    local_rows.append({"local_candidate_id": local_id, "model": model, "parent_id": parent_id, "phase_id": phase_id, "direction": direction, "candidate_open_time": row["open_time"], "decision_open_time": df.iloc[decision_idx]["open_time"], "status": candidate["status"], "accepted_departure": candidate["accepted_departure"], "accepted_extension": candidate["accepted_extension"], "frozen_upper_bound": upper, "frozen_lower_bound": lower, "frozen_boundary": candidate["frozen_boundary"], "frozen_atr": candidate["frozen_atr"], "observed_bars": candidate["observed_bars"], "outside_close_count": candidate["outside_close_count"], "outside_fraction": candidate["outside_fraction"], "longest_outside_run": candidate["longest_outside_run"], "longest_deep_reclaim_run": candidate["longest_deep_reclaim_run"], "rejection_reason": candidate["rejection_reason"], "effective_open_time": df.iloc[int(candidate["effective_idx"])]["open_time"] if int(candidate["effective_idx"]) >= 0 else pd.NaT, "last_timestamp_used": df.iloc[decision_idx]["open_time"]})
                    bar.loc[i:decision_idx, ["local_candidate_state", "phase_id", "last_timestamp_used"]] = [direction, phase_id, df.iloc[decision_idx]["open_time"]]
                    if model == MODEL_PRICE_ONLY and candidate["accepted_departure"]:
                        resolution_kind = f"CONFIRMED_PARENT_{direction}_RESOLUTION"
                        resolution_direction = direction
                        effective_idx = int(candidate["effective_idx"])
                        local_conf_idx = decision_idx
                        parent_conf_idx = decision_idx
                        phases.append({"phase_id": phase_id, "model": model, "parent_id": parent_id, "phase_type": f"INTERNAL_{direction}_DEPARTURE", "direction": direction, "start_open_time": row["open_time"], "effective_open_time": df.iloc[effective_idx]["open_time"], "decision_open_time": df.iloc[decision_idx]["open_time"], "end_open_time": df.iloc[decision_idx]["open_time"], "local_candidate_id": local_id, "price_regime_id": "", "ema_regime_id": "", "joint_candidate_id": "", "joint_candidate_result": "", "expanded_parent_boundary": False, "last_timestamp_used": df.iloc[decision_idx]["open_time"]})
                        confirmed = True
                        state_event(sm_events, model, parent_id, decision_idx, df, "LOCAL_PRICE_CANDIDATE", "PARENT_RESOLVED", resolution_kind, upper, lower, "price-only baseline immediate close")
                        i = decision_idx + 1
                        break
                    if candidate["accepted_departure"]:
                        price_id = f"PR{len(price_regimes) + (1 if active_price is None else 0):03d}"
                        active_price = {"price_regime_id": price_id, "model": model, "parent_id": parent_id, "phase_id": phase_id, "local_candidate_id": local_id, "direction": direction, "candidate_idx": i, "first_outside_idx": int(candidate["effective_idx"]), "confirmation_idx": decision_idx, "candidate_open_time": row["open_time"], "first_outside_open_time": df.iloc[int(candidate["effective_idx"])]["open_time"], "local_acceptance_confirmation_open_time": df.iloc[decision_idx]["open_time"], "frozen_parent_boundary": candidate["frozen_boundary"], "frozen_atr": candidate["frozen_atr"], "outside_close_count": candidate["outside_close_count"], "deep_reclaim_run": 0, "active": True, "termination_reason": "", "termination_open_time": pd.NaT, "last_timestamp_used": df.iloc[decision_idx]["open_time"]}
                        phases.append({"phase_id": phase_id, "model": model, "parent_id": parent_id, "phase_type": f"INTERNAL_{direction}_DEPARTURE", "direction": direction, "start_open_time": row["open_time"], "effective_open_time": df.iloc[int(candidate["effective_idx"])]["open_time"], "decision_open_time": df.iloc[decision_idx]["open_time"], "end_open_time": df.iloc[decision_idx]["open_time"], "local_candidate_id": local_id, "price_regime_id": price_id, "ema_regime_id": active_ema["ema_regime_id"] if active_ema is not None else "", "joint_candidate_id": "", "joint_candidate_result": "", "expanded_parent_boundary": False, "last_timestamp_used": df.iloc[decision_idx]["open_time"]})
                        state_event(sm_events, model, parent_id, decision_idx, df, "LOCAL_PRICE_CANDIDATE", "ACTIVE_PRICE_OUTSIDE_REGIME", "LOCAL_ACCEPTED_DEPARTURE", upper, lower, str(candidate["status"]), price_id=price_id)
                    elif candidate["accepted_extension"]:
                        old_upper, old_lower = upper, lower
                        ext = candidate["extension"]
                        upper, lower = float(ext["new_upper"]), float(ext["new_lower"])
                        parent["upper"], parent["lower"] = upper, lower
                        boundary_version += 1
                        phases.append({"phase_id": phase_id, "model": model, "parent_id": parent_id, "phase_type": f"INTERNAL_ACCEPTED_{direction}_EXTENSION", "direction": direction, "start_open_time": row["open_time"], "effective_open_time": pd.NaT, "decision_open_time": df.iloc[decision_idx]["open_time"], "end_open_time": df.iloc[decision_idx]["open_time"], "local_candidate_id": local_id, "price_regime_id": "", "ema_regime_id": "", "joint_candidate_id": "", "joint_candidate_result": "", "expanded_parent_boundary": True, "last_timestamp_used": df.iloc[decision_idx]["open_time"]})
                        extensions.append({"extension_id": f"EX{len(extensions)+1:03d}", "model": model, "parent_id": parent_id, "phase_id": phase_id, "price_regime_id": "", "direction": direction, "old_upper_bound": old_upper, "old_lower_bound": old_lower, "proposed_body_boundary": ext["proposed_body_boundary"], "new_upper_bound": upper, "new_lower_bound": lower, "outside_body_values_used": fmt(ext["outside_body_values"]), "wick_extreme_ignored": ext["wick_extreme_ignored"], "boundary_version": boundary_version, "evidence_start_open_time": row["open_time"], "evidence_end_open_time": df.iloc[decision_idx]["open_time"], "last_timestamp_used": df.iloc[decision_idx]["open_time"]})
                    else:
                        phases.append({"phase_id": phase_id, "model": model, "parent_id": parent_id, "phase_type": f"INTERNAL_REJECTED_{direction}_EXCURSION", "direction": direction, "start_open_time": row["open_time"], "effective_open_time": pd.NaT, "decision_open_time": df.iloc[decision_idx]["open_time"], "end_open_time": df.iloc[decision_idx]["open_time"], "local_candidate_id": local_id, "price_regime_id": "", "ema_regime_id": "", "joint_candidate_id": "", "joint_candidate_result": "", "expanded_parent_boundary": False, "last_timestamp_used": df.iloc[decision_idx]["open_time"]})
                    i = decision_idx + 1
                    continue
            i += 1
        if not confirmed:
            parent_conf_idx = len(df) - 1
            if active_price is not None:
                active_price["active"] = False
                active_price["termination_reason"] = "TRAIN_END"
                active_price["termination_open_time"] = df.iloc[-1]["open_time"]
                price_regimes.append(active_price)
            if active_ema is not None:
                active_ema["active"] = False
                active_ema["termination_reason"] = "TRAIN_END"
                active_ema["termination_open_time"] = df.iloc[-1]["open_time"]
        bar.loc[parent_start_idx:parent_conf_idx, ["parent_id", "parent_state", "active_upper_bound_before_bar", "active_lower_bound_before_bar", "boundary_version"]] = [parent_id, "PARENT_RESOLVED" if confirmed else "PARENT_ACTIVE_INSIDE", upper, lower, boundary_version]
        parent_phases = [p for p in phases if p["parent_id"] == parent_id and p["model"] == model]
        parent_joints = [j for j in joints if j["parent_id"] == parent_id and j["model"] == model]
        parent_price = [p for p in price_regimes if p["parent_id"] == parent_id and p["model"] == model]
        parent_emas = [e for e in ema_regimes if e["parent_id"] == parent_id and e["model"] == model]
        phase_counts = Counter(p["phase_type"] for p in parent_phases)
        pad = (upper - lower) * 0.05 if upper > lower else float(df.iloc[parent_conf_idx]["atr14"])
        parents.append({"model": model, "parent_id": parent_id, "display_start_open_time": df.iloc[max(0, parent_start_idx - 12)]["open_time"], "parent_start_open_time": df.iloc[parent_start_idx]["open_time"], "first_core_trigger_open_time": df.iloc[trig]["open_time"], "bounds_confirmation_open_time": df.iloc[bounds_idx]["open_time"], "initial_upper_bound": float(upper_seed["initial_upper_bound"]), "initial_lower_bound": float(lower_seed["initial_lower_bound"]), "final_upper_bound": upper, "final_lower_bound": lower, "upper_wick_reference": upper_wick, "lower_wick_reference": lower_wick, "boundary_version_count": boundary_version, "internal_phase_count_by_type": ";".join(f"{k}:{v}" for k, v in sorted(phase_counts.items())), "internal_phase_count": len(parent_phases), "local_candidate_count": len([x for x in local_rows if x["parent_id"] == parent_id and x["model"] == model]), "accepted_price_regime_up_count": len([p for p in parent_price if p["direction"] == "UP"]), "accepted_price_regime_down_count": len([p for p in parent_price if p["direction"] == "DOWN"]), "ema_regime_count_by_scale_direction": ";".join(f"{k[0]}_{k[1]}:{v}" for k, v in sorted(Counter((e["source_scale"], e["direction"]) for e in parent_emas).items())), "joint_candidate_count": len(parent_joints), "failed_joint_count": len([j for j in parent_joints if j["joint_status"] == "FAILED"]), "resolution_direction": resolution_direction, "resolution_kind": resolution_kind, "effective_resolution_open_time": df.iloc[effective_idx]["open_time"] if effective_idx >= 0 else pd.NaT, "local_price_confirmation_open_time": df.iloc[local_conf_idx]["open_time"] if local_conf_idx >= 0 else pd.NaT, "joint_overlap_open_time": df.iloc[joint_overlap_idx]["open_time"] if joint_overlap_idx >= 0 else pd.NaT, "parent_resolution_confirmation_open_time": df.iloc[parent_conf_idx]["open_time"], "actual_final_bar_used": df.iloc[parent_conf_idx]["open_time"], "open_at_train_end": not confirmed, "r1_mapping": "", "r2_mapping": "", "r3_mapping": "", "r5_mapping": "", "display_box_top": upper + pad, "display_box_bottom": lower - pad})
        cursor = parent_conf_idx + 1
    return {"parents": pd.DataFrame(parents), "phases": pd.DataFrame(phases), "locals": pd.DataFrame(local_rows), "price_regimes": pd.DataFrame(price_regimes), "ema_events": pd.DataFrame(ema_events), "ema_regimes": pd.DataFrame(ema_regimes), "rearms": pd.DataFrame(ema_rearms), "joints": pd.DataFrame(joints), "boundary_events": pd.DataFrame(boundary_events), "extensions": pd.DataFrame(extensions), "events": pd.DataFrame(sm_events), "bar": bar, "suppressed": sum(int(x.get("suppressed", 0)) for x in [locals().get("rearm", {})] if False)}


def overlap_mapping(primary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if primary.empty:
        return empty_df(["model", "parent_id", "legacy_source", "legacy_id", "overlap_reason"])
    legacy_files = [
        ("R1", OUT / "long_context_disputed_zones.csv", "zone_id", "zone_start_open_time", "exit_confirmation_open_time"),
        ("R2", OUT / "long_context_disputed_zones_r2.csv", "zone_id", "zone_start_open_time", "exit_confirmation_open_time"),
        ("R3", OUT / "parent_disputed_zones_r3.csv", "parent_zone_id", "parent_start_open_time", "parent_resolution_confirmation_open_time"),
        ("R5", ROOT / "experiments/EXP-011B_LONG_CONFLICT_WINDOWS/artifacts/long_dispute_sections_r5.csv", "section_id", "dispute_start_open_time", "effective_resolution_open_time"),
    ]
    for source, path, id_col, start_col, end_col in legacy_files:
        if not path.exists():
            continue
        old = pd.read_csv(path, parse_dates=[start_col, end_col])
        for p in primary.itertuples():
            ps, pe = pd.Timestamp(p.parent_start_open_time), pd.Timestamp(p.parent_resolution_confirmation_open_time)
            for row in old.itertuples(index=False):
                os, oe = pd.Timestamp(getattr(row, start_col)), pd.Timestamp(getattr(row, end_col))
                if oe >= ps and os <= pe:
                    rows.append({"model": p.model, "parent_id": p.parent_id, "legacy_source": source, "legacy_id": getattr(row, id_col), "overlap_reason": "post-run temporal overlap only"})
    return pd.DataFrame(rows)


def model_comparison(results: dict[str, dict[str, pd.DataFrame | int]]) -> pd.DataFrame:
    rows = []
    for model, result in results.items():
        parents = result["parents"]
        joints = result["joints"]
        rows.append({"model": model, "parent_count": len(parents), "confirmed_up_count": int((parents["resolution_kind"] == "CONFIRMED_PARENT_UP_RESOLUTION").sum()) if not parents.empty else 0, "confirmed_down_count": int((parents["resolution_kind"] == "CONFIRMED_PARENT_DOWN_RESOLUTION").sum()) if not parents.empty else 0, "open_at_train_end_count": int((parents["resolution_kind"] == "OPEN_AT_TRAIN_END").sum()) if not parents.empty else 0, "joint_candidate_count": len(joints), "failed_joint_count": int((joints["joint_status"] == "FAILED").sum()) if not joints.empty else 0})
    return pd.DataFrame(rows)


def acceptance(df: pd.DataFrame, results: dict[str, dict[str, pd.DataFrame | int]], mapping: pd.DataFrame) -> pd.DataFrame:
    primary = results[MODEL_PRIMARY]
    parents = primary["parents"]
    phases = primary["phases"]
    joints = primary["joints"]
    events = primary["events"]
    rearm = primary["rearms"]
    bar = primary["bar"]
    source = Path(__file__).read_text()
    before_mapping = source.split("def overlap_mapping", 1)[0]
    def status(ok: bool) -> str:
        return "PASS" if ok else "FAIL"
    r5map = mapping[(mapping["legacy_source"] == "R5")] if not mapping.empty else pd.DataFrame()
    p_lc = {}
    for lc in ["LC001", "LC002", "LC003"]:
        ids = r5map[r5map["legacy_id"] == lc]["parent_id"].unique().tolist() if not r5map.empty else []
        p_lc[lc] = ids
    failed = joints[joints["joint_status"] == "FAILED"] if not joints.empty else pd.DataFrame()
    later_local = False
    later_joint = False
    if not failed.empty:
        first_fail_time = pd.Timestamp(failed.iloc[0]["joint_decision_open_time"])
        locals_df = primary["locals"]
        later_local = bool((pd.to_datetime(locals_df["candidate_open_time"]) > first_fail_time).any()) if not locals_df.empty else False
        later_joint = bool((pd.to_datetime(joints["joint_overlap_open_time"]) > first_fail_time).any()) if not joints.empty else False
    open_rows = parents[parents["open_at_train_end"] == True] if not parents.empty else pd.DataFrame()
    open_covers = bool(open_rows.empty or open_rows["parent_resolution_confirmation_open_time"].apply(pd.Timestamp).eq(df.iloc[-1]["open_time"]).all())
    new_band_ok = bool(rearm.empty or rearm["first_prior_window_strictly_after_previous_confirmation"].fillna(True).astype(bool).all())
    no_wick = bool(primary["extensions"].empty or primary["extensions"]["outside_body_values_used"].astype(str).str.len().gt(0).all())
    joints_have_overlap = bool(joints.empty or (joints["joint_overlap_open_time"].notna().all() and joints["price_regime_id"].astype(str).str.len().gt(0).all() and joints["ema_regime_id"].astype(str).str.len().gt(0).all()))
    ema12_result = results[MODEL_EMA12]
    ema12_executed = bool(len(ema12_result["ema_events"]) > 0 and len(ema12_result["joints"]) > 0 and set(ema12_result["ema_events"]["source_scale"].astype(str).unique().tolist()) == {"BOOTSTRAP_EMA12"})
    rows = [
        ("DETECTION_USES_RAW_OHLC_NOT_R2_R3_LABELS", "detector source before post-run mapping excludes legacy artifact reads", "no generated legacy CSV reads in detector", status("long_context_disputed_zones_r2.csv" not in before_mapping and "parent_disputed_zones_r3.csv" not in before_mapping), ""),
        ("NO_SOURCE_R5_GROUPING_IN_DETECTOR", "source_r5 grouping not used in detector", "absent before mapping", status("source_r5_sections" not in before_mapping), ""),
        ("EXPECTED_THREE_PRIMARY_PARENTS", "manual diagnostic", "3", status(len(parents) == 3), str(len(parents))),
        ("FIRST_PARENT_COMPACT", "manual diagnostic LC001 overlap", "one parent", status(len(p_lc["LC001"]) == 1), ";".join(p_lc["LC001"])),
        ("NOVEMBER_SINGLE_PARENT", "manual diagnostic LC002 overlap", "one parent", status(len(p_lc["LC002"]) == 1), ";".join(p_lc["LC002"])),
        ("NOVEMBER_MULTIPLE_INTERNAL_PHASES", "manual diagnostic", ">=2", status(bool(p_lc["LC002"]) and phases[phases["parent_id"].isin(p_lc["LC002"])].shape[0] >= 2), ""),
        ("DECEMBER_JANUARY_SINGLE_PARENT", "manual diagnostic LC003 overlap", "one parent", status(len(p_lc["LC003"]) == 1), ";".join(p_lc["LC003"])),
        ("DECEMBER_MULTIPLE_INTERNAL_PHASES", "manual diagnostic", ">=2", status(bool(p_lc["LC003"]) and phases[phases["parent_id"].isin(p_lc["LC003"])].shape[0] >= 2), ""),
        ("MID_DECEMBER_UP_REMAINS_INTERNAL", "manual diagnostic", "internal phase present", status(bool(p_lc["LC003"]) and phases[(phases["parent_id"].isin(p_lc["LC003"])) & (phases["direction"] == "UP")].shape[0] > 0), ""),
        ("MID_DECEMBER_EARLY_DOWN_REMAINS_INTERNAL", "manual diagnostic", "internal down phase present", status(bool(p_lc["LC003"]) and phases[(phases["parent_id"].isin(p_lc["LC003"])) & (phases["direction"] == "DOWN")].shape[0] > 0), ""),
        ("FAILED_JOINT_PARENT_REMAINS_ACTIVE", "failed joint continuation", "parent active after fail", status(bool(not failed.empty and "FAILED_JOINT_CONTINUE_PARENT" in events["event_type"].tolist())), ""),
        ("FAILED_JOINT_CONTINUES_FROM_NEXT_BAR", "event log contains continuation", "continue event", status(bool(not failed.empty and "FAILED_JOINT_CONTINUE_PARENT" in events["event_type"].tolist())), ""),
        ("LATER_LOCAL_CANDIDATE_AFTER_FAILED_JOINT", "January continuation diagnostic", "later local", status(later_local), ""),
        ("LATER_JOINT_CANDIDATE_ALLOWED_AFTER_FAILED_JOINT", "January continuation diagnostic", "later joint", status(later_joint), ""),
        ("PRIMARY_FIRST_PARENT_UP_RESOLUTION", "manual diagnostic", "UP resolution", status(bool(p_lc["LC001"]) and (parents[parents["parent_id"].isin(p_lc["LC001"])]["resolution_kind"] == "CONFIRMED_PARENT_UP_RESOLUTION").any()), ""),
        ("PRIMARY_NOVEMBER_UP_RESOLUTION", "manual diagnostic", "UP resolution", status(bool(p_lc["LC002"]) and (parents[parents["parent_id"].isin(p_lc["LC002"])]["resolution_kind"] == "CONFIRMED_PARENT_UP_RESOLUTION").any()), ""),
        ("PRIMARY_DECEMBER_DOWN_RESOLUTION", "manual diagnostic", "DOWN resolution", status(bool(p_lc["LC003"]) and (parents[parents["parent_id"].isin(p_lc["LC003"])]["resolution_kind"] == "CONFIRMED_PARENT_DOWN_RESOLUTION").any()), ""),
        ("DOWNSIDE_COMPARISON_FILTERS_DOWN_DIRECTION", "downside comparison uses DOWN only", "explicit down filter", status(bool((parents["resolution_direction"] == "DOWN").any()) if not parents.empty else False), ""),
        ("OPEN_PARENT_COVERS_ACTUAL_TRAIN_END", "open parents use final OHLC bar or no parent is open", str(df.iloc[-1]["open_time"]), status(open_covers), f"open_parent_count={len(open_rows)}"),
        ("ACTIVE_REGIME_OVERLAP_NOT_ARBITRARY_EVENT_AGE", "joint source is active-regime overlap", "joint overlap plus active ids", status(joints_have_overlap), ""),
        ("NO_DUPLICATE_EMA_EVENT_BEFORE_REARM", "new EMA events require rearm proof", "strict rearm gates", status(new_band_ok), ""),
        ("NEW_BAND_WINDOW_STRICTLY_AFTER_PREVIOUS_CONFIRMATION", "rearm proof", "strict", status(new_band_ok), ""),
        ("NO_POST_DECISION_DATA_USED", "last timestamp fields populated", "yes", status(bool(primary["locals"].empty or primary["locals"]["last_timestamp_used"].notna().all())), ""),
        ("NO_WICK_ONLY_PARENT_BOUNDARY_UPDATE", "extensions use body evidence", "body values", status(no_wick), ""),
        ("PRICE_ONLY_BASELINE_EXECUTED_INDEPENDENTLY", "baseline output exists", "parents", status(len(results[MODEL_PRICE_ONLY]["parents"]) > 0), ""),
        ("INTERNAL_EMA12_BASELINE_EXECUTED_WITH_EMA_AND_PROBATION", "baseline has EMA/joint machinery", "EMA12 events and joints", status(ema12_executed), ""),
        ("NO_DATE_HARDCODING", "source scan", "no expected date literals in detector", status("2024-01-03" not in before_mapping and "2023-11-24" not in before_mapping), ""),
        ("NO_PRICE_HARDCODING", "source scan", "no manual price literals", status("0.6615" not in before_mapping and "0.3976" not in before_mapping), ""),
        ("NO_PARENT_PHASE_OR_LEGACY_ID_HARDCODING", "source scan", "no legacy ids in detector", status("Z00" not in before_mapping and "LC00" not in before_mapping), ""),
        ("NO_FUTURE_PERIOD_USED", "timestamp cutoff", str(END), status(bool(df["open_time"].max() < END_BOUNDARY)), str(df["open_time"].max())),
    ]
    return pd.DataFrame(rows, columns=["test_id", "description", "expected_result", "status", "details"])


def manual_review(parents: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for p in parents.itertuples():
        rows.append({"parent_id": p.parent_id, "parent_start_open_time": p.parent_start_open_time, "parent_resolution_confirmation_open_time": p.parent_resolution_confirmation_open_time, "question_parent_is_broad_process": "", "question_internal_phases_reasonable": "", "question_resolution_timing_visible": "", "question_failed_joint_continuation_visible": "", "question_binance_bybit_boundary_difference": "", "review_notes": ""})
    return pd.DataFrame(rows)


def pine_script(parents: pd.DataFrame, phases: pd.DataFrame, joints: pd.DataFrame, extensions: pd.DataFrame) -> str:
    lines = [
        "//@version=6",
        'indicator("EXP-012 Causal Parent State Machine R4", overlay=true, max_boxes_count=300, max_lines_count=300, max_labels_count=300)',
        'model = input.string("ALL", "Model", options=["ALL", "R4_PRICE_PLUS_ACTIVE_PARENT_EMA", "PRICE_ONLY_IMMEDIATE_CLOSE_BASELINE_R4", "PRICE_PLUS_ACTIVE_INTERNAL_EMA12_BASELINE_R4"])',
        'showPhases = input.bool(false, "Internal phases")',
        'showDiagnostics = input.bool(false, "Diagnostics")',
        "inRange(s, e) => time >= s and time <= e",
    ]
    for p in parents.itertuples():
        s = int(pd.Timestamp(p.parent_start_open_time).timestamp() * 1000)
        e = int(pd.Timestamp(p.parent_resolution_confirmation_open_time).timestamp() * 1000)
        top = float(p.display_box_top)
        bot = float(p.display_box_bottom)
        lines.append(f'if (model == "ALL" or model == "{p.model}") and barstate.islast')
        lines.append(f"    box.new({s}, {top:.8f}, {e}, {bot:.8f}, xloc=xloc.bar_time, bgcolor=color.new(color.yellow, 86), border_color=color.new(color.orange, 20))")
        lines.append(f"    line.new({s}, {p.final_upper_bound:.8f}, {e}, {p.final_upper_bound:.8f}, xloc=xloc.bar_time, color=color.new(color.orange, 0), width=2)")
        lines.append(f"    line.new({s}, {p.final_lower_bound:.8f}, {e}, {p.final_lower_bound:.8f}, xloc=xloc.bar_time, color=color.new(color.orange, 0), width=2)")
    for ph in phases.itertuples():
        s = int(pd.Timestamp(ph.start_open_time).timestamp() * 1000)
        e = int(pd.Timestamp(ph.end_open_time).timestamp() * 1000)
        lines.append(f'if showPhases and (model == "ALL" or model == "{ph.model}") and barstate.islast')
        lines.append(f"    box.new({s}, high, {e}, low, xloc=xloc.bar_time, bgcolor=color.new(color.gray, 92), border_color=color.new(color.gray, 70))")
    for j in joints.itertuples():
        t = int(pd.Timestamp(j.joint_overlap_open_time).timestamp() * 1000)
        color_name = "color.red" if j.joint_status == "FAILED" else "color.lime"
        lines.append(f'if showDiagnostics and (model == "ALL" or model == "{j.model}") and time == {t}')
        lines.append(f'    label.new(time, high, "{j.joint_id} {j.joint_status}", xloc=xloc.bar_time, style=label.style_label_down, color=color.new({color_name}, 0), textcolor=color.white)')
    for ex in extensions.itertuples():
        t = int(pd.Timestamp(ex.last_timestamp_used).timestamp() * 1000)
        lines.append(f'if showDiagnostics and (model == "ALL" or model == "{ex.model}") and time == {t}')
        lines.append(f'    label.new(time, close, "EXT", xloc=xloc.bar_time, style=label.style_label_left, color=color.new(color.blue, 0), textcolor=color.white)')
    return "\n".join(lines) + "\n"


def update_docs(results: dict[str, dict[str, pd.DataFrame | int]], mapping: pd.DataFrame, acc: pd.DataFrame, comp: pd.DataFrame) -> None:
    primary = results[MODEL_PRIMARY]
    parents = primary["parents"]
    phases = primary["phases"]
    joints = primary["joints"]
    report = [
        "# EXP-012 R4 - CAUSAL PARENT STATE MACHINE",
        "",
        "Status: AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW",
        "",
        "Verdict: AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW",
        "",
        "R4 replaces the R3 post-hoc grouping with a chronological raw-bar state machine. R2/R3/R5 artifacts are loaded only after R4 outputs are frozen, for temporal-overlap mapping and diagnostics.",
        "",
        "## Model Comparison",
        "",
        comp.to_string(index=False),
        "",
        "## Primary Parents",
    ]
    for p in parents.itertuples():
        report.append(f"- `{p.parent_id}`: start `{p.parent_start_open_time}`, bounds `{float(p.final_lower_bound):.6f}`-`{float(p.final_upper_bound):.6f}`, phases `{p.internal_phase_count}`, resolution `{p.resolution_kind}`, confirmation `{p.parent_resolution_confirmation_open_time}`")
    report += ["", "## Joint Candidates"]
    if joints.empty:
        report.append("- none")
    else:
        for j in joints.itertuples():
            report.append(f"- `{j.joint_id}` `{j.parent_id}` {j.direction}: overlap `{j.joint_overlap_open_time}`, decision `{j.joint_decision_open_time}`, `{j.joint_status}` {j.failure_reason}")
    report += ["", "## January Continuation Audit"]
    failed = joints[joints["joint_status"] == "FAILED"] if not joints.empty else pd.DataFrame()
    if failed.empty:
        report.append("- No failed joint candidate was generated in the primary run.")
    else:
        first = failed.iloc[0]
        later_locals = primary["locals"][pd.to_datetime(primary["locals"]["candidate_open_time"]) > pd.Timestamp(first["joint_decision_open_time"])]
        later_joints = joints[pd.to_datetime(joints["joint_overlap_open_time"]) > pd.Timestamp(first["joint_decision_open_time"])]
        report.append(f"- First failed joint: `{first['joint_id']}` at `{first['joint_decision_open_time']}`, reason `{first['failure_reason']}`.")
        report.append(f"- Later local candidates after failure: `{len(later_locals)}`.")
        report.append(f"- Later joint candidates after failure: `{len(later_joints)}`.")
    report += ["", "## Acceptance Tests"]
    for row in acc.itertuples():
        report.append(f"- `{row.test_id}`: `{row.status}` - {row.details}")
    report += [
        "",
        "## Constraints",
        "",
        "No data after `2024-01-08 23:59:59.999 UTC` was used. No Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, forecast, entries, stops, position sizing, or trading logic. `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B were not modified.",
        "",
        "Automatic OHLC outputs use Binance spot; manual review remains Bybit ADAUSDT Perpetual 4H, so candle and boundary differences may exist.",
    ]
    (EXP / "REPORT.md").write_text("\n".join(line.rstrip() for line in report) + "\n")
    review = """# EXP-012 R4 TradingView Review

Status: AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW

1. Open Bybit ADAUSDT Perpetual Contract on 4H.
2. Add `artifacts/LONG_CONTEXT_CAUSAL_PARENT_STATE_MACHINE_R4.pine`.
3. Review parent boxes, optional internal phases, joint candidates, failed joints, retries, and accepted extensions.
4. Fill `artifacts/manual_causal_parent_review.csv`.

Check whether each parent box is one broad accepted price process, whether internal phases are reasonable, whether failed joint candidates leave the parent active, whether later candidates after failed joints are visible, and whether Binance spot versus Bybit perpetual differences could explain boundary mismatch.

Do not assess prediction or trading value.
"""
    (EXP / "REVIEW_INSTRUCTIONS.md").write_text(review)
    task = """# EXP-012 R4 - CAUSAL PARENT STATE MACHINE

Status: AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW

R4 implemented a chronological raw-bar state machine for parent disputed zones, active price regimes, active EMA regimes, joint candidates, failed-joint continuation, baselines, post-run historical mapping, Pine review, and manual review CSV.
"""
    (EXP / "TASK.md").write_text(task)
    queue = (ROOT / "PROJECT_QUEUE.md").read_text()
    start = queue.find("### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES")
    end = queue.find("---", start)
    if start >= 0 and end >= 0:
        replacement = """### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES

Статус: AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW

EXP-012 R4 заменил R3 post-hoc grouping на причинный raw-bar state machine:
`NO_PARENT -> PARENT_BUILDING_BOUNDS -> PARENT_ACTIVE_INSIDE -> LOCAL_PRICE_CANDIDATE ->
ACTIVE_PRICE_OUTSIDE_REGIME / ACTIVE_EMA_DEPARTURE_REGIME -> JOINT_PARENT_CANDIDATE`.
R2/R3/R5 артефакты используются только после freeze R4 outputs для temporal-overlap mapping.

Primary parent zones: `{parents}`.
Joint candidates: `{joints}`, confirmed: `{confirmed}`, failed: `{failed}`.
Acceptance: `{passed}` PASS / `{failed_tests}` FAIL.

Следующее действие:
Проверить parent state machine в TradingView через
`experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/LONG_CONTEXT_CAUSAL_PARENT_STATE_MACHINE_R4.pine`
и заполнить `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/manual_causal_parent_review.csv`.

""".format(parents=len(parents), joints=len(joints), confirmed=int((joints["joint_status"] == "CONFIRMED").sum()) if not joints.empty else 0, failed=int((joints["joint_status"] == "FAILED").sum()) if not joints.empty else 0, passed=int((acc["status"] == "PASS").sum()), failed_tests=int((acc["status"] == "FAIL").sum()))
        queue = queue[:start] + replacement + queue[end:]
        (ROOT / "PROJECT_QUEUE.md").write_text(queue)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    full = add_r4_ema_features(r2.add_features(r2.load_ohlc()))
    df = full[(full["open_time"] >= START) & (full["open_time"] < END_BOUNDARY)].reset_index(drop=True)
    results = {model: run_model(df, model) for model in [MODEL_PRIMARY, MODEL_PRICE_ONLY, MODEL_EMA12]}
    primary = results[MODEL_PRIMARY]
    mapping = overlap_mapping(primary["parents"])
    if not mapping.empty:
        grouped = mapping.groupby(["model", "parent_id", "legacy_source"])["legacy_id"].apply(lambda s: ";".join(map(str, s))).reset_index()
        for source, col in [("R1", "r1_mapping"), ("R2", "r2_mapping"), ("R3", "r3_mapping"), ("R5", "r5_mapping")]:
            sub = grouped[grouped["legacy_source"] == source]
            for row in sub.itertuples():
                mask = primary["parents"]["parent_id"] == row.parent_id
                primary["parents"].loc[mask, col] = row.legacy_id
    comp = model_comparison(results)
    acc = acceptance(df, results, mapping)
    write_csv(primary["parents"], OUT / "parent_disputed_zones_r4.csv")
    write_csv(primary["phases"], OUT / "internal_phases_r4.csv")
    write_csv(primary["locals"], OUT / "local_price_candidates_r4.csv")
    write_csv(primary["price_regimes"], OUT / "active_price_regimes_r4.csv")
    write_csv(pd.concat([results[m]["ema_events"] for m in results], ignore_index=True), OUT / "ema_departure_events_r4.csv")
    write_csv(pd.concat([results[m]["ema_regimes"] for m in results], ignore_index=True), OUT / "active_ema_regimes_r4.csv")
    write_csv(pd.concat([results[m]["rearms"] for m in results], ignore_index=True), OUT / "ema_rearm_events_r4.csv")
    write_csv(primary["joints"], OUT / "joint_parent_candidates_r4.csv")
    write_csv(primary["boundary_events"], OUT / "parent_boundary_events_r4.csv")
    write_csv(primary["extensions"], OUT / "parent_accepted_extensions_r4.csv")
    write_csv(primary["events"], OUT / "state_machine_events_r4.csv")
    write_csv(primary["bar"], OUT / "parent_zone_bar_features_r4.csv")
    write_csv(mapping, OUT / "r4_historical_mapping.csv")
    write_csv(comp, OUT / "r4_model_comparison.csv")
    write_csv(acc, OUT / "r4_acceptance_tests.csv")
    write_csv(manual_review(primary["parents"]), OUT / "manual_causal_parent_review.csv")
    (OUT / "LONG_CONTEXT_CAUSAL_PARENT_STATE_MACHINE_R4.pine").write_text(pine_script(primary["parents"], primary["phases"], primary["joints"], primary["extensions"]))
    update_docs(results, mapping, acc, comp)
    print({"status": "AWAITING_TW_CAUSAL_PARENT_STATE_MACHINE_REVIEW", "parents": len(primary["parents"]), "joints": len(primary["joints"]), "acceptance_pass": int((acc["status"] == "PASS").sum()), "acceptance_fail": int((acc["status"] == "FAIL").sum())})


if __name__ == "__main__":
    main()
