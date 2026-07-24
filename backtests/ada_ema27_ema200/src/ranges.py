"""Боковик как коридор между экстремумами. Проверка трёх трактовок и вложенности.

Постановка владельца ветки: движение на 4h — это перемещение цены от боковика
к боковику; боковик сам по себе неопределённость, решение принимать негде.
Значит размечать надо боковики, а движение получается как то, что между ними.

Проверены три несовместимые трактовки «боковика» против пяти прямоугольников,
размеченных вручную на 4h (декабрь 2023 — июнь 2024, файл ada_4h_3.png):

  1. СЖАТИЕ. comp = размах / (ATR% * sqrt(n)) — сколько цена натоптала
     относительно ожидаемого размаха случайного блуждания той же длины.
     Порогов не содержит. Жадный поиск минимумов нашёл бокс E (перекрытие 94%,
     2-е место по сжатию за 2.5 года) и не нашёл A, B, C, D вообще.

  2. ЧИСЛО ПЕРЕСЕЧЕНИЙ EMA27 за окно. Не разделяет: боксы легли на 41, 50, 86,
     95 и 98-й перцентиль фона — то есть где угодно.

  3. КОРИДОР МЕЖДУ ЭКСТРЕМУМАМИ (этот файл). Границы — последний подтверждённый
     свинг-хай и свинг-лоу, коридор живёт, пока close внутри, выход закрытием
     закрывает боковик и начинает движение.

Третья трактовка выиграла, но не сразу: при w=3 она воспроизводила только бокс A,
а B, C, D, E дробила на 5-11 осколков. Дробление оказалось не дефектом, а
ВЛОЖЕННОСТЬЮ: крупный боковик состоит из мелких, ровно как боковик 4h состоит
из боковиков 15m. Масштаб задаётся окном свинга w, и на w=18 все пять
прямоугольников собираются в один коридор каждый.

Роль EMA27 (владелец просил строить на ней): быстрая средняя обязана лежать
ВНУТРИ коридора. В боковике она через него проходит, в тренде уводит цену за
границу. Условие бинарное, порога не содержит.

Что здесь ПОДОБРАНО и требует честной оговорки: w=18 выбрано по максимуму
согласия с пятью прямоугольниками, чьи даты сняты с картинки на глаз. Пять
шумных точек — слишком мало, чтобы фиксировать параметр. Устойчиво не значение
w, а сам факт монотонного перехода: на w=3 не совпадает ничего, на w>=18
совпадает всё.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from zones import add_features, load

W = 18          # окно свинга: масштаб боковика. См. оговорку в докстринге.
MIN_BARS = 36   # 2*W — короче коридор не отличим от шума самого свинга
WARMUP = 31

# Прямоугольники, размеченные владельцем на 4h. Сняты с ada_4h_3.png и
# ada_4h_4..7.png по осям. Уровни границ проверены по барам: снятые с картинки
# значения отличаются от фактических high/low на 0.0001..0.0006, то есть
# владелец ставит границы ровно по свинг-экстремумам. Даты — +/- пара баров.
#
# Масштабы различаются в 20 раз (18 баров у G2 против 372 у E): владелец
# размечает на нескольких масштабах сразу, одним w это не покрыть.
# G1 и G2 — самые направленные из девяти (ER 0.42 и 0.33 против 0.03..0.08
# у настоящих боковиков), владелец сам пометил G2 как спорный.
BOXES = {
    "F1": ("2023-10-02", "2023-10-09"),
    "F2": ("2023-10-13", "2023-10-21"),
    "A": ("2023-11-12", "2023-12-03"),
    "B": ("2023-12-14", "2024-01-04"),
    # G1/G2 — по ada_4h_8.png. Первый вариант (ada_4h_7.png) владелец назвал
    # подтянутым «чтобы улучшить результат»; честная перестройка оказалась
    # ЕЩЁ менее похожей на боковик: ER 0.42->0.47 и 0.33->0.43. Оставлены как
    # контрпримеры: это паузы внутри хода, а не боковики.
    "G1": ("2024-01-08", "2024-01-10"),
    "G2": ("2024-01-11", "2024-01-14"),
    "C": ("2024-01-24", "2024-02-11"),
    "D": ("2024-03-19", "2024-04-12"),
    "E": ("2024-04-13", "2024-06-13"),
}


def swings(h: np.ndarray, l: np.ndarray, w: int) -> tuple[np.ndarray, np.ndarray]:
    """Свинг на баре k — экстремум в окне +/-w. Подтверждается только на k+w."""
    hs = pd.Series(h).rolling(2 * w + 1, center=True).max().to_numpy()
    ls = pd.Series(l).rolling(2 * w + 1, center=True).min().to_numpy()
    ok_h, ok_l = np.isfinite(hs), np.isfinite(ls)
    is_sh, is_sl = np.zeros(len(h), bool), np.zeros(len(h), bool)
    is_sh[ok_h] = h[ok_h] >= hs[ok_h]
    is_sl[ok_l] = l[ok_l] <= ls[ok_l]
    return is_sh, is_sl


def detect(df: pd.DataFrame, w: int = W, min_bars: int | None = None,
           need_e27: bool = True) -> pd.DataFrame:
    """Коридоры между экстремумами. Заглядывания нет: свинг бара k доступен с k+w."""
    if min_bars is None:
        min_bars = max(MIN_BARS, 2 * w)
    h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    e27 = df.ema27.to_numpy()
    is_sh, is_sl = swings(h, l, w)
    n = len(df)
    out: list[dict] = []
    i, shi, sli = WARMUP, -1, -1

    while i < n:
        k = i - w
        if k >= 0:
            if is_sh[k]:
                shi = k
            if is_sl[k]:
                sli = k
        if shi < 0 or sli < 0:
            i += 1
            continue

        top, bot = h[shi], l[sli]
        # EMA27 обязана быть внутри коридора — иначе это не боковик, а тренд.
        if top <= bot or (need_e27 and not (bot <= e27[i] <= top)):
            i += 1
            continue

        t0 = min(shi, sli)
        j = i
        while j < n and bot <= c[j] <= top:
            j += 1
        if j >= n:
            break

        if j - t0 >= min_bars:
            seg = slice(t0, j + 1)
            out.append({
                "start": df.timestamp_utc.iloc[t0],
                "end": df.timestamp_utc.iloc[j],
                "bars": j - t0,
                "top": top,
                "bot": bot,
                "width": (top - bot) / ((top + bot) / 2) * 100,
                # куда цена вышла из коридора — это и есть начало движения
                "exit": "вверх" if c[j] > top else "вниз",
                # какую долю высоты коридора проходит EMA27: в боковике мало
                "e27_span": (e27[seg].max() - e27[seg].min()) / (top - bot) * 100,
                "start_idx": t0,
                "end_idx": j,
            })
            shi = sli = -1
            i = j + 1
        else:
            i += 1

    return pd.DataFrame(out)


def coverage(z: pd.DataFrame, total: int) -> float:
    if z.empty:
        return 0.0
    return 100.0 * sum(int(r.end_idx) - int(r.start_idx) + 1
                       for r in z.itertuples()) / total


def box_index(ts: pd.Series) -> dict[str, tuple[int, int]]:
    return {k: (int(ts.searchsorted(pd.Timestamp(a, tz="UTC"))),
                int(ts.searchsorted(pd.Timestamp(b, tz="UTC") + pd.Timedelta("1D"))) - 1)
            for k, (a, b) in BOXES.items()}


def sweep(df: pd.DataFrame, widths: tuple[int, ...]) -> None:
    """Как масштаб w меняет разметку и согласие с ручными прямоугольниками.

    Метрика — IoU (пересечение / объединение по барам), а не доля покрытия
    бокса. Односторонняя доля льстит: коридор вчетверо длиннее бокса накрывает
    его на 100%, хотя разметки не воспроизводит.
    """
    idx = box_index(df.timestamp_utc)
    print(f"{'w':>3} {'коридоров':>10} {'покрытие':>9} {'баров мед':>10} "
          f"{'ширина мед':>11}   IoU с боксом, %")
    print(f"{'':>3} {'':>10} {'':>9} {'':>10} {'':>11}   "
          + " ".join(f"{k:>5}" for k in BOXES))
    for w in widths:
        z = detect(df, w=w)
        if z.empty:
            print(f"{w:3d}  коридоров нет")
            continue
        cells = []
        for _, (a, b) in idx.items():
            hit = z[(z.start_idx <= b) & (z.end_idx >= a)]
            if hit.empty:
                cells.append(f"{'—':>5}")
                continue
            inter = np.minimum(b, hit.end_idx) - np.maximum(a, hit.start_idx) + 1
            union = np.maximum(b, hit.end_idx) - np.minimum(a, hit.start_idx) + 1
            cells.append(f"{(inter / union * 100).max():5.0f}")
        print(f"{w:3d} {len(z):10d} {coverage(z, len(df)):8.1f}% "
              f"{z.bars.median():10.0f} {z.width.median():10.1f}%   "
              + " ".join(cells))


def nesting(df_slow: pd.DataFrame, df_fast: pd.DataFrame,
            w_slow: int, w_fast: int, names: tuple[str, str]) -> None:
    """Тезис владельца: боковик старшего ТФ — это движение на младшем."""
    zs, zf = detect(df_slow, w=w_slow), detect(df_fast, w=w_fast)
    for nm, z, d in ((names[0], zs, df_slow), (names[1], zf, df_fast)):
        print(f"{nm:>4}: {len(z):4d} коридоров | покрытие {coverage(z, len(d)):4.1f}% | "
              f"баров мед {z.bars.median():3.0f} | ширина мед {z.width.median():4.1f}%")

    rows = []
    for r in zs.itertuples():
        inner = zf[(zf.start >= r.start) & (zf.end <= r.end)].reset_index(drop=True)
        moves = []
        for k in range(len(inner) - 1):
            a, b = inner.iloc[k], inner.iloc[k + 1]
            lo, hi = min(a.bot, b.bot), max(a.top, b.top)
            moves.append((hi - lo) / ((hi + lo) / 2) * 100)
        rows.append((r.width, len(inner),
                     inner.width.median() if len(inner) else np.nan,
                     np.median(moves) if moves else np.nan))
    n = pd.DataFrame(rows, columns=["w_slow", "cnt", "w_fast", "move"])
    print(f"\nвнутри одного коридора {names[0]}:")
    print(f"  коридоров {names[1]}: медиана {n.cnt.median():.0f}, "
          f"p90 {n.cnt.quantile(.9):.0f}, пусто у {(n.cnt == 0).sum()} из {len(n)}")
    print(f"  ширина {names[0]} {n.w_slow.median():.1f}% против "
          f"{names[1]} {n.w_fast.median():.1f}% — в "
          f"{n.w_slow.median() / n.w_fast.median():.1f} раза шире")
    print(f"  ход между соседними коридорами {names[1]}: "
          f"медиана {n.move.median():.1f}% — это "
          f"{n.move.median() / n.w_fast.median():.1f} высоты коридора {names[1]}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="4h")
    p.add_argument("--suffix", default="_ext")
    p.add_argument("--w", type=int, default=W)
    p.add_argument("--sweep", action="store_true", help="перебрать масштаб w")
    p.add_argument("--nesting", action="store_true",
                   help="проверить вложенность 4h/15m (исходный период)")
    p.add_argument("--list", action="store_true")
    args = p.parse_args(argv)

    if args.nesting:
        nesting(add_features(load("4h")), add_features(load("15m")),
                W, W, ("4h", "15m"))
        return 0

    df = add_features(load(args.tf, args.suffix))
    if args.sweep:
        sweep(df, (3, 5, 8, 12, 18, 25, 35))
        return 0

    z = detect(df, w=args.w)
    print(f"{args.tf} w={args.w}: {len(z)} коридоров | "
          f"покрытие {coverage(z, len(df)):.1f}% | "
          f"баров мед {z.bars.median():.0f} (p90 {z.bars.quantile(.9):.0f}) | "
          f"ширина мед {z.width.median():.1f}% "
          f"(p10 {z.width.quantile(.1):.1f}, p90 {z.width.quantile(.9):.1f}) | "
          f"выход вверх {(z.exit == 'вверх').sum()}, вниз {(z.exit == 'вниз').sum()}")
    print(f"EMA27 проходит {z.e27_span.median():.0f}% высоты коридора (медиана)")

    if args.list:
        pd.set_option("display.width", 200)
        cols = ["start", "end", "bars", "bot", "top", "width", "exit", "e27_span"]
        print()
        print(z[cols].to_string(index=False, float_format=lambda v: f"{v:7.3f}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
