#!/usr/bin/env python3
"""EXP-005C: OHLC-only taxonomy of matched non-major outcomes.

Self-contained on purpose: the project environment has numpy/pandas but not
sklearn/scipy/matplotlib. This script avoids external ML/plot dependencies.
"""

from __future__ import annotations

import csv
import math
import random
import statistics
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES"
EXP_B = EXP / "EXP-005B_SELECTION_BIAS_TEST/artifacts"
OUT = EXP / "EXP-005C_TAXONOMY_OF_MATCHED_OUTCOMES/artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

SYMBOL = "ADAUSDT"
TIMEFRAME = "4H"
RESEARCH_END = pd.Timestamp("2025-07-01 00:00")
HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")
HOLDOUT_END = pd.Timestamp("2026-07-01 00:00")
HORIZONS = [10, 20, 30, 60]
PRIMARY_H = 30
MAJOR_THRESHOLD_PCT = 0.25
RANDOM_SEED = 20260712


CORE_FEATURES = [
    "signed_close_return_atr",
    "mfe_atr",
    "mae_atr",
    "signed_efficiency",
    "net_to_path_ratio",
    "return_sign_changes",
    "number_of_local_pivots",
    "high_low_range_atr",
    "realized_volatility_ratio",
    "atr_decay",
    "overlap_ratio",
    "fraction_bars_in_event_direction",
    "longest_same_direction_run",
    "time_to_mfe",
    "time_to_mae",
]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df.sort_values("dt").reset_index(drop=True)
    prev_close = df["close"].shift(1).fillna(df["close"])
    df["true_range"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(),
            (df["high"] - prev_close).abs().to_numpy(),
            (df["low"] - prev_close).abs().to_numpy(),
        ]
    )
    df["body"] = (df["close"] - df["open"]).abs()
    df["range"] = df["high"] - df["low"]
    df["bar_dir"] = np.sign(df["close"] - df["open"]).astype(int)
    return df[df["dt"] <= RESEARCH_END].copy().reset_index(drop=True)


def sign_for(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def atr_at(df: pd.DataFrame, idx: int, n: int = 14) -> float:
    start = max(0, idx - n + 1)
    value = float(df.loc[start:idx, "true_range"].mean())
    return value if value > 0 else 1e-12


def local_pivots(values: list[float]) -> int:
    count = 0
    for i in range(1, len(values) - 1):
        if values[i] > values[i - 1] and values[i] > values[i + 1]:
            count += 1
        elif values[i] < values[i - 1] and values[i] < values[i + 1]:
            count += 1
    return count


def longest_run(items: list[int], target: int | None = None) -> int:
    best = 0
    cur = 0
    prev = None
    for item in items:
        if item == 0:
            cur = 0
            prev = None
            continue
        if target is not None:
            cur = cur + 1 if item == target else 0
        else:
            cur = cur + 1 if item == prev else 1
            prev = item
        best = max(best, cur)
    return best


def outcome_features_for_event(
    df: pd.DataFrame,
    event_id: str,
    timestamp: str,
    direction: str,
    matched_group_id: str,
    horizon: int,
    event_type: str,
) -> dict:
    idx_map = {str(t): i for i, t in enumerate(df["open_dt"])}
    idx = idx_map[timestamp]
    t0 = df.iloc[idx]
    close0 = float(t0["close"])
    atr0 = atr_at(df, idx)
    pre30 = df.iloc[max(0, idx - 30) : idx]
    pre10 = df.iloc[max(0, idx - 10) : idx]
    pre60 = df.iloc[max(0, idx - 60) : idx]
    win = df.iloc[idx + 1 : min(len(df), idx + 1 + horizon)].copy()
    if len(win) < horizon:
        raise ValueError(f"not enough research bars after {event_id} for H={horizon}")

    sgn = sign_for(direction)
    closes = win["close"].to_numpy(dtype=float)
    highs = win["high"].to_numpy(dtype=float)
    lows = win["low"].to_numpy(dtype=float)
    opens = win["open"].to_numpy(dtype=float)
    ranges = np.maximum(win["range"].to_numpy(dtype=float), 1e-12)
    bodies = win["body"].to_numpy(dtype=float)
    trs = win["true_range"].to_numpy(dtype=float)
    step_prices = np.r_[close0, closes]
    diffs = np.diff(step_prices)
    returns = diffs / step_prices[:-1]
    signed_close_move = sgn * (closes[-1] - close0)
    signed_close_return_pct = signed_close_move / close0
    favorable = (highs - close0) if direction == "LONG" else (close0 - lows)
    adverse = (close0 - lows) if direction == "LONG" else (highs - close0)
    mfe = float(np.max(favorable))
    mae = float(np.max(adverse))
    signed_mfe_pct = mfe / close0
    signed_mae_pct = -mae / close0
    mfe_i = int(np.argmax(favorable)) + 1
    mae_i = int(np.argmax(adverse)) + 1
    path = float(np.sum(np.abs(diffs)))
    total_path_pct = path / close0
    efficiency = abs(closes[-1] - close0) / path if path else 0.0
    signed_eff = signed_close_move / path if path else 0.0
    net_to_path = signed_close_move / path if path else 0.0
    ret_signs = [int(np.sign(x)) for x in diffs if abs(x) > 1e-12]
    sign_changes = sum(1 for a, b in zip(ret_signs, ret_signs[1:]) if a != b)
    pivots = local_pivots(list(closes))
    hl_range = float(np.max(highs) - np.min(lows))
    rv = float(np.std(returns, ddof=0)) if len(returns) else 0.0
    pre30_ret = pre30["close"].pct_change().dropna().to_numpy(dtype=float)
    pre10_ret = pre10["close"].pct_change().dropna().to_numpy(dtype=float)
    pre60_ret = pre60["close"].pct_change().dropna().to_numpy(dtype=float)
    pre30_rv = float(np.std(pre30_ret, ddof=0)) if len(pre30_ret) else 0.0
    pre10_rv = float(np.std(pre10_ret, ddof=0)) if len(pre10_ret) else 0.0
    pre60_rv = float(np.std(pre60_ret, ddof=0)) if len(pre60_ret) else 0.0
    rv_ratio = rv / pre30_rv if pre30_rv else 0.0
    pre30_range = float(pre30["high"].max() - pre30["low"].min()) if len(pre30) else 0.0
    range_expansion = hl_range / pre30_range if pre30_range else 0.0
    pre10_range = float(pre10["high"].max() - pre10["low"].min()) if len(pre10) else 0.0
    pre60_range = float(pre60["high"].max() - pre60["low"].min()) if len(pre60) else 0.0
    range_expansion_10 = hl_range / pre10_range if pre10_range else 0.0
    range_expansion_60 = hl_range / pre60_range if pre60_range else 0.0

    half = max(1, len(win) // 2)
    rolling_range_contraction = (
        float(win["range"].iloc[half:].mean()) / float(win["range"].iloc[:half].mean())
        if float(win["range"].iloc[:half].mean()) > 0
        else 0.0
    )
    atr_decay = float(np.mean(trs[half:]) / np.mean(trs[:half])) if np.mean(trs[:half]) else 0.0
    rv_first = float(np.std(returns[: max(1, len(returns) // 2)], ddof=0))
    rv_last = float(np.std(returns[max(1, len(returns) // 2) :], ddof=0))
    realized_volatility_decay = rv_last / rv_first if rv_first else 0.0
    overlaps = []
    inside = 0
    outside = 0
    for i in range(1, len(win)):
        lo = max(float(lows[i]), float(lows[i - 1]))
        hi = min(float(highs[i]), float(highs[i - 1]))
        overlaps.append(max(0.0, hi - lo))
        if highs[i] <= highs[i - 1] and lows[i] >= lows[i - 1]:
            inside += 1
        if highs[i] >= highs[i - 1] and lows[i] <= lows[i - 1]:
            outside += 1
    avg_range = float(np.mean(ranges))
    overlap_ratio = float(np.mean(overlaps)) / avg_range if avg_range else 0.0
    body_range = bodies / ranges
    upper_wicks = (highs - np.maximum(opens, closes)) / ranges
    lower_wicks = (np.minimum(opens, closes) - lows) / ranges
    candle_dirs = np.sign(closes - opens).astype(int)
    close_dirs = np.sign(diffs).astype(int)
    target = sgn
    event_dir_fraction = float(np.mean(close_dirs == target))
    body_dir_fraction = float(np.mean(candle_dirs == target))
    close_side_fraction = (
        float(np.mean(closes >= close0)) if direction == "LONG" else float(np.mean(closes <= close0))
    )
    favorable_break = np.where(favorable > 0)[0]
    adverse_break = np.where(adverse > 0)[0]
    bars_until_fav = int(favorable_break[0] + 1) if len(favorable_break) else horizon + 1
    bars_until_adv = int(adverse_break[0] + 1) if len(adverse_break) else horizon + 1
    initial_signed = sgn * (closes[0] - close0)
    if horizon == 60:
        after30 = df.iloc[idx + 31 : idx + 61]
        if len(after30):
            if direction == "LONG":
                delayed_mfe = (float(after30["high"].max()) - close0) / close0
                delayed_mae = (close0 - float(after30["low"].min())) / close0
            else:
                delayed_mfe = (close0 - float(after30["low"].min())) / close0
                delayed_mae = (float(after30["high"].max()) - close0) / close0
        else:
            delayed_mfe = 0.0
            delayed_mae = 0.0
    else:
        delayed_mfe = 0.0
        delayed_mae = 0.0

    signed_return = signed_close_return_pct
    final_direction = "EVENT_DIRECTION" if signed_return > 0 else "AGAINST_EVENT_DIRECTION" if signed_return < 0 else "FLAT"
    return {
        "event_id": event_id,
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "timestamp": timestamp,
        "direction": direction,
        "matched_group_id": matched_group_id,
        "event_type": event_type,
        "horizon": horizon,
        "signed_close_return_pct": signed_close_return_pct,
        "signed_close_return_atr": signed_close_move / atr0,
        "mfe_pct": signed_mfe_pct,
        "mfe_atr": mfe / atr0,
        "mae_pct": signed_mae_pct,
        "mae_atr": -mae / atr0,
        "final_direction": final_direction,
        "efficiency_ratio": efficiency,
        "signed_efficiency": signed_eff,
        "total_path_pct": total_path_pct,
        "total_path_atr": path / atr0,
        "net_to_path_ratio": net_to_path,
        "return_sign_changes": sign_changes,
        "swing_direction_changes": pivots,
        "number_of_local_pivots": pivots,
        "high_low_range_pct": hl_range / close0,
        "high_low_range_atr": hl_range / atr0,
        "range_expansion_vs_pre_event": range_expansion,
        "range_expansion_vs_pre10": range_expansion_10,
        "range_expansion_vs_pre60": range_expansion_60,
        "realized_volatility": rv,
        "realized_volatility_ratio": rv_ratio,
        "realized_volatility_ratio_pre10": rv / pre10_rv if pre10_rv else 0.0,
        "realized_volatility_ratio_pre60": rv / pre60_rv if pre60_rv else 0.0,
        "rolling_range_contraction": rolling_range_contraction,
        "atr_decay": atr_decay,
        "realized_volatility_decay": realized_volatility_decay,
        "inside_bar_fraction": inside / max(1, len(win) - 1),
        "overlap_ratio": overlap_ratio,
        "body_range_ratio": float(np.mean(body_range)),
        "mean_body_to_range": float(np.mean(body_range)),
        "median_body_to_range": float(np.median(body_range)),
        "upper_wick_fraction": float(np.mean(upper_wicks)),
        "lower_wick_fraction": float(np.mean(lower_wicks)),
        "directional_body_fraction": body_dir_fraction,
        "large_body_fraction": float(np.mean(body_range >= 0.60)),
        "doji_fraction": float(np.mean(body_range <= 0.10)),
        "outside_bar_fraction": outside / max(1, len(win) - 1),
        "fraction_bars_in_event_direction": event_dir_fraction,
        "longest_same_direction_run": longest_run([int(x) for x in close_dirs], target=target),
        "close_above_or_below_event_price_fraction": close_side_fraction,
        "time_to_mfe": mfe_i,
        "time_to_mae": mae_i,
        "time_to_new_extreme": min(mfe_i, horizon + 1),
        "initial_move_in_expected_direction": int(initial_signed > 0),
        "initial_move_against_expected_direction": int(initial_signed < 0),
        "bars_until_first_favorable_break": bars_until_fav,
        "bars_until_first_adverse_break": bars_until_adv,
        "mfe_before_mae": int(mfe_i < mae_i),
        "mae_before_mfe": int(mae_i < mfe_i),
        "delayed_mfe_after_30": delayed_mfe,
        "delayed_mae_after_30": -delayed_mae,
        "delayed_major_move_flag": int(horizon == 60 and delayed_mfe >= MAJOR_THRESHOLD_PCT),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def wide_features(features: pd.DataFrame) -> pd.DataFrame:
    id_cols = ["event_id", "symbol", "timeframe", "timestamp", "direction", "matched_group_id", "event_type"]
    rows = []
    for event_id, group in features.groupby("event_id"):
        base = group.iloc[0][id_cols].to_dict()
        for _, row in group.iterrows():
            h = int(row["horizon"])
            for col, value in row.items():
                if col in id_cols or col == "horizon":
                    continue
                base[f"{col}_h{h}"] = value
        rows.append(base)
    return pd.DataFrame(rows)


def feature_summary(df: pd.DataFrame) -> pd.DataFrame:
    numeric = df.select_dtypes(include=[np.number])
    rows = []
    for col in numeric.columns:
        vals = numeric[col].dropna().to_numpy(dtype=float)
        rows.append(
            {
                "feature": col,
                "count": len(vals),
                "mean": float(np.mean(vals)) if len(vals) else "",
                "std": float(np.std(vals)) if len(vals) else "",
                "median": float(np.median(vals)) if len(vals) else "",
                "p10": float(np.percentile(vals, 10)) if len(vals) else "",
                "p25": float(np.percentile(vals, 25)) if len(vals) else "",
                "p75": float(np.percentile(vals, 75)) if len(vals) else "",
                "p90": float(np.percentile(vals, 90)) if len(vals) else "",
                "min": float(np.min(vals)) if len(vals) else "",
                "max": float(np.max(vals)) if len(vals) else "",
                "missing_count": int(df[col].isna().sum()),
                "constant": int(len(set(np.round(vals, 12))) <= 1) if len(vals) else 1,
            }
        )
    return pd.DataFrame(rows)


def robust_scale(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    med = np.median(x, axis=0)
    q25 = np.percentile(x, 25, axis=0)
    q75 = np.percentile(x, 75, axis=0)
    iqr = q75 - q25
    iqr[iqr == 0] = 1.0
    return (x - med) / iqr, med, iqr


def standard_scale(x: np.ndarray) -> np.ndarray:
    mu = np.mean(x, axis=0)
    sd = np.std(x, axis=0)
    sd[sd == 0] = 1.0
    return (x - mu) / sd


def pairwise_dist(x: np.ndarray) -> np.ndarray:
    diff = x[:, None, :] - x[None, :, :]
    return np.sqrt(np.sum(diff * diff, axis=2))


def kmeans(x: np.ndarray, k: int, n_init: int = 50) -> tuple[np.ndarray, float]:
    rng = random.Random(RANDOM_SEED + k)
    best_labels = None
    best_inertia = float("inf")
    n = len(x)
    for _ in range(n_init):
        centers = x[rng.sample(range(n), k)].copy()
        labels = np.zeros(n, dtype=int)
        for _iter in range(100):
            d = np.sqrt(((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2))
            new_labels = np.argmin(d, axis=1)
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels
            for j in range(k):
                if np.any(labels == j):
                    centers[j] = x[labels == j].mean(axis=0)
        inertia = float(np.sum((x - centers[labels]) ** 2))
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels.copy()
    return best_labels, best_inertia


def agglomerative_average(x: np.ndarray, k: int) -> np.ndarray:
    clusters = {i: [i] for i in range(len(x))}
    dmat = pairwise_dist(x)
    while len(clusters) > k:
        keys = list(clusters)
        best = None
        best_d = float("inf")
        for a_i, a in enumerate(keys):
            for b in keys[a_i + 1 :]:
                d = float(np.mean([dmat[i, j] for i in clusters[a] for j in clusters[b]]))
                if d < best_d:
                    best_d = d
                    best = (a, b)
        a, b = best
        clusters[a] = clusters[a] + clusters[b]
        del clusters[b]
    labels = np.zeros(len(x), dtype=int)
    for new_id, members in enumerate(clusters.values()):
        for m in members:
            labels[m] = new_id
    return labels


def dbscan_simple(x: np.ndarray) -> np.ndarray:
    d = pairwise_dist(x)
    kth = np.sort(d + np.eye(len(x)) * 1e9, axis=1)[:, 3]
    eps = float(np.percentile(kth, 45))
    min_pts = 4
    labels = np.full(len(x), -1, dtype=int)
    cluster_id = 0
    for i in range(len(x)):
        if labels[i] != -1:
            continue
        neigh = list(np.where(d[i] <= eps)[0])
        if len(neigh) < min_pts:
            continue
        labels[i] = cluster_id
        queue = neigh[:]
        while queue:
            j = queue.pop()
            if labels[j] == -1:
                labels[j] = cluster_id
            if labels[j] != cluster_id:
                continue
            jn = list(np.where(d[j] <= eps)[0])
            if len(jn) >= min_pts:
                for q in jn:
                    if labels[q] == -1:
                        queue.append(q)
        cluster_id += 1
    return labels


def silhouette_score(x: np.ndarray, labels: np.ndarray) -> float:
    unique = [u for u in sorted(set(labels)) if u >= 0]
    if len(unique) < 2:
        return 0.0
    d = pairwise_dist(x)
    vals = []
    for i in range(len(x)):
        own = labels[i]
        if own < 0:
            continue
        same = [j for j in range(len(x)) if labels[j] == own and j != i]
        a = float(np.mean([d[i, j] for j in same])) if same else 0.0
        b = min(float(np.mean([d[i, j] for j in range(len(x)) if labels[j] == u])) for u in unique if u != own)
        vals.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return float(np.mean(vals)) if vals else 0.0


def db_index(x: np.ndarray, labels: np.ndarray) -> float:
    unique = [u for u in sorted(set(labels)) if u >= 0]
    if len(unique) < 2:
        return 0.0
    centers = {u: x[labels == u].mean(axis=0) for u in unique}
    scat = {u: float(np.mean(np.linalg.norm(x[labels == u] - centers[u], axis=1))) for u in unique}
    vals = []
    for u in unique:
        worst = 0.0
        for v in unique:
            if u == v:
                continue
            dist = float(np.linalg.norm(centers[u] - centers[v]))
            worst = max(worst, (scat[u] + scat[v]) / dist if dist else 0.0)
        vals.append(worst)
    return float(np.mean(vals))


def ch_score(x: np.ndarray, labels: np.ndarray) -> float:
    unique = [u for u in sorted(set(labels)) if u >= 0]
    n = len(x)
    k = len(unique)
    if k < 2 or n <= k:
        return 0.0
    overall = x.mean(axis=0)
    between = 0.0
    within = 0.0
    for u in unique:
        pts = x[labels == u]
        center = pts.mean(axis=0)
        between += len(pts) * float(np.sum((center - overall) ** 2))
        within += float(np.sum((pts - center) ** 2))
    return (between / (k - 1)) / (within / (n - k)) if within else 0.0


def ari(labels_a: np.ndarray, labels_b: np.ndarray) -> float:
    n = len(labels_a)
    if n < 2:
        return 1.0
    ca = Counter(labels_a)
    cb = Counter(labels_b)
    contingency = Counter(zip(labels_a, labels_b))

    def comb2(v: int) -> float:
        return v * (v - 1) / 2

    sum_ij = sum(comb2(v) for v in contingency.values())
    sum_a = sum(comb2(v) for v in ca.values())
    sum_b = sum(comb2(v) for v in cb.values())
    total = comb2(n)
    expected = sum_a * sum_b / total if total else 0
    max_idx = 0.5 * (sum_a + sum_b)
    return (sum_ij - expected) / (max_idx - expected) if max_idx != expected else 0.0


def cluster_metrics_rows(x: np.ndarray, labels_by_name: dict[str, np.ndarray]) -> list[dict]:
    rows = []
    for name, labels in labels_by_name.items():
        counts = Counter(labels)
        rows.append(
            {
                "model": name,
                "cluster_count": len([c for c in counts if c >= 0]),
                "noise_count": counts.get(-1, 0),
                "min_cluster_size": min([v for k, v in counts.items() if k >= 0] or [0]),
                "max_cluster_size": max([v for k, v in counts.items() if k >= 0] or [0]),
                "silhouette": silhouette_score(x, labels),
                "davies_bouldin": db_index(x, labels),
                "calinski_harabasz": ch_score(x, labels),
            }
        )
    return rows


def choose_primary_clustering(x: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    labels_by_name = {}
    for k in range(2, 8):
        labels_by_name[f"kmeans_k{k}"] = kmeans(x, k)[0]
        labels_by_name[f"agglo_k{k}"] = agglomerative_average(x, k)
    labels_by_name["dbscan_simple"] = dbscan_simple(x)
    rows = cluster_metrics_rows(x, labels_by_name)
    eligible = [
        r
        for r in rows
        if r["model"].startswith("agglo") and r["min_cluster_size"] >= 4 and 2 <= r["cluster_count"] <= 5
    ]
    eligible = sorted(eligible, key=lambda r: (r["silhouette"], -r["davies_bouldin"]), reverse=True)
    chosen = eligible[0]["model"] if eligible else "agglo_k3"
    return labels_by_name[chosen], rows


def pca_2d(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centered = x - x.mean(axis=0)
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    coords = centered @ vt[:2].T
    explained = (s**2) / np.sum(s**2) if np.sum(s**2) else np.zeros_like(s)
    return coords, explained[:2]


def png_scatter(path: Path, points: np.ndarray, labels: list[str], title: str) -> None:
    width, height = 900, 650
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    colors = [
        (31, 119, 180),
        (255, 127, 14),
        (44, 160, 44),
        (214, 39, 40),
        (148, 103, 189),
        (140, 86, 75),
        (127, 127, 127),
    ]
    x = points[:, 0]
    y = points[:, 1]
    xmin, xmax = float(x.min()), float(x.max())
    ymin, ymax = float(y.min()), float(y.max())
    if xmax == xmin:
        xmax += 1
    if ymax == ymin:
        ymax += 1
    for i, (px, py) in enumerate(points):
        xx = int(60 + (px - xmin) / (xmax - xmin) * (width - 120))
        yy = int(height - 60 - (py - ymin) / (ymax - ymin) * (height - 120))
        color = colors[hash(labels[i]) % len(colors)]
        img[max(0, yy - 4) : min(height, yy + 5), max(0, xx - 4) : min(width, xx + 5)] = color
    write_png(path, img)


def write_png(path: Path, img: np.ndarray) -> None:
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)


def simple_pdf(path: Path, lines: list[str]) -> None:
    w, h = 900, 1100
    pages = []
    for start in range(0, len(lines), 45):
        cmds = [f"1 1 1 rg 0 0 {w} {h} re f", "/F1 15 Tf 0 0 0 rg 40 1060 Td (EXP-005C Outcome Taxonomy Overview) Tj"]
        y = 1025
        for line in lines[start : start + 45]:
            safe = str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            cmds.append(f"/F1 9 Tf 0 0 0 rg 45 {y} Td ({safe}) Tj")
            y -= 22
        pages.append("\n".join(cmds).encode("latin-1", errors="replace"))
    objs = []

    def obj(s):
        objs.append(s if isinstance(s, bytes) else s.encode("latin-1"))

    obj("<< /Type /Catalog /Pages 2 0 R >>")
    kids = [f"{3+i*2} 0 R" for i in range(len(pages))]
    obj(f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>")
    font_obj = 3 + len(pages) * 2
    for i, content in enumerate(pages):
        obj(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] /Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {4+i*2} 0 R >>")
        obj(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(pdf)


def taxonomy_name(row: pd.Series) -> str:
    if row["delayed_major_move_flag"]:
        return "DELAYED_MAJOR_MOVE"
    if row["signed_efficiency"] > 0.22 and row["signed_close_return_atr"] > 1.0:
        return "WEAK_REVERSAL"
    if row["signed_efficiency"] < -0.12 or row["signed_close_return_atr"] < -1.0:
        return "TREND_CONTINUATION"
    if row["net_to_path_ratio"] < 0.12 and row["return_sign_changes"] >= 8:
        return "RANGE_WHIPSAW"
    if row["atr_decay"] < 0.75 and row["range_expansion_vs_pre_event"] < 0.85:
        return "COMPRESSION"
    return "UNCLASSIFIED"


def main() -> None:
    random.seed(RANDOM_SEED)
    ensure_dirs()
    df = load_ohlc()
    failed = pd.read_csv(EXP_B / "failed_turns.csv")
    major = pd.read_csv(EXP_B / "major_starts.csv")
    if len(failed) != 45:
        raise RuntimeError(f"expected 45 matched non-major events, got {len(failed)}")
    features = []
    for _, row in failed.iterrows():
        for h in HORIZONS:
            features.append(
                outcome_features_for_event(
                    df,
                    event_id=row["failed_id"],
                    timestamp=row["candidate_time"],
                    direction=row["direction"],
                    matched_group_id=row["matched_move_id"],
                    horizon=h,
                    event_type="MATCHED_NON_MAJOR",
                )
            )
    feature_df = pd.DataFrame(features)
    feature_df.to_csv(OUT / "outcome_features.csv", index=False)
    wide = wide_features(feature_df)
    wide.to_csv(OUT / "outcome_features_wide.csv", index=False)
    summary = feature_summary(feature_df)
    summary.to_csv(OUT / "outcome_feature_summary.csv", index=False)
    corr = feature_df.select_dtypes(include=[np.number]).corr(numeric_only=True)
    corr.to_csv(OUT / "outcome_feature_correlations.csv")

    h30 = feature_df[feature_df["horizon"] == PRIMARY_H].reset_index(drop=True)
    x_raw = h30[CORE_FEATURES].to_numpy(dtype=float)
    x, _, _ = robust_scale(x_raw)
    primary_labels, metric_rows = choose_primary_clustering(x)
    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(OUT / "cluster_model_metrics.csv", index=False)
    cluster_assign = h30[["event_id", "timestamp", "direction", "matched_group_id"]].copy()
    cluster_assign["cluster_id"] = primary_labels
    # Compact cluster names from profiles after labels exist.
    profile_rows = []
    for cid in sorted(set(primary_labels)):
        sub = h30[primary_labels == cid]
        profile_rows.append(
            {
                "cluster_id": cid,
                "size": len(sub),
                "median_signed_return_atr": sub["signed_close_return_atr"].median(),
                "median_mfe_atr": sub["mfe_atr"].median(),
                "median_mae_atr": sub["mae_atr"].median(),
                "median_efficiency": sub["signed_efficiency"].median(),
                "median_sign_changes": sub["return_sign_changes"].median(),
                "median_range_atr": sub["high_low_range_atr"].median(),
                "median_volatility_ratio": sub["realized_volatility_ratio"].median(),
                "median_time_to_mfe": sub["time_to_mfe"].median(),
                "median_time_to_mae": sub["time_to_mae"].median(),
                "delayed_major_move_count": int(sub["delayed_major_move_flag"].sum()),
            }
        )
    profiles = pd.DataFrame(profile_rows)

    def cluster_label(row):
        if row["delayed_major_move_count"] >= max(1, row["size"] // 3):
            return "DELAYED_MAJOR_MOVE"
        if row["median_efficiency"] > 0.18 and row["median_signed_return_atr"] > 0:
            return "WEAK_REVERSAL"
        if row["median_signed_return_atr"] < -0.5:
            return "TREND_CONTINUATION"
        if row["median_sign_changes"] >= 8:
            return "RANGE_WHIPSAW"
        return f"OUTCOME_CLUSTER_{int(row['cluster_id'])}"

    profiles["cluster_name"] = profiles.apply(cluster_label, axis=1)
    profiles.to_csv(OUT / "cluster_profiles.csv", index=False)
    name_map = dict(zip(profiles["cluster_id"], profiles["cluster_name"]))
    cluster_assign["cluster_name"] = cluster_assign["cluster_id"].map(name_map)
    cluster_assign.to_csv(OUT / "cluster_assignments.csv", index=False)

    # Stability: algorithm/horizon/feature/scaler plus bootstrap/subsampling.
    stability_rows = []
    labels_by_variant = {"primary_h30_core_robust": primary_labels}
    for h in [20, 60]:
        hh = feature_df[feature_df["horizon"] == h].reset_index(drop=True)
        xx, _, _ = robust_scale(hh[CORE_FEATURES].to_numpy(dtype=float))
        labels_by_variant[f"agglo_h{h}_core_robust"] = agglomerative_average(xx, len(set(primary_labels)))
    labels_by_variant["kmeans_h30_core_robust"] = kmeans(x, len(set(primary_labels)))[0]
    labels_by_variant["dbscan_h30_core_robust"] = dbscan_simple(x)
    labels_by_variant["agglo_h30_core_standard"] = agglomerative_average(standard_scale(x_raw), len(set(primary_labels)))
    reduced_features = [f for f in CORE_FEATURES if f not in {"mfe_atr", "mae_atr", "swing_direction_changes"}]
    xx, _, _ = robust_scale(h30[reduced_features].to_numpy(dtype=float))
    labels_by_variant["agglo_h30_reduced_robust"] = agglomerative_average(xx, len(set(primary_labels)))
    for name, labels in labels_by_variant.items():
        stability_rows.append(
            {
                "variant": name,
                "cluster_count": len([c for c in set(labels) if c >= 0]),
                "ari_vs_primary": ari(primary_labels, labels) if len(labels) == len(primary_labels) else "",
                "silhouette": silhouette_score(x if len(labels) == len(primary_labels) else x, labels)
                if len(labels) == len(primary_labels)
                else "",
            }
        )

    n = len(h30)
    co = np.zeros((n, n))
    together = np.zeros((n, n))
    ari_vals = []
    rng = random.Random(RANDOM_SEED)
    for _ in range(500):
        sample = sorted(rng.sample(range(n), max(4, int(n * 0.8))))
        sx = x[sample]
        slabels = agglomerative_average(sx, len(set(primary_labels)))
        ari_vals.append(ari(primary_labels[sample], slabels))
        for a_i, a in enumerate(sample):
            for b_i, b in enumerate(sample):
                co[a, b] += 1
                if slabels[a_i] == slabels[b_i]:
                    together[a, b] += 1
    coclust = np.divide(together, co, out=np.zeros_like(together), where=co > 0)
    stability_rows.append(
        {
            "variant": "bootstrap_80pct_500",
            "cluster_count": len(set(primary_labels)),
            "ari_vs_primary": float(np.mean(ari_vals)),
            "silhouette": "",
        }
    )
    pd.DataFrame(stability_rows).to_csv(OUT / "cluster_stability.csv", index=False)
    coc = pd.DataFrame(coclust, index=h30["event_id"], columns=h30["event_id"])
    coc.to_csv(OUT / "co_clustering_matrix.csv")

    # Rule taxonomy.
    tax_rows = []
    for _, row in h30.iterrows():
        cid = int(cluster_assign.loc[cluster_assign["event_id"] == row["event_id"], "cluster_id"].iloc[0])
        cname = name_map[cid]
        rule = taxonomy_name(row)
        conf = "HIGH" if rule == cname or rule == "DELAYED_MAJOR_MOVE" else "MEDIUM" if rule != "UNCLASSIFIED" else "LOW"
        tax_rows.append(
            {
                "event_id": row["event_id"],
                "cluster_id": cid,
                "cluster_name": cname,
                "rule_based_class": rule,
                "confidence": conf,
                "horizon": PRIMARY_H,
                "delayed_major_move_flag": int(row["delayed_major_move_flag"]),
            }
        )
    taxonomy = pd.DataFrame(tax_rows)
    taxonomy.to_csv(OUT / "outcome_taxonomy.csv", index=False)
    (OUT / "taxonomy_rules.md").write_text(
        """# EXP-005C Rule-Based Outcome Taxonomy

Rules are post-hoc interpretations of cluster profiles. They are not optimized for prediction and do not force every event into a class.

1. `DELAYED_MAJOR_MOVE`: `delayed_major_move_flag == 1`.
2. `WEAK_REVERSAL`: `signed_efficiency > 0.22` and `signed_close_return_atr > 1.0`.
3. `TREND_CONTINUATION`: `signed_efficiency < -0.12` or `signed_close_return_atr < -1.0`.
4. `RANGE_WHIPSAW`: `net_to_path_ratio < 0.12` and `return_sign_changes >= 8`.
5. `COMPRESSION`: `ATR_decay < 0.75` and `range_expansion_vs_pre_event < 0.85`.
6. Otherwise `UNCLASSIFIED`.
""",
        encoding="utf-8",
    )

    # Major comparison after taxonomy.
    major_features = []
    for _, row in major.iterrows():
        for h in HORIZONS:
            major_features.append(
                outcome_features_for_event(
                    df,
                    event_id=row["move_id"],
                    timestamp=row["start_time"],
                    direction=row["direction"],
                    matched_group_id=row["move_id"],
                    horizon=h,
                    event_type="MAJOR_START",
                )
            )
    major_df = pd.DataFrame(major_features)
    major_h30 = major_df[major_df["horizon"] == PRIMARY_H].reset_index(drop=True)
    combined = pd.concat([h30, major_h30], ignore_index=True)
    comp_rows = []
    for event_type, sub in combined.groupby("event_type"):
        comp_rows.append(
            {
                "event_type": event_type,
                "count": len(sub),
                "median_signed_return_atr": sub["signed_close_return_atr"].median(),
                "median_mfe_atr": sub["mfe_atr"].median(),
                "median_mae_atr": sub["mae_atr"].median(),
                "median_signed_efficiency": sub["signed_efficiency"].median(),
                "median_range_atr": sub["high_low_range_atr"].median(),
                "delayed_major_move_count": int(sub["delayed_major_move_flag"].sum()),
            }
        )
    pd.DataFrame(comp_rows).to_csv(OUT / "major_vs_taxonomy_comparison.csv", index=False)

    # PCA/embedding.
    coords, explained = pca_2d(x)
    pca_df = h30[["event_id", "direction"]].copy()
    pca_df["pc1"] = coords[:, 0]
    pca_df["pc2"] = coords[:, 1]
    pca_df["cluster_id"] = primary_labels
    pca_df["signed_return_atr"] = h30["signed_close_return_atr"]
    pca_df["signed_efficiency"] = h30["signed_efficiency"]
    pca_df["mfe_atr"] = h30["mfe_atr"]
    pca_df["explained_pc1"] = explained[0] if len(explained) else 0
    pca_df["explained_pc2"] = explained[1] if len(explained) > 1 else 0
    pca_df.to_csv(OUT / "outcome_pca.csv", index=False)
    png_scatter(OUT / "outcome_pca.png", coords, [str(x) for x in primary_labels], "PCA")
    # UMAP unavailable; use PCA coordinates as deterministic fallback embedding.
    png_scatter(OUT / "outcome_embedding.png", coords, [str(x) for x in h30["signed_close_return_atr"].round(1)], "Embedding")

    # Representatives.
    rep_rows = []
    for cid in sorted(set(primary_labels)):
        sub_idx = np.where(primary_labels == cid)[0]
        center = x[sub_idx].mean(axis=0)
        dists = [(i, float(np.linalg.norm(x[i] - center))) for i in sub_idx]
        ordered = sorted(dists, key=lambda t: t[1])
        rep_ids = set()
        for i, dist in ordered[:3]:
            rep_ids.add(i)
            rep_rows.append(
                {
                    "event_id": h30.loc[i, "event_id"],
                    "cluster_id": cid,
                    "role": "representative",
                    "distance_to_cluster_center": dist,
                    "symbol": SYMBOL,
                    "timestamp": h30.loc[i, "timestamp"],
                    "direction": h30.loc[i, "direction"],
                }
            )
        boundary_candidates = [item for item in ordered[::-1] if item[0] not in rep_ids]
        for i, dist in boundary_candidates[:2]:
            rep_rows.append(
                {
                    "event_id": h30.loc[i, "event_id"],
                    "cluster_id": cid,
                    "role": "boundary",
                    "distance_to_cluster_center": dist,
                    "symbol": SYMBOL,
                    "timestamp": h30.loc[i, "timestamp"],
                    "direction": h30.loc[i, "direction"],
                }
            )
    pd.DataFrame(rep_rows).to_csv(OUT / "representative_events.csv", index=False)

    # Pine review.
    colors = {
        "TREND_CONTINUATION": "color.rgb(210, 70, 70)",
        "WEAK_REVERSAL": "color.rgb(0, 170, 120)",
        "RANGE_WHIPSAW": "color.rgb(230, 150, 0)",
        "DELAYED_MAJOR_MOVE": "color.rgb(120, 80, 210)",
        "COMPRESSION": "color.rgb(80, 150, 190)",
        "UNCLASSIFIED": "color.rgb(120, 120, 120)",
    }
    times = []
    ids = []
    dirs = []
    clusters = []
    classes = []
    delayed = []
    for _, row in taxonomy.merge(h30[["event_id", "timestamp", "direction"]], on="event_id").iterrows():
        ts = pd.Timestamp(row["timestamp"])
        times.append(f'timestamp("Etc/UTC", {ts.year}, {ts.month}, {ts.day}, {ts.hour}, {ts.minute})')
        ids.append(f'"{row["event_id"]}"')
        dirs.append(f'"{row["direction"]}"')
        clusters.append(f'"C{row["cluster_id"]}"')
        classes.append(f'"{row["rule_based_class"]}"')
        delayed.append("true" if int(row["delayed_major_move_flag"]) else "false")
    pine = f"""//@version=6
indicator("EXP-005C Outcome Taxonomy Review", overlay=true, max_lines_count=300, max_labels_count=300)

// Fixed review markup. Classes are loaded from EXP-005C CSV outputs. No signal.
showLabels = input.bool(true, "showLabels")
showWindows = input.bool(true, "showOutcomeWindow")

var int[] times = array.from({', '.join(times)})
var string[] ids = array.from({', '.join(ids)})
var string[] dirs = array.from({', '.join(dirs)})
var string[] clusters = array.from({', '.join(clusters)})
var string[] classes = array.from({', '.join(classes)})
var bool[] delayed = array.from({', '.join(delayed)})

f_color(cls) =>
    cls == "TREND_CONTINUATION" ? {colors['TREND_CONTINUATION']} :
     cls == "WEAK_REVERSAL" ? {colors['WEAK_REVERSAL']} :
     cls == "RANGE_WHIPSAW" ? {colors['RANGE_WHIPSAW']} :
     cls == "DELAYED_MAJOR_MOVE" ? {colors['DELAYED_MAJOR_MOVE']} :
     cls == "COMPRESSION" ? {colors['COMPRESSION']} :
     {colors['UNCLASSIFIED']}

var color bg = na
bg := na
for i = 0 to array.size(times) - 1
    int t = array.get(times, i)
    string id = array.get(ids, i)
    string dir = array.get(dirs, i)
    string cl = array.get(clusters, i)
    string cls = array.get(classes, i)
    bool dly = array.get(delayed, i)
    color c = f_color(cls)
    int outEnd = t + 30 * 4 * 60 * 60 * 1000
    if showWindows and time > t and time <= outEnd
        bg := color.new(c, 90)
    if time == t
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=c, width=2)
        if showLabels
            label.new(time, high, id + " " + dir + " " + cl + " " + cls + (dly ? " DELAYED" : ""), xloc=xloc.bar_time, style=label.style_label_down, color=color.new(c, 0), textcolor=color.white, size=size.tiny)
bgcolor(bg)
"""
    (OUT / "OUTCOME_TAXONOMY_REVIEW.pine").write_text(pine)

    delayed_count = int(h30["delayed_major_move_flag"].sum())
    mean_bootstrap_ari = float(np.mean(ari_vals))
    stable_clusters = int(sum(1 for _, row in profiles.iterrows() if row["size"] >= 4))
    spectrum = "WEAK_CLUSTER_STRUCTURE"
    if mean_bootstrap_ari < 0.35 or metrics_df["silhouette"].max() < 0.25:
        spectrum = "CONTINUOUS_OUTCOME_SPECTRUM"
    overview_lines = [
        "Goal: describe post-event outcomes of 45 matched_non_major_events.",
        "Technical label failed_turn from EXP-005B is not treated as a market type.",
        f"Feature rows: {len(feature_df)} event x horizon rows.",
        f"Primary horizon: H={PRIMARY_H}. Core features: {len(CORE_FEATURES)}.",
        f"Primary clusters: {len(set(primary_labels))}. Stable-size clusters: {stable_clusters}.",
        f"Bootstrap mean ARI: {mean_bootstrap_ari:.3f}.",
        f"Delayed major moves after H30: {delayed_count}.",
        f"Discrete vs continuous verdict: {spectrum}.",
        "",
        "Cluster profiles:",
    ]
    for _, row in profiles.iterrows():
        overview_lines.append(
            f"C{int(row['cluster_id'])} {row['cluster_name']}: n={int(row['size'])}, med_ret_atr={row['median_signed_return_atr']:.2f}, med_eff={row['median_efficiency']:.2f}, delayed={int(row['delayed_major_move_count'])}"
        )
    overview_lines += [
        "",
        "Major comparison:",
    ]
    for row in comp_rows:
        overview_lines.append(str(row))
    simple_pdf(OUT / "OUTCOME_TAXONOMY_OVERVIEW.pdf", overview_lines)

    # Small manifest for report generation.
    report_stats = {
        "primary_cluster_count": len(set(primary_labels)),
        "stable_clusters": stable_clusters,
        "delayed_count": delayed_count,
        "bootstrap_mean_ari": mean_bootstrap_ari,
        "spectrum_verdict": spectrum,
        "main_verdict": "WEAK_OUTCOME_TAXONOMY" if spectrum == "WEAK_CLUSTER_STRUCTURE" else "CONTINUOUS_OUTCOME_SPECTRUM",
    }
    pd.DataFrame([report_stats]).to_csv(OUT / "run_summary.csv", index=False)


if __name__ == "__main__":
    main()
