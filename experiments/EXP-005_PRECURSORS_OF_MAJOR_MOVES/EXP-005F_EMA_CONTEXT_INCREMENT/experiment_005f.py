#!/usr/bin/env python3
"""EXP-005F: fixed EMA context increment test."""

from __future__ import annotations

import csv
import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES"
EXP_D = EXP / "EXP-005D_CONTINUOUS_OUTCOME_SEVERITY/artifacts"
OUT = EXP / "EXP-005F_EMA_CONTEXT_INCREMENT/artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

RESEARCH_START = pd.Timestamp("2023-07-01 00:00")
RESEARCH_END = pd.Timestamp("2025-07-01 00:00")
HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")
HOLDOUT_END = pd.Timestamp("2026-07-01 00:00")
PRIMARY_H = 30

MODEL_FEATURES = {
    "Model 0": ["pre_net_return_atr"],
    "Model 1": [
        "price_minus_ema27_atr",
        "ema27_slope_5",
        "ema27_slope_10",
        "ema27_slope_change",
        "fraction_last10_above_ema27",
        "number_of_ema27_crosses_last20",
        "distance_change_to_ema27_last10",
    ],
    "Model 2": [
        "price_minus_ema27_atr",
        "ema27_slope_5",
        "ema27_slope_10",
        "ema27_slope_change",
        "fraction_last10_above_ema27",
        "number_of_ema27_crosses_last20",
        "distance_change_to_ema27_last10",
        "price_minus_ema200_atr",
        "ema200_slope_10",
        "ema200_slope_30",
        "fraction_last30_above_ema200",
        "number_of_ema200_crosses_last50",
        "distance_change_to_ema200_last20",
        "ema27_minus_ema200_atr",
        "ema27_above_ema200",
        "ema27_ema200_distance_change_last20",
        "price_between_ema27_ema200",
        "ema27_turning_against_previous_state",
    ],
    "Model 3": [
        "pre_net_return_atr",
        "price_minus_ema27_atr",
        "ema27_slope_5",
        "ema27_slope_10",
        "ema27_slope_change",
        "fraction_last10_above_ema27",
        "number_of_ema27_crosses_last20",
        "distance_change_to_ema27_last10",
        "price_minus_ema200_atr",
        "ema200_slope_10",
        "ema200_slope_30",
        "fraction_last30_above_ema200",
        "number_of_ema200_crosses_last50",
        "distance_change_to_ema200_last20",
        "ema27_minus_ema200_atr",
        "ema27_above_ema200",
        "ema27_ema200_distance_change_last20",
        "price_between_ema27_ema200",
        "ema27_turning_against_previous_state",
    ],
}


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def rankdata(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x)
    ranks = np.empty(len(x), dtype=float)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    return pearson(rankdata(np.asarray(x)), rankdata(np.asarray(y)))


def roc_auc(y: np.ndarray, p: np.ndarray) -> float:
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    pos = y == 1
    neg = y == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return 0.5
    ranks = rankdata(p)
    return float((ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def pr_auc(y: np.ndarray, p: np.ndarray) -> float:
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    if y.sum() == 0:
        return 0.0
    order = np.argsort(-p)
    ys = y[order]
    tp = np.cumsum(ys)
    fp = np.cumsum(1 - ys)
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / y.sum()
    prev_recall = np.concatenate([[0.0], recall[:-1]])
    return float(np.sum((recall - prev_recall) * precision))


def classification_metrics(y: np.ndarray, p: np.ndarray, severity: np.ndarray) -> dict[str, float]:
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    pred = (p >= 0.5).astype(int)
    pos = y == 1
    neg = y == 0
    tpr = float(((pred == 1) & pos).sum() / pos.sum()) if pos.sum() else 0.0
    tnr = float(((pred == 0) & neg).sum() / neg.sum()) if neg.sum() else 0.0
    return {
        "roc_auc": roc_auc(y, p),
        "pr_auc": pr_auc(y, p),
        "balanced_accuracy": (tpr + tnr) / 2,
        "brier_score": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
        "spearman_prob_severity": spearman(p, severity),
        "prevalence": float(np.mean(y)),
    }


def regression_metrics(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    err = pred - y
    sst = float(np.sum((y - np.mean(y)) ** 2))
    sse = float(np.sum(err**2))
    return {
        "r2": 0.0 if sst == 0 else 1.0 - sse / sst,
        "spearman": spearman(pred, y),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(math.sqrt(np.mean(err**2))),
    }


def robust_z(values: np.ndarray) -> np.ndarray:
    med = float(np.nanmedian(values))
    iqr = float(np.nanpercentile(values, 75) - np.nanpercentile(values, 25))
    if not np.isfinite(iqr) or iqr == 0:
        iqr = 1.0
    return (values - med) / iqr


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -40, 40)))


def fit_scaler(x: np.ndarray) -> dict[str, np.ndarray]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std == 0] = 1.0
    return {"mean": mean, "std": std}


def apply_scaler(x: np.ndarray, scaler: dict[str, np.ndarray]) -> np.ndarray:
    return (x - scaler["mean"]) / scaler["std"]


def class_weights(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=int)
    n = len(y)
    pos = max(int(y.sum()), 1)
    neg = max(n - pos, 1)
    return np.where(y == 1, n / (2 * pos), n / (2 * neg)).astype(float)


def fit_logistic(x: np.ndarray, y: np.ndarray, c: float = 1.0) -> dict[str, np.ndarray | float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    wgt = class_weights(y)
    beta = np.zeros(x.shape[1] + 1, dtype=float)
    alpha = 1.0 / c
    lr = 0.08
    prev = 1e99
    for step in range(6000):
        z = beta[0] + x @ beta[1:]
        p = sigmoid(z)
        err = (p - y) * wgt
        grad = np.empty_like(beta)
        grad[0] = err.mean()
        grad[1:] = (x.T @ err) / len(y) + alpha * beta[1:] / len(y)
        beta -= lr * grad
        if step % 100 == 0:
            p = np.clip(p, 1e-6, 1 - 1e-6)
            loss = -np.mean(wgt * (y * np.log(p) + (1 - y) * np.log(1 - p))) + 0.5 * alpha * float(np.sum(beta[1:] ** 2)) / len(y)
            if abs(prev - loss) < 1e-10:
                break
            if loss > prev + 1e-4:
                lr *= 0.5
            prev = loss
    return {"intercept": float(beta[0]), "coef": beta[1:]}


def predict_logistic(model: dict[str, np.ndarray | float], x: np.ndarray) -> np.ndarray:
    return sigmoid(float(model["intercept"]) + np.asarray(x, dtype=float) @ np.asarray(model["coef"], dtype=float))


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> dict[str, np.ndarray | float]:
    design = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0
    beta = np.linalg.pinv(design.T @ design + penalty) @ design.T @ y
    return {"intercept": float(beta[0]), "coef": np.asarray(beta[1:], dtype=float)}


def predict_linear(model: dict[str, np.ndarray | float], x: np.ndarray) -> np.ndarray:
    return float(model["intercept"]) + np.asarray(x, dtype=float) @ np.asarray(model["coef"], dtype=float)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df.sort_values("dt").reset_index(drop=True)
    prev = df["close"].shift(1).fillna(df["close"])
    df["true_range"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(float),
            (df["high"] - prev).abs().to_numpy(float),
            (df["low"] - prev).abs().to_numpy(float),
        ]
    )
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    return df[(df["dt"] >= RESEARCH_START) & (df["dt"] <= RESEARCH_END)].copy().reset_index(drop=True)


def atr_at(df: pd.DataFrame, idx: int, n: int = 14) -> float:
    v = float(df.loc[max(0, idx - n + 1) : idx, "true_range"].mean())
    return v if v > 0 else 1e-12


def crosses(series_a: pd.Series, series_b: pd.Series) -> int:
    diff = (series_a - series_b).to_numpy(float)
    signs = np.sign(diff)
    count = 0
    for a, b in zip(signs, signs[1:]):
        if a == 0 or b == 0:
            continue
        if a != b:
            count += 1
    return count


def ema_features_at(df: pd.DataFrame, event_time: str, shift_bars: int = 0) -> dict[str, float]:
    t = pd.Timestamp(event_time)
    matches = df.index[df["dt"] == t].tolist()
    if not matches:
        raise RuntimeError(f"Event time not found: {event_time}")
    event_idx = matches[0] + shift_bars
    idx = event_idx - 1
    if idx < 50 or idx >= len(df):
        raise RuntimeError(f"Insufficient closed-bar EMA context for {event_time} shift {shift_bars}")
    atr = atr_at(df, idx)
    close = float(df.loc[idx, "close"])
    ema27 = float(df.loc[idx, "ema27"])
    ema200 = float(df.loc[idx, "ema200"])
    d27 = df["close"] - df["ema27"]
    d200 = df["close"] - df["ema200"]
    ema_dist = df["ema27"] - df["ema200"]
    out = {
        "price_minus_ema27_atr": (close - ema27) / atr,
        "ema27_slope_5": (float(df.loc[idx, "ema27"]) - float(df.loc[idx - 5, "ema27"])) / atr,
        "ema27_slope_10": (float(df.loc[idx, "ema27"]) - float(df.loc[idx - 10, "ema27"])) / atr,
        "ema27_slope_change": (
            (float(df.loc[idx, "ema27"]) - float(df.loc[idx - 5, "ema27"]))
            - (float(df.loc[idx - 5, "ema27"]) - float(df.loc[idx - 10, "ema27"]))
        )
        / atr,
        "fraction_last10_above_ema27": float((df.loc[idx - 9 : idx, "close"] > df.loc[idx - 9 : idx, "ema27"]).mean()),
        "number_of_ema27_crosses_last20": float(crosses(df.loc[idx - 19 : idx, "close"], df.loc[idx - 19 : idx, "ema27"])),
        "distance_change_to_ema27_last10": (float(d27.loc[idx]) - float(d27.loc[idx - 10])) / atr,
        "price_minus_ema200_atr": (close - ema200) / atr,
        "ema200_slope_10": (float(df.loc[idx, "ema200"]) - float(df.loc[idx - 10, "ema200"])) / atr,
        "ema200_slope_30": (float(df.loc[idx, "ema200"]) - float(df.loc[idx - 30, "ema200"])) / atr,
        "fraction_last30_above_ema200": float((df.loc[idx - 29 : idx, "close"] > df.loc[idx - 29 : idx, "ema200"]).mean()),
        "number_of_ema200_crosses_last50": float(crosses(df.loc[idx - 49 : idx, "close"], df.loc[idx - 49 : idx, "ema200"])),
        "distance_change_to_ema200_last20": (float(d200.loc[idx]) - float(d200.loc[idx - 20])) / atr,
        "ema27_minus_ema200_atr": (ema27 - ema200) / atr,
        "ema27_above_ema200": float(ema27 > ema200),
        "ema27_ema200_distance_change_last20": (float(ema_dist.loc[idx]) - float(ema_dist.loc[idx - 20])) / atr,
        "price_between_ema27_ema200": float(min(ema27, ema200) <= close <= max(ema27, ema200)),
        "ema27_turning_against_previous_state": float(
            np.sign(float(df.loc[idx, "ema27"]) - float(df.loc[idx - 5, "ema27"]))
            != np.sign(float(df.loc[idx - 5, "ema27"]) - float(df.loc[idx - 10, "ema27"]))
        ),
    }
    return out


def shifted_pre_net_return_atr(df: pd.DataFrame, event_time: str, shift_bars: int = 0) -> float:
    t = pd.Timestamp(event_time)
    matches = df.index[df["dt"] == t].tolist()
    if not matches:
        raise RuntimeError(f"Event time not found: {event_time}")
    event_idx = matches[0] + shift_bars
    if event_idx < 30 or event_idx >= len(df):
        raise RuntimeError(f"Insufficient pre-window for {event_time} shift {shift_bars}")
    w = df.iloc[event_idx - 30 : event_idx]
    return float(w["close"].iloc[-1] - w["close"].iloc[0]) / atr_at(df, event_idx - 1)


def load_events_with_targets() -> pd.DataFrame:
    events = pd.read_csv(EXP_D / "events_input.csv")
    pre = pd.read_csv(EXP_D / "pre_event_features.csv")
    targets = pd.read_csv(EXP_D / "outcome_targets.csv")
    events["event_time"] = pd.to_datetime(events["event_time"])
    events = events[(events["event_time"] >= RESEARCH_START) & (events["event_time"] <= RESEARCH_END)].copy()
    pre = pre[pre["pre_window"] == 30][["event_id", "pre_net_return_atr"]].copy()
    targets = targets[targets["horizon"] == PRIMARY_H][
        ["event_id", "signed_close_return_atr", "MFE_atr", "signed_efficiency"]
    ].copy()
    base = events.merge(pre, on="event_id", how="left", validate="one_to_one")
    base = base.merge(targets, on="event_id", how="left", validate="one_to_one")
    if len(base) != 60:
        raise RuntimeError(f"Expected 60 events, got {len(base)}")
    base["target_major"] = (base["source_type"] == "MAJOR").astype(int)
    base["severity_score"] = (
        robust_z(base["signed_close_return_atr"].to_numpy(float))
        + robust_z(base["MFE_atr"].to_numpy(float))
        + robust_z(base["signed_efficiency"].to_numpy(float))
    ) / 3.0
    return base.sort_values("event_time").reset_index(drop=True)


def build_feature_frame(shift_bars: int = 0) -> pd.DataFrame:
    df = load_ohlc()
    base = load_events_with_targets()
    rows = []
    for r in base.itertuples():
        row = r._asdict()
        row["event_time"] = str(pd.Timestamp(r.event_time))
        row["pre_net_return_atr"] = shifted_pre_net_return_atr(df, str(r.event_time), shift_bars)
        row.update(ema_features_at(df, str(r.event_time), shift_bars))
        rows.append(row)
    return pd.DataFrame(rows)


def train_predict_logistic(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> tuple[np.ndarray, np.ndarray, dict, dict]:
    scaler = fit_scaler(train[features].to_numpy(float))
    x_train = apply_scaler(train[features].to_numpy(float), scaler)
    x_test = apply_scaler(test[features].to_numpy(float), scaler)
    model = fit_logistic(x_train, train["target_major"].to_numpy(int), c=1.0)
    return predict_logistic(model, x_train), predict_logistic(model, x_test), model, scaler


def group_oof(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pred_rows = []
    coef_rows = []
    for model_name, cols in MODEL_FEATURES.items():
        for group in sorted(features["match_group"].unique()):
            train = features[features["match_group"] != group]
            test = features[features["match_group"] == group]
            _, p_test, model, scaler = train_predict_logistic(train, test, cols)
            for (_, r), p in zip(test.iterrows(), p_test):
                pred_rows.append(
                    {
                        "validation": "group_oof",
                        "fold_group": group,
                        "model": model_name,
                        "event_id": r["event_id"],
                        "event_time": r["event_time"],
                        "match_group": r["match_group"],
                        "source_type": r["source_type"],
                        "direction": r["direction"],
                        "target_major": int(r["target_major"]),
                        "severity_score": float(r["severity_score"]),
                        "predicted_probability": float(p),
                    }
                )
            for name, coef in zip(cols, np.asarray(model["coef"], dtype=float)):
                coef_rows.append({"validation": "group_oof", "fold_group": group, "model": model_name, "feature": name, "coefficient": float(coef)})

    preds = pd.DataFrame(pred_rows)
    metric_rows = []
    for model_name in MODEL_FEATURES:
        d = preds[preds["model"] == model_name]
        metric_rows.append({"validation": "group_oof", "model": model_name, "n": len(d), **classification_metrics(d["target_major"].to_numpy(int), d["predicted_probability"].to_numpy(float), d["severity_score"].to_numpy(float))})
    return preds, pd.DataFrame(metric_rows), pd.DataFrame(coef_rows)


def temporal_split(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_groups = {f"M{i:02d}" for i in range(1, 11)}
    test_groups = {f"M{i:02d}" for i in range(11, 16)}
    train = features[features["match_group"].isin(train_groups)].copy()
    test = features[features["match_group"].isin(test_groups)].copy()
    return train, test


def temporal_validation(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, test = temporal_split(features)
    pred_rows = []
    coef_rows = []
    metric_rows = []
    for model_name, cols in MODEL_FEATURES.items():
        p_train, p_test, model, scaler = train_predict_logistic(train, test, cols)
        for split_name, frame, probs in [("TRAIN", train, p_train), ("TEMPORAL_TEST", test, p_test)]:
            m = classification_metrics(frame["target_major"].to_numpy(int), probs, frame["severity_score"].to_numpy(float))
            metric_rows.append({"validation": "temporal", "split": split_name, "model": model_name, "n": len(frame), **m})
            for (_, r), p in zip(frame.iterrows(), probs):
                pred_rows.append(
                    {
                        "validation": "temporal",
                        "split": split_name,
                        "model": model_name,
                        "event_id": r["event_id"],
                        "event_time": r["event_time"],
                        "match_group": r["match_group"],
                        "source_type": r["source_type"],
                        "direction": r["direction"],
                        "target_major": int(r["target_major"]),
                        "severity_score": float(r["severity_score"]),
                        "predicted_probability": float(p),
                    }
                )
        for name, coef in zip(cols, np.asarray(model["coef"], dtype=float)):
            coef_rows.append({"validation": "temporal", "fold_group": "", "model": model_name, "feature": name, "coefficient": float(coef)})

    severity_rows = []
    for model_name, cols in {"Model 0": MODEL_FEATURES["Model 0"], "Model 3": MODEL_FEATURES["Model 3"]}.items():
        scaler = fit_scaler(train[cols].to_numpy(float))
        x_train = apply_scaler(train[cols].to_numpy(float), scaler)
        x_test = apply_scaler(test[cols].to_numpy(float), scaler)
        ridge = fit_ridge(x_train, train["severity_score"].to_numpy(float), alpha=1.0)
        pred = predict_linear(ridge, x_test)
        severity_rows.append({"validation": "temporal_severity", "split": "TEMPORAL_TEST", "model": model_name, "n": len(test), **regression_metrics(test["severity_score"].to_numpy(float), pred)})
    return pd.DataFrame(pred_rows), pd.DataFrame(metric_rows), pd.DataFrame(coef_rows), pd.DataFrame(severity_rows)


def calibration(preds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for validation in preds["validation"].unique():
        for model in preds["model"].unique():
            d = preds[(preds["validation"] == validation) & (preds["model"] == model)].copy()
            if "split" in d.columns:
                d = d[(d["split"].isna()) | (d["split"] == "TEMPORAL_TEST")]
            if d.empty:
                continue
            d = d.sort_values("predicted_probability").reset_index(drop=True)
            chunks = np.array_split(d, 4)
            for i, chunk in enumerate(chunks, start=1):
                rows.append(
                    {
                        "validation": validation,
                        "model": model,
                        "quartile": i,
                        "n": len(chunk),
                        "probability_mean": float(chunk["predicted_probability"].mean()),
                        "major_rate": float(chunk["target_major"].mean()),
                        "major_count": int(chunk["target_major"].sum()),
                        "severity_mean": float(chunk["severity_score"].mean()),
                    }
                )
    return pd.DataFrame(rows)


def leave_one_temporal_group(features: pd.DataFrame) -> pd.DataFrame:
    train, test = temporal_split(features)
    rows = []
    for remove_group in sorted(test["match_group"].unique()):
        t = test[test["match_group"] != remove_group]
        for model_name in ["Model 0", "Model 3"]:
            _, p, _, _ = train_predict_logistic(train, t, MODEL_FEATURES[model_name])
            rows.append({"removed": remove_group, "removed_type": "match_group", "model": model_name, "n": len(t), **classification_metrics(t["target_major"].to_numpy(int), p, t["severity_score"].to_numpy(float))})
    for event_id in sorted(test[test["target_major"] == 1]["event_id"].unique()):
        t = test[test["event_id"] != event_id]
        for model_name in ["Model 0", "Model 3"]:
            _, p, _, _ = train_predict_logistic(train, t, MODEL_FEATURES[model_name])
            rows.append({"removed": event_id, "removed_type": "major_event", "model": model_name, "n": len(t), **classification_metrics(t["target_major"].to_numpy(int), p, t["severity_score"].to_numpy(float))})
    for direction in ["LONG", "SHORT"]:
        t = test[test["direction"] == direction]
        tr = train[train["direction"] == direction]
        for model_name in ["Model 0", "Model 3"]:
            _, p, _, _ = train_predict_logistic(tr, t, MODEL_FEATURES[model_name])
            rows.append({"removed": "", "removed_type": f"direction_{direction}", "model": model_name, "n": len(t), **classification_metrics(t["target_major"].to_numpy(int), p, t["severity_score"].to_numpy(float))})
    return pd.DataFrame(rows)


def start_shift_results() -> pd.DataFrame:
    rows = []
    for shift in [-3, 0, 3]:
        f = build_feature_frame(shift)
        train, test = temporal_split(f)
        for model_name in ["Model 0", "Model 3"]:
            _, p, model, _ = train_predict_logistic(train, test, MODEL_FEATURES[model_name])
            m = classification_metrics(test["target_major"].to_numpy(int), p, test["severity_score"].to_numpy(float))
            rows.append(
                {
                    "shift_bars": shift,
                    "model": model_name,
                    "n": len(test),
                    "first_coefficient": float(np.asarray(model["coef"])[0]),
                    "first_coefficient_sign": "positive" if float(np.asarray(model["coef"])[0]) > 0 else "negative",
                    **m,
                }
            )
    return pd.DataFrame(rows)


def png_write(path: Path, width: int, height: int, pixels: list[list[tuple[int, int, int]]]) -> None:
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b in row:
            raw.extend([r, g, b])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def draw_scatter(path: Path, x: np.ndarray, y: np.ndarray, colors: np.ndarray | None = None) -> None:
    width, height = 760, 520
    margin = 60
    pixels = [[(255, 255, 255) for _ in range(width)] for _ in range(height)]

    def line(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            t = s / steps
            xx = int(round(x0 + (x1 - x0) * t))
            yy = int(round(y0 + (y1 - y0) * t))
            if 0 <= xx < width and 0 <= yy < height:
                pixels[yy][xx] = color

    def dot(cx: int, cy: int, color: tuple[int, int, int]) -> None:
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                if dx * dx + dy * dy <= 16:
                    xx, yy = cx + dx, cy + dy
                    if 0 <= xx < width and 0 <= yy < height:
                        pixels[yy][xx] = color

    line(margin, height - margin, width - margin, height - margin, (20, 20, 20))
    line(margin, margin, margin, height - margin, (20, 20, 20))
    if len(x):
        xmin, xmax = float(np.min(x)), float(np.max(x))
        ymin, ymax = float(np.min(y)), float(np.max(y))
        if xmin == xmax:
            xmin -= 1
            xmax += 1
        if ymin == ymax:
            ymin -= 1
            ymax += 1
        for i, (xi, yi) in enumerate(zip(x, y)):
            px = margin + int((xi - xmin) / (xmax - xmin) * (width - 2 * margin))
            py = height - margin - int((yi - ymin) / (ymax - ymin) * (height - 2 * margin))
            color = (0, 110, 180) if colors is None or colors[i] == 0 else (210, 50, 50)
            dot(px, py, color)
    png_write(path, width, height, pixels)


def draw_calibration(path: Path, cal: pd.DataFrame) -> None:
    d = cal[(cal["validation"] == "temporal") & (cal["model"] == "Model 3")].sort_values("quartile")
    draw_scatter(path, d["probability_mean"].to_numpy(float), d["major_rate"].to_numpy(float))


def draw_roc(path: Path, preds: pd.DataFrame) -> None:
    d = preds[(preds["split"] == "TEMPORAL_TEST") & (preds["model"] == "Model 3")].sort_values("predicted_probability")
    y = d["target_major"].to_numpy(int)
    p = d["predicted_probability"].to_numpy(float)
    thresholds = np.r_[np.inf, np.sort(np.unique(p))[::-1], -np.inf]
    xs, ys = [], []
    for th in thresholds:
        pred = p >= th
        tp = ((pred == 1) & (y == 1)).sum()
        fp = ((pred == 1) & (y == 0)).sum()
        pos = max((y == 1).sum(), 1)
        neg = max((y == 0).sum(), 1)
        xs.append(fp / neg)
        ys.append(tp / pos)
    draw_scatter(path, np.asarray(xs), np.asarray(ys))


def make_pine(temporal_preds: pd.DataFrame) -> None:
    d = temporal_preds[temporal_preds["model"] == "Model 3"].sort_values("event_time").copy()
    times = []
    labels = []
    colors = []
    probs = []
    for r in d.itertuples():
        ts = pd.Timestamp(r.event_time)
        times.append(f'timestamp("Etc/UTC", {ts.year}, {ts.month}, {ts.day}, {ts.hour}, {ts.minute})')
        labels.append(f'"{r.event_id} {r.source_type} p={r.predicted_probability:.2f}"')
        colors.append("1" if r.source_type == "MAJOR" else "0")
        probs.append(f"{float(r.predicted_probability):.6f}")
    text = f'''//@version=6
indicator("EXP-005F EMA Context Review", overlay=true, max_lines_count=200, max_labels_count=200)

// Fixed visual research markup only. The model is not calculated in Pine.
// Use on ADAUSDT 4H. Recommended ticker: BYBIT:ADAUSDT.P; fallback: BINANCE:ADAUSDT.
showEvents = input.bool(true, "showEvents")
showLabels = input.bool(true, "showLabels")
showHoldoutShade = input.bool(true, "showHoldoutShade")

ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
plot(ema27, "EMA27", color=color.new(color.teal, 0), linewidth=2)
plot(ema200, "EMA200", color=color.new(color.orange, 0), linewidth=2)

holdoutStart = timestamp("Etc/UTC", 2025, 7, 1, 4, 0)
holdoutEnd = timestamp("Etc/UTC", 2026, 7, 1, 0, 0)
bgcolor(showHoldoutShade and time >= holdoutStart and time <= holdoutEnd ? color.new(color.gray, 86) : na)

var int[] eventTimes = array.from({", ".join(times)})
var string[] eventLabels = array.from({", ".join(labels)})
var int[] eventClasses = array.from({", ".join(colors)})
var float[] eventProbs = array.from({", ".join(probs)})

if showEvents
    for i = 0 to array.size(eventTimes) - 1
        int et = array.get(eventTimes, i)
        int cls = array.get(eventClasses, i)
        string labelText = array.get(eventLabels, i)
        float prob = array.get(eventProbs, i)
        color c = cls == 1 ? color.new(color.red, 0) : color.new(color.blue, 0)
        if time == et
            line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=c, width=cls == 1 ? 2 : 1, style=cls == 1 ? line.style_solid : line.style_dashed)
            if showLabels
                label.new(time, high, labelText, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(c, 0), textcolor=color.white, size=size.tiny)
'''
    (OUT / "EMA_CONTEXT_REVIEW.pine").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    features = build_feature_frame(0)
    features.to_csv(OUT / "events_with_ema_features.csv", index=False)

    group_preds, group_metrics, group_coefs = group_oof(features)
    temporal_preds, temporal_metrics, temporal_coefs, severity_metrics = temporal_validation(features)
    all_temporal_metrics = pd.concat([temporal_metrics, severity_metrics], ignore_index=True, sort=False)
    cal = calibration(pd.concat([group_preds, temporal_preds], ignore_index=True, sort=False))
    loo = leave_one_temporal_group(features)
    shift = start_shift_results()

    group_preds.to_csv(OUT / "group_oof_predictions.csv", index=False)
    group_metrics.to_csv(OUT / "group_oof_metrics.csv", index=False)
    temporal_preds.to_csv(OUT / "temporal_predictions.csv", index=False)
    all_temporal_metrics.to_csv(OUT / "temporal_metrics.csv", index=False)
    pd.concat([group_coefs, temporal_coefs], ignore_index=True, sort=False).to_csv(OUT / "model_coefficients.csv", index=False)
    loo.to_csv(OUT / "leave_one_group_out.csv", index=False)
    shift.to_csv(OUT / "start_shift_results.csv", index=False)
    cal.to_csv(OUT / "calibration_table.csv", index=False)

    draw_scatter(
        OUT / "ema_feature_distributions.png",
        features["price_minus_ema27_atr"].to_numpy(float),
        features["price_minus_ema200_atr"].to_numpy(float),
        features["target_major"].to_numpy(int),
    )
    draw_roc(OUT / "temporal_roc.png", temporal_preds)
    draw_calibration(OUT / "temporal_calibration.png", cal)
    make_pine(temporal_preds)

    print("EXP-005F complete")
    print(group_metrics.to_string(index=False))
    print(all_temporal_metrics.to_string(index=False))


if __name__ == "__main__":
    main()
