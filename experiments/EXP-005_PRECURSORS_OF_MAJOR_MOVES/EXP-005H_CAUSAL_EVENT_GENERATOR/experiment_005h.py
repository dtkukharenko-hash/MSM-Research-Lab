#!/usr/bin/env python3
"""EXP-005H: causal event generator on research only."""

from __future__ import annotations

import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES"
EXP_B = EXP / "EXP-005B_SELECTION_BIAS_TEST/artifacts"
EXP_F = EXP / "EXP-005F_EMA_CONTEXT_INCREMENT/artifacts"
OUT = EXP / "EXP-005H_CAUSAL_EVENT_GENERATOR/artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

RESEARCH_START = pd.Timestamp("2023-07-01 00:00")
RESEARCH_END = pd.Timestamp("2025-07-01 00:00")
DEV_END = pd.Timestamp("2024-12-19 23:59")
PSEUDO_START = pd.Timestamp("2024-12-20 00:00")
TRUE_HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")
TRUE_HOLDOUT_END = pd.Timestamp("2026-07-01 00:00")

FEATURES = [
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
]

SPEC = {
    "name": "EXP-005H causal event generator v1",
    "frozen_before_pseudo_holdout": True,
    "true_holdout_used": False,
    "development_period": {"start": str(RESEARCH_START), "end": str(DEV_END)},
    "pseudo_holdout_period": {"start": str(PSEUDO_START), "end": str(RESEARCH_END)},
    "true_holdout_period_not_used": {"start": str(TRUE_HOLDOUT_START), "end": str(TRUE_HOLDOUT_END)},
    "inputs": ["OHLC", "EMA27", "EMA200", "closed bars up to t"],
    "conditions": {
        "LONG": [
            "pre_net_return_atr_30 <= -2.0",
            "close[t] > close[t-1]",
            "distance_to_ema27[t] > distance_to_ema27[t-3]",
            "price_minus_ema27_atr[t] >= -1.5",
            "number_of_ema200_crosses_last50 <= 12",
        ],
        "SHORT": [
            "pre_net_return_atr_30 >= 2.0",
            "close[t] < close[t-1]",
            "distance_to_ema27[t] < distance_to_ema27[t-3]",
            "price_minus_ema27_atr[t] <= 1.5",
            "number_of_ema200_crosses_last50 <= 12",
        ],
    },
    "cooldown": {"any_direction_bars": 6, "same_direction_bars": 12},
    "outcome_label_status": "BLOCKED_BY_NONFORMAL_MAJOR_OUTCOME_DEFINITION",
}


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


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


def crosses(a: pd.Series, b: pd.Series) -> int:
    diff = (a - b).to_numpy(float)
    signs = np.sign(diff)
    count = 0
    for x, y in zip(signs, signs[1:]):
        if x and y and x != y:
            count += 1
    return count


def feature_at(df: pd.DataFrame, event_idx: int) -> dict[str, float]:
    # Model features use t-1 closed context, matching EXP-005F.
    idx = event_idx - 1
    atr = atr_at(df, idx)
    close = float(df.loc[idx, "close"])
    ema27 = float(df.loc[idx, "ema27"])
    ema200 = float(df.loc[idx, "ema200"])
    w = df.iloc[event_idx - 30 : event_idx]
    d27 = df["close"] - df["ema27"]
    d200 = df["close"] - df["ema200"]
    ema_dist = df["ema27"] - df["ema200"]
    return {
        "pre_net_return_atr": float(w["close"].iloc[-1] - w["close"].iloc[0]) / atr,
        "price_minus_ema27_atr": (close - ema27) / atr,
        "ema27_slope_5": (float(df.loc[idx, "ema27"]) - float(df.loc[idx - 5, "ema27"])) / atr,
        "ema27_slope_10": (float(df.loc[idx, "ema27"]) - float(df.loc[idx - 10, "ema27"])) / atr,
        "ema27_slope_change": ((float(df.loc[idx, "ema27"]) - float(df.loc[idx - 5, "ema27"])) - (float(df.loc[idx - 5, "ema27"]) - float(df.loc[idx - 10, "ema27"]))) / atr,
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


def generator_feature_at_t(df: pd.DataFrame, idx: int) -> dict[str, float]:
    atr = atr_at(df, idx)
    w = df.iloc[idx - 30 + 1 : idx + 1]
    d27 = df["close"] - df["ema27"]
    return {
        "pre_net_return_atr_t": float(w["close"].iloc[-1] - w["close"].iloc[0]) / atr,
        "price_minus_ema27_atr_t": (float(df.loc[idx, "close"]) - float(df.loc[idx, "ema27"])) / atr,
        "distance_change_to_ema27_last3_t": (float(d27.loc[idx]) - float(d27.loc[idx - 3])) / atr,
        "number_of_ema200_crosses_last50_t": float(crosses(df.loc[idx - 49 : idx, "close"], df.loc[idx - 49 : idx, "ema200"])),
    }


def generate_events(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    last_any = -10_000
    last_by_dir = {"LONG": -10_000, "SHORT": -10_000}
    seq = 1
    for idx in range(250, len(df)):
        t = df.loc[idx, "dt"]
        if t < start or t > end:
            continue
        if idx - last_any < SPEC["cooldown"]["any_direction_bars"]:
            continue
        gf = generator_feature_at_t(df, idx)
        close = float(df.loc[idx, "close"])
        prev_close = float(df.loc[idx - 1, "close"])
        candidates = []
        if (
            gf["pre_net_return_atr_t"] <= -2.0
            and close > prev_close
            and gf["distance_change_to_ema27_last3_t"] > 0
            and gf["price_minus_ema27_atr_t"] >= -1.5
            and gf["number_of_ema200_crosses_last50_t"] <= 12
            and idx - last_by_dir["LONG"] >= SPEC["cooldown"]["same_direction_bars"]
        ):
            candidates.append("LONG")
        if (
            gf["pre_net_return_atr_t"] >= 2.0
            and close < prev_close
            and gf["distance_change_to_ema27_last3_t"] < 0
            and gf["price_minus_ema27_atr_t"] <= 1.5
            and gf["number_of_ema200_crosses_last50_t"] <= 12
            and idx - last_by_dir["SHORT"] >= SPEC["cooldown"]["same_direction_bars"]
        ):
            candidates.append("SHORT")
        if not candidates:
            continue
        direction = candidates[0]
        model_features = feature_at(df, idx)
        event_id = f"CG{seq:04d}"
        rows.append(
            {
                "event_id": event_id,
                "event_time": str(t),
                "event_idx": idx,
                "direction": direction,
                "rule_version": "EXP-005H-v1",
                "causal_available": True,
                **gf,
                **model_features,
            }
        )
        seq += 1
        last_any = idx
        last_by_dir[direction] = idx
    return pd.DataFrame(rows)


def load_known_events() -> pd.DataFrame:
    major = pd.read_csv(EXP_B / "major_starts.csv")
    failed = pd.read_csv(EXP_B / "failed_turns.csv")
    rows = []
    for r in major.itertuples():
        rows.append({"known_id": r.move_id, "known_time": pd.Timestamp(r.start_time), "direction": r.direction, "known_label": "MAJOR", "period": "development" if pd.Timestamp(r.start_time) <= DEV_END else "pseudo_holdout"})
    for r in failed.itertuples():
        ct = pd.Timestamp(r.candidate_time)
        rows.append({"known_id": r.failed_id, "known_time": ct, "direction": r.direction, "known_label": "NON_MAJOR", "period": "development" if ct <= DEV_END else "pseudo_holdout"})
    return pd.DataFrame(rows)


def match_events(generated: pd.DataFrame, known: pd.DataFrame, period: str, tolerance_bars: int = 3) -> pd.DataFrame:
    rows = []
    known_p = known[known["period"] == period].copy()
    generated_p = generated.copy()
    for k in known_p.itertuples():
        same = generated_p[generated_p["direction"] == k.direction].copy()
        if same.empty:
            rows.append({"known_id": k.known_id, "known_label": k.known_label, "known_time": str(k.known_time), "direction": k.direction, "matched_event_id": "", "distance_bars": "", "match_status": "RETROSPECTIVE_ONLY"})
            continue
        same["distance_bars"] = ((pd.to_datetime(same["event_time"]) - k.known_time).abs() / pd.Timedelta(hours=4)).astype(int)
        best = same.sort_values("distance_bars").iloc[0]
        if int(best["distance_bars"]) <= tolerance_bars:
            rows.append({"known_id": k.known_id, "known_label": k.known_label, "known_time": str(k.known_time), "direction": k.direction, "matched_event_id": best["event_id"], "distance_bars": int(best["distance_bars"]), "match_status": "MATCHED"})
        else:
            rows.append({"known_id": k.known_id, "known_label": k.known_label, "known_time": str(k.known_time), "direction": k.direction, "matched_event_id": best["event_id"], "distance_bars": int(best["distance_bars"]), "match_status": "RETROSPECTIVE_ONLY"})
    return pd.DataFrame(rows)


def fit_scaler(x: np.ndarray) -> dict[str, np.ndarray]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std == 0] = 1.0
    return {"mean": mean, "std": std}


def apply_scaler(x: np.ndarray, scaler: dict[str, np.ndarray]) -> np.ndarray:
    return (x - scaler["mean"]) / scaler["std"]


def class_weights(y: np.ndarray) -> np.ndarray:
    n = len(y)
    pos = max(int(y.sum()), 1)
    neg = max(n - pos, 1)
    return np.where(y == 1, n / (2 * pos), n / (2 * neg)).astype(float)


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -40, 40)))


def fit_logistic(x: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray | float]:
    beta = np.zeros(x.shape[1] + 1)
    wgt = class_weights(y)
    lr = 0.08
    alpha = 1.0
    for _ in range(5000):
        p = sigmoid(beta[0] + x @ beta[1:])
        err = (p - y) * wgt
        grad = np.empty_like(beta)
        grad[0] = err.mean()
        grad[1:] = (x.T @ err) / len(y) + alpha * beta[1:] / len(y)
        beta -= lr * grad
    return {"intercept": float(beta[0]), "coef": beta[1:]}


def predict(model: dict[str, np.ndarray | float], x: np.ndarray) -> np.ndarray:
    return sigmoid(float(model["intercept"]) + x @ np.asarray(model["coef"]))


def train_and_predict(dev_known: pd.DataFrame, pseudo_candidates: pd.DataFrame) -> pd.DataFrame:
    research = pd.read_csv(EXP_F / "events_with_ema_features.csv")
    research["event_time"] = pd.to_datetime(research["event_time"])
    train = research[research["event_time"] <= DEV_END].copy()
    x = train[FEATURES].to_numpy(float)
    y = train["target_major"].to_numpy(int)
    scaler = fit_scaler(x)
    model = fit_logistic(apply_scaler(x, scaler), y)
    if pseudo_candidates.empty:
        return pseudo_candidates.assign(predicted_probability=[])
    px = apply_scaler(pseudo_candidates[FEATURES].to_numpy(float), scaler)
    out = pseudo_candidates.copy()
    out["predicted_probability_model3"] = predict(model, px)
    return out


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def png_write(path: Path, width: int, height: int, color=(245, 245, 245)) -> None:
    raw = bytearray()
    for _ in range(height):
        raw.append(0)
        for _ in range(width):
            raw.extend(color)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def write_pdf(path: Path) -> None:
    text = b"BT /F1 12 Tf 50 760 Td (EXP-005H Causal Event Generator - EVENT_DEFINITION_BLOCKED) Tj ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n" + text + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(bytes(out))


def main() -> None:
    ensure_dirs()
    (OUT / "causal_event_specification.json").write_text(json.dumps(SPEC, indent=2), encoding="utf-8")
    df = load_ohlc()
    dev_candidates = generate_events(df, RESEARCH_START, DEV_END)
    pseudo_candidates = generate_events(df, PSEUDO_START, RESEARCH_END)
    known = load_known_events()
    dev_match = match_events(dev_candidates, known, "development")
    pseudo_match = match_events(pseudo_candidates, known, "pseudo_holdout")
    predictions = train_and_predict(dev_match, pseudo_candidates)

    dev_candidates.to_csv(OUT / "development_events.csv", index=False)
    pseudo_candidates.to_csv(OUT / "pseudo_holdout_candidates.csv", index=False)
    predictions.to_csv(OUT / "pseudo_holdout_predictions.csv", index=False)
    pd.concat([dev_match.assign(period="development"), pseudo_match.assign(period="pseudo_holdout")], ignore_index=True).to_csv(OUT / "event_matching.csv", index=False)

    pseudo_labels = pseudo_candidates[["event_id", "event_time", "direction"]].copy()
    pseudo_labels["outcome_label"] = "UNKNOWN"
    pseudo_labels["label_status"] = "BLOCKED"
    pseudo_labels["reason"] = "Major/non-major/censored outcome definition from EXP-005A is not numeric and exact enough for confirmatory labeling."
    pseudo_labels.to_csv(OUT / "pseudo_holdout_labels.csv", index=False)

    months = max((RESEARCH_END - PSEUDO_START).days / 30.4375, 1)
    generator_metrics = pd.DataFrame(
        [
            {
                "verdict": "EVENT_DEFINITION_BLOCKED",
                "development_candidates": len(dev_candidates),
                "pseudo_holdout_candidates": len(pseudo_candidates),
                "pseudo_candidate_rate_per_month": len(pseudo_candidates) / months,
                "pseudo_long": int((pseudo_candidates["direction"] == "LONG").sum()) if not pseudo_candidates.empty else 0,
                "pseudo_short": int((pseudo_candidates["direction"] == "SHORT").sum()) if not pseudo_candidates.empty else 0,
                "development_known_matched": int((dev_match["match_status"] == "MATCHED").sum()),
                "development_known_total": len(dev_match),
                "pseudo_known_matched": int((pseudo_match["match_status"] == "MATCHED").sum()),
                "pseudo_known_total": len(pseudo_match),
                "pseudo_retrospective_only_share": float((pseudo_match["match_status"] == "RETROSPECTIVE_ONLY").mean()) if len(pseudo_match) else 1.0,
                "outcome_label_status": "BLOCKED",
            }
        ]
    )
    generator_metrics.to_csv(OUT / "generator_metrics.csv", index=False)

    blocked = {"status": "BLOCKED", "reason": "Outcome definition is not formalized; no pseudo-holdout ROC/PR metrics calculated."}
    for name in ["model_metrics.csv", "leave_one_major_out.csv"]:
        pd.DataFrame([blocked]).to_csv(OUT / name, index=False)

    for name in ["candidate_timeline.png", "probability_distribution.png"]:
        png_write(OUT / name, 760, 420)

    pine = """//@version=6
indicator("EXP-005H Causal Event Review", overlay=true, max_lines_count=200, max_labels_count=200)
ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
plot(ema27, "EMA27", color=color.new(color.teal, 0))
plot(ema200, "EMA200", color=color.new(color.orange, 0))
// Candidate list is fixed in artifacts/pseudo_holdout_candidates.csv.
// Outcome labels are blocked because EXP-005A major definition is not formalized.
"""
    (OUT / "CAUSAL_EVENT_REVIEW.pine").write_text(pine, encoding="utf-8")
    write_pdf(OUT / "CAUSAL_EVENT_OVERVIEW.pdf")
    print("EXP-005H complete with EVENT_DEFINITION_BLOCKED")
    print(generator_metrics.to_string(index=False))


if __name__ == "__main__":
    main()
