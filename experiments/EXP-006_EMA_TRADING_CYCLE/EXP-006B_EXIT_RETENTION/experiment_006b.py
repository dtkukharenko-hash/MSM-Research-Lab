#!/usr/bin/env python3
"""EXP-006B: fixed ENTRY_A/STOP_A exit-retention diagnostics."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/EXP-006_EMA_TRADING_CYCLE/EXP-006B_EXIT_RETENTION"
OUT = EXP / "artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

DEV_START = pd.Timestamp("2023-07-01 00:00")
DEV_END = pd.Timestamp("2024-06-30 23:59")
VAL_START = pd.Timestamp("2024-07-01 00:00")
VAL_END = pd.Timestamp("2024-12-19 23:59")
REUSED_START = pd.Timestamp("2024-12-20 00:00")
REUSED_END = pd.Timestamp("2025-07-01 00:00")
TRUE_HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")

EXITS = ["EXIT_R0", "EXIT_R1", "EXIT_R2", "EXIT_R3", "EXIT_R4", "EXIT_R5"]
FEE = 0.001
SLIP = 0.0005
START_CAPITAL = 1000.0


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df[(df["dt"] >= DEV_START) & (df["dt"] <= REUSED_END)].copy().sort_values("dt").reset_index(drop=True)
    if df["dt"].max() >= TRUE_HOLDOUT_START:
        raise RuntimeError("True holdout entered EXP-006B dataframe.")
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
    df["ema27_slope_5"] = df["ema27"] - df["ema27"].shift(5)
    df["ema27_slope_10"] = df["ema27"] - df["ema27"].shift(10)
    df["ema200_slope_20"] = df["ema200"] - df["ema200"].shift(20)
    bull = (df["close"] > df["ema200"]) & (df["ema200_slope_20"] > 0) & (df["ema27"] > df["ema200"])
    bear = (df["close"] < df["ema200"]) & (df["ema200_slope_20"] < 0) & (df["ema27"] < df["ema200"])
    df["regime"] = np.where(bull, "BULL_REGIME", np.where(bear, "BEAR_REGIME", "TRANSITION_REGIME"))
    return df


def side(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def slipped(price: float, direction: str, is_entry: bool, cost_mult: float = 1.0) -> float:
    s = side(direction)
    sign = s if is_entry else -s
    return price * (1 + sign * SLIP * cost_mult)


def prep_long(df: pd.DataFrame, i: int) -> bool:
    r = df.loc[i]
    context = r["regime"] == "BULL_REGIME" or (r["regime"] == "TRANSITION_REGIME" and r["ema27"] > r["ema200"] and r["ema200_slope_20"] >= 0)
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
    context = r["regime"] == "BEAR_REGIME" or (r["regime"] == "TRANSITION_REGIME" and r["ema27"] < r["ema200"] and r["ema200_slope_20"] <= 0)
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


def entry_a_direction(df: pd.DataFrame, i: int) -> str | None:
    if i < 220 or i + 1 >= len(df):
        return None
    if prep_long(df, i) and df.loc[i - 1, "close"] <= df.loc[i - 1, "ema27"] and df.loc[i, "close"] > df.loc[i, "ema27"]:
        return "LONG"
    if prep_short(df, i) and df.loc[i - 1, "close"] >= df.loc[i - 1, "ema27"] and df.loc[i, "close"] < df.loc[i, "ema27"]:
        return "SHORT"
    return None


def stop_a(df: pd.DataFrame, signal_i: int, direction: str) -> float:
    w = df.loc[signal_i - 4 : signal_i]
    return float(w["low"].min() if direction == "LONG" else w["high"].max())


def regime_flip(df: pd.DataFrame, i: int, direction: str) -> bool:
    r = df.loc[i]
    if direction == "LONG":
        return bool(r["close"] < r["ema200"] and r["ema27"] < r["ema200"] and r["ema200_slope_20"] < 0)
    return bool(r["close"] > r["ema200"] and r["ema27"] > r["ema200"] and r["ema200_slope_20"] > 0)


def scope_for(t: pd.Timestamp) -> str | None:
    if DEV_START <= t <= DEV_END:
        return "DEVELOPMENT"
    if VAL_START <= t <= VAL_END:
        return "EXIT_VALIDATION"
    if REUSED_START <= t <= REUSED_END:
        return "REUSED_TEMPORAL_TEST"
    return None


def simulate_exit(df: pd.DataFrame, entry_i: int, signal_i: int, direction: str, exit_kind: str) -> dict:
    entry_raw = float(df.loc[entry_i, "open"])
    entry_price = slipped(entry_raw, direction, True)
    init_stop = stop_a(df, signal_i, direction)
    s = side(direction)
    atr = float(df.loc[signal_i, "atr14"])
    active_stop = init_stop
    best_atr = 0.0
    worst_atr = 0.0
    best_price = entry_price
    worst_price = entry_price
    best_i = entry_i
    worst_i = entry_i
    warning_i = None
    be_active = False
    exit_i = len(df) - 1
    exit_raw = float(df.loc[exit_i, "close"])
    reason = "END_OF_DATA"
    for i in range(entry_i, len(df) - 1):
        high = float(df.loc[i, "high"])
        low = float(df.loc[i, "low"])
        fav_price = high if direction == "LONG" else low
        adv_price = low if direction == "LONG" else high
        fav_atr = s * (fav_price - entry_price) / atr
        adv_atr = s * (adv_price - entry_price) / atr
        if fav_atr > best_atr:
            best_atr = fav_atr
            best_price = fav_price
            best_i = i
        if adv_atr < worst_atr:
            worst_atr = adv_atr
            worst_price = adv_price
            worst_i = i
        # Stop handling for every variant.
        if exit_kind == "EXIT_R1" and best_atr >= 1.0 and not be_active:
            be_active = True
            active_stop = entry_price + (2 * FEE + SLIP) * entry_price if direction == "LONG" else entry_price - (2 * FEE + SLIP) * entry_price
        stop_hit = (direction == "LONG" and low <= active_stop) or (direction == "SHORT" and high >= active_stop)
        if stop_hit:
            exit_i = i
            exit_raw = active_stop
            reason = "BREAK_EVEN_STOP" if be_active else "STOP_A"
            break
        close = float(df.loc[i, "close"])
        ema = float(df.loc[i, "ema27"])
        prev_close = float(df.loc[i - 1, "close"])
        prev_ema = float(df.loc[i - 1, "ema27"])
        below = close < ema if direction == "LONG" else close > ema
        prev_below = prev_close < prev_ema if direction == "LONG" else prev_close > prev_ema
        exit_next = False
        if regime_flip(df, i, direction):
            exit_next = True
            reason = "REGIME_FLIP"
        elif exit_kind == "EXIT_R0":
            exit_next = prev_below and below
            reason = "EMA27_TWO_CLOSES" if exit_next else reason
        elif exit_kind == "EXIT_R2" and best_atr >= 1.5:
            current_fav = s * (close - entry_price) / atr
            exit_next = best_atr - current_fav >= 1.0
            reason = "ATR_GIVEBACK" if exit_next else reason
        elif exit_kind in {"EXIT_R3", "EXIT_R5"} and best_atr >= 1.0:
            current_fav = s * (close - entry_price) / atr
            exit_next = current_fav <= 0.5 * best_atr
            reason = "MFE_50_GIVEBACK" if exit_next else reason
        if not exit_next and exit_kind in {"EXIT_R4", "EXIT_R5"}:
            if warning_i is None and below:
                warning_i = i
            elif warning_i is not None:
                warn_low = float(df.loc[warning_i, "low"])
                warn_high = float(df.loc[warning_i, "high"])
                cancel = close > ema if direction == "LONG" else close < ema
                confirm = below or (close < warn_low if direction == "LONG" else close > warn_high)
                if cancel:
                    warning_i = None
                elif confirm:
                    exit_next = True
                    reason = "EMA27_HYSTERESIS"
        if exit_next:
            exit_i = i + 1
            exit_raw = float(df.loc[exit_i, "open"])
            break
    exit_price = slipped(exit_raw, direction, False)
    gross = s * (exit_price - entry_price) / entry_price
    net = gross - 2 * FEE
    mfe_price_delta = abs(best_price - entry_price)
    realized_delta = s * (exit_price - entry_price)
    capture = np.nan if mfe_price_delta <= 0 else realized_delta / mfe_price_delta
    giveback = best_atr - (s * (exit_price - entry_price) / atr)
    return {
        "entry_price": entry_price,
        "stop_price": init_stop,
        "exit_time": df.loc[exit_i, "dt"],
        "exit_price": exit_price,
        "exit_reason": reason,
        "bars": int(exit_i - entry_i + 1),
        "gross_return": gross,
        "net_return": net,
        "mfe_atr": best_atr,
        "mae_atr": worst_atr,
        "mfe_price": best_price,
        "mae_price": worst_price,
        "mfe_time": df.loc[best_i, "dt"],
        "mae_time": df.loc[worst_i, "dt"],
        "mfe_capture": capture,
        "mfe_giveback_atr": giveback,
        "be_activated": be_active,
    }


def run_all(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    tid = 1
    for i in range(220, len(df) - 1):
        direction = entry_a_direction(df, i)
        if direction is None:
            continue
        entry_i = i + 1
        sc = scope_for(pd.Timestamp(df.loc[entry_i, "dt"]))
        if sc is None:
            continue
        for ex in EXITS:
            res = simulate_exit(df, entry_i, i, direction, ex)
            rows.append(
                {
                    "trade_key": f"EA_{tid:04d}",
                    "exit_variant": ex,
                    "scope": sc,
                    "signal_time": df.loc[i, "dt"],
                    "entry_time": df.loc[entry_i, "dt"],
                    "direction": direction,
                    "entry_regime": df.loc[i, "regime"],
                    **res,
                }
            )
        tid += 1
    return pd.DataFrame(rows)


def equity(rets: pd.Series) -> pd.Series:
    vals = [START_CAPITAL]
    for r in rets.fillna(0):
        vals.append(vals[-1] * (1 + float(r)))
    return pd.Series(vals[1:])


def max_dd(eq: pd.Series) -> float:
    if eq.empty:
        return 0.0
    return float((eq / eq.cummax() - 1).min())


def classify_failure(r: pd.Series) -> str:
    if r["mfe_atr"] < 1.0:
        return "NO_MOVEMENT"
    if r["mfe_atr"] >= 1.5 and r["net_return"] <= 0:
        return "GOOD_ENTRY_BAD_EXIT"
    if r["mfe_capture"] < 0:
        return "LATE_EXIT"
    if r["mfe_capture"] > 0.75 and r["mfe_atr"] >= 2.0 and r["bars"] <= 4:
        return "EARLY_EXIT"
    return "MIXED"


def phase(mfe_atr: float) -> str:
    if mfe_atr < 1.0:
        return "NO_MOVEMENT_MFE_LT_1_ATR"
    if mfe_atr < 2.0:
        return "WEAK_MOVEMENT_MFE_1_2_ATR"
    return "STRONG_MOVEMENT_MFE_GE_2_ATR"


def metrics(tr: pd.DataFrame, scope: str, exit_variant: str, cost_mult: float = 1.0) -> dict:
    if tr.empty:
        return {"scope": scope, "exit_variant": exit_variant, "cost_mult": cost_mult, "trades": 0}
    rets = tr["gross_return"] - 2 * FEE * cost_mult
    eq = equity(rets)
    wins = rets[rets > 0]
    losses = rets[rets < 0]
    pf = float(wins.sum() / abs(losses.sum())) if abs(losses.sum()) > 1e-12 else (999.0 if wins.sum() > 0 else 0.0)
    cap = tr["mfe_capture"].replace([np.inf, -np.inf], np.nan)
    fail = tr["failure_type"].value_counts(normalize=True)
    return {
        "scope": scope,
        "exit_variant": exit_variant,
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
        "avg_bars_held": float(tr["bars"].mean()),
        "median_bars_held": float(tr["bars"].median()),
        "avg_mfe_atr": float(tr["mfe_atr"].mean()),
        "avg_mae_atr": float(tr["mae_atr"].mean()),
        "realized_profit_to_mfe": float(cap.mean(skipna=True)),
        "median_mfe_capture": float(cap.median(skipna=True)),
        "mean_mfe_capture": float(cap.mean(skipna=True)),
        "giveback_from_mfe_atr": float(tr["mfe_giveback_atr"].mean()),
        "good_entry_bad_exit_share": float(fail.get("GOOD_ENTRY_BAD_EXIT", 0.0)),
        "early_exit_share": float(fail.get("EARLY_EXIT", 0.0)),
        "late_exit_share": float(fail.get("LATE_EXIT", 0.0)),
        "stop_exit_share": float(tr["exit_reason"].str.contains("STOP", na=False).mean()),
        "ema_exit_share": float(tr["exit_reason"].str.contains("EMA", na=False).mean()),
        "giveback_exit_share": float(tr["exit_reason"].str.contains("GIVEBACK", na=False).mean()),
        "break_even_exit_share": float((tr["exit_reason"] == "BREAK_EVEN_STOP").mean()),
        "long_total_return": float((1 + rets[tr["direction"] == "LONG"]).prod() - 1) if (tr["direction"] == "LONG").any() else 0.0,
        "short_total_return": float((1 + rets[tr["direction"] == "SHORT"]).prod() - 1) if (tr["direction"] == "SHORT").any() else 0.0,
    }


def concentration(tr: pd.DataFrame, scope: str, exit_variant: str) -> dict:
    if tr.empty:
        return {"scope": scope, "exit_variant": exit_variant, "top1_profit_share": np.nan, "without_top1_return": np.nan}
    wins = tr[tr["net_return"] > 0]
    top_share = float(wins["net_return"].max() / wins["net_return"].sum()) if len(wins) and wins["net_return"].sum() > 0 else 1.0
    without = tr.drop(index=tr["net_return"].idxmax()) if len(tr) else tr
    return {
        "scope": scope,
        "exit_variant": exit_variant,
        "top1_profit_share": top_share,
        "without_top1_return": float((1 + without["net_return"]).prod() - 1) if len(without) else 0.0,
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


def chart(series: list[tuple[str, list[float]]], path: Path) -> None:
    colors = [(0, 110, 180), (220, 80, 40), (60, 150, 80), (150, 80, 180), (40, 40, 40), (180, 150, 0)]
    r = Raster()
    vals = [x for _, xs in series for x in xs]
    ymin, ymax = (min(vals), max(vals)) if vals else (0, 1)
    if ymax == ymin:
        ymax = ymin + 1
    pad = 46
    r.line(pad, r.h - pad, r.w - 20, r.h - pad, (160, 160, 160), 1)
    r.line(pad, 20, pad, r.h - pad, (160, 160, 160), 1)
    for si, (_, xs) in enumerate(series):
        pts = []
        for i, val in enumerate(xs):
            x = pad + i / max(1, len(xs) - 1) * (r.w - pad - 20)
            y = r.h - pad - (val - ymin) / (ymax - ymin) * (r.h - pad - 20)
            pts.append((x, y))
        for a, b in zip(pts, pts[1:]):
            r.line(a[0], a[1], b[0], b[1], colors[si % len(colors)], 2)
    r.save(path)


def pdf_text(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:100]


def write_pdf_streams(pages: list[str], path: Path) -> None:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
    ]
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for i, content in enumerate(pages):
        stream = content.encode("latin-1", errors="replace")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {4 + i * 2} 0 R >>".encode())
        objs.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
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


def text_page(lines: list[str]) -> str:
    content = ["BT /F1 12 Tf 36 760 Td"]
    for line in lines[:55]:
        content.append(f"({pdf_text(line)}) Tj 0 -14 Td")
    content.append("ET")
    return "\n".join(content)


def trade_panel(df: pd.DataFrame, base: pd.Series, new: pd.Series, title: str, x: float, y: float, w: float, h: float) -> str:
    entry_t = pd.Timestamp(base["entry_time"])
    base_exit_t = pd.Timestamp(base["exit_time"])
    new_exit_t = pd.Timestamp(new["exit_time"])
    idx = {pd.Timestamp(t): i for i, t in zip(df.index, df["dt"])}
    entry_i = idx[entry_t]
    end_i = min(len(df) - 1, max(idx[base_exit_t], idx[new_exit_t]) + 12)
    start_i = max(0, entry_i - 12)
    win = df.loc[start_i:end_i]
    prices = list(win["close"].astype(float)) + list(win["ema27"].astype(float)) + list(win["ema200"].astype(float)) + [float(base["stop_price"]), float(base["mfe_price"]), float(new["exit_price"]), float(base["exit_price"])]
    ymin, ymax = min(prices), max(prices)
    if ymax == ymin:
        ymax = ymin + 1
    def px(i: int) -> float:
        return x + (i - start_i) / max(1, end_i - start_i) * w
    def py(v: float) -> float:
        return y + (v - ymin) / (ymax - ymin) * h
    cmds = [f"0.85 0.85 0.85 RG 0.5 w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S"]
    for col, color in [("close", "0 0 0"), ("ema27", "0 0.5 0.9"), ("ema200", "0.95 0.45 0")]:
        pts = [(px(i), py(float(v))) for i, v in zip(win.index, win[col])]
        cmds.append(f"{color} RG 0.7 w")
        for j, (xx, yy) in enumerate(pts):
            cmds.append(f"{xx:.2f} {yy:.2f} {'m' if j == 0 else 'l'}")
        cmds.append("S")
    ei = px(entry_i)
    bi = px(idx[base_exit_t])
    ni = px(idx[new_exit_t])
    stop_y = py(float(base["stop_price"]))
    mfe_y = py(float(base["mfe_price"]))
    cmds += [
        f"0 0.6 0 RG 1 w {ei:.2f} {y:.2f} m {ei:.2f} {y+h:.2f} l S",
        f"0.8 0 0 RG 1 w {bi:.2f} {y:.2f} m {bi:.2f} {y+h:.2f} l S",
        f"0.45 0 0.8 RG 1 w {ni:.2f} {y:.2f} m {ni:.2f} {y+h:.2f} l S",
        f"0.8 0 0 RG 0.5 w {x:.2f} {stop_y:.2f} m {x+w:.2f} {stop_y:.2f} l S",
        f"0 0.7 0 RG 0.5 w {x:.2f} {mfe_y:.2f} m {x+w:.2f} {mfe_y:.2f} l S",
        f"BT /F1 7 Tf {x:.2f} {y+h+8:.2f} Td ({pdf_text(title)}) Tj ET",
        f"BT /F1 7 Tf {x:.2f} {y-10:.2f} Td ({pdf_text(str(new['direction']))} cap={float(new['mfe_capture']):.2f} new={pdf_text(str(new['exit_reason']))}) Tj ET",
    ]
    return "\n".join(cmds)


def write_visual_pdf(df: pd.DataFrame, trades: pd.DataFrame, selected_ids: list[str]) -> None:
    chosen = selected_ids[0] if selected_ids else "EXIT_R0"
    base = trades[trades["exit_variant"] == "EXIT_R0"].set_index(["scope", "trade_key"])
    new = trades[trades["exit_variant"] == chosen].set_index(["scope", "trade_key"])
    joined = base.add_prefix("base_").join(new.add_prefix("new_"), how="inner").reset_index()
    def pick(mask, n=5):
        return joined[mask].head(n)
    preserved = pick((joined["base_net_return"] < joined["new_net_return"]) & (joined["new_net_return"] > 0), 5)
    too_early = pick((joined["new_bars"] < joined["base_bars"]) & (joined["new_net_return"] < joined["base_net_return"]), 5)
    no_move = pick(joined["new_mfe_atr"] < 1.0, 5)
    strong = pick(joined["new_mfe_atr"] >= 2.0, 5)
    pages = [text_page([
        "EXP-006B EMA Exit Retention Visual Audit",
        f"New exit shown: {chosen}",
        "Green vertical: entry. Red vertical: baseline EXIT_R0. Purple vertical: selected exit.",
        "Red dotted horizontal: STOP_A. Green dotted horizontal: MFE level.",
    ])]
    boxes = [(36, 560), (318, 560), (36, 360), (318, 360), (36, 160)]
    for title, subset in [("baseline gave back, new preserved", preserved), ("new too early", too_early), ("no movement", no_move), ("strong movement MFE>=2 ATR", strong)]:
        cmds = [f"BT /F1 12 Tf 36 760 Td ({pdf_text(title)}) Tj ET"]
        for (_, row), (x, y) in zip(subset.iterrows(), boxes):
            b = row.filter(like="base_").rename(lambda c: c.replace("base_", ""))
            n = row.filter(like="new_").rename(lambda c: c.replace("new_", ""))
            cmds.append(trade_panel(df, b, n, f"{row['scope']} {row['trade_key']}", x, y, 240, 140))
        pages.append("\n".join(cmds))
    write_pdf_streams(pages, OUT / "EMA_EXIT_RETENTION_OVERVIEW.pdf")


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


def write_pine(trades: pd.DataFrame, selected: list[str]) -> None:
    view = trades[(trades["scope"] != "DEVELOPMENT") & (trades["exit_variant"].isin(["EXIT_R0", *selected]))].head(100)
    def ts(t) -> str:
        p = pd.Timestamp(t)
        return f'timestamp("Etc/UTC", {p.year}, {p.month}, {p.day}, {p.hour}, {p.minute})'
    starts = ", ".join(ts(t) for t in view["entry_time"]) or 'timestamp("Etc/UTC", 2024, 7, 1, 0, 0)'
    exits = ", ".join(ts(t) for t in view["exit_time"]) or 'timestamp("Etc/UTC", 2024, 7, 1, 4, 0)'
    labels = ", ".join(f'"{x}"' for x in view["exit_variant"] + ":" + view["exit_reason"]) or '"NA"'
    stops = ", ".join(f"{float(x):.8f}" for x in view["stop_price"]) or "0.0"
    mfe = ", ".join(f"{float(x):.8f}" for x in view["mfe_price"]) or "0.0"
    text = f"""//@version=6
indicator("EXP-006B EMA Exit Retention Review", overlay=true, max_lines_count=500, max_labels_count=500)
showLabels = input.bool(true, "show labels")
showStops = input.bool(true, "show STOP_A")
showMfe = input.bool(true, "show MFE level")
ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
plot(ema27, "EMA27", color=color.aqua)
plot(ema200, "EMA200", color=color.orange)
slope20 = ema200 - ema200[20]
bull = close > ema200 and slope20 > 0 and ema27 > ema200
bear = close < ema200 and slope20 < 0 and ema27 < ema200
bgcolor(bull ? color.new(color.green, 92) : bear ? color.new(color.red, 92) : color.new(color.gray, 95))
var int[] starts = array.from({starts})
var int[] exits = array.from({exits})
var float[] stops = array.from({stops})
var float[] mfes = array.from({mfe})
var string[] labels = array.from({labels})
for i = 0 to array.size(starts) - 1
    int st = array.get(starts, i)
    int en = array.get(exits, i)
    float sp = array.get(stops, i)
    float mp = array.get(mfes, i)
    string lab = array.get(labels, i)
    if time == st
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.green, width=2)
        if showLabels
            label.new(time, high, "ENTRY_A " + lab, xloc=xloc.bar_time, style=label.style_label_down, color=color.green, textcolor=color.white, size=size.tiny)
    if time == en
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.red, width=2)
    if showStops and time >= st and time <= en
        line.new(st, sp, en, sp, xloc=xloc.bar_time, color=color.new(color.red, 40), style=line.style_dotted)
    if showMfe and time >= st and time <= en
        line.new(st, mp, en, mp, xloc=xloc.bar_time, color=color.new(color.lime, 45), style=line.style_dashed)
"""
    (OUT / "EMA_EXIT_RETENTION_REVIEW.pine").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    df = load_ohlc()
    trades = run_all(df)
    trades["failure_type"] = trades.apply(classify_failure, axis=1)
    trades["phase"] = trades["mfe_atr"].apply(phase)
    trades.to_csv(OUT / "all_exit_trades.csv", index=False)

    metric_rows = []
    stress_rows = []
    conc_rows = []
    for (scope, ex), g in trades.groupby(["scope", "exit_variant"]):
        metric_rows.append(metrics(g, scope, ex, 1.0))
        conc_rows.append(concentration(g, scope, ex))
        for cm in [1.0, 2.0, 3.0]:
            stress_rows.append(metrics(g, scope, ex, cm))
    met = pd.DataFrame(metric_rows)
    stress = pd.DataFrame(stress_rows)
    conc = pd.DataFrame(conc_rows)
    dev = met[met["scope"] == "DEVELOPMENT"].merge(conc[conc["scope"] == "DEVELOPMENT"], on=["scope", "exit_variant"], how="left")
    baseline = dev[dev["exit_variant"] == "EXIT_R0"].iloc[0]
    s2 = stress[(stress["scope"] == "DEVELOPMENT") & (stress["cost_mult"] == 2.0)][["exit_variant", "profit_factor", "total_return"]].rename(columns={"profit_factor": "pf_cost_x2", "total_return": "return_cost_x2"})
    s3 = stress[(stress["scope"] == "DEVELOPMENT") & (stress["cost_mult"] == 3.0)][["exit_variant", "profit_factor", "total_return"]].rename(columns={"profit_factor": "pf_cost_x3", "total_return": "return_cost_x3"})
    dev = dev.merge(s2, on="exit_variant", how="left").merge(s3, on="exit_variant", how="left")
    dev["passes_development"] = (
        (dev["trades"] >= 20)
        & (dev["profit_factor"] > 1.10)
        & (dev["max_drawdown"] >= -0.35)
        & (dev["median_mfe_capture"] > float(baseline["median_mfe_capture"]))
        & (dev["good_entry_bad_exit_share"] < float(baseline["good_entry_bad_exit_share"]))
        & (dev["pf_cost_x2"] > 0.75)
        & (dev["without_top1_return"] > 0)
        & ~((dev["long_total_return"] > 0) & (dev["short_total_return"] < -0.20))
        & ~((dev["short_total_return"] > 0) & (dev["long_total_return"] < -0.20))
    )
    dev["rank_score"] = (
        dev["profit_factor"].clip(0, 5)
        + dev["median_mfe_capture"].fillna(0).clip(-1, 2)
        - dev["good_entry_bad_exit_share"].fillna(1)
        + dev["without_top1_return"].fillna(-1).clip(-1, 3)
        + dev["pf_cost_x2"].fillna(0).clip(0, 3) / 3
    )
    selected = dev[(dev["exit_variant"] != "EXIT_R0") & (dev["passes_development"])].sort_values("rank_score", ascending=False).head(2)
    selected_ids = selected["exit_variant"].tolist()
    val = met[(met["scope"] == "EXIT_VALIDATION") & (met["exit_variant"].isin(["EXIT_R0", *selected_ids]))].merge(conc, on=["scope", "exit_variant"], how="left")
    reused = met[(met["scope"] == "REUSED_TEMPORAL_TEST") & (met["exit_variant"].isin(["EXIT_R0", *selected_ids]))].merge(conc, on=["scope", "exit_variant"], how="left")
    dev.to_csv(OUT / "development_metrics.csv", index=False)
    selected.to_csv(OUT / "selected_exits.csv", index=False)
    val.to_csv(OUT / "exit_validation_metrics.csv", index=False)
    reused.to_csv(OUT / "reused_temporal_metrics.csv", index=False)
    stress.to_csv(OUT / "cost_stress.csv", index=False)
    conc.to_csv(OUT / "concentration_checks.csv", index=False)

    cap_rows = []
    for (scope, ex), g in trades.groupby(["scope", "exit_variant"]):
        cap = g["mfe_capture"]
        cap_rows.append({
            "scope": scope, "exit_variant": ex, "capture_unknown": float(cap.isna().mean()),
            "capture_lt_0": float((cap < 0).mean()), "capture_0_25": float(((cap >= 0) & (cap < 0.25)).mean()),
            "capture_25_50": float(((cap >= 0.25) & (cap < 0.50)).mean()),
            "capture_50_75": float(((cap >= 0.50) & (cap < 0.75)).mean()),
            "capture_gt_75": float((cap >= 0.75).mean()),
        })
    pd.DataFrame(cap_rows).to_csv(OUT / "mfe_capture_distribution.csv", index=False)
    fail = trades.groupby(["scope", "exit_variant", "failure_type"]).size().reset_index(name="count")
    fail["share"] = fail["count"] / fail.groupby(["scope", "exit_variant"])["count"].transform("sum")
    fail.to_csv(OUT / "failure_type_comparison.csv", index=False)
    reasons = trades.groupby(["scope", "exit_variant", "exit_reason"]).size().reset_index(name="count")
    reasons["share"] = reasons["count"] / reasons.groupby(["scope", "exit_variant"])["count"].transform("sum")
    reasons.to_csv(OUT / "exit_reason_counts.csv", index=False)
    phase_df = trades.groupby(["scope", "exit_variant", "phase"]).agg(
        trades=("trade_key", "count"),
        avg_return=("net_return", "mean"),
        median_capture=("mfe_capture", "median"),
        good_entry_bad_exit_share=("failure_type", lambda s: float((s == "GOOD_ENTRY_BAD_EXIT").mean())),
    ).reset_index()
    phase_df.to_csv(OUT / "trade_phase_analysis.csv", index=False)

    chart([(ex, list(dev.sort_values("exit_variant").loc[dev["exit_variant"] == ex, ["median_mfe_capture", "mean_mfe_capture"]].iloc[0])) for ex in dev["exit_variant"]], OUT / "mfe_capture_comparison.png")
    chart([(ex, [float(dev[dev["exit_variant"] == ex]["giveback_from_mfe_atr"].iloc[0])]) for ex in dev["exit_variant"]], OUT / "giveback_comparison.png")
    chart([(ex, list(equity(trades[(trades["scope"] == "DEVELOPMENT") & (trades["exit_variant"] == ex)].sort_values("exit_time")["net_return"]))) for ex in EXITS], OUT / "equity_curves.png")
    write_pine(trades, selected_ids)
    write_visual_pdf(df, trades, selected_ids)
    write_report(dev, selected, val, reused, stress, conc)


def verdict(dev: pd.DataFrame, selected: pd.DataFrame, val: pd.DataFrame, stress: pd.DataFrame, conc: pd.DataFrame) -> str:
    if dev.empty:
        return "DATA_INSUFFICIENT"
    if selected.empty:
        base = dev[dev["exit_variant"] == "EXIT_R0"].iloc[0]
        if base["avg_mfe_atr"] < 1.0:
            return "ENTRY_EDGE_TOO_WEAK"
        return "NO_STABLE_EXIT_IMPROVEMENT"
    val_base = val[val["exit_variant"] == "EXIT_R0"].iloc[0] if (val["exit_variant"] == "EXIT_R0").any() else None
    best = val[val["exit_variant"].isin(selected["exit_variant"])].sort_values("profit_factor", ascending=False)
    if best.empty:
        return "PARTIAL_EXIT_IMPROVEMENT"
    b = best.iloc[0]
    sx2 = stress[(stress["scope"] == "EXIT_VALIDATION") & (stress["exit_variant"] == b["exit_variant"]) & (stress["cost_mult"] == 2.0)]
    c = conc[(conc["scope"] == "EXIT_VALIDATION") & (conc["exit_variant"] == b["exit_variant"])]
    strong = (
        b["profit_factor"] > 1.10
        and val_base is not None
        and b["median_mfe_capture"] > val_base["median_mfe_capture"]
        and b["good_entry_bad_exit_share"] < val_base["good_entry_bad_exit_share"]
        and b["max_drawdown"] >= val_base["max_drawdown"] - 0.03
        and not sx2.empty and float(sx2.iloc[0]["profit_factor"]) > 1.0
        and not c.empty and float(c.iloc[0]["without_top1_return"]) > 0
    )
    if strong:
        return "EXIT_RETENTION_FOUND"
    if b["early_exit_share"] > val_base["early_exit_share"] + 0.20:
        return "EARLY_EXIT_REPLACES_LATE_EXIT"
    return "PARTIAL_EXIT_IMPROVEMENT"


def write_report(dev: pd.DataFrame, selected: pd.DataFrame, val: pd.DataFrame, reused: pd.DataFrame, stress: pd.DataFrame, conc: pd.DataFrame) -> None:
    v = verdict(dev, selected, val, stress, conc)
    selected_ids = selected["exit_variant"].tolist()
    base_dev = dev[dev["exit_variant"] == "EXIT_R0"].iloc[0]
    lines = [
        "# EXP-006B — Exit Retention Report",
        "",
        f"Verdict: **{v}**",
        "",
        "## Boundary",
        "",
        "- Entry, initial STOP_A, EMA27/EMA200 regimes and costs are unchanged from EXP-006.",
        f"- Source: `{DATA}` read-only.",
        f"- True holdout after {TRUE_HOLDOUT_START} was not used.",
        "- REUSED TEMPORAL TEST is explicitly not independent OOS.",
        "",
        "## Development Metrics",
        "",
        md_table(dev, ["exit_variant", "trades", "profit_factor", "total_return", "max_drawdown", "median_mfe_capture", "mean_mfe_capture", "good_entry_bad_exit_share", "early_exit_share", "late_exit_share", "pf_cost_x2", "return_cost_x2", "without_top1_return", "passes_development"]),
        "",
        "## Selected Exits",
        "",
        md_table(selected, ["exit_variant", "profit_factor", "median_mfe_capture", "good_entry_bad_exit_share", "max_drawdown", "rank_score"]) if not selected.empty else "No exit variant passed the fixed DEVELOPMENT gate.",
        "",
        "## Exit Validation",
        "",
        md_table(val, ["exit_variant", "trades", "profit_factor", "total_return", "max_drawdown", "median_mfe_capture", "good_entry_bad_exit_share", "early_exit_share", "late_exit_share", "without_top1_return"]) if not val.empty else "No selected exits reached validation; baseline only may be absent.",
        "",
        "## Reused Temporal Test",
        "",
        md_table(reused, ["exit_variant", "trades", "profit_factor", "total_return", "max_drawdown", "median_mfe_capture", "good_entry_bad_exit_share", "without_top1_return"]) if not reused.empty else "Not run for selected exits because no exit passed validation gate.",
        "",
        "## Answers",
        "",
        "1. MFE capture was recalculated directionally as realized favorable price delta divided by max favorable price delta; UNKNOWN is used when MFE <= 0.",
        f"2. Baseline EXIT_R0 DEVELOPMENT median MFE capture: `{base_dev['median_mfe_capture']:.3f}`, GOOD_ENTRY_BAD_EXIT `{base_dev['good_entry_bad_exit_share']:.1%}`.",
        f"3. Best DEVELOPMENT retention candidates: `{', '.join(selected_ids) if selected_ids else 'none'}`.",
        "4. GOOD_ENTRY_BAD_EXIT changes are in `failure_type_comparison.csv` and metric tables.",
        "5. EARLY_EXIT share is reported per exit; no early-exit replacement is accepted without validation.",
        "6. Phase analysis for MFE <1, 1-2, >=2 ATR is in `trade_phase_analysis.csv`.",
        f"7. DEVELOPMENT passed variants: `{', '.join(selected_ids) if selected_ids else 'none'}`.",
        "8. EXIT VALIDATION was applied without rule changes to selected variants only.",
        "9. REUSED TEMPORAL TEST is a consistency check only, not independent OOS.",
        "10. Costs x2/x3 are in `cost_stress.csv`.",
        "11. Concentration checks are in `concentration_checks.csv`.",
        "12. LONG/SHORT totals are in `development_metrics.csv`.",
        f"13. Working retention mechanism: `{v}`.",
        "14. Do not prepare a true holdout unless the strong criteria are met; otherwise continue only from the diagnosed exit-retention result.",
        "",
        "## Artifacts",
        "",
        "- `artifacts/all_exit_trades.csv`",
        "- `artifacts/development_metrics.csv`",
        "- `artifacts/selected_exits.csv`",
        "- `artifacts/exit_validation_metrics.csv`",
        "- `artifacts/reused_temporal_metrics.csv`",
        "- `artifacts/mfe_capture_distribution.csv`",
        "- `artifacts/failure_type_comparison.csv`",
        "- `artifacts/exit_reason_counts.csv`",
        "- `artifacts/cost_stress.csv`",
        "- `artifacts/concentration_checks.csv`",
        "- `artifacts/trade_phase_analysis.csv`",
        "- `artifacts/mfe_capture_comparison.png`",
        "- `artifacts/giveback_comparison.png`",
        "- `artifacts/equity_curves.png`",
        "- `artifacts/EMA_EXIT_RETENTION_REVIEW.pine`",
        "- `artifacts/EMA_EXIT_RETENTION_OVERVIEW.pdf`",
    ]
    (EXP / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
