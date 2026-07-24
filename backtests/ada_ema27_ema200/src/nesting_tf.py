"""Какой младший ТФ лучше разрешает боковик 4h: 15m, 5m или 3m.

Владелец предложил взять вместо 15m более тонкий ТФ «для более точного
определения». Вопрос проверяемый: считаем одним и тем же детектором коридоров
(src/ranges.py) на 4h и на каждом младшем ТФ и смотрим, что лежит внутри
одного 4h-коридора.

Две метрики, за которыми стоит следить, тянут в разные стороны:

  РАЗРЕШЕНИЕ = ширина коридора 4h / ширина коридора младшего ТФ.
    Чем больше, тем тоньше младший ТФ режет 4h-коробку и тем меньше её
    высоты придётся отдать на подтверждение выхода. Больше — лучше.

  ОТНОШЕНИЕ ХОДА = ход между соседними коридорами младшего ТФ / высота
    коридора младшего ТФ. Это сигнал к шуму в его собственном масштабе.
    Если рынок самоподобен, отношение не меняется с ТФ, и тонкий ТФ даёт
    только больше объектов, а не больше информации. Если растёт — тонкий ТФ
    действительно лучше. Если падает — на тонком ТФ структура тонет в шуме.

Оговорка по данным: 3m и 5m в DATA-002 отсутствуют (нативный источник там
15m), они выкачаны напрямую с Bybit и валидации DATA-002 за собой не несут.
Поэтому здесь же печатается проверка на гэпы и дубликаты.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from ranges import W, coverage, detect
from zones import add_features, load

STEP = {"3m": pd.Timedelta(minutes=3), "5m": pd.Timedelta(minutes=5),
        "15m": pd.Timedelta(minutes=15), "1h": pd.Timedelta(hours=1),
        "4h": pd.Timedelta(hours=4)}


def audit(df: pd.DataFrame, tf: str) -> str:
    """Гэпы и дубликаты: у 3m/5m нет пометки DATA-002, проверяем сами."""
    d = df.timestamp_utc.diff().dropna()
    step = STEP[tf]
    gaps = int((d != step).sum())
    dups = int(df.timestamp_utc.duplicated().sum())
    bad = int((df.high < df.low).sum() + (df.close > df.high).sum()
              + (df.close < df.low).sum())
    return (f"{len(df):7d} баров | {df.timestamp_utc.iloc[0]:%Y-%m-%d}.."
            f"{df.timestamp_utc.iloc[-1]:%Y-%m-%d} | гэпов {gaps} | "
            f"дублей {dups} | битых OHLC {bad}")


def nest(z_slow: pd.DataFrame, z_fast: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in z_slow.itertuples():
        inner = (z_fast[(z_fast.start >= r.start) & (z_fast.end <= r.end)]
                 .reset_index(drop=True))
        moves = []
        for k in range(len(inner) - 1):
            a, b = inner.iloc[k], inner.iloc[k + 1]
            lo, hi = min(a.bot, b.bot), max(a.top, b.top)
            moves.append((hi - lo) / ((hi + lo) / 2) * 100)
        rows.append({
            "w_slow": r.width,
            "cnt": len(inner),
            "w_fast": inner.width.median() if len(inner) else np.nan,
            "move": np.median(moves) if moves else np.nan,
        })
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fast", default="15m,5m,3m")
    p.add_argument("--w", type=int, default=W)
    args = p.parse_args(argv)
    fast_tfs = [t.strip() for t in args.fast.split(",")]

    d4 = add_features(load("4h"))
    z4 = detect(d4, w=args.w)
    print("=== данные ===")
    print(f"  4h : {audit(d4, '4h')}")

    fast: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for tf in fast_tfs:
        try:
            d = add_features(load(tf))
        except FileNotFoundError as e:
            print(f"  {tf:3}: НЕТ ДАННЫХ — {e}")
            continue
        print(f"  {tf:3}: {audit(d, tf)}")
        fast[tf] = (d, detect(d, w=args.w))

    print(f"\n=== разметка коридоров, w={args.w} ===")
    print(f"  4h : {len(z4):5d} коридоров | покрытие {coverage(z4, len(d4)):4.1f}% | "
          f"баров мед {z4.bars.median():3.0f} | ширина мед {z4.width.median():5.2f}%")
    for tf, (d, z) in fast.items():
        print(f"  {tf:3}: {len(z):5d} коридоров | покрытие {coverage(z, len(d)):4.1f}% | "
              f"баров мед {z.bars.median():3.0f} | ширина мед {z.width.median():5.2f}%")

    print(f"\n=== что лежит внутри одного 4h-коридора ({len(z4)} шт) ===")
    print(f"{'ТФ':>4} {'коридоров':>10} {'ширина ТФ':>10} {'РАЗРЕШЕНИЕ':>11} "
          f"{'ход':>7} {'ОТНОШЕНИЕ ХОДА':>15} {'пусто':>6}")
    for tf, (_, zf) in fast.items():
        n = nest(z4, zf)
        w_fast = n.w_fast.median()
        move = n.move.median()
        print(f"{tf:>4} {n.cnt.median():10.0f} {w_fast:9.2f}% "
              f"{z4.width.median() / w_fast:10.1f}x {move:6.2f}% "
              f"{move / w_fast:14.2f} {int((n.cnt == 0).sum()):6d}")
    print("\nРАЗРЕШЕНИЕ — во сколько раз 4h-коридор шире коридора младшего ТФ.")
    print("ОТНОШЕНИЕ ХОДА — ход между соседними коридорами в высотах коридора.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
