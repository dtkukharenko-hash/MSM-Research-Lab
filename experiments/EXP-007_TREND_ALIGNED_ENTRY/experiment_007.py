#!/usr/bin/env python3
"""EXP-007: trend-aligned EMA entry research on ADAUSDT 4H 2023-2024 only."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-007_TREND_ALIGNED_ENTRY"
OUT = EXP / "artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")

DEVELOPMENT_START = pd.Timestamp("2023-07-01 00:00")
DEVELOPMENT_END = pd.Timestamp("2024-06-30 23:59")
VALIDATION_START = pd.Timestamp("2024-07-01 00:00")
VALIDATION_END = pd.Timestamp("2024-12-31 23:59")
FORBIDDEN_HOLDOUT_START = pd.Timestamp("2025-07-01 00:00")

ENTRIES = ["ENTRY_A", "ENTRY_T1", "ENTRY_T2", "ENTRY_T3", "ENTRY_T4"]
FEE = 0.001
SLIP = 0.0005
START_CAPITAL = 1000.0


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df.sort_values("dt").reset_index(drop=True)
    df = df[(df["dt"] >= DEVELOPMENT_START) & (df["dt"] <= VALIDATION_END)].copy().reset_index(drop=True)
    if df["dt"].max() >= FORBIDDEN_HOLDOUT_START:
        raise RuntimeError("Forbidden holdout entered EXP-007 data frame.")
    prev = df["close"].shift(1).fillna(df["close"])
    df["tr"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(float),
            (df["high"] - prev).abs().to_numpy(float),
            (df["low"] - prev).abs().to_numpy(float),
        ]
    )
    df["body"] = (df["close"] - df["open"]).abs()
    df["bar_dir"] = np.sign(df["close"] - df["open"]).replace(0, np.nan).ffill().fillna(0)
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["atr14"] = df["tr"].rolling(14, min_periods=1).mean()
    df["ema27_slope_10"] = df["ema27"] - df["ema27"].shift(10)
    df["ema200_slope_20"] = df["ema200"] - df["ema200"].shift(20)
    ema_diff = df["ema27"] - df["ema200"]
    cross = np.sign(ema_diff).replace(0, np.nan).ffill().fillna(0).diff().abs() > 0
    df["crossings_last30"] = cross.rolling(30, min_periods=1).sum()
    price_side = np.sign(df["close"] - df["ema27"]).replace(0, np.nan).ffill().fillna(0)
    df["ema27_cross_last10"] = (price_side.diff().abs() > 0).rolling(10, min_periods=1).sum()
    df["dir_changes_last10"] = (df["bar_dir"].diff().abs() > 0).rolling(10, min_periods=1).sum()
    df["range20"] = df["high"].rolling(20, min_periods=1).max() - df["low"].rolling(20, min_periods=1).min()
    df["median_body10"] = df["body"].rolling(10, min_periods=1).median().shift(1)
    df["ema_distance_atr"] = (df["ema27"] - df["ema200"]).abs() / df["atr14"].replace(0, np.nan)
    lo = np.minimum(df["ema27"], df["ema200"])
    hi = np.maximum(df["ema27"], df["ema200"])
    df["price_between_emas"] = (df["close"] > lo) & (df["close"] < hi)
    long_ctx = (
        (df["ema27"] > df["ema200"])
        & (df["ema200_slope_20"] > 0)
        & (df["close"] > df["ema200"])
        & (df["ema_distance_atr"] >= 0.25)
        & (df["crossings_last30"] <= 1)
        & (~df["price_between_emas"])
    )
    short_ctx = (
        (df["ema27"] < df["ema200"])
        & (df["ema200_slope_20"] < 0)
        & (df["close"] < df["ema200"])
        & (df["ema_distance_atr"] >= 0.25)
        & (df["crossings_last30"] <= 1)
        & (~df["price_between_emas"])
    )
    df["context"] = np.where(long_ctx, "LONG_CONTEXT", np.where(short_ctx, "SHORT_CONTEXT", "BLOCK_CONTEXT"))
    return df


def side(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def slipped(price: float, direction: str, is_entry: bool, cost_mult: float = 1.0) -> float:
    s = side(direction)
    sign = s if is_entry else -s
    return price * (1 + sign * SLIP * cost_mult)


def is_impulse_bar(df: pd.DataFrame, i: int) -> bool:
    med = float(df.loc[i, "median_body10"])
    if not math.isfinite(med) or med <= 0:
        return False
    return bool(df.loc[i, "body"] > 1.5 * med)


def context_allows(df: pd.DataFrame, i: int, direction: str) -> bool:
    return (direction == "LONG" and df.loc[i, "context"] == "LONG_CONTEXT") or (
        direction == "SHORT" and df.loc[i, "context"] == "SHORT_CONTEXT"
    )


def chop_block(df: pd.DataFrame, i: int) -> tuple[bool, str]:
    if df.loc[i, "crossings_last30"] > 1:
        return True, "EMA_CROSSINGS_LAST30"
    s1 = float(df.loc[i, "ema27_slope_10"])
    s2 = float(df.loc[i, "ema200_slope_20"])
    if math.isfinite(s1) and math.isfinite(s2) and s1 * s2 < 0:
        return True, "EMA_SLOPES_DIFFER"
    if float(df.loc[i, "range20"]) < 2 * float(df.loc[i, "atr14"]):
        return True, "RANGE20_LT_2ATR"
    if df.loc[i, "dir_changes_last10"] >= 6:
        return True, "DIRECTION_CHANGES_LAST10"
    if df.loc[i, "ema27_cross_last10"] >= 5:
        return True, "PRICE_EMA27_CROSSES_LAST10"
    return False, ""


def late_entry_block(df: pd.DataFrame, i: int, direction: str) -> tuple[bool, str]:
    s = side(direction)
    atr = float(df.loc[i, "atr14"])
    if atr <= 0 or not math.isfinite(atr):
        return True, "NO_ATR"
    move5 = s * (float(df.loc[i, "close"]) - float(df.loc[max(0, i - 5), "close"]))
    dist_ema = abs(float(df.loc[i, "close"]) - float(df.loc[i, "ema27"]))
    last3 = df.loc[i - 2 : i] if i >= 2 else df.loc[:i]
    last3_all = len(last3) == 3 and all(np.sign((last3["close"] - last3["open"]).to_numpy(float)) == s)
    last3_move = s * (float(df.loc[i, "close"]) - float(df.loc[i - 2, "open"])) if i >= 2 else 0
    if move5 > 2 * atr:
        return True, "MOVE5_GT_2ATR"
    if dist_ema > 1.5 * atr:
        return True, "DIST_EMA27_GT_1_5ATR"
    if is_impulse_bar(df, i):
        return True, "IMPULSE_BAR"
    if last3_all and last3_move > 1.5 * atr:
        return True, "THREE_BAR_EXTENSION"
    return False, ""


def baseline_entry_a(df: pd.DataFrame, i: int) -> str | None:
    if i < 220 or i + 1 >= len(df):
        return None
    r = df.loc[i]
    last10 = df.loc[i - 9 : i]
    long_ctx = r["context"] == "LONG_CONTEXT" or (r["ema27"] > r["ema200"] and r["ema200_slope_20"] >= 0)
    short_ctx = r["context"] == "SHORT_CONTEXT" or (r["ema27"] < r["ema200"] and r["ema200_slope_20"] <= 0)
    prep_long = (
        long_ctx
        and (last10["low"] < last10["ema27"]).any()
        and r["close"] > r["ema27"]
        and r["ema27_slope_10"] >= 0
        and r["close"] - r["ema27"] <= 2 * r["atr14"]
    )
    prep_short = (
        short_ctx
        and (last10["high"] > last10["ema27"]).any()
        and r["close"] < r["ema27"]
        and r["ema27_slope_10"] <= 0
        and r["ema27"] - r["close"] <= 2 * r["atr14"]
    )
    if prep_long and df.loc[i - 1, "close"] <= df.loc[i - 1, "ema27"] and r["close"] > r["ema27"]:
        return "LONG"
    if prep_short and df.loc[i - 1, "close"] >= df.loc[i - 1, "ema27"] and r["close"] < r["ema27"]:
        return "SHORT"
    return None


def entry_t1(df: pd.DataFrame, i: int) -> str | None:
    if i < 220 or i + 1 >= len(df):
        return None
    r = df.loc[i]
    last10 = df.loc[i - 9 : i]
    if r["context"] == "SHORT_CONTEXT":
        if (last10["high"] > last10["ema27"]).any() and r["close"] < r["ema27"] and r["ema27"] - r["close"] <= r["atr14"] and not (is_impulse_bar(df, i) and r["close"] < r["open"]):
            return "SHORT"
    if r["context"] == "LONG_CONTEXT":
        if (last10["low"] < last10["ema27"]).any() and r["close"] > r["ema27"] and r["close"] - r["ema27"] <= r["atr14"] and not (is_impulse_bar(df, i) and r["close"] > r["open"]):
            return "LONG"
    return None


def entry_t2(df: pd.DataFrame, i: int) -> str | None:
    if i < 221 or i + 1 >= len(df):
        return None
    r = df.loc[i]
    prev10 = df.loc[i - 10 : i - 1]
    if r["context"] == "SHORT_CONTEXT":
        pullback_high = float(prev10["high"].max())
        bearish = r["close"] < r["open"] and r["close"] < (r["open"] + r["close"]) / 2 and r["close"] < r["ema27"]
        confirm = r["high"] <= pullback_high
        if (prev10["high"] >= prev10["ema27"]).any() and bearish and confirm and not is_impulse_bar(df, i):
            return "SHORT"
    if r["context"] == "LONG_CONTEXT":
        pullback_low = float(prev10["low"].min())
        bullish = r["close"] > r["open"] and r["close"] > (r["open"] + r["close"]) / 2 and r["close"] > r["ema27"]
        confirm = r["low"] >= pullback_low
        if (prev10["low"] <= prev10["ema27"]).any() and bullish and confirm and not is_impulse_bar(df, i):
            return "LONG"
    return None


def entry_t3(df: pd.DataFrame, i: int) -> str | None:
    if i < 225 or i + 1 >= len(df):
        return None
    r = df.loc[i]
    atr = float(r["atr14"])
    if r["context"] == "SHORT_CONTEXT":
        pullback = (df.loc[i - 4 : i - 1, "close"].diff() > 0).sum() >= 2
        local_low = float(df.loc[i - 10 : i - 1, "low"].min())
        if pullback and r["close"] < local_low and abs(r["close"] - r["ema27"]) <= 1.5 * atr:
            return "SHORT"
    if r["context"] == "LONG_CONTEXT":
        pullback = (df.loc[i - 4 : i - 1, "close"].diff() < 0).sum() >= 2
        local_high = float(df.loc[i - 10 : i - 1, "high"].max())
        if pullback and r["close"] > local_high and abs(r["close"] - r["ema27"]) <= 1.5 * atr:
            return "LONG"
    return None


def entry_t4(df: pd.DataFrame, i: int) -> str | None:
    if i < 221 or i + 1 >= len(df):
        return None
    r = df.loc[i]
    p = df.loc[i - 1]
    prev10 = df.loc[i - 10 : i - 2]
    if is_impulse_bar(df, i) or is_impulse_bar(df, i - 1):
        return None
    if r["context"] == "SHORT_CONTEXT":
        touched = (prev10["high"] >= prev10["ema27"]).any()
        if touched and p["close"] < p["ema27"] and r["close"] < r["ema27"] and r["close"] < p["close"]:
            return "SHORT"
    if r["context"] == "LONG_CONTEXT":
        touched = (prev10["low"] <= prev10["ema27"]).any()
        if touched and p["close"] > p["ema27"] and r["close"] > r["ema27"] and r["close"] > p["close"]:
            return "LONG"
    return None


ENTRY_FUNCS = {
    "ENTRY_A": baseline_entry_a,
    "ENTRY_T1": entry_t1,
    "ENTRY_T2": entry_t2,
    "ENTRY_T3": entry_t3,
    "ENTRY_T4": entry_t4,
}


def candidate_signal(df: pd.DataFrame, i: int, entry: str) -> dict | None:
    direction = ENTRY_FUNCS[entry](df, i)
    if direction is None:
        return None
    context_ok = context_allows(df, i, direction)
    late, late_reason = late_entry_block(df, i, direction)
    chop, chop_reason = chop_block(df, i)
    blocked = []
    if not context_ok:
        blocked.append("CONTEXT_BLOCK")
    if late:
        blocked.append("LATE_ENTRY_BLOCK")
    if chop:
        blocked.append("CHOP_BLOCK")
    return {
        "entry_variant": entry,
        "signal_i": i,
        "signal_time": df.loc[i, "dt"],
        "entry_i": i + 1,
        "entry_time": df.loc[i + 1, "dt"],
        "direction": direction,
        "context": df.loc[i, "context"],
        "context_ok": context_ok,
        "late_entry_block": late,
        "late_reason": late_reason,
        "chop_block": chop,
        "chop_reason": chop_reason,
        "blocked": bool(blocked),
        "block_reason": "|".join(blocked),
        "distance_to_ema27_atr": abs(float(df.loc[i, "close"] - df.loc[i, "ema27"])) / max(float(df.loc[i, "atr14"]), 1e-12),
        "move5_atr": side(direction) * (float(df.loc[i, "close"]) - float(df.loc[max(0, i - 5), "close"])) / max(float(df.loc[i, "atr14"]), 1e-12),
    }


def stop_a(df: pd.DataFrame, signal_i: int, direction: str) -> float:
    w = df.loc[signal_i - 4 : signal_i]
    return float(w["low"].min() if direction == "LONG" else w["high"].max())


def regime_flip(df: pd.DataFrame, i: int, direction: str) -> bool:
    r = df.loc[i]
    if direction == "LONG":
        return bool(r["close"] < r["ema200"] and r["ema27"] < r["ema200"] and r["ema200_slope_20"] < 0)
    return bool(r["close"] > r["ema200"] and r["ema27"] > r["ema200"] and r["ema200_slope_20"] > 0)


def exit_r5(df: pd.DataFrame, pos: dict, i: int) -> tuple[bool, str, float | None]:
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
    stop_hit = (direction == "LONG" and low <= pos["stop_price"]) or (direction == "SHORT" and high >= pos["stop_price"])
    if stop_hit:
        return True, "STOP_A", pos["stop_price"]
    current_fav_close = s * (close - entry_price) / atr
    close_exit = False
    reason = ""
    if pos["mfe_atr"] >= 1.0 and current_fav_close <= 0.5 * pos["mfe_atr"]:
        close_exit = True
        reason = "MFE_50_GIVEBACK"
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
    if regime_flip(df, i, direction):
        close_exit = True
        reason = "REGIME_FLIP"
    if close_exit and i + 1 < len(df):
        return True, reason, float(df.loc[i + 1, "open"])
    return False, "", None


def fixed_horizon(df: pd.DataFrame, entry_i: int, entry_price: float, direction: str, atr: float) -> dict:
    out = {}
    s = side(direction)
    for h in [3, 6, 12, 24]:
        end_i = min(len(df) - 1, entry_i + h - 1)
        w = df.loc[entry_i:end_i]
        mfe = s * ((w["high"].max() if direction == "LONG" else w["low"].min()) - entry_price) / atr
        mae = s * ((w["low"].min() if direction == "LONG" else w["high"].max()) - entry_price) / atr
        out[f"mfe_{h}b_atr"] = float(mfe)
        out[f"mae_{h}b_atr"] = float(mae)
    hit1 = hit2 = hitm1 = None
    for j in range(entry_i, min(len(df), entry_i + 25)):
        hi = s * ((df.loc[j, "high"] if direction == "LONG" else df.loc[j, "low"]) - entry_price) / atr
        lo = s * ((df.loc[j, "low"] if direction == "LONG" else df.loc[j, "high"]) - entry_price) / atr
        if hit1 is None and hi >= 1:
            hit1 = j
        if hit2 is None and hi >= 2:
            hit2 = j
        if hitm1 is None and lo <= -1:
            hitm1 = j
    out["plus1_before_minus1"] = bool(hit1 is not None and (hitm1 is None or hit1 <= hitm1))
    out["plus2_before_minus1"] = bool(hit2 is not None and (hitm1 is None or hit2 <= hitm1))
    return out


def simulate(df: pd.DataFrame, entry: str, start: pd.Timestamp, end: pd.Timestamp, scope: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signals = []
    trades = []
    fixed = []
    pos = None
    trade_no = 1
    for i in range(220, len(df) - 1):
        t = pd.Timestamp(df.loc[i, "dt"])
        next_t = pd.Timestamp(df.loc[i + 1, "dt"])
        if next_t < start or t > end:
            continue
        cand = candidate_signal(df, i, entry)
        if cand and start <= next_t <= end:
            executed = (pos is None) and not cand["blocked"]
            sig = dict(cand)
            sig.update({"scope": scope, "executed": executed, "skip_reason": "" if executed else ("POSITION_OPEN" if pos is not None and not cand["blocked"] else cand["block_reason"])})
            signals.append(sig)
            if executed:
                direction = cand["direction"]
                entry_raw = float(df.loc[i + 1, "open"])
                entry_price = slipped(entry_raw, direction, True)
                atr = float(df.loc[i, "atr14"])
                pos = {
                    "trade_id": f"{entry}_{scope}_{trade_no:04d}",
                    "entry_variant": entry,
                    "scope": scope,
                    "signal_time": t,
                    "entry_time": next_t,
                    "signal_i": i,
                    "entry_i": i + 1,
                    "direction": direction,
                    "entry_price": entry_price,
                    "stop_price": stop_a(df, i, direction),
                    "atr": atr,
                    "mfe_atr": 0.0,
                    "mae_atr": 0.0,
                    "mfe_price": entry_price,
                    "mae_price": entry_price,
                    "mfe_i": i + 1,
                    "mae_i": i + 1,
                    "warning_i": None,
                    "distance_to_ema27_atr": cand["distance_to_ema27_atr"],
                    "move5_atr": cand["move5_atr"],
                    "context": cand["context"],
                }
                fixed.append({"trade_id": pos["trade_id"], **fixed_horizon(df, i + 1, entry_price, direction, atr)})
                trade_no += 1
        if pos is None:
            continue
        if i < pos["entry_i"]:
            continue
        should_exit, reason, exit_raw = exit_r5(df, pos, i)
        if not should_exit:
            continue
        exit_i = i if reason == "STOP_A" else min(i + 1, len(df) - 1)
        exit_price = slipped(float(exit_raw), pos["direction"], False)
        s = side(pos["direction"])
        gross = s * (exit_price - pos["entry_price"]) / pos["entry_price"]
        net = gross - 2 * FEE
        mfe_delta = abs(pos["mfe_price"] - pos["entry_price"])
        realized_delta = s * (exit_price - pos["entry_price"])
        cap = np.nan if mfe_delta <= 0 else realized_delta / mfe_delta
        trades.append(
            {
                **{k: pos[k] for k in ["trade_id", "entry_variant", "scope", "signal_time", "entry_time", "direction", "context", "entry_price", "stop_price", "distance_to_ema27_atr", "move5_atr"]},
                "exit_time": df.loc[exit_i, "dt"],
                "exit_price": exit_price,
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
            }
        )
        pos = None
    return pd.DataFrame(signals), pd.DataFrame(trades), pd.DataFrame(fixed)


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


def trade_failure_type(r: pd.Series) -> str:
    if r["mfe_atr"] < 1:
        return "BAD_ENTRY"
    if r["mfe_atr"] >= 1.5 and r["net_return"] <= 0:
        return "GOOD_ENTRY_BAD_EXIT"
    if r["move5_atr"] > 2:
        return "LATE_ENTRY"
    return "MIXED"


def metric_row(tr: pd.DataFrame, sig: pd.DataFrame, fixed: pd.DataFrame, label: str, cost_mult: float = 1.0) -> dict:
    row = {"entry_variant": label, "signals": int(len(sig)), "executed_trades": int(len(tr))}
    row["blocked_by_context"] = int(sig["block_reason"].fillna("").str.contains("CONTEXT_BLOCK").sum()) if not sig.empty else 0
    row["blocked_by_late_entry"] = int(sig["block_reason"].fillna("").str.contains("LATE_ENTRY_BLOCK").sum()) if not sig.empty else 0
    row["blocked_by_chop"] = int(sig["block_reason"].fillna("").str.contains("CHOP_BLOCK").sum()) if not sig.empty else 0
    if tr.empty:
        return {
            **row,
            "long_trades": 0,
            "short_trades": 0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "average_trade": 0.0,
            "median_trade": 0.0,
        }
    rets = tr["gross_return"] - 2 * FEE * cost_mult
    eq = equity_curve(rets)
    joined = tr.merge(fixed, on="trade_id", how="left")
    wins = rets[rets > 0]
    row.update(
        {
            "long_trades": int((tr["direction"] == "LONG").sum()),
            "short_trades": int((tr["direction"] == "SHORT").sum()),
            "profit_factor": pf(rets),
            "total_return": float(eq.iloc[-1] / START_CAPITAL - 1),
            "max_drawdown": max_dd(rets),
            "win_rate": float((rets > 0).mean()),
            "average_trade": float(rets.mean()),
            "median_trade": float(rets.median()),
            "average_mfe": float(tr["mfe_atr"].mean()),
            "average_mae": float(tr["mae_atr"].mean()),
            "median_mfe": float(tr["mfe_atr"].median()),
            "median_mae": float(tr["mae_atr"].median()),
            "mfe_3b": float(joined["mfe_3b_atr"].mean()),
            "mfe_6b": float(joined["mfe_6b_atr"].mean()),
            "mfe_12b": float(joined["mfe_12b_atr"].mean()),
            "mfe_24b": float(joined["mfe_24b_atr"].mean()),
            "mae_3b": float(joined["mae_3b_atr"].mean()),
            "mae_6b": float(joined["mae_6b_atr"].mean()),
            "mae_12b": float(joined["mae_12b_atr"].mean()),
            "mae_24b": float(joined["mae_24b_atr"].mean()),
            "plus1_before_minus1": float(joined["plus1_before_minus1"].mean()),
            "plus2_before_minus1": float(joined["plus2_before_minus1"].mean()),
            "bad_entry_share": float((tr["failure_type"] == "BAD_ENTRY").mean()),
            "late_entry_share": float((tr["failure_type"] == "LATE_ENTRY").mean()),
            "good_entry_bad_exit_share": float((tr["failure_type"] == "GOOD_ENTRY_BAD_EXIT").mean()),
            "stop_out_rate": float((tr["exit_reason"] == "STOP_A").mean()),
            "average_distance_to_ema27_at_entry": float(tr["distance_to_ema27_atr"].mean()),
            "average_move_already_completed_before_entry": float(tr["move5_atr"].mean()),
            "top1_profit_share": float(wins.max() / wins.sum()) if len(wins) and wins.sum() > 0 else 1.0,
            "result_without_top1": float((1 + rets.drop(index=rets.idxmax())).prod() - 1) if len(rets) > 1 else 0.0,
            "cost_mult": cost_mult,
        }
    )
    return row


def select_entries(dev: pd.DataFrame) -> pd.DataFrame:
    d = dev.copy()
    if d.empty:
        return pd.DataFrame(columns=["entry_variant", "selection_rank", "selection_reason"])
    d["score"] = (
        d["profit_factor"].clip(upper=5).fillna(0)
        + d["plus1_before_minus1"].fillna(0)
        + d["median_mfe"].fillna(0)
        - d["bad_entry_share"].fillna(1)
        - d["late_entry_share"].fillna(1)
        + (d["result_without_top1"] > 0).astype(float)
    )
    d = d[d["executed_trades"] >= 3].sort_values(["score", "profit_factor"], ascending=False).head(2)
    return pd.DataFrame(
        [
            {"entry_variant": r.entry_variant, "selection_rank": k + 1, "selection_reason": "fixed predeclared score on DEVELOPMENT only"}
            for k, r in enumerate(d.itertuples(index=False))
        ]
    )


def write_pine() -> None:
    text = """//@version=6
indicator("EXP-007 Trend-Aligned EMA Entry Review", overlay=true, max_labels_count=500)
showBaseline = input.bool(true, "showBaseline")
showT1 = input.bool(true, "showT1")
showT2 = input.bool(true, "showT2")
showT3 = input.bool(true, "showT3")
showT4 = input.bool(true, "showT4")
showBlocked = input.bool(true, "showBlocked")
showLong = input.bool(true, "showLong")
showShort = input.bool(true, "showShort")
showOnlySelected = input.bool(false, "showOnlySelected")
tradeFrom = input.int(1, "tradeFrom", minval=1)
tradeTo = input.int(500, "tradeTo", minval=1)
ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
atr14 = ta.atr(14)
ema200Slope20 = ema200 - ema200[20]
ema27Slope10 = ema27 - ema27[10]
dist = math.abs(ema27 - ema200) / atr14
crossing = ta.cross(ema27, ema200) ? 1 : 0
cross30 = math.sum(crossing, 30)
between = close > math.min(ema27, ema200) and close < math.max(ema27, ema200)
longContext = ema27 > ema200 and ema200Slope20 > 0 and close > ema200 and dist >= 0.25 and cross30 <= 1 and not between
shortContext = ema27 < ema200 and ema200Slope20 < 0 and close < ema200 and dist >= 0.25 and cross30 <= 1 and not between
blockContext = not longContext and not shortContext
plot(ema27, "EMA27", color=color.aqua)
plot(ema200, "EMA200", color=color.orange)
bgcolor(longContext ? color.new(color.green, 90) : shortContext ? color.new(color.red, 90) : color.new(color.gray, 94))
body = math.abs(close - open)
medBody = ta.median(body[1], 10)
impulse = body > 1.5 * medBody
range20 = ta.highest(high, 20) - ta.lowest(low, 20)
dirChange = math.sum(math.sign(close - open) != math.sign(close[1] - open[1]) ? 1 : 0, 10)
ema27Cross10 = math.sum(ta.cross(close, ema27) ? 1 : 0, 10)
chop = cross30 > 1 or ema27Slope10 * ema200Slope20 < 0 or range20 < 2 * atr14 or dirChange >= 6 or ema27Cross10 >= 5
lateLong = close - close[5] > 2 * atr14 or math.abs(close - ema27) > 1.5 * atr14 or impulse or (close > open and close[1] > open[1] and close[2] > open[2] and close - open[2] > 1.5 * atr14)
lateShort = close[5] - close > 2 * atr14 or math.abs(close - ema27) > 1.5 * atr14 or impulse or (close < open and close[1] < open[1] and close[2] < open[2] and open[2] - close > 1.5 * atr14)
baselineLong = ta.crossover(close, ema27) and ema27 > ema200
baselineShort = ta.crossunder(close, ema27) and ema27 < ema200
t1Long = longContext and ta.lowest(low - ema27, 10) < 0 and close > ema27 and close - ema27 <= atr14 and not impulse
t1Short = shortContext and ta.highest(high - ema27, 10) > 0 and close < ema27 and ema27 - close <= atr14 and not impulse
t2Long = longContext and ta.lowest(low - ema27, 10) <= 0 and close > open and close > ema27 and not impulse
t2Short = shortContext and ta.highest(high - ema27, 10) >= 0 and close < open and close < ema27 and not impulse
t3Long = longContext and close > ta.highest(high[1], 10) and math.abs(close - ema27) <= 1.5 * atr14
t3Short = shortContext and close < ta.lowest(low[1], 10) and math.abs(close - ema27) <= 1.5 * atr14
t4Long = longContext and ta.lowest(low[2] - ema27[2], 8) <= 0 and close[1] > ema27[1] and close > ema27 and close > close[1] and not impulse and not impulse[1]
t4Short = shortContext and ta.highest(high[2] - ema27[2], 8) >= 0 and close[1] < ema27[1] and close < ema27 and close < close[1] and not impulse and not impulse[1]
okLong = showLong and not chop and not lateLong
okShort = showShort and not chop and not lateShort
plotshape(showBaseline and baselineLong and okLong, "ENTRY_A LONG", shape.triangleup, location.belowbar, color.green, size=size.tiny, text="A")
plotshape(showBaseline and baselineShort and okShort, "ENTRY_A SHORT", shape.triangledown, location.abovebar, color.red, size=size.tiny, text="A")
plotshape(showT1 and t1Long and okLong, "T1 LONG", shape.triangleup, location.belowbar, color.lime, size=size.tiny, text="T1")
plotshape(showT1 and t1Short and okShort, "T1 SHORT", shape.triangledown, location.abovebar, color.maroon, size=size.tiny, text="T1")
plotshape(showT2 and t2Long and okLong, "T2 LONG", shape.triangleup, location.belowbar, color.lime, size=size.tiny, text="T2")
plotshape(showT2 and t2Short and okShort, "T2 SHORT", shape.triangledown, location.abovebar, color.maroon, size=size.tiny, text="T2")
plotshape(showT3 and t3Long and okLong, "T3 LONG", shape.triangleup, location.belowbar, color.lime, size=size.tiny, text="T3")
plotshape(showT3 and t3Short and okShort, "T3 SHORT", shape.triangledown, location.abovebar, color.maroon, size=size.tiny, text="T3")
plotshape(showT4 and t4Long and okLong, "T4 LONG", shape.triangleup, location.belowbar, color.lime, size=size.tiny, text="T4")
plotshape(showT4 and t4Short and okShort, "T4 SHORT", shape.triangledown, location.abovebar, color.maroon, size=size.tiny, text="T4")
plotshape(showBlocked and blockContext, "BLOCK_CONTEXT", shape.xcross, location.top, color.gray, size=size.tiny)
plotshape(showBlocked and chop, "CHOP_BLOCK", shape.circle, location.top, color.yellow, size=size.tiny)
plotshape(showBlocked and (lateLong or lateShort), "LATE_ENTRY_BLOCK", shape.circle, location.bottom, color.orange, size=size.tiny)
"""
    (OUT / "EXP007_TREND_ENTRY_REVIEW.pine").write_text(text, encoding="utf-8")


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

    def rect(self, x0: float, y0: float, x1: float, y1: float, c: tuple[int, int, int]) -> None:
        x0, x1 = sorted([int(round(x0)), int(round(x1))])
        y0, y1 = sorted([int(round(y0)), int(round(y1))])
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.dot(x, y, c)

    def save(self, path: Path) -> None:
        raw = b"".join(b"\x00" + bytes(self.p[y * self.w * 3 : (y + 1) * self.w * 3]) for y in range(self.h))

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b"")
        )


def simple_bar_png(rows: pd.DataFrame, labels: list[str], cols: list[str], path: Path) -> None:
    r = Raster()
    pad_l, pad_b, top = 70, 60, 30
    r.line(pad_l, r.h - pad_b, r.w - 30, r.h - pad_b, (150, 150, 150), 1)
    r.line(pad_l, top, pad_l, r.h - pad_b, (150, 150, 150), 1)
    vals = []
    for _, row in rows.iterrows():
        for col in cols:
            vals.append(float(row.get(col, 0) or 0))
    ymin = min(0.0, min(vals) if vals else 0.0)
    ymax = max(1.0, max(vals) if vals else 1.0)
    span = ymax - ymin if ymax != ymin else 1.0
    n = max(1, len(rows) * len(cols))
    bar_w = max(6, (r.w - pad_l - 60) / (n * 1.4))
    x = pad_l + 20
    colors = [(40, 120, 190), (220, 120, 40), (80, 160, 90), (180, 80, 150)]
    for _, row in rows.iterrows():
        for ci, col in enumerate(cols):
            v = float(row.get(col, 0) or 0)
            y0 = r.h - pad_b - (0 - ymin) / span * (r.h - pad_b - top)
            y1 = r.h - pad_b - (v - ymin) / span * (r.h - pad_b - top)
            r.rect(x, y0, x + bar_w, y1, colors[ci % len(colors)])
            x += bar_w + 4
        x += bar_w
    r.save(path)


def simple_pdf(lines: list[str], path: Path) -> None:
    content = ["BT /F1 10 Tf 36 760 Td"]
    for line in lines[:60]:
        s = str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:105]
        content.append(f"({s}) Tj 0 -12 Td")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def visual_trade_pdf(examples: pd.DataFrame, df: pd.DataFrame, path: Path) -> None:
    pages: list[bytes] = []
    for _, row in examples.head(30).iterrows():
        try:
            entry_i = int(df.index[df["dt"].eq(pd.Timestamp(row["entry_time"]))][0])
        except IndexError:
            continue
        start = max(0, entry_i - 25)
        end = min(len(df) - 1, entry_i + 35)
        w = df.loc[start:end].reset_index(drop=True)
        prices = pd.concat([w["close"], w["ema27"], w["ema200"]]).astype(float)
        ymin, ymax = float(prices.min()), float(prices.max())
        if ymin == ymax:
            ymax += 1
        x0, y0, width, height = 54, 110, 500, 560

        def xy(k: int, value: float) -> tuple[float, float]:
            x = x0 + (k / max(1, len(w) - 1)) * width
            y = y0 + ((value - ymin) / (ymax - ymin)) * height
            return x, y

        def polyline(values: pd.Series, color: str, lw: float = 1.0) -> list[str]:
            cmds = [color, f"{lw} w"]
            first = True
            for k, v in enumerate(values.astype(float)):
                x, y = xy(k, float(v))
                cmds.append(f"{x:.2f} {y:.2f} {'m' if first else 'l'}")
                first = False
            cmds.append("S")
            return cmds

        cmds = [
            "BT /F1 10 Tf 36 760 Td",
            f"({str(row['trade_id'])} {str(row['entry_variant'])} {str(row['direction'])} ret={float(row['net_return']):.2%} reason={str(row['exit_reason'])}) Tj",
            "ET",
            "0.8 0.8 0.8 RG 0.5 w",
            f"{x0} {y0} m {x0 + width} {y0} l {x0 + width} {y0 + height} l {x0} {y0 + height} l {x0} {y0} l S",
        ]
        cmds += polyline(w["close"], "0 0 0 RG", 1.3)
        cmds += polyline(w["ema27"], "0 0.45 0.85 RG", 0.9)
        cmds += polyline(w["ema200"], "1 0.45 0 RG", 0.9)
        for t, color in [(pd.Timestamp(row["entry_time"]), "0 0.7 0 RG"), (pd.Timestamp(row["exit_time"]), "0.6 0 0.8 RG")]:
            idx = w.index[w["dt"].eq(t)]
            if len(idx):
                x, _ = xy(int(idx[0]), float(w.loc[int(idx[0]), "close"]))
                cmds += [color, "1.4 w", f"{x:.2f} {y0:.2f} m {x:.2f} {y0 + height:.2f} l S"]
        pages.append("\n".join(cmds).encode("latin-1", errors="replace"))
    if not pages:
        pages = [b"BT /F1 12 Tf 36 760 Td (No visual examples available) Tj ET"]

    objs: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for page_no, stream in enumerate(pages):
        content_obj = 4 + page_no * 2
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_obj} 0 R >>".encode()
        )
        objs.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def write_plots(dev: pd.DataFrame, val: pd.DataFrame, tr: pd.DataFrame, df: pd.DataFrame) -> None:
    simple_bar_png(dev, dev["entry_variant"].tolist() if "entry_variant" in dev else [], ["profit_factor", "plus1_before_minus1"], OUT / "entry_comparison.png")
    simple_bar_png(dev, dev["entry_variant"].tolist() if "entry_variant" in dev else [], ["median_mfe", "median_mae"], OUT / "mfe_mae_comparison.png")
    ctx = df["context"].value_counts().rename_axis("entry_variant").reset_index(name="count")
    simple_bar_png(ctx, ctx["entry_variant"].tolist(), ["count"], OUT / "context_distribution.png")

    examples = pd.concat(
        [
            tr[(tr["direction"] == "SHORT") & (tr["net_return"] > 0)].head(10),
            tr[(tr["direction"] == "LONG") & (tr["net_return"] > 0)].head(10),
            tr[tr["net_return"] < 0].head(5),
            tr.head(30),
        ]
    ).drop_duplicates("trade_id")
    visual_trade_pdf(examples, df, OUT / "EXP007_TREND_ENTRY_OVERVIEW.pdf")


def md_table(df: pd.DataFrame, max_rows: int = 12) -> str:
    if df.empty:
        return "No rows."
    view = df.head(max_rows).copy()
    cols = list(view.columns)

    def cell(v) -> str:
        if isinstance(v, float):
            return f"{v:.6g}"
        return str(v)

    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in view.iterrows():
        rows.append("| " + " | ".join(cell(row[c]) for c in cols) + " |")
    if len(df) > max_rows:
        rows.append(f"| ... {len(df) - max_rows} more rows |" + " | " * (len(cols) - 1))
    return "\n".join(rows)


def write_report(dev: pd.DataFrame, val: pd.DataFrame, selected: pd.DataFrame, signals: pd.DataFrame, trades: pd.DataFrame, verdict: str) -> None:
    base = signals[signals["entry_variant"] == "ENTRY_A"]
    baseline_counter = int(
        (
            ((base["direction"] == "LONG") & (base["context"] != "LONG_CONTEXT"))
            | ((base["direction"] == "SHORT") & (base["context"] != "SHORT_CONTEXT"))
        ).sum()
    ) if not base.empty else 0
    report = [
        "# EXP-007 — Trend-Aligned EMA Entry",
        "",
        "## Scope",
        "",
        "ADAUSDT 4H, development 2023-07-01 -> 2024-06-30, validation 2024-07-01 -> 2024-12-31. Data after 2024-12-31 was not used. The consumed 2025-2026 holdout was not opened.",
        "",
        "## Selected Entries",
        "",
        md_table(selected) if not selected.empty else "No selected entries.",
        "",
        "## Development Metrics",
        "",
        md_table(dev),
        "",
        "## Validation Metrics",
        "",
        md_table(val) if not val.empty else "No validation trades.",
        "",
        "## Required Answers",
        "",
        f"1. Baseline ENTRY_A raw signals against strict EMA context: {baseline_counter}.",
        f"2. Directional gate blocked {int(signals['block_reason'].fillna('').str.contains('CONTEXT_BLOCK').sum())} candidate signals.",
        f"3. LATE_ENTRY_BLOCK blocked {int(signals['block_reason'].fillna('').str.contains('LATE_ENTRY_BLOCK').sum())}; CHOP_BLOCK blocked {int(signals['block_reason'].fillna('').str.contains('CHOP_BLOCK').sum())}.",
        "4. Best SHORT_CONTEXT entry on development: "
        + (trades[(trades["scope"] == "DEVELOPMENT") & (trades["direction"] == "SHORT")].groupby("entry_variant")["net_return"].sum().sort_values(ascending=False).index[0] if not trades[(trades["scope"] == "DEVELOPMENT") & (trades["direction"] == "SHORT")].empty else "DATA_INSUFFICIENT")
        + ".",
        "5. Best LONG_CONTEXT entry on development: "
        + (trades[(trades["scope"] == "DEVELOPMENT") & (trades["direction"] == "LONG")].groupby("entry_variant")["net_return"].sum().sort_values(ascending=False).index[0] if not trades[(trades["scope"] == "DEVELOPMENT") & (trades["direction"] == "LONG")].empty else "DATA_INSUFFICIENT")
        + ".",
        "6. Bad-entry reduction is assessed in `entry_quality.csv`; selected entries are compared to gated ENTRY_A.",
        "7. Late entries are blocked before execution by the fixed LATE_ENTRY_BLOCK.",
        "8. +1 ATR before -1 ATR is reported in development and validation metrics.",
        "9. PF and DD are reported in development and validation metrics.",
        "10. Validation transfer is summarized by the verdict below.",
        "11. LONG/SHORT symmetry remains limited if one side has a small sample.",
        "12. Candidate entries: " + (", ".join(selected["entry_variant"].tolist()) if not selected.empty else "none") + ".",
        "13. Next experiment should visually review selected entry failures before any new holdout.",
        "14. Research can continue without new holdout as long as it remains on 2023-2024 or other non-consumed research data.",
        "",
        "## Verdict",
        "",
        verdict,
    ]
    (EXP / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def determine_verdict(val: pd.DataFrame, selected: pd.DataFrame) -> str:
    if selected.empty:
        return "DATA_INSUFFICIENT"
    if val.empty or int(val["executed_trades"].sum()) < 5:
        return "DATA_INSUFFICIENT"
    good = val[(val["profit_factor"] > 1.0) & (val["bad_entry_share"] < 0.5) & (val["plus1_before_minus1"] >= 0.45)]
    if good.empty:
        return "NO_STABLE_ENTRY"
    long_good = bool((good["long_trades"] > 0).any())
    short_good = bool((good["short_trades"] > 0).any())
    if long_good and short_good:
        return "TREND_ALIGNED_ENTRY_FOUND"
    if short_good:
        return "SHORT_ENTRY_FOUND_LONG_WEAK"
    if long_good:
        return "LONG_ENTRY_FOUND_SHORT_WEAK"
    return "ENTRY_FILTERS_HELP_BUT_WEAK"


def main() -> None:
    ensure_dirs()
    df = load_ohlc()
    all_signals = []
    all_trades = []
    all_fixed = []
    dev_rows = []
    for entry in ENTRIES:
        sig, tr, fixed = simulate(df, entry, DEVELOPMENT_START, DEVELOPMENT_END, "DEVELOPMENT")
        if not tr.empty:
            tr["failure_type"] = tr.apply(trade_failure_type, axis=1)
        all_signals.append(sig)
        all_trades.append(tr)
        all_fixed.append(fixed)
        dev_rows.append(metric_row(tr, sig, fixed, entry))
    signals_dev = pd.concat(all_signals, ignore_index=True) if all_signals else pd.DataFrame()
    trades_dev = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    fixed_dev = pd.concat(all_fixed, ignore_index=True) if all_fixed else pd.DataFrame()
    dev = pd.DataFrame(dev_rows)
    selected = select_entries(dev)

    val_signals = []
    val_trades = []
    val_fixed = []
    val_rows = []
    for entry in selected["entry_variant"].tolist():
        sig, tr, fixed = simulate(df, entry, VALIDATION_START, VALIDATION_END, "VALIDATION")
        if not tr.empty:
            tr["failure_type"] = tr.apply(trade_failure_type, axis=1)
        val_signals.append(sig)
        val_trades.append(tr)
        val_fixed.append(fixed)
        val_rows.append(metric_row(tr, sig, fixed, entry))
    signals_val = pd.concat(val_signals, ignore_index=True) if val_signals else pd.DataFrame()
    trades_val = pd.concat(val_trades, ignore_index=True) if val_trades else pd.DataFrame()
    fixed_val = pd.concat(val_fixed, ignore_index=True) if val_fixed else pd.DataFrame()
    val = pd.DataFrame(val_rows)

    signals = pd.concat([signals_dev, signals_val], ignore_index=True)
    trades = pd.concat([trades_dev, trades_val], ignore_index=True)
    fixed = pd.concat([fixed_dev, fixed_val], ignore_index=True)

    if not trades.empty:
        trades["period_after_2024"] = pd.Timestamp("1900-01-01")
        if pd.to_datetime(trades["entry_time"]).max() > VALIDATION_END:
            raise RuntimeError("Trade after 2024-12-31 entered EXP-007.")

    signals.to_csv(OUT / "all_entry_signals.csv", index=False)
    trades.to_csv(OUT / "all_entry_trades.csv", index=False)
    dev.to_csv(OUT / "development_metrics.csv", index=False)
    selected.to_csv(OUT / "selected_entries.csv", index=False)
    val.to_csv(OUT / "validation_metrics.csv", index=False)
    trades_val.to_csv(OUT / "validation_trades.csv", index=False)
    signals[signals["block_reason"].fillna("").str.contains("CONTEXT_BLOCK")].to_csv(OUT / "context_blocks.csv", index=False)
    signals[signals["block_reason"].fillna("").str.contains("LATE_ENTRY_BLOCK")].to_csv(OUT / "late_entry_blocks.csv", index=False)
    signals[signals["block_reason"].fillna("").str.contains("CHOP_BLOCK")].to_csv(OUT / "chop_blocks.csv", index=False)
    fixed.to_csv(OUT / "fixed_horizon_outcomes.csv", index=False)

    entry_quality = trades.groupby(["scope", "entry_variant", "direction"], dropna=False).agg(
        trades=("trade_id", "count"),
        bad_entry_share=("failure_type", lambda s: float((s == "BAD_ENTRY").mean())),
        late_entry_share=("failure_type", lambda s: float((s == "LATE_ENTRY").mean())),
        good_entry_bad_exit_share=("failure_type", lambda s: float((s == "GOOD_ENTRY_BAD_EXIT").mean())),
        median_mfe=("mfe_atr", "median"),
        median_mae=("mae_atr", "median"),
        total_return=("net_return", lambda s: float((1 + s).prod() - 1)),
    ).reset_index() if not trades.empty else pd.DataFrame()
    entry_quality.to_csv(OUT / "entry_quality.csv", index=False)

    cost_rows = []
    for scope, sigs, fixed_df in [("DEVELOPMENT", signals_dev, fixed_dev), ("VALIDATION", signals_val, fixed_val)]:
        tr_scope = trades[trades["scope"] == scope] if not trades.empty else pd.DataFrame()
        for entry in sorted(tr_scope["entry_variant"].unique()) if not tr_scope.empty else []:
            tr_e = tr_scope[tr_scope["entry_variant"] == entry]
            sig_e = sigs[sigs["entry_variant"] == entry] if not sigs.empty else pd.DataFrame()
            fix_e = fixed_df[fixed_df["trade_id"].isin(tr_e["trade_id"])] if not fixed_df.empty else pd.DataFrame()
            for cm in [1, 2, 3]:
                row = metric_row(tr_e, sig_e, fix_e, entry, cm)
                row["scope"] = scope
                row["cost_mult"] = cm
                cost_rows.append(row)
    pd.DataFrame(cost_rows).to_csv(OUT / "cost_stress.csv", index=False)

    conc = []
    for (scope, entry), g in trades.groupby(["scope", "entry_variant"]) if not trades.empty else []:
        rets = g["net_return"]
        wins = rets[rets > 0]
        conc.append(
            {
                "scope": scope,
                "entry_variant": entry,
                "trades": len(g),
                "top1_profit_share": float(wins.max() / wins.sum()) if len(wins) and wins.sum() > 0 else 1.0,
                "result_without_top1": float((1 + rets.drop(index=rets.idxmax())).prod() - 1) if len(rets) > 1 else 0.0,
            }
        )
    pd.DataFrame(conc).to_csv(OUT / "concentration_checks.csv", index=False)

    dist = trades.groupby(["scope", "entry_variant"]).agg(
        avg_distance_to_ema27_atr=("distance_to_ema27_atr", "mean"),
        median_distance_to_ema27_atr=("distance_to_ema27_atr", "median"),
        avg_move5_atr=("move5_atr", "mean"),
        median_move5_atr=("move5_atr", "median"),
    ).reset_index() if not trades.empty else pd.DataFrame()
    dist.to_csv(OUT / "entry_distance_analysis.csv", index=False)

    write_pine()
    write_plots(dev, val, trades, df)
    verdict = determine_verdict(val, selected)
    write_report(dev, val, selected, signals, trades, verdict)
    print(verdict)
    print("selected", selected["entry_variant"].tolist() if not selected.empty else [])


if __name__ == "__main__":
    main()
