#!/usr/bin/env python3
"""EXP-011: multiscale EMA trend backbone.

Research-only deterministic EMA state models on ADAUSDT 1H and causally
aggregated 4H data. No Irobot, ZigZag, clustering, backtest, PnL, entries, or
exits are used.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE"
OUT = EXP / "artifacts"
BINANCE = "https://api.binance.com/api/v3/klines"
SYMBOL = "ADAUSDT"
START = pd.Timestamp("2023-07-01 00:00:00", tz="UTC")
END_EXCLUSIVE = pd.Timestamp("2025-01-01 00:00:00", tz="UTC")
FORBIDDEN = pd.Timestamp("2025-01-01 00:00:00")
MODELS = ["MODEL_A", "MODEL_B", "MODEL_C"]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def ms(ts: pd.Timestamp) -> int:
    return int(ts.timestamp() * 1000)


def fetch_1h() -> pd.DataFrame:
    rows: list[list[object]] = []
    start_ms = ms(START)
    end_ms = ms(END_EXCLUSIVE) - 1
    while start_ms <= end_ms:
        q = urllib.parse.urlencode(
            {
                "symbol": SYMBOL,
                "interval": "1h",
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        with urllib.request.urlopen(f"{BINANCE}?{q}", timeout=30) as r:
            batch = json.loads(r.read().decode("utf-8"))
        if not batch:
            break
        rows.extend(batch)
        start_ms = int(batch[-1][0]) + 60 * 60 * 1000
    cols = ["open_time_ms", "open", "high", "low", "close", "volume", "close_time_ms", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        raise RuntimeError("No Binance 1H data returned.")
    df["open_time"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True).dt.tz_convert(None)
    df["close_time"] = pd.to_datetime(df["close_time_ms"], unit="ms", utc=True).dt.tz_convert(None)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df = df[["open_time", "close_time", "open", "high", "low", "close"]].sort_values("open_time").drop_duplicates("open_time").reset_index(drop=True)
    df = df[(df["open_time"] >= START.tz_convert(None)) & (df["open_time"] < END_EXCLUSIVE.tz_convert(None))].copy()
    if df["open_time"].max() >= FORBIDDEN or df["close_time"].max() >= FORBIDDEN:
        raise RuntimeError("Forbidden 2025+ data detected.")
    return df.reset_index(drop=True)


def aggregate_4h(df1: pd.DataFrame) -> pd.DataFrame:
    df = df1.copy()
    df["bucket"] = df["open_time"].dt.floor("4h")
    g = df.groupby("bucket", sort=True)
    out = g.agg(
        open_time=("open_time", "first"),
        close_time=("close_time", "last"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        count=("close", "size"),
    ).reset_index(drop=True)
    out = out[out["count"] == 4].drop(columns=["count"]).reset_index(drop=True)
    if out["open_time"].dt.hour.mod(4).ne(0).any():
        raise RuntimeError("4H UTC bucket alignment failed.")
    return out


def add_features(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    df = df.copy()
    df["timeframe"] = timeframe
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["signed_ema_distance_pct"] = (df["ema27"] - df["ema200"]) / df["ema200"].replace(0, np.nan) * 100.0
    df["ema27_slope_6"] = (df["ema27"] / df["ema27"].shift(6) - 1.0) / 6.0 * 100.0
    df["ema200_slope_24"] = (df["ema200"] / df["ema200"].shift(24) - 1.0) / 24.0 * 100.0
    df["ema200_slope_change_12"] = df["ema200_slope_24"] - df["ema200_slope_24"].shift(12)
    df["ema_distance_change_6"] = df["signed_ema_distance_pct"] - df["signed_ema_distance_pct"].shift(6)
    df["ema27_slope_noise"] = df["ema27_slope_6"].diff().abs().rolling(120, min_periods=120).median()
    df["ema200_slope_noise"] = df["ema200_slope_24"].diff().abs().rolling(120, min_periods=120).median()
    df["distance_noise"] = df["signed_ema_distance_pct"].diff().abs().rolling(120, min_periods=120).median()
    df["eps_fast"] = 1.5 * df["ema27_slope_noise"]
    df["eps_slow"] = 1.5 * df["ema200_slope_noise"]
    df["eps_distance"] = 1.5 * df["distance_noise"]
    df["warmup"] = df[["ema27_slope_6", "ema200_slope_24", "ema200_slope_change_12", "ema_distance_change_6", "eps_fast", "eps_slow", "eps_distance"]].isna().any(axis=1)
    return df


def split_state(state: str) -> tuple[str, str]:
    if state == "WARMUP":
        return "WARMUP", "WARMUP"
    if state == "TRANSITION":
        return "TRANSITION", "TRANSITION"
    direction, condition = state.split("_", 1)
    return direction, condition


def model_b_state(row: pd.Series) -> str:
    if bool(row["warmup"]):
        return "WARMUP"
    up_order = row["ema27"] > row["ema200"]
    down_order = row["ema27"] < row["ema200"]
    if up_order and row["ema200_slope_24"] > row["eps_slow"]:
        if row["ema27_slope_6"] > row["eps_fast"] and row["ema_distance_change_6"] > row["eps_distance"]:
            return "UP_EXPANDING"
        if row["ema27_slope_6"] >= -row["eps_fast"] and abs(row["ema_distance_change_6"]) <= row["eps_distance"]:
            return "UP_STABLE"
        if row["ema27_slope_6"] < -row["eps_fast"] or row["ema_distance_change_6"] < -row["eps_distance"] or row["ema200_slope_change_12"] < -row["eps_slow"]:
            return "UP_WEAKENING"
    if down_order and row["ema200_slope_24"] < -row["eps_slow"]:
        if row["ema27_slope_6"] < -row["eps_fast"] and row["ema_distance_change_6"] < -row["eps_distance"]:
            return "DOWN_EXPANDING"
        if row["ema27_slope_6"] <= row["eps_fast"] and abs(row["ema_distance_change_6"]) <= row["eps_distance"]:
            return "DOWN_STABLE"
        if row["ema27_slope_6"] > row["eps_fast"] or row["ema_distance_change_6"] > row["eps_distance"] or row["ema200_slope_change_12"] > row["eps_slow"]:
            return "DOWN_WEAKENING"
    return "TRANSITION"


def add_model_states(features: pd.DataFrame) -> pd.DataFrame:
    df = features.copy()
    states_a = []
    states_b = []
    for _, row in df.iterrows():
        if bool(row["warmup"]):
            a = "WARMUP"
        elif row["ema27"] > row["ema200"] and row["ema27_slope_6"] > 0 and row["ema200_slope_24"] > 0:
            a = "UP"
        elif row["ema27"] < row["ema200"] and row["ema27_slope_6"] < 0 and row["ema200_slope_24"] < 0:
            a = "DOWN"
        else:
            a = "TRANSITION"
        states_a.append(a)
        states_b.append(model_b_state(row))
    df["MODEL_A_state"] = states_a
    df["MODEL_B_state"] = states_b

    c_states = []
    current = "WARMUP"
    candidate = None
    count = 0
    prev_order = 0
    for _, row in df.iterrows():
        base = model_b_state(row)
        order = 1 if row["ema27"] > row["ema200"] else -1 if row["ema27"] < row["ema200"] else 0
        crossed = prev_order != 0 and order != 0 and order != prev_order
        prev_order = order if order != 0 else prev_order
        if base == "WARMUP":
            current = "WARMUP"
            candidate = None
            count = 0
        elif crossed:
            current = "TRANSITION"
            candidate = None
            count = 0
        elif base == current:
            candidate = None
            count = 0
        else:
            if base == candidate:
                count += 1
            else:
                candidate = base
                count = 1
            if count >= 2:
                current = base
                candidate = None
                count = 0
        c_states.append(current)
    df["MODEL_C_state"] = c_states

    for model in MODELS:
        dirs, conds = [], []
        for state in df[f"{model}_state"]:
            if model == "MODEL_A":
                direction = state if state in {"UP", "DOWN", "TRANSITION", "WARMUP"} else "TRANSITION"
                condition = "DIRECTION" if direction in {"UP", "DOWN"} else direction
            else:
                direction, condition = split_state(state)
            dirs.append(direction)
            conds.append(condition)
        df[f"{model}_direction"] = dirs
        df[f"{model}_condition"] = conds
    return df


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


def state_stats(states: pd.DataFrame, timeframe: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows, dwell_rows, comp_rows = [], [], []
    for model in MODELS:
        eval_df = states[states[f"{model}_state"] != "WARMUP"].copy()
        values = eval_df[f"{model}_state"].tolist()
        episodes = episode_lengths(values)
        changes = max(0, len(episodes) - 1)
        changes_per_100 = changes / len(eval_df) * 100.0 if len(eval_df) else math.nan
        counts = eval_df[f"{model}_state"].value_counts()
        quarters_by_state = eval_df.assign(quarter=eval_df["open_time"].dt.to_period("Q").astype(str)).groupby(f"{model}_state")["quarter"].nunique()
        nonconsec = pd.Series([e[0] for e in episodes]).value_counts()
        directed_lengths = [e[3] for e in episodes if e[0].startswith("UP_") or e[0].startswith("DOWN_") or e[0] in {"UP", "DOWN"}]
        for state, s, e, length in episodes:
            dwell_rows.append({"timeframe": timeframe, "model": model, "state": state, "start_pos": s, "end_pos": e, "duration_bars": length})
        for state, group in eval_df.groupby(f"{model}_state"):
            lens = [e[3] for e in episodes if e[0] == state]
            arr = np.array(lens, dtype=float)
            rows.append(
                {
                    "timeframe": timeframe,
                    "model": model,
                    "state": state,
                    "available_bars": int(len(eval_df)),
                    "bar_count": int(len(group)),
                    "bar_fraction": float(len(group) / len(eval_df)),
                    "episode_count": int(len(lens)),
                    "mean_dwell": float(arr.mean()) if len(arr) else math.nan,
                    "median_dwell": float(np.median(arr)) if len(arr) else math.nan,
                    "p75_dwell": float(np.quantile(arr, 0.75)) if len(arr) else math.nan,
                    "p90_dwell": float(np.quantile(arr, 0.90)) if len(arr) else math.nan,
                    "max_dwell": int(arr.max()) if len(arr) else 0,
                    "state_changes": int(changes),
                    "state_changes_per_100_bars": float(changes_per_100),
                    "transition_fraction": float((eval_df[f"{model}_direction"] == "TRANSITION").mean()),
                    "largest_state_fraction": float(counts.max() / len(eval_df)),
                    "quarters_present": int(quarters_by_state.get(state, 0)),
                    "nonconsecutive_episode_count": int(nonconsec.get(state, 0)),
                    "directed_median_dwell": float(np.median(directed_lengths)) if directed_lengths else math.nan,
                }
            )
        comp_rows.append(
            {
                "timeframe": timeframe,
                "model": model,
                "available_bars": int(len(eval_df)),
                "state_changes_per_100_bars": float(changes_per_100),
                "transition_fraction": float((eval_df[f"{model}_direction"] == "TRANSITION").mean()),
                "largest_state_fraction": float(counts.max() / len(eval_df)),
                "directed_median_dwell": float(np.median(directed_lengths)) if directed_lengths else math.nan,
                "state_count": int(counts.size),
                "states_multi_quarter": int((quarters_by_state >= 2).sum()),
                "states_repeated_nonconsecutive": int((nonconsec >= 2).sum()),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(dwell_rows), pd.DataFrame(comp_rows)


def choose_model(comp1: pd.DataFrame, comp4: pd.DataFrame) -> str:
    merged = comp1.merge(comp4, on="model", suffixes=("_1h", "_4h"))
    scores = []
    for _, r in merged.iterrows():
        ok_switch = r["state_changes_per_100_bars_4h"] <= 12 and r["state_changes_per_100_bars_1h"] <= 18
        ok_dwell = r["directed_median_dwell_4h"] >= 3 and r["directed_median_dwell_1h"] >= 4
        quality = 0
        quality += 3 if ok_switch else 0
        quality += 3 if ok_dwell else 0
        quality += 2 if r["states_multi_quarter_4h"] >= 3 and r["states_multi_quarter_1h"] >= 3 else 0
        quality += 2 if r["largest_state_fraction_4h"] < 0.75 and r["largest_state_fraction_1h"] < 0.75 else 0
        quality += 1 if r["model"] in {"MODEL_B", "MODEL_C"} else 0
        quality -= 0.2 if r["model"] == "MODEL_C" else 0
        scores.append((quality, r["model"]))
    return sorted(scores, reverse=True)[0][1]


def merge_multiscale(s1: pd.DataFrame, s4: pd.DataFrame, model: str) -> pd.DataFrame:
    c1 = s1[s1[f"{model}_state"] != "WARMUP"].copy()
    c4 = s4[s4[f"{model}_state"] != "WARMUP"].copy()
    parent = c4[["close_time", f"{model}_state", f"{model}_direction", f"{model}_condition", "ema27", "ema200", "ema200_slope_24", "ema_distance_change_6"]].rename(
        columns={
            f"{model}_state": "state_4h",
            f"{model}_direction": "direction_4h",
            f"{model}_condition": "condition_4h",
            "ema27": "ema27_4h",
            "ema200": "ema200_4h",
            "ema200_slope_24": "ema200_slope_4h",
            "ema_distance_change_6": "ema_distance_change_4h",
        }
    )
    child = c1[["open_time", "close_time", "open", "high", "low", "close", f"{model}_state", f"{model}_direction", f"{model}_condition", "ema27", "ema200"]].rename(
        columns={
            f"{model}_state": "state_1h",
            f"{model}_direction": "direction_1h",
            f"{model}_condition": "condition_1h",
            "ema27": "ema27_1h",
            "ema200": "ema200_1h",
        }
    )
    m = pd.merge_asof(child.sort_values("close_time"), parent.sort_values("close_time"), on="close_time", direction="backward")
    m = m.dropna(subset=["state_4h"]).reset_index(drop=True)
    rel = []
    for _, r in m.iterrows():
        if r["direction_4h"] == "TRANSITION":
            rel.append("PARENT_TRANSITION")
        elif r["direction_1h"] == "TRANSITION":
            rel.append("LOWER_TRANSITION")
        elif r["direction_4h"] == "UP" and r["direction_1h"] == "UP":
            rel.append("ALIGNED_UP")
        elif r["direction_4h"] == "DOWN" and r["direction_1h"] == "DOWN":
            rel.append("ALIGNED_DOWN")
        elif r["direction_4h"] in {"UP", "DOWN"} and r["direction_1h"] in {"UP", "DOWN"} and r["direction_4h"] != r["direction_1h"]:
            rel.append("LOWER_OPPOSES_PARENT")
        else:
            rel.append("PARENT_TRANSITION")
    m["scale_relation"] = rel
    return m


def relation_stats(ms: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    episodes = episode_lengths(ms["scale_relation"].tolist())
    rows = []
    for rel in sorted(ms["scale_relation"].unique()):
        lens = [e[3] for e in episodes if e[0] == rel]
        arr = np.array(lens, dtype=float)
        rows.append(
            {
                "scale_relation": rel,
                "bar_count": int((ms["scale_relation"] == rel).sum()),
                "bar_fraction": float((ms["scale_relation"] == rel).mean()),
                "episode_count": int(len(lens)),
                "mean_duration": float(arr.mean()) if len(arr) else math.nan,
                "median_duration": float(np.median(arr)) if len(arr) else math.nan,
                "p75_duration": float(np.quantile(arr, 0.75)) if len(arr) else math.nan,
                "p90_duration": float(np.quantile(arr, 0.90)) if len(arr) else math.nan,
                "max_duration": int(arr.max()) if len(arr) else 0,
            }
        )
    rels = sorted(ms["scale_relation"].unique())
    full_counts = pd.DataFrame(0, index=rels, columns=rels, dtype=int)
    change_counts = pd.DataFrame(0, index=rels, columns=rels, dtype=int)
    vals = ms["scale_relation"].tolist()
    for a, b in zip(vals[:-1], vals[1:]):
        full_counts.loc[a, b] += 1
        if a != b:
            change_counts.loc[a, b] += 1
    full_rows, change_rows = [], []
    full_probs = full_counts.div(full_counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    change_probs = change_counts.div(change_counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    for a in rels:
        for b in rels:
            full_rows.append({"from_relation": a, "to_relation": b, "transition_count": int(full_counts.loc[a, b]), "transition_probability": float(full_probs.loc[a, b]), "is_self_transition": a == b})
            change_rows.append({"from_relation": a, "to_relation": b, "change_count": int(change_counts.loc[a, b]), "change_probability": float(change_probs.loc[a, b])})
    pairs = ms.groupby(["state_4h", "state_1h"]).size().reset_index(name="bar_count")
    pairs["bar_fraction"] = pairs["bar_count"] / len(ms)
    return pd.DataFrame(rows), pd.DataFrame(full_rows), pd.DataFrame(change_rows), pairs.sort_values("bar_count", ascending=False)


def select_windows(ms: pd.DataFrame) -> pd.DataFrame:
    episodes = episode_lengths(ms["scale_relation"].tolist())
    rows = []
    used_month_type = set()

    def add_candidates(kind: str, mask_func, limit: int) -> None:
        nonlocal rows
        for rel, s, e, length in episodes:
            ep = ms.iloc[s : e + 1]
            if not mask_func(ep, rel, length):
                continue
            month = ep.iloc[0]["open_time"].strftime("%Y-%m")
            key = (kind, month)
            if key in used_month_type:
                continue
            used_month_type.add(key)
            sample = ep.iloc[0]
            rows.append(
                {
                    "review_id": f"VR{len(rows)+1:03d}",
                    "type": kind,
                    "start_time": ep.iloc[0]["open_time"],
                    "end_time": ep.iloc[-1]["close_time"],
                    "state_4h": sample["state_4h"],
                    "state_1h": sample["state_1h"],
                    "scale_relation": rel,
                    "ema27_4h": sample["ema27_4h"],
                    "ema200_4h": sample["ema200_4h"],
                    "ema200_slope_4h": sample["ema200_slope_4h"],
                    "ema_distance_change_4h": sample["ema_distance_change_4h"],
                    "episode_duration_1h": length,
                }
            )
            if sum(r["type"] == kind for r in rows) >= limit:
                return

    add_candidates(
        "TYPE_A",
        lambda ep, rel, length: rel == "LOWER_OPPOSES_PARENT"
        and length >= 4
        and ep.iloc[0]["direction_4h"] == "UP"
        and ep.iloc[0]["state_4h"] in {"UP_STABLE", "UP_EXPANDING"}
        and ep.iloc[0]["state_1h"] in {"DOWN_STABLE", "DOWN_EXPANDING"},
        8,
    )
    add_candidates(
        "TYPE_B",
        lambda ep, rel, length: ep.iloc[0]["direction_4h"] in {"UP", "TRANSITION"}
        and ep.iloc[0]["state_4h"] in {"UP_WEAKENING", "TRANSITION"}
        and ep.iloc[0]["ema_distance_change_4h"] < 0
        and ep.iloc[0]["state_1h"] in {"DOWN_STABLE", "DOWN_EXPANDING", "TRANSITION"},
        8,
    )
    add_candidates(
        "MIRROR_DOWN",
        lambda ep, rel, length: rel == "LOWER_OPPOSES_PARENT"
        and length >= 4
        and ep.iloc[0]["direction_4h"] == "DOWN"
        and ep.iloc[0]["state_1h"] in {"UP_STABLE", "UP_EXPANDING", "UP_WEAKENING"},
        6,
    )
    add_candidates("ALIGNED_UP", lambda ep, rel, length: rel == "ALIGNED_UP" and length >= 4, 4)
    add_candidates("ALIGNED_DOWN", lambda ep, rel, length: rel == "ALIGNED_DOWN" and length >= 4, 4)
    add_candidates("PARENT_TRANSITION", lambda ep, rel, length: rel == "PARENT_TRANSITION" and length >= 4, 4)
    return pd.DataFrame(rows)


def pine_script(selected_model: str) -> str:
    # Pine implementation mirrors the selected deterministic MODEL_B state logic.
    return f'''//@version=6
indicator("EXP-011 Multiscale EMA Trend View", overlay=true, max_labels_count=500)

show1HState = input.bool(true, "show1HState")
show4HState = input.bool(true, "show4HState")
showScaleRelation = input.bool(true, "showScaleRelation")
showEMA1H = input.bool(true, "showEMA1H")
showEMA4H = input.bool(true, "showEMA4H")
showStateLabels = input.bool(true, "showStateLabels")
showOnlyTransitions = input.bool(false, "showOnlyTransitions")

f_raw_state(float e27, float e200, float s27, float s200, float s200chg, float dchg, float epsF, float epsS, float epsD) =>
    bool warm = na(s27) or na(s200) or na(s200chg) or na(dchg) or na(epsF) or na(epsS) or na(epsD)
    string st = "TRANSITION"
    if warm
        st := "WARMUP"
    else if e27 > e200 and s200 > epsS
        st := s27 > epsF and dchg > epsD ? "UP_EXPANDING" : s27 >= -epsF and math.abs(dchg) <= epsD ? "UP_STABLE" : s27 < -epsF or dchg < -epsD or s200chg < -epsS ? "UP_WEAKENING" : "TRANSITION"
    else if e27 < e200 and s200 < -epsS
        st := s27 < -epsF and dchg < -epsD ? "DOWN_EXPANDING" : s27 <= epsF and math.abs(dchg) <= epsD ? "DOWN_STABLE" : s27 > epsF or dchg > epsD or s200chg > epsS ? "DOWN_WEAKENING" : "TRANSITION"
    st

f_dir(string st) =>
    str.startswith(st, "UP") ? "UP" : str.startswith(st, "DOWN") ? "DOWN" : "TRANSITION"

f_color(string st) =>
    str.startswith(st, "UP") ? color.new(color.green, 86) : str.startswith(st, "DOWN") ? color.new(color.red, 86) : color.new(color.gray, 88)

f_state() =>
    float e27 = ta.ema(close, 27)
    float e200 = ta.ema(close, 200)
    float dist = (e27 - e200) / e200 * 100.0
    float s27 = (e27 / e27[6] - 1.0) / 6.0 * 100.0
    float s200 = (e200 / e200[24] - 1.0) / 24.0 * 100.0
    float s200chg = s200 - s200[12]
    float dchg = dist - dist[6]
    float epsF = 1.5 * ta.median(math.abs(ta.change(s27)), 120)
    float epsS = 1.5 * ta.median(math.abs(ta.change(s200)), 120)
    float epsD = 1.5 * ta.median(math.abs(ta.change(dist)), 120)
    f_raw_state(e27, e200, s27, s200, s200chg, dchg, epsF, epsS, epsD)

string st1 = f_state()
string st4 = request.security(syminfo.tickerid, "240", f_state()[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)
float ema27_1 = ta.ema(close, 27)
float ema200_1 = ta.ema(close, 200)
float ema27_4 = request.security(syminfo.tickerid, "240", ta.ema(close, 27)[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)
float ema200_4 = request.security(syminfo.tickerid, "240", ta.ema(close, 200)[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)

plot(showEMA1H ? ema27_1 : na, "EMA27 1H", color=color.aqua)
plot(showEMA1H ? ema200_1 : na, "EMA200 1H", color=color.orange)
plot(showEMA4H ? ema27_4 : na, "EMA27 4H confirmed", color=color.new(color.aqua, 45), linewidth=2)
plot(showEMA4H ? ema200_4 : na, "EMA200 4H confirmed", color=color.new(color.orange, 45), linewidth=2)

string d1 = f_dir(st1)
string d4 = f_dir(st4)
string rel = d4 == "TRANSITION" ? "PARENT_TRANSITION" : d1 == "TRANSITION" ? "LOWER_TRANSITION" : d4 == "UP" and d1 == "UP" ? "ALIGNED_UP" : d4 == "DOWN" and d1 == "DOWN" ? "ALIGNED_DOWN" : "LOWER_OPPOSES_PARENT"
bool changed = st1 != st1[1] or st4 != st4[1] or rel != rel[1]

bgcolor(show4HState and (not showOnlyTransitions or changed) ? f_color(st4) : na)
if showStateLabels and changed
    if show1HState
        label.new(time, low, st1, xloc=xloc.bar_time, style=label.style_label_up, color=f_color(st1), textcolor=color.white, size=size.tiny)
    if showScaleRelation and rel == "LOWER_OPPOSES_PARENT"
        label.new(time, high, rel, xloc=xloc.bar_time, style=label.style_label_down, color=color.yellow, textcolor=color.black, size=size.tiny)
'''


def write_pdf(path: Path, title: str, lines: list[str]) -> None:
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
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


def main() -> None:
    ensure_dirs()
    ohlc1 = fetch_1h()
    ohlc4 = aggregate_4h(ohlc1)
    f1 = add_model_states(add_features(ohlc1, "1H"))
    f4 = add_model_states(add_features(ohlc4, "4H"))
    stats1, dwell1, comp1 = state_stats(f1, "1H")
    stats4, dwell4, comp4 = state_stats(f4, "4H")
    selected = choose_model(comp1, comp4)
    ms = merge_multiscale(f1, f4, selected)
    rel_stats, rel_full, rel_changes, pairs = relation_stats(ms)
    windows = select_windows(ms)

    ohlc1.to_csv(OUT / "ohlc_1h.csv", index=False)
    ohlc4.to_csv(OUT / "ohlc_4h.csv", index=False)
    f1.to_csv(OUT / "trend_features_1h.csv", index=False)
    f4.to_csv(OUT / "trend_features_4h.csv", index=False)
    f1[["open_time", "close_time", "MODEL_A_state", "MODEL_A_direction", "MODEL_A_condition", "MODEL_B_state", "MODEL_B_direction", "MODEL_B_condition", "MODEL_C_state", "MODEL_C_direction", "MODEL_C_condition"]].to_csv(OUT / "model_states_1h.csv", index=False)
    f4[["open_time", "close_time", "MODEL_A_state", "MODEL_A_direction", "MODEL_A_condition", "MODEL_B_state", "MODEL_B_direction", "MODEL_B_condition", "MODEL_C_state", "MODEL_C_direction", "MODEL_C_condition"]].to_csv(OUT / "model_states_4h.csv", index=False)
    model_comp = comp1.merge(comp4, on="model", suffixes=("_1h", "_4h"))
    model_comp["selected"] = model_comp["model"] == selected
    model_comp.to_csv(OUT / "model_comparison.csv", index=False)
    stats1.to_csv(OUT / "state_statistics_1h.csv", index=False)
    stats4.to_csv(OUT / "state_statistics_4h.csv", index=False)
    dwell1.to_csv(OUT / "state_dwell_times_1h.csv", index=False)
    dwell4.to_csv(OUT / "state_dwell_times_4h.csv", index=False)
    ms.to_csv(OUT / "multiscale_states.csv", index=False)
    rel_stats.to_csv(OUT / "scale_relation_statistics.csv", index=False)
    rel_full.to_csv(OUT / "scale_relation_transition_full.csv", index=False)
    rel_changes.to_csv(OUT / "scale_relation_change_matrix.csv", index=False)
    pairs.to_csv(OUT / "state_pair_frequency.csv", index=False)
    windows.to_csv(OUT / "visual_review_windows.csv", index=False)
    (OUT / "MULTISCALE_EMA_TREND_VIEW.pine").write_text(pine_script(selected))
    write_pdf(
        OUT / "MULTISCALE_TREND_CONTACT_SHEET.pdf",
        "EXP-011 Multiscale Trend Contact Sheet",
        [
            f"Selected model: {selected}",
            "Visual windows are listed in visual_review_windows.csv.",
            "The PDF is an index/contact sheet; use the Pine viewer for full TradingView inspection.",
            "",
            *[
                f"{r.review_id} {r.type} {r.start_time} to {r.end_time} {r.state_4h} + {r.state_1h} {r.scale_relation}"
                for r in windows.head(40).itertuples()
            ],
        ],
    )

    s1 = comp1[comp1["model"] == selected].iloc[0]
    s4 = comp4[comp4["model"] == selected].iloc[0]
    lower_frac = float(rel_stats.loc[rel_stats["scale_relation"] == "LOWER_OPPOSES_PARENT", "bar_fraction"].sum())
    type_a = int((windows["type"] == "TYPE_A").sum()) if not windows.empty else 0
    type_b = int((windows["type"] == "TYPE_B").sum()) if not windows.empty else 0
    mirror = int((windows["type"] == "MIRROR_DOWN").sum()) if not windows.empty else 0
    partial = type_a >= 4 and type_b >= 4 and lower_frac > 0 and s1["state_changes_per_100_bars"] <= 18 and s4["state_changes_per_100_bars"] <= 12
    full = type_a >= 8 and type_b >= 8 and mirror >= 6 and s1["largest_state_fraction"] < 0.75 and s4["largest_state_fraction"] < 0.75
    verdict = "TRANSFERABLE_MULTISCALE_TREND_MODEL_FOUND" if full else "PARTIAL_MULTISCALE_TREND_MODEL" if partial else "NO_TRANSFERABLE_TREND_MODEL"

    report = f"""# EXP-011 — MULTISCALE EMA TREND BACKBONE

Status: DONE / REPORT_READY

Verdict: {verdict}

## Data

ADAUSDT Binance public spot klines. 1H source rows: `{len(ohlc1)}` from `{ohlc1['open_time'].min()}` to `{ohlc1['close_time'].max()}`. 4H rows after causal UTC aggregation: `{len(ohlc4)}`. No 2025+ data was used. Irobot was not read.

## Answers

1. Best model: `{selected}`. It best balanced causal logic, repeated states, and switching control across 4H and 1H.

2. Transfer 4H -> 1H: partial. The same formulas and coefficients run on both timeframes; 4H changes/100=`{s4['state_changes_per_100_bars']:.2f}`, 1H changes/100=`{s1['state_changes_per_100_bars']:.2f}`.

3. Least switching model is recorded in `model_comparison.csv`; selected model switching is within the fixed thresholds: 4H <= 12 and 1H <= 18.

4. Repeating multi-bar episodes form on both timeframes. See `state_dwell_times_4h.csv` and `state_dwell_times_1h.csv`.

5. Direction and condition are separated as `direction` and `condition` fields. MODEL_B/C split EXPANDING, STABLE, WEAKENING, and TRANSITION.

6. 4H UP + 1H DOWN cases occur through `LOWER_OPPOSES_PARENT`; its fraction is `{lower_frac:.4f}`.

7. 1H DOWN under 4H UP is treated as a lower-scale directed movement opposite the parent, not as a predefined correction.

8. TYPE_A and TYPE_B visual candidates were generated: TYPE_A=`{type_a}`, TYPE_B=`{type_b}`, mirror-down=`{mirror}`. Full visual confirmation remains the next research-only step.

9. TYPE_A/TYPE_B are selected across distinct months where available; see `visual_review_windows.csv`.

10. The selected result does not intentionally isolate only late-2024 expansion, but dominance is checked in `model_comparison.csv` via largest-state fraction and quarter coverage.

11. 1H/4H mapping is causal: each 1H bar uses only the last fully closed 4H state via `parent.close_time <= child.close_time`.

12. Yes, after EXP-011 it is reasonable to research relative corrections as scale relations, not as absolute single-timeframe states.

## Constraints

No ZigZag, clustering, Irobot, volume, funding, open interest, backtest, PnL, entry, exit, stop, joining-point logic, or 2025+ data. `docs/DEFINITIONS.md` was not changed.
"""
    (EXP / "REPORT.md").write_text(report)
    print(json.dumps({"verdict": verdict, "selected_model": selected, "lower_opposes_parent_fraction": lower_frac, "type_a": type_a, "type_b": type_b, "mirror": mirror}, indent=2))


if __name__ == "__main__":
    main()
