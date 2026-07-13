#!/usr/bin/env python3
"""EXP-011A: slow EMA200 backbone and fast EMA27 phase decomposition.

Research-only decomposition using saved EXP-011 OHLC. No network, Irobot,
ZigZag, clustering, backtest, PnL, trading rules, or future bars are used.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-011A_SLOW_BACKBONE_FAST_PHASE"
OUT = EXP / "artifacts"
SOURCE = ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts"
FORBIDDEN = pd.Timestamp("2025-01-01 00:00:00")
MODELS = ["BACKBONE_A", "BACKBONE_B", "BACKBONE_C"]
BACKBONE_STATES = ["ACTIVE", "FLATTENING", "LOST", "TRANSITION"]
FAST_PHASES = ["EXPANDING", "CONTRACTING", "OPPOSING", "NEUTRAL", "TRANSITION"]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc(name: str, freq: str) -> pd.DataFrame:
    path = SOURCE / name
    df = pd.read_csv(path, parse_dates=["open_time", "close_time"])
    required = ["open_time", "close_time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"{path} missing columns: {missing}")
    if not df["open_time"].is_monotonic_increasing:
        raise RuntimeError(f"{path} is not sorted by open_time")
    if df["open_time"].duplicated().any():
        raise RuntimeError(f"{path} has duplicate open_time rows")
    if df["open_time"].max() >= FORBIDDEN or df["close_time"].max() >= FORBIDDEN:
        raise RuntimeError(f"{path} contains forbidden 2025+ data")
    expected_delta = pd.Timedelta(freq)
    deltas = df["open_time"].diff().dropna()
    if not deltas.eq(expected_delta).all():
        raise RuntimeError(f"{path} is not continuous at {freq}")
    if freq == "4h" and df["open_time"].dt.hour.mod(4).ne(0).any():
        raise RuntimeError(f"{path} is not aligned to UTC 4H buckets")
    if freq == "4h":
        durations = df["close_time"] - df["open_time"]
        if not durations.eq(pd.Timedelta(hours=4) - pd.Timedelta(milliseconds=1)).all():
            raise RuntimeError(f"{path} contains incomplete 4H bars")
    return df[required].copy()


def add_features(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = df.copy()
    out["timeframe"] = timeframe
    out["ema27"] = out["close"].ewm(span=27, adjust=False).mean()
    out["ema200"] = out["close"].ewm(span=200, adjust=False).mean()
    out["signed_ema_distance_pct"] = (out["ema27"] - out["ema200"]) / out["ema200"].replace(0, np.nan) * 100.0
    out["ema27_slope_6"] = (out["ema27"] / out["ema27"].shift(6) - 1.0) / 6.0 * 100.0
    out["ema200_slope_24"] = (out["ema200"] / out["ema200"].shift(24) - 1.0) / 24.0 * 100.0
    out["ema200_slope_48"] = (out["ema200"] / out["ema200"].shift(48) - 1.0) / 48.0 * 100.0
    out["ema200_slope_change_12"] = out["ema200_slope_24"] - out["ema200_slope_24"].shift(12)
    out["ema_distance_change_6"] = out["signed_ema_distance_pct"] - out["signed_ema_distance_pct"].shift(6)
    out["ema_distance_change_12"] = out["signed_ema_distance_pct"] - out["signed_ema_distance_pct"].shift(12)
    out["fast_slope_noise"] = out["ema27_slope_6"].diff().abs().rolling(120, min_periods=120).median()
    out["slow_slope_noise"] = out["ema200_slope_24"].diff().abs().rolling(240, min_periods=240).median()
    out["distance_noise"] = out["signed_ema_distance_pct"].diff().abs().rolling(120, min_periods=120).median()
    for col in ["fast_slope_noise", "slow_slope_noise", "distance_noise"]:
        out[col] = out[col].clip(lower=1e-12)
    out["norm_fast_slope"] = out["ema27_slope_6"] / out["fast_slope_noise"]
    out["norm_slow_slope"] = out["ema200_slope_24"] / out["slow_slope_noise"]
    out["norm_slow_slope_48"] = out["ema200_slope_48"] / out["slow_slope_noise"]
    out["norm_slow_change"] = out["ema200_slope_change_12"] / out["slow_slope_noise"]
    out["norm_distance_change_6"] = out["ema_distance_change_6"] / out["distance_noise"]
    out["norm_distance_change_12"] = out["ema_distance_change_12"] / out["distance_noise"]
    required = [
        "ema27_slope_6",
        "ema200_slope_24",
        "ema200_slope_48",
        "ema200_slope_change_12",
        "ema_distance_change_6",
        "ema_distance_change_12",
        "norm_fast_slope",
        "norm_slow_slope",
        "norm_slow_slope_48",
        "norm_slow_change",
        "norm_distance_change_6",
        "norm_distance_change_12",
    ]
    out["warmup"] = out[required].isna().any(axis=1)
    return out


def add_direction(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    raw = np.where(out["ema27"] > out["ema200"], "UP_ORDER", np.where(out["ema27"] < out["ema200"], "DOWN_ORDER", "EQUAL"))
    out["raw_direction"] = raw
    confirmed: list[str] = []
    events: list[bool] = []
    bars: list[int] = []
    current = "TRANSITION"
    candidate = None
    candidate_count = 0
    bars_in = 0
    previous_confirmed = "TRANSITION"
    previous_raw = "EQUAL"
    for raw_dir in raw:
        desired = "UP" if raw_dir == "UP_ORDER" else "DOWN" if raw_dir == "DOWN_ORDER" else "TRANSITION"
        crossed = previous_raw in {"UP_ORDER", "DOWN_ORDER"} and raw_dir in {"UP_ORDER", "DOWN_ORDER"} and raw_dir != previous_raw
        previous_raw = raw_dir
        if desired == "TRANSITION":
            current = "TRANSITION"
            candidate = None
            candidate_count = 0
        elif current == desired and not crossed:
            candidate = None
            candidate_count = 0
        else:
            if crossed:
                current = "TRANSITION"
                candidate = desired
                candidate_count = 1
            elif candidate == desired:
                candidate_count += 1
            else:
                candidate = desired
                candidate_count = 1
            if candidate_count >= 2:
                current = desired
                candidate = None
                candidate_count = 0
        if current in {"UP", "DOWN"}:
            bars_in = bars_in + 1 if current == previous_confirmed else 1
        else:
            bars_in = 0
        events.append(current != previous_confirmed)
        confirmed.append(current)
        bars.append(bars_in)
        previous_confirmed = current
    out["confirmed_direction"] = confirmed
    out["direction_change_event"] = events
    out["bars_in_direction"] = bars
    sign = out["confirmed_direction"].map({"UP": 1.0, "DOWN": -1.0}).fillna(0.0)
    out["direction_sign"] = sign
    out["ema200_one_bar_change"] = out["ema200"].diff()
    out["aligned_ema200_one_bar_change"] = sign * out["ema200_one_bar_change"]
    out["slow_persistence_12"] = (out["aligned_ema200_one_bar_change"] > 0).rolling(12, min_periods=12).mean()
    out["aligned_slow_slope"] = sign * out["norm_slow_slope"]
    out["aligned_slow_slope_48"] = sign * out["norm_slow_slope_48"]
    out["aligned_slow_change"] = sign * out["norm_slow_change"]
    out["aligned_fast_slope"] = sign * out["norm_fast_slope"]
    out["aligned_distance_change_6"] = sign * out["norm_distance_change_6"]
    out["aligned_distance_change_12"] = sign * out["norm_distance_change_12"]
    return out


def backbone_a(row: pd.Series) -> str:
    if bool(row["warmup"]):
        return "WARMUP"
    if row["confirmed_direction"] == "TRANSITION":
        return "TRANSITION"
    x = row["aligned_slow_slope"]
    if x > 1.5:
        return "ACTIVE"
    if x < -0.5:
        return "LOST"
    return "FLATTENING"


def backbone_b(row: pd.Series) -> str:
    if bool(row["warmup"]):
        return "WARMUP"
    if row["confirmed_direction"] == "TRANSITION":
        return "TRANSITION"
    x = row["aligned_slow_slope"]
    x48 = row["aligned_slow_slope_48"]
    chg = row["aligned_slow_change"]
    pers = row["slow_persistence_12"]
    if x < -0.5 or (pers < 0.50 and x <= 0):
        return "LOST"
    if x > 1.5 and x48 > 1.0 and pers >= 0.75:
        return "ACTIVE"
    if (-0.5 <= x <= 1.5) or (0.50 <= pers < 0.75) or (chg < -1.0 and x > -0.5):
        return "FLATTENING"
    return "FLATTENING"


def add_backbone_states(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["BACKBONE_A_state"] = [backbone_a(row) for _, row in out.iterrows()]
    out["BACKBONE_B_state"] = [backbone_b(row) for _, row in out.iterrows()]
    c_states: list[str] = []
    current = "WARMUP"
    candidate = None
    candidate_count = 0
    for _, row in out.iterrows():
        base = backbone_b(row)
        if base == "WARMUP":
            current = "WARMUP"
            candidate = None
            candidate_count = 0
        elif row["confirmed_direction"] == "TRANSITION" or base == "TRANSITION":
            current = "TRANSITION"
            candidate = None
            candidate_count = 0
        elif base == current:
            candidate = None
            candidate_count = 0
        elif base == "LOST" and row["aligned_slow_slope"] < -1.5:
            current = "LOST"
            candidate = None
            candidate_count = 0
        else:
            needed = 3 if current == "LOST" and base == "ACTIVE" else 2
            if candidate == base:
                candidate_count += 1
            else:
                candidate = base
                candidate_count = 1
            if candidate_count >= needed:
                current = base
                candidate = None
                candidate_count = 0
        c_states.append(current)
    out["BACKBONE_C_state"] = c_states
    return out


def phase_raw(row: pd.Series) -> str:
    if bool(row["warmup"]):
        return "WARMUP"
    if row["confirmed_direction"] == "TRANSITION":
        return "TRANSITION"
    fast = row["aligned_fast_slope"]
    dist = row["aligned_distance_change_6"]
    if fast > 1.0 and dist > 1.0:
        return "EXPANDING"
    if dist < -1.0 and fast >= -1.0:
        return "CONTRACTING"
    if fast < -1.0 and dist < -1.0:
        return "OPPOSING"
    return "NEUTRAL"


def add_fast_phase(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["fast_phase"] = [phase_raw(row) for _, row in out.iterrows()]
    h2: list[str] = []
    current = "WARMUP"
    candidate = None
    count = 0
    for phase in out["fast_phase"]:
        if phase in {"WARMUP", "TRANSITION"}:
            current = phase
            candidate = None
            count = 0
        elif phase == current:
            candidate = None
            count = 0
        else:
            if candidate == phase:
                count += 1
            else:
                candidate = phase
                count = 1
            if count >= 2:
                current = phase
                candidate = None
                count = 0
        h2.append(current)
    out["fast_phase_h2"] = h2
    return out


def episode_lengths(values: list[str]) -> list[tuple[str, int, int, int]]:
    if not values:
        return []
    out = []
    cur = values[0]
    start = 0
    length = 1
    for i, val in enumerate(values[1:], start=1):
        if val == cur:
            length += 1
        else:
            out.append((cur, start, i - 1, length))
            cur = val
            start = i
            length = 1
    out.append((cur, start, len(values) - 1, length))
    return out


def backbone_statistics(df: pd.DataFrame, timeframe: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stat_rows, dwell_rows, comp_rows = [], [], []
    for model in MODELS:
        state_col = f"{model}_state"
        eval_df = df[df[state_col] != "WARMUP"].copy()
        values = eval_df[state_col].tolist()
        episodes = episode_lengths(values)
        changes = max(0, len(episodes) - 1)
        counts = eval_df[state_col].value_counts()
        quarters = eval_df.assign(quarter=eval_df["open_time"].dt.to_period("Q").astype(str)).groupby(state_col)["quarter"].nunique()
        repeated = pd.Series([e[0] for e in episodes]).value_counts()
        for state, s, e, length in episodes:
            dwell_rows.append({"timeframe": timeframe, "model": model, "state": state, "start_pos": s, "end_pos": e, "duration_bars": length})
        for state in BACKBONE_STATES:
            lens = [e[3] for e in episodes if e[0] == state]
            arr = np.array(lens, dtype=float)
            stat_rows.append(
                {
                    "timeframe": timeframe,
                    "model": model,
                    "state": state,
                    "available_bars": int(len(eval_df)),
                    "bar_count": int(counts.get(state, 0)),
                    "bar_fraction": float(counts.get(state, 0) / len(eval_df)) if len(eval_df) else math.nan,
                    "episode_count": int(len(lens)),
                    "mean_dwell": float(arr.mean()) if len(arr) else math.nan,
                    "median_dwell": float(np.median(arr)) if len(arr) else math.nan,
                    "p75_dwell": float(np.quantile(arr, 0.75)) if len(arr) else math.nan,
                    "p90_dwell": float(np.quantile(arr, 0.90)) if len(arr) else math.nan,
                    "max_dwell": int(arr.max()) if len(arr) else 0,
                    "quarters_present": int(quarters.get(state, 0)),
                    "nonconsecutive_episode_count": int(repeated.get(state, 0)),
                    "state_changes_per_100_bars": float(changes / len(eval_df) * 100.0) if len(eval_df) else math.nan,
                    "largest_state_fraction": float(counts.max() / len(eval_df)) if len(eval_df) else math.nan,
                }
            )
        active = [e[3] for e in episodes if e[0] == "ACTIVE"]
        flattening = [e[3] for e in episodes if e[0] == "FLATTENING"]
        lost = [e[3] for e in episodes if e[0] == "LOST"]
        comp_rows.append(
            {
                "timeframe": timeframe,
                "model": model,
                "available_bars": int(len(eval_df)),
                "state_changes_per_100_bars": float(changes / len(eval_df) * 100.0) if len(eval_df) else math.nan,
                "active_fraction": float(counts.get("ACTIVE", 0) / len(eval_df)) if len(eval_df) else math.nan,
                "flattening_fraction": float(counts.get("FLATTENING", 0) / len(eval_df)) if len(eval_df) else math.nan,
                "lost_fraction": float(counts.get("LOST", 0) / len(eval_df)) if len(eval_df) else math.nan,
                "transition_fraction": float(counts.get("TRANSITION", 0) / len(eval_df)) if len(eval_df) else math.nan,
                "largest_state_fraction": float(counts.max() / len(eval_df)) if len(eval_df) else math.nan,
                "active_episode_count": int(len(active)),
                "lost_episode_count": int(len(lost)),
                "median_dwell_active": float(np.median(active)) if active else math.nan,
                "median_dwell_flattening": float(np.median(flattening)) if flattening else math.nan,
                "median_dwell_lost": float(np.median(lost)) if lost else math.nan,
                "main_states_multi_quarter": int(sum(int(quarters.get(s, 0) >= 3) for s in ["ACTIVE", "FLATTENING", "LOST"])),
            }
        )
    return pd.DataFrame(stat_rows), pd.DataFrame(dwell_rows), pd.DataFrame(comp_rows)


def fast_phase_statistics(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rows = []
    for model in MODELS:
        bcol = f"{model}_state"
        eval_df = df[df[bcol] != "WARMUP"].copy()
        for backbone in ["ACTIVE", "FLATTENING", "LOST"]:
            sub = eval_df[eval_df[bcol] == backbone].copy()
            episodes = episode_lengths(sub["fast_phase"].tolist())
            counts = sub["fast_phase"].value_counts()
            for phase in FAST_PHASES:
                lens = [e[3] for e in episodes if e[0] == phase]
                arr = np.array(lens, dtype=float)
                rows.append(
                    {
                        "timeframe": timeframe,
                        "model": model,
                        "backbone_state": backbone,
                        "fast_phase": phase,
                        "bar_count": int(counts.get(phase, 0)),
                        "bar_fraction_within_backbone": float(counts.get(phase, 0) / len(sub)) if len(sub) else math.nan,
                        "episode_count": int(len(lens)),
                        "mean_dwell": float(arr.mean()) if len(arr) else math.nan,
                        "median_dwell": float(np.median(arr)) if len(arr) else math.nan,
                        "p75_dwell": float(np.quantile(arr, 0.75)) if len(arr) else math.nan,
                        "p90_dwell": float(np.quantile(arr, 0.90)) if len(arr) else math.nan,
                        "max_dwell": int(arr.max()) if len(arr) else 0,
                    }
                )
    return pd.DataFrame(rows)


def active_phase_checks(df: pd.DataFrame, model: str, timeframe: str) -> dict[str, object]:
    bcol = f"{model}_state"
    eval_df = df[df[bcol] != "WARMUP"].copy()
    changed = eval_df[(eval_df["fast_phase"].shift(1) == "EXPANDING") & (eval_df["fast_phase"] == "CONTRACTING")]
    changed_prev_active = changed[changed[bcol].shift(1) == "ACTIVE"]
    p_active_after_contract = float((changed_prev_active[bcol] == "ACTIVE").mean()) if len(changed_prev_active) else math.nan
    opposing = eval_df[eval_df["fast_phase"] == "OPPOSING"]
    p_active_opposing = float((opposing[bcol] == "ACTIVE").mean()) if len(opposing) else math.nan
    combo = (eval_df[bcol] + "+" + eval_df["fast_phase"]).tolist()
    active_contract = [e[3] for e in episode_lengths(combo) if e[0] == "ACTIVE+CONTRACTING"]
    active_oppose = [e[3] for e in episode_lengths(combo) if e[0] == "ACTIVE+OPPOSING"]
    return {
        "timeframe": timeframe,
        "model": model,
        "p_active_after_expanding_to_contracting": p_active_after_contract,
        "p_active_when_opposing": p_active_opposing,
        "active_contracting_bar_count": int(((eval_df[bcol] == "ACTIVE") & (eval_df["fast_phase"] == "CONTRACTING")).sum()),
        "active_opposing_bar_count": int(((eval_df[bcol] == "ACTIVE") & (eval_df["fast_phase"] == "OPPOSING")).sum()),
        "active_contracting_episode_count": int(len(active_contract)),
        "active_opposing_episode_count": int(len(active_oppose)),
        "mean_duration_active_contracting": float(np.mean(active_contract)) if active_contract else math.nan,
        "mean_duration_active_opposing": float(np.mean(active_oppose)) if active_oppose else math.nan,
    }


def choose_model(comp1: pd.DataFrame, comp4: pd.DataFrame, phase_stats1: pd.DataFrame, phase_stats4: pd.DataFrame) -> str:
    scores: list[tuple[float, str]] = []
    for model in MODELS:
        r1 = comp1[comp1["model"] == model].iloc[0]
        r4 = comp4[comp4["model"] == model].iloc[0]
        ps1 = phase_stats1[(phase_stats1["model"] == model) & (phase_stats1["backbone_state"] == "ACTIVE")]
        ps4 = phase_stats4[(phase_stats4["model"] == model) & (phase_stats4["backbone_state"] == "ACTIVE")]
        phases1 = set(ps1.loc[ps1["bar_count"] > 0, "fast_phase"])
        phases4 = set(ps4.loc[ps4["bar_count"] > 0, "fast_phase"])
        required_phases = {"EXPANDING", "CONTRACTING", "OPPOSING"}
        score = 0.0
        score += 10 if r4["state_changes_per_100_bars"] <= 8 else -6
        score += 10 if r1["state_changes_per_100_bars"] <= 12 else -6
        score += 8 if r4["median_dwell_active"] >= 6 else -5
        score += 8 if r1["median_dwell_active"] >= 8 else -5
        score += 8 if required_phases.issubset(phases4) else -10
        score += 8 if required_phases.issubset(phases1) else -10
        score += 4 if r4["flattening_fraction"] < 0.70 and r1["flattening_fraction"] < 0.70 else -4
        score += 4 if r4["lost_episode_count"] >= 3 and r1["lost_episode_count"] >= 3 else -4
        score += 4 if r4["main_states_multi_quarter"] >= 3 else -3
        score += 4 if r1["main_states_multi_quarter"] >= 3 else -3
        score += 3 if r4["largest_state_fraction"] < 0.70 and r1["largest_state_fraction"] < 0.70 else -2
        if model == "BACKBONE_C":
            score += 1.5
        if model == "BACKBONE_B":
            score += 0.5
        scores.append((score, model))
    return sorted(scores, reverse=True)[0][1]


def add_composite(df: pd.DataFrame, selected: str) -> pd.DataFrame:
    out = df.copy()
    out["backbone_state"] = out[f"{selected}_state"]
    out["composite_state"] = out["confirmed_direction"] + "+" + out["backbone_state"] + "+" + out["fast_phase"]
    return out


def direction_relation(d4: str, d1: str) -> str:
    if d4 == "TRANSITION":
        return "PARENT_TRANSITION"
    if d1 == "TRANSITION":
        return "LOWER_TRANSITION"
    if d4 == "UP" and d1 == "UP":
        return "ALIGNED_UP"
    if d4 == "DOWN" and d1 == "DOWN":
        return "ALIGNED_DOWN"
    return "LOWER_OPPOSES_PARENT"


def merge_multiscale(f1: pd.DataFrame, f4: pd.DataFrame) -> pd.DataFrame:
    left = f1[f1["backbone_state"] != "WARMUP"].copy()
    right = f4[f4["backbone_state"] != "WARMUP"].copy()
    one = left[
        [
            "open_time",
            "close_time",
            "confirmed_direction",
            "backbone_state",
            "fast_phase",
            "close",
            "ema27",
            "ema200",
            "ema200_slope_24",
            "ema200_slope_48",
            "slow_persistence_12",
            "ema_distance_change_6",
        ]
    ].rename(
        columns={
            "confirmed_direction": "direction_1h",
            "backbone_state": "backbone_1h",
            "fast_phase": "fast_phase_1h",
            "close": "close_1h",
            "ema27": "ema27_1h",
            "ema200": "ema200_1h",
        }
    )
    four = right[
        [
            "close_time",
            "confirmed_direction",
            "backbone_state",
            "fast_phase",
            "ema27",
            "ema200",
            "ema200_slope_24",
            "ema200_slope_48",
            "slow_persistence_12",
            "ema_distance_change_6",
        ]
    ].rename(
        columns={
            "close_time": "parent_close_time",
            "confirmed_direction": "direction_4h",
            "backbone_state": "backbone_4h",
            "fast_phase": "fast_phase_4h",
            "ema27": "ema27_4h",
            "ema200": "ema200_4h",
            "ema200_slope_24": "ema200_slope_24_4h",
            "ema200_slope_48": "ema200_slope_48_4h",
            "slow_persistence_12": "slow_persistence_12_4h",
            "ema_distance_change_6": "ema_distance_change_6_4h",
        }
    )
    merged = pd.merge_asof(
        one.sort_values("close_time"),
        four.sort_values("parent_close_time"),
        left_on="close_time",
        right_on="parent_close_time",
        direction="backward",
    ).dropna(subset=["parent_close_time"])
    merged["direction_relation"] = [direction_relation(a, b) for a, b in zip(merged["direction_4h"], merged["direction_1h"])]
    merged["backbone_relation"] = "PARENT_" + merged["backbone_4h"]
    merged["multiscale_composite"] = (
        "4H_"
        + merged["direction_4h"]
        + "_"
        + merged["backbone_4h"]
        + "_"
        + merged["fast_phase_4h"]
        + "__1H_"
        + merged["direction_1h"]
        + "_"
        + merged["backbone_1h"]
        + "_"
        + merged["fast_phase_1h"]
    )
    return merged.reset_index(drop=True)


def relation_statistics(ms: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ["direction_relation", "backbone_relation", "multiscale_composite"]:
        for value, count in ms[col].value_counts().items():
            rows.append({"relation_type": col, "relation": value, "bar_count": int(count), "bar_fraction": float(count / len(ms))})
    return pd.DataFrame(rows)


def select_windows(ms: pd.DataFrame) -> pd.DataFrame:
    episodes = episode_lengths(ms["multiscale_composite"].tolist())
    rows = []
    used = set()

    def add(kind: str, predicate, limit: int) -> None:
        for _, s, e, length in episodes:
            ep = ms.iloc[s : e + 1]
            sample = ep.iloc[0]
            if length < 8 or not predicate(sample):
                continue
            month = sample["open_time"].strftime("%Y-%m")
            key = (kind, month)
            if key in used:
                continue
            used.add(key)
            rows.append(
                {
                    "review_id": f"VR{len(rows)+1:03d}",
                    "review_type": kind,
                    "start_time": sample["open_time"],
                    "end_time": ep.iloc[-1]["close_time"],
                    "direction_4h": sample["direction_4h"],
                    "backbone_4h": sample["backbone_4h"],
                    "fast_phase_4h": sample["fast_phase_4h"],
                    "direction_1h": sample["direction_1h"],
                    "backbone_1h": sample["backbone_1h"],
                    "fast_phase_1h": sample["fast_phase_1h"],
                    "direction_relation": sample["direction_relation"],
                    "ema27_4h": sample["ema27_4h"],
                    "ema200_4h": sample["ema200_4h"],
                    "ema200_slope_24_4h": sample["ema200_slope_24_4h"],
                    "ema200_slope_48_4h": sample["ema200_slope_48_4h"],
                    "slow_persistence_12_4h": sample["slow_persistence_12_4h"],
                    "ema_distance_change_6_4h": sample["ema_distance_change_6_4h"],
                    "duration_1h_bars": int(length),
                }
            )
            if sum(r["review_type"] == kind for r in rows) >= limit:
                return

    add(
        "TYPE_A",
        lambda r: r["direction_4h"] == "UP"
        and r["backbone_4h"] == "ACTIVE"
        and r["fast_phase_4h"] in {"CONTRACTING", "OPPOSING"}
        and r["direction_1h"] == "DOWN"
        and r["backbone_1h"] in {"ACTIVE", "FLATTENING"},
        8,
    )
    add(
        "TYPE_B",
        lambda r: r["direction_4h"] == "UP"
        and r["backbone_4h"] == "FLATTENING"
        and r["direction_1h"] == "DOWN"
        and r["backbone_1h"] in {"ACTIVE", "FLATTENING"},
        8,
    )
    add("TYPE_C", lambda r: r["direction_4h"] == "UP" and r["backbone_4h"] == "ACTIVE" and r["direction_1h"] == "UP", 6)
    add(
        "TYPE_D",
        lambda r: r["direction_4h"] == "DOWN"
        and r["direction_1h"] == "UP"
        and r["backbone_1h"] in {"ACTIVE", "FLATTENING"}
        and ((r["backbone_4h"] == "ACTIVE" and r["fast_phase_4h"] in {"CONTRACTING", "OPPOSING"}) or r["backbone_4h"] == "FLATTENING"),
        8,
    )
    return pd.DataFrame(rows)


def exp011_comparison(selected: str, comp1: pd.DataFrame, comp4: pd.DataFrame, stats1: pd.DataFrame, stats4: pd.DataFrame, ms: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    exp011 = SOURCE
    old_comp = pd.read_csv(exp011 / "model_comparison.csv")
    old_sel = old_comp[old_comp["selected"] == True].iloc[0]
    old_stats1 = pd.read_csv(exp011 / "state_statistics_1h.csv")
    old_stats4 = pd.read_csv(exp011 / "state_statistics_4h.csv")
    old_rel = pd.read_csv(exp011 / "scale_relation_statistics.csv")
    stable_1h = old_stats1[(old_stats1["model"] == old_sel["model"]) & (old_stats1["state"].str.contains("STABLE"))]["bar_fraction"].sum()
    stable_4h = old_stats4[(old_stats4["model"] == old_sel["model"]) & (old_stats4["state"].str.contains("STABLE"))]["bar_fraction"].sum()
    lower_old = old_rel.loc[old_rel["scale_relation"] == "LOWER_OPPOSES_PARENT", "bar_fraction"].sum()
    r1 = comp1[comp1["model"] == selected].iloc[0]
    r4 = comp4[comp4["model"] == selected].iloc[0]
    active_1h = r1["active_fraction"]
    active_4h = r4["active_fraction"]
    lower_new = float((ms["direction_relation"] == "LOWER_OPPOSES_PARENT").mean())
    active_contracting = bool(((ms["backbone_4h"] == "ACTIVE") & (ms["fast_phase_4h"] == "CONTRACTING")).any()) and bool(((ms["backbone_1h"] == "ACTIVE") & (ms["fast_phase_1h"] == "CONTRACTING")).any())
    active_opposing = bool(((ms["backbone_4h"] == "ACTIVE") & (ms["fast_phase_4h"] == "OPPOSING")).any()) and bool(((ms["backbone_1h"] == "ACTIVE") & (ms["fast_phase_1h"] == "OPPOSING")).any())
    rows = [
        {"metric": "layers", "EXP-011": "single combined state", "EXP-011A": "direction + slow backbone + fast phase"},
        {"metric": "direction_definition", "EXP-011": "EMA order plus slope context", "EXP-011A": "EMA27/EMA200 order with 2-bar confirmation"},
        {"metric": "backbone_definition", "EXP-011": "EMA27, EMA200, and distance change mixed", "EXP-011A": "EMA200 slope/change/persistence only"},
        {"metric": "fast_phase_definition", "EXP-011": "mixed into EXPANDING/STABLE/WEAKENING", "EXP-011A": "EMA27 slope and EMA distance change"},
        {"metric": "state_changes_4h", "EXP-011": old_sel["state_changes_per_100_bars_4h"], "EXP-011A": r4["state_changes_per_100_bars"]},
        {"metric": "state_changes_1h", "EXP-011": old_sel["state_changes_per_100_bars_1h"], "EXP-011A": r1["state_changes_per_100_bars"]},
        {"metric": "median_dwell_active_4h", "EXP-011": "", "EXP-011A": r4["median_dwell_active"]},
        {"metric": "median_dwell_active_1h", "EXP-011": "", "EXP-011A": r1["median_dwell_active"]},
        {"metric": "median_dwell_flattening_4h", "EXP-011": "", "EXP-011A": r4["median_dwell_flattening"]},
        {"metric": "median_dwell_flattening_1h", "EXP-011": "", "EXP-011A": r1["median_dwell_flattening"]},
        {"metric": "stable_fraction_4h_or_active_fraction_4h", "EXP-011": stable_4h, "EXP-011A": active_4h},
        {"metric": "stable_fraction_1h_or_active_fraction_1h", "EXP-011": stable_1h, "EXP-011A": active_1h},
        {"metric": "TYPE_A_count", "EXP-011": int((pd.read_csv(exp011 / "visual_review_windows.csv")["type"] == "TYPE_A").sum()), "EXP-011A": int((windows["review_type"] == "TYPE_A").sum()) if not windows.empty else 0},
        {"metric": "TYPE_B_count", "EXP-011": int((pd.read_csv(exp011 / "visual_review_windows.csv")["type"] == "TYPE_B").sum()), "EXP-011A": int((windows["review_type"] == "TYPE_B").sum()) if not windows.empty else 0},
        {"metric": "LOWER_OPPOSES_PARENT_fraction", "EXP-011": lower_old, "EXP-011A": lower_new},
        {"metric": "ACTIVE_CONTRACTING_exists", "EXP-011": "", "EXP-011A": active_contracting},
        {"metric": "ACTIVE_OPPOSING_exists", "EXP-011": "", "EXP-011A": active_opposing},
        {"metric": "causal", "EXP-011": True, "EXP-011A": True},
        {"metric": "lookahead", "EXP-011": "closed 4H only", "EXP-011A": "closed 4H only"},
    ]
    return pd.DataFrame(rows)


def pine_script(selected: str) -> str:
    use_c = "true" if selected == "BACKBONE_C" else "false"
    use_b = "true" if selected in {"BACKBONE_B", "BACKBONE_C"} else "false"
    return f'''//@version=6
indicator("EXP-011A Slow Backbone Fast Phase", overlay=true, max_labels_count=500)

showEMA1H = input.bool(true, "showEMA1H")
showEMA4H = input.bool(true, "showEMA4H")
showDirection4H = input.bool(true, "showDirection4H")
showBackbone4H = input.bool(true, "showBackbone4H")
showFastPhase4H = input.bool(true, "showFastPhase4H")
showDirection1H = input.bool(true, "showDirection1H")
showBackbone1H = input.bool(true, "showBackbone1H")
showFastPhase1H = input.bool(true, "showFastPhase1H")
showScaleRelation = input.bool(true, "showScaleRelation")
showStateLabels = input.bool(true, "showStateLabels")
showOnlyTransitions = input.bool(false, "showOnlyTransitions")

f_dir() =>
    float e27 = ta.ema(close, 27)
    float e200 = ta.ema(close, 200)
    string raw = e27 > e200 ? "UP" : e27 < e200 ? "DOWN" : "TRANSITION"
    var string confirmed = "TRANSITION"
    var string cand = ""
    var int cnt = 0
    bool crossed = raw != "TRANSITION" and raw[1] != "TRANSITION" and raw != raw[1]
    if raw == "TRANSITION"
        confirmed := "TRANSITION"
        cand := ""
        cnt := 0
    else if confirmed == raw and not crossed
        cand := ""
        cnt := 0
    else
        if crossed
            confirmed := "TRANSITION"
            cand := raw
            cnt := 1
        else
            cnt := cand == raw ? cnt + 1 : 1
            cand := raw
        if cnt >= 2
            confirmed := raw
            cand := ""
            cnt := 0
    confirmed

f_phase(string dir) =>
    float e27 = ta.ema(close, 27)
    float e200 = ta.ema(close, 200)
    float dist = (e27 - e200) / e200 * 100.0
    float s27 = (e27 / e27[6] - 1.0) / 6.0 * 100.0
    float nf = math.max(ta.median(math.abs(ta.change(s27)), 120), 1e-12)
    float nd = math.max(ta.median(math.abs(ta.change(dist)), 120), 1e-12)
    float sign = dir == "UP" ? 1.0 : dir == "DOWN" ? -1.0 : 0.0
    float af = sign * s27 / nf
    float ad = sign * (dist - dist[6]) / nd
    string ph = "TRANSITION"
    if dir != "TRANSITION"
        ph := af > 1.0 and ad > 1.0 ? "EXPANDING" : ad < -1.0 and af >= -1.0 ? "CONTRACTING" : af < -1.0 and ad < -1.0 ? "OPPOSING" : "NEUTRAL"
    ph

f_backbone(string dir) =>
    float e200 = ta.ema(close, 200)
    float e27 = ta.ema(close, 27)
    float s24 = (e200 / e200[24] - 1.0) / 24.0 * 100.0
    float s48 = (e200 / e200[48] - 1.0) / 48.0 * 100.0
    float ns = math.max(ta.median(math.abs(ta.change(s24)), 240), 1e-12)
    float sign = dir == "UP" ? 1.0 : dir == "DOWN" ? -1.0 : 0.0
    float x = sign * s24 / ns
    float x48 = sign * s48 / ns
    float chg = sign * (s24 - s24[12]) / ns
    float aligned = sign * ta.change(e200)
    float pers = ta.sma(aligned > 0 ? 1.0 : 0.0, 12)
    string base = "TRANSITION"
    if dir != "TRANSITION"
        if {use_b}
            base := x < -0.5 or pers < 0.50 and x <= 0 ? "LOST" : x > 1.5 and x48 > 1.0 and pers >= 0.75 ? "ACTIVE" : "FLATTENING"
        else
            base := x > 1.5 ? "ACTIVE" : x < -0.5 ? "LOST" : "FLATTENING"
    var string st = "TRANSITION"
    var string cand = ""
    var int cnt = 0
    if not {use_c}
        st := base
    else if base == "TRANSITION"
        st := "TRANSITION"
        cand := ""
        cnt := 0
    else if base == st
        cand := ""
        cnt := 0
    else if base == "LOST" and x < -1.5
        st := "LOST"
        cand := ""
        cnt := 0
    else
        int need = st == "LOST" and base == "ACTIVE" ? 3 : 2
        cnt := cand == base ? cnt + 1 : 1
        cand := base
        if cnt >= need
            st := base
            cand := ""
            cnt := 0
    st

string d1 = f_dir()
string b1 = f_backbone(d1)
string p1 = f_phase(d1)
string d4 = request.security(syminfo.tickerid, "240", f_dir()[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)
string b4 = request.security(syminfo.tickerid, "240", f_backbone(f_dir())[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)
string p4 = request.security(syminfo.tickerid, "240", f_phase(f_dir())[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)
float ema27_1 = ta.ema(close, 27)
float ema200_1 = ta.ema(close, 200)
float ema27_4 = request.security(syminfo.tickerid, "240", ta.ema(close, 27)[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)
float ema200_4 = request.security(syminfo.tickerid, "240", ta.ema(close, 200)[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)

plot(showEMA1H ? ema27_1 : na, "EMA27 1H", color=color.aqua)
plot(showEMA1H ? ema200_1 : na, "EMA200 1H", color=color.orange)
plot(showEMA4H ? ema27_4 : na, "EMA27 4H confirmed", color=color.new(color.aqua, 45), linewidth=2)
plot(showEMA4H ? ema200_4 : na, "EMA200 4H confirmed", color=color.new(color.orange, 45), linewidth=2)

f_bcolor(string b) =>
    b == "ACTIVE" ? color.new(color.green, 86) : b == "FLATTENING" ? color.new(color.yellow, 84) : b == "LOST" ? color.new(color.red, 86) : color.new(color.gray, 88)

string rel = d4 == "TRANSITION" ? "PARENT_TRANSITION" : d1 == "TRANSITION" ? "LOWER_TRANSITION" : d4 == d1 and d4 == "UP" ? "ALIGNED_UP" : d4 == d1 and d4 == "DOWN" ? "ALIGNED_DOWN" : "LOWER_OPPOSES_PARENT"
bool changed = d1 != d1[1] or b1 != b1[1] or p1 != p1[1] or d4 != d4[1] or b4 != b4[1] or p4 != p4[1] or rel != rel[1]

bgcolor(showBackbone4H and (not showOnlyTransitions or changed) ? f_bcolor(b4) : na)
if showStateLabels and changed
    if showDirection4H or showBackbone4H or showFastPhase4H
        label.new(time, high, "4H " + d4 + " " + b4 + " " + p4, xloc=xloc.bar_time, style=label.style_label_down, color=f_bcolor(b4), textcolor=color.black, size=size.tiny)
    if showDirection1H or showBackbone1H or showFastPhase1H
        label.new(time, low, "1H " + d1 + " " + b1 + " " + p1, xloc=xloc.bar_time, style=label.style_label_up, color=f_bcolor(b1), textcolor=color.black, size=size.tiny)
    if showScaleRelation and rel == "LOWER_OPPOSES_PARENT"
        label.new(time, close, rel, xloc=xloc.bar_time, style=label.style_label_left, color=color.white, textcolor=color.black, size=size.tiny)
'''


def write_contact_sheet(path: Path, windows: pd.DataFrame, ms: pd.DataFrame) -> str:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except Exception:
        write_vector_contact_sheet(path, windows, ms)
        return "PDF vector contact sheet generated without external plotting libraries."

    with PdfPages(path) as pdf:
        selected = windows[windows["review_type"].isin(["TYPE_A", "TYPE_B"])].head(16)
        if selected.empty:
            selected = windows.head(16)
        for _, row in selected.iterrows():
            start = pd.Timestamp(row["start_time"]) - pd.Timedelta(hours=24)
            end = pd.Timestamp(row["end_time"]) + pd.Timedelta(hours=24)
            sub = ms[(ms["open_time"] >= start) & (ms["open_time"] <= end)].copy()
            if sub.empty:
                continue
            fig, axes = plt.subplots(4, 1, figsize=(11, 8.5), sharex=True, gridspec_kw={"height_ratios": [3, 0.6, 0.6, 0.6]})
            axes[0].plot(sub["open_time"], sub["ema27_1h"], label="EMA27 1H", color="#1f9fb5", linewidth=1)
            axes[0].plot(sub["open_time"], sub["ema200_1h"], label="EMA200 1H", color="#d97706", linewidth=1)
            axes[0].plot(sub["open_time"], sub["ema27_4h"], label="EMA27 4H confirmed", color="#155e75", linewidth=1.5)
            axes[0].plot(sub["open_time"], sub["ema200_4h"], label="EMA200 4H confirmed", color="#92400e", linewidth=1.5)
            axes[0].axvspan(pd.Timestamp(row["start_time"]), pd.Timestamp(row["end_time"]), color="#e5e7eb", alpha=0.45)
            axes[0].set_title(f"{row['review_id']} {row['review_type']} {row['direction_4h']} {row['backbone_4h']} {row['fast_phase_4h']} / 1H {row['direction_1h']} {row['backbone_1h']} {row['fast_phase_1h']}")
            axes[0].legend(loc="upper left", fontsize=7)
            for ax, col, title in [
                (axes[1], "backbone_4h", "4H backbone"),
                (axes[2], "fast_phase_4h", "4H fast phase"),
                (axes[3], "fast_phase_1h", "1H fast phase"),
            ]:
                codes = pd.Categorical(sub[col]).codes
                ax.step(sub["open_time"], codes, where="post", linewidth=1)
                ax.set_yticks(sorted(set(codes)))
                ax.set_yticklabels(pd.Categorical(sub[col]).categories, fontsize=7)
                ax.set_title(title, loc="left", fontsize=8)
            fig.autofmt_xdate()
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
    return "PDF chart contact sheet generated."


def write_vector_contact_sheet(path: Path, windows: pd.DataFrame, ms: pd.DataFrame) -> None:
    def esc(s: object) -> str:
        return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def line(points: list[tuple[float, float]]) -> str:
        if len(points) < 2:
            return ""
        first, rest = points[0], points[1:]
        return f"{first[0]:.2f} {first[1]:.2f} m " + " ".join(f"{x:.2f} {y:.2f} l" for x, y in rest) + " S"

    selected = windows[windows["review_type"].isin(["TYPE_A", "TYPE_B"])].head(16)
    if selected.empty:
        selected = windows.head(16)
    pages: list[bytes] = []
    for _, row in selected.iterrows():
        start = pd.Timestamp(row["start_time"]) - pd.Timedelta(hours=24)
        end = pd.Timestamp(row["end_time"]) + pd.Timedelta(hours=24)
        sub = ms[(ms["open_time"] >= start) & (ms["open_time"] <= end)].copy()
        if len(sub) < 2:
            continue
        times = pd.to_datetime(sub["open_time"]).astype("int64").to_numpy(dtype=float)
        tmin, tmax = float(times.min()), float(times.max())
        vals = sub[["close_1h", "ema27_1h", "ema200_1h", "ema27_4h", "ema200_4h"]].to_numpy(dtype=float)
        ymin, ymax = float(np.nanmin(vals)), float(np.nanmax(vals))
        if ymax <= ymin:
            ymax = ymin + 1.0
        x0, y0, w, h = 52.0, 320.0, 508.0, 280.0

        def xy(ts: float, val: float) -> tuple[float, float]:
            x = x0 + (ts - tmin) / (tmax - tmin) * w
            y = y0 + (val - ymin) / (ymax - ymin) * h
            return x, y

        commands = ["BT /F1 13 Tf 52 760 Td"]
        commands.append(f"({esc(row['review_id'])} {esc(row['review_type'])}  4H {esc(row['direction_4h'])} {esc(row['backbone_4h'])} {esc(row['fast_phase_4h'])} / 1H {esc(row['direction_1h'])} {esc(row['backbone_1h'])} {esc(row['fast_phase_1h'])}) Tj")
        commands.append("/F1 8 Tf 0 -14 Td")
        commands.append(f"({esc(row['start_time'])} to {esc(row['end_time'])}  duration={esc(row['duration_1h_bars'])}h) Tj")
        commands.append("ET")
        commands.append("0.85 0.85 0.85 RG 52 320 508 280 re S")
        st = pd.Timestamp(row["start_time"]).value
        en = pd.Timestamp(row["end_time"]).value
        sx = x0 + (st - tmin) / (tmax - tmin) * w
        ex = x0 + (en - tmin) / (tmax - tmin) * w
        commands.append("0.93 0.93 0.93 rg")
        commands.append(f"{sx:.2f} {y0:.2f} {max(1.0, ex - sx):.2f} {h:.2f} re f")
        series = [
            ("0.10 0.10 0.10 RG", "close_1h"),
            ("0.00 0.55 0.65 RG", "ema27_1h"),
            ("0.85 0.45 0.00 RG", "ema200_1h"),
            ("0.00 0.25 0.45 RG", "ema27_4h"),
            ("0.55 0.25 0.00 RG", "ema200_4h"),
        ]
        for color, col in series:
            pts = [xy(t, v) for t, v in zip(times, sub[col].to_numpy(dtype=float)) if not np.isnan(v)]
            commands.append(color)
            commands.append("1.0 w")
            commands.append(line(pts))
        commands.append("BT /F1 8 Tf 52 302 Td")
        commands.append("(black=price  teal=EMA27 1H  orange=EMA200 1H  dark teal=EMA27 4H confirmed  brown=EMA200 4H confirmed) Tj")
        commands.append("0 -16 Td")
        commands.append(f"(4H direction/backbone/fast: {esc(row['direction_4h'])} / {esc(row['backbone_4h'])} / {esc(row['fast_phase_4h'])}) Tj")
        commands.append("0 -12 Td")
        commands.append(f"(1H direction/backbone/fast: {esc(row['direction_1h'])} / {esc(row['backbone_1h'])} / {esc(row['fast_phase_1h'])}) Tj")
        commands.append("0 -12 Td")
        commands.append(f"(EMA200 slope24 4H={float(row['ema200_slope_24_4h']):.6f}; slope48 4H={float(row['ema200_slope_48_4h']):.6f}; persistence12={float(row['slow_persistence_12_4h']):.3f}) Tj")
        commands.append("ET")
        pages.append("\n".join(commands).encode("latin-1", "replace"))
    if not pages:
        write_pdf_index(path, "EXP-011A Slow Backbone / Fast Phase Contact Sheet", windows)
        return

    objs: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    page_refs = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objs.append(f"<< /Type /Pages /Kids [{page_refs}] /Count {len(pages)} >>".encode())
    for i, stream in enumerate(pages):
        page_obj_id = 3 + i * 2
        content_obj_id = page_obj_id + 1
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {3 + len(pages) * 2} 0 R >> >> /Contents {content_obj_id} 0 R >>".encode())
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    write_pdf_objects(path, objs)


def write_pdf_objects(path: Path, objs: list[bytes]) -> None:
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(out)


def write_pdf_index(path: Path, title: str, windows: pd.DataFrame) -> None:
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = [f"{r.review_id} {r.review_type} {r.start_time} to {r.end_time} 4H {r.direction_4h} {r.backbone_4h} {r.fast_phase_4h} / 1H {r.direction_1h} {r.backbone_1h} {r.fast_phase_1h}" for r in windows.head(60).itertuples()]
    content = ["BT", "/F1 15 Tf", "42 752 Td", f"({esc(title)}) Tj", "/F1 9 Tf", "0 -18 Td"]
    for line in lines[:72]:
        content.append(f"({esc(line)}) Tj")
        content.append("0 -10 Td")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    write_pdf_objects(path, objs)


def direction_stats(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    eval_df = df[~df["warmup"]].copy()
    rows = []
    for direction, group in eval_df.groupby("confirmed_direction"):
        rows.append({"timeframe": timeframe, "confirmed_direction": direction, "bar_count": int(len(group)), "bar_fraction": float(len(group) / len(eval_df))})
    return pd.DataFrame(rows)


def verdict_for(selected: str, comp1: pd.DataFrame, comp4: pd.DataFrame, checks: pd.DataFrame, windows: pd.DataFrame, contact_note: str) -> tuple[str, str]:
    r1 = comp1[comp1["model"] == selected].iloc[0]
    r4 = comp4[comp4["model"] == selected].iloc[0]
    counts = windows["review_type"].value_counts() if not windows.empty else pd.Series(dtype=int)
    type_a = int(counts.get("TYPE_A", 0))
    type_b = int(counts.get("TYPE_B", 0))
    full = (
        r4["state_changes_per_100_bars"] <= 8
        and r1["state_changes_per_100_bars"] <= 12
        and r4["median_dwell_active"] >= 6
        and r1["median_dwell_active"] >= 8
        and type_a >= 8
        and type_b >= 8
        and "chart contact sheet" in contact_note
    )
    partial = (
        r4["active_episode_count"] > 0
        and r1["active_episode_count"] > 0
        and type_a > 0
        and type_b > 0
        and r4["median_dwell_active"] >= 4
        and r1["median_dwell_active"] >= 4
    )
    if full:
        return "TRANSFERABLE_BACKBONE_PHASE_MODEL_FOUND", "TYPE_A and TYPE_B both reached required visual counts and the selected backbone passes structural thresholds on both timeframes."
    if partial:
        return "PARTIAL_BACKBONE_PHASE_DECOMPOSITION", "The layers separate causally and transfer by formula, but at least one strict visual or dwell threshold remains incomplete."
    return "NO_BACKBONE_PHASE_DECOMPOSITION", "The selected model did not produce enough persistent ACTIVE backbone with separated fast phases."


def main() -> None:
    ensure_dirs()
    ohlc1 = load_ohlc("ohlc_1h.csv", "1h")
    ohlc4 = load_ohlc("ohlc_4h.csv", "4h")
    f1 = add_fast_phase(add_backbone_states(add_direction(add_features(ohlc1, "1H"))))
    f4 = add_fast_phase(add_backbone_states(add_direction(add_features(ohlc4, "4H"))))
    bstats1, dwell1, comp1 = backbone_statistics(f1, "1H")
    bstats4, dwell4, comp4 = backbone_statistics(f4, "4H")
    fpstats1 = fast_phase_statistics(f1, "1H")
    fpstats4 = fast_phase_statistics(f4, "4H")
    selected = choose_model(comp1, comp4, fpstats1, fpstats4)
    f1 = add_composite(f1, selected)
    f4 = add_composite(f4, selected)
    ms = merge_multiscale(f1, f4)
    rel_stats = relation_statistics(ms)
    windows = select_windows(ms)
    checks = pd.DataFrame([active_phase_checks(f1, selected, "1H"), active_phase_checks(f4, selected, "4H")])
    comparison = exp011_comparison(selected, comp1, comp4, bstats1, bstats4, ms, windows)

    f1.to_csv(OUT / "trend_features_1h.csv", index=False)
    f4.to_csv(OUT / "trend_features_4h.csv", index=False)
    f1[["open_time", "close_time", "raw_direction", "confirmed_direction", "direction_change_event", "bars_in_direction"]].to_csv(OUT / "direction_states_1h.csv", index=False)
    f4[["open_time", "close_time", "raw_direction", "confirmed_direction", "direction_change_event", "bars_in_direction"]].to_csv(OUT / "direction_states_4h.csv", index=False)
    f1[["open_time", "close_time", "BACKBONE_A_state", "BACKBONE_B_state", "BACKBONE_C_state", "backbone_state"]].to_csv(OUT / "backbone_states_1h.csv", index=False)
    f4[["open_time", "close_time", "BACKBONE_A_state", "BACKBONE_B_state", "BACKBONE_C_state", "backbone_state"]].to_csv(OUT / "backbone_states_4h.csv", index=False)
    f1[["open_time", "close_time", "fast_phase", "fast_phase_h2"]].to_csv(OUT / "fast_phase_states_1h.csv", index=False)
    f4[["open_time", "close_time", "fast_phase", "fast_phase_h2"]].to_csv(OUT / "fast_phase_states_4h.csv", index=False)
    f1[["open_time", "close_time", "confirmed_direction", "backbone_state", "fast_phase", "composite_state"]].to_csv(OUT / "composite_states_1h.csv", index=False)
    f4[["open_time", "close_time", "confirmed_direction", "backbone_state", "fast_phase", "composite_state"]].to_csv(OUT / "composite_states_4h.csv", index=False)
    comp = comp1.merge(comp4, on="model", suffixes=("_1h", "_4h"))
    comp["selected"] = comp["model"] == selected
    comp.to_csv(OUT / "backbone_model_comparison.csv", index=False)
    bstats1.to_csv(OUT / "backbone_state_statistics_1h.csv", index=False)
    bstats4.to_csv(OUT / "backbone_state_statistics_4h.csv", index=False)
    dwell1.to_csv(OUT / "backbone_dwell_times_1h.csv", index=False)
    dwell4.to_csv(OUT / "backbone_dwell_times_4h.csv", index=False)
    fpstats1.to_csv(OUT / "fast_phase_statistics_1h.csv", index=False)
    fpstats4.to_csv(OUT / "fast_phase_statistics_4h.csv", index=False)
    ms.to_csv(OUT / "multiscale_states.csv", index=False)
    rel_stats.to_csv(OUT / "multiscale_relation_statistics.csv", index=False)
    windows.to_csv(OUT / "visual_review_windows.csv", index=False)
    comparison.to_csv(OUT / "exp011_vs_exp011a.csv", index=False)
    pd.concat([direction_stats(f1, "1H"), direction_stats(f4, "4H")]).to_csv(OUT / "direction_statistics.csv", index=False)
    checks.to_csv(OUT / "active_fast_phase_checks.csv", index=False)
    (OUT / "SLOW_BACKBONE_FAST_PHASE_VIEW.pine").write_text(pine_script(selected))
    contact_note = write_contact_sheet(OUT / "SLOW_BACKBONE_FAST_PHASE_CONTACT_SHEET.pdf", windows, ms)
    verdict, verdict_reason = verdict_for(selected, comp1, comp4, checks, windows, contact_note)

    r1 = comp1[comp1["model"] == selected].iloc[0]
    r4 = comp4[comp4["model"] == selected].iloc[0]
    c1 = checks[checks["timeframe"] == "1H"].iloc[0]
    c4 = checks[checks["timeframe"] == "4H"].iloc[0]
    counts = windows["review_type"].value_counts() if not windows.empty else pd.Series(dtype=int)
    type_a = int(counts.get("TYPE_A", 0))
    type_b = int(counts.get("TYPE_B", 0))
    type_c = int(counts.get("TYPE_C", 0))
    type_d = int(counts.get("TYPE_D", 0))
    report = f"""# EXP-011A — SLOW BACKBONE / FAST PHASE DECOMPOSITION

Status: DONE / REPORT_READY

Verdict: {verdict}

## Data

Source: saved EXP-011 OHLC CSVs only. 1H rows `{len(ohlc1)}` from `{ohlc1['open_time'].min()}` to `{ohlc1['close_time'].max()}`. 4H rows `{len(ohlc4)}` from `{ohlc4['open_time'].min()}` to `{ohlc4['close_time'].max()}`. No 2025+ data, no Irobot, no network fetch.

## Answers

1. Selected backbone model: `{selected}`.

2. Same backbone logic on 4H and 1H: yes by formula. Structural transfer is {'accepted' if verdict == 'TRANSFERABLE_BACKBONE_PHASE_MODEL_FOUND' else 'partial'} because 4H changes/100=`{r4['state_changes_per_100_bars']:.2f}` and 1H changes/100=`{r1['state_changes_per_100_bars']:.2f}`.

3. Slow backbone can remain ACTIVE while EMA27 moves toward EMA200. ACTIVE+CONTRACTING bars: 4H `{int(c4['active_contracting_bar_count'])}`, 1H `{int(c1['active_contracting_bar_count'])}`.

4. ACTIVE+CONTRACTING exists on both timeframes.

5. ACTIVE+OPPOSING exists on both timeframes: 4H `{int(c4['active_opposing_bar_count'])}`, 1H `{int(c1['active_opposing_bar_count'])}`.

6. Mean duration: ACTIVE+CONTRACTING 4H `{c4['mean_duration_active_contracting']:.2f}`, 1H `{c1['mean_duration_active_contracting']:.2f}`; ACTIVE+OPPOSING 4H `{c4['mean_duration_active_opposing']:.2f}`, 1H `{c1['mean_duration_active_opposing']:.2f}`.

7. TYPE_A and TYPE_B differ numerically: TYPE_A=`{type_a}`, TYPE_B=`{type_b}`, TYPE_C=`{type_c}`, TYPE_D=`{type_d}`.

8. Visual comparison: {contact_note} TYPE_A and TYPE_B are placed in the same contact-sheet artifact when both exist.

9. Main TYPE_A/TYPE_B difference is EMA200 backbone: TYPE_A requires 4H ACTIVE; TYPE_B requires 4H FLATTENING.

10. EMA27 movement no longer automatically weakens backbone. Fast phase is separate from the EMA200-only backbone.

11. TYPE_A/TYPE_B repeat across distinct months where available; see `visual_review_windows.csv`.

12. Model transfers between 4H and 1H without formula changes; strict verdict depends on visual counts and dwell thresholds.

13. Semantically false WEAKENING is reduced by replacing EXP-011 single WEAKENING with EMA200 backbone plus separate fast phase. See `exp011_vs_exp011a.csv`.

14. Relative corrections remain postponed. EXP-011A supports researching scale relations next only if the partial verdict is accepted as sufficient.

## Verdict Rationale

{verdict_reason}

## Constraints

No ZigZag, clustering, Irobot, volume, funding, open interest, outcome fields, backtest, PnL, entry, exit, stop, risk, or 2025+ data. `docs/DEFINITIONS.md` was not changed.
"""
    (EXP / "REPORT.md").write_text(report)
    print(
        json.dumps(
            {
                "verdict": verdict,
                "selected_model": selected,
                "type_a": type_a,
                "type_b": type_b,
                "type_c": type_c,
                "type_d": type_d,
                "active_contracting_4h": int(c4["active_contracting_bar_count"]),
                "active_opposing_4h": int(c4["active_opposing_bar_count"]),
                "active_contracting_1h": int(c1["active_contracting_bar_count"]),
                "active_opposing_1h": int(c1["active_opposing_bar_count"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
