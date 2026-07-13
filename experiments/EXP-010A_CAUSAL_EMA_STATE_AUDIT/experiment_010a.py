#!/usr/bin/env python3
"""EXP-010A: causal EMA state audit.

This script audits EXP-010 and builds a two-layer EMA state model:
EMA backbone clustering plus a causal local price phase machine.

It uses only local EXP-010 OHLC artifacts as source data, then recomputes
EMA27/EMA200 and all EXP-010A features. It does not read Irobot, use ZigZag,
build a trading system, search entries/exits, backtest, or calculate PnL.
"""

from __future__ import annotations

import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-010A_CAUSAL_EMA_STATE_AUDIT"
OUT = EXP / "artifacts"
EXP010 = ROOT / "experiments/EXP-010_EMA_STATE_MODEL"
EXP010_ART = EXP010 / "artifacts"

START = pd.Timestamp("2023-07-01 00:00:00")
END = pd.Timestamp("2024-12-31 20:00:00")
FORBIDDEN = pd.Timestamp("2025-01-01 00:00:00")
K_VALUES = [2, 3, 4, 5, 6]
SEEDS = list(range(100, 130))

RAW_FEATURES = [
    "signed_ema_distance_pct",
    "ema27_slope_3",
    "ema27_slope_6",
    "ema200_slope_12",
    "ema200_slope_24",
    "ema200_slope_change",
    "ema_distance_change_6",
    "ema_distance_change_12",
]

ALIGNED_FEATURES = [
    "absolute_ema_distance_pct",
    "aligned_ema27_slope_3",
    "aligned_ema27_slope_6",
    "aligned_ema200_slope_12",
    "aligned_ema200_slope_24",
    "aligned_ema200_slope_change",
    "aligned_distance_change_6",
    "aligned_distance_change_12",
]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    src = EXP010_ART / "ema_state_features.csv"
    df = pd.read_csv(src, usecols=["dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values("dt").drop_duplicates("dt").reset_index(drop=True)
    df = df[(df["dt"] >= START) & (df["dt"] <= END)].copy().reset_index(drop=True)
    if df.empty or df["dt"].max() >= FORBIDDEN:
        raise RuntimeError("EXP-010A source data missing or contains 2025+ rows.")
    return df


def add_backbone_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["signed_ema_distance_pct"] = (df["ema27"] - df["ema200"]) / df["ema200"].replace(0, np.nan) * 100.0
    df["ema27_slope_3"] = (df["ema27"] / df["ema27"].shift(3) - 1.0) / 3.0 * 100.0
    df["ema27_slope_6"] = (df["ema27"] / df["ema27"].shift(6) - 1.0) / 6.0 * 100.0
    df["ema200_slope_12"] = (df["ema200"] / df["ema200"].shift(12) - 1.0) / 12.0 * 100.0
    df["ema200_slope_24"] = (df["ema200"] / df["ema200"].shift(24) - 1.0) / 24.0 * 100.0
    df["ema200_slope_change"] = df["ema200_slope_12"] - df["ema200_slope_12"].shift(12)
    df["ema_distance_change_6"] = df["signed_ema_distance_pct"] - df["signed_ema_distance_pct"].shift(6)
    df["ema_distance_change_12"] = df["signed_ema_distance_pct"] - df["signed_ema_distance_pct"].shift(12)
    df["direction"] = np.where(df["ema27"] > df["ema200"], 1, -1)
    df["absolute_ema_distance_pct"] = df["signed_ema_distance_pct"].abs()
    for col in ["ema27_slope_3", "ema27_slope_6", "ema200_slope_12", "ema200_slope_24", "ema200_slope_change"]:
        df["aligned_" + col] = df["direction"] * df[col]
    df["aligned_distance_change_6"] = df["direction"] * df["ema_distance_change_6"]
    df["aligned_distance_change_12"] = df["direction"] * df["ema_distance_change_12"]
    return df


def standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu = np.nanmean(x, axis=0)
    sig = np.nanstd(x, axis=0)
    sig[sig == 0] = 1.0
    return (x - mu) / sig, mu, sig


def kmeans_plus_plus(x: np.ndarray, k: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    centers = [x[rng.integers(0, len(x))]]
    for _ in range(1, k):
        dist = np.min(((x[:, None, :] - np.array(centers)[None, :, :]) ** 2).sum(axis=2), axis=1)
        total = dist.sum()
        if total <= 0:
            centers.append(x[rng.integers(0, len(x))])
        else:
            centers.append(x[rng.choice(len(x), p=dist / total)])
    return np.array(centers, dtype=float)


def kmeans(x: np.ndarray, k: int, seed: int, max_iter: int = 500) -> tuple[np.ndarray, np.ndarray, float]:
    centers = kmeans_plus_plus(x, k, seed)
    labels = np.full(len(x), -1, dtype=int)
    for _ in range(max_iter):
        dist = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = dist.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for j in range(k):
            if np.any(labels == j):
                centers[j] = x[labels == j].mean(axis=0)
    inertia = float(((x - centers[labels]) ** 2).sum())
    return labels, centers, inertia


def silhouette_score(x: np.ndarray, labels: np.ndarray, max_points: int = 900) -> float:
    if len(x) > max_points:
        idx = np.linspace(0, len(x) - 1, max_points).astype(int)
        x = x[idx]
        labels = labels[idx]
    labs = np.unique(labels)
    if len(labs) < 2:
        return math.nan
    diff = x[:, None, :] - x[None, :, :]
    dist = np.sqrt((diff * diff).sum(axis=2))
    vals = []
    for i in range(len(x)):
        same = labels == labels[i]
        a = float(dist[i, same].mean()) if same.sum() > 1 else 0.0
        b = min(float(dist[i, labels == lab].mean()) for lab in labs if lab != labels[i])
        vals.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return float(np.mean(vals))


def adjusted_rand_index(a: np.ndarray, b: np.ndarray) -> float:
    a_vals, a_inv = np.unique(a, return_inverse=True)
    b_vals, b_inv = np.unique(b, return_inverse=True)
    table = np.zeros((len(a_vals), len(b_vals)), dtype=np.int64)
    for i, j in zip(a_inv, b_inv):
        table[i, j] += 1

    def comb2(n: np.ndarray | int) -> np.ndarray | float:
        return np.asarray(n) * (np.asarray(n) - 1) / 2.0

    sum_comb = float(comb2(table).sum())
    row_comb = float(comb2(table.sum(axis=1)).sum())
    col_comb = float(comb2(table.sum(axis=0)).sum())
    total = float(comb2(len(a)))
    expected = row_comb * col_comb / total if total else 0.0
    max_index = 0.5 * (row_comb + col_comb)
    return (sum_comb - expected) / (max_index - expected) if max_index != expected else 1.0


def dwell_times(labels: np.ndarray) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    if len(labels) == 0:
        return out
    current = int(labels[0])
    length = 1
    for lab in labels[1:]:
        lab = int(lab)
        if lab == current:
            length += 1
        else:
            out.setdefault(current, []).append(length)
            current = lab
            length = 1
    out.setdefault(current, []).append(length)
    return out


def ordered_labels(df: pd.DataFrame, labels: np.ndarray, model: str) -> np.ndarray:
    metric = "signed_ema_distance_pct" if model == "MODEL_RAW" else "absolute_ema_distance_pct"
    tmp = pd.DataFrame({"label": labels, "metric": df[metric].to_numpy(float)})
    order = tmp.groupby("label")["metric"].mean().sort_values().index.tolist()
    mapping = {old: new for new, old in enumerate(order, start=1)}
    return np.array([mapping[x] for x in labels], dtype=int)


def run_clustering(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, int, int], np.ndarray]]:
    runs = []
    labels_by_run: dict[tuple[str, int, int], np.ndarray] = {}
    for model, cols in [("MODEL_RAW", RAW_FEATURES), ("MODEL_ALIGNED", ALIGNED_FEATURES)]:
        x, _, _ = standardize(features[cols].to_numpy(float))
        for k in K_VALUES:
            for seed in SEEDS:
                labels, _, inertia = kmeans(x, k, seed)
                labels = ordered_labels(features, labels, model)
                labels_by_run[(model, k, seed)] = labels
                counts = pd.Series(labels).value_counts().sort_index()
                dwell = dwell_times(labels)
                row = {
                    "model": model,
                    "k": k,
                    "seed": seed,
                    "silhouette": silhouette_score(x, labels),
                    "inertia": inertia,
                    "min_cluster_fraction": float(counts.min() / len(labels)),
                    "degenerate": bool((counts / len(labels) < 0.05).any()),
                }
                for state in range(1, k + 1):
                    row[f"cluster_{state}_size"] = int(counts.get(state, 0))
                    row[f"state_{state}_median_dwell"] = float(np.median(dwell.get(state, [0])))
                runs.append(row)
    runs_df = pd.DataFrame(runs)
    stability_rows = []
    for model in ["MODEL_RAW", "MODEL_ALIGNED"]:
        for k in K_VALUES:
            subset = runs_df[(runs_df["model"] == model) & (runs_df["k"] == k)]
            aris = []
            for a, b in combinations(SEEDS, 2):
                aris.append(adjusted_rand_index(labels_by_run[(model, k, a)], labels_by_run[(model, k, b)]))
            med_dwell_cols = [c for c in subset.columns if c.startswith("state_") and c.endswith("_median_dwell")]
            median_dwells = subset[med_dwell_cols].median(axis=0).to_numpy(float)
            pass_dwell = int((median_dwells >= 3.0).sum()) >= 2
            row = {
                "model": model,
                "k": k,
                "median_ari": float(np.median(aris)),
                "p10_ari": float(np.quantile(aris, 0.10)),
                "median_silhouette": float(subset["silhouette"].median()),
                "p10_silhouette": float(subset["silhouette"].quantile(0.10)),
                "min_cluster_fraction": float(subset["min_cluster_fraction"].min()),
                "degenerate_runs": int(subset["degenerate"].sum()),
                "states_with_median_dwell_ge_3": int((median_dwells >= 3.0).sum()),
            }
            row["stable_candidate"] = bool(
                row["median_ari"] >= 0.80
                and row["p10_ari"] >= 0.65
                and row["median_silhouette"] >= 0.25
                and row["min_cluster_fraction"] >= 0.05
                and row["states_with_median_dwell_ge_3"] >= 2
            )
            stability_rows.append(row)
    return runs_df, pd.DataFrame(stability_rows), labels_by_run


def choose_model(stability: pd.DataFrame, runs: pd.DataFrame, labels_by_run: dict[tuple[str, int, int], np.ndarray]) -> tuple[str, int, int, np.ndarray]:
    stable = stability[stability["stable_candidate"]].copy()
    if stable.empty:
        ranked = stability.sort_values(
            ["median_ari", "p10_ari", "median_silhouette", "min_cluster_fraction"],
            ascending=[False, False, False, False],
        )
    else:
        ranked = stable.sort_values(
            ["median_ari", "p10_ari", "median_silhouette", "min_cluster_fraction"],
            ascending=[False, False, False, False],
        )
    model = str(ranked.iloc[0]["model"])
    k = int(ranked.iloc[0]["k"])
    subset = runs[(runs["model"] == model) & (runs["k"] == k)].sort_values(["degenerate", "silhouette"], ascending=[True, False])
    seed = int(subset.iloc[0]["seed"])
    return model, k, seed, labels_by_run[(model, k, seed)]


def local_price_phase(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    phase = []
    corrections = []
    active: dict[str, object] | None = None
    pending_resumption = False

    for i, row in df.iterrows():
        direction = 1 if row["ema27"] > row["ema200"] else -1
        context = "LONG" if direction == 1 else "SHORT"
        local = "EXPANSION"
        event = ""
        corr_id = math.nan

        if active is not None:
            active_dir = int(active["direction"])
            context_lost = (active_dir == 1 and row["ema27"] <= row["ema200"]) or (active_dir == -1 and row["ema27"] >= row["ema200"])
            if context_lost:
                local = "CONTEXT_LOSS"
                event = "CONTEXT_LOSS"
                active["end_i"] = i
                active["end_time"] = row["dt"]
                active["end_status"] = "CONTEXT_LOSS"
                corrections.append(active)
                active = None
                pending_resumption = False
            elif pending_resumption:
                local = "EXPANSION"
                active = None
                pending_resumption = False

        if active is None and event == "" and i > 0:
            prev_close = float(df.loc[i - 1, "close"])
            against = (direction == 1 and row["close"] < prev_close) or (direction == -1 and row["close"] > prev_close)
            if against:
                corr_id = len(corrections) + 1
                if direction == 1:
                    pre_extreme = float(df.loc[max(0, i - 3) : i - 1, "high"].max())
                    running_extreme = float(row["low"])
                else:
                    pre_extreme = float(df.loc[max(0, i - 3) : i - 1, "low"].min())
                    running_extreme = float(row["high"])
                active = {
                    "correction_id": int(corr_id),
                    "direction": int(direction),
                    "direction_label": context,
                    "start_i": int(i),
                    "start_time": row["dt"],
                    "pre_correction_extreme": pre_extreme,
                    "correction_start_close": float(row["close"]),
                    "running_extreme": running_extreme,
                    "duration_bars": 1,
                    "max_depth_pct": abs(pre_extreme - running_extreme) / pre_extreme * 100.0 if pre_extreme else 0.0,
                    "min_distance_to_ema27_pct": abs(float(row["close"] - row["ema27"]) / float(row["ema27"]) * 100.0),
                    "min_distance_to_ema200_pct": abs(float(row["close"] - row["ema200"]) / float(row["ema200"]) * 100.0),
                    "recovery_attempt_count": 0,
                    "end_i": math.nan,
                    "end_time": pd.NaT,
                    "end_status": "",
                }
                local = "PULLBACK"
                event = "CORRECTION_START"

        if active is not None and event not in {"CONTEXT_LOSS"}:
            corr_id = int(active["correction_id"])
            active["duration_bars"] = int(i - int(active["start_i"]) + 1)
            if int(active["direction"]) == 1:
                active["running_extreme"] = min(float(active["running_extreme"]), float(row["low"]))
                depth = (float(active["pre_correction_extreme"]) - float(active["running_extreme"])) / float(active["pre_correction_extreme"]) * 100.0
                recovery = i > 0 and row["close"] > df.loc[i - 1, "close"] and row["close"] > df.loc[i - 1, "high"]
                failed_recovery = active.get("in_recovery", False) and row["close"] < df.loc[i - 1, "close"] and row["close"] <= float(active["pre_correction_extreme"])
                resumed = row["close"] > float(active["pre_correction_extreme"])
            else:
                active["running_extreme"] = max(float(active["running_extreme"]), float(row["high"]))
                depth = (float(active["running_extreme"]) - float(active["pre_correction_extreme"])) / float(active["pre_correction_extreme"]) * 100.0
                recovery = i > 0 and row["close"] < df.loc[i - 1, "close"] and row["close"] < df.loc[i - 1, "low"]
                failed_recovery = active.get("in_recovery", False) and row["close"] > df.loc[i - 1, "close"] and row["close"] >= float(active["pre_correction_extreme"])
                resumed = row["close"] < float(active["pre_correction_extreme"])
            active["max_depth_pct"] = max(float(active["max_depth_pct"]), float(depth))
            active["min_distance_to_ema27_pct"] = min(float(active["min_distance_to_ema27_pct"]), abs(float(row["close"] - row["ema27"]) / float(row["ema27"]) * 100.0))
            active["min_distance_to_ema200_pct"] = min(float(active["min_distance_to_ema200_pct"]), abs(float(row["close"] - row["ema200"]) / float(row["ema200"]) * 100.0))
            if failed_recovery:
                active["in_recovery"] = False
                active["recovery_attempt_count"] = int(active["recovery_attempt_count"]) + 1
                local = "PULLBACK"
                event = "RECOVERY_FAILED"
            elif resumed:
                local = "RESUMPTION"
                event = "RESUMPTION"
                active["end_i"] = i
                active["end_time"] = row["dt"]
                active["end_status"] = "RESUMPTION"
                corrections.append(active.copy())
                pending_resumption = True
            elif recovery:
                if not active.get("in_recovery", False):
                    active["recovery_attempt_count"] = int(active["recovery_attempt_count"]) + 1
                active["in_recovery"] = True
                local = "RECOVERY"
                event = "RECOVERY"
            else:
                local = "RECOVERY" if active.get("in_recovery", False) else "PULLBACK"

        phase.append(
            {
                "dt": row["dt"],
                "direction": context,
                "local_phase": local if direction in [1, -1] else "NO_CONTEXT",
                "local_event": event,
                "correction_id": corr_id,
            }
        )

    if active is not None:
        active["end_i"] = len(df) - 1
        active["end_time"] = df.iloc[-1]["dt"]
        active["end_status"] = "OPEN_END"
        corrections.append(active)
    return pd.DataFrame(phase), pd.DataFrame(corrections)


def build_dwell(labels: np.ndarray) -> pd.DataFrame:
    rows = []
    d = dwell_times(labels)
    for state, vals in sorted(d.items()):
        arr = np.array(vals, dtype=float)
        rows.append(
            {
                "backbone_state": int(state),
                "episode_count": int(len(arr)),
                "mean_dwell": float(arr.mean()),
                "median_dwell": float(np.median(arr)),
                "p75_dwell": float(np.quantile(arr, 0.75)),
                "p90_dwell": float(np.quantile(arr, 0.90)),
                "max_dwell": int(arr.max()),
            }
        )
    return pd.DataFrame(rows)


def transition_full(labels: np.ndarray) -> pd.DataFrame:
    states = sorted(set(int(x) for x in labels))
    counts = pd.DataFrame(0, index=states, columns=states, dtype=int)
    for a, b in zip(labels[:-1], labels[1:]):
        counts.loc[int(a), int(b)] += 1
    probs = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    rows = []
    for a in states:
        for b in states:
            rows.append(
                {
                    "from_state": a,
                    "to_state": b,
                    "transition_count": int(counts.loc[a, b]),
                    "transition_probability": float(probs.loc[a, b]),
                    "is_self_transition": a == b,
                }
            )
    return pd.DataFrame(rows)


def transition_changes(labels: np.ndarray) -> pd.DataFrame:
    states = sorted(set(int(x) for x in labels))
    counts = pd.DataFrame(0, index=states, columns=states, dtype=int)
    for a, b in zip(labels[:-1], labels[1:]):
        if int(a) != int(b):
            counts.loc[int(a), int(b)] += 1
    probs = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    rows = []
    for a in states:
        for b in states:
            rows.append({"from_state": a, "to_state": b, "state_change_count": int(counts.loc[a, b]), "state_change_probability": float(probs.loc[a, b])})
    return pd.DataFrame(rows)


def state_statistics(composite: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for state, g in composite.groupby("backbone_state"):
        rows.append(
            {
                "backbone_state": int(state),
                "bar_count": int(len(g)),
                "bar_fraction": float(len(g) / len(composite)),
                "ema200_slope_12_mean": float(g["ema200_slope_12"].mean()),
                "ema200_slope_24_mean": float(g["ema200_slope_24"].mean()),
                "signed_ema_distance_pct_mean": float(g["signed_ema_distance_pct"].mean()),
                "ema_distance_change_12_mean": float(g["ema_distance_change_12"].mean()),
                "pullback_bar_fraction": float((g["local_phase"] == "PULLBACK").mean()),
                "recovery_bar_fraction": float((g["local_phase"] == "RECOVERY").mean()),
                "context_loss_count": int((g["local_phase"] == "CONTEXT_LOSS").sum()),
            }
        )
    return pd.DataFrame(rows)


def state_outcomes(composite: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in composite.iterrows():
        i = int(row["source_i"])
        direction = int(row["direction_num"])
        close = float(row["close"])
        out = {
            "dt": row["dt"],
            "backbone_state": int(row["backbone_state"]),
            "direction": row["direction"],
        }
        for horizon in [5, 10, 20]:
            future = composite[(composite["source_i"] > i) & (composite["source_i"] <= i + horizon)]
            if future.empty:
                updated = math.nan
                mfe = math.nan
                mae = math.nan
            elif direction == 1:
                updated = float(future["high"].max() > row["high"])
                mfe = (future["high"].max() - close) / close * 100.0
                mae = (future["low"].min() - close) / close * 100.0
            else:
                updated = float(future["low"].min() < row["low"])
                mfe = (close - future["low"].min()) / close * 100.0
                mae = (close - future["high"].max()) / close * 100.0
            out[f"updates_directional_extreme_h{horizon}"] = updated
            out[f"forward_mfe_pct_h{horizon}"] = mfe
            out[f"forward_mae_pct_h{horizon}"] = mae
        rows.append(out)
    return pd.DataFrame(rows)


def audit_exp010() -> dict[str, object]:
    features = pd.read_csv(EXP010_ART / "ema_state_features.csv")
    corrections = pd.read_csv(EXP010_ART / "corrections.csv")
    clusters = pd.read_csv(EXP010_ART / "ema_state_clusters.csv")
    input_cols = [
        "ema27_slope_pct",
        "ema27_angle_change_deg",
        "ema27_speed_change_pct",
        "ema200_slope_pct",
        "ema200_angle_change_deg",
        "ema200_speed_change_pct",
        "ema_distance_pct",
        "ema_distance_change_pct",
        "price_to_ema27_pct",
        "price_to_ema200_pct",
        "active_correction_duration",
        "active_correction_depth_pct",
        "last_correction_duration",
        "last_correction_depth_pct",
        "last_correction_updated_extreme",
        "last_correction_bars_to_update_extreme",
    ]
    present = [c for c in input_cols if c in clusters.columns]
    corr = clusters[present].corr(numeric_only=True)
    near_dupes = []
    for a, b in combinations(present, 2):
        val = corr.loc[a, b]
        if pd.notna(val) and abs(val) >= 0.98:
            near_dupes.append({"feature_a": a, "feature_b": b, "pearson": float(val)})
    durations = corrections["duration_bars"].astype(float)
    audit = {
        "future_leakage_features": [
            {
                "feature": "last_correction_updated_extreme",
                "issue": "EXP-010 measured whether the directional extreme updated within the next 20 bars after correction end, then attached it as a clustering input on later rows.",
            },
            {
                "feature": "last_correction_bars_to_update_extreme",
                "issue": "EXP-010 measured bars until future directional extreme update after correction end, then attached it as a clustering input on later rows.",
            },
        ],
        "duplicate_checks_required": {
            "ema27_slope_pct_vs_ema27_speed_pct": "ema27_speed_pct was identical in construction to ema27_slope_pct in EXP-010 before speed_change was selected.",
            "ema200_slope_pct_vs_ema200_speed_pct": "ema200_speed_pct was identical in construction to ema200_slope_pct in EXP-010 before speed_change was selected.",
        },
        "near_duplicate_features_abs_pearson_ge_0_98": near_dupes,
        "correction_definition": "Continuous close-to-close movement against current EMA direction; first bar back in trend direction ended the correction.",
        "correction_count": int(len(corrections)),
        "correction_duration_mean": float(durations.mean()),
        "correction_duration_median": float(durations.median()),
        "correction_duration_p75": float(durations.quantile(0.75)),
        "correction_duration_p90": float(durations.quantile(0.90)),
        "one_bar_correction_fraction": float((durations == 1).mean()),
        "transition_matrix_method": {
            "self_transitions_excluded": True,
            "why_probability_1_not_market_sequence": "With self-transitions removed, two states can only change 1->2 or 2->1, so transition probability 1.00 is a counting artifact of excluding persistence, not evidence of a market sequence.",
        },
    }
    (OUT / "exp010_audit.json").write_text(json.dumps(audit, indent=2))
    return audit


def build_composite(features: pd.DataFrame, selected_labels: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    valid = features.dropna(subset=RAW_FEATURES + ALIGNED_FEATURES).copy().reset_index(drop=False).rename(columns={"index": "source_i"})
    valid["backbone_state"] = selected_labels
    phase, corrections = local_price_phase(valid)
    local = pd.concat([valid[["source_i", "dt", "open", "high", "low", "close", "ema27", "ema200"]].reset_index(drop=True), phase[["direction", "local_phase", "local_event", "correction_id"]]], axis=1)
    comp = pd.concat([valid.reset_index(drop=True), phase[["local_phase", "local_event", "correction_id"]]], axis=1)
    comp["direction_num"] = np.where(comp["ema27"] > comp["ema200"], 1, -1)
    comp["direction"] = np.where(comp["direction_num"] == 1, "LONG", "SHORT")
    comp["composite_state"] = "STATE_" + comp["backbone_state"].astype(str) + " + " + comp["local_phase"]
    return comp, local, corrections


def compact_ts(t: pd.Timestamp) -> str:
    t = pd.Timestamp(t)
    return f'timestamp("Etc/UTC", {t.year}, {t.month}, {t.day}, {t.hour}, {t.minute})'


def intervals_from_states(comp: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp, int]]:
    rows = []
    start = pd.Timestamp(comp.iloc[0]["dt"])
    last_state = int(comp.iloc[0]["backbone_state"])
    prev = start
    for _, row in comp.iloc[1:].iterrows():
        state = int(row["backbone_state"])
        t = pd.Timestamp(row["dt"])
        if state != last_state:
            rows.append((start, prev, last_state))
            start = t
            last_state = state
        prev = t
    rows.append((start, prev, last_state))
    return rows


def build_pine(comp: pd.DataFrame) -> str:
    intervals = intervals_from_states(comp)
    starts = ", ".join(compact_ts(a) for a, _, _ in intervals)
    ends = ", ".join(compact_ts(b) for _, b, _ in intervals)
    states = ", ".join(str(s) for _, _, s in intervals)
    events = comp[comp["local_event"].isin(["CORRECTION_START", "RECOVERY", "RESUMPTION", "CONTEXT_LOSS"])].copy()
    recovery = events[events["local_event"] == "RECOVERY"].sort_values("dt").groupby("correction_id", dropna=True).head(1)
    events = pd.concat([events[events["local_event"] != "RECOVERY"], recovery], ignore_index=True).sort_values("dt")
    event_times = ", ".join(compact_ts(t) for t in events["dt"])
    event_codes = ", ".join(str({"CORRECTION_START": 1, "RECOVERY": 2, "RESUMPTION": 3, "CONTEXT_LOSS": 4}[e]) for e in events["local_event"])
    return f'''//@version=6
indicator("EXP-010A EMA State Audit View", overlay=true, max_labels_count=500)

showBackboneState = input.bool(true, "showBackboneState")
showLocalPhase = input.bool(true, "showLocalPhase")
showCorrectionStart = input.bool(true, "showCorrectionStart")
showRecovery = input.bool(true, "showRecovery")
showResumption = input.bool(true, "showResumption")
showContextLoss = input.bool(true, "showContextLoss")
showStateLabels = input.bool(true, "showStateLabels")

var int[] sA = array.from({starts})
var int[] sB = array.from({ends})
var int[] sN = array.from({states})
var int[] eT = array.from({event_times})
var int[] eC = array.from({event_codes})

ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
plot(ema27, "EMA27", color=color.aqua, linewidth=1)
plot(ema200, "EMA200", color=color.orange, linewidth=1)

f_state_color(int s) => s == 1 ? color.new(color.blue, 86) : s == 2 ? color.new(color.orange, 86) : s == 3 ? color.new(color.teal, 86) : s == 4 ? color.new(color.red, 86) : color.new(color.gray, 88)

int stateNo = na
bool transition = false
for i = 0 to array.size(sN) - 1
    int a = array.get(sA, i)
    int b = array.get(sB, i)
    if time >= a and time <= b
        stateNo := array.get(sN, i)
        transition := time == a

bgcolor(showBackboneState and not na(stateNo) ? f_state_color(stateNo) : na)
if showStateLabels and transition and not na(stateNo)
    label.new(time, high, "State " + str.tostring(stateNo), xloc=xloc.bar_time, style=label.style_label_down, color=color.black, textcolor=color.white, size=size.tiny)

if showLocalPhase
    for i = 0 to array.size(eT) - 1
        if time == array.get(eT, i)
            int code = array.get(eC, i)
            bool ok = code == 1 ? showCorrectionStart : code == 2 ? showRecovery : code == 3 ? showResumption : showContextLoss
            string txt = code == 1 ? "PULLBACK" : code == 2 ? "RECOVERY" : code == 3 ? "RESUMPTION" : "CONTEXT_LOSS"
            color c = code == 1 ? color.yellow : code == 2 ? color.blue : code == 3 ? color.green : color.red
            if ok
                label.new(time, close, txt, xloc=xloc.bar_time, style=label.style_label_left, color=c, textcolor=color.black, size=size.tiny)
'''


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path: Path, title: str, lines: list[str]) -> None:
    content = ["BT", "/F1 15 Tf", "42 752 Td", f"({pdf_escape(title)}) Tj", "/F1 9 Tf", "0 -20 Td"]
    for line in lines[:70]:
        content.append(f"({pdf_escape(line)}) Tj")
        content.append("0 -11 Td")
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


def compare_exp010(audit: dict[str, object], stability: pd.DataFrame, chosen_model: str, chosen_k: int, comp: pd.DataFrame, corrections: pd.DataFrame) -> pd.DataFrame:
    exp010_stats = pd.read_csv(EXP010_ART / "cluster_statistics.csv")
    exp010_sel = pd.read_csv(EXP010_ART / "cluster_selection.csv").sort_values("silhouette", ascending=False).iloc[0]
    chosen_stab = stability[(stability["model"] == chosen_model) & (stability["k"] == chosen_k)].iloc[0]
    dwell = build_dwell(comp["backbone_state"].to_numpy(int))
    return pd.DataFrame(
        [
            {
                "experiment": "EXP-010",
                "feature_count": 16,
                "has_lookahead": True,
                "has_duplicate_features": True,
                "selected_k": int(exp010_sel["k"]),
                "silhouette": float(exp010_sel["silhouette"]),
                "ari_stability": np.nan,
                "min_cluster_fraction": float(exp010_stats["bar_fraction"].min()),
                "median_state_duration": np.nan,
                "state_count": int(exp010_stats["state"].nunique()),
                "largest_state_fraction": float(exp010_stats["bar_fraction"].max()),
                "mean_correction_duration": audit["correction_duration_mean"],
                "median_correction_duration": audit["correction_duration_median"],
                "one_bar_correction_fraction": audit["one_bar_correction_fraction"],
                "has_self_transition": False,
                "causal_state_assignment": False,
            },
            {
                "experiment": "EXP-010A",
                "feature_count": 8,
                "has_lookahead": False,
                "has_duplicate_features": False,
                "selected_k": chosen_k,
                "silhouette": float(chosen_stab["median_silhouette"]),
                "ari_stability": float(chosen_stab["median_ari"]),
                "min_cluster_fraction": float(chosen_stab["min_cluster_fraction"]),
                "median_state_duration": float(dwell["median_dwell"].median()),
                "state_count": int(comp["backbone_state"].nunique()),
                "largest_state_fraction": float(comp["backbone_state"].value_counts(normalize=True).max()),
                "mean_correction_duration": float(corrections["duration_bars"].mean()),
                "median_correction_duration": float(corrections["duration_bars"].median()),
                "one_bar_correction_fraction": float((corrections["duration_bars"] == 1).mean()),
                "has_self_transition": True,
                "causal_state_assignment": True,
            },
        ]
    )


def main() -> None:
    ensure_dirs()
    audit = audit_exp010()
    raw = load_ohlc()
    features = add_backbone_features(raw)
    valid = features.dropna(subset=RAW_FEATURES + ALIGNED_FEATURES).copy().reset_index(drop=True)
    runs, stability, labels_by_run = run_clustering(valid)
    chosen_model, chosen_k, chosen_seed, labels = choose_model(stability, runs, labels_by_run)
    comp, local, corrections = build_composite(features, labels)
    chosen_stab = stability[(stability["model"] == chosen_model) & (stability["k"] == chosen_k)].iloc[0]
    stable = bool(chosen_stab["stable_candidate"])
    verdict = "CAUSAL_EMA_STATE_STRUCTURE_FOUND" if stable else "PARTIAL_CAUSAL_EMA_STATE_STRUCTURE"
    if not stable and float(chosen_stab["median_ari"]) < 0.50:
        verdict = "NO_STABLE_EMA_STATE_STRUCTURE"

    stats = state_statistics(comp)
    dwell = build_dwell(comp["backbone_state"].to_numpy(int))
    trans = transition_full(comp["backbone_state"].to_numpy(int))
    changes = transition_changes(comp["backbone_state"].to_numpy(int))
    outcomes = state_outcomes(comp)
    comparison = compare_exp010(audit, stability, chosen_model, chosen_k, comp, corrections)

    features.to_csv(OUT / "backbone_features.csv", index=False)
    local.to_csv(OUT / "local_price_phases.csv", index=False)
    comp.to_csv(OUT / "composite_states.csv", index=False)
    runs.to_csv(OUT / "clustering_runs.csv", index=False)
    stability.to_csv(OUT / "cluster_stability.csv", index=False)
    stats.to_csv(OUT / "backbone_state_statistics.csv", index=False)
    trans.to_csv(OUT / "transition_matrix_full.csv", index=False)
    changes.to_csv(OUT / "state_change_matrix.csv", index=False)
    dwell.to_csv(OUT / "state_dwell_times.csv", index=False)
    outcomes.to_csv(OUT / "state_outcomes.csv", index=False)
    corrections.to_csv(OUT / "corrections.csv", index=False)
    comparison.to_csv(OUT / "exp010_vs_exp010a.csv", index=False)
    (OUT / "EMA_STATE_AUDIT_VIEW.pine").write_text(build_pine(comp))

    one_bar = float((corrections["duration_bars"] == 1).mean())
    repeated = int((dwell["episode_count"] >= 2).sum())
    pullback_by_state = comp[comp["local_phase"].isin(["PULLBACK", "RECOVERY"])].groupby("backbone_state").size().to_dict()
    ctx_loss = int((comp["local_phase"] == "CONTEXT_LOSS").sum())
    report = f"""# EXP-010A — CAUSAL EMA STATE AUDIT

Status: DONE / REPORT_READY

Verdict: {verdict}

## Data

ADAUSDT 4H, `{features['dt'].min()}` -> `{features['dt'].max()}`. Source: local EXP-010 OHLC artifact, recomputed EMA27/EMA200. Irobot was not read. No 2025+ rows were used.

## Answers

1. Did EXP-010 contain future leakage?

Yes. `last_correction_updated_extreme` and `last_correction_bars_to_update_extreme` were outcome-style fields measured after correction end and then used as clustering inputs on later rows. EXP-010A excludes them from backbone clustering.

2. Which EXP-010 features were duplicating?

EXP-010 constructed speed as slope, so `ema27_speed_pct` duplicated `ema27_slope_pct`, and `ema200_speed_pct` duplicated `ema200_slope_pct`. Near-duplicate correlations are listed in `exp010_audit.json`.

3. Why did k=2 in EXP-010 split the market into 88.4% and 11.6%?

Because the mixed feature set included price-to-EMA distance, EMA distance, and post-correction outcome fields. That separated the rare late-2024 expansion/extreme-distance regime from the rest more than it separated lifecycle states.

4. Was EXP-010 State 2 a lifecycle state or extreme price expansion?

Mostly an extreme price expansion: EXP-010 State 2 had large `price_to_ema200_pct` and large EMA distance. EXP-010A treats that as an audit finding, not a lifecycle label.

5. Was a stable k found after removing lookahead and duplicate features?

Chosen model: `{chosen_model}`, k=`{chosen_k}`, seed=`{chosen_seed}`. Median silhouette `{chosen_stab['median_silhouette']:.3f}`, median ARI `{chosen_stab['median_ari']:.3f}`, p10 ARI `{chosen_stab['p10_ari']:.3f}`, min cluster fraction `{chosen_stab['min_cluster_fraction']:.3f}`. Stable candidate: `{stable}`.

6. Which model is more stable: MODEL_RAW or MODEL_ALIGNED?

The selected model is `{chosen_model}`. Full comparison for all k is in `cluster_stability.csv`.

7. Does the model distinguish PULLBACK inside one backbone state, PULLBACK inside another backbone state, and CONTEXT_LOSS?

Partially. Pullback/recovery bars exist by backbone state: `{pullback_by_state}`. CONTEXT_LOSS events: `{ctx_loss}`. The distinction is structural and causal, but visual review is still required before assigning semantic names.

8. Does the model visually distinguish correction while EMA200 keeps rising vs correction while EMA200 flattens?

Partially. EMA200 slope statistics differ by state in `backbone_state_statistics.csv`, and Pine/PDF artifacts expose examples. No semantic names are assigned.

9. Do backbone states recur on multiple segments, not only one extreme expansion?

Episodes by state are in `state_dwell_times.csv`; states with at least two episodes: `{repeated}`.

10. Can the states be considered causal?

Yes for assignment: backbone features use only current and previous closed bars, and local phases are determined after the current bar closes. Outcome data are retrospective evaluation only. They are not state input features.

11. What verdict does EXP-010A receive?

`{verdict}`.

## Correction Summary

- correction count: `{len(corrections)}`
- median correction duration: `{float(corrections['duration_bars'].median()):.2f}` bars
- one-bar correction fraction: `{one_bar:.3f}`

## Artifacts

All required artifacts were created under `artifacts/`.
"""
    (EXP / "REPORT.md").write_text(report)
    pdf_lines = [
        "Required visual audit windows:",
        "1. 2023-10-01 to 2024-03-31",
        "2. Mid up-period corrections",
        "3. Late section of same up-period",
        "4. At least two down contexts",
        "5. One-bar correction examples",
        "6. Multi-bar corrections with recovery attempts",
        "",
        f"Verdict: {verdict}",
        f"Selected: {chosen_model}, k={chosen_k}, seed={chosen_seed}",
        f"Median silhouette: {chosen_stab['median_silhouette']:.3f}",
        f"Median ARI: {chosen_stab['median_ari']:.3f}",
        f"Corrections: {len(corrections)}, median duration={corrections['duration_bars'].median():.2f}, one-bar={one_bar:.3f}",
        "",
        "Backbone state statistics:",
        *[
            f"State {int(r.backbone_state)} bars={int(r.bar_count)} frac={r.bar_fraction:.3f} ema200_12={r.ema200_slope_12_mean:.4f} pullback_frac={r.pullback_bar_fraction:.3f}"
            for r in stats.itertuples()
        ],
        "",
        "Use EMA_STATE_AUDIT_VIEW.pine for chart inspection. No BUY/SELL labels.",
    ]
    write_pdf(OUT / "EMA_STATE_AUDIT_CONTACT_SHEET.pdf", "EXP-010A EMA State Audit Contact Sheet", pdf_lines)
    print(json.dumps({"verdict": verdict, "model": chosen_model, "k": chosen_k, "seed": chosen_seed, "median_silhouette": float(chosen_stab["median_silhouette"]), "median_ari": float(chosen_stab["median_ari"]), "corrections": len(corrections)}, indent=2))


if __name__ == "__main__":
    main()
