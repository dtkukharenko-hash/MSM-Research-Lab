"""Зона как коридор между EMA27 (сверху) и EMA200 (снизу).

Конструкция по словесному описанию:
  цена шла выше EMA27, EMA27 выше EMA200, EMA200 смотрит вверх;
  происходит пробой EMA27 вниз; цена движется под EMA27,
  но к EMA200 не приближается; EMA200 по-прежнему растёт.

Зона начинается на баре пробоя EMA27 вниз и живёт, пока цена между
средними. Два исхода:
  * "reclaim" — close вернулся выше EMA27 (откат закончился, тренд продолжен);
  * "ema200"  — low достиг EMA200 (откат превратился в слом).

Ключевая величина — глубина захода, нормированная на ширину коридора:
    depth = (EMA27 − min low) / (EMA27 − EMA200)   на момент минимума
0 — цена сразу отскочила от EMA27, 1 — дошла до EMA200. Это и есть
формализация "не приближается к EMA200", и она безразмерна: сравнима
на любой стадии тренда, где бы средние ни разошлись.

Зона расширяется вместе со спредом EMA27−EMA200 — то есть сама по себе,
по мере созревания движения, без подгонки размера.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from zones import add_features, load

MIN_BARS = 3          # мгновенные проколы EMA27 зоной не считаем
SLOPE_LOOKBACK = 30   # горизонт наклона EMA200


def detect(df: pd.DataFrame, min_bars: int = MIN_BARS,
           require_rising: bool = True) -> pd.DataFrame:
    close = df["close"].to_numpy()
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()
    e27 = df["ema27"].to_numpy()
    e200 = df["ema200"].to_numpy()
    slope = df["slope200"].to_numpy()

    zones = []
    total = len(df)
    i = SLOPE_LOOKBACK + 1

    while i < total - 1:
        # Пробой EMA27 вниз в лонговом контексте с растущей EMA200.
        crossed = close[i - 1] >= e27[i - 1] and close[i] < e27[i]
        ctx = e27[i] > e200[i] and np.isfinite(slope[i])
        if require_rising:
            ctx = ctx and slope[i] > 0
        if not (crossed and ctx):
            i += 1
            continue

        t0 = i
        j = i + 1
        outcome, end = None, None
        min_low, depth = np.inf, 0.0

        while j < total:
            corridor = e27[j] - e200[j]
            if corridor <= 0:            # средние сошлись — контекст разрушен
                outcome, end = "cross", j
                break
            if low[j] <= e200[j]:        # дошли до медленной средней
                min_low = min(min_low, low[j])
                depth = 1.0
                outcome, end = "ema200", j
                break
            if low[j] < min_low:
                min_low = low[j]
                depth = max(depth, (e27[j] - min_low) / corridor)
            if close[j] > e27[j]:        # вернулись над быстрой средней
                outcome, end = "reclaim", j
                break
            j += 1

        if end is None:
            break

        bars = end - t0
        if bars >= min_bars:
            zones.append({
                "start": df["timestamp_utc"].iloc[t0],
                "end": df["timestamp_utc"].iloc[end],
                "bars": bars,
                "outcome": outcome,
                "depth": min(depth, 1.0),
                "spread_t0": (e27[t0] - e200[t0]) / e200[t0] * 100,
                "slope200_t0": slope[t0],
                "start_idx": t0,
                "end_idx": end,
            })
        i = end + 1

    return pd.DataFrame(zones)


def outcomes(df: pd.DataFrame, z: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Что было после закрытия зоны: доходность, лучший и худший ход."""
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(close)
    z = z.copy()
    idx = z["end_idx"].to_numpy()
    end = np.minimum(idx + horizon, n - 1)
    z[f"fwd{horizon}"] = (close[end] / close[idx] - 1) * 100
    z["mfe"] = [(high[i + 1:j + 1].max() / close[i] - 1) * 100 if j > i else np.nan
                for i, j in zip(idx, end)]
    z["mae"] = [(low[i + 1:j + 1].min() / close[i] - 1) * 100 if j > i else np.nan
                for i, j in zip(idx, end)]
    return z


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="4h")
    p.add_argument("--horizon", type=int, default=30)
    p.add_argument("--min-bars", type=int, default=MIN_BARS)
    args = p.parse_args(argv)

    df = add_features(load(args.tf))
    z = outcomes(df, detect(df, args.min_bars), args.horizon)
    if z.empty:
        print("зон не найдено")
        return 0
    pd.set_option("display.width", 220)
    cols = ["start", "end", "bars", "outcome", "depth", "spread_t0",
            "slope200_t0", f"fwd{args.horizon}", "mfe", "mae"]
    print(z[cols].to_string(index=False, float_format=lambda v: f"{v:7.2f}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
