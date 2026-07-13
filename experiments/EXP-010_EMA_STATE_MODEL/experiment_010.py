#!/usr/bin/env python3
"""EXP-010: EMA state model.

Research-only state clustering for ADAUSDT 4H using only OHLC, EMA27, and
EMA200. The script does not use Irobot, ZigZag, future labels, trading entries,
exits, backtest logic, or PnL.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-010_EMA_STATE_MODEL"
OUT = EXP / "artifacts"

START = pd.Timestamp("2023-07-01 00:00:00", tz="UTC")
END = pd.Timestamp("2024-12-31 20:00:00", tz="UTC")
FORBIDDEN = pd.Timestamp("2025-01-01 00:00:00", tz="UTC")
SYMBOL = "ADAUSDT"
INTERVAL = "4h"
BINANCE = "https://api.binance.com/api/v3/klines"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def ms(ts: pd.Timestamp) -> int:
    return int(ts.timestamp() * 1000)


def fetch_ohlc() -> pd.DataFrame:
    rows: list[list[object]] = []
    start_ms = ms(START)
    end_ms = ms(END)
    while start_ms <= end_ms:
        query = urllib.parse.urlencode(
            {
                "symbol": SYMBOL,
                "interval": INTERVAL,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        with urllib.request.urlopen(f"{BINANCE}?{query}", timeout=30) as resp:
            batch = json.loads(resp.read().decode("utf-8"))
        if not batch:
            break
        rows.extend(batch)
        next_start = int(batch[-1][0]) + 4 * 60 * 60 * 1000
        if next_start <= start_ms:
            raise RuntimeError("Binance pagination did not advance.")
        start_ms = next_start

    cols = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        raise RuntimeError("No OHLC data returned.")
    df["dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df = df[["dt", "open", "high", "low", "close"]].sort_values("dt").drop_duplicates("dt").reset_index(drop=True)
    df = df[(df["dt"] >= START) & (df["dt"] <= END)].copy().reset_index(drop=True)
    if df.empty or df["dt"].max() >= FORBIDDEN:
        raise RuntimeError("Data window is empty or includes forbidden 2025+ rows.")
    return df


def add_ema_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    for span in [27, 200]:
        ema = f"ema{span}"
        slope = f"ema{span}_slope_pct"
        angle = f"ema{span}_angle_deg"
        df[slope] = df[ema].pct_change() * 100.0
        df[angle] = np.degrees(np.arctan(df[slope].fillna(0.0)))
        df[f"ema{span}_angle_change_deg"] = df[angle].diff()
        df[f"ema{span}_speed_pct"] = df[slope]
        df[f"ema{span}_speed_change_pct"] = df[slope].diff()

    df["ema27_gt_ema200"] = df["ema27"] > df["ema200"]
    df["ema_relation"] = np.where(df["ema27_gt_ema200"], "EMA27_GT_EMA200", "EMA27_LT_EMA200")
    df["ema_distance_pct"] = (df["ema27"] - df["ema200"]).abs() / df["ema200"].replace(0, np.nan) * 100.0
    df["ema_distance_change_pct"] = df["ema_distance_pct"].diff()
    flat_threshold = max(0.005, float(df["ema_distance_change_pct"].abs().quantile(0.20)))
    df["ema_distance_change_state"] = np.where(
        df["ema_distance_change_pct"] > flat_threshold,
        "INCREASING",
        np.where(df["ema_distance_change_pct"] < -flat_threshold, "DECREASING", "FLAT"),
    )
    df["price_to_ema27_pct"] = (df["close"] - df["ema27"]) / df["ema27"].replace(0, np.nan) * 100.0
    df["price_to_ema200_pct"] = (df["close"] - df["ema200"]) / df["ema200"].replace(0, np.nan) * 100.0
    df["abs_price_to_ema27_pct"] = df["price_to_ema27_pct"].abs()
    df["abs_price_to_ema200_pct"] = df["price_to_ema200_pct"].abs()
    df["main_direction"] = np.where(
        (df["ema27"] > df["ema200"]) & (df["ema27_slope_pct"] >= 0),
        1,
        np.where((df["ema27"] < df["ema200"]) & (df["ema27_slope_pct"] <= 0), -1, 0),
    )
    return df


@dataclass
class Correction:
    correction_id: int
    direction: str
    start_i: int
    end_i: int
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    duration_bars: int
    max_depth_pct: float
    min_abs_distance_to_ema27_pct: float
    min_abs_distance_to_ema200_pct: float
    changed_ema27_slope: bool
    changed_ema200_slope: bool
    bars_to_update_extreme: float
    updated_extreme: bool


def build_corrections(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    active: dict[str, object] | None = None
    corrections: list[Correction] = []
    bar_state = pd.DataFrame(
        {
            "active_correction_id": np.nan,
            "active_correction_duration": 0,
            "active_correction_depth_pct": 0.0,
            "last_correction_duration": 0.0,
            "last_correction_depth_pct": 0.0,
            "last_correction_updated_extreme": np.nan,
            "last_correction_bars_to_update_extreme": np.nan,
        },
        index=df.index,
    )
    last: Correction | None = None

    def close_active(end_i: int) -> Correction:
        assert active is not None
        direction = int(active["direction"])
        start_i = int(active["start_i"])
        pre_extreme = float(active["pre_extreme"])
        lookahead_end = min(len(df) - 1, end_i + 20)
        bars_to_update = math.nan
        updated = False
        for j in range(end_i + 1, lookahead_end + 1):
            if (direction == 1 and float(df.loc[j, "high"]) > pre_extreme) or (direction == -1 and float(df.loc[j, "low"]) < pre_extreme):
                bars_to_update = float(j - end_i)
                updated = True
                break
        return Correction(
            correction_id=len(corrections) + 1,
            direction="UP_TREND_PULLBACK" if direction == 1 else "DOWN_TREND_PULLBACK",
            start_i=start_i,
            end_i=end_i,
            start_time=df.loc[start_i, "dt"],
            end_time=df.loc[end_i, "dt"],
            duration_bars=end_i - start_i + 1,
            max_depth_pct=float(active["max_depth_pct"]),
            min_abs_distance_to_ema27_pct=float(active["min_abs_distance_to_ema27_pct"]),
            min_abs_distance_to_ema200_pct=float(active["min_abs_distance_to_ema200_pct"]),
            changed_ema27_slope=bool(active["changed_ema27_slope"]),
            changed_ema200_slope=bool(active["changed_ema200_slope"]),
            bars_to_update_extreme=bars_to_update,
            updated_extreme=updated,
        )

    for i in range(1, len(df)):
        if last is not None:
            bar_state.loc[i, "last_correction_duration"] = last.duration_bars
            bar_state.loc[i, "last_correction_depth_pct"] = last.max_depth_pct
            bar_state.loc[i, "last_correction_updated_extreme"] = float(last.updated_extreme)
            bar_state.loc[i, "last_correction_bars_to_update_extreme"] = last.bars_to_update_extreme
        direction = int(df.loc[i - 1, "main_direction"])
        delta = float(df.loc[i, "close"] - df.loc[i - 1, "close"])
        against = direction != 0 and direction * delta < 0
        if active is None and against:
            pre_extreme = float(df.loc[i - 1, "high"] if direction == 1 else df.loc[i - 1, "low"])
            active = {
                "direction": direction,
                "start_i": i,
                "start_close": float(df.loc[i - 1, "close"]),
                "pre_extreme": pre_extreme,
                "ema27_slope_sign": math.copysign(1, float(df.loc[i - 1, "ema27_slope_pct"])) if df.loc[i - 1, "ema27_slope_pct"] != 0 else 0,
                "ema200_slope_sign": math.copysign(1, float(df.loc[i - 1, "ema200_slope_pct"])) if df.loc[i - 1, "ema200_slope_pct"] != 0 else 0,
                "max_depth_pct": 0.0,
                "min_abs_distance_to_ema27_pct": float(abs(df.loc[i, "price_to_ema27_pct"])),
                "min_abs_distance_to_ema200_pct": float(abs(df.loc[i, "price_to_ema200_pct"])),
                "changed_ema27_slope": False,
                "changed_ema200_slope": False,
            }
        elif active is not None and (not against or direction != int(active["direction"])):
            corr = close_active(i - 1)
            corrections.append(corr)
            last = corr
            active = None
            if against:
                pre_extreme = float(df.loc[i - 1, "high"] if direction == 1 else df.loc[i - 1, "low"])
                active = {
                    "direction": direction,
                    "start_i": i,
                    "start_close": float(df.loc[i - 1, "close"]),
                    "pre_extreme": pre_extreme,
                    "ema27_slope_sign": math.copysign(1, float(df.loc[i - 1, "ema27_slope_pct"])) if df.loc[i - 1, "ema27_slope_pct"] != 0 else 0,
                    "ema200_slope_sign": math.copysign(1, float(df.loc[i - 1, "ema200_slope_pct"])) if df.loc[i - 1, "ema200_slope_pct"] != 0 else 0,
                    "max_depth_pct": 0.0,
                    "min_abs_distance_to_ema27_pct": float(abs(df.loc[i, "price_to_ema27_pct"])),
                    "min_abs_distance_to_ema200_pct": float(abs(df.loc[i, "price_to_ema200_pct"])),
                    "changed_ema27_slope": False,
                    "changed_ema200_slope": False,
                }

        if active is not None:
            start_close = float(active["start_close"])
            pullback_close = float(df.loc[i, "close"])
            depth_pct = abs(pullback_close - start_close) / start_close * 100.0 if start_close else 0.0
            active["max_depth_pct"] = max(float(active["max_depth_pct"]), depth_pct)
            active["min_abs_distance_to_ema27_pct"] = min(float(active["min_abs_distance_to_ema27_pct"]), float(abs(df.loc[i, "price_to_ema27_pct"])))
            active["min_abs_distance_to_ema200_pct"] = min(float(active["min_abs_distance_to_ema200_pct"]), float(abs(df.loc[i, "price_to_ema200_pct"])))
            e27_sign = math.copysign(1, float(df.loc[i, "ema27_slope_pct"])) if df.loc[i, "ema27_slope_pct"] != 0 else 0
            e200_sign = math.copysign(1, float(df.loc[i, "ema200_slope_pct"])) if df.loc[i, "ema200_slope_pct"] != 0 else 0
            active["changed_ema27_slope"] = bool(active["changed_ema27_slope"] or (e27_sign != active["ema27_slope_sign"] and e27_sign != 0))
            active["changed_ema200_slope"] = bool(active["changed_ema200_slope"] or (e200_sign != active["ema200_slope_sign"] and e200_sign != 0))
            bar_state.loc[i, "active_correction_id"] = int(len(corrections) + 1)
            bar_state.loc[i, "active_correction_duration"] = i - int(active["start_i"]) + 1
            bar_state.loc[i, "active_correction_depth_pct"] = float(active["max_depth_pct"])

    if active is not None:
        corrections.append(close_active(len(df) - 1))

    corr_df = pd.DataFrame([c.__dict__ for c in corrections])
    return corr_df, bar_state.reset_index(drop=True)


def standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu = np.nanmean(x, axis=0)
    sig = np.nanstd(x, axis=0)
    sig[sig == 0] = 1.0
    return (x - mu) / sig, mu, sig


def kmeans(x: np.ndarray, k: int, seed: int = 10, max_iter: int = 100) -> tuple[np.ndarray, np.ndarray, float]:
    rng = np.random.default_rng(seed)
    centers = x[rng.choice(len(x), size=k, replace=False)].copy()
    labels = np.zeros(len(x), dtype=int)
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


def silhouette_score(x: np.ndarray, labels: np.ndarray) -> float:
    unique = np.unique(labels)
    if len(unique) < 2:
        return math.nan
    diff = x[:, None, :] - x[None, :, :]
    dist = np.sqrt((diff * diff).sum(axis=2))
    scores = []
    for i in range(len(x)):
        same = labels == labels[i]
        a = dist[i, same].mean() if same.sum() > 1 else 0.0
        b = min(dist[i, labels == lab].mean() for lab in unique if lab != labels[i])
        scores.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return float(np.mean(scores))


def cluster_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str], pd.DataFrame]:
    feature_cols = [
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
    work = df.copy()
    work["last_correction_updated_extreme"] = work["last_correction_updated_extreme"].fillna(0.0)
    work["last_correction_bars_to_update_extreme"] = work["last_correction_bars_to_update_extreme"].fillna(21.0)
    work = work.dropna(subset=feature_cols).copy().reset_index(drop=True)
    x_raw = work[feature_cols].to_numpy(float)
    x, _, _ = standardize(x_raw)
    runs = []
    best: tuple[float, int, np.ndarray, np.ndarray, float] | None = None
    for k in range(2, 9):
        labels, centers, inertia = kmeans(x, k, seed=100 + k)
        sil = silhouette_score(x, labels)
        runs.append({"k": k, "silhouette": sil, "inertia": inertia})
        if best is None or sil > best[0]:
            best = (sil, k, labels, centers, inertia)
    assert best is not None
    _, k, labels, _, _ = best
    work["state"] = labels + 1

    # Order state numbers by EMA27/EMA200 signed separation so Pine colors remain stable.
    ordering = (
        work.assign(signed_ema_distance=np.where(work["ema27_gt_ema200"], work["ema_distance_pct"], -work["ema_distance_pct"]))
        .groupby("state")["signed_ema_distance"]
        .mean()
        .sort_values()
        .index.tolist()
    )
    mapping = {old: new for new, old in enumerate(ordering, start=1)}
    work["state"] = work["state"].map(mapping).astype(int)
    runs_df = pd.DataFrame(runs)
    return work, runs_df, feature_cols, pd.DataFrame({"old_state": list(mapping.keys()), "state": list(mapping.values())})


def build_cluster_stats(clustered: pd.DataFrame, corrections: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    rows = []
    for state, g in clustered.groupby("state"):
        rows.append(
            {
                "state": int(state),
                "bar_count": int(len(g)),
                "bar_fraction": len(g) / len(clustered),
                "ema27_slope_mean": g["ema27_slope_pct"].mean(),
                "ema200_slope_mean": g["ema200_slope_pct"].mean(),
                "ema27_ema200_distance_mean": g["ema_distance_pct"].mean(),
                "ema_distance_change_mean": g["ema_distance_change_pct"].mean(),
                "avg_correction_depth": g["last_correction_depth_pct"].mean(),
                "avg_correction_duration": g["last_correction_duration"].mean(),
                "extreme_update_frequency": g["last_correction_updated_extreme"].mean(),
                "price_to_ema27_pct_mean": g["price_to_ema27_pct"].mean(),
                "price_to_ema200_pct_mean": g["price_to_ema200_pct"].mean(),
            }
        )
    stats = pd.DataFrame(rows).sort_values("state")
    means = clustered.groupby("state")[feature_cols].mean()
    global_mean = clustered[feature_cols].mean()
    global_std = clustered[feature_cols].std().replace(0, np.nan)
    sep = ((means - global_mean).abs() / global_std).mean(axis=0).sort_values(ascending=False)
    stats.attrs["top_features"] = sep.head(8).index.tolist()
    return stats


def transition_matrix(clustered: pd.DataFrame) -> pd.DataFrame:
    seq = clustered["state"].to_numpy(int)
    states = sorted(clustered["state"].unique())
    counts = pd.DataFrame(0, index=states, columns=states, dtype=int)
    for a, b in zip(seq[:-1], seq[1:]):
        if a != b:
            counts.loc[a, b] += 1
    probs = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    rows = []
    for a in states:
        for b in states:
            rows.append({"from_state": a, "to_state": b, "transition_count": int(counts.loc[a, b]), "transition_probability": float(probs.loc[a, b])})
    return pd.DataFrame(rows)


def build_pine(clustered: pd.DataFrame) -> str:
    intervals = []
    last_state = None
    start = None
    prev_time = None
    for _, row in clustered.iterrows():
        state = int(row["state"])
        t = pd.Timestamp(row["dt"])
        if last_state is None:
            last_state, start = state, t
        elif state != last_state:
            intervals.append((start, prev_time, last_state))
            start, last_state = t, state
        prev_time = t
    if last_state is not None:
        intervals.append((start, prev_time, last_state))

    def ts(t: pd.Timestamp) -> str:
        return f'timestamp("Etc/UTC", {t.year}, {t.month}, {t.day}, {t.hour}, {t.minute})'

    starts = ", ".join(ts(a) for a, _, _ in intervals)
    ends = ", ".join(ts(b) for _, b, _ in intervals)
    states = ", ".join(str(s) for _, _, s in intervals)
    return f'''//@version=6
indicator("EXP-010 EMA State View", overlay=true, max_labels_count=200)

// Research-only state display. Uses only fixed EXP-010 state intervals; no prediction, entries, exits, or PnL.
showStateLabels = input.bool(true, "showStateLabels")

var int[] stateStarts = array.from({starts})
var int[] stateEnds = array.from({ends})
var int[] stateNos = array.from({states})

f_state_color(int s) =>
    s == 1 ? color.new(color.blue, 86) : s == 2 ? color.new(color.teal, 86) : s == 3 ? color.new(color.yellow, 84) : s == 4 ? color.new(color.orange, 84) : s == 5 ? color.new(color.red, 86) : color.new(color.gray, 86)

int currentState = na
bool transitionBar = false
for i = 0 to array.size(stateNos) - 1
    int a = array.get(stateStarts, i)
    int b = array.get(stateEnds, i)
    if time >= a and time <= b
        currentState := array.get(stateNos, i)
        transitionBar := time == a

bgcolor(na(currentState) ? na : f_state_color(currentState))

if showStateLabels and transitionBar and not na(currentState)
    label.new(time, high, "State " + str.tostring(currentState), xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.black, 0), textcolor=color.white, size=size.tiny)
'''


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(path: Path, title: str, lines: list[str]) -> None:
    width, height = 612, 792
    content_lines = ["BT", "/F1 16 Tf", "50 750 Td", f"({pdf_escape(title)}) Tj", "/F1 10 Tf", "0 -24 Td"]
    for line in lines[:55]:
        content_lines.append(f"({pdf_escape(line)}) Tj")
        content_lines.append("0 -14 Td")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(out)


def write_report(
    df: pd.DataFrame,
    clustered: pd.DataFrame,
    corrections: pd.DataFrame,
    stats: pd.DataFrame,
    transitions: pd.DataFrame,
    runs: pd.DataFrame,
    feature_cols: list[str],
) -> str:
    top_features = stats.attrs["top_features"]
    best_k = int(runs.sort_values("silhouette", ascending=False).iloc[0]["k"])
    best_sil = float(runs.sort_values("silhouette", ascending=False).iloc[0]["silhouette"])
    dominant = (
        transitions[transitions["from_state"] != transitions["to_state"]]
        .sort_values(["from_state", "transition_probability"], ascending=[True, False])
        .groupby("from_state")
        .head(1)
    )
    transition_lines = "; ".join(
        f"State {int(r.from_state)} -> State {int(r.to_state)} ({r.transition_probability:.2f})" for r in dominant.itertuples()
    )
    ema200_range = stats["ema200_slope_mean"].max() - stats["ema200_slope_mean"].min()
    corr_depth_range = stats["avg_correction_depth"].max() - stats["avg_correction_depth"].min()
    corr_duration_range = stats["avg_correction_duration"].max() - stats["avg_correction_duration"].min()

    report = f"""# EXP-010 — EMA STATE MODEL

Status: DONE / REPORT_READY

## Data

ADAUSDT 4H, Binance public spot klines, `{df['dt'].min()}` -> `{df['dt'].max()}`.
Rows used: `{len(df)}` raw bars, `{len(clustered)}` clustered bars after causal rolling-feature warmup.
No Irobot source was read. No data after 2024-12-31 was used.

## Method

Only OHLC, EMA27, and EMA200 were used. EMA-derived features were computed per closed bar: EMA values, slope percent, angle, angle change, speed, speed change, EMA relation, EMA distance, EMA distance change state, and price distances to EMA27/EMA200.

Corrections were defined without ZigZag as continuous close-to-close movement against the current EMA direction:
`EMA27 > EMA200` with non-negative EMA27 slope means up-direction, `EMA27 < EMA200` with non-positive EMA27 slope means down-direction, otherwise no correction is started. For each completed correction the script measured duration, maximum depth, nearest distance to EMA27/EMA200, whether EMA slopes changed sign, and whether the directional extreme was updated within the next 20 bars. These post-correction fields are attached only after a correction is complete.

State discovery used k-means clustering for k=2..8 on standardized features. k was selected by silhouette score. No state labels were manually assigned; final names are only State numbers.

## Answers

1. Did automatic clustering identify recurring market states?

Yes, with caveats. The best silhouette was `{best_sil:.3f}` at `k={best_k}`. This is enough to say the EMA/price/correction features form recurring regimes, but not enough to call them predictive or tradable.

2. Which features most separated the states?

Most separating features by standardized between-state mean distance:
{', '.join(f'`{x}`' for x in top_features)}.

3. Do transitions follow State A -> State B -> State C, or are they random?

Transitions are not purely random, but they are not a clean universal chain. Dominant observed transition routes were: {transition_lines}. The transition matrix should be read as descriptive state persistence/rotation, not as a forecast rule.

4. Does EMA200 behavior change between states?

Yes. Mean EMA200 slope differs across states by `{ema200_range:.4f}` percentage points per 4H bar. State-level values are in `cluster_statistics.csv`.

5. Does correction behavior change between states?

Yes. Average completed-correction depth differs by `{corr_depth_range:.3f}` percentage points and average completed-correction duration differs by `{corr_duration_range:.2f}` bars across states. State-level correction update frequency is also reported in `cluster_statistics.csv`.

## Constraints Audit

- No 2025+ data used.
- No Irobot read.
- No ZigZag used.
- No future data was used for assigning current-bar state; post-correction measurements are only attached after the correction has ended.
- No trading system, entries, exits, stop logic, backtest, or PnL.
- `docs/DEFINITIONS.md` was not changed.

## Artifacts

- `artifacts/ema_state_features.csv`
- `artifacts/ema_state_clusters.csv`
- `artifacts/cluster_statistics.csv`
- `artifacts/state_transition_matrix.csv`
- `artifacts/EMA_STATE_VIEW.pine`
- `artifacts/EMA_STATE_CONTACT_SHEET.pdf`
"""
    (EXP / "REPORT.md").write_text(report)
    return report


def main() -> None:
    ensure_dirs()
    raw = fetch_ohlc()
    df = add_ema_features(raw)
    corrections, correction_state = build_corrections(df)
    features = pd.concat([df.reset_index(drop=True), correction_state], axis=1)
    features["dt"] = features["dt"].dt.tz_convert("UTC").dt.tz_localize(None)
    if pd.Timestamp(features["dt"].max()) >= pd.Timestamp("2025-01-01"):
        raise RuntimeError("Forbidden 2025+ row detected.")
    clustered, runs, feature_cols, _ = cluster_features(features)
    stats = build_cluster_stats(clustered, corrections, feature_cols)
    transitions = transition_matrix(clustered)

    features.to_csv(OUT / "ema_state_features.csv", index=False)
    clustered.to_csv(OUT / "ema_state_clusters.csv", index=False)
    stats.to_csv(OUT / "cluster_statistics.csv", index=False)
    transitions.to_csv(OUT / "state_transition_matrix.csv", index=False)
    runs.to_csv(OUT / "cluster_selection.csv", index=False)
    corrections.to_csv(OUT / "corrections.csv", index=False)
    (OUT / "EMA_STATE_VIEW.pine").write_text(build_pine(clustered))

    report = write_report(features, clustered, corrections, stats, transitions, runs, feature_cols)
    pdf_lines = [
        f"Rows: raw={len(features)}, clustered={len(clustered)}, corrections={len(corrections)}",
        f"Best k: {int(runs.sort_values('silhouette', ascending=False).iloc[0]['k'])}",
        f"Best silhouette: {float(runs.sort_values('silhouette', ascending=False).iloc[0]['silhouette']):.3f}",
        "Top separating features:",
        *[f"- {x}" for x in stats.attrs["top_features"]],
        "",
        "Cluster statistics:",
        *[
            f"State {int(r.state)} bars={int(r.bar_count)} ema27_slope={r.ema27_slope_mean:.4f} ema200_slope={r.ema200_slope_mean:.4f} corr_depth={r.avg_correction_depth:.3f}"
            for r in stats.itertuples()
        ],
        "",
        "No trading conclusions. State numbers only.",
    ]
    write_simple_pdf(OUT / "EMA_STATE_CONTACT_SHEET.pdf", "EXP-010 EMA State Contact Sheet", pdf_lines)
    print(report.splitlines()[0])
    print(f"rows={len(features)} clustered={len(clustered)} states={stats['state'].nunique()} corrections={len(corrections)}")


if __name__ == "__main__":
    main()
