"""Побарный эмулятор ada_boxes.pine — сверка порта с pivots.py и ranges.py.

Тот же приём, что вскрыл правило L3a при сверке ada_zones_long.pine: Pine не
умеет смотреть вперёд и держит состояние иначе, чем питон, поэтому совпадение
результата надо доказывать, а не предполагать.

Эмулятор повторяет логику Pine буквально, включая порядок проверок, и
запускается на тех же данных. Расхождения печатаются с указанием бара.

Оговорка о разогреве: на графике TradingView ta.ema(close, 200) считается от
первого бара графика и первые ~200 баров смещена, тогда как в CSV колонки
ema27/ema200 посчитаны на расширенном окне и смещения не имеют. Эмулятор
использует колонки из CSV, то есть проверяет ЛОГИКУ, а не разогрев. На живом
графике держите слева запас минимум в 600 баров.
"""

from __future__ import annotations

import argparse
import math

import numpy as np
import pandas as pd

from pivots import CONFIRM_BARS, ISO_ATR, WARMUP, pivots
from ranges import detect as ranges_detect
from zones import add_features, load


def pine_pivots(df: pd.DataFrame, confirm_bars: int = CONFIRM_BARS,
                iso_atr: float = ISO_ATR) -> pd.DataFrame:
    """Буквальный перенос блока «ОПОРНЫЕ ЭКСТРЕМУМЫ» из ada_boxes.pine."""
    c, h, l = (df[k].to_numpy() for k in ("close", "high", "low"))
    e27, atr = df.ema27.to_numpy(), df.atr.to_numpy()
    nan = math.nan

    above = c[WARMUP] >= e27[WARMUP]
    idx1, val1, atr1 = WARMUP, (h if above else l)[WARMUP], atr[WARMUP]
    idx2, val2 = -1, nan
    run = 0
    out: list[dict] = []

    for i in range(WARMUP + 1, len(df)):
        v = h[i] if above else l[i]
        better = v > val1 if above else v < val1
        if better:
            idx2, val2 = idx1, val1
            idx1, val1, atr1 = i, v, atr[i]
        elif math.isnan(val2) or (v > val2 if above else v < val2):
            idx2, val2 = i, v

        if (c[i] >= e27[i]) == above:
            run = 0
            continue

        run += 1
        if run < confirm_bars:
            continue

        p_idx, p_val, iso = idx1, val1, False
        if (iso_atr > 0 and idx2 >= 0 and not math.isnan(val2)
                and abs(val1 - val2) > iso_atr * atr1):
            p_idx, p_val, iso = idx2, val2, True

        out.append({"kind": "high" if above else "low",
                    "time": df.timestamp_utc.iloc[p_idx],
                    "price": p_val, "isolated": iso, "idx": p_idx})

        above = not above
        idx1, val1, atr1 = i, (h[i] if above else l[i]), atr[i]
        idx2, val2 = -1, nan
        run = 0

    return pd.DataFrame(out)


def pine_boxes(df: pd.DataFrame, w: int, min_bars: int, grace: int,
               need_close_in: bool) -> pd.DataFrame:
    """Буквальный перенос блока «ПРЯМОУГОЛЬНИКИ» из ada_boxes.pine.

    need_close_in — открывать ли прямоугольник только когда close уже внутри
    границ. В Pine это условие есть, в ranges.detect его нет; параметр
    позволяет измерить, во что обходится разница.
    """
    c, h, l = (df[k].to_numpy() for k in ("close", "high", "low"))
    e27 = df.ema27.to_numpy()
    n = len(df)
    hs = pd.Series(h).rolling(2 * w + 1, center=True).max().to_numpy()
    ls = pd.Series(l).rolling(2 * w + 1, center=True).min().to_numpy()

    shi = sli = -1
    shp = slp = math.nan
    in_box = False
    b_top = b_bot = math.nan
    b_start = -1
    out_n = 0
    out: list[dict] = []

    for i in range(WARMUP, n):
        k = i - w
        if k >= 0 and np.isfinite(hs[k]) and h[k] >= hs[k]:
            shi, shp = k, h[k]
        if k >= 0 and np.isfinite(ls[k]) and l[k] <= ls[k]:
            sli, slp = k, l[k]

        if in_box:
            if b_bot <= c[i] <= b_top:
                out_n = 0
            else:
                out_n += 1
                if out_n > grace:
                    # end — ПЕРВЫЙ бар снаружи, как в ranges.detect: он входит
                    # в запись. Отсчёт от последнего бара внутри давал ошибку
                    # на единицу и менял проверку min_bars.
                    end = i - out_n + 1
                    if end - b_start >= min_bars:
                        out.append({"start": df.timestamp_utc.iloc[b_start],
                                    "end": df.timestamp_utc.iloc[end],
                                    "bars": end - b_start,
                                    "bot": b_bot, "top": b_top,
                                    "start_idx": b_start, "end_idx": end})
                    in_box, out_n = False, 0
                    shi = sli = -1
        elif shi >= 0 and sli >= 0 and shp > slp and slp <= e27[i] <= shp:
            if not need_close_in or slp <= c[i] <= shp:
                in_box = True
                b_top, b_bot = shp, slp
                b_start = min(shi, sli)
                out_n = 0

    return pd.DataFrame(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="4h")
    p.add_argument("--suffix", default="_ext")
    args = p.parse_args(argv)

    df = add_features(load(args.tf, args.suffix))
    print(f"{args.tf}{args.suffix}: {len(df)} баров")

    print("\n=== опорные экстремумы: Pine против pivots.py ===")
    for cb in (1, 2, 3):
        for iso in (0.0, ISO_ATR):
            pe = pine_pivots(df, cb, iso)
            py = pivots(df, cb, iso if iso > 0 else None)
            same = list(pe.idx) == list(py.idx)
            diff_price = 0
            if same and len(pe):
                diff_price = int((pe.price.to_numpy() != py.price.to_numpy()).sum())
            print(f"  cb={cb} iso={iso:.1f}: pine {len(pe):4d} | python {len(py):4d} | "
                  f"бары {'СОВПАЛИ' if same else 'РАЗОШЛИСЬ'} | "
                  f"расхождений по цене {diff_price}")
            if not same:
                a, b = set(pe.idx), set(py.idx)
                for k in sorted(a - b)[:3]:
                    print(f"      только pine : бар {k} {df.timestamp_utc.iloc[k]}")
                for k in sorted(b - a)[:3]:
                    print(f"      только python: бар {k} {df.timestamp_utc.iloc[k]}")

    print("\n=== прямоугольники: Pine против ranges.py ===")
    for w in (5, 8, 18):
        mb = max(36, 2 * w)
        py = ranges_detect(df, w=w, min_bars=mb)
        for need_in in (False, True):
            pe = pine_boxes(df, w, mb, 0, need_in)
            same = set(pe.start_idx) == set(py.start_idx) if len(pe) else not len(py)
            tag = "close внутри при открытии" if need_in else "как в ranges.py"
            print(f"  w={w:2d} [{tag:26}]: pine {len(pe):3d} | python {len(py):3d} | "
                  f"старты {'СОВПАЛИ' if same else 'РАЗОШЛИСЬ'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
