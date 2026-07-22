"""Правила разметки зон для лонга и шорта. Задача — только разметка.

ЛОНГ (исходная формулировка):
  L1. Контекст: EMA27 > EMA200, EMA200 растёт.
  L2. Пока close >= EMA27, ведём бегущий МАКСИМУМ high.
  L3. Событие: close уходит НИЖЕ EMA27 -> максимум фиксируется как level
      (верхняя граница зоны).
  L4. Зона активна, пока close < level и low не дошёл до EMA200.
  L5. Исходы: breakout (close > level) | ema200 (low <= EMA200)
      | context (EMA27 <= EMA200).

ШОРТ — зеркально:
  S1. Контекст: EMA27 < EMA200, EMA200 падает.
  S2. Пока close <= EMA27, ведём бегущий МИНИМУМ low.
  S3. Событие: close уходит ВЫШЕ EMA27 -> минимум фиксируется как level
      (нижняя граница зоны).
  S4. Зона активна, пока close > level и high не дошёл до EMA200.
  S5. Исходы: breakout (close < level) | ema200 (high >= EMA200)
      | context (EMA27 >= EMA200).

Реализация общая: для шорта все цены и средние отражаются знаком, после чего
работает та же логика. Подбираемых порогов нет, кроме min_bars.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from zones import add_features, load

MIN_BARS = 3
WARMUP = 31


def detect(df: pd.DataFrame, side: str = "long", min_bars: int = MIN_BARS,
           require_slope: bool = True) -> pd.DataFrame:
    """side='long'|'short'. Возвращает размеченные зоны."""
    s = 1.0 if side == "long" else -1.0

    # Отражение: для шорта максимум становится минимумом и наоборот.
    close = s * df["close"].to_numpy()
    hi = s * (df["high"] if side == "long" else df["low"]).to_numpy()
    lo = s * (df["low"] if side == "long" else df["high"]).to_numpy()
    e27 = s * df["ema27"].to_numpy()
    e200 = s * df["ema200"].to_numpy()
    slope = s * df["slope200"].to_numpy()

    zones = []
    total = len(df)
    run_ext = -np.inf          # бегущий экстремум в отражённых координатах
    i = WARMUP

    while i < total - 1:
        if close[i] >= e27[i]:
            run_ext = max(run_ext, hi[i])
            i += 1
            continue

        ctx = e27[i] > e200[i] and np.isfinite(slope[i])
        if require_slope:
            ctx = ctx and slope[i] > 0
        if not (ctx and np.isfinite(run_ext) and run_ext > close[i]):
            run_ext = -np.inf
            i += 1
            continue

        t0, level = i, run_ext
        corridor0 = abs(e27[t0] - e200[t0]) / abs(e200[t0]) * 100
        j, outcome, end, depth = t0 + 1, None, None, 0.0

        while j < total:
            if e27[j] <= e200[j]:
                outcome, end = "context", j
                break
            if lo[j] <= e200[j]:
                outcome, end, depth = "ema200", j, 1.0
                break
            depth = max(depth, (e27[j] - lo[j]) / (e27[j] - e200[j]))
            if close[j] > level:
                outcome, end = "breakout", j
                break
            j += 1

        if end is None:
            break

        bars = end - t0
        if bars >= min_bars:
            seg = slice(t0, end + 1)
            zones.append({
                "side": side,
                "start": df["timestamp_utc"].iloc[t0],
                "end": df["timestamp_utc"].iloc[end],
                "bars": bars,
                "outcome": outcome,
                "level": s * level,
                "depth": min(depth, 1.0),
                # размах зоны в % — в исходных, неотражённых ценах
                "range_pct": (df["high"].to_numpy()[seg].max()
                              - df["low"].to_numpy()[seg].min())
                             / df["close"].to_numpy()[seg].mean() * 100,
                "corridor_t0": corridor0,
                "start_idx": t0,
                "end_idx": end,
            })
        run_ext = -np.inf
        i = end + 1

    return pd.DataFrame(zones)


def summary(z: pd.DataFrame, label: str) -> None:
    if z.empty:
        print(f"{label}: зон не найдено")
        return
    vc = z.outcome.value_counts()
    br = vc.get("breakout", 0)
    print(f"{label}: {len(z):4d} зон | breakout {br:3d} ({100*br/len(z):3.0f}%) | "
          f"ema200 {vc.get('ema200', 0):3d} | context {vc.get('context', 0):3d} | "
          f"баров мед {z.bars.median():4.0f} (p90 {z.bars.quantile(.9):4.0f}) | "
          f"размах мед {z.range_pct.median():5.1f}% | коридор мед {z.corridor_t0.median():5.1f}%")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="4h")
    p.add_argument("--suffix", default="_ext", help="_ext = период по 2025 вкл.")
    p.add_argument("--side", default="both", choices=["long", "short", "both"])
    p.add_argument("--min-bars", type=int, default=MIN_BARS)
    p.add_argument("--list", action="store_true", help="печатать все зоны")
    args = p.parse_args(argv)

    df = add_features(load(args.tf, args.suffix))
    sides = ["long", "short"] if args.side == "both" else [args.side]
    out = []
    for side in sides:
        z = detect(df, side, args.min_bars)
        summary(z, f"{args.tf} {side:5}")
        out.append(z)

    if args.list:
        pd.set_option("display.width", 220)
        allz = pd.concat(out).sort_values("start")
        cols = ["side", "start", "end", "bars", "outcome", "level", "depth",
                "range_pct", "corridor_t0"]
        print()
        print(allz[cols].to_string(index=False, float_format=lambda v: f"{v:7.2f}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
