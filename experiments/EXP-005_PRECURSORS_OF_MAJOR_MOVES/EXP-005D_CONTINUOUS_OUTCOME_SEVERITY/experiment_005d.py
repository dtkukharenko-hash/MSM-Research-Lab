#!/usr/bin/env python3
"""EXP-005D: pre-event OHLC features vs continuous outcome severity."""

from __future__ import annotations

import csv
import math
import random
import statistics
import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES"
EXP_B = EXP / "EXP-005B_SELECTION_BIAS_TEST/artifacts"
OUT = EXP / "EXP-005D_CONTINUOUS_OUTCOME_SEVERITY/artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

SYMBOL = "ADAUSDT"
TIMEFRAME = "4H"
RESEARCH_END = pd.Timestamp("2025-07-01 00:00")
HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")
HOLDOUT_END = pd.Timestamp("2026-07-01 00:00")
HORIZONS = [10, 20, 30, 60]
PRIMARY_H = 30
SEED = 20260712


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df.sort_values("dt").reset_index(drop=True)
    prev = df["close"].shift(1).fillna(df["close"])
    df["true_range"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(),
            (df["high"] - prev).abs().to_numpy(),
            (df["low"] - prev).abs().to_numpy(),
        ]
    )
    df["body"] = (df["close"] - df["open"]).abs()
    df["range"] = df["high"] - df["low"]
    return df[df["dt"] <= RESEARCH_END].copy().reset_index(drop=True)


def sign_dir(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def atr_at(df: pd.DataFrame, idx: int, n: int = 14) -> float:
    v = float(df.loc[max(0, idx - n + 1) : idx, "true_range"].mean())
    return v if v > 0 else 1e-12


def robust_z(values: np.ndarray) -> np.ndarray:
    med = np.nanmedian(values)
    iqr = np.nanpercentile(values, 75) - np.nanpercentile(values, 25)
    if not np.isfinite(iqr) or iqr == 0:
        iqr = 1.0
    return (values - med) / iqr


def rankdata(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x)
    ranks = np.empty(len(x), dtype=float)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = rank
        i = j + 1
    return ranks


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return pearson(rankdata(np.asarray(x)), rankdata(np.asarray(y)))


def local_pivots(vals: np.ndarray) -> int:
    c = 0
    for i in range(1, len(vals) - 1):
        if vals[i] > vals[i - 1] and vals[i] > vals[i + 1]:
            c += 1
        elif vals[i] < vals[i - 1] and vals[i] < vals[i + 1]:
            c += 1
    return c


def longest_run(signs: list[int], target: int | None = None) -> int:
    best = 0
    cur = 0
    prev = None
    for s in signs:
        if s == 0:
            cur = 0
            prev = None
            continue
        if target is None:
            cur = cur + 1 if s == prev else 1
            prev = s
        else:
            cur = cur + 1 if s == target else 0
        best = max(best, cur)
    return best


def build_events() -> pd.DataFrame:
    major = pd.read_csv(EXP_B / "major_starts.csv")
    failed = pd.read_csv(EXP_B / "failed_turns.csv")
    rows = []
    for _, r in major.iterrows():
        rows.append(
            {
                "event_id": r["move_id"],
                "source_type": "MAJOR",
                "direction": r["direction"],
                "event_time": r["start_time"],
                "match_group": r["move_id"],
                "positive_move_id": r["move_id"],
                "match_quality": "",
                "available_history_flag": "OK",
                "censored_flag": "false",
            }
        )
    for _, r in failed.iterrows():
        rows.append(
            {
                "event_id": r["failed_id"],
                "source_type": "MATCHED_NON_MAJOR",
                "direction": r["direction"],
                "event_time": r["candidate_time"],
                "match_group": r["matched_move_id"],
                "positive_move_id": r["matched_move_id"],
                "match_quality": r.get("match_distance", ""),
                "available_history_flag": "OK",
                "censored_flag": "false",
            }
        )
    return pd.DataFrame(rows).sort_values("event_time").reset_index(drop=True)


def pre_features(df: pd.DataFrame, idx: int, event: pd.Series, window: int) -> dict:
    direction = event["direction"]
    sgn = sign_dir(direction)
    w = df.iloc[max(0, idx - window) : idx].copy()
    if len(w) < window:
        return {"available_history_flag": "INSUFFICIENT_HISTORY", "pre_window": window}
    close0 = float(df.iloc[idx]["close"])
    atr0 = atr_at(df, idx - 1 if idx > 0 else idx)
    closes = w["close"].to_numpy(float)
    highs = w["high"].to_numpy(float)
    lows = w["low"].to_numpy(float)
    opens = w["open"].to_numpy(float)
    bodies = w["body"].to_numpy(float)
    ranges = np.maximum(w["range"].to_numpy(float), 1e-12)
    trs = w["true_range"].to_numpy(float)
    steps = np.diff(closes)
    signs = [int(np.sign(x)) for x in steps if abs(x) > 1e-12]
    path = float(np.sum(np.abs(steps)))
    net = float(closes[-1] - closes[0])
    net_pct = net / closes[0] if closes[0] else 0
    eff = abs(net) / path if path else 0
    half = max(1, len(w) // 2)
    third = max(1, len(w) // 3)
    first = w.iloc[:third]
    last = w.iloc[-third:]
    rets = w["close"].pct_change().dropna().to_numpy(float)
    first_rets = w.iloc[:half]["close"].pct_change().dropna().to_numpy(float)
    second_rets = w.iloc[half:]["close"].pct_change().dropna().to_numpy(float)
    rv1 = float(np.std(first_rets)) if len(first_rets) else 0
    rv2 = float(np.std(second_rets)) if len(second_rets) else 0
    full_range = float(np.max(highs) - np.min(lows))
    close_pos = (closes[-1] - np.min(lows)) / full_range if full_range else 0.5
    new_high = 0
    new_low = 0
    rh = highs[0]
    rl = lows[0]
    for h, l in zip(highs[1:], lows[1:]):
        if h > rh:
            new_high += 1
            rh = h
        if l < rl:
            new_low += 1
            rl = l
    # Pullbacks against event direction inside pre-window.
    pulls = []
    cur = 0.0
    for d in steps:
        adverse = -sgn * d
        if adverse > 0:
            cur += adverse
        elif cur > 0:
            pulls.append(cur / close0)
            cur = 0
    if cur > 0:
        pulls.append(cur / close0)
    last5 = w.tail(5)
    l5_steps = np.diff(last5["close"].to_numpy(float))
    l5_path = float(np.sum(np.abs(l5_steps)))
    l5_net = float(last5["close"].iloc[-1] - last5["close"].iloc[0]) if len(last5) > 1 else 0
    l5_ranges = np.maximum(last5["range"].to_numpy(float), 1e-12)
    l5_bodies = last5["body"].to_numpy(float)
    fh_net = float(w["close"].iloc[half - 1] - w["close"].iloc[0])
    sh_net = float(w["close"].iloc[-1] - w["close"].iloc[half])
    first_eff = abs(fh_net) / float(np.sum(np.abs(np.diff(w["close"].iloc[:half].to_numpy(float))))) if half > 1 else 0
    second_path = float(np.sum(np.abs(np.diff(w["close"].iloc[half:].to_numpy(float)))))
    second_eff = abs(sh_net) / second_path if second_path else 0
    return {
        "available_history_flag": "OK",
        "pre_window": window,
        "pre_net_return": net_pct,
        "pre_net_return_atr": net / atr0,
        "pre_efficiency_ratio": eff,
        "pre_signed_efficiency": sgn * net / path if path else 0,
        "fraction_bars_in_event_direction": float(np.mean(np.sign(steps) == sgn)) if len(steps) else 0,
        "fraction_bars_against_event_direction": float(np.mean(np.sign(steps) == -sgn)) if len(steps) else 0,
        "number_of_direction_changes": sum(1 for a, b in zip(signs, signs[1:]) if a != b),
        "longest_same_direction_run": longest_run(signs),
        "longest_opposite_direction_run": longest_run(signs, target=-sgn),
        "pre_high_low_range_pct": full_range / closes[0] if closes[0] else 0,
        "pre_high_low_range_atr": full_range / atr0,
        "realized_volatility": float(np.std(rets)) if len(rets) else 0,
        "ATR14_at_event": atr0,
        "volatility_first_half": rv1,
        "volatility_second_half": rv2,
        "volatility_change_ratio": rv2 / rv1 if rv1 else 0,
        "average_true_range_first_third": float(first["true_range"].mean()),
        "average_true_range_last_third": float(last["true_range"].mean()),
        "range_compression_ratio": float(last["range"].mean()) / float(first["range"].mean()) if float(first["range"].mean()) else 0,
        "range_expansion_ratio": float(last["range"].max()) / float(first["range"].max()) if float(first["range"].max()) else 0,
        "average_body": float(np.mean(bodies)),
        "median_body": float(np.median(bodies)),
        "max_body": float(np.max(bodies)),
        "average_body_first_third": float(first["body"].mean()),
        "average_body_last_third": float(last["body"].mean()),
        "body_growth_ratio": float(last["body"].mean()) / float(first["body"].mean()) if float(first["body"].mean()) else 0,
        "upper_wick_share": float(np.mean((highs - np.maximum(opens, closes)) / ranges)),
        "lower_wick_share": float(np.mean((np.minimum(opens, closes) - lows) / ranges)),
        "full_range_to_body_ratio": float(np.mean(ranges / np.maximum(bodies, 1e-12))),
        "directional_body_share": float(np.mean(np.sign(closes - opens) == sgn)),
        "new_high_count": new_high,
        "new_low_count": new_low,
        "distance_from_30bar_high": (np.max(highs) - closes[-1]) / atr0,
        "distance_from_30bar_low": (closes[-1] - np.min(lows)) / atr0,
        "close_position_in_range": close_pos,
        "failed_high_break_count": int(np.sum((highs[1:] > highs[:-1]) & (closes[1:] <= highs[:-1]))),
        "failed_low_break_count": int(np.sum((lows[1:] < lows[:-1]) & (closes[1:] >= lows[:-1]))),
        "pullback_count": len(pulls),
        "average_pullback_depth": float(np.mean(pulls)) if pulls else 0,
        "maximum_pullback_depth": float(np.max(pulls)) if pulls else 0,
        "last5_net_return": l5_net / float(last5["close"].iloc[0]) if len(last5) else 0,
        "last5_efficiency": abs(l5_net) / l5_path if l5_path else 0,
        "last5_directional_share": float(np.mean(np.sign(l5_steps) == sgn)) if len(l5_steps) else 0,
        "last5_body_growth": l5_bodies[-1] / float(np.mean(l5_bodies[:3])) if len(l5_bodies) >= 3 and np.mean(l5_bodies[:3]) else 0,
        "last5_range_growth": l5_ranges[-1] / float(np.mean(l5_ranges[:3])) if len(l5_ranges) >= 3 and np.mean(l5_ranges[:3]) else 0,
        "last5_sign_changes": sum(1 for a, b in zip([int(np.sign(x)) for x in l5_steps], [int(np.sign(x)) for x in l5_steps][1:]) if a != b),
        "last5_new_extreme": int((last5["high"].max() >= w["high"].max()) if direction == "LONG" else (last5["low"].min() <= w["low"].min())),
        "last5_failed_continuation": int((last5["high"].max() <= w.iloc[:-5]["high"].max()) if direction == "SHORT" and len(w) > 5 else (last5["low"].min() >= w.iloc[:-5]["low"].min()) if len(w) > 5 else 0),
        "last5_acceleration_proxy": float(np.mean(l5_bodies[-2:]) / np.mean(l5_bodies[:3])) if len(l5_bodies) >= 5 and np.mean(l5_bodies[:3]) else 0,
        "first_half_net_return": fh_net / float(w["close"].iloc[0]),
        "second_half_net_return": sh_net / float(w["close"].iloc[half]) if float(w["close"].iloc[half]) else 0,
        "sign_change_between_halves": int(np.sign(fh_net) != np.sign(sh_net)),
        "efficiency_change_between_halves": second_eff - first_eff,
        "volatility_change_between_halves": rv2 - rv1,
        "body_size_change_between_halves": float(w.iloc[half:]["body"].mean()) - float(w.iloc[:half]["body"].mean()),
        "extreme_update_rate_change": (new_high + new_low) / window,
    }


def outcome_targets(df: pd.DataFrame, idx: int, event: pd.Series, horizon: int) -> dict:
    direction = event["direction"]
    sgn = sign_dir(direction)
    close0 = float(df.iloc[idx]["close"])
    atr0 = atr_at(df, idx)
    win = df.iloc[idx + 1 : min(len(df), idx + 1 + horizon)]
    closes = win["close"].to_numpy(float)
    highs = win["high"].to_numpy(float)
    lows = win["low"].to_numpy(float)
    path_steps = np.diff(np.r_[close0, closes])
    signed_close = sgn * (closes[-1] - close0)
    if direction == "LONG":
        mfe = float(win["high"].max() - close0)
        mae = float(close0 - win["low"].min())
    else:
        mfe = float(close0 - win["low"].min())
        mae = float(win["high"].max() - close0)
    path = float(np.sum(np.abs(path_steps)))
    close_dirs = np.sign(path_steps).astype(int)
    favorable = (highs - close0) if direction == "LONG" else (close0 - lows)
    adverse = (close0 - lows) if direction == "LONG" else (highs - close0)
    mfe_i = int(np.argmax(favorable)) + 1
    mae_i = int(np.argmax(adverse)) + 1
    after_mfe = closes[mfe_i - 1 :]
    if len(after_mfe):
        peak_price = float(highs[mfe_i - 1]) if direction == "LONG" else float(lows[mfe_i - 1])
        if direction == "LONG":
            reversal_after = int((peak_price - float(np.min(after_mfe))) / atr0 > 1.0)
        else:
            reversal_after = int((float(np.max(after_mfe)) - peak_price) / atr0 > 1.0)
    else:
        reversal_after = 0
    return {
        "event_id": event["event_id"],
        "horizon": horizon,
        "signed_close_return_atr": signed_close / atr0,
        "signed_close_return_pct": signed_close / close0,
        "MFE_atr": mfe / atr0,
        "MAE_atr": -mae / atr0,
        "signed_efficiency": signed_close / path if path else 0,
        "net_to_path_ratio": signed_close / path if path else 0,
        "directional_persistence": float(np.mean(close_dirs == sgn)) if len(close_dirs) else 0,
        "longest_directional_run": longest_run([int(x) for x in close_dirs], target=sgn),
        "time_to_MFE": mfe_i,
        "time_to_MAE": mae_i,
        "path_length_atr": path / atr0,
        "high_low_range_atr": (float(win["high"].max()) - float(win["low"].min())) / atr0,
        "number_of_sign_changes": sum(1 for a, b in zip(close_dirs, close_dirs[1:]) if a != b),
        "number_of_local_pivots": local_pivots(closes),
        "reversal_after_MFE": reversal_after,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def fit_linear(x: np.ndarray, y: np.ndarray, ridge: float = 0.0) -> np.ndarray:
    x1 = np.c_[np.ones(len(x)), x]
    reg = np.eye(x1.shape[1]) * ridge
    reg[0, 0] = 0
    return np.linalg.pinv(x1.T @ x1 + reg) @ x1.T @ y


def pred_linear(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.c_[np.ones(len(x)), x] @ beta


def fit_lasso_cd(x: np.ndarray, y: np.ndarray, alpha: float = 0.03, iters: int = 200) -> np.ndarray:
    x1 = np.c_[np.ones(len(x)), x]
    beta = np.zeros(x1.shape[1])
    beta[0] = np.mean(y)
    for _ in range(iters):
        for j in range(x1.shape[1]):
            r = y - x1 @ beta + x1[:, j] * beta[j]
            rho = float(np.mean(x1[:, j] * r))
            z = float(np.mean(x1[:, j] ** 2)) or 1.0
            if j == 0:
                beta[j] = rho / z
            else:
                beta[j] = np.sign(rho) * max(abs(rho) - alpha, 0) / z
    return beta


def fit_huber(x: np.ndarray, y: np.ndarray, delta: float = 1.35) -> np.ndarray:
    beta = fit_linear(x, y, ridge=0.1)
    for _ in range(20):
        pred = pred_linear(beta, x)
        r = y - pred
        scale = np.median(np.abs(r)) / 0.6745 or 1.0
        w = np.minimum(1.0, delta * scale / np.maximum(np.abs(r), 1e-12))
        x1 = np.c_[np.ones(len(x)), x]
        wx = x1 * w[:, None]
        beta = np.linalg.pinv(wx.T @ x1 + np.eye(x1.shape[1]) * 0.01) @ wx.T @ y
    return beta


def fit_forest_stumps(x: np.ndarray, y: np.ndarray, n_trees: int = 80) -> list:
    rng = random.Random(SEED)
    trees = []
    n, p = x.shape
    for _ in range(n_trees):
        idxs = [rng.randrange(n) for _ in range(n)]
        feats = rng.sample(range(p), max(1, int(math.sqrt(p))))
        best = None
        best_loss = float("inf")
        for f in feats:
            vals = x[idxs, f]
            for q in [25, 50, 75]:
                thr = float(np.percentile(vals, q))
                left = [i for i in idxs if x[i, f] <= thr]
                right = [i for i in idxs if x[i, f] > thr]
                if not left or not right:
                    continue
                lp = float(np.mean(y[left]))
                rp = float(np.mean(y[right]))
                loss = sum((y[i] - (lp if x[i, f] <= thr else rp)) ** 2 for i in idxs)
                if loss < best_loss:
                    best_loss = loss
                    best = (f, thr, lp, rp)
        trees.append(best if best else (0, 0.0, float(np.mean(y)), float(np.mean(y))))
    return trees


def pred_forest(trees: list, x: np.ndarray) -> np.ndarray:
    out = []
    for row in x:
        vals = [lp if row[f] <= thr else rp for f, thr, lp, rp in trees]
        out.append(float(np.mean(vals)))
    return np.array(out)


def metrics(y: np.ndarray, pred: np.ndarray) -> dict:
    err = pred - y
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return {
        "r2": 1 - ss_res / ss_tot if ss_tot else 0,
        "spearman": spearman(y, pred),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "median_absolute_error": float(np.median(np.abs(err))),
    }


def group_oof(features: pd.DataFrame, y: np.ndarray, feature_cols: list[str], model: str) -> np.ndarray:
    groups = features["match_group"].to_numpy()
    unique = list(dict.fromkeys(groups))
    pred = np.zeros(len(features))
    x_all = features[feature_cols].to_numpy(float)
    for g in unique:
        test = groups == g
        train = ~test
        xtr = x_all[train]
        xte = x_all[test]
        ytr = y[train]
        med = np.median(xtr, axis=0)
        iqr = np.percentile(xtr, 75, axis=0) - np.percentile(xtr, 25, axis=0)
        iqr[iqr == 0] = 1
        xtr = (xtr - med) / iqr
        xte = (xte - med) / iqr
        if model == "mean":
            pred[test] = np.mean(ytr)
        elif model == "linear":
            pred[test] = pred_linear(fit_linear(xtr, ytr, 0.0), xte)
        elif model == "ridge":
            pred[test] = pred_linear(fit_linear(xtr, ytr, 1.0), xte)
        elif model == "lasso":
            pred[test] = pred_linear(fit_lasso_cd(xtr, ytr, 0.04), xte)
        elif model == "huber":
            pred[test] = pred_linear(fit_huber(xtr, ytr), xte)
        elif model == "forest":
            pred[test] = pred_forest(fit_forest_stumps(xtr, ytr), xte)
    return pred


def png_scatter(path: Path, x: np.ndarray, y: np.ndarray) -> None:
    w, h = 900, 650
    img = np.ones((h, w, 3), dtype=np.uint8) * 255
    xmin, xmax = float(np.min(x)), float(np.max(x))
    ymin, ymax = float(np.min(y)), float(np.max(y))
    if xmax == xmin:
        xmax += 1
    if ymax == ymin:
        ymax += 1
    for px, py in zip(x, y):
        xx = int(60 + (px - xmin) / (xmax - xmin) * (w - 120))
        yy = int(h - 60 - (py - ymin) / (ymax - ymin) * (h - 120))
        img[max(0, yy - 4) : min(h, yy + 5), max(0, xx - 4) : min(w, xx + 5)] = (31, 119, 180)
    write_png(path, img)


def png_bar(path: Path, values: np.ndarray) -> None:
    w, h = 900, 650
    img = np.ones((h, w, 3), dtype=np.uint8) * 255
    vals = np.asarray(values, dtype=float)
    vmin, vmax = float(vals.min()), float(vals.max())
    if vmax == vmin:
        vmax += 1
    for i, v in enumerate(vals):
        x0 = 40 + int(i * (w - 80) / len(vals))
        x1 = 40 + int((i + 0.8) * (w - 80) / len(vals))
        y = int(h - 50 - (v - vmin) / (vmax - vmin) * (h - 100))
        img[min(y, h - 50) : max(y, h - 50), x0:x1] = (44, 160, 44)
    write_png(path, img)


def write_png(path: Path, img: np.ndarray) -> None:
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(img.shape[0]))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", img.shape[1], img.shape[0], 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)


def simple_pdf(path: Path, lines: list[str]) -> None:
    w, h = 900, 1100
    pages = []
    for start in range(0, len(lines), 44):
        cmds = [f"1 1 1 rg 0 0 {w} {h} re f", "/F1 15 Tf 0 0 0 rg 40 1060 Td (EXP-005D Severity Overview) Tj"]
        y = 1025
        for line in lines[start : start + 44]:
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
    font = 3 + len(pages) * 2
    for i, c in enumerate(pages):
        obj(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] /Resources << /Font << /F1 {font} 0 R >> >> /Contents {4+i*2} 0 R >>")
        obj(f"<< /Length {len(c)} >>\nstream\n".encode() + c + b"\nendstream")
    obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pdf = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offs:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(pdf)


def main() -> None:
    random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_ohlc()
    events = build_events()
    idx = {str(t): i for i, t in enumerate(df["open_dt"])}
    events["event_idx"] = events["event_time"].map(idx)
    events.to_csv(OUT / "events_input.csv", index=False)
    pre_rows = []
    target_rows = []
    for _, ev in events.iterrows():
        i = int(ev["event_idx"])
        for w in [10, 20, 30, 50]:
            row = {k: ev[k] for k in ["event_id", "source_type", "direction", "event_time", "match_group"]}
            row.update(pre_features(df, i, ev, w))
            pre_rows.append(row)
        for h in HORIZONS:
            target_rows.append(outcome_targets(df, i, ev, h))
    pre = pd.DataFrame(pre_rows)
    targets = pd.DataFrame(target_rows)
    pre.to_csv(OUT / "pre_event_features.csv", index=False)
    targets.to_csv(OUT / "outcome_targets.csv", index=False)
    scores = []
    for h in HORIZONS:
        sub = targets[targets["horizon"] == h].copy()
        c1 = robust_z(sub["signed_close_return_atr"].to_numpy(float))
        c2 = robust_z(sub["MFE_atr"].to_numpy(float))
        c3 = robust_z(sub["signed_efficiency"].to_numpy(float))
        for j, (_, row) in enumerate(sub.iterrows()):
            scores.append(
                {
                    "event_id": row["event_id"],
                    "horizon": h,
                    "severity_return_component": c1[j],
                    "severity_mfe_component": c2[j],
                    "severity_efficiency_component": c3[j],
                    "severity_score": (c1[j] + c2[j] + c3[j]) / 3,
                }
            )
    scores = pd.DataFrame(scores)
    scores.to_csv(OUT / "severity_scores.csv", index=False)
    main_pre = pre[(pre["pre_window"] == 30) & (pre["available_history_flag"] == "OK")].copy()
    main = main_pre.merge(scores[scores["horizon"] == PRIMARY_H], on="event_id").merge(events[["event_id", "source_type"]], on="event_id", suffixes=("", "_event"))
    y = main["severity_score"].to_numpy(float)
    feature_cols = [c for c in main.columns if c not in {"event_id", "source_type", "source_type_event", "direction", "event_time", "match_group", "available_history_flag", "pre_window"} and np.issubdtype(main[c].dtype, np.number)]
    # Remove target leakage columns from features.
    feature_cols = [c for c in feature_cols if not c.startswith("severity_")]
    corr_rows = []
    rng = random.Random(SEED)
    for c in feature_cols:
        x = main[c].to_numpy(float)
        sp = spearman(x, y)
        pr = pearson(x, y)
        boots = []
        for _ in range(300):
            ids = [rng.randrange(len(x)) for _ in range(len(x))]
            boots.append(spearman(x[ids], y[ids]))
        corr_rows.append(
            {
                "feature": c,
                "spearman": sp,
                "pearson": pr,
                "robust_slope": np.median((y - np.median(y)) / (x - np.median(x) + 1e-9)),
                "bootstrap_ci_low": float(np.percentile(boots, 5)),
                "bootstrap_ci_high": float(np.percentile(boots, 95)),
                "direction": "positive" if sp > 0 else "negative" if sp < 0 else "flat",
            }
        )
    pd.DataFrame(corr_rows).sort_values("spearman", key=lambda s: s.abs(), ascending=False).to_csv(OUT / "feature_correlations.csv", index=False)
    models = {
        "mean": feature_cols,
        "linear": feature_cols,
        "ridge": feature_cols,
        "lasso": feature_cols,
        "huber": feature_cols,
        "forest": feature_cols,
        "pre_net_return_only": ["pre_net_return"],
        "volatility_only": ["realized_volatility", "volatility_change_ratio", "ATR14_at_event"],
        "last5_only": [c for c in feature_cols if c.startswith("last5_")],
    }
    pred_rows = []
    metric_rows = []
    fold_rows = []
    for model, cols in models.items():
        pred = group_oof(main, y, cols, model if model in {"mean", "linear", "ridge", "lasso", "huber", "forest"} else "ridge")
        m = metrics(y, pred)
        m.update({"model": model, "feature_count": len(cols)})
        metric_rows.append(m)
        for _, row in main.iterrows():
            fold_rows.append({"match_group": row["match_group"], "event_id": row["event_id"], "model": model})
        for eid, actual, p in zip(main["event_id"], y, pred):
            pred_rows.append({"event_id": eid, "model": model, "actual_severity": actual, "oof_predicted_severity": p})
    pd.DataFrame(pred_rows).to_csv(OUT / "model_oof_predictions.csv", index=False)
    pd.DataFrame(metric_rows).to_csv(OUT / "model_metrics.csv", index=False)
    pd.DataFrame(fold_rows).drop_duplicates().to_csv(OUT / "group_cv_folds.csv", index=False)
    # Permutation baseline for best model family.
    perm_rows = []
    best_model = max(metric_rows, key=lambda r: r["spearman"])["model"]
    best_cols = models[best_model]
    for i in range(100):
        yy = y.copy()
        random.Random(SEED + i).shuffle(yy)
        pred = group_oof(main, yy, best_cols, best_model if best_model in {"mean", "linear", "ridge", "lasso", "huber", "forest"} else "ridge")
        mm = metrics(yy, pred)
        mm["iteration"] = i
        mm["model"] = best_model
        perm_rows.append(mm)
    pd.DataFrame(perm_rows).to_csv(OUT / "permutation_results.csv", index=False)
    # Stability removals.
    stability = []
    severity_order = np.argsort(-y)
    for label, remove in [
        ("none", []),
        ("top1", list(severity_order[:1])),
        ("top3", list(severity_order[:3])),
        ("major_removed", list(np.where(main["source_type"] == "MAJOR")[0])),
    ]:
        keep = np.array([i for i in range(len(main)) if i not in remove])
        sub = main.iloc[keep].copy()
        yy = y[keep]
        if len(sub) > 5:
            pp = group_oof(sub, yy, best_cols, best_model if best_model in {"mean", "linear", "ridge", "lasso", "huber", "forest"} else "ridge")
            mm = metrics(yy, pp)
        else:
            mm = {"r2": 0, "spearman": 0, "mae": 0, "rmse": 0, "median_absolute_error": 0}
        mm.update({"test": label, "removed_count": len(remove), "remaining_count": len(keep)})
        stability.append(mm)
    pd.DataFrame(stability).to_csv(OUT / "leave_one_out_stability.csv", index=False)
    # Start shift stability for top correlated features.
    top_features = [r["feature"] for r in sorted(corr_rows, key=lambda r: abs(r["spearman"]), reverse=True)[:5]]
    shift_rows = []
    for sh in [-3, -2, -1, 0, 1, 2, 3]:
        vals = []
        yy = []
        for _, ev in events.iterrows():
            ii = int(ev["event_idx"]) + sh
            if ii < 50 or ii >= len(df) - 60:
                continue
            pf = pre_features(df, ii, ev, 30)
            if pf["available_history_flag"] != "OK":
                continue
            target = scores[(scores["event_id"] == ev["event_id"]) & (scores["horizon"] == PRIMARY_H)]["severity_score"].iloc[0]
            row = {"shift": sh, "event_id": ev["event_id"], "severity_score": target}
            for f in top_features:
                row[f] = pf[f]
            vals.append(row)
        sdf = pd.DataFrame(vals)
        for f in top_features:
            shift_rows.append({"shift": sh, "feature": f, "spearman": spearman(sdf[f].to_numpy(float), sdf["severity_score"].to_numpy(float)), "n": len(sdf)})
    pd.DataFrame(shift_rows).to_csv(OUT / "start_shift_stability.csv", index=False)
    # Plots.
    best_pred_df = pd.DataFrame(pred_rows)
    best_pred_df = best_pred_df[best_pred_df["model"] == best_model]
    png_bar(OUT / "severity_distribution.png", np.sort(y))
    png_bar(OUT / "severity_rank_plot.png", y[np.argsort(y)])
    png_scatter(OUT / "predicted_vs_actual.png", best_pred_df["actual_severity"].to_numpy(float), best_pred_df["oof_predicted_severity"].to_numpy(float))
    imp = pd.DataFrame(corr_rows).sort_values("spearman", key=lambda s: s.abs(), ascending=False).head(15)
    png_bar(OUT / "feature_importance.png", imp["spearman"].abs().to_numpy(float))
    # Pine.
    ranks = pd.Series(rankdata(y), index=main["event_id"]).to_dict()
    times = []
    ids = []
    types = []
    ranks_arr = []
    for _, ev in events.iterrows():
        ts = pd.Timestamp(ev["event_time"])
        times.append(f'timestamp("Etc/UTC", {ts.year}, {ts.month}, {ts.day}, {ts.hour}, {ts.minute})')
        ids.append(f'"{ev["event_id"]}"')
        types.append(f'"{ev["source_type"]}"')
        ranks_arr.append(str(int(ranks.get(ev["event_id"], 0))))
    pine = f"""//@version=6
indicator("EXP-005D Severity Review", overlay=true, max_lines_count=200, max_labels_count=200)
showLabels = input.bool(true, "showLabels")
showPreWindow = input.bool(true, "showPreWindow")
showHoldout = input.bool(true, "showHoldout")
var int[] times = array.from({', '.join(times)})
var string[] ids = array.from({', '.join(ids)})
var string[] types = array.from({', '.join(types)})
var int[] ranks = array.from({', '.join(ranks_arr)})
int holdoutStart = timestamp("Etc/UTC", 2025, 7, 1, 4, 0)
int holdoutEnd = timestamp("Etc/UTC", 2026, 7, 1, 0, 0)
var color bg = na
bg := na
if showHoldout and time >= holdoutStart and time <= holdoutEnd
    bg := color.new(color.gray, 82)
for i = 0 to array.size(times) - 1
    int t = array.get(times, i)
    string id = array.get(ids, i)
    string typ = array.get(types, i)
    int r = array.get(ranks, i)
    color c = typ == "MAJOR" ? color.rgb(0, 170, 120) : color.rgb(230, 150, 0)
    if showPreWindow and time >= t - 30 * 4 * 60 * 60 * 1000 and time < t
        bg := color.new(c, 91)
    if time == t
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=c, width=2)
        if showLabels
            label.new(time, high, id + " " + typ + " rank=" + str.tostring(r), xloc=xloc.bar_time, style=label.style_label_down, color=color.new(c, 0), textcolor=color.white, size=size.tiny)
bgcolor(bg)
"""
    (OUT / "SEVERITY_REVIEW.pine").write_text(pine)
    best_metrics = max(metric_rows, key=lambda r: r["spearman"])
    top_corr = pd.DataFrame(corr_rows).sort_values("spearman", key=lambda s: s.abs(), ascending=False).head(5)
    lines = [
        f"Events used: {len(main)}",
        "Severity score = robust_z(return_atr)+robust_z(MFE_atr)+robust_z(signed_efficiency) / 3",
        f"Best model: {best_metrics['model']} Spearman={best_metrics['spearman']:.3f} R2={best_metrics['r2']:.3f}",
        f"Best MAE={best_metrics['mae']:.3f} RMSE={best_metrics['rmse']:.3f}",
        "Top correlations:",
    ]
    for _, row in top_corr.iterrows():
        lines.append(f"{row['feature']}: spearman={row['spearman']:.3f}")
    lines += ["Stability:", pd.DataFrame(stability).to_string(index=False), "Research/holdout boundary: holdout not used."]
    simple_pdf(OUT / "SEVERITY_OVERVIEW.pdf", lines)


if __name__ == "__main__":
    main()
