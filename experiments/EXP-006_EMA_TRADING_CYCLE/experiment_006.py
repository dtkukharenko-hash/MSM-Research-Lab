#!/usr/bin/env python3
"""EXP-006: fixed EMA27/EMA200 trading cycle research backtest."""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-006_EMA_TRADING_CYCLE"
OUT = EXP / "artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

RESEARCH_START = pd.Timestamp("2023-07-01 00:00")
TRAIN_END = pd.Timestamp("2024-12-19 23:59")
TEST_START = pd.Timestamp("2024-12-20 00:00")
RESEARCH_END = pd.Timestamp("2025-07-01 00:00")
TRUE_HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")

ENTRIES = ["ENTRY_A", "ENTRY_B", "ENTRY_C"]
STOPS = ["STOP_A", "STOP_B"]
EXITS = ["EXIT_A", "EXIT_B", "EXIT_C", "EXIT_D"]
FEE = 0.001
SLIP = 0.0005
START_CAPITAL = 1000.0


@dataclass(frozen=True)
class Combo:
    entry: str
    stop: str
    exit: str

    @property
    def combo_id(self) -> str:
        return f"{self.entry}_{self.stop}_{self.exit}"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df.sort_values("dt").reset_index(drop=True)
    df = df[(df["dt"] >= RESEARCH_START) & (df["dt"] <= RESEARCH_END)].copy().reset_index(drop=True)
    prev = df["close"].shift(1).fillna(df["close"])
    df["tr"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(float),
            (df["high"] - prev).abs().to_numpy(float),
            (df["low"] - prev).abs().to_numpy(float),
        ]
    )
    df["body"] = (df["close"] - df["open"]).abs()
    df["range"] = (df["high"] - df["low"]).replace(0, np.nan)
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["atr14"] = df["tr"].rolling(14, min_periods=1).mean()
    df["ema27_slope_5"] = df["ema27"] - df["ema27"].shift(5)
    df["ema27_slope_10"] = df["ema27"] - df["ema27"].shift(10)
    df["ema200_slope_20"] = df["ema200"] - df["ema200"].shift(20)
    cond_bull = (df["close"] > df["ema200"]) & (df["ema200_slope_20"] > 0) & (df["ema27"] > df["ema200"])
    cond_bear = (df["close"] < df["ema200"]) & (df["ema200_slope_20"] < 0) & (df["ema27"] < df["ema200"])
    df["regime"] = np.where(cond_bull, "BULL_REGIME", np.where(cond_bear, "BEAR_REGIME", "TRANSITION"))
    if df["dt"].max() >= TRUE_HOLDOUT_START:
        raise RuntimeError("True holdout row entered EXP-006 data frame.")
    return df


def side(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def slipped(price: float, direction: str, is_entry: bool, cost_mult: float = 1.0) -> float:
    s = side(direction)
    # Long entry and short exit are paid up; short entry and long exit are paid down.
    sign = s if is_entry else -s
    return price * (1.0 + sign * SLIP * cost_mult)


def prep_long(df: pd.DataFrame, i: int) -> bool:
    r = df.loc[i]
    context = r["regime"] == "BULL_REGIME" or (
        r["regime"] == "TRANSITION" and r["ema27"] > r["ema200"] and r["ema200_slope_20"] >= 0
    )
    last10 = df.loc[i - 9 : i]
    sustained_fall = df.loc[i - 2, "close"] > df.loc[i - 1, "close"] > df.loc[i, "close"]
    return bool(
        context
        and (last10["low"] < last10["ema27"]).any()
        and r["close"] > r["ema27"]
        and r["ema27_slope_5"] > 0
        and r["ema27_slope_10"] >= 0
        and not sustained_fall
        and r["close"] - r["ema27"] <= 2 * r["atr14"]
    )


def prep_short(df: pd.DataFrame, i: int) -> bool:
    r = df.loc[i]
    context = r["regime"] == "BEAR_REGIME" or (
        r["regime"] == "TRANSITION" and r["ema27"] < r["ema200"] and r["ema200_slope_20"] <= 0
    )
    last10 = df.loc[i - 9 : i]
    sustained_rise = df.loc[i - 2, "close"] < df.loc[i - 1, "close"] < df.loc[i, "close"]
    return bool(
        context
        and (last10["high"] > last10["ema27"]).any()
        and r["close"] < r["ema27"]
        and r["ema27_slope_5"] < 0
        and r["ema27_slope_10"] <= 0
        and not sustained_rise
        and r["ema27"] - r["close"] <= 2 * r["atr14"]
    )


def signal_direction(df: pd.DataFrame, i: int, entry: str) -> str | None:
    if i < 220 or i + 1 >= len(df):
        return None
    pl = prep_long(df, i)
    ps = prep_short(df, i)
    if entry == "ENTRY_A":
        if pl and df.loc[i - 1, "close"] <= df.loc[i - 1, "ema27"] and df.loc[i, "close"] > df.loc[i, "ema27"]:
            return "LONG"
        if ps and df.loc[i - 1, "close"] >= df.loc[i - 1, "ema27"] and df.loc[i, "close"] < df.loc[i, "ema27"]:
            return "SHORT"
    elif entry == "ENTRY_B":
        if pl and df.loc[i, "high"] > df.loc[i - 3 : i - 1, "high"].max():
            return "LONG"
        if ps and df.loc[i, "low"] < df.loc[i - 3 : i - 1, "low"].min():
            return "SHORT"
    elif entry == "ENTRY_C":
        if pl and df.loc[i - 1, "close"] > df.loc[i - 1, "ema27"] and df.loc[i, "close"] >= df.loc[i - 1, "close"]:
            return "LONG"
        if ps and df.loc[i - 1, "close"] < df.loc[i - 1, "ema27"] and df.loc[i, "close"] <= df.loc[i - 1, "close"]:
            return "SHORT"
    return None


def initial_stop(df: pd.DataFrame, signal_i: int, entry_price: float, direction: str, stop_kind: str) -> float:
    if stop_kind == "STOP_A":
        w = df.loc[signal_i - 4 : signal_i]
        return float(w["low"].min() if direction == "LONG" else w["high"].max())
    atr = float(df.loc[signal_i, "atr14"])
    return entry_price - 1.5 * atr if direction == "LONG" else entry_price + 1.5 * atr


def regime_flip(df: pd.DataFrame, i: int, direction: str) -> bool:
    r = df.loc[i]
    if direction == "LONG":
        return bool(r["close"] < r["ema200"] and r["ema27"] < r["ema200"] and r["ema200_slope_20"] < 0)
    return bool(r["close"] > r["ema200"] and r["ema27"] > r["ema200"] and r["ema200_slope_20"] > 0)


def latest_reference(df: pd.DataFrame, entry_i: int, i: int, direction: str) -> dict | None:
    if i <= entry_i + 1:
        return None
    start = max(entry_i, 10)
    chosen = None
    for j in range(start, i + 1):
        r = df.loc[j]
        med = float(df.loc[j - 10 : j - 1, "body"].median())
        rng = float(r["range"]) if math.isfinite(float(r["range"])) and float(r["range"]) > 0 else 1e-12
        if direction == "LONG":
            cond = r["close"] > r["open"] and r["body"] > med and (r["close"] - r["low"]) / rng >= 2 / 3
            updated = df.loc[j + 1 : i, "high"].max() > r["high"] if j + 1 <= i else False
        else:
            cond = r["close"] < r["open"] and r["body"] > med and (r["high"] - r["close"]) / rng >= 2 / 3
            updated = df.loc[j + 1 : i, "low"].min() < r["low"] if j + 1 <= i else False
        if cond and updated:
            lo = min(float(r["open"]), float(r["close"]))
            hi = max(float(r["open"]), float(r["close"]))
            chosen = {
                "ref_time": r["dt"],
                "ref_idx": j,
                "ref_open": float(r["open"]),
                "ref_close": float(r["close"]),
                "ref_mid": (lo + hi) / 2,
                "ref_body_low": lo,
                "ref_body_high": hi,
            }
    return chosen


def exit_signal(df: pd.DataFrame, i: int, pos: dict, exit_kind: str, ref: dict | None, pending: dict | None) -> tuple[bool, str, dict | None]:
    direction = pos["direction"]
    s = side(direction)
    if regime_flip(df, i, direction):
        return True, "REGIME_FLIP", None
    close = float(df.loc[i, "close"])
    ema27 = float(df.loc[i, "ema27"])
    if exit_kind == "EXIT_A":
        if (direction == "LONG" and close < ema27) or (direction == "SHORT" and close > ema27):
            return True, "EMA27_CLOSE", None
    if exit_kind in {"EXIT_B", "EXIT_D"}:
        if i > pos["entry_i"]:
            c1 = float(df.loc[i - 1, "close"])
            e1 = float(df.loc[i - 1, "ema27"])
            if direction == "LONG" and c1 < e1 and close < ema27:
                return True, "EMA27_TWO_CLOSES", None
            if direction == "SHORT" and c1 > e1 and close > ema27:
                return True, "EMA27_TWO_CLOSES", None
    if exit_kind == "EXIT_D" and ref is not None:
        if direction == "LONG" and close < ref["ref_open"]:
            return True, "REFERENCE_OPEN_BREAK", None
        if direction == "SHORT" and close > ref["ref_open"]:
            return True, "REFERENCE_OPEN_BREAK", None
    if exit_kind == "EXIT_C" and ref is not None:
        if pending is not None:
            extreme_updated = (
                float(df.loc[i, "high"]) > pending["extreme_at_trigger"]
                if direction == "LONG"
                else float(df.loc[i, "low"]) < pending["extreme_at_trigger"]
            )
            if extreme_updated:
                return False, "", None
            if i - pending["trigger_i"] >= 2:
                return True, "REFERENCE_MID_CONFIRM", None
            return False, "", pending
        counter = (direction == "LONG" and close < float(df.loc[i, "open"])) or (
            direction == "SHORT" and close > float(df.loc[i, "open"])
        )
        violated = (direction == "LONG" and close < ref["ref_mid"]) or (direction == "SHORT" and close > ref["ref_mid"])
        if counter and violated:
            extreme = float(df.loc[pos["entry_i"] : i, "high"].max() if direction == "LONG" else df.loc[pos["entry_i"] : i, "low"].min())
            return False, "", {"trigger_i": i, "extreme_at_trigger": extreme}
    return False, "", pending


def backtest(df: pd.DataFrame, combo: Combo, start: pd.Timestamp, end: pd.Timestamp, combo_scope: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    trades = []
    refs = []
    pos = None
    pending_c = None
    trade_id = 1
    for i in range(220, len(df) - 1):
        t = df.loc[i, "dt"]
        next_t = df.loc[i + 1, "dt"]
        if next_t < start or t > end:
            continue
        if pos is None:
            if t < start or t > end:
                continue
            direction = signal_direction(df, i, combo.entry)
            if direction is None:
                continue
            entry_raw = float(df.loc[i + 1, "open"])
            entry_exec = slipped(entry_raw, direction, True)
            stop = initial_stop(df, i, entry_exec, direction, combo.stop)
            if (direction == "LONG" and stop >= entry_exec) or (direction == "SHORT" and stop <= entry_exec):
                continue
            pos = {
                "trade_id": f"{combo.combo_id}_{combo_scope}_{trade_id:04d}",
                "combo_id": combo.combo_id,
                "entry": combo.entry,
                "stop_kind": combo.stop,
                "exit": combo.exit,
                "direction": direction,
                "signal_i": i,
                "entry_i": i + 1,
                "signal_time": df.loc[i, "dt"],
                "entry_time": df.loc[i + 1, "dt"],
                "entry_raw": entry_raw,
                "entry_price": entry_exec,
                "stop_price": stop,
                "entry_regime": df.loc[i, "regime"],
                "mfe": 0.0,
                "mae": 0.0,
                "best_i": i + 1,
                "worst_i": i + 1,
            }
            pending_c = None
            trade_id += 1
            continue
        direction = pos["direction"]
        s = side(direction)
        high_ret = s * (float(df.loc[i, "high"]) - pos["entry_price"]) / pos["entry_price"]
        low_ret = s * (float(df.loc[i, "low"]) - pos["entry_price"]) / pos["entry_price"]
        bar_mfe = max(high_ret, low_ret)
        bar_mae = min(high_ret, low_ret)
        if bar_mfe > pos["mfe"]:
            pos["mfe"] = bar_mfe
            pos["best_i"] = i
        if bar_mae < pos["mae"]:
            pos["mae"] = bar_mae
            pos["worst_i"] = i
        stop_hit = (direction == "LONG" and float(df.loc[i, "low"]) <= pos["stop_price"]) or (
            direction == "SHORT" and float(df.loc[i, "high"]) >= pos["stop_price"]
        )
        exit_now = False
        reason = ""
        exit_raw = None
        ref = latest_reference(df, pos["entry_i"], i, direction)
        if ref is not None:
            refs.append({"trade_id": pos["trade_id"], "combo_id": combo.combo_id, "scope": combo_scope, **ref})
        if stop_hit:
            exit_now = True
            reason = "STOP"
            exit_raw = pos["stop_price"]
        else:
            exit_now, reason, pending_c = exit_signal(df, i, pos, combo.exit, ref, pending_c)
            if exit_now and i + 1 < len(df):
                exit_raw = float(df.loc[i + 1, "open"])
        if exit_now:
            exit_i = i if reason == "STOP" else i + 1
            if exit_i >= len(df):
                exit_i = len(df) - 1
            if exit_raw is None:
                exit_raw = float(df.loc[exit_i, "open"])
            exit_exec = slipped(exit_raw, direction, False)
            gross = s * (exit_exec - pos["entry_price"]) / pos["entry_price"]
            net = gross - 2 * FEE
            bars = exit_i - pos["entry_i"] + 1
            mfe = pos["mfe"]
            capture = net / mfe if mfe > 0 else 0.0
            delay = max(0, exit_i - pos["best_i"])
            trades.append(
                {
                    **{k: pos[k] for k in ["trade_id", "combo_id", "entry", "stop_kind", "exit", "direction", "signal_time", "entry_time", "entry_regime", "entry_raw", "entry_price", "stop_price"]},
                    "scope": combo_scope,
                    "exit_time": df.loc[exit_i, "dt"],
                    "exit_price": exit_exec,
                    "exit_reason": reason,
                    "bars": bars,
                    "gross_return": gross,
                    "net_return": net,
                    "mfe": mfe,
                    "mae": pos["mae"],
                    "mfe_capture": capture,
                    "exit_delay_bars": delay,
                    "best_time": df.loc[pos["best_i"], "dt"],
                    "worst_time": df.loc[pos["worst_i"], "dt"],
                }
            )
            pos = None
            pending_c = None
    return pd.DataFrame(trades), pd.DataFrame(refs)


def equity_curve(returns: pd.Series, start_capital: float = START_CAPITAL) -> pd.Series:
    vals = [start_capital]
    for r in returns.fillna(0):
        vals.append(vals[-1] * (1 + float(r)))
    return pd.Series(vals[1:])


def max_dd(eq: pd.Series) -> float:
    if eq.empty:
        return 0.0
    peak = eq.cummax()
    dd = eq / peak - 1
    return float(dd.min())


def metrics(tr: pd.DataFrame, combo_id: str, scope: str, cost_mult: float = 1.0) -> dict:
    if tr.empty:
        return {"combo_id": combo_id, "scope": scope, "cost_mult": cost_mult, "trades": 0}
    rets = tr["gross_return"] - (2 * FEE * cost_mult)
    eq = equity_curve(rets)
    wins = rets[rets > 0]
    losses = rets[rets < 0]
    pf = float(wins.sum() / abs(losses.sum())) if abs(losses.sum()) > 1e-12 else (999.0 if wins.sum() > 0 else 0.0)
    long_rets = rets[tr["direction"] == "LONG"]
    short_rets = rets[tr["direction"] == "SHORT"]
    period_bars = max(1, (pd.to_datetime(tr["exit_time"]).max() - pd.to_datetime(tr["entry_time"]).min()).total_seconds() / (4 * 3600))
    exposure = float(tr["bars"].sum() / period_bars)
    return {
        "combo_id": combo_id,
        "scope": scope,
        "cost_mult": cost_mult,
        "trades": int(len(tr)),
        "long_trades": int((tr["direction"] == "LONG").sum()),
        "short_trades": int((tr["direction"] == "SHORT").sum()),
        "win_rate": float((rets > 0).mean()),
        "average_trade": float(rets.mean()),
        "median_trade": float(rets.median()),
        "profit_factor": pf,
        "total_return": float(eq.iloc[-1] / START_CAPITAL - 1),
        "max_drawdown": max_dd(eq),
        "exposure": exposure,
        "avg_bars": float(tr["bars"].mean()),
        "median_bars": float(tr["bars"].median()),
        "avg_mae": float(tr["mae"].mean()),
        "avg_mfe": float(tr["mfe"].mean()),
        "mfe_capture_ratio": float(tr["mfe_capture"].replace([np.inf, -np.inf], np.nan).fillna(0).mean()),
        "exit_delay_bars": float(tr["exit_delay_bars"].mean()),
        "stop_out_rate": float((tr["exit_reason"] == "STOP").mean()),
        "regime_flip_exit_rate": float((tr["exit_reason"] == "REGIME_FLIP").mean()),
        "long_total_return": float((1 + long_rets).prod() - 1) if len(long_rets) else 0.0,
        "short_total_return": float((1 + short_rets).prod() - 1) if len(short_rets) else 0.0,
        "fee_slippage_model": f"fee {FEE:.4f} per side, slippage {SLIP:.4f} per side, cost_mult={cost_mult}",
    }


def concentration(tr: pd.DataFrame, combo_id: str, scope: str) -> dict:
    if tr.empty:
        return {"combo_id": combo_id, "scope": scope, "top1_profit_share": np.nan, "without_top1_total_return": np.nan}
    wins = tr[tr["net_return"] > 0].copy()
    top_share = float(wins["net_return"].max() / wins["net_return"].sum()) if len(wins) and wins["net_return"].sum() > 0 else 1.0
    if len(tr):
        drop_idx = tr["net_return"].idxmax()
        without = tr.drop(index=drop_idx)
        total_without = float((1 + without["net_return"]).prod() - 1) if len(without) else 0.0
    else:
        total_without = 0.0
    return {"combo_id": combo_id, "scope": scope, "top1_profit_share": top_share, "without_top1_total_return": total_without}


class Raster:
    def __init__(self, width: int = 1000, height: int = 520, bg: tuple[int, int, int] = (255, 255, 255)):
        self.w = width
        self.h = height
        self.p = bytearray(bg * (width * height))

    def dot(self, x: int, y: int, c: tuple[int, int, int]) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            k = (y * self.w + x) * 3
            self.p[k : k + 3] = bytes(c)

    def line(self, x0: float, y0: float, x1: float, y1: float, c: tuple[int, int, int], width: int = 1) -> None:
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
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


def scale_points(xs: list[float], ys: list[float], width: int, height: int, pad: int = 44) -> list[tuple[float, float]]:
    if not xs or not ys:
        return []
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if xmax == xmin:
        xmax = xmin + 1
    if ymax == ymin:
        ymax = ymin + 1
    pts = []
    for x, y in zip(xs, ys):
        px = pad + (x - xmin) / (xmax - xmin) * (width - 2 * pad)
        py = height - pad - (y - ymin) / (ymax - ymin) * (height - 2 * pad)
        pts.append((px, py))
    return pts


def raster_line_chart(series: list[tuple[str, list[float]]], path: Path, width: int = 1000, height: int = 520) -> None:
    colors = [(0, 110, 180), (220, 80, 40), (60, 150, 80), (120, 80, 180), (30, 30, 30), (180, 150, 0)]
    r = Raster(width, height)
    r.line(44, height - 44, width - 20, height - 44, (160, 160, 160))
    r.line(44, 20, 44, height - 44, (160, 160, 160))
    for idx, (_, vals) in enumerate(series):
        pts = scale_points(list(range(len(vals))), vals, width, height)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            r.line(x0, y0, x1, y1, colors[idx % len(colors)], 2)
    r.save(path)


def pdf_text(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_stream_page(lines: list[str], width: int = 792, height: int = 612) -> str:
    return "\n".join(lines)


def write_pdf(pages: list[str], path: Path, width: int = 792, height: int = 612) -> None:
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for i, content in enumerate(pages):
        content_b = content.encode("latin-1", errors="replace")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {4 + i * 2} 0 R >>".encode())
        objects.append(f"<< /Length {len(content_b)} >>\nstream\n".encode() + content_b + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def pdf_polyline(vals: list[float], x: float, y: float, w: float, h: float, color: str = "0 0 0", width: float = 0.7) -> str:
    if len(vals) < 2:
        return ""
    ymin, ymax = min(vals), max(vals)
    if ymax == ymin:
        ymax = ymin + 1
    cmds = [f"{color} RG {width} w"]
    for idx, val in enumerate(vals):
        px = x + idx / (len(vals) - 1) * w
        py = y + (val - ymin) / (ymax - ymin) * h
        cmds.append(f"{px:.2f} {py:.2f} {'m' if idx == 0 else 'l'}")
    cmds.append("S")
    return "\n".join(cmds)


def build_analyses(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows_e = []
    for entry, g in trades.groupby("entry"):
        early = float(((g["mae"] < -0.0075) & (g["mfe"] > 0)).mean()) if len(g) else 0
        late = float((g["mfe"] < 0.0075).mean()) if len(g) else 0
        rows_e.append(
            {
                "entry": entry,
                "signals": int(len(g)),
                "false_starts": int((g["mfe"] <= 0.003).sum()),
                "avg_adverse_move": float(g["mae"].mean()),
                "too_early": int(((g["mae"] < -0.0075) & (g["mfe"] > 0)).sum()),
                "too_late": int((g["mfe"] < 0.0075).sum()),
                "bull_regime_share": float((g["entry_regime"] == "BULL_REGIME").mean()),
                "bear_regime_share": float((g["entry_regime"] == "BEAR_REGIME").mean()),
                "transition_share": float((g["entry_regime"] == "TRANSITION").mean()),
                "long_avg_return": float(g.loc[g["direction"] == "LONG", "net_return"].mean()) if (g["direction"] == "LONG").any() else 0.0,
                "short_avg_return": float(g.loc[g["direction"] == "SHORT", "net_return"].mean()) if (g["direction"] == "SHORT").any() else 0.0,
                "early_definition": "MAE < -0.75% with positive MFE",
                "late_definition": "MFE < 0.75%",
            }
        )
    rows_x = []
    for ex, g in trades.groupby("exit"):
        rows_x.append(
            {
                "exit": ex,
                "trades": int(len(g)),
                "avg_mfe_capture": float(g["mfe_capture"].replace([np.inf, -np.inf], np.nan).fillna(0).mean()),
                "avg_profit_giveback_from_mfe": float((g["mfe"] - g["net_return"]).mean()),
                "avg_exit_delay_bars": float(g["exit_delay_bars"].mean()),
                "premature_exits": int(((g["mfe"] - g["net_return"]) < 0.005).sum()),
                "late_exits": int((g["exit_delay_bars"] >= 5).sum()),
                "ema27_exits": int(g["exit_reason"].str.contains("EMA27", na=False).sum()),
                "reference_exits": int(g["exit_reason"].str.contains("REFERENCE", na=False).sum()),
                "stop_exits": int((g["exit_reason"] == "STOP").sum()),
                "regime_flip_exits": int((g["exit_reason"] == "REGIME_FLIP").sum()),
            }
        )
    return pd.DataFrame(rows_e), pd.DataFrame(rows_x)


def trade_pdf_panel(df: pd.DataFrame, trade: pd.Series, x: float, y: float, wbox: float, hbox: float) -> str:
    entry_i = int(df.index[df["dt"] == pd.Timestamp(trade["entry_time"])][0])
    exit_i = int(df.index[df["dt"] == pd.Timestamp(trade["exit_time"])][0])
    lo = max(0, entry_i - 20)
    hi = min(len(df) - 1, exit_i + 20)
    win = df.loc[lo:hi]
    vals = list(win["close"].astype(float))
    ymin = min(list(win["low"].astype(float)) + [float(trade["stop_price"])])
    ymax = max(list(win["high"].astype(float)) + [float(trade["stop_price"])])
    if ymax == ymin:
        ymax = ymin + 1
    def px(idx: int) -> float:
        return x + (idx - lo) / max(1, hi - lo) * wbox
    def py(val: float) -> float:
        return y + (val - ymin) / (ymax - ymin) * hbox
    cmds = [f"0.85 0.85 0.85 RG 0.5 w {x:.2f} {y:.2f} {wbox:.2f} {hbox:.2f} re S"]
    for col, cname in [("close", "0 0 0"), ("ema27", "0 0.45 0.85"), ("ema200", "0.95 0.45 0")]:
        pts = []
        for idx, val in zip(win.index, win[col].astype(float)):
            pts.append((px(idx), py(val)))
        cmds.append(f"{cname} RG 0.7 w")
        for j, (xx, yy) in enumerate(pts):
            cmds.append(f"{xx:.2f} {yy:.2f} {'m' if j == 0 else 'l'}")
        cmds.append("S")
    ei = px(entry_i)
    xi = px(exit_i)
    stop_y = py(float(trade["stop_price"]))
    cmds += [
        f"0 0.6 0 RG 1 w {ei:.2f} {y:.2f} m {ei:.2f} {y+hbox:.2f} l S",
        f"0.9 0 0 RG 1 w {xi:.2f} {y:.2f} m {xi:.2f} {y+hbox:.2f} l S",
        f"0.7 0 0 RG 0.5 w {x:.2f} {stop_y:.2f} m {x+wbox:.2f} {stop_y:.2f} l S",
        f"BT /F1 7 Tf {x:.2f} {y+hbox+8:.2f} Td ({pdf_text(str(trade['trade_id'])[:46])}) Tj ET",
        f"BT /F1 7 Tf {x:.2f} {y-10:.2f} Td ({pdf_text(str(trade['direction']))} {pdf_text(str(trade['exit_reason']))} net={float(trade['net_return']):.2%}) Tj ET",
    ]
    return "\n".join(cmds)


def make_plots(df: pd.DataFrame, trades: pd.DataFrame, metrics_df: pd.DataFrame, shortlist: pd.DataFrame) -> None:
    eq_series = []
    for combo_id, g in trades[trades["combo_id"].isin(shortlist["combo_id"])].groupby("combo_id"):
        eq_series.append((combo_id, list(equity_curve(g.sort_values("exit_time")["net_return"]))))
    if not eq_series:
        eq_series = [("no_shortlist", [START_CAPITAL, START_CAPITAL])]
    raster_line_chart(eq_series, OUT / "equity_curves.png")

    ea = pd.read_csv(OUT / "entry_analysis.csv")
    raster_line_chart([(row["entry"], [0, float(row["avg_adverse_move"])]) for _, row in ea.iterrows()] or [("empty", [0, 0])], OUT / "entry_comparison.png")

    xa = pd.read_csv(OUT / "exit_analysis.csv")
    raster_line_chart([(row["exit"], [0, float(row["avg_profit_giveback_from_mfe"])]) for _, row in xa.iterrows()] or [("empty", [0, 0])], OUT / "exit_comparison.png")

    m = metrics_df[metrics_df["scope"] == "TRAIN"].copy().sort_values("mfe_capture_ratio")
    raster_line_chart([("profit_factor_by_mfe_capture", list(m["profit_factor"].fillna(0)))], OUT / "mfe_capture.png")

    sample = []
    pool = trades[trades["combo_id"].isin(shortlist["combo_id"])].copy()
    if not pool.empty:
        sample.extend(pool.nlargest(5, "net_return").to_dict("records"))
        sample.extend(pool.nsmallest(5, "net_return").to_dict("records"))
        sample.extend(pool.nsmallest(5, "exit_delay_bars").to_dict("records"))
        sample.extend(pool.nlargest(5, "exit_delay_bars").to_dict("records"))
    pages = []
    if not sample:
        pages.append("BT /F1 16 Tf 250 300 Td (No shortlist trades available) Tj ET")
    for k in range(0, len(sample), 4):
        cmds = ["BT /F1 12 Tf 36 582 Td (EXP-006 EMA Trading Cycle Visual Audit) Tj ET"]
        boxes = [(36, 330), (414, 330), (36, 70), (414, 70)]
        for rec, (xx, yy) in zip(sample[k : k + 4], boxes):
            cmds.append(trade_pdf_panel(df, pd.Series(rec), xx, yy, 330, 190))
        pages.append(pdf_stream_page(cmds))
    write_pdf(pages, OUT / "EMA_TRADING_CYCLE_OVERVIEW.pdf")


def write_pine(short_trades: pd.DataFrame) -> None:
    rows = short_trades.head(80).copy()
    def ts_expr(t: str) -> str:
        p = pd.Timestamp(t)
        return f'timestamp("Etc/UTC", {p.year}, {p.month}, {p.day}, {p.hour}, {p.minute})'
    starts = ", ".join(ts_expr(str(t)) for t in rows["entry_time"]) or 'timestamp("Etc/UTC", 2023, 7, 1, 0, 0)'
    ends = ", ".join(ts_expr(str(t)) for t in rows["exit_time"]) or 'timestamp("Etc/UTC", 2023, 7, 1, 4, 0)'
    dirs = ", ".join(f'"{d}"' for d in rows["direction"]) or '"NA"'
    labels = ", ".join(f'"{r.entry}/{r.stop_kind}/{r.exit}"' for _, r in rows.iterrows()) or '"NA"'
    text = f"""//@version=6
indicator("EXP-006 EMA Trading Cycle Review", overlay=true, max_lines_count=500, max_labels_count=500)

// Visual research markup only. Not a strategy and not an auto-detector.
// Use on ADAUSDT 4H. True holdout is intentionally not marked.
showEntryA = input.bool(true, "show ENTRY_A")
showEntryB = input.bool(true, "show ENTRY_B")
showEntryC = input.bool(true, "show ENTRY_C")
showExitA = input.bool(true, "show EXIT_A")
showExitB = input.bool(true, "show EXIT_B")
showExitC = input.bool(true, "show EXIT_C")
showExitD = input.bool(true, "show EXIT_D")
showLabels = input.bool(true, "show labels")

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
var string[] dirs = array.from({dirs})
var string[] labs = array.from({labels})

f_visible(lab) =>
    str.contains(lab, "ENTRY_A") and showEntryA or str.contains(lab, "ENTRY_B") and showEntryB or str.contains(lab, "ENTRY_C") and showEntryC

f_exit_visible(lab) =>
    str.contains(lab, "EXIT_A") and showExitA or str.contains(lab, "EXIT_B") and showExitB or str.contains(lab, "EXIT_C") and showExitC or str.contains(lab, "EXIT_D") and showExitD

refLong = close > open and math.abs(close - open) > ta.median(math.abs(close - open), 10) and close >= low + (high - low) * 0.66
refShort = close < open and math.abs(close - open) > ta.median(math.abs(close - open), 10) and close <= high - (high - low) * 0.66
barcolor(refLong ? color.new(color.lime, 0) : refShort ? color.new(color.fuchsia, 0) : na)

for i = 0 to array.size(starts) - 1
    int st = array.get(starts, i)
    int en = array.get(ends, i)
    string dir = array.get(dirs, i)
    string lab = array.get(labs, i)
    if time == st and f_visible(lab)
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.green, width=2)
        if showLabels
            label.new(time, high, "EXP-006 " + dir + " " + lab, xloc=xloc.bar_time, style=label.style_label_down, color=color.green, textcolor=color.white, size=size.tiny)
    if time == en and f_exit_visible(lab)
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.red, width=2)
        if showLabels
            label.new(time, low, "exit " + lab, xloc=xloc.bar_time, style=label.style_label_up, color=color.red, textcolor=color.white, size=size.tiny)
"""
    (OUT / "EMA_TRADING_CYCLE_REVIEW.pine").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    df = load_ohlc()
    combos = [Combo(e, s, x) for e in ENTRIES for s in STOPS for x in EXITS]
    all_trades = []
    all_refs = []
    metric_rows = []
    stress_rows = []
    concentration_rows = []
    for combo in combos:
        tr_train, refs_train = backtest(df, combo, RESEARCH_START, TRAIN_END, "TRAIN")
        tr_test, refs_test = backtest(df, combo, TEST_START, RESEARCH_END, "TEMPORAL_TEST")
        for tr in [tr_train, tr_test]:
            if not tr.empty:
                all_trades.append(tr)
        for rr in [refs_train, refs_test]:
            if not rr.empty:
                all_refs.append(rr)
        for scope, tr in [("TRAIN", tr_train), ("TEMPORAL_TEST", tr_test)]:
            metric_rows.append(metrics(tr, combo.combo_id, scope, 1.0))
            concentration_rows.append(concentration(tr, combo.combo_id, scope))
            for cm in [1.0, 2.0, 3.0]:
                stress_rows.append(metrics(tr, combo.combo_id, scope, cm))
    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    refs = pd.concat(all_refs, ignore_index=True) if all_refs else pd.DataFrame()
    metrics_df = pd.DataFrame(metric_rows)
    stress = pd.DataFrame(stress_rows)
    conc = pd.DataFrame(concentration_rows)
    trades.to_csv(OUT / "trades_all_combinations.csv", index=False)
    metrics_df.to_csv(OUT / "combination_metrics.csv", index=False)
    refs.to_csv(OUT / "reference_candles.csv", index=False)
    stress.to_csv(OUT / "cost_stress.csv", index=False)
    conc.to_csv(OUT / "concentration_checks.csv", index=False)
    entry_analysis, exit_analysis = build_analyses(trades[trades["scope"] == "TRAIN"] if not trades.empty else trades)
    entry_analysis.to_csv(OUT / "entry_analysis.csv", index=False)
    exit_analysis.to_csv(OUT / "exit_analysis.csv", index=False)

    train = metrics_df[metrics_df["scope"] == "TRAIN"].merge(conc[conc["scope"] == "TRAIN"], on=["combo_id", "scope"], how="left")
    s2 = stress[(stress["scope"] == "TRAIN") & (stress["cost_mult"] == 2.0)][["combo_id", "profit_factor", "total_return"]].rename(columns={"profit_factor": "pf_cost_x2", "total_return": "return_cost_x2"})
    s3 = stress[(stress["scope"] == "TRAIN") & (stress["cost_mult"] == 3.0)][["combo_id", "profit_factor", "total_return"]].rename(columns={"profit_factor": "pf_cost_x3", "total_return": "return_cost_x3"})
    train = train.merge(s2, on="combo_id", how="left").merge(s3, on="combo_id", how="left")
    train["passes_train_gate"] = (
        (train["profit_factor"] > 1.10)
        & (train["max_drawdown"] >= -0.35)
        & (train["trades"] >= 20)
        & (train["return_cost_x2"] > -0.05)
        & (train["top1_profit_share"] <= 0.60)
        & ~((train["long_total_return"] > 0) & (train["short_total_return"] < -0.20))
        & ~((train["short_total_return"] > 0) & (train["long_total_return"] < -0.20))
    )
    train["rank_score"] = (
        train["profit_factor"].clip(0, 5)
        + train["mfe_capture_ratio"].clip(-1, 2)
        + train["total_return"].clip(-1, 3)
        - train["top1_profit_share"].fillna(1)
        + train["return_cost_x2"].fillna(-1).clip(-1, 3)
        + (train["trades"].clip(0, 80) / 80)
    )
    rankings = train.sort_values(["passes_train_gate", "rank_score"], ascending=[False, False])
    shortlist = rankings[rankings["passes_train_gate"]].head(3).copy()
    if shortlist.empty:
        shortlist = rankings.head(0).copy()
    rankings.to_csv(OUT / "train_rankings.csv", index=False)
    shortlist.to_csv(OUT / "shortlist.csv", index=False)
    test_metrics = metrics_df[(metrics_df["scope"] == "TEMPORAL_TEST") & (metrics_df["combo_id"].isin(shortlist["combo_id"]))]
    test_trades = trades[(trades["scope"] == "TEMPORAL_TEST") & (trades["combo_id"].isin(shortlist["combo_id"]))] if not trades.empty and not shortlist.empty else pd.DataFrame()
    test_metrics.to_csv(OUT / "temporal_test_metrics.csv", index=False)
    test_trades.to_csv(OUT / "temporal_test_trades.csv", index=False)
    make_plots(df, trades, metrics_df, shortlist)
    write_pine(test_trades if not test_trades.empty else trades[trades["scope"] == "TRAIN"].head(80))
    write_report(df, trades, metrics_df, rankings, shortlist, test_metrics, stress, conc, entry_analysis, exit_analysis)


def fmt_pct(x: float) -> str:
    if pd.isna(x):
        return "n/a"
    return f"{x:.2%}"


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    if df.empty:
        return "No rows."
    use = df[cols].copy()
    def cell(v) -> str:
        if isinstance(v, float):
            return f"{v:.6g}"
        return str(v)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = ["| " + " | ".join(cell(v) for v in row) + " |" for row in use.to_numpy()]
    return "\n".join([header, sep, *rows])


def write_report(df: pd.DataFrame, trades: pd.DataFrame, metrics_df: pd.DataFrame, rankings: pd.DataFrame, shortlist: pd.DataFrame, test_metrics: pd.DataFrame, stress: pd.DataFrame, conc: pd.DataFrame, entry_analysis: pd.DataFrame, exit_analysis: pd.DataFrame) -> None:
    if len(df) < 300:
        verdict = "DATA_INSUFFICIENT"
    elif shortlist.empty:
        verdict = "NO_WORKABLE_CYCLE"
    else:
        best_test = test_metrics.sort_values("profit_factor", ascending=False).head(1)
        strong = (
            not best_test.empty
            and float(best_test.iloc[0]["profit_factor"]) > 1.10
            and float(best_test.iloc[0]["max_drawdown"]) >= -0.35
            and bool((stress[(stress["scope"] == "TEMPORAL_TEST") & (stress["combo_id"] == best_test.iloc[0]["combo_id"]) & (stress["cost_mult"] == 2.0)]["total_return"] > -0.05).any())
            and bool((conc[(conc["scope"] == "TEMPORAL_TEST") & (conc["combo_id"] == best_test.iloc[0]["combo_id"])]["top1_profit_share"] <= 0.60).any())
        )
        if strong:
            verdict = "WORKABLE_EMA_CYCLE_FOUND"
        else:
            verdict = "WEAK_EMA_CYCLE"
    train_top = rankings.head(3)
    best_train = rankings.iloc[0] if len(rankings) else None
    best_test = test_metrics.sort_values("profit_factor", ascending=False).head(1)
    best_test_row = best_test.iloc[0] if not best_test.empty else None
    best_entry = entry_analysis.sort_values("avg_adverse_move", ascending=False).head(1)
    best_exit = exit_analysis.sort_values("avg_mfe_capture", ascending=False).head(1)
    stop_train = metrics_df[metrics_df["scope"] == "TRAIN"].copy()
    stop_summary = stop_train.assign(stop_kind=stop_train["combo_id"].str.extract(r"(STOP_[AB])")[0]).groupby("stop_kind")["avg_mfe"].mean().sort_values(ascending=False)
    lines = [
        "# EXP-006 — EMA Trading Cycle Report",
        "",
        f"Verdict: **{verdict}**",
        "",
        "## Data Boundary",
        "",
        f"- Source: `{DATA}` read-only.",
        f"- Research rows used: {len(df)}, from {df['dt'].min()} to {df['dt'].max()}.",
        f"- Train: {RESEARCH_START} -> {TRAIN_END}.",
        f"- Temporal test: {TEST_START} -> {RESEARCH_END}.",
        f"- True holdout from {TRUE_HOLDOUT_START} was not loaded into the experiment dataframe.",
        "- Costs: fee 0.10% per side and slippage 0.05% per side; stress x2 and x3 are reported separately.",
        "- Causality: all entries and close-based exits are executed on the next open; active references are updated only from closed bars.",
        "",
        "## Train Shortlist",
        "",
    ]
    if shortlist.empty:
        lines.append("No combination passed the fixed train gates: PF > 1.10, max drawdown >= -35%, at least 20 trades, x2 costs not destructive, top-1 concentration <= 60%, and no complete LONG/SHORT conflict.")
    else:
        lines.append(md_table(shortlist, ["combo_id", "trades", "profit_factor", "total_return", "max_drawdown", "mfe_capture_ratio", "pf_cost_x2", "return_cost_x2", "top1_profit_share"]))
    lines += ["", "## Temporal Test", ""]
    if test_metrics.empty:
        lines.append("Temporal test was not run on a shortlist because no train combination passed the gates.")
    else:
        lines.append(md_table(test_metrics, ["combo_id", "trades", "profit_factor", "total_return", "max_drawdown", "mfe_capture_ratio", "stop_out_rate", "regime_flip_exit_rate"]))
        lines.append("")
        lines.append("Cost stress for shortlisted temporal-test combinations is stored in `artifacts/cost_stress.csv`.")
    lines += [
        "",
        "## Answers",
        "",
        f"1. Working EMA regime: train trades occurred mainly in explicit EMA regimes; best train combo was `{best_train['combo_id'] if best_train is not None else 'n/a'}`. The regime filter was not enough by itself; transfer is judged by temporal test.",
        f"2. Best entry by adverse-move proxy: `{best_entry.iloc[0]['entry'] if not best_entry.empty else 'n/a'}`.",
        f"3. Stop that least broke favorable movement by average MFE: `{stop_summary.index[0] if len(stop_summary) else 'n/a'}`.",
        f"4. Exit with highest average MFE capture on train: `{best_exit.iloc[0]['exit'] if not best_exit.empty else 'n/a'}`.",
        f"5. Active reference candle helped only where reference exits appeared; reference exit counts are in `exit_analysis.csv` and `reference_candles.csv`.",
        f"6. Best temporal MFE capture: `{fmt_pct(float(best_test_row['mfe_capture_ratio'])) if best_test_row is not None else 'n/a'}`.",
        "7. Error location: compare `entry_analysis.csv` for early/late starts and `exit_analysis.csv` for giveback/delay; this run keeps those as descriptive diagnostics, not new rules.",
        "8. LONG/SHORT symmetry: shortlist gating rejected combinations with a complete side conflict; exact side returns are in `train_rankings.csv`.",
        f"9. TRAIN passed combinations: {len(shortlist)}.",
        f"10. Temporal transfer: {'at least one shortlisted combination was tested' if not test_metrics.empty else 'none, because shortlist is empty'}.",
        "11. Costs x2/x3: reported in `cost_stress.csv`; shortlist gate required x2 not to destroy train result.",
        "12. Concentration: top-1 profit share and without-top1 return are in `concentration_checks.csv`.",
        "13. Simple working system: allowed only if strong verdict criteria pass; otherwise keep as research-only evidence.",
        f"14. Ready for separate holdout test: {'yes, as a frozen candidate' if verdict == 'WORKABLE_EMA_CYCLE_FOUND' else 'no, current evidence is not strong enough'}.",
        "15. Next experiment: if evidence is weak, inspect whether failure is entry timing or exit retention before any holdout; do not open true holdout yet.",
        "",
        "## Top 3 Train Ranking Rows",
        "",
        md_table(train_top, ["combo_id", "passes_train_gate", "trades", "profit_factor", "total_return", "max_drawdown", "mfe_capture_ratio", "rank_score"]) if len(train_top) else "No train rows.",
        "",
        "## Artifacts",
        "",
        "- `artifacts/trades_all_combinations.csv`",
        "- `artifacts/combination_metrics.csv`",
        "- `artifacts/train_rankings.csv`",
        "- `artifacts/shortlist.csv`",
        "- `artifacts/temporal_test_metrics.csv`",
        "- `artifacts/temporal_test_trades.csv`",
        "- `artifacts/entry_analysis.csv`",
        "- `artifacts/exit_analysis.csv`",
        "- `artifacts/reference_candles.csv`",
        "- `artifacts/cost_stress.csv`",
        "- `artifacts/concentration_checks.csv`",
        "- `artifacts/equity_curves.png`",
        "- `artifacts/entry_comparison.png`",
        "- `artifacts/exit_comparison.png`",
        "- `artifacts/mfe_capture.png`",
        "- `artifacts/EMA_TRADING_CYCLE_REVIEW.pine`",
        "- `artifacts/EMA_TRADING_CYCLE_OVERVIEW.pdf`",
    ]
    (EXP / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
