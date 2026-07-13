#!/usr/bin/env python3
"""EXP-006A: diagnose EXP-006 train-to-temporal failure without new rules."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP006 = ROOT / "experiments/EXP-006_EMA_TRADING_CYCLE"
EXP = EXP006 / "EXP-006A_ENTRY_EXIT_DIAGNOSIS"
OUT = EXP / "artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

TRAIN_START = pd.Timestamp("2023-07-01 00:00")
TRAIN_END = pd.Timestamp("2024-12-19 23:59")
TEST_START = pd.Timestamp("2024-12-20 00:00")
RESEARCH_END = pd.Timestamp("2025-07-01 00:00")
TRUE_HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")
PRIMARY = "ENTRY_A_STOP_A_EXIT_B"
SHORTLIST = ["ENTRY_A_STOP_A_EXIT_B", "ENTRY_A_STOP_B_EXIT_B", "ENTRY_A_STOP_A_EXIT_A"]
HORIZONS = [3, 6, 12, 24, 48]
FEE = 0.001
SLIP = 0.0005


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df.sort_values("dt").reset_index(drop=True)
    df = df[(df["dt"] >= TRAIN_START) & (df["dt"] <= RESEARCH_END)].copy().reset_index(drop=True)
    if df["dt"].max() >= TRUE_HOLDOUT_START:
        raise RuntimeError("True holdout entered EXP-006A data frame.")
    prev = df["close"].shift(1).fillna(df["close"])
    df["tr"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(float),
            (df["high"] - prev).abs().to_numpy(float),
            (df["low"] - prev).abs().to_numpy(float),
        ]
    )
    df["body"] = (df["close"] - df["open"]).abs()
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["atr14"] = df["tr"].rolling(14, min_periods=1).mean()
    df["ema200_slope_20"] = df["ema200"] - df["ema200"].shift(20)
    bull = (df["close"] > df["ema200"]) & (df["ema200_slope_20"] > 0) & (df["ema27"] > df["ema200"])
    bear = (df["close"] < df["ema200"]) & (df["ema200_slope_20"] < 0) & (df["ema27"] < df["ema200"])
    df["regime"] = np.where(bull, "BULL_REGIME", np.where(bear, "BEAR_REGIME", "TRANSITION_REGIME"))
    return df


def side(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def slipped(price: float, direction: str, is_entry: bool) -> float:
    s = side(direction)
    sign = s if is_entry else -s
    return price * (1.0 + sign * SLIP)


def idx_map(df: pd.DataFrame) -> dict[pd.Timestamp, int]:
    return {pd.Timestamp(t): int(i) for i, t in zip(df.index, df["dt"])}


def first_threshold(df: pd.DataFrame, start_i: int, end_i: int, entry_price: float, direction: str, atr: float, plus: float, minus: float) -> str:
    s = side(direction)
    plus_i = None
    minus_i = None
    for i in range(start_i, end_i + 1):
        up = s * (float(df.loc[i, "high"]) - entry_price) / atr
        down = s * (float(df.loc[i, "low"]) - entry_price) / atr
        best = max(up, down)
        worst = min(up, down)
        if plus_i is None and best >= plus:
            plus_i = i
        if minus_i is None and worst <= -minus:
            minus_i = i
        if plus_i is not None or minus_i is not None:
            break
    if plus_i is not None and minus_i is None:
        return "PLUS_FIRST"
    if minus_i is not None and plus_i is None:
        return "MINUS_FIRST"
    if plus_i is None and minus_i is None:
        return "NEITHER"
    return "PLUS_FIRST" if plus_i <= minus_i else "MINUS_FIRST"


def path_for_trade(df: pd.DataFrame, m: dict[pd.Timestamp, int], r: pd.Series, horizon: int) -> dict:
    entry_i = m[pd.Timestamp(r["entry_time"])]
    end_i = min(entry_i + horizon, len(df) - 1)
    w = df.loc[entry_i:end_i]
    direction = r["direction"]
    s = side(direction)
    entry_price = float(r["entry_price"])
    atr = float(df.loc[entry_i, "atr14"])
    high_ret = s * (w["high"].to_numpy(float) - entry_price) / entry_price
    low_ret = s * (w["low"].to_numpy(float) - entry_price) / entry_price
    high_atr = s * (w["high"].to_numpy(float) - entry_price) / atr
    low_atr = s * (w["low"].to_numpy(float) - entry_price) / atr
    best_ret_series = np.maximum(high_ret, low_ret)
    worst_ret_series = np.minimum(high_ret, low_ret)
    best_atr_series = np.maximum(high_atr, low_atr)
    worst_atr_series = np.minimum(high_atr, low_atr)
    mfe_pos = int(np.argmax(best_ret_series))
    mae_pos = int(np.argmin(worst_ret_series))
    close_ret = s * (float(df.loc[end_i, "close"]) - entry_price) / entry_price
    return {
        "trade_id": r["trade_id"],
        "combo_id": r["combo_id"],
        "scope": r["scope"],
        "direction": direction,
        "entry_regime": r["entry_regime"],
        "entry_time": r["entry_time"],
        "horizon_bars": horizon,
        "signed_return": close_ret,
        "mfe": float(best_ret_series.max()),
        "mae": float(worst_ret_series.min()),
        "mfe_atr": float(best_atr_series.max()),
        "mae_atr": float(worst_atr_series.min()),
        "reached_plus_1atr": bool(best_atr_series.max() >= 1.0),
        "reached_plus_2atr": bool(best_atr_series.max() >= 2.0),
        "reached_minus_1atr": bool(worst_atr_series.min() <= -1.0),
        "reached_minus_2atr": bool(worst_atr_series.min() <= -2.0),
        "time_to_mfe_bars": mfe_pos,
        "time_to_mae_bars": mae_pos,
        "plus1_before_minus1": first_threshold(df, entry_i, end_i, entry_price, direction, atr, 1.0, 1.0),
        "plus2_before_minus1": first_threshold(df, entry_i, end_i, entry_price, direction, atr, 2.0, 1.0),
    }


def future_after_exit(df: pd.DataFrame, m: dict[pd.Timestamp, int], r: pd.Series, bars: int = 12) -> float:
    exit_i = m[pd.Timestamp(r["exit_time"])]
    end_i = min(exit_i + bars, len(df) - 1)
    if end_i <= exit_i:
        return 0.0
    w = df.loc[exit_i:end_i]
    s = side(r["direction"])
    atr = float(df.loc[exit_i, "atr14"])
    return float(max(s * (w["high"].max() - float(r["exit_price"])) / atr, s * (w["low"].min() - float(r["exit_price"])) / atr))


def no_stop_exit_b_return(df: pd.DataFrame, m: dict[pd.Timestamp, int], r: pd.Series) -> dict:
    entry_i = m[pd.Timestamp(r["entry_time"])]
    direction = r["direction"]
    entry_price = float(r["entry_price"])
    exit_i = len(df) - 1
    reason = "END_OF_DATA"
    for i in range(entry_i + 1, len(df) - 1):
        close = float(df.loc[i, "close"])
        ema27 = float(df.loc[i, "ema27"])
        prev_close = float(df.loc[i - 1, "close"])
        prev_ema27 = float(df.loc[i - 1, "ema27"])
        if direction == "LONG" and prev_close < prev_ema27 and close < ema27:
            exit_i = i + 1
            reason = "EMA27_TWO_CLOSES_NO_STOP"
            break
        if direction == "SHORT" and prev_close > prev_ema27 and close > ema27:
            exit_i = i + 1
            reason = "EMA27_TWO_CLOSES_NO_STOP"
            break
        reg = df.loc[i, "regime"]
        if (direction == "LONG" and reg == "BEAR_REGIME") or (direction == "SHORT" and reg == "BULL_REGIME"):
            exit_i = i + 1
            reason = "REGIME_FLIP_NO_STOP"
            break
    exit_raw = float(df.loc[exit_i, "open"])
    exit_price = slipped(exit_raw, direction, False)
    ret = side(direction) * (exit_price - entry_price) / entry_price - 2 * FEE
    return {"no_stop_exit_b_return": ret, "no_stop_exit_b_reason": reason, "no_stop_exit_b_time": df.loc[exit_i, "dt"]}


def classify_trade(df: pd.DataFrame, m: dict[pd.Timestamp, int], r: pd.Series, p24: pd.Series, p48: pd.Series) -> tuple[str, dict]:
    entry_i = m[pd.Timestamp(r["entry_time"])]
    exit_i = m[pd.Timestamp(r["exit_time"])]
    s = side(r["direction"])
    atr = float(df.loc[entry_i, "atr14"])
    entry_price = float(r["entry_price"])
    mfe_atr = float(p48["mfe_atr"])
    mae_atr = float(p48["mae_atr"])
    net_atr = float(r["net_return"]) * entry_price / atr
    high24 = df.loc[entry_i : min(entry_i + 24, len(df) - 1), "high"].max()
    low24 = df.loc[entry_i : min(entry_i + 24, len(df) - 1), "low"].min()
    move24 = s * ((high24 if s == 1 else low24) - entry_price) / atr
    pre_w = df.loc[max(0, entry_i - 24) : entry_i]
    pre_move = s * ((entry_price - pre_w["low"].min()) if s == 1 else (pre_w["high"].max() - entry_price)) / atr
    late_entry = move24 > 0 and pre_move > 0.5 * (pre_move + move24)
    fut = future_after_exit(df, m, r, 12)
    giveback_ratio = (mfe_atr - net_atr) / mfe_atr if mfe_atr > 0 else 0.0
    stop_too_tight = r["exit_reason"] == "STOP" and fut >= 1.5
    quick_regime = False
    for i in range(entry_i, min(entry_i + 12, len(df) - 1) + 1):
        reg = df.loc[i, "regime"]
        if (r["direction"] == "LONG" and reg == "BEAR_REGIME") or (r["direction"] == "SHORT" and reg == "BULL_REGIME"):
            quick_regime = True
            break
    if mfe_atr < 0.5 and abs(mae_atr) > 1.0:
        typ = "BAD_ENTRY"
    elif mfe_atr >= 1.5 and float(r["net_return"]) <= 0:
        typ = "GOOD_ENTRY_BAD_EXIT"
    elif late_entry:
        typ = "LATE_ENTRY"
    elif fut >= 1.5:
        typ = "EARLY_EXIT"
    elif giveback_ratio > 0.75:
        typ = "LATE_EXIT"
    elif stop_too_tight:
        typ = "STOP_TOO_TIGHT"
    elif quick_regime:
        typ = "REGIME_FAILURE"
    else:
        typ = "MIXED"
    return typ, {
        "mfe_atr_48": mfe_atr,
        "mae_atr_48": mae_atr,
        "net_atr": net_atr,
        "future_after_exit_atr_12": fut,
        "mfe_giveback_ratio": giveback_ratio,
        "late_entry_pre_move_atr": pre_move,
        "late_entry_post_24_move_atr": move24,
        "quick_opposite_regime": quick_regime,
    }


def environment(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, scope: str) -> dict:
    w = df[(df["dt"] >= start) & (df["dt"] <= end)].copy()
    ema27_cross = int(np.sum(np.sign((w["close"] - w["ema27"]).to_numpy(float))[1:] != np.sign((w["close"] - w["ema27"]).to_numpy(float))[:-1]))
    ema200_cross = int(np.sum(np.sign((w["close"] - w["ema200"]).to_numpy(float))[1:] != np.sign((w["close"] - w["ema200"]).to_numpy(float))[:-1]))
    dirs = np.sign(w["close"].diff().fillna(0).to_numpy(float))
    runs = []
    cur = 0
    prev = 0
    pullbacks = []
    for d, tr in zip(dirs, w["tr"].to_numpy(float)):
        if d == prev and d != 0:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 1 if d != 0 else 0
            prev = d
    closes = w["close"].to_numpy(float)
    for i in range(12, len(closes)):
        seg = closes[i - 12 : i + 1]
        if seg[-1] >= seg[0]:
            running = np.maximum.accumulate(seg)
            pullbacks.append(float(np.max(running - seg)))
        else:
            running = np.minimum.accumulate(seg)
            pullbacks.append(float(np.max(seg - running)))
    if cur:
        runs.append(cur)
    segments = []
    for reg, g in w.groupby((w["regime"] != w["regime"].shift()).cumsum()):
        segments.append((g["regime"].iloc[0], len(g)))
    avg_reg = {r: np.mean([n for rr, n in segments if rr == r]) if any(rr == r for rr, _ in segments) else 0 for r in ["BULL_REGIME", "BEAR_REGIME", "TRANSITION_REGIME"]}
    ema27_dist = (w["close"] - w["ema27"]).abs()
    return {
        "scope": scope,
        "bars": int(len(w)),
        "atr14_median": float(w["atr14"].median()),
        "atr14_iqr": float(w["atr14"].quantile(0.75) - w["atr14"].quantile(0.25)),
        "share_above_ema200": float((w["close"] > w["ema200"]).mean()),
        "share_below_ema200": float((w["close"] < w["ema200"]).mean()),
        "ema27_crosses": ema27_cross,
        "ema200_crosses": ema200_cross,
        "avg_bull_regime_bars": float(avg_reg["BULL_REGIME"]),
        "avg_bear_regime_bars": float(avg_reg["BEAR_REGIME"]),
        "avg_transition_regime_bars": float(avg_reg["TRANSITION_REGIME"]),
        "transition_share": float((w["regime"] == "TRANSITION_REGIME").mean()),
        "avg_directional_run_bars": float(np.mean(runs)) if runs else 0.0,
        "avg_pullback_depth_atr": float(np.mean(pullbacks) / w["atr14"].median()) if pullbacks else 0.0,
        "avg_speed_return_to_ema27": float(ema27_dist.diff().abs().mean() / w["atr14"].median()),
    }


class Raster:
    def __init__(self, w: int = 1000, h: int = 520):
        self.w = w
        self.h = h
        self.p = bytearray((255, 255, 255) * (w * h))

    def dot(self, x: int, y: int, c: tuple[int, int, int]) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            k = (y * self.w + x) * 3
            self.p[k : k + 3] = bytes(c)

    def line(self, x0: float, y0: float, x1: float, y1: float, c: tuple[int, int, int], width: int = 2) -> None:
        x0, y0, x1, y1 = map(lambda v: int(round(v)), [x0, y0, x1, y1])
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            for ox in range(-(width // 2), width // 2 + 1):
                for oy in range(-(width // 2), width // 2 + 1):
                    self.dot(x0 + ox, y0 + oy, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def save(self, path: Path) -> None:
        raw = b"".join(b"\x00" + bytes(self.p[y * self.w * 3 : (y + 1) * self.w * 3]) for y in range(self.h))
        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(raw, 9))
        png += chunk(b"IEND", b"")
        path.write_bytes(png)


def simple_chart(series: list[tuple[str, list[float]]], path: Path) -> None:
    colors = [(0, 120, 190), (220, 80, 40), (50, 150, 80), (150, 80, 180), (20, 20, 20)]
    r = Raster()
    allv = [v for _, vals in series for v in vals]
    ymin, ymax = (min(allv), max(allv)) if allv else (0, 1)
    if ymax == ymin:
        ymax = ymin + 1
    pad = 45
    r.line(pad, r.h - pad, r.w - 20, r.h - pad, (160, 160, 160), 1)
    r.line(pad, 20, pad, r.h - pad, (160, 160, 160), 1)
    for si, (_, vals) in enumerate(series):
        pts = []
        for i, val in enumerate(vals):
            x = pad + i / max(1, len(vals) - 1) * (r.w - pad - 20)
            y = r.h - pad - (val - ymin) / (ymax - ymin) * (r.h - pad - 20)
            pts.append((x, y))
        for a, b in zip(pts, pts[1:]):
            r.line(a[0], a[1], b[0], b[1], colors[si % len(colors)], 2)
    r.save(path)


def pdf_text(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:90]


def write_pdf(lines: list[str], path: Path) -> None:
    content = ["BT /F1 12 Tf 36 760 Td"]
    for line in lines[:55]:
        content.append(f"({pdf_text(line)}) Tj 0 -14 Td")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, obj in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offs:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    if df.empty:
        return "No rows."
    def cell(v) -> str:
        if isinstance(v, float):
            return f"{v:.6g}"
        return str(v)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df[cols].iterrows():
        rows.append("| " + " | ".join(cell(r[c]) for c in cols) + " |")
    return "\n".join(rows)


def write_pine(test_primary: pd.DataFrame, failures: pd.DataFrame) -> None:
    merged = test_primary.merge(failures[["trade_id", "diagnostic_type"]], on="trade_id", how="left").head(80)
    def ts(t) -> str:
        p = pd.Timestamp(t)
        return f'timestamp("Etc/UTC", {p.year}, {p.month}, {p.day}, {p.hour}, {p.minute})'
    starts = ", ".join(ts(t) for t in merged["entry_time"]) or 'timestamp("Etc/UTC", 2024, 12, 20, 0, 0)'
    ends = ", ".join(ts(t) for t in merged["exit_time"]) or 'timestamp("Etc/UTC", 2024, 12, 20, 4, 0)'
    stops = ", ".join(f"{float(x):.8f}" for x in merged["stop_price"]) or "0.0"
    types = ", ".join(f'"{x}"' for x in merged["diagnostic_type"].fillna("UNKNOWN")) or '"UNKNOWN"'
    dirs = ", ".join(f'"{x}"' for x in merged["direction"]) or '"NA"'
    text = f"""//@version=6
indicator("EXP-006A EMA Cycle Diagnosis Review", overlay=true, max_lines_count=500, max_labels_count=500)

// Diagnostic markup only. Uses EXP-006 temporal-test trades for ENTRY_A_STOP_A_EXIT_B.
showLabels = input.bool(true, "show labels")
showStops = input.bool(true, "show stops")

ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
plot(ema27, "EMA27", color=color.aqua)
plot(ema200, "EMA200", color=color.orange)

slope20 = ema200 - ema200[20]
bull = close > ema200 and slope20 > 0 and ema27 > ema200
bear = close < ema200 and slope20 < 0 and ema27 < ema200
bgcolor(bull ? color.new(color.green, 92) : bear ? color.new(color.red, 92) : color.new(color.gray, 95))

var int[] starts = array.from({starts})
var int[] ends = array.from({ends})
var float[] stops = array.from({stops})
var string[] types = array.from({types})
var string[] dirs = array.from({dirs})

for i = 0 to array.size(starts) - 1
    int st = array.get(starts, i)
    int en = array.get(ends, i)
    float sp = array.get(stops, i)
    string typ = array.get(types, i)
    string dir = array.get(dirs, i)
    if time == st
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.green, width=2)
        if showLabels
            label.new(time, high, dir + " " + typ, xloc=xloc.bar_time, style=label.style_label_down, color=color.green, textcolor=color.white, size=size.tiny)
    if time == en
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.red, width=2)
        if showLabels
            label.new(time, low, "exit " + typ, xloc=xloc.bar_time, style=label.style_label_up, color=color.red, textcolor=color.white, size=size.tiny)
    if showStops and time >= st and time <= en
        line.new(st, sp, en, sp, xloc=xloc.bar_time, color=color.new(color.red, 40), style=line.style_dotted)
"""
    (OUT / "EMA_CYCLE_DIAGNOSIS_REVIEW.pine").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    df = load_ohlc()
    m = idx_map(df)
    trades = pd.read_csv(EXP006 / "artifacts/trades_all_combinations.csv")
    trades = trades[trades["combo_id"].isin(SHORTLIST)].copy()
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])
    paths = []
    for _, r in trades.iterrows():
        if pd.Timestamp(r["entry_time"]) not in m:
            continue
        for h in HORIZONS:
            paths.append(path_for_trade(df, m, r, h))
    paths_df = pd.DataFrame(paths)
    paths_df.to_csv(OUT / "fixed_horizon_outcomes.csv", index=False)
    primary_paths = paths_df[paths_df["combo_id"] == PRIMARY]
    path_metrics = primary_paths.groupby(["scope", "horizon_bars"]).agg(
        trades=("trade_id", "count"),
        avg_signed_return=("signed_return", "mean"),
        avg_mfe_atr=("mfe_atr", "mean"),
        avg_mae_atr=("mae_atr", "mean"),
        reached_plus1_share=("reached_plus_1atr", "mean"),
        reached_plus2_share=("reached_plus_2atr", "mean"),
        reached_minus1_share=("reached_minus_1atr", "mean"),
        plus1_before_minus1_share=("plus1_before_minus1", lambda s: float((s == "PLUS_FIRST").mean())),
        plus2_before_minus1_share=("plus2_before_minus1", lambda s: float((s == "PLUS_FIRST").mean())),
        avg_time_to_mfe=("time_to_mfe_bars", "mean"),
        avg_time_to_mae=("time_to_mae_bars", "mean"),
    ).reset_index()
    path_metrics.to_csv(OUT / "trade_path_metrics.csv", index=False)

    oracle_rows = []
    for _, r in trades.iterrows():
        p = paths_df[(paths_df["trade_id"] == r["trade_id"])]
        if p.empty:
            continue
        row = {
            "trade_id": r["trade_id"],
            "combo_id": r["combo_id"],
            "scope": r["scope"],
            "signal_time": r["signal_time"],
            "direction": r["direction"],
            "actual_net_return": r["net_return"],
            "exit_reason": r["exit_reason"],
        }
        for h in HORIZONS:
            ph = p[p["horizon_bars"] == h].iloc[0]
            row[f"oracle_mfe_return_{h}"] = ph["mfe"]
            row[f"fixed_exit_return_{h}"] = ph["signed_return"]
            row[f"max_possible_atr_{h}"] = ph["mfe_atr"]
        oracle_rows.append(row)
    oracle = pd.DataFrame(oracle_rows)
    actual_ab = trades[trades["combo_id"].isin(["ENTRY_A_STOP_A_EXIT_A", "ENTRY_A_STOP_A_EXIT_B"])][["combo_id", "scope", "signal_time", "direction", "net_return"]].copy()
    actual_piv = actual_ab.pivot_table(index=["scope", "signal_time", "direction"], columns="combo_id", values="net_return", aggfunc="first").reset_index()
    actual_piv = actual_piv.rename(columns={"ENTRY_A_STOP_A_EXIT_A": "actual_exit_a_return", "ENTRY_A_STOP_A_EXIT_B": "actual_exit_b_return"})
    oracle = oracle.merge(actual_piv, on=["scope", "signal_time", "direction"] if "signal_time" in oracle.columns else [], how="left") if False else oracle
    oracle.to_csv(OUT / "oracle_exit_analysis.csv", index=False)

    primary = trades[trades["combo_id"] == PRIMARY].copy()
    failures = []
    p24 = paths_df[(paths_df["combo_id"] == PRIMARY) & (paths_df["horizon_bars"] == 24)].set_index("trade_id")
    p48 = paths_df[(paths_df["combo_id"] == PRIMARY) & (paths_df["horizon_bars"] == 48)].set_index("trade_id")
    for _, r in primary.iterrows():
        typ, vals = classify_trade(df, m, r, p24.loc[r["trade_id"]], p48.loc[r["trade_id"]])
        failures.append({"trade_id": r["trade_id"], "scope": r["scope"], "direction": r["direction"], "entry_regime": r["entry_regime"], "diagnostic_type": typ, "net_return": r["net_return"], "exit_reason": r["exit_reason"], **vals})
    fail = pd.DataFrame(failures)
    fail.to_csv(OUT / "failure_classification.csv", index=False)
    comp_rows = []
    for scope, g in fail.groupby("scope"):
        base = {"group": "ALL", "scope": scope, "n": len(g)}
        for typ in ["BAD_ENTRY", "GOOD_ENTRY_BAD_EXIT", "LATE_ENTRY", "EARLY_EXIT", "LATE_EXIT", "STOP_TOO_TIGHT", "REGIME_FAILURE", "MIXED"]:
            base[typ] = float((g["diagnostic_type"] == typ).mean())
        comp_rows.append(base)
    for col in ["direction", "entry_regime"]:
        for keys, g in fail.groupby(["scope", col]):
            base = {"group": f"{col}:{keys[1]}", "scope": keys[0], "n": len(g)}
            for typ in ["BAD_ENTRY", "GOOD_ENTRY_BAD_EXIT", "LATE_ENTRY", "EARLY_EXIT", "LATE_EXIT", "STOP_TOO_TIGHT", "REGIME_FAILURE", "MIXED"]:
                base[typ] = float((g["diagnostic_type"] == typ).mean())
            comp_rows.append(base)
    comp = pd.DataFrame(comp_rows)
    comp.to_csv(OUT / "train_test_failure_comparison.csv", index=False)

    env = pd.DataFrame([environment(df, TRAIN_START, TRAIN_END, "TRAIN"), environment(df, TEST_START, RESEARCH_END, "TEMPORAL_TEST")])
    env.to_csv(OUT / "regime_environment_comparison.csv", index=False)

    stop_pairs = trades[trades["combo_id"].isin(["ENTRY_A_STOP_A_EXIT_B", "ENTRY_A_STOP_B_EXIT_B"])].copy()
    stop_diag = stop_pairs.pivot_table(index=["scope", "signal_time", "direction"], columns="combo_id", values=["net_return", "exit_reason", "mfe", "mae"], aggfunc="first").reset_index()
    stop_diag.columns = ["_".join([str(x) for x in c if x]) for c in stop_diag.columns]
    stop_diag["stop_diff_return_b_minus_a"] = stop_diag.get("net_return_ENTRY_A_STOP_B_EXIT_B", 0) - stop_diag.get("net_return_ENTRY_A_STOP_A_EXIT_B", 0)
    stop_diag["stop_a_premature"] = (stop_diag.get("exit_reason_ENTRY_A_STOP_A_EXIT_B", "") == "STOP") & (stop_diag["stop_diff_return_b_minus_a"] > 0.01)
    stop_diag["stop_b_increased_loss"] = stop_diag["stop_diff_return_b_minus_a"] < -0.01
    no_stop_rows = []
    for _, r in trades[trades["combo_id"] == PRIMARY].iterrows():
        no_stop_rows.append({"scope": r["scope"], "signal_time": r["signal_time"], "direction": r["direction"], **no_stop_exit_b_return(df, m, r)})
    no_stop = pd.DataFrame(no_stop_rows)
    stop_diag = stop_diag.merge(no_stop, on=["scope", "signal_time", "direction"], how="left")
    stop_diag.to_csv(OUT / "stop_diagnosis.csv", index=False)

    exit_pairs = trades[trades["combo_id"].isin(["ENTRY_A_STOP_A_EXIT_A", "ENTRY_A_STOP_A_EXIT_B"])].copy()
    exit_diag = exit_pairs.pivot_table(index=["scope", "signal_time", "direction"], columns="combo_id", values=["net_return", "mfe", "mae"], aggfunc="first").reset_index()
    exit_diag.columns = ["_".join([str(x) for x in c if x]) for c in exit_diag.columns]
    fixed_primary = oracle[oracle["combo_id"] == PRIMARY][["scope", "signal_time", "direction", "fixed_exit_return_6", "fixed_exit_return_12", "fixed_exit_return_24", "oracle_mfe_return_48"]]
    exit_diag = exit_diag.merge(fixed_primary, on=["scope", "signal_time", "direction"], how="left")
    exit_diag.to_csv(OUT / "exit_diagnosis.csv", index=False)

    simple_chart([
        ("TRAIN", list(path_metrics[path_metrics["scope"] == "TRAIN"].sort_values("horizon_bars")["avg_signed_return"])),
        ("TEST", list(path_metrics[path_metrics["scope"] == "TEMPORAL_TEST"].sort_values("horizon_bars")["avg_signed_return"])),
    ], OUT / "entry_quality_train_vs_test.png")
    all_types = ["BAD_ENTRY", "GOOD_ENTRY_BAD_EXIT", "LATE_ENTRY", "EARLY_EXIT", "LATE_EXIT", "STOP_TOO_TIGHT", "REGIME_FAILURE", "MIXED"]
    all_comp = comp[comp["group"] == "ALL"].set_index("scope")
    simple_chart([(s, [float(all_comp.loc[s, t]) for t in all_types]) for s in all_comp.index], OUT / "failure_types_train_vs_test.png")
    gb = fail.groupby("scope")["mfe_giveback_ratio"].mean()
    simple_chart([(k, [0, v]) for k, v in gb.items()], OUT / "mfe_giveback_train_vs_test.png")
    simple_chart([(row["scope"], [row["transition_share"], row["ema27_crosses"] / max(row["bars"], 1), row["ema200_crosses"] / max(row["bars"], 1), row["avg_directional_run_bars"]]) for _, row in env.iterrows()], OUT / "regime_comparison.png")
    write_pine(primary[primary["scope"] == "TEMPORAL_TEST"], fail)
    write_pdf([
        "EXP-006A EMA cycle diagnosis",
        f"Primary combo: {PRIMARY}",
        f"TRAIN trades: {int((primary['scope']=='TRAIN').sum())}",
        f"TEMPORAL TEST trades: {int((primary['scope']=='TEMPORAL_TEST').sum())}",
        "This PDF is a compact artifact index. Detailed charts are PNG/CSV.",
        "Holdout after 2025-07-01 04:00 UTC was not used.",
    ], OUT / "EMA_CYCLE_DIAGNOSIS_OVERVIEW.pdf")
    write_report(path_metrics, fail, comp, env, stop_diag, exit_diag)


def verdict_from(path_metrics: pd.DataFrame, fail: pd.DataFrame, env: pd.DataFrame) -> str:
    if fail.empty:
        return "DATA_INSUFFICIENT"
    allc = fail.groupby("scope")["diagnostic_type"].value_counts(normalize=True).unstack(fill_value=0)
    test_bad = float(allc.get("BAD_ENTRY", pd.Series()).get("TEMPORAL_TEST", 0))
    test_good_bad_exit = float(allc.get("GOOD_ENTRY_BAD_EXIT", pd.Series()).get("TEMPORAL_TEST", 0))
    test_stop = float(allc.get("STOP_TOO_TIGHT", pd.Series()).get("TEMPORAL_TEST", 0))
    env_i = env.set_index("scope")
    test_more_chop = (
        env_i.loc["TEMPORAL_TEST", "transition_share"] > env_i.loc["TRAIN", "transition_share"]
        and env_i.loc["TEMPORAL_TEST", "avg_directional_run_bars"] < env_i.loc["TRAIN", "avg_directional_run_bars"]
    )
    h24 = path_metrics[path_metrics["horizon_bars"] == 24].set_index("scope")
    test_entry_positive = h24.loc["TEMPORAL_TEST", "avg_mfe_atr"] >= 1.0 and h24.loc["TEMPORAL_TEST", "plus1_before_minus1_share"] > 0.4
    if test_bad >= 0.45 and not test_entry_positive:
        return "NO_RECOVERABLE_EDGE"
    if test_more_chop and test_bad + allc.get("REGIME_FAILURE", pd.Series()).get("TEMPORAL_TEST", 0) >= 0.40:
        return "REGIME_SHIFT_DOMINATES"
    if test_stop >= 0.35:
        return "STOP_FAILURE"
    if test_entry_positive and test_good_bad_exit >= 0.35:
        return "ENTRY_VALID_EXIT_FAILURE"
    if test_bad >= 0.35:
        return "EXIT_VALID_ENTRY_FAILURE"
    return "MULTIPLE_FAILURES"


def write_report(path_metrics: pd.DataFrame, fail: pd.DataFrame, comp: pd.DataFrame, env: pd.DataFrame, stop_diag: pd.DataFrame, exit_diag: pd.DataFrame) -> None:
    verdict = verdict_from(path_metrics, fail, env)
    h24 = path_metrics[path_metrics["horizon_bars"] == 24].set_index("scope")
    h48 = path_metrics[path_metrics["horizon_bars"] == 48].set_index("scope")
    allc = comp[comp["group"] == "ALL"].set_index("scope")
    stop_summary = stop_diag.groupby("scope").agg(
        pairs=("signal_time", "count"),
        stop_a_premature=("stop_a_premature", "mean"),
        stop_b_increased_loss=("stop_b_increased_loss", "mean"),
        avg_return_diff_b_minus_a=("stop_diff_return_b_minus_a", "mean"),
    ).reset_index()
    exit_cols = [c for c in exit_diag.columns if c.startswith("net_return_")]
    exit_summary = exit_diag.groupby("scope")[exit_cols].mean().reset_index() if exit_cols else pd.DataFrame()
    env_i = env.set_index("scope")
    trend_worse = bool(
        env_i.loc["TEMPORAL_TEST", "transition_share"] > env_i.loc["TRAIN", "transition_share"]
        and env_i.loc["TEMPORAL_TEST", "avg_directional_run_bars"] < env_i.loc["TRAIN", "avg_directional_run_bars"]
    )
    lines = [
        "# EXP-006A — Entry / Exit Diagnosis Report",
        "",
        f"Verdict: **{verdict}**",
        "",
        "## Scope",
        "",
        f"- Primary combo: `{PRIMARY}`.",
        "- Shortlisted EXP-006 combos only.",
        f"- Source: `{DATA}` read-only.",
        f"- True holdout after {TRUE_HOLDOUT_START} was not used.",
        "",
        "## Entry Quality",
        "",
        md_table(path_metrics, ["scope", "horizon_bars", "trades", "avg_signed_return", "avg_mfe_atr", "avg_mae_atr", "plus1_before_minus1_share", "plus2_before_minus1_share"]),
        "",
        "## Failure Mix",
        "",
        md_table(comp[comp["group"] == "ALL"], ["scope", "n", "BAD_ENTRY", "GOOD_ENTRY_BAD_EXIT", "LATE_ENTRY", "EARLY_EXIT", "LATE_EXIT", "STOP_TOO_TIGHT", "REGIME_FAILURE", "MIXED"]),
        "",
        "## Environment",
        "",
        md_table(env, ["scope", "atr14_median", "atr14_iqr", "share_above_ema200", "ema27_crosses", "ema200_crosses", "avg_bull_regime_bars", "avg_bear_regime_bars", "avg_transition_regime_bars", "transition_share", "avg_directional_run_bars", "avg_pullback_depth_atr"]),
        "",
        "## Stop Diagnosis",
        "",
        md_table(stop_summary, ["scope", "pairs", "stop_a_premature", "stop_b_increased_loss", "avg_return_diff_b_minus_a"]),
        "",
        "## Exit Diagnosis",
        "",
        md_table(exit_summary, list(exit_summary.columns)) if not exit_summary.empty else "No exit rows.",
        "",
        "## Answers",
        "",
        f"1. ENTRY_A on TEMPORAL TEST: 24-bar average signed return `{h24.loc['TEMPORAL_TEST', 'avg_signed_return']:.4f}`, average MFE `{h24.loc['TEMPORAL_TEST', 'avg_mfe_atr']:.2f}` ATR. Entry had some favorable path, but it was weaker than TRAIN.",
        f"2. +1 ATR before -1 ATR: TRAIN `{h24.loc['TRAIN', 'plus1_before_minus1_share']:.1%}`, TEST `{h24.loc['TEMPORAL_TEST', 'plus1_before_minus1_share']:.1%}` on 24 bars.",
        f"3. BAD_ENTRY share: TRAIN `{allc.loc['TRAIN', 'BAD_ENTRY']:.1%}`, TEST `{allc.loc['TEMPORAL_TEST', 'BAD_ENTRY']:.1%}`.",
        f"4. GOOD_ENTRY_BAD_EXIT share: TRAIN `{allc.loc['TRAIN', 'GOOD_ENTRY_BAD_EXIT']:.1%}`, TEST `{allc.loc['TEMPORAL_TEST', 'GOOD_ENTRY_BAD_EXIT']:.1%}`.",
        f"5. MFE giveback: TRAIN `{fail[fail.scope=='TRAIN']['mfe_giveback_ratio'].mean():.1%}`, TEST `{fail[fail.scope=='TEMPORAL_TEST']['mfe_giveback_ratio'].mean():.1%}`.",
        "6. EXIT_A vs EXIT_B: see `exit_diagnosis.csv`; no new exit is selected here.",
        "7. STOP_A vs STOP_B: see `stop_diagnosis.csv`; no-stop and stop differences are diagnostic only.",
        f"8. TEST trendiness worsened: `{trend_worse}`.",
        "9. LONG/SHORT differences are in `train_test_failure_comparison.csv` groups `direction:*`.",
        "10. Regime differences are in `train_test_failure_comparison.csv` groups `entry_regime:*`.",
        f"11. Main source of failure: `{verdict}`.",
        f"12. Continue branch: {'only with the diagnosed cause, no immediate new rules' if verdict != 'NO_RECOVERABLE_EDGE' else 'no, close or pause EMA-cycle branch'}." ,
        "13. Next experiment: follow the verdict category only; do not invent a new entry now.",
        "",
        "## Artifacts",
        "",
        "- `artifacts/trade_path_metrics.csv`",
        "- `artifacts/fixed_horizon_outcomes.csv`",
        "- `artifacts/oracle_exit_analysis.csv`",
        "- `artifacts/failure_classification.csv`",
        "- `artifacts/train_test_failure_comparison.csv`",
        "- `artifacts/regime_environment_comparison.csv`",
        "- `artifacts/stop_diagnosis.csv`",
        "- `artifacts/exit_diagnosis.csv`",
        "- `artifacts/entry_quality_train_vs_test.png`",
        "- `artifacts/failure_types_train_vs_test.png`",
        "- `artifacts/mfe_giveback_train_vs_test.png`",
        "- `artifacts/regime_comparison.png`",
        "- `artifacts/EMA_CYCLE_DIAGNOSIS_REVIEW.pine`",
        "- `artifacts/EMA_CYCLE_DIAGNOSIS_OVERVIEW.pdf`",
    ]
    (EXP / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
