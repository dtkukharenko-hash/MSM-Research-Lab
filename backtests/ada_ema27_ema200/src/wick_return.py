"""Проверка гипотезы о возврате в тень после резкого прокола.

Формулировка: было резкое движение вниз, но оно не закрепилось — был откат
внутри той же свечи (длинная нижняя тень). Решение принимается на следующей,
зелёной свече. Утверждение: цена должна вернуться в тень хотя бы наполовину.

Событие t:
  нижняя тень = min(open, close) - low, доминирует в баре (>= WICK_FRAC размаха)
  и по масштабу не меньше ATR_MULT * ATR(t-1) — «резкость»;
  бар t+1 зелёный (close > open) — это бар решения.
Отсчёт от close[t+1], будущее читается с бара t+2. Заглядывания нет.

Цели: half = (min(open,close)[t] + low[t]) / 2, full = low[t].

Два контроля — без них цифра бессмысленна, потому что на волатильном рынке
цена рано или поздно доходит до любого уровня в паре процентов:
  UP   — симметричная цель вверх на том же расстоянии от той же точки;
  BASE — та же цель вниз на d%, усреднённая по всем барам выборки
         (безусловная вероятность такого хода за тот же горизонт).

Результат: гипотеза не подтверждается. См. блок ВЫВОД внизу файла.
"""

from __future__ import annotations

import argparse
from math import comb

import numpy as np
import pandas as pd

from zones import add_features, load

WICK_FRAC = 0.5        # доля нижней тени в размахе бара
ATR_MULT = 1.0         # тень в ATR предыдущего бара
HORIZONS = (5, 10, 20, 50)
WARMUP = 31


def future_extremes(df: pd.DataFrame, hz: int) -> tuple[np.ndarray, np.ndarray]:
    """min(low) и max(high) на окне [i+1, i+hz]; NaN там, где окно не помещается."""
    n = len(df)
    fmin = np.full(n, np.nan)
    fmax = np.full(n, np.nan)
    rmin = df["low"].rolling(hz).min().to_numpy()
    rmax = df["high"].rolling(hz).max().to_numpy()
    fmin[: n - hz] = rmin[hz:]
    fmax[: n - hz] = rmax[hz:]
    return fmin, fmax


def build_events(df: pd.DataFrame, wick_frac: float = WICK_FRAC,
                 atr_mult: float = ATR_MULT, target: str = "half") -> pd.DataFrame:
    o, h, lo, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e27, e200, slope = (df[k].to_numpy() for k in ("ema27", "ema200", "slope200"))
    atr_prev = df["atr"].shift(1).to_numpy()
    body_lo = np.minimum(o, c)
    wick = body_lo - lo
    rng = h - lo

    idx = []
    for t in range(WARMUP, len(df) - 2):
        if rng[t] <= 0 or not np.isfinite(atr_prev[t]):
            continue
        if wick[t] / rng[t] < wick_frac or wick[t] < atr_mult * atr_prev[t]:
            continue
        if c[t + 1] <= o[t + 1]:          # решение — только на зелёной свече
            continue
        tgt = (body_lo[t] + lo[t]) / 2.0 if target == "half" else lo[t]
        if tgt >= c[t + 1]:               # цель уже пройдена — не событие
            continue
        idx.append(t)

    if not idx:
        return pd.DataFrame()
    idx = np.array(idx)
    tgt = (body_lo[idx] + lo[idx]) / 2.0 if target == "half" else lo[idx]
    ref = c[idx + 1]
    return pd.DataFrame({
        "t": idx,
        "ts": df["timestamp_utc"].to_numpy()[idx],
        "ref": ref,
        "d": (ref - tgt) / ref,           # расстояние до цели, доля
        "wick_atr": wick[idx] / atr_prev[idx],
        "long_ctx": (e27[idx] > e200[idx]) & np.isfinite(slope[idx]) & (slope[idx] > 0),
        "below27": c[idx] < e27[idx],
    })


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) при X ~ Bin(n, p) — односторонний тест против базлайна."""
    return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))


def analyse(df: pd.DataFrame, ev: pd.DataFrame, label: str) -> None:
    if ev.empty:
        print(f"\n{label}: событий нет")
        return
    c = df["close"].to_numpy()
    print(f"\n{label}: n={len(ev)} | тень мед {ev.wick_atr.median():.1f}xATR | "
          f"расстояние до цели мед {100 * ev.d.median():.2f}%")
    print(f"{'гор.':>5} | {'событие':>8} {'контроль↑':>10} {'базлайн':>8} | "
          f"{'лифт':>6} | {'p':>6}")
    for hz in HORIZONS:
        fmin, fmax = future_extremes(df, hz)
        j = ev.t.to_numpy() + 1
        ok = np.isfinite(fmin[j])
        if not ok.any():
            continue
        j, ref, d = j[ok], ev.ref.to_numpy()[ok], ev.d.to_numpy()[ok]
        hit = float((fmin[j] <= ref * (1 - d)).mean())
        hit_up = float((fmax[j] >= ref * (1 + d)).mean())
        valid = np.isfinite(fmin)
        base = float(np.mean([(fmin[valid] <= c[valid] * (1 - dd)).mean() for dd in d]))
        n = len(j)
        p = binom_sf(int(round(hit * n)), n, base)
        print(f"{hz:>5} | {100 * hit:7.0f}% {100 * hit_up:9.0f}% {100 * base:7.0f}% | "
              f"{hit / max(base, 1e-9):5.2f}x | {p:6.3f}")


def sweep(df: pd.DataFrame, hz: int = 20) -> None:
    """Развёртка по порогам «резкости» — эффект не должен жить на одном пороге."""
    print(f"\n  пороги, подмножество «старт зоны», горизонт {hz}:")
    fmin, fmax = future_extremes(df, hz)
    for wf in (0.4, 0.5, 0.6):
        for am in (0.8, 1.0, 1.5, 2.0):
            ev = build_events(df, wf, am)
            if ev.empty:
                continue
            ev = ev[ev.long_ctx & ev.below27]
            if ev.empty:
                continue
            j = ev.t.to_numpy() + 1
            ok = np.isfinite(fmin[j])
            j, ref, d = j[ok], ev.ref.to_numpy()[ok], ev.d.to_numpy()[ok]
            if len(j) < 5:
                print(f"    тень>={wf} ATR>={am}: n={len(j)} — мало")
                continue
            dn = 100 * (fmin[j] <= ref * (1 - d)).mean()
            up = 100 * (fmax[j] >= ref * (1 + d)).mean()
            print(f"    тень>={wf} ATR>={am}: n={len(j):3d} | "
                  f"вниз {dn:3.0f}% против вверх {up:3.0f}%")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="both", choices=["4h", "1h", "both"])
    p.add_argument("--suffix", default="", help="'' = 2023-07..2024-12, '_ext' = по 2025")
    p.add_argument("--target", default="half", choices=["half", "full"])
    args = p.parse_args(argv)

    tfs = ["4h", "1h"] if args.tf == "both" else [args.tf]
    for tf in tfs:
        df = add_features(load(tf, args.suffix))
        head = (f"=== {tf} | {df.timestamp_utc.iloc[0].date()}"
                f"..{df.timestamp_utc.iloc[-1].date()} | {len(df)} баров ===")
        print("\n" + "=" * len(head) + f"\n{head}\n" + "=" * len(head))
        ev = build_events(df, target=args.target)
        analyse(df, ev, f"все проколы (тень>={WICK_FRAC} бара, >={ATR_MULT} ATR)")
        analyse(df, ev[ev.long_ctx & ev.below27],
                "лонг-контекст + close<EMA27 (старт зоны)")
        sweep(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ВЫВОД (4h и 1h, 2023-07-01..2024-12-31)
#
# 1. В буквальной формулировке гипотеза неопровержима и потому бесполезна.
#    Возврат на половину тени «когда-нибудь» случается в 98-100% случаев,
#    но зеркальный ход вверх на то же расстояние — в 95-100%. Без горизонта
#    это свойство волатильности ADA, а не свойство прокола.
#
# 2. С горизонтом эффект от шума не отличается. Лифт над безусловным
#    базлайном 1.0-1.35x, p от 0.04 до 0.75 на 8 проверенных ячейках —
#    ровно столько значимых, сколько даёт случай при таком числе проверок.
#    Единственная ячейка p<0.05 (1h, все проколы, H=20, p=0.039) поправку
#    на множественность не переживает.
#
# 3. Асимметрия «вниз чаще, чем вверх» в подмножестве «старт зоны» есть и
#    по знаку устойчива (4h: 70-80% против 40-60%; 1h: 73-79% против 45-48%),
#    но выборка 7-44 события — мощности не хватает.
#
# 4. Главное возражение по существу: эффект СЛАБЕЕТ с ростом резкости.
#    1h, тень>=0.4: ATR>=0.8 даёт 70% против 54%, ATR>=1.5 уже 50% против 50%,
#    ATR>=2.0 — 38% против 62%, то есть знак переворачивается. Гипотеза была
#    именно про резкое движение, а на самых резких проколах она не работает.
#    Это довод против правила, а не нехватка данных.
