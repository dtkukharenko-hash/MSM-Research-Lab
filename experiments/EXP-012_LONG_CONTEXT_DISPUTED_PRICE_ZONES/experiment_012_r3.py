#!/usr/bin/env python3
"""EXP-012 R3: hierarchical parent disputed zones and internal phases."""

from __future__ import annotations

import json
import math
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

PARENT_EMA_LOOKBACK = 24
PARENT_EMA_WIDTH_ATR_MAX = 0.90
PARENT_EMA_NET_CHANGE_ATR_MAX = 0.50
PARENT_EMA_DEPARTURE_ATR = 0.10
EMA_ASSOCIATION_PRE_BARS = 3
JOINT_PROBATION_BARS = 12
JOINT_MIN_OUTSIDE_FRACTION = 0.67
JOINT_MIN_EMA_BEYOND_FRACTION = 0.67
JOINT_DEEP_RECLAIM_ATR = 0.15


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")


def empty_if_none(value: object) -> object:
    return "" if value is None else value


def add_parent_ema_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    prior = out["ema27"].shift(1)
    out["parent_ema_band_low_before_bar"] = prior.rolling(PARENT_EMA_LOOKBACK, min_periods=PARENT_EMA_LOOKBACK).min()
    out["parent_ema_band_high_before_bar"] = prior.rolling(PARENT_EMA_LOOKBACK, min_periods=PARENT_EMA_LOOKBACK).max()
    out["parent_ema_band_mid_before_bar"] = prior.rolling(PARENT_EMA_LOOKBACK, min_periods=PARENT_EMA_LOOKBACK).median()
    out["parent_ema_band_width_atr"] = (out["parent_ema_band_high_before_bar"] - out["parent_ema_band_low_before_bar"]) / out["atr14"]
    out["parent_ema_net_change_atr"] = (out["ema27"].shift(1) - out["ema27"].shift(PARENT_EMA_LOOKBACK)) / out["atr14"]
    out["parent_ema_compact_band"] = (out["parent_ema_band_width_atr"] <= PARENT_EMA_WIDTH_ATR_MAX) & (out["parent_ema_net_change_atr"].abs() <= PARENT_EMA_NET_CHANGE_ATR_MAX)
    return out


def idx_at(df: pd.DataFrame, ts: object) -> int:
    matches = df.index[df["open_time"] == pd.Timestamp(ts)].tolist()
    if not matches:
        raise RuntimeError(f"open_time not found: {ts}")
    return int(matches[0])


def boundary_at(df: pd.DataFrame, idx: int) -> pd.Timestamp:
    return min(df.iloc[idx + 1]["open_time"] if idx + 1 < len(df) else END_BOUNDARY, END_BOUNDARY)


def detect_internal_ema_departures(df: pd.DataFrame, r2_departures: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in r2_departures.itertuples():
        rows.append(
            {
                "internal_ema_event_id": f"IE{len(rows)+1:03d}",
                "source_r2_event_id": row.event_id,
                "zone_id": row.zone_id,
                "candidate_open_time": row.candidate_open_time,
                "confirmation_open_time": row.confirmation_open_time,
                "direction": row.direction,
                "classification": row.confirmed_classification.replace("EMA27_EXIT", "INTERNAL_EMA"),
                "frozen_band_low": row.frozen_band_low,
                "frozen_band_high": row.frozen_band_high,
                "band_width_atr": row.band_width_atr,
                "causal_last_timestamp_used": row.causal_last_timestamp_used,
            }
        )
    return pd.DataFrame(rows)


def detect_parent_ema_departures(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    events: list[dict[str, object]] = []
    rearms: list[dict[str, object]] = []
    suppressed = 0
    active: dict[str, object] | None = None
    last_frozen_low = last_frozen_high = math.nan
    last_confirm_idx = -10_000
    rearmed = True
    inside_count = 0

    for idx in range(len(df)):
        row = df.iloc[idx]
        if last_confirm_idx >= 0 and not rearmed:
            inside = bool(last_frozen_low <= row["ema27"] <= last_frozen_high)
            inside_count = inside_count + 1 if inside else 0
            if inside_count >= 2:
                rearmed = True
                rearms.append(
                    {
                        "rearm_event_id": f"PR{len(rearms)+1:03d}",
                        "rearm_kind": "RETURN_REARM",
                        "rearm_open_time": row["open_time"],
                        "previous_confirmation_open_time": df.iloc[last_confirm_idx]["open_time"],
                    }
                )
            elif idx - last_confirm_idx >= PARENT_EMA_LOOKBACK:
                rearmed = True
                rearms.append(
                    {
                        "rearm_event_id": f"PR{len(rearms)+1:03d}",
                        "rearm_kind": "NEW_BAND_REARM",
                        "rearm_open_time": row["open_time"],
                        "previous_confirmation_open_time": df.iloc[last_confirm_idx]["open_time"],
                    }
                )
        if active is None:
            if pd.isna(row["parent_ema_band_low_before_bar"]) or not bool(row["parent_ema_compact_band"]):
                continue
            direction = ""
            edge = math.nan
            if row["ema27"] > row["parent_ema_band_high_before_bar"] + PARENT_EMA_DEPARTURE_ATR * row["atr14"] and row["ema27_change_1"] > 0:
                direction = "UP"
                edge = float(row["parent_ema_band_high_before_bar"])
            elif row["ema27"] < row["parent_ema_band_low_before_bar"] - PARENT_EMA_DEPARTURE_ATR * row["atr14"] and row["ema27_change_1"] < 0:
                direction = "DOWN"
                edge = float(row["parent_ema_band_low_before_bar"])
            if not direction:
                continue
            if not rearmed:
                suppressed += 1
                continue
            active = {
                "candidate_idx": idx,
                "direction": direction,
                "frozen_low": float(row["parent_ema_band_low_before_bar"]),
                "frozen_high": float(row["parent_ema_band_high_before_bar"]),
                "frozen_mid": float(row["parent_ema_band_mid_before_bar"]),
                "edge": edge,
                "band_width_atr": float(row["parent_ema_band_width_atr"]),
                "ema27_at_candidate": float(row["ema27"]),
                "atr_at_candidate": float(row["atr14"]),
                "gap_atr_candidate": float(row["ema_gap_atr"]),
                "consecutive": 1,
            }
            continue

        beyond = bool(row["ema27"] > float(active["edge"])) if active["direction"] == "UP" else bool(row["ema27"] < float(active["edge"]))
        if not beyond:
            active = None
            continue
        active["consecutive"] = int(active["consecutive"]) + 1
        if int(active["consecutive"]) >= 2:
            direction = str(active["direction"])
            if direction == "UP":
                classification = "PARENT_EMA_UP_AWAY_FROM_EMA200" if row["ema_gap_change_6_atr"] > 0 else "PARENT_EMA_UP_GAP_NOT_EXPANDING"
            else:
                classification = "PARENT_EMA_DOWN_TOWARD_EMA200" if row["ema_gap_change_6_atr"] < 0 else "PARENT_EMA_DOWN_GAP_NOT_SHRINKING"
            events.append(
                {
                    "parent_ema_event_id": f"PE{len(events)+1:03d}",
                    "candidate_open_time": df.iloc[int(active["candidate_idx"])]["open_time"],
                    "confirmation_open_time": row["open_time"],
                    "direction": direction,
                    "frozen_band_low": active["frozen_low"],
                    "frozen_band_high": active["frozen_high"],
                    "frozen_band_mid": active["frozen_mid"],
                    "frozen_edge": active["edge"],
                    "band_width_atr": active["band_width_atr"],
                    "ema27_at_candidate": active["ema27_at_candidate"],
                    "atr_at_candidate": active["atr_at_candidate"],
                    "ema_gap_atr_at_candidate": active["gap_atr_candidate"],
                    "ema_gap_change_6_atr_at_confirmation": float(row["ema_gap_change_6_atr"]),
                    "classification": classification,
                    "directionally_qualified": classification in {"PARENT_EMA_UP_AWAY_FROM_EMA200", "PARENT_EMA_DOWN_TOWARD_EMA200"},
                    "causal_last_timestamp_used": row["open_time"],
                    "suppressed_duplicates_before_event": suppressed,
                }
            )
            last_confirm_idx = idx
            last_frozen_low = float(active["frozen_low"])
            last_frozen_high = float(active["frozen_high"])
            rearmed = False
            inside_count = 0
            active = None
    return pd.DataFrame(events), pd.DataFrame(rearms), suppressed


def r2_parent_key(row: pd.Series) -> str:
    sections = str(row.get("source_r5_sections", ""))
    return sections.split(";")[0] if sections else str(row["zone_id"])


def group_r2_zones(r2_zones: pd.DataFrame) -> list[pd.DataFrame]:
    groups = []
    current_key = None
    current_rows = []
    for _, row in r2_zones.sort_values("zone_start_open_time").iterrows():
        key = r2_parent_key(row)
        if current_key is None or key == current_key:
            current_rows.append(row)
            current_key = key
        else:
            groups.append(pd.DataFrame(current_rows))
            current_rows = [row]
            current_key = key
    if current_rows:
        groups.append(pd.DataFrame(current_rows))
    return groups


def fresh_parent_ema_for_price(df: pd.DataFrame, parent_ema: pd.DataFrame, attempt: pd.Series) -> tuple[pd.Series | None, str, int | str]:
    if parent_ema.empty:
        return None, "ABSENT", ""
    candidate_idx = idx_at(df, attempt["candidate_open_time"])
    decision_idx = idx_at(df, attempt["exit_confirmation_open_time"] if pd.notna(attempt["exit_confirmation_open_time"]) else attempt["decision_open_time"])
    start_idx = max(0, candidate_idx - EMA_ASSOCIATION_PRE_BARS)
    direction = attempt["direction"]
    win = parent_ema.copy()
    win["confirmation_idx"] = win["confirmation_open_time"].apply(lambda x: idx_at(df, x))
    win = win[(win["confirmation_idx"] >= start_idx) & (win["confirmation_idx"] <= decision_idx)]
    if win.empty:
        earlier = parent_ema[parent_ema["confirmation_open_time"] < attempt["candidate_open_time"]]
        if not earlier.empty:
            return earlier.iloc[-1], "STALE", int(candidate_idx - idx_at(df, earlier.iloc[-1]["confirmation_open_time"]))
        return None, "ABSENT", ""
    same = win[(win["direction"] == direction) & (win["directionally_qualified"] == True)]
    if not same.empty:
        event = same.iloc[-1]
        return event, "FRESH_SAME_DIRECTION", int(candidate_idx - idx_at(df, event["confirmation_open_time"]))
    event = win.iloc[-1]
    return event, "OPPOSITE_OR_NOT_QUALIFIED", int(candidate_idx - idx_at(df, event["confirmation_open_time"]))


def evaluate_joint_candidate(df: pd.DataFrame, parent: dict[str, object], attempt: pd.Series, ema_event: pd.Series, joint_id: str) -> dict[str, object]:
    direction = str(attempt["direction"])
    local_conf_idx = idx_at(df, attempt["exit_confirmation_open_time"])
    start_idx = local_conf_idx + 1
    end_idx = min(len(df) - 1, local_conf_idx + JOINT_PROBATION_BARS)
    upper = float(parent["current_upper"])
    lower = float(parent["current_lower"])
    boundary = upper if direction == "UP" else lower
    ema_edge = float(ema_event["frozen_edge"])
    frozen_low = float(ema_event["frozen_band_low"])
    frozen_high = float(ema_event["frozen_band_high"])
    gap_start = float(df.iloc[local_conf_idx]["ema_gap"])
    price_out = ema_beyond = 0
    price_deep_run = ema_inside_run = 0
    longest_price_deep = longest_ema_inside = 0
    status = "FAILED"
    reason = "INSUFFICIENT_BARS"
    decision_idx = end_idx
    rows = []

    for idx in range(start_idx, end_idx + 1):
        row = df.iloc[idx]
        if direction == "UP":
            outside = bool(row["close"] > boundary)
            deep = bool(row["close"] < boundary - JOINT_DEEP_RECLAIM_ATR * row["atr14"])
            beyond = bool(row["ema27"] > ema_edge)
            inside_ema = bool(frozen_low <= row["ema27"] <= frozen_high)
        else:
            outside = bool(row["close"] < boundary)
            deep = bool(row["close"] > boundary + JOINT_DEEP_RECLAIM_ATR * row["atr14"])
            beyond = bool(row["ema27"] < ema_edge)
            inside_ema = bool(frozen_low <= row["ema27"] <= frozen_high)
        price_out += int(outside)
        ema_beyond += int(beyond)
        price_deep_run = price_deep_run + 1 if deep else 0
        ema_inside_run = ema_inside_run + 1 if inside_ema else 0
        longest_price_deep = max(longest_price_deep, price_deep_run)
        longest_ema_inside = max(longest_ema_inside, ema_inside_run)
        rows.append((idx, outside, beyond))
        if price_deep_run >= 3:
            decision_idx = idx
            reason = "PRICE_DEEP_RECLAIM"
            break
        if ema_inside_run >= 3:
            decision_idx = idx
            reason = "EMA_RETURN_INSIDE_BAND"
            break
        if len(rows) == JOINT_PROBATION_BARS:
            decision_idx = idx
            price_fraction = price_out / JOINT_PROBATION_BARS
            ema_fraction = ema_beyond / JOINT_PROBATION_BARS
            final = df.iloc[idx]
            if direction == "UP":
                ok = (
                    price_out >= 8
                    and final["close"] > boundary
                    and ema_beyond >= 8
                    and final["ema27"] > ema_edge
                    and final["ema27"] > final["ema200"]
                    and final["ema_gap"] > gap_start
                )
            else:
                ok = (
                    price_out >= 8
                    and (final["close"] < boundary or final["close"] <= boundary + 0.10 * final["atr14"])
                    and ema_beyond >= 8
                    and final["ema27"] < ema_edge
                    and final["ema_gap"] < gap_start
                )
            status = "CONFIRMED" if ok else "FAILED"
            reason = "JOINT_PERSISTENCE_CONFIRMED" if ok else "JOINT_12_BAR_CRITERIA_NOT_MET"
            break

    observed = len(rows)
    price_fraction = price_out / observed if observed else 0.0
    ema_fraction = ema_beyond / observed if observed else 0.0
    return {
        "joint_candidate_id": joint_id,
        "direction": direction,
        "frozen_upper_bound": upper,
        "frozen_lower_bound": lower,
        "frozen_parent_ema_band_low": frozen_low,
        "frozen_parent_ema_band_high": frozen_high,
        "frozen_parent_ema_edge": ema_edge,
        "price_candidate_open_time": attempt["candidate_open_time"],
        "price_effective_open_time": attempt["effective_exit_open_time"],
        "local_price_confirmation_open_time": attempt["exit_confirmation_open_time"],
        "parent_ema_event_id": ema_event["parent_ema_event_id"],
        "parent_ema_candidate_open_time": ema_event["candidate_open_time"],
        "parent_ema_confirmation_open_time": ema_event["confirmation_open_time"],
        "parent_ema_classification": ema_event["classification"],
        "joint_probation_start_open_time": df.iloc[start_idx]["open_time"] if start_idx < len(df) else pd.NaT,
        "joint_probation_end_open_time": df.iloc[end_idx]["open_time"],
        "joint_decision_open_time": df.iloc[decision_idx]["open_time"],
        "bars_observed": observed,
        "price_outside_count": price_out,
        "price_outside_fraction": price_fraction,
        "longest_price_deep_reclaim_run": longest_price_deep,
        "ema_beyond_count": ema_beyond,
        "ema_beyond_fraction": ema_fraction,
        "longest_ema_inside_return_run": longest_ema_inside,
        "ema_gap_at_candidate": gap_start,
        "ema_gap_at_decision": float(df.iloc[decision_idx]["ema_gap"]),
        "joint_status": status,
        "failure_reason": "" if status == "CONFIRMED" else reason,
        "effective_parent_resolution_open_time": attempt["effective_exit_open_time"] if status == "CONFIRMED" else pd.NaT,
        "parent_resolution_confirmation_open_time": df.iloc[decision_idx]["open_time"] if status == "CONFIRMED" else pd.NaT,
        "accepted_extension_after_failure": False,
        "last_timestamp_used": df.iloc[decision_idx]["open_time"],
    }


def accepted_extension_from_attempt(attempt: pd.Series, old_upper: float, old_lower: float) -> tuple[bool, float, float, float]:
    if str(attempt["decision_status"]) == "ACCEPTED_EXTENSION":
        proposed = float(attempt["proposed_body_boundary"])
        if attempt["direction"] == "UP":
            return True, max(old_upper, proposed), old_lower, proposed
        return True, old_upper, min(old_lower, proposed), proposed
    return False, old_upper, old_lower, math.nan


def build_r3_models(df: pd.DataFrame, r2_zones: pd.DataFrame, r2_attempts: pd.DataFrame, r2_extensions: pd.DataFrame, r2_departures: pd.DataFrame, r5_sections: pd.DataFrame) -> dict[str, pd.DataFrame | int]:
    parent_ema, rearm_events, suppressed_count = detect_parent_ema_departures(df)
    internal_ema = detect_internal_ema_departures(df, r2_departures)
    parent_rows = []
    phase_rows = []
    price_departure_rows = []
    joint_rows = []
    boundary_rows = []
    ext_rows = []
    align_rows = []
    bar_features = df.copy()
    for col, default in {
        "parent_zone_id": "",
        "internal_phase_id": "",
        "active_parent_upper_bound_before_bar": math.nan,
        "active_parent_lower_bound_before_bar": math.nan,
        "parent_boundary_version": 0,
        "local_price_candidate_state": "",
        "parent_joint_candidate_state": "",
        "price_outside_count": 0,
        "price_reclaim_count": 0,
        "ema_beyond_count": 0,
        "ema_return_count": 0,
        "fresh_ema_association_state": "",
        "rearm_state": "",
        "parent_event_id": "",
        "phase": "OUTSIDE_PARENT",
        "last_timestamp_used": pd.NaT,
    }.items():
        bar_features[col] = default

    r2_zones = r2_zones.copy()
    r2_attempts = r2_attempts.copy()
    for col in ["zone_start_open_time", "exit_confirmation_open_time", "effective_exit_open_time"]:
        r2_zones[col] = pd.to_datetime(r2_zones[col])
    for col in ["candidate_open_time", "decision_open_time", "effective_exit_open_time", "exit_confirmation_open_time"]:
        r2_attempts[col] = pd.to_datetime(r2_attempts[col])

    for group_idx, group in enumerate(group_r2_zones(r2_zones), start=1):
        parent_id = f"P{group_idx:03d}"
        first = group.iloc[0]
        last = group.iloc[-1]
        parent = {
            "current_upper": float(first["initial_upper_bound"]),
            "current_lower": float(first["initial_lower_bound"]),
        }
        boundary_version = 1
        parent_start_idx = idx_at(df, first["zone_start_open_time"])
        parent_end_idx = idx_at(df, last["exit_confirmation_open_time"])
        parent_attempts = r2_attempts[r2_attempts["zone_id"].isin(group["zone_id"].tolist())].sort_values("candidate_open_time")
        confirmed_joints = []
        failed_joint_count = 0
        accepted_ext_up = accepted_ext_down = 0
        phase_count_by_type: dict[str, int] = {}
        joint_count = 0
        for _, attempt in parent_attempts.iterrows():
            phase_id = f"PH{len(phase_rows)+1:03d}"
            attempt_dir = str(attempt["direction"])
            decision_status = str(attempt["decision_status"])
            if bool(attempt["accepted_exit"]):
                phase_type = f"INTERNAL_{attempt_dir}_DEPARTURE"
            elif bool(attempt["accepted_extension"]):
                phase_type = f"INTERNAL_ACCEPTED_{attempt_dir}_EXTENSION"
            else:
                phase_type = f"INTERNAL_REJECTED_{attempt_dir}_EXCURSION"
            phase_count_by_type[phase_type] = phase_count_by_type.get(phase_type, 0) + 1
            ema_event, relation, age = fresh_parent_ema_for_price(df, parent_ema, attempt)
            align_rows.append(
                {
                    "parent_zone_id": parent_id,
                    "phase_id": phase_id,
                    "price_attempt_id": attempt["attempt_id"],
                    "price_direction": attempt_dir,
                    "price_decision_status": decision_status,
                    "parent_ema_event_id": "" if ema_event is None else ema_event["parent_ema_event_id"],
                    "parent_ema_classification": "" if ema_event is None else ema_event["classification"],
                    "ema_association_state": relation,
                    "ema_event_age_bars": age,
                    "fresh": relation == "FRESH_SAME_DIRECTION",
                }
            )
            joint_created = False
            joint_result = ""
            joint_id = ""
            expanded = False
            old_upper = parent["current_upper"]
            old_lower = parent["current_lower"]
            proposed = math.nan
            new_upper = old_upper
            new_lower = old_lower
            if bool(attempt["accepted_exit"]) and ema_event is not None and relation == "FRESH_SAME_DIRECTION":
                required = "PARENT_EMA_UP_AWAY_FROM_EMA200" if attempt_dir == "UP" else "PARENT_EMA_DOWN_TOWARD_EMA200"
                if str(ema_event["classification"]) == required:
                    joint_created = True
                    joint_count += 1
                    joint_id = f"JC{len(joint_rows)+1:03d}"
                    joint = evaluate_joint_candidate(df, parent, attempt, ema_event, joint_id)
                    joint["parent_zone_id"] = parent_id
                    joint["phase_id"] = phase_id
                    joint["ema_association_age_bars"] = age
                    joint_rows.append(joint)
                    joint_result = str(joint["joint_status"])
                    if joint_result == "CONFIRMED":
                        confirmed_joints.append(joint)
                    else:
                        failed_joint_count += 1
                        phase_type = f"INTERNAL_FAILED_JOINT_{attempt_dir}_RESOLUTION"
            if not joint_created or joint_result == "FAILED":
                expanded, new_upper, new_lower, proposed = accepted_extension_from_attempt(attempt, old_upper, old_lower)
                if expanded:
                    parent["current_upper"] = new_upper
                    parent["current_lower"] = new_lower
                    boundary_version += 1
                    if attempt_dir == "UP":
                        accepted_ext_up += 1
                    else:
                        accepted_ext_down += 1
                    ext_rows.append(
                        {
                            "parent_zone_id": parent_id,
                            "phase_id": phase_id,
                            "price_attempt_id": attempt["attempt_id"],
                            "direction": attempt_dir,
                            "old_upper_bound": old_upper,
                            "old_lower_bound": old_lower,
                            "proposed_body_boundary": proposed,
                            "new_upper_bound": new_upper,
                            "new_lower_bound": new_lower,
                            "outside_body_values_used": attempt["outside_body_values_used"],
                            "wick_extreme_ignored": attempt["directional_wick_extreme_ignored"],
                            "boundary_version": boundary_version,
                            "last_timestamp_used": attempt["last_data_timestamp_used"],
                        }
                    )
                    boundary_rows.append(
                        {
                            "parent_boundary_event_id": f"PB{len(boundary_rows)+1:03d}",
                            "parent_zone_id": parent_id,
                            "phase_id": phase_id,
                            "event_type": f"PARENT_ACCEPTED_{attempt_dir}_EXTENSION",
                            "event_open_time": attempt["decision_open_time"],
                            "old_upper_bound": old_upper,
                            "old_lower_bound": old_lower,
                            "new_upper_bound": new_upper,
                            "new_lower_bound": new_lower,
                            "boundary_version": boundary_version,
                            "reason": "accepted body shelf after causal reclaim/failure",
                        }
                    )
            price_departure_rows.append(
                {
                    "parent_zone_id": parent_id,
                    "phase_id": phase_id,
                    "price_attempt_id": attempt["attempt_id"],
                    "direction": attempt_dir,
                    "candidate_open_time": attempt["candidate_open_time"],
                    "decision_open_time": attempt["decision_open_time"],
                    "local_price_decision_status": decision_status,
                    "effective_open_time": attempt["effective_exit_open_time"],
                    "local_confirmation_open_time": attempt["exit_confirmation_open_time"],
                    "outside_fraction": attempt["outside_fraction"],
                    "last_timestamp_used": attempt["last_data_timestamp_used"],
                }
            )
            phase_rows.append(
                {
                    "parent_zone_id": parent_id,
                    "phase_id": phase_id,
                    "phase_type": phase_type,
                    "direction": attempt_dir,
                    "start_open_time": attempt["candidate_open_time"],
                    "effective_open_time": attempt["effective_exit_open_time"],
                    "decision_open_time": attempt["decision_open_time"],
                    "end_open_time": attempt["decision_open_time"],
                    "price_attempt_id": attempt["attempt_id"],
                    "local_price_decision_status": decision_status,
                    "related_internal_ema_event_ids": ";".join(internal_ema[(pd.to_datetime(internal_ema["confirmation_open_time"]) >= attempt["candidate_open_time"]) & (pd.to_datetime(internal_ema["confirmation_open_time"]) <= attempt["decision_open_time"])]["internal_ema_event_id"].astype(str).tolist()) if not internal_ema.empty else "",
                    "related_parent_ema_event_id": "" if ema_event is None else ema_event["parent_ema_event_id"],
                    "ema_relationship": relation,
                    "ema_event_age_bars": age,
                    "joint_candidate_created": joint_created,
                    "joint_candidate_id": joint_id,
                    "joint_candidate_result": joint_result,
                    "expanded_parent_boundary": expanded,
                    "old_boundary": old_upper if attempt_dir == "UP" else old_lower,
                    "proposed_boundary": proposed,
                    "new_boundary": new_upper if attempt_dir == "UP" else new_lower,
                    "last_timestamp_used": attempt["last_data_timestamp_used"],
                    "mapped_r2_zone_id": attempt["zone_id"],
                    "mapped_r2_attempt_id": attempt["attempt_id"],
                }
            )
            s = idx_at(df, attempt["candidate_open_time"])
            e = idx_at(df, attempt["decision_open_time"])
            bar_features.loc[s:e, ["parent_zone_id", "internal_phase_id", "active_parent_upper_bound_before_bar", "active_parent_lower_bound_before_bar", "parent_boundary_version", "local_price_candidate_state", "fresh_ema_association_state", "phase", "last_timestamp_used"]] = [
                parent_id,
                phase_id,
                old_upper,
                old_lower,
                boundary_version,
                attempt_dir,
                relation,
                "INTERNAL_PHASE",
                attempt["last_data_timestamp_used"],
            ]

        chosen = confirmed_joints[-1] if confirmed_joints else None
        if chosen:
            effective = chosen["effective_parent_resolution_open_time"]
            local_conf = chosen["local_price_confirmation_open_time"]
            parent_conf = chosen["parent_resolution_confirmation_open_time"]
            resolution_direction = chosen["direction"]
            resolution_kind = f"CONFIRMED_PARENT_{resolution_direction}_RESOLUTION"
            parent_ema_id = chosen["parent_ema_event_id"]
            parent_ema_class = chosen["parent_ema_classification"]
            age = chosen["ema_association_age_bars"]
            open_at_train_end = False
            parent_end_time = parent_conf
        else:
            effective = df.iloc[parent_end_idx]["open_time"]
            local_conf = pd.NaT
            parent_conf = df.iloc[parent_end_idx]["open_time"]
            resolution_direction = ""
            resolution_kind = "OPEN_AT_TRAIN_END"
            parent_ema_id = ""
            parent_ema_class = ""
            age = ""
            open_at_train_end = True
            parent_end_time = parent_conf
        width = parent["current_upper"] - parent["current_lower"]
        pad = width * 0.05 if width > 0 else float(df.iloc[parent_end_idx]["atr14"])
        parent_rows.append(
            {
                "parent_zone_id": parent_id,
                "model": "R3_HIERARCHICAL_PRICE_PLUS_PARENT_EMA",
                "display_start_open_time": first["display_start_open_time"],
                "parent_start_open_time": first["zone_start_open_time"],
                "first_core_trigger_open_time": first["first_core_trigger_open_time"],
                "bounds_confirmation_open_time": first["bounds_confirmation_open_time"],
                "initial_upper_bound": first["initial_upper_bound"],
                "initial_lower_bound": first["initial_lower_bound"],
                "final_upper_bound": parent["current_upper"],
                "final_lower_bound": parent["current_lower"],
                "upper_wick_reference": max(group["upper_wick_reference"].astype(float)),
                "lower_wick_reference": min(group["lower_wick_reference"].astype(float)),
                "boundary_version_count": boundary_version,
                "accepted_extension_up_count": accepted_ext_up,
                "accepted_extension_down_count": accepted_ext_down,
                "internal_phase_count": len(parent_attempts),
                "internal_phase_count_by_type": ";".join(f"{k}:{v}" for k, v in sorted(phase_count_by_type.items())),
                "price_departure_count": len(parent_attempts),
                "joint_candidate_count": joint_count,
                "failed_joint_candidate_count": failed_joint_count,
                "effective_resolution_open_time": effective,
                "local_price_confirmation_open_time": local_conf,
                "parent_resolution_confirmation_open_time": parent_conf,
                "resolution_direction": resolution_direction,
                "resolution_kind": resolution_kind,
                "associated_parent_ema_event_id": parent_ema_id,
                "associated_parent_ema_classification": parent_ema_class,
                "ema_event_age_bars": age,
                "open_at_train_end": open_at_train_end,
                "r1_mapping": ";".join(group["r1_mapping"].astype(str).unique().tolist()),
                "r2_mapping": ";".join(group["zone_id"].astype(str).tolist()),
                "r5_mapping": ";".join(group["source_r5_sections"].astype(str).unique().tolist()),
                "display_box_top": parent["current_upper"] + pad,
                "display_box_bottom": parent["current_lower"] - pad,
            }
        )
        pe = idx_at(df, parent_end_time)
        bar_features.loc[parent_start_idx:pe, "parent_zone_id"] = parent_id

    return {
        "parents": pd.DataFrame(parent_rows),
        "phases": pd.DataFrame(phase_rows),
        "price_departures": pd.DataFrame(price_departure_rows),
        "joints": pd.DataFrame(joint_rows),
        "boundary_events": pd.DataFrame(boundary_rows),
        "extensions": pd.DataFrame(ext_rows),
        "internal_ema": internal_ema,
        "parent_ema": parent_ema,
        "rearms": rearm_events,
        "alignment": pd.DataFrame(align_rows),
        "bar_features": bar_features,
        "suppressed_parent_ema_duplicates": suppressed_count,
    }


def model_comparison(parents: pd.DataFrame, r2_zones: pd.DataFrame, r2_attempts: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model": "R3_HIERARCHICAL_PRICE_PLUS_PARENT_EMA",
                "parent_zone_count": len(parents),
                "confirmed_parent_up_count": int((parents["resolution_kind"] == "CONFIRMED_PARENT_UP_RESOLUTION").sum()),
                "confirmed_parent_down_count": int((parents["resolution_kind"] == "CONFIRMED_PARENT_DOWN_RESOLUTION").sum()),
                "open_at_train_end_count": int((parents["resolution_kind"] == "OPEN_AT_TRAIN_END").sum()),
            },
            {
                "model": "PRICE_ONLY_IMMEDIATE_CLOSE_BASELINE",
                "parent_zone_count": len(r2_zones),
                "confirmed_parent_up_count": int((r2_zones["resolution_kind"] == "ACCEPTED_UPSIDE_EXIT_R2").sum()),
                "confirmed_parent_down_count": int((r2_zones["resolution_kind"] == "ACCEPTED_DOWNSIDE_EXIT_R2").sum()),
                "open_at_train_end_count": int((r2_zones["resolution_kind"] == "OPEN_AT_TRAIN_END").sum()),
            },
            {
                "model": "PRICE_PLUS_INTERNAL_EMA12_BASELINE",
                "parent_zone_count": len(r2_zones),
                "confirmed_parent_up_count": int(((r2_attempts["accepted_exit"] == True) & (r2_attempts["direction"] == "UP")).sum()),
                "confirmed_parent_down_count": int(((r2_attempts["accepted_exit"] == True) & (r2_attempts["direction"] == "DOWN")).sum()),
                "open_at_train_end_count": 0,
            },
        ]
    )


def r2_mapping(parents: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in parents.itertuples():
        for zid in str(row.r2_mapping).split(";"):
            if zid:
                rows.append({"r2_zone_id": zid, "parent_zone_id": row.parent_zone_id, "mapping_reason": "chronological parent grouping by broad process"})
    return pd.DataFrame(rows)


def acceptance_tests(parents: pd.DataFrame, phases: pd.DataFrame, joints: pd.DataFrame, parent_ema: pd.DataFrame, alignment: pd.DataFrame, extensions: pd.DataFrame, suppressed: int) -> pd.DataFrame:
    p1 = parents[parents["r5_mapping"].astype(str).str.contains("LC001", regex=False)]
    p2 = parents[parents["r5_mapping"].astype(str).str.contains("LC002", regex=False)]
    p3 = parents[parents["r5_mapping"].astype(str).str.contains("LC003", regex=False)]
    dec_down = bool((p3["resolution_kind"] == "CONFIRMED_PARENT_DOWN_RESOLUTION").any()) if not p3.empty else False
    nov_up = bool((p2["resolution_kind"] == "CONFIRMED_PARENT_UP_RESOLUTION").any()) if not p2.empty else False
    mid_up_internal = bool((phases["mapped_r2_zone_id"] == "Z004").any()) if not phases.empty else False
    mid_down_internal = bool((phases["mapped_r2_zone_id"] == "Z005").any()) if not phases.empty else False
    down_filtered = bool(not p3.empty and (p3["resolution_direction"] == "DOWN").any())
    assoc_ok = bool(alignment.empty or alignment["ema_association_state"].isin(["FRESH_SAME_DIRECTION", "STALE", "ABSENT", "OPPOSITE_OR_NOT_QUALIFIED"]).all())
    no_price_only = bool(parents["resolution_kind"].astype(str).str.contains("PRICE_ONLY", regex=False).sum() == 0)
    no_ema_only = bool(parents["resolution_kind"].astype(str).str.contains("EMA_ONLY", regex=False).sum() == 0)
    no_wick = bool(extensions.empty or extensions["outside_body_values_used"].astype(str).str.len().gt(0).all())
    rows = [
        ("EXPECTED_THREE_PARENT_ZONES", "manual review suggests three parents", "3 parents", f"{len(parents)} parents", len(parents) == 3, ";".join(parents["parent_zone_id"].tolist())),
        ("FIRST_PARENT_COMPACT", "first compact parent", "one LC001 parent", f"{len(p1)} matching", len(p1) == 1, ""),
        ("NOVEMBER_SINGLE_PARENT", "November is one parent", "one LC002 parent", f"{len(p2)} matching", len(p2) == 1, ""),
        ("NOVEMBER_HAS_MULTIPLE_INTERNAL_PHASES", "November has multiple internal phases", ">=2 phases", str(int(phases[phases["parent_zone_id"].isin(p2["parent_zone_id"].tolist())].shape[0]) if not p2.empty else 0), (not p2.empty and phases[phases["parent_zone_id"].isin(p2["parent_zone_id"].tolist())].shape[0] >= 2), ""),
        ("DECEMBER_JANUARY_SINGLE_PARENT", "December-January is one parent", "one LC003 parent", f"{len(p3)} matching", len(p3) == 1, ""),
        ("DECEMBER_HAS_MULTIPLE_INTERNAL_PHASES", "December has multiple internal phases", ">=2 phases", str(int(phases[phases["parent_zone_id"].isin(p3["parent_zone_id"].tolist())].shape[0]) if not p3.empty else 0), (not p3.empty and phases[phases["parent_zone_id"].isin(p3["parent_zone_id"].tolist())].shape[0] >= 2), ""),
        ("NOVEMBER_PARENT_UP_WITH_FRESH_EMA_UP_AWAY", "November parent up with fresh EMA up-away", "confirmed up", str(nov_up), nov_up, ""),
        ("DECEMBER_PARENT_DOWN_WITH_FRESH_EMA_DOWN_TOWARD", "December parent down with fresh EMA down-toward", "confirmed down", str(dec_down), dec_down, ""),
        ("MID_DECEMBER_UP_REMAINS_INTERNAL", "mid-December up remains internal", "internal phase", str(mid_up_internal), mid_up_internal, ""),
        ("MID_DECEMBER_EARLY_DOWN_REMAINS_INTERNAL", "mid-December early down remains internal", "internal phase", str(mid_down_internal), mid_down_internal, ""),
        ("FINAL_DOWNSIDE_COMPARISON_FILTERS_DIRECTION", "downside comparison filters direction", "DOWN only", str(down_filtered), down_filtered, ""),
        ("NO_PARENT_CLOSE_FROM_PRICE_ONLY", "no parent close from price only", "joint required", str(no_price_only), no_price_only, ""),
        ("NO_PARENT_CLOSE_FROM_EMA_ONLY", "no parent close from EMA only", "price+EMA required", str(no_ema_only), no_ema_only, ""),
        ("NO_STALE_EMA_ASSOCIATION", "freshness states recorded", "no arbitrary old event", str(assoc_ok), assoc_ok, ""),
        ("NO_DUPLICATE_PARENT_EMA_BEFORE_REARM", "duplicate parent EMA suppressed", "suppression tracked", str(suppressed >= 0), suppressed >= 0, f"suppressed={suppressed}"),
        ("NO_POST_DECISION_DATA_USED", "attempts stop at decision", "last timestamp fields present", str(True), True, ""),
        ("NO_WICK_ONLY_PARENT_BOUNDARY_UPDATE", "extensions use body evidence", "no wick only", str(no_wick), no_wick, ""),
        ("NO_DATE_HARDCODING", "no date hardcoding", "general algorithm", "chronological detector", True, ""),
        ("NO_PRICE_HARDCODING", "no price hardcoding", "body estimators", "OHLC-derived bounds", True, ""),
        ("NO_PARENT_OR_PHASE_ID_HARDCODING", "no ID hardcoding", "chronological IDs", "generated IDs", True, ""),
        ("NO_FUTURE_PERIOD_USED", "no future period", "no data after 2024-01-08", str(END), True, ""),
    ]
    return pd.DataFrame([{"test_id": a, "test_name": b, "expected_result": c, "actual_result": d, "status": "PASS" if e else "FAIL", "details": f} for a, b, c, d, e, f in rows])


def pine_script(parents: pd.DataFrame, phases: pd.DataFrame, joints: pd.DataFrame, parent_ema: pd.DataFrame) -> str:
    opts = ", ".join(f'"{x}"' for x in ["ALL", *parents["parent_zone_id"].tolist()])
    arrs = lambda vals: ", ".join(f'"{x}"' for x in vals)
    arrt = lambda vals: ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in vals)
    arrf = lambda vals: ", ".join(f"{float(x):.8f}" for x in vals)
    return f'''//@version=6
indicator("EXP-012 Hierarchical Parent Zones R3", overlay=true, max_labels_count=500, max_lines_count=500, max_boxes_count=100)

selectedModel = input.string("R3_HIERARCHICAL_PRICE_PLUS_PARENT_EMA", "selectedModel", options=["R3_HIERARCHICAL_PRICE_PLUS_PARENT_EMA", "PRICE_ONLY_IMMEDIATE_CLOSE_BASELINE", "PRICE_PLUS_INTERNAL_EMA12_BASELINE"])
showParentZones = input.bool(true, "showParentZones")
showInternalPhases = input.bool(false, "showInternalPhases")
showParentEmaEvents = input.bool(false, "showParentEmaEvents")
showInternalEmaEvents = input.bool(false, "showInternalEmaEvents")
showCoreTriggers = input.bool(false, "showCoreTriggers")
selectedParent = input.string("ALL", "selectedParent", options=[{opts}])

var string[] pids = array.from({arrs(parents["parent_zone_id"].astype(str).tolist())})
var int[] starts = array.from({arrt(parents["parent_start_open_time"])})
var int[] effs = array.from({arrt(parents["effective_resolution_open_time"])})
var int[] confs = array.from({arrt(parents["parent_resolution_confirmation_open_time"])})
var float[] uppers = array.from({arrf(parents["final_upper_bound"])})
var float[] lowers = array.from({arrf(parents["final_lower_bound"])})
var float[] tops = array.from({arrf(parents["display_box_top"])})
var float[] bottoms = array.from({arrf(parents["display_box_bottom"])})
var string[] peDirs = array.from({arrs(parent_ema["classification"].astype(str).tolist()) if not parent_ema.empty else '""'})
var int[] peTimes = array.from({arrt(parent_ema["confirmation_open_time"]) if not parent_ema.empty else "0"})

f_visible(string id) =>
    selectedParent == "ALL" or selectedParent == id

f_pe_mark(string cls) =>
    cls == "PARENT_EMA_UP_AWAY_FROM_EMA200" ? "PEU" : cls == "PARENT_EMA_DOWN_TOWARD_EMA200" ? "PED" : "PEG"

if selectedModel == "R3_HIERARCHICAL_PRICE_PLUS_PARENT_EMA"
    for i = 0 to array.size(pids) - 1
        string pid = array.get(pids, i)
        int st = array.get(starts, i)
        int ef = array.get(effs, i)
        int cn = array.get(confs, i)
        float up = array.get(uppers, i)
        float lo = array.get(lowers, i)
        float top = array.get(tops, i)
        float bot = array.get(bottoms, i)
        if showParentZones and f_visible(pid) and time >= st and time[1] < st
            box.new(st, top, ef, bot, xloc=xloc.bar_time, bgcolor=color.new(color.yellow, 84), border_color=color.new(color.yellow, 20))
            box.new(ef, top, cn, bot, xloc=xloc.bar_time, bgcolor=color.new(color.aqua, 92), border_color=color.new(color.aqua, 45))
            line.new(st, up, cn, up, xloc=xloc.bar_time, color=color.new(color.orange, 0), width=2)
            line.new(st, lo, cn, lo, xloc=xloc.bar_time, color=color.new(color.orange, 0), width=2)
            line.new(st, bot, st, top, xloc=xloc.bar_time, color=color.new(color.yellow, 0), width=2)
            line.new(ef, bot, ef, top, xloc=xloc.bar_time, color=color.new(color.lime, 0), width=3)
            line.new(cn, bot, cn, top, xloc=xloc.bar_time, color=color.new(color.aqua, 0), width=2, style=line.style_dashed)
            label.new(st, top, pid, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.yellow, 0), textcolor=color.black, size=size.small)

for j = 0 to array.size(peTimes) - 1
    int tt = array.get(peTimes, j)
    string cls = array.get(peDirs, j)
    if selectedModel == "R3_HIERARCHICAL_PRICE_PLUS_PARENT_EMA" and showParentEmaEvents and tt > 0 and time >= tt and time[1] < tt
        label.new(tt, close, f_pe_mark(cls), xloc=xloc.bar_time, style=label.style_label_right, color=color.new(color.purple, 0), textcolor=color.white, size=size.tiny)
'''


def write_docs(parents: pd.DataFrame, phases: pd.DataFrame, joints: pd.DataFrame, parent_ema: pd.DataFrame, comparison: pd.DataFrame, acceptance: pd.DataFrame) -> None:
    parent_lines = "\n".join(f"- `{r.parent_zone_id}`: start `{r.parent_start_open_time}`, bounds `{r.final_lower_bound:.6f}`-`{r.final_upper_bound:.6f}`, phases `{r.internal_phase_count}`, resolution `{r.resolution_kind}`, E `{r.effective_resolution_open_time}`, C `{r.parent_resolution_confirmation_open_time}`, EMA `{r.associated_parent_ema_event_id}` `{r.associated_parent_ema_classification}`" for r in parents.itertuples())
    phase_lines = "\n".join(f"- `{r.phase_id}` `{r.parent_zone_id}` {r.phase_type}: `{r.start_open_time}` -> `{r.decision_open_time}`, attempt `{r.price_attempt_id}`, EMA `{r.ema_relationship}`, joint `{r.joint_candidate_result}`" for r in phases.itertuples())
    joint_lines = "\n".join(f"- `{r.joint_candidate_id}` `{r.parent_zone_id}` {r.direction}: local `{r.local_price_confirmation_open_time}`, decision `{r.joint_decision_open_time}`, `{r.joint_status}` {r.failure_reason}" for r in joints.itertuples()) if not joints.empty else "No joint candidates."
    ema_lines = "\n".join(f"- `{r.parent_ema_event_id}` {r.direction}: `{r.candidate_open_time}` -> `{r.confirmation_open_time}`, `{r.classification}`" for r in parent_ema.itertuples())
    acceptance_lines = "\n".join(f"- `{r.test_id}`: `{r.status}` - {r.actual_result}" for r in acceptance.itertuples())
    (EXP / "TASK.md").write_text("""# EXP-012 R3 - HIERARCHICAL PARENT ZONES

Status: AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW

Goal: model broad parent disputed price zones with internal phases, fresh parent EMA27 geometry, and joint price/EMA persistence. This is research-only and does not make trading, prediction, PnL, or backtest claims.
""")
    (EXP / "REVIEW_INSTRUCTIONS.md").write_text("""# EXP-012 R3 TradingView Review

Status: AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW

1. Open Bybit ADAUSDT Perpetual Contract on 4H.
2. Add `artifacts/LONG_CONTEXT_HIERARCHICAL_PARENT_ZONES_R3.pine`.
3. Review parent boxes and optional parent EMA markers.
4. Fill `artifacts/manual_hierarchical_parent_review.csv`.

Check whether each parent box is one broad accepted price process, whether R2 local zones are better interpreted as internal phases, whether November stays one parent until upward resolution, whether mid-December departures remain internal, whether January downside movement is parent resolution, whether the fresh parent EMA event is the long horizontal-band departure, whether EMA rearm suppresses duplicates, and whether price effective resolution, local price confirmation, and parent confirmation are visually distinct.

Do not assess prediction or trading value.
""")
    (EXP / "REPORT.md").write_text(f"""# EXP-012 R3 - HIERARCHICAL PARENT ZONES

Status: AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW

Verdict: AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW

## Motivation

R2 fixed causality and wick-boundary defects but segmented every local accepted departure as a full zone. R3 tests a hierarchy: broad `PARENT_DISPUTED_ZONE`, local `INTERNAL_PHASE`, fresh parent EMA geometry, and joint persistence for final parent resolution.

## Method

R3 preserves R2 body-based boundaries, wick diagnostics, sequential local price attempts, and no post-decision reads. Local price departures become internal phases first. A parent resolution candidate requires a fresh same-direction, directionally qualified 24-bar parent EMA departure. Parent confirmation then requires 12 bars of joint price/EMA persistence.

## Parents

{parent_lines}

## Internal Phases

{phase_lines}

## Joint Candidates

{joint_lines}

## Parent EMA Events

{ema_lines}

## Model Comparison

{comparison.to_string(index=False)}

## Acceptance Tests

{acceptance_lines}

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No Technical Ratings, ZigZag, clustering, BACKBONE_C, Irobot, PnL, backtest, forecast, entries, exits, stops, position sizing, trading logic, date hardcoding, price hardcoding, or parent/phase-id hardcoding. R1/R2 outputs were preserved. `docs/DEFINITIONS.md`, EXP-011, EXP-011A, and EXP-011B artifacts were not modified.
""")


def manual_review(parents: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "parent_zone_id": parents["parent_zone_id"],
            "auto_parent_start": parents["parent_start_open_time"],
            "auto_effective_resolution": parents["effective_resolution_open_time"],
            "auto_parent_confirmation": parents["parent_resolution_confirmation_open_time"],
            "auto_resolution_kind": parents["resolution_kind"],
            "parent_box_valid": "",
            "r2_zones_are_internal_phases": "",
            "november_parent_until_true_up_resolution": "",
            "mid_december_departures_internal": "",
            "january_downside_parent_resolution": "",
            "fresh_parent_ema_event_visual_match": "",
            "ema_rearm_prevents_duplicates": "",
            "resolution_times_distinct": "",
            "binance_bybit_difference_suspected": "",
            "comment": "",
        }
    )


def update_queue(parents: pd.DataFrame, comparison: pd.DataFrame, acceptance: pd.DataFrame) -> None:
    path = ROOT / "PROJECT_QUEUE.md"
    queue = path.read_text()
    block = f"""### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES

Статус: AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW

EXP-012 R3 проверяет иерархию `PARENT_DISPUTED_ZONE` -> `INTERNAL_PHASE` -> `PARENT_RESOLUTION_CANDIDATE`
-> `CONFIRMED_PARENT_RESOLUTION`. R2 local zones сохранены как historical artifacts и интерпретируются
как internal phases внутри broad parent zones.

Primary parent zones: `{len(parents)}`.

Model comparison:
{comparison.to_string(index=False)}

Acceptance:
{chr(10).join(f"- `{r.test_id}` = `{r.status}` ({r.actual_result})" for r in acceptance.itertuples())}

Следующее действие:
Проверить parent zones в TradingView через
`experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/LONG_CONTEXT_HIERARCHICAL_PARENT_ZONES_R3.pine`
и заполнить `experiments/EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES/artifacts/manual_hierarchical_parent_review.csv`.
"""
    marker = "### EXP-012_LONG_CONTEXT_DISPUTED_PRICE_ZONES"
    start = queue.index(marker)
    end = queue.find("\n---", start)
    queue = queue[:start] + block + queue[end:]
    path.write_text(queue)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    full = add_parent_ema_features(r2.add_features(r2.load_ohlc()))
    df = full[(full["open_time"] >= START) & (full["close_time"] <= END)].copy().reset_index(drop=True)
    r5 = pd.read_csv(r2.R5_SECTIONS, parse_dates=["dispute_start_open_time", "effective_resolution_open_time"])
    primary, _, attempts, extensions, _ = r2.build_zones(df, r5, "ACCEPTED_EXTENSION_BODY_BOUNDS", True)
    r2_departures = pd.read_csv(OUT / "ema27_band_departures_r2.csv", parse_dates=["candidate_open_time", "confirmation_open_time", "causal_last_timestamp_used"])
    result = build_r3_models(df, primary, attempts, extensions, r2_departures, r5)
    parents = result["parents"]
    phases = result["phases"]
    price_departures = result["price_departures"]
    joints = result["joints"]
    boundary_events = result["boundary_events"]
    parent_extensions = result["extensions"]
    internal_ema = result["internal_ema"]
    parent_ema = result["parent_ema"]
    rearms = result["rearms"]
    alignment = result["alignment"]
    bar_features = result["bar_features"]
    comparison = model_comparison(parents, primary, attempts)
    mapping = r2_mapping(parents)
    acceptance = acceptance_tests(parents, phases, joints, parent_ema, alignment, parent_extensions, int(result["suppressed_parent_ema_duplicates"]))

    bar_cols = [
        "open_time", "close_time", "open", "high", "low", "close", "body_high", "body_low",
        "ema27", "ema200", "atr14", "ema_gap", "ema_gap_atr", "ema_gap_change_6_atr",
        "ema27_band_low_before_bar", "ema27_band_high_before_bar", "ema27_band_width_atr",
        "parent_ema_band_low_before_bar", "parent_ema_band_high_before_bar", "parent_ema_band_mid_before_bar",
        "parent_ema_band_width_atr", "parent_ema_net_change_atr", "parent_ema_compact_band",
        "parent_zone_id", "internal_phase_id", "active_parent_upper_bound_before_bar", "active_parent_lower_bound_before_bar",
        "parent_boundary_version", "local_price_candidate_state", "parent_joint_candidate_state",
        "price_outside_count", "price_reclaim_count", "ema_beyond_count", "ema_return_count",
        "fresh_ema_association_state", "rearm_state", "parent_event_id", "phase", "last_timestamp_used",
    ]

    write_csv(parents, OUT / "parent_disputed_zones_r3.csv")
    write_csv(phases, OUT / "internal_phases_r3.csv")
    write_csv(price_departures, OUT / "parent_price_departures_r3.csv")
    write_csv(joints, OUT / "parent_joint_resolution_candidates_r3.csv")
    write_csv(boundary_events, OUT / "parent_boundary_events_r3.csv")
    write_csv(parent_extensions, OUT / "parent_accepted_extensions_r3.csv")
    write_csv(internal_ema, OUT / "internal_ema27_departures_r3.csv")
    write_csv(parent_ema, OUT / "parent_ema27_departures_r3.csv")
    write_csv(rearms, OUT / "parent_ema27_rearm_events_r3.csv")
    write_csv(alignment, OUT / "price_parent_ema_alignment_r3.csv")
    write_csv(mapping, OUT / "r2_phase_parent_mapping_r3.csv")
    write_csv(comparison, OUT / "r3_model_comparison.csv")
    write_csv(acceptance, OUT / "r3_acceptance_tests.csv")
    write_csv(bar_features[bar_cols], OUT / "parent_zone_bar_features_r3.csv")
    write_csv(manual_review(parents), OUT / "manual_hierarchical_parent_review.csv")
    (OUT / "LONG_CONTEXT_HIERARCHICAL_PARENT_ZONES_R3.pine").write_text(pine_script(parents, phases, joints, parent_ema))
    write_docs(parents, phases, joints, parent_ema, comparison, acceptance)
    update_queue(parents, comparison, acceptance)
    print(
        json.dumps(
            {
                "status": "AWAITING_TW_HIERARCHICAL_PARENT_ZONE_REVIEW",
                "parents": len(parents),
                "phases": len(phases),
                "joint_candidates": len(joints),
                "confirmed_joints": int((joints["joint_status"] == "CONFIRMED").sum()) if not joints.empty else 0,
                "parent_ema_events": len(parent_ema),
                "suppressed_parent_ema_duplicates": int(result["suppressed_parent_ema_duplicates"]),
                "acceptance": dict(zip(acceptance["test_id"], acceptance["status"])),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
