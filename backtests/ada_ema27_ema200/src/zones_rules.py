"""Зона по фиксированному последнему максимуму перед уходом под EMA27.

Правила (сформулированы по трём размеченным вручную примерам):

  R1. Контекст: EMA27 > EMA200 и EMA200 растёт.
  R2. Цена идёт выше EMA27. Пока это так, ведём бегущий максимум high.
  R3. Событие: close уходит ниже EMA27. В этот момент бегущий максимум
      ФИКСИРУЕТСЯ — это верхняя граница зоны (горизонталь), level.
  R4. Зона живёт, пока close < level и цена не дошла до EMA200.
  R5. Исходы:
        breakout — close > level (зона пробита вверх, тренд продолжен);
        ema200   — low <= EMA200 (откат перерос в слом);
        context  — EMA27 ушла под EMA200 (контекст разрушен).

Последовательность «маленькая зона, потом больше» не постулируется:
размер зоны получается сам, из спреда EMA27−EMA200 и расстояния до level.

Никакого look-ahead: level фиксируется на баре события, все проверки —
по текущему бару.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from zones import add_features, load

MIN_BARS = 3


def detect(df: pd.DataFrame, min_bars: int = MIN_BARS,
           require_rising: bool = True, max_bars: int | None = None) -> pd.DataFrame:
    close = df["close"].to_numpy()
    high, low = df["high"].to_numpy(), df["low"].to_numpy()
    e27, e200 = df["ema27"].to_numpy(), df["ema200"].to_numpy()
    slope = df["slope200"].to_numpy()
    total = len(df)

    zones = []
    run_max = -np.inf          # R2: бегущий максимум над EMA27
    i = 31

    while i < total - 1:
        above = close[i] >= e27[i]
        if above:
            run_max = max(run_max, high[i]) if np.isfinite(run_max) else high[i]
            i += 1
            continue

        # R3: событие — ушли под EMA27. Фиксируем level.
        ctx = e27[i] > e200[i] and np.isfinite(slope[i])
        if require_rising:
            ctx = ctx and slope[i] > 0
        if not (ctx and np.isfinite(run_max) and run_max > close[i]):
            run_max = -np.inf
            i += 1
            continue

        t0, level = i, run_max
        corridor0 = (e27[t0] - e200[t0]) / e200[t0] * 100
        j, outcome, end = t0 + 1, None, None
        min_low = low[t0]
        depth = 0.0

        while j < total:
            if e27[j] <= e200[j]:
                outcome, end = "context", j
                break
            if low[j] <= e200[j]:
                outcome, end, depth = "ema200", j, 1.0
                break
            if low[j] < min_low:
                min_low = low[j]
            # Глубину считаем ПО ТЕКУЩЕМУ бару: сравнивать старый минимум с
            # сегодняшней EMA200 нельзя — EMA200 растёт, и депth уползал бы к 1
            # без всякого приближения цены к средней.
            depth = max(depth, (e27[j] - low[j]) / (e27[j] - e200[j]))
            if close[j] > level:
                outcome, end = "breakout", j
                break
            if max_bars and j - t0 >= max_bars:
                outcome, end = "timeout", j
                break
            j += 1

        if end is None:
            break

        bars = end - t0
        if bars >= min_bars:
            seg = slice(t0, end + 1)
            zones.append({
                "start": df["timestamp_utc"].iloc[t0],
                "end": df["timestamp_utc"].iloc[end],
                "bars": bars,
                "outcome": outcome,
                "level": level,
                # насколько цена просела от level к моменту события, %
                "drop_at_event": (level - close[t0]) / level * 100,
                "depth": min(depth, 1.0),
                "range_pct": (high[seg].max() - low[seg].min()) / close[seg].mean() * 100,
                "corridor_t0": corridor0,
                "slope200_t0": slope[t0],
                "start_idx": t0,
                "end_idx": end,
            })
        run_max = -np.inf
        i = end + 1

    return pd.DataFrame(zones)


def outcomes(df: pd.DataFrame, z: pd.DataFrame, horizon: int) -> pd.DataFrame:
    close, high, low = (df["close"].to_numpy(), df["high"].to_numpy(),
                        df["low"].to_numpy())
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
    pd.set_option("display.width", 240)
    cols = ["start", "end", "bars", "outcome", "level", "drop_at_event", "depth",
            "range_pct", "corridor_t0", f"fwd{args.horizon}", "mfe", "mae"]
    print(z[cols].to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
