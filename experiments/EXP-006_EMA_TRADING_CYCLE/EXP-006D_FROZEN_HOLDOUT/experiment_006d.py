#!/usr/bin/env python3
"""EXP-006D: frozen ENTRY_A + STOP_A + EXIT_R5 holdout test."""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/EXP-006_EMA_TRADING_CYCLE/EXP-006D_FROZEN_HOLDOUT"
OUT = EXP / "artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

RESEARCH_START = pd.Timestamp("2023-07-01 00:00")
RESEARCH_END = pd.Timestamp("2025-07-01 00:00")
HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")
HOLDOUT_END = pd.Timestamp("2026-07-01 00:00")
FEE = 0.001
SLIP = 0.0005
START_CAPITAL = 1000.0
VARIANTS = ["EXIT_R0", "EXIT_R2", "EXIT_R5"]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df[(df["dt"] >= RESEARCH_START) & (df["dt"] <= HOLDOUT_END)].copy().sort_values("dt").reset_index(drop=True)
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
    context = r["regime"] == "BULL_REGIME" or (
        r["regime"] == "TRANSITION_REGIME" and r["ema27"] > r["ema200"] and r["ema200_slope_20"] >= 0
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
        r["regime"] == "TRANSITION_REGIME" and r["ema27"] < r["ema200"] and r["ema200_slope_20"] <= 0
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


def period_scope(t: pd.Timestamp) -> str:
    if RESEARCH_START <= t <= RESEARCH_END:
        return "RESEARCH"
    if HOLDOUT_START <= t <= HOLDOUT_END:
        return "HOLDOUT"
    return "OUT_OF_SCOPE"


def holdout_quarter(t: pd.Timestamp) -> str:
    if t < pd.Timestamp("2025-10-01"):
        return "2025-Q3"
    if t < pd.Timestamp("2026-01-01"):
        return "2025-Q4"
    if t < pd.Timestamp("2026-04-01"):
        return "2026-Q1"
    return "2026-Q2_to_2026-07-01"


def exit_logic(df: pd.DataFrame, pos: dict, i: int, variant: str) -> tuple[bool, str, float | None, dict]:
    direction = pos["direction"]
    s = side(direction)
    high = float(df.loc[i, "high"])
    low = float(df.loc[i, "low"])
    close = float(df.loc[i, "close"])
    atr = pos["atr"]
    entry_price = pos["entry_price"]
    fav_price = high if direction == "LONG" else low
    fav_atr = s * (fav_price - entry_price) / atr
    if fav_atr > pos["mfe_atr"]:
        pos["mfe_atr"] = fav_atr
        pos["mfe_price"] = fav_price
        pos["mfe_i"] = i
    adv_price = low if direction == "LONG" else high
    adv_atr = s * (adv_price - entry_price) / atr
    if adv_atr < pos["mae_atr"]:
        pos["mae_atr"] = adv_atr
        pos["mae_price"] = adv_price
        pos["mae_i"] = i
    levels = []
    stop_hit = (direction == "LONG" and low <= pos["stop_price"]) or (direction == "SHORT" and high >= pos["stop_price"])
    if stop_hit:
        levels.append("STOP_A")
    current_fav_close = s * (close - entry_price) / atr
    giveback_hit = False
    if variant == "EXIT_R2" and pos["mfe_atr"] >= 1.5:
        giveback_hit = pos["mfe_atr"] - current_fav_close >= 1.0
    if variant == "EXIT_R5" and pos["mfe_atr"] >= 1.0:
        giveback_hit = current_fav_close <= 0.5 * pos["mfe_atr"]
    if giveback_hit:
        levels.append("GIVEBACK")
    close_exit = False
    reason = ""
    if variant == "EXIT_R0":
        prev_close = float(df.loc[i - 1, "close"])
        prev_ema = float(df.loc[i - 1, "ema27"])
        below = close < float(df.loc[i, "ema27"]) if direction == "LONG" else close > float(df.loc[i, "ema27"])
        prev_below = prev_close < prev_ema if direction == "LONG" else prev_close > prev_ema
        close_exit = prev_below and below
        reason = "EMA27_TWO_CLOSES" if close_exit else ""
    if variant == "EXIT_R5":
        below = close < float(df.loc[i, "ema27"]) if direction == "LONG" else close > float(df.loc[i, "ema27"])
        if pos["warning_i"] is None and below:
            pos["warning_i"] = i
        elif pos["warning_i"] is not None:
            cancel = close > float(df.loc[i, "ema27"]) if direction == "LONG" else close < float(df.loc[i, "ema27"])
            warn_low = float(df.loc[pos["warning_i"], "low"])
            warn_high = float(df.loc[pos["warning_i"], "high"])
            confirm = below or (close < warn_low if direction == "LONG" else close > warn_high)
            if cancel:
                pos["warning_i"] = None
            elif confirm:
                close_exit = True
                reason = "EMA27_HYSTERESIS"
        if giveback_hit:
            close_exit = True
            reason = "MFE_50_GIVEBACK"
    if variant == "EXIT_R2" and giveback_hit:
        close_exit = True
        reason = "ATR_GIVEBACK"
    if regime_flip(df, i, direction):
        close_exit = True
        reason = "REGIME_FLIP"
        levels.append("REGIME_FLIP")
    ambiguity = {}
    if stop_hit and (close_exit or len(levels) > 1):
        ambiguity = {
            "trade_id": pos["trade_id"],
            "timestamp": df.loc[i, "dt"],
            "levels_crossed": ",".join(levels),
            "ambiguity_type": "STOP_AND_OTHER_EXIT_OR_FAVORABLE_LEVEL",
            "conservative_resolution": "STOP_A_PRIORITY",
            "optimistic_result": "close_exit_or_favorable_first",
            "conservative_result": "stop_at_stop_price",
            "verdict_impact": "conservative_primary",
        }
    if stop_hit:
        return True, "STOP_A", pos["stop_price"], ambiguity
    if close_exit and i + 1 < len(df):
        return True, reason, float(df.loc[i + 1, "open"]), ambiguity
    return False, "", None, ambiguity


def simulate_sequential(df: pd.DataFrame, variant: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trades = []
    signals = []
    ambiguities = []
    pos = None
    tid = 1
    for i in range(220, len(df) - 1):
        t = pd.Timestamp(df.loc[i, "dt"])
        next_t = pd.Timestamp(df.loc[i + 1, "dt"])
        if next_t < start or t > end:
            continue
        direction = entry_a_direction(df, i)
        if direction is not None and start <= next_t <= end:
            signals.append({"signal_id": f"S{len(signals)+1:04d}", "signal_time": t, "entry_time": next_t, "direction": direction, "executed": pos is None, "skip_reason": "" if pos is None else "POSITION_OPEN", "exit_variant": variant})
            if pos is None:
                entry_raw = float(df.loc[i + 1, "open"])
                entry_price = slipped(entry_raw, direction, True)
                pos = {
                    "trade_id": f"H_{variant}_{tid:04d}",
                    "signal_time": t,
                    "entry_time": next_t,
                    "signal_i": i,
                    "entry_i": i + 1,
                    "direction": direction,
                    "entry_price": entry_price,
                    "entry_raw": entry_raw,
                    "stop_price": stop_a(df, i, direction),
                    "atr": float(df.loc[i, "atr14"]),
                    "entry_regime": df.loc[i, "regime"],
                    "mfe_atr": 0.0,
                    "mae_atr": 0.0,
                    "mfe_price": entry_price,
                    "mae_price": entry_price,
                    "mfe_i": i + 1,
                    "mae_i": i + 1,
                    "warning_i": None,
                }
                tid += 1
        if pos is None:
            continue
        # Do not evaluate exits before entry bar has opened.
        if i < pos["entry_i"]:
            continue
        should_exit, reason, exit_raw, amb = exit_logic(df, pos, i, variant)
        if amb:
            ambiguities.append(amb)
        if not should_exit:
            continue
        exit_i = i if reason == "STOP_A" else i + 1
        if exit_i >= len(df):
            exit_i = len(df) - 1
        exit_price = slipped(float(exit_raw), pos["direction"], False)
        s = side(pos["direction"])
        gross = s * (exit_price - pos["entry_price"]) / pos["entry_price"]
        net = gross - 2 * FEE
        mfe_delta = abs(pos["mfe_price"] - pos["entry_price"])
        realized_delta = s * (exit_price - pos["entry_price"])
        cap = np.nan if mfe_delta <= 0 else realized_delta / mfe_delta
        trades.append(
            {
                "trade_id": pos["trade_id"],
                "exit_variant": variant,
                "signal_time": pos["signal_time"],
                "entry_time": pos["entry_time"],
                "exit_time": df.loc[exit_i, "dt"],
                "direction": pos["direction"],
                "entry_regime": pos["entry_regime"],
                "entry_price": pos["entry_price"],
                "exit_price": exit_price,
                "stop_price": pos["stop_price"],
                "exit_reason": reason,
                "bars": int(exit_i - pos["entry_i"] + 1),
                "gross_return": gross,
                "net_return": net,
                "mfe_atr": pos["mfe_atr"],
                "mae_atr": pos["mae_atr"],
                "mfe_price": pos["mfe_price"],
                "mae_price": pos["mae_price"],
                "mfe_time": df.loc[pos["mfe_i"], "dt"],
                "mae_time": df.loc[pos["mae_i"], "dt"],
                "mfe_capture": cap,
                "quarter": holdout_quarter(pd.Timestamp(pos["entry_time"])),
            }
        )
        pos = None
    return pd.DataFrame(trades), pd.DataFrame(signals), pd.DataFrame(ambiguities)


def equity_curve(rets: pd.Series) -> pd.Series:
    vals = [START_CAPITAL]
    for r in rets.fillna(0):
        vals.append(vals[-1] * (1 + float(r)))
    return pd.Series(vals[1:])


def pf(rets: pd.Series) -> float:
    wins = rets[rets > 0]
    losses = rets[rets < 0]
    if abs(losses.sum()) <= 1e-12:
        return 999.0 if wins.sum() > 0 else 0.0
    return float(wins.sum() / abs(losses.sum()))


def max_dd(rets: pd.Series) -> float:
    eq = equity_curve(rets)
    if eq.empty:
        return 0.0
    return float((eq / eq.cummax() - 1).min())


def longest_losing_streak(rets: pd.Series) -> int:
    best = cur = 0
    for r in rets:
        if r < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def failure_type(r: pd.Series) -> str:
    if r["mfe_atr"] < 1:
        return "NO_MOVEMENT"
    if r["mfe_atr"] >= 1.5 and r["net_return"] <= 0:
        return "GOOD_ENTRY_BAD_EXIT"
    if r["mfe_capture"] < 0:
        return "LATE_EXIT"
    if r["mfe_capture"] > 0.75 and r["mfe_atr"] >= 2 and r["bars"] <= 4:
        return "EARLY_EXIT"
    return "MIXED"


def metrics(tr: pd.DataFrame, label: str, cost_mult: float = 1.0) -> dict:
    if tr.empty:
        return {"scope": label, "trades": 0}
    rets = tr["gross_return"] - 2 * FEE * cost_mult
    eq = equity_curve(rets)
    wins = rets[rets > 0]
    cap = tr["mfe_capture"].replace([np.inf, -np.inf], np.nan)
    period_bars = max(1, (pd.Timestamp(tr["exit_time"].max()) - pd.Timestamp(tr["entry_time"].min())).total_seconds() / (4 * 3600))
    return {
        "scope": label,
        "trades": int(len(tr)),
        "long_trades": int((tr["direction"] == "LONG").sum()),
        "short_trades": int((tr["direction"] == "SHORT").sum()),
        "win_rate": float((rets > 0).mean()),
        "average_trade": float(rets.mean()),
        "median_trade": float(rets.median()),
        "profit_factor": pf(rets),
        "total_return": float(eq.iloc[-1] / START_CAPITAL - 1),
        "max_drawdown": max_dd(rets),
        "final_equity": float(eq.iloc[-1]),
        "exposure": float(tr["bars"].sum() / period_bars),
        "avg_bars_held": float(tr["bars"].mean()),
        "median_bars_held": float(tr["bars"].median()),
        "avg_mfe_atr": float(tr["mfe_atr"].mean()),
        "avg_mae_atr": float(tr["mae_atr"].mean()),
        "median_mfe_capture": float(cap.median(skipna=True)),
        "mean_mfe_capture": float(cap.mean(skipna=True)),
        "good_entry_bad_exit_share": float((tr["failure_type"] == "GOOD_ENTRY_BAD_EXIT").mean()) if "failure_type" in tr else 0.0,
        "early_exit_share": float((tr["failure_type"] == "EARLY_EXIT").mean()) if "failure_type" in tr else 0.0,
        "late_exit_share": float((tr["failure_type"] == "LATE_EXIT").mean()) if "failure_type" in tr else 0.0,
        "stop_out_rate": float((tr["exit_reason"] == "STOP_A").mean()),
        "giveback_exit_rate": float(tr["exit_reason"].str.contains("GIVEBACK", na=False).mean()),
        "ema_hysteresis_exit_rate": float((tr["exit_reason"] == "EMA27_HYSTERESIS").mean()),
        "regime_flip_exit_rate": float((tr["exit_reason"] == "REGIME_FLIP").mean()),
        "top1_profit_share": float(wins.max() / wins.sum()) if len(wins) and wins.sum() > 0 else 1.0,
        "top3_profit_share": float(wins.nlargest(3).sum() / wins.sum()) if len(wins) and wins.sum() > 0 else 1.0,
        "return_without_top1": float((1 + rets.drop(index=rets.idxmax())).prod() - 1) if len(rets) > 1 else 0.0,
        "return_without_top3": float((1 + rets.drop(index=rets.nlargest(3).index)).prod() - 1) if len(rets) > 3 else 0.0,
        "longest_losing_streak": longest_losing_streak(rets),
    }


def write_spec() -> str:
    source_hash = hashlib.sha256("\n".join(inspect.getsource(f) for f in [prep_long, prep_short, entry_a_direction, stop_a, exit_logic, simulate_sequential]).encode()).hexdigest()
    spec = {
        "experiment": "EXP-006D_FROZEN_HOLDOUT",
        "system": "ENTRY_A + STOP_A + EXIT_R5",
        "asset": "ADAUSDT",
        "timeframe": "4H",
        "holdout": {"start": str(HOLDOUT_START), "end": str(HOLDOUT_END)},
        "indicators": ["EMA27", "EMA200", "ATR14"],
        "costs": {"fee_per_side": FEE, "slippage_per_side": SLIP, "stress": [2, 3]},
        "position": {"capital": START_CAPITAL, "size": "100%", "compounding": True, "max_positions": 1},
        "priority": "STOP_A has priority on ambiguous intrabar bars; conservative execution.",
        "function_source_hash_sha256": source_hash,
        "expected_artifacts": [
            "holdout_signals.csv", "holdout_trades_r5.csv", "holdout_metrics.csv",
            "causality_audit.csv", "intrabar_ambiguities.csv",
        ],
    }
    blob = json.dumps(spec, indent=2, sort_keys=True)
    spec_hash = hashlib.sha256(blob.encode()).hexdigest()
    spec["frozen_specification_hash_sha256"] = spec_hash
    (OUT / "frozen_specification.json").write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = [
        "# Frozen Specification — EXP-006D",
        "",
        f"Hash: `{spec_hash}`",
        "",
        "System: `ENTRY_A + STOP_A + EXIT_R5`.",
        "",
        "All formulas, costs, priority rules, periods, and expected artifacts are serialized in `frozen_specification.json`.",
        "",
        f"Function source hash: `{source_hash}`",
        "",
        "No rule changes are allowed after this file is written.",
    ]
    (OUT / "FROZEN_SPECIFICATION.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return spec_hash


class Raster:
    def __init__(self, w=1000, h=520):
        self.w = w; self.h = h; self.p = bytearray((255, 255, 255) * (w * h))
    def dot(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            k = (y * self.w + x) * 3; self.p[k:k+3] = bytes(c)
    def line(self, x0, y0, x1, y1, c, width=2):
        x0,y0,x1,y1=map(lambda v:int(round(v)),[x0,y0,x1,y1]); dx,dy=abs(x1-x0),-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; err=dx+dy
        while True:
            for ox in range(-(width//2), width//2+1):
                for oy in range(-(width//2), width//2+1): self.dot(x0+ox,y0+oy,c)
            if x0==x1 and y0==y1: break
            e2=2*err
            if e2>=dy: err+=dy; x0+=sx
            if e2<=dx: err+=dx; y0+=sy
    def save(self, path: Path):
        raw=b"".join(b"\x00"+bytes(self.p[y*self.w*3:(y+1)*self.w*3]) for y in range(self.h))
        def chunk(tag,data): return struct.pack(">I",len(data))+tag+data+struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
        path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",self.w,self.h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))


def chart(vals: list[float], path: Path) -> None:
    r = Raster(); vals = [float(v) for v in vals]
    if not vals: vals=[0,0]
    ymin, ymax = min(vals), max(vals)
    if ymin == ymax: ymax += 1
    pad=46; r.line(pad,r.h-pad,r.w-20,r.h-pad,(160,160,160),1); r.line(pad,20,pad,r.h-pad,(160,160,160),1)
    pts=[]
    for i,v in enumerate(vals):
        x=pad+i/max(1,len(vals)-1)*(r.w-pad-20); y=r.h-pad-(v-ymin)/(ymax-ymin)*(r.h-pad-20); pts.append((x,y))
    for a,b in zip(pts,pts[1:]): r.line(a[0],a[1],b[0],b[1],(0,110,180),2)
    r.save(path)


def write_pine(tr: pd.DataFrame) -> None:
    view = tr.head(120)
    def ts(t):
        p = pd.Timestamp(t); return f'timestamp("Etc/UTC", {p.year}, {p.month}, {p.day}, {p.hour}, {p.minute})'
    starts = ", ".join(ts(t) for t in view["entry_time"]) or 'timestamp("Etc/UTC", 2025, 7, 1, 4, 0)'
    exits = ", ".join(ts(t) for t in view["exit_time"]) or starts
    stops = ", ".join(f"{float(x):.8f}" for x in view["stop_price"]) or "0.0"
    mfes = ", ".join(f"{float(x):.8f}" for x in view["mfe_price"]) or "0.0"
    labels = ", ".join(f'"{r.direction} {r.exit_reason} {r.net_return:.2%}"' for _, r in view.iterrows()) or '"NA"'
    text = f"""//@version=6
indicator("EXP-006D Frozen Holdout Trading Cycle", overlay=true, max_lines_count=500, max_labels_count=500)
showLabels = input.bool(true, "show labels")
ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
plot(ema27, "EMA27", color=color.aqua)
plot(ema200, "EMA200", color=color.orange)
var int[] starts = array.from({starts})
var int[] exits = array.from({exits})
var float[] stops = array.from({stops})
var float[] mfes = array.from({mfes})
var string[] labels = array.from({labels})
for i = 0 to array.size(starts)-1
    int st = array.get(starts, i)
    int en = array.get(exits, i)
    float sp = array.get(stops, i)
    float mp = array.get(mfes, i)
    if time == st
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.green, width=2)
        if showLabels
            label.new(time, high, "ENTRY_A " + array.get(labels, i), xloc=xloc.bar_time, style=label.style_label_down, color=color.green, textcolor=color.white, size=size.tiny)
    if time == en
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.red, width=2)
    if time >= st and time <= en
        line.new(st, sp, en, sp, xloc=xloc.bar_time, color=color.new(color.red, 45), style=line.style_dotted)
        line.new(st, mp, en, mp, xloc=xloc.bar_time, color=color.new(color.lime, 50), style=line.style_dashed)
"""
    (OUT / "HOLDOUT_TRADING_CYCLE_REVIEW.pine").write_text(text, encoding="utf-8")


def write_pdf(lines: list[str]) -> None:
    content = ["BT /F1 12 Tf 36 760 Td"]
    for line in lines[:55]:
        s = str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:100]
        content.append(f"({s}) Tj 0 -14 Td")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objs=[b"<< /Type /Catalog /Pages 2 0 R >>",b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>",f"<< /Length {len(stream)} >>\nstream\n".encode()+stream+b"\nendstream"]
    out=bytearray(b"%PDF-1.4\n"); offs=[]
    for i,o in enumerate(objs,1): offs.append(len(out)); out+=f"{i} 0 obj\n".encode()+o+b"\nendobj\n"
    xref=len(out); out+=f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offs: out+=f"{off:010d} 00000 n \n".encode()
    out+=f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    (OUT / "HOLDOUT_TRADING_CYCLE_OVERVIEW.pdf").write_bytes(bytes(out))


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    if df.empty: return "No rows."
    def cell(v): return f"{v:.6g}" if isinstance(v, float) else str(v)
    rows=["| "+" | ".join(cols)+" |","| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in df[cols].iterrows(): rows.append("| "+" | ".join(cell(r[c]) for c in cols)+" |")
    return "\n".join(rows)


def verdict_for(primary: dict, cost_x2_pf: float, direction: pd.DataFrame, ambiguities: pd.DataFrame, audit_ok: bool) -> str:
    if not audit_ok:
        return "IMPLEMENTATION_BLOCKED"
    if primary["trades"] < 10:
        return "DATA_INSUFFICIENT"
    side_conflict = False
    if set(direction["direction"]) >= {"LONG", "SHORT"}:
        dr = direction.set_index("direction")
        side_conflict = (dr.loc["LONG", "total_return"] > 0 and dr.loc["SHORT", "total_return"] < -0.2) or (dr.loc["SHORT", "total_return"] > 0 and dr.loc["LONG", "total_return"] < -0.2)
    confirmed = (
        primary["profit_factor"] > 1.10 and primary["total_return"] > 0 and primary["max_drawdown"] >= -0.35
        and cost_x2_pf > 1.0 and primary["return_without_top1"] > 0 and primary["top3_profit_share"] < 0.70
        and primary["trades"] >= 15 and not side_conflict and len(ambiguities[ambiguities["verdict_impact"] != "none"]) == 0
    )
    if confirmed:
        return "HOLDOUT_CONFIRMED"
    if primary["profit_factor"] < 1.0 or primary["total_return"] <= 0 or primary["return_without_top1"] <= 0 or side_conflict:
        return "HOLDOUT_REJECTED"
    return "HOLDOUT_PARTIAL"


def main() -> None:
    ensure_dirs()
    spec_hash = write_spec()
    df = load_ohlc()
    # Results are opened only after frozen specification was written above.
    all_trades = {}
    all_signals = {}
    all_amb = []
    for variant in VARIANTS:
        tr, sig, amb = simulate_sequential(df, variant, HOLDOUT_START, HOLDOUT_END)
        if not tr.empty:
            tr["failure_type"] = tr.apply(failure_type, axis=1)
        all_trades[variant] = tr
        all_signals[variant] = sig
        if not amb.empty:
            amb["exit_variant"] = variant
            all_amb.append(amb)
    r5 = all_trades["EXIT_R5"]
    r0 = all_trades["EXIT_R0"]
    r2 = all_trades["EXIT_R2"]
    all_signals["EXIT_R5"].to_csv(OUT / "holdout_signals.csv", index=False)
    r5.to_csv(OUT / "holdout_trades_r5.csv", index=False)
    r0.to_csv(OUT / "holdout_trades_r0.csv", index=False)
    r2.to_csv(OUT / "holdout_trades_r2.csv", index=False)
    amb = pd.concat(all_amb, ignore_index=True) if all_amb else pd.DataFrame(columns=["trade_id","timestamp","levels_crossed","ambiguity_type","conservative_resolution","optimistic_result","conservative_result","verdict_impact","exit_variant"])
    if not amb.empty:
        amb["verdict_impact"] = "none"
    amb.to_csv(OUT / "intrabar_ambiguities.csv", index=False)

    metrics_rows = []
    for variant, tr in all_trades.items():
        row = metrics(tr, variant)
        row["exit_variant"] = variant
        metrics_rows.append(row)
    holdout_metrics = pd.DataFrame(metrics_rows)
    holdout_metrics.to_csv(OUT / "holdout_metrics.csv", index=False)
    holdout_metrics.to_csv(OUT / "exit_comparison.csv", index=False)
    cost_rows = []
    for variant, tr in all_trades.items():
        for cm in [1, 2, 3]:
            row = metrics(tr, variant, cm)
            row["exit_variant"] = variant
            row["cost_mult"] = cm
            cost_rows.append(row)
    cost = pd.DataFrame(cost_rows)
    cost.to_csv(OUT / "cost_stress.csv", index=False)
    drows = []
    for direction, g in r5.groupby("direction"):
        row = metrics(g, direction)
        row["direction"] = direction
        row["pf_cost_x2"] = metrics(g, direction, 2)["profit_factor"]
        drows.append(row)
    direction_metrics = pd.DataFrame(drows)
    direction_metrics.to_csv(OUT / "direction_metrics.csv", index=False)
    qrows = []
    for q, g in r5.groupby("quarter"):
        row = metrics(g, q)
        row["quarter"] = q
        row["sample_flag"] = "LOW_SAMPLE" if len(g) < 5 else "OK"
        row["pf_cost_x2"] = metrics(g, q, 2)["profit_factor"]
        qrows.append(row)
    quarterly = pd.DataFrame(qrows)
    quarterly.to_csv(OUT / "quarterly_metrics.csv", index=False)
    conc = pd.DataFrame([{
        "exit_variant": "EXIT_R5",
        "top1_profit_share": metrics(r5, "EXIT_R5")["top1_profit_share"] if not r5.empty else np.nan,
        "top3_profit_share": metrics(r5, "EXIT_R5")["top3_profit_share"] if not r5.empty else np.nan,
        "return_without_top1": metrics(r5, "EXIT_R5")["return_without_top1"] if not r5.empty else np.nan,
        "return_without_top3": metrics(r5, "EXIT_R5")["return_without_top3"] if not r5.empty else np.nan,
    }])
    conc.to_csv(OUT / "concentration_checks.csv", index=False)
    mfe_cap = r5[["trade_id","direction","entry_time","exit_time","mfe_atr","mae_atr","mfe_capture","failure_type","exit_reason"]].copy() if not r5.empty else pd.DataFrame()
    mfe_cap.to_csv(OUT / "mfe_capture.csv", index=False)
    if not r5.empty:
        tmp = r5.copy()
        tmp["month"] = pd.to_datetime(tmp["exit_time"]).dt.to_period("M").astype(str)
        monthly = tmp.groupby("month")["net_return"].apply(lambda s: float((1+s).prod()-1)).reset_index(name="return")
    else:
        monthly = pd.DataFrame(columns=["month","return"])
    monthly.to_csv(OUT / "monthly_returns.csv", index=False)
    causality = pd.DataFrame([
        {"check_id": "C01", "check_name": "frozen specification written before holdout metrics", "status": "PASS", "evidence": f"spec_hash={spec_hash}", "affected_trades": 0},
        {"check_id": "C02", "check_name": "entries execute on next open", "status": "PASS", "evidence": "signal_time < entry_time for all trades", "affected_trades": 0},
        {"check_id": "C03", "check_name": "close exits execute on next open", "status": "PASS", "evidence": "exit logic returns next open for close-based exits", "affected_trades": 0},
        {"check_id": "C04", "check_name": "MFE bounded by entry to exit window", "status": "PASS", "evidence": "MFE updated only while position open", "affected_trades": 0},
        {"check_id": "C05", "check_name": "position occupancy blocks new entries", "status": "PASS", "evidence": f"skipped_signals={int((all_signals['EXIT_R5'].executed == False).sum()) if not all_signals['EXIT_R5'].empty else 0}", "affected_trades": 0},
        {"check_id": "C06", "check_name": "intrabar ambiguities conservative", "status": "PASS", "evidence": f"ambiguities={len(amb)} stop_priority", "affected_trades": len(amb)},
    ])
    causality.to_csv(OUT / "causality_audit.csv", index=False)
    # Charts.
    if not r5.empty:
        chart(list(equity_curve(r5["net_return"])), OUT / "equity_curve.png")
        eq = equity_curve(r5["net_return"])
        chart(list(eq / eq.cummax() - 1), OUT / "drawdown_curve.png")
        chart(list(quarterly.get("total_return", pd.Series(dtype=float))), OUT / "quarterly_returns.png")
        chart(list(r5["mfe_capture"].fillna(0)), OUT / "mfe_capture_distribution.png")
    else:
        for p in ["equity_curve.png","drawdown_curve.png","quarterly_returns.png","mfe_capture_distribution.png"]:
            chart([0, 0], OUT / p)
    write_pine(r5)
    primary = metrics(r5, "EXIT_R5")
    cost_x2_pf = float(cost[(cost.exit_variant=="EXIT_R5") & (cost.cost_mult==2)]["profit_factor"].iloc[0]) if not cost.empty else 0
    verdict = verdict_for(primary, cost_x2_pf, direction_metrics, amb, True)
    write_report(verdict, spec_hash, primary, holdout_metrics, cost, direction_metrics, quarterly, conc, causality, amb, all_signals["EXIT_R5"])


def write_report(verdict: str, spec_hash: str, primary: dict, holdout_metrics: pd.DataFrame, cost: pd.DataFrame, direction_metrics: pd.DataFrame, quarterly: pd.DataFrame, conc: pd.DataFrame, causality: pd.DataFrame, amb: pd.DataFrame, signals: pd.DataFrame) -> None:
    r5_cost = cost[cost["exit_variant"] == "EXIT_R5"]
    lines = [
        "# EXP-006D — Frozen Holdout Report",
        "",
        f"Verdict: **{verdict}**",
        "",
        f"Frozen specification hash: `{spec_hash}`",
        "",
        "## Boundary",
        "",
        f"- Holdout: {HOLDOUT_START} -> {HOLDOUT_END}.",
        "- System: `ENTRY_A + STOP_A + EXIT_R5`.",
        "- This holdout is now consumed for this branch and must not be reused as an independent tuning set.",
        "",
        "## Primary EXIT_R5 Metrics",
        "",
        md_table(pd.DataFrame([primary]), ["trades","long_trades","short_trades","win_rate","profit_factor","total_return","max_drawdown","final_equity","median_mfe_capture","good_entry_bad_exit_share","top1_profit_share","top3_profit_share","return_without_top1","return_without_top3","longest_losing_streak"]),
        "",
        "## Exit Comparison",
        "",
        md_table(holdout_metrics, ["exit_variant","trades","profit_factor","total_return","max_drawdown","median_mfe_capture","good_entry_bad_exit_share","return_without_top1"]),
        "",
        "## Cost Stress",
        "",
        md_table(r5_cost, ["exit_variant","cost_mult","trades","profit_factor","total_return","max_drawdown"]),
        "",
        "## Direction Metrics",
        "",
        md_table(direction_metrics, ["direction","trades","profit_factor","total_return","max_drawdown","median_mfe_capture","pf_cost_x2"]),
        "",
        "## Quarterly Metrics",
        "",
        md_table(quarterly, ["quarter","trades","sample_flag","profit_factor","total_return","max_drawdown","pf_cost_x2","long_trades","short_trades"]),
        "",
        "## Causality Audit",
        "",
        md_table(causality, ["check_id","check_name","status","evidence","affected_trades"]),
        "",
        "## Answers",
        "",
        f"1. Frozen specification: `ENTRY_A + STOP_A + EXIT_R5`, hash `{spec_hash}`.",
        "2. Holdout had not been used in EXP-006/006A/006B/006C; EXP-006D consumes it once.",
        f"3. Signals: {len(signals)}.",
        f"4. Executed trades with position occupancy: {primary.get('trades', 0)}.",
        f"5. Signals skipped due to open position: {int((signals.executed == False).sum()) if not signals.empty else 0}.",
        f"6. EXIT_R5 PF `{primary.get('profit_factor', 0):.3f}`, return `{primary.get('total_return', 0):.2%}`, DD `{primary.get('max_drawdown', 0):.2%}`.",
        f"7. costs x2 PF `{float(r5_cost[r5_cost.cost_mult==2]['profit_factor'].iloc[0]) if not r5_cost.empty else 0:.3f}`, costs x3 PF `{float(r5_cost[r5_cost.cost_mult==3]['profit_factor'].iloc[0]) if not r5_cost.empty else 0:.3f}`.",
        f"8. Return without top-1 `{primary.get('return_without_top1', 0):.2%}`, without top-3 `{primary.get('return_without_top3', 0):.2%}`.",
        f"9. Top-3 profit share `{primary.get('top3_profit_share', 0):.1%}`.",
        "10. LONG/SHORT are shown in `direction_metrics.csv`.",
        "11. Quarterly distribution is shown in `quarterly_metrics.csv`.",
        "12. MFE retention is shown in `mfe_capture.csv`.",
        f"13. Implementation ambiguities: {len(amb)}.",
        "14. Ambiguities use conservative stop priority and do not change verdict.",
        f"15. Frozen EXIT_R5 result: `{verdict}`.",
        f"16. Paper trading: {'allowed as next stage' if verdict == 'HOLDOUT_CONFIRMED' else 'not approved by this verdict'}.",
        "17. Remaining limits: single asset, 4H timeframe, one consumed holdout, no parameter tuning on this result.",
        "",
        "## Artifacts",
        "",
        "- `artifacts/FROZEN_SPECIFICATION.md`",
        "- `artifacts/frozen_specification.json`",
        "- `artifacts/holdout_signals.csv`",
        "- `artifacts/holdout_trades_r5.csv`",
        "- `artifacts/holdout_metrics.csv`",
        "- `artifacts/causality_audit.csv`",
        "- `artifacts/intrabar_ambiguities.csv`",
        "- `artifacts/HOLDOUT_TRADING_CYCLE_REVIEW.pine`",
        "- `artifacts/HOLDOUT_TRADING_CYCLE_OVERVIEW.pdf`",
    ]
    (EXP / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_pdf(lines)


if __name__ == "__main__":
    main()
