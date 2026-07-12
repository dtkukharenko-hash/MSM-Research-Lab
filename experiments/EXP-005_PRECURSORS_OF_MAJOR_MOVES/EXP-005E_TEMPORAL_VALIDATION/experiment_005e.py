#!/usr/bin/env python3
"""EXP-005E: fixed temporal validation of EXP-005D severity signal."""

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
OUT = EXP / "EXP-005E_TEMPORAL_VALIDATION/artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

RESEARCH_START = pd.Timestamp("2023-07-01 00:00")
RESEARCH_END = pd.Timestamp("2025-07-01 00:00")
HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")
HOLDOUT_END = pd.Timestamp("2026-07-01 00:00")
PRIMARY_H = 30


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
        rank = (i + j) / 2 + 1
        ranks[order[i : j + 1]] = rank
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


def metrics(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    err = pred - y
    sst = float(np.sum((y - np.mean(y)) ** 2))
    sse = float(np.sum(err**2))
    return {
        "spearman": spearman(pred, y),
        "pearson": pearson(pred, y),
        "r2": 0.0 if sst == 0 else 1.0 - sse / sst,
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(math.sqrt(np.mean(err**2))),
    }


def robust_params(values: pd.Series) -> dict[str, float]:
    arr = values.to_numpy(float)
    med = float(np.nanmedian(arr))
    iqr = float(np.nanpercentile(arr, 75) - np.nanpercentile(arr, 25))
    if not np.isfinite(iqr) or iqr == 0:
        iqr = 1.0
    return {"median": med, "iqr": iqr}


def apply_robust(values: pd.Series, params: dict[str, float]) -> np.ndarray:
    return (values.to_numpy(float) - params["median"]) / params["iqr"]


def fit_linear(x: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray | float]:
    x = np.asarray(x, dtype=float).reshape(-1, 1)
    y = np.asarray(y, dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.pinv(design) @ y
    return {"intercept": float(beta[0]), "coef": np.asarray(beta[1:], dtype=float)}


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> dict[str, np.ndarray | float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mean_x = x.mean(axis=0)
    std_x = x.std(axis=0)
    std_x[std_x == 0] = 1.0
    z = (x - mean_x) / std_x
    design = np.column_stack([np.ones(len(z)), z])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    beta = np.linalg.pinv(design.T @ design + penalty) @ design.T @ y
    return {
        "intercept": float(beta[0]),
        "coef": np.asarray(beta[1:], dtype=float),
        "mean_x": mean_x,
        "std_x": std_x,
        "alpha": alpha,
    }


def predict_linear(model: dict[str, np.ndarray | float], x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float).reshape(-1, 1)
    return float(model["intercept"]) + x @ np.asarray(model["coef"], dtype=float)


def predict_ridge(model: dict[str, np.ndarray | float], x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    z = (x - np.asarray(model["mean_x"], dtype=float)) / np.asarray(model["std_x"], dtype=float)
    return float(model["intercept"]) + z @ np.asarray(model["coef"], dtype=float)


def sign_dir(direction: str) -> int:
    return 1 if direction == "LONG" else -1


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
    return df[(df["dt"] >= RESEARCH_START) & (df["dt"] <= RESEARCH_END)].copy().reset_index(drop=True)


def atr_at(df: pd.DataFrame, idx: int, n: int = 14) -> float:
    v = float(df.loc[max(0, idx - n + 1) : idx, "true_range"].mean())
    return v if v > 0 else 1e-12


def shifted_pre_net_return_atr(df: pd.DataFrame, event_time: str, direction: str, shift_bars: int) -> float:
    t = pd.Timestamp(event_time)
    matches = df.index[df["dt"] == t].tolist()
    if not matches:
        return float("nan")
    idx = matches[0] + shift_bars
    if idx < 30 or idx >= len(df):
        return float("nan")
    w = df.iloc[idx - 30 : idx]
    net = float(w["close"].iloc[-1] - w["close"].iloc[0])
    return net / atr_at(df, idx - 1)


def load_base() -> pd.DataFrame:
    events = pd.read_csv(EXP_D / "events_input.csv")
    features = pd.read_csv(EXP_D / "pre_event_features.csv")
    outcomes = pd.read_csv(EXP_D / "outcome_targets.csv")
    events["event_time"] = pd.to_datetime(events["event_time"])
    events = events[(events["event_time"] >= RESEARCH_START) & (events["event_time"] <= RESEARCH_END)].copy()

    features = features[features["pre_window"] == 30].copy()
    outcomes = outcomes[outcomes["horizon"] == PRIMARY_H].copy()

    base = events.merge(
        features[
            [
                "event_id",
                "pre_window",
                "pre_net_return_atr",
                "pre_signed_efficiency",
            ]
        ],
        on="event_id",
        how="left",
        validate="one_to_one",
    )
    base = base.merge(
        outcomes[
            [
                "event_id",
                "signed_close_return_atr",
                "MFE_atr",
                "signed_efficiency",
            ]
        ],
        on="event_id",
        how="left",
        validate="one_to_one",
    )
    if len(base) != 60:
        raise RuntimeError(f"Expected 60 events, got {len(base)}")
    required = [
        "event_id",
        "source_type",
        "direction",
        "event_time",
        "match_group",
        "pre_net_return_atr",
        "pre_signed_efficiency",
        "signed_close_return_atr",
        "MFE_atr",
        "signed_efficiency",
    ]
    if base[required].isna().any().any():
        missing = base[required].columns[base[required].isna().any()].tolist()
        raise RuntimeError(f"Missing values in columns: {missing}")
    return base


def assign_split(base: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    major = base[base["source_type"] == "MAJOR"].sort_values("event_time")
    group_times = major[["match_group", "event_time"]].drop_duplicates()
    n_groups = len(group_times)
    train_n = int(math.floor(n_groups * 0.70))
    train_groups = set(group_times.iloc[:train_n]["match_group"])
    test_groups = set(group_times.iloc[train_n:]["match_group"])
    base = base.copy()
    base["split"] = np.where(base["match_group"].isin(train_groups), "TRAIN", "TEMPORAL_TEST")
    split_info = {
        "n_groups": n_groups,
        "train_group_count": len(train_groups),
        "test_group_count": len(test_groups),
        "train_groups": sorted(train_groups),
        "test_groups": sorted(test_groups),
        "train_last_major_time": str(group_times.iloc[train_n - 1]["event_time"]),
        "test_first_major_time": str(group_times.iloc[train_n]["event_time"]),
        "split_rule": "first floor(15 * 0.70) match_groups by major event time are TRAIN; remaining groups are TEMPORAL_TEST",
    }
    return base, split_info


def add_train_normalized_target(base: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    base = base.copy()
    train = base[base["split"] == "TRAIN"]
    params = {
        "signed_close_return_atr": robust_params(train["signed_close_return_atr"]),
        "MFE_atr": robust_params(train["MFE_atr"]),
        "signed_efficiency": robust_params(train["signed_efficiency"]),
    }
    for col, p in params.items():
        base[f"z_{col}"] = apply_robust(base[col], p)
    base["severity_score"] = (
        base["z_signed_close_return_atr"] + base["z_MFE_atr"] + base["z_signed_efficiency"]
    ) / 3.0
    return base, params


def quartile_rows(preds: pd.DataFrame, model_name: str) -> list[dict]:
    rows = []
    d = preds[preds["model"] == model_name].sort_values("prediction").reset_index(drop=True)
    chunks = np.array_split(d, 4)
    for i, chunk in enumerate(chunks, start=1):
        rows.append(
            {
                "model": model_name,
                "quartile": i,
                "n": len(chunk),
                "predicted_mean": float(chunk["prediction"].mean()),
                "actual_mean": float(chunk["severity_score"].mean()),
                "actual_median": float(chunk["severity_score"].median()),
            }
        )
    return rows


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


def draw_scatter(path: Path, x: np.ndarray, y: np.ndarray, title: str) -> None:
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
        for xi, yi in zip(x, y):
            px = margin + int((xi - xmin) / (xmax - xmin) * (width - 2 * margin))
            py = height - margin - int((yi - ymin) / (ymax - ymin) * (height - 2 * margin))
            dot(px, py, (0, 105, 180))
    png_write(path, width, height, pixels)


def draw_rank(path: Path, preds: pd.DataFrame) -> None:
    d = preds[preds["model"] == "Model A"].sort_values("prediction").reset_index(drop=True)
    x = np.arange(len(d), dtype=float)
    draw_scatter(path, x, d["severity_score"].to_numpy(float), "Temporal rank plot")


def main() -> None:
    ensure_dirs()
    base = load_base()
    base, split_info = assign_split(base)
    base, target_params = add_train_normalized_target(base)

    split_cols = [
        "event_id",
        "source_type",
        "direction",
        "event_time",
        "match_group",
        "split",
        "pre_net_return_atr",
        "pre_signed_efficiency",
        "severity_score",
    ]
    base[split_cols].sort_values(["split", "event_time", "event_id"]).to_csv(OUT / "temporal_split.csv", index=False)

    train = base[base["split"] == "TRAIN"].copy()
    test = base[base["split"] == "TEMPORAL_TEST"].copy()
    train_mean = float(train["severity_score"].mean())

    models: dict[str, dict] = {
        "Baseline": {"type": "baseline", "prediction": train_mean},
        "Model A": fit_linear(train[["pre_net_return_atr"]].to_numpy(), train["severity_score"].to_numpy()),
        "Model B": fit_linear(train[["pre_signed_efficiency"]].to_numpy(), train["severity_score"].to_numpy()),
        "Model C": fit_ridge(
            train[["pre_net_return_atr", "pre_signed_efficiency"]].to_numpy(),
            train["severity_score"].to_numpy(),
            alpha=1.0,
        ),
    }

    pred_rows = []
    metric_rows = []
    for name, model in models.items():
        if model.get("type") == "baseline":
            train_pred = np.full(len(train), model["prediction"])
            test_pred = np.full(len(test), model["prediction"])
            coef_sign = "NA"
            coefficient = 0.0
        elif name == "Model C":
            train_pred = predict_ridge(model, train[["pre_net_return_atr", "pre_signed_efficiency"]].to_numpy())
            test_pred = predict_ridge(model, test[["pre_net_return_atr", "pre_signed_efficiency"]].to_numpy())
            coefficient = float(np.asarray(model["coef"])[0])
            coef_sign = "positive" if coefficient > 0 else "negative" if coefficient < 0 else "zero"
        elif name == "Model A":
            train_pred = predict_linear(model, train[["pre_net_return_atr"]].to_numpy())
            test_pred = predict_linear(model, test[["pre_net_return_atr"]].to_numpy())
            coefficient = float(np.asarray(model["coef"])[0])
            coef_sign = "positive" if coefficient > 0 else "negative" if coefficient < 0 else "zero"
        else:
            train_pred = predict_linear(model, train[["pre_signed_efficiency"]].to_numpy())
            test_pred = predict_linear(model, test[["pre_signed_efficiency"]].to_numpy())
            coefficient = float(np.asarray(model["coef"])[0])
            coef_sign = "positive" if coefficient > 0 else "negative" if coefficient < 0 else "zero"

        for split_name, frame, pred in [("TRAIN", train, train_pred), ("TEMPORAL_TEST", test, test_pred)]:
            m = metrics(frame["severity_score"].to_numpy(), pred)
            metric_rows.append(
                {
                    "model": name,
                    "split": split_name,
                    "n": len(frame),
                    "spearman": m["spearman"],
                    "pearson": m["pearson"],
                    "r2": m["r2"],
                    "mae": m["mae"],
                    "rmse": m["rmse"],
                    "coefficient": coefficient,
                    "coefficient_sign": coef_sign,
                }
            )
            for (_, r), p in zip(frame.iterrows(), pred):
                pred_rows.append(
                    {
                        "event_id": r["event_id"],
                        "source_type": r["source_type"],
                        "direction": r["direction"],
                        "event_time": r["event_time"],
                        "match_group": r["match_group"],
                        "split": split_name,
                        "model": name,
                        "prediction": float(p),
                        "severity_score": float(r["severity_score"]),
                    }
                )

    preds = pd.DataFrame(pred_rows)
    quartiles = pd.DataFrame(quartile_rows(preds[preds["split"] == "TEMPORAL_TEST"], "Model A"))
    for row in quartiles.to_dict("records"):
        metric_rows.append(
            {
                "model": row["model"],
                "split": f"TEMPORAL_TEST_PRED_Q{row['quartile']}",
                "n": row["n"],
                "spearman": "",
                "pearson": "",
                "r2": "",
                "mae": "",
                "rmse": "",
                "coefficient": "",
                "coefficient_sign": "",
                "predicted_mean": row["predicted_mean"],
                "actual_mean": row["actual_mean"],
                "actual_median": row["actual_median"],
            }
        )

    preds.to_csv(OUT / "temporal_test_predictions.csv", index=False)
    pd.DataFrame(metric_rows).to_csv(OUT / "temporal_metrics.csv", index=False)

    model_a_test = preds[(preds["split"] == "TEMPORAL_TEST") & (preds["model"] == "Model A")].copy()
    concentration_rows = []
    checks = [
        ("all_test", model_a_test),
        ("remove_top1_actual", model_a_test.drop(model_a_test["severity_score"].idxmax())),
        ("remove_top1_prediction", model_a_test.drop(model_a_test["prediction"].idxmax())),
    ]
    for name, frame in checks:
        m = metrics(frame["severity_score"].to_numpy(), frame["prediction"].to_numpy())
        concentration_rows.append({"test": name, "removed_group": "", "n": len(frame), **m})
    for group in sorted(model_a_test["match_group"].unique()):
        frame = model_a_test[model_a_test["match_group"] != group]
        m = metrics(frame["severity_score"].to_numpy(), frame["prediction"].to_numpy())
        concentration_rows.append({"test": "leave_one_group_out", "removed_group": group, "n": len(frame), **m})
    pd.DataFrame(concentration_rows).to_csv(OUT / "leave_one_group_out_test.csv", index=False)

    ohlc = load_ohlc()
    shift_rows = []
    for shift in [-3, 0, 3]:
        shifted = base.copy()
        shifted["shifted_pre_net_return_atr"] = [
            shifted_pre_net_return_atr(ohlc, str(r.event_time), r.direction, shift) for r in shifted.itertuples()
        ]
        shifted = shifted.dropna(subset=["shifted_pre_net_return_atr"])
        shifted_train = shifted[shifted["split"] == "TRAIN"]
        shifted_test = shifted[shifted["split"] == "TEMPORAL_TEST"]
        model = fit_linear(shifted_train[["shifted_pre_net_return_atr"]].to_numpy(), shifted_train["severity_score"].to_numpy())
        pred = predict_linear(model, shifted_test[["shifted_pre_net_return_atr"]].to_numpy())
        m = metrics(shifted_test["severity_score"].to_numpy(), pred)
        shift_rows.append(
            {
                "shift_bars": shift,
                "train_n": len(shifted_train),
                "test_n": len(shifted_test),
                "coefficient": float(np.asarray(model["coef"])[0]),
                "coefficient_sign": "positive"
                if float(np.asarray(model["coef"])[0]) > 0
                else "negative"
                if float(np.asarray(model["coef"])[0]) < 0
                else "zero",
                **m,
            }
        )
    pd.DataFrame(shift_rows).to_csv(OUT / "start_shift_temporal.csv", index=False)

    nonmajor_train = train[train["source_type"] == "MATCHED_NON_MAJOR"]
    nonmajor_test = test[test["source_type"] == "MATCHED_NON_MAJOR"]
    major_test = test[test["source_type"] == "MAJOR"]
    nonmajor_model = fit_linear(
        nonmajor_train[["pre_net_return_atr"]].to_numpy(),
        nonmajor_train["severity_score"].to_numpy(),
    )
    nm_pred = predict_linear(nonmajor_model, nonmajor_test[["pre_net_return_atr"]].to_numpy())
    mj_pred = predict_linear(nonmajor_model, major_test[["pre_net_return_atr"]].to_numpy())
    nm_metrics = metrics(nonmajor_test["severity_score"].to_numpy(), nm_pred)
    mj_rank = spearman(mj_pred, major_test["severity_score"].to_numpy()) if len(major_test) > 1 else 0.0
    secondary = {
        "nonmajor_model_coefficient": float(np.asarray(nonmajor_model["coef"])[0]),
        "nonmajor_test_n": len(nonmajor_test),
        "nonmajor_test_metrics": nm_metrics,
        "test_major_n": len(major_test),
        "test_major_rank_spearman": mj_rank,
        "test_major_predictions": [
            {
                "event_id": r.event_id,
                "event_time": str(r.event_time),
                "prediction": float(p),
                "severity_score": float(r.severity_score),
            }
            for r, p in zip(major_test.itertuples(), mj_pred)
        ],
    }

    params = {
        "research_period": {"start": str(RESEARCH_START), "end": str(RESEARCH_END)},
        "true_holdout_not_opened": {"start": str(HOLDOUT_START), "end": str(HOLDOUT_END)},
        "target_horizon": PRIMARY_H,
        "target_component_train_params": target_params,
        "temporal_split": split_info,
        "models": {
            "Model A": {"feature": "pre_net_return_atr", "model": "linear_regression"},
            "Model B": {"feature": "pre_signed_efficiency", "model": "linear_regression"},
            "Model C": {
                "features": ["pre_net_return_atr", "pre_signed_efficiency"],
                "model": "ridge_regression",
                "alpha": 1.0,
            },
            "Baseline": {"model": "train_mean_severity", "value": train_mean},
        },
        "fitted_parameters": {
            "Model A": {
                "intercept": float(models["Model A"]["intercept"]),
                "coefficient": float(np.asarray(models["Model A"]["coef"])[0]),
            },
            "Model B": {
                "intercept": float(models["Model B"]["intercept"]),
                "coefficient": float(np.asarray(models["Model B"]["coef"])[0]),
            },
            "Model C": {
                "intercept": float(models["Model C"]["intercept"]),
                "coefficients": [float(x) for x in np.asarray(models["Model C"]["coef"])],
            },
        },
        "nonmajor_secondary": secondary,
    }
    (OUT / "train_parameters.json").write_text(json.dumps(params, indent=2), encoding="utf-8")

    draw_scatter(
        OUT / "temporal_predicted_vs_actual.png",
        model_a_test["prediction"].to_numpy(float),
        model_a_test["severity_score"].to_numpy(float),
        "Model A temporal test",
    )
    draw_rank(OUT / "temporal_rank_plot.png", preds[preds["split"] == "TEMPORAL_TEST"])

    print("EXP-005E temporal validation complete")
    print(pd.DataFrame(metric_rows).head(12).to_string(index=False))


if __name__ == "__main__":
    main()
