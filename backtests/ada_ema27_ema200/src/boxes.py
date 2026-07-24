"""Прямоугольник по определению владельца: границы — наиболее посещаемые уровни.

Формулировка, выбранная владельцем и проверенная в notes/ranges.md:

  Прямоугольник — участок, на котором EMA27 проходит внутри, а верхняя и
  нижняя границы заданы наиболее посещаемыми уровнями, к каждому из которых
  цена подходила раздельно два и более раз. Прокол границы тенью или отдельным
  закрытием прямоугольник не отменяет, пока цена к границе возвращается.
  Прямоугольник кончается, когда цена ушла за границу и не вернулась.

Отличие от ranges.py принципиальное. Там граница строилась от ЭКСТРЕМУМА ноги
(с отсечкой изолированного прокола, с поиском «второго типа якоря»), и каждый
трудный случай требовал отдельной заплатки. Здесь экстремум границу не задаёт
вовсе: он лишь выдвигает кандидата, а уровнем тот становится, только когда к
нему вернулись. Проверка на краевых уровнях показала, что владелец выбирает не
самый непробиваемый уровень (медиана перцентиля 0%), а самый посещаемый
(медиана 81%).

Одним этим правилом объясняются пять случаев, которые раньше чинились по
отдельности: изолированный прокол (один визит), обвал 05.03.2024 (один визит
длиной 15 минут), низ G2 (четыре визита, хотя не экстремум ноги), полоса из
восьми лоёв в прямоугольнике 3 (граница там, где скучились визиты) и сама
проницаемость границы (самый посещаемый уровень заведомо не самый крайний).

Ретроспективность встроена в определение: прямоугольника не существует, пока
не случился второй подход. Колонка `known` хранит бар, на котором он стал
известен, `start` — бар, которым он рисуется задним числом.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from zones import add_features, load

TOL = 0.5        # окрестность уровня, % — из проверки в notes/ranges.md
MIN_VISITS = 2   # «два и более раза» — прямо из определения
LOOKBACK = 200   # сколько баров назад кандидат остаётся живым
GRACE = 13       # баров вне границы до смерти: p90 возвращающихся выходов
MIN_BARS = 12
WARMUP = 31


class Level:
    """Кандидат в границы. Уровнем становится на MIN_VISITS-м визите."""

    __slots__ = ("price", "kind", "born", "visits", "inside", "active_at")

    def __init__(self, price: float, kind: str, born: int):
        self.price = price
        self.kind = kind          # 'sup' — снизу, 'res' — сверху
        self.born = born
        self.visits = 1           # бар рождения — первый визит
        self.inside = True        # цена сейчас в окрестности
        self.active_at = -1       # бар, на котором визитов стало MIN_VISITS

    def touch(self, ext: float, i: int, tol: float) -> None:
        near = abs(ext - self.price) / self.price * 100 <= tol
        if near and not self.inside:
            self.visits += 1
            if self.visits == MIN_VISITS:
                self.active_at = i
        self.inside = near


def detect(df: pd.DataFrame, tol: float = TOL, lookback: int = LOOKBACK,
           grace: int = GRACE, min_bars: int = MIN_BARS) -> pd.DataFrame:
    """Прямоугольники. Заглядывания нет: уровень активируется на своём втором
    визите, прямоугольник открывается не раньше, чем активны обе границы."""
    h, l, c = (df[k].to_numpy() for k in ("high", "low", "close"))
    e27 = df.ema27.to_numpy()
    n = len(df)

    sup: list[Level] = []
    res: list[Level] = []
    out: list[dict] = []

    in_box = False
    bot = top = np.nan
    t0 = known = -1
    outside = 0          # закрытий подряд вне границ

    for i in range(WARMUP, n):
        for lv in sup:
            lv.touch(l[i], i, tol)
        for lv in res:
            lv.touch(h[i], i, tol)

        if in_box:
            if bot <= c[i] <= top:
                outside = 0
            else:
                outside += 1
                if outside > grace:
                    # Цена ушла и не вернулась — прямоугольник кончился.
                    end = i - outside
                    if end - t0 >= min_bars:
                        seg = slice(t0, end + 1)
                        out.append({
                            "start": df.timestamp_utc.iloc[t0],
                            "known": df.timestamp_utc.iloc[known],
                            "end": df.timestamp_utc.iloc[end],
                            "bars": end - t0,
                            "bot": bot, "top": top,
                            "width": (top - bot) / ((top + bot) / 2) * 100,
                            "exit": "вниз" if c[i] < bot else "вверх",
                            "start_idx": t0, "end_idx": end,
                        })
                    in_box, outside = False, 0
        else:
            # Действующие уровни: снизу и сверху от цены, EMA27 между ними.
            lo_c = [x for x in sup if 0 <= x.active_at <= i
                    and x.price < e27[i] and i - x.born <= lookback]
            hi_c = [x for x in res if 0 <= x.active_at <= i
                    and x.price > e27[i] and i - x.born <= lookback]
            if lo_c and hi_c:
                # Самый посещаемый; при равенстве — ближайший к цене.
                b = max(lo_c, key=lambda x: (x.visits, x.price))
                t = max(hi_c, key=lambda x: (x.visits, -x.price))
                if b.price <= c[i] <= t.price:
                    in_box, bot, top = True, b.price, t.price
                    known = i
                    # Начало — не рождение уровня, а бар, с которого цена уже
                    # держится между границами. Иначе прямоугольник датируется
                    # задолго до того, как в нём что-то происходит: при отсчёте
                    # от рождения уровня медиана длины выходила 210 баров при
                    # запаздывании 144, то есть коробка почти целиком лежала
                    # в прошлом, невидимом в момент открытия.
                    t0 = i
                    while (t0 > WARMUP and bot <= c[t0 - 1] <= top
                           and i - t0 < lookback):
                        t0 -= 1
                    outside = 0

        sup.append(Level(l[i], "sup", i))
        res.append(Level(h[i], "res", i))
        if len(sup) > 2 * lookback:
            sup = [x for x in sup if i - x.born <= lookback]
            res = [x for x in res if i - x.born <= lookback]

    return pd.DataFrame(out)


def coverage(z: pd.DataFrame, total: int) -> float:
    if z.empty:
        return 0.0
    mask = np.zeros(total, bool)
    for r in z.itertuples():
        mask[int(r.start_idx):int(r.end_idx) + 1] = True
    return 100.0 * mask.sum() / total


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="4h")
    p.add_argument("--suffix", default="_ext")
    p.add_argument("--tol", type=float, default=TOL)
    p.add_argument("--grace", type=int, default=GRACE)
    p.add_argument("--list", action="store_true")
    args = p.parse_args(argv)

    df = add_features(load(args.tf, args.suffix))
    z = detect(df, tol=args.tol, grace=args.grace)
    if z.empty:
        print("прямоугольников не найдено")
        return 0
    lag = (z.known - z.start).dt.total_seconds() / 3600 / 4
    print(f"{args.tf} tol={args.tol}% grace={args.grace}: {len(z)} прямоугольников | "
          f"покрытие {coverage(z, len(df)):.1f}% | "
          f"баров мед {z.bars.median():.0f} (p90 {z.bars.quantile(.9):.0f}) | "
          f"ширина мед {z.width.median():.1f}% | "
          f"выход вверх {(z.exit == 'вверх').sum()}, вниз {(z.exit == 'вниз').sum()}")
    print(f"запаздывание (бар известности минус бар начала): "
          f"медиана {lag.median():.0f} баров, p90 {lag.quantile(.9):.0f}")
    if args.list:
        pd.set_option("display.width", 200)
        cols = ["start", "known", "end", "bars", "bot", "top", "width", "exit"]
        print()
        print(z[cols].to_string(index=False, float_format=lambda v: f"{v:7.4f}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
