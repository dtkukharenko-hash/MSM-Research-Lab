"""Развилка в правиле L3: чем фиксировать level — максимумом всей ноги или
последним свинг-хаем перед уходом под EMA27.

Обе трактовки следуют из исходной формулировки «последний максимум до того,
как цена ушла за EMA27», и на трёх размеченных вручную зонах совпадают.
Расходятся, когда нога состоит из нескольких волн: 27.04.2025 даёт 0.7458
(максимум ноги, пик 24.04) против 0.7174 (последний свинг-хай 27.04).

  leg_max — бегущий максимум high за всё время над EMA27 (текущее поведение);
  swing   — последний ЛОКАЛЬНЫЙ максимум: high[i] >= max(high[i-w..i+w]),
            подтверждённый w барами справа строго ДО t0, иначе заглядывание.
            Если такого нет или он не выше close[t0] — откат к leg_max.

Меняется не только верхняя граница, но и исход: более низкий level ближе,
поэтому часть зон закрывается пробоем вверх там, где раньше доходила до EMA200.

Логика L1/L2/L4/L5 и зеркальность шорта — как в zones_both.detect.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from zones import add_features, load

MIN_BARS = 3
WARMUP = 31


def swing_flags(hi: np.ndarray, w: int) -> np.ndarray:
    """is_swing[i] — high[i] не ниже всех соседей в окне +/-w."""
    n = len(hi)
    s = pd.Series(hi)
    both = s.rolling(2 * w + 1, center=True).max().to_numpy()
    flags = np.zeros(n, dtype=bool)
    ok = np.isfinite(both)
    flags[ok] = hi[ok] >= both[ok]
    return flags


def detect(df: pd.DataFrame, side: str = "long", level_mode: str = "leg_max",
           swing_w: int = 3, min_bars: int = MIN_BARS) -> pd.DataFrame:
    s = 1.0 if side == "long" else -1.0
    close = s * df["close"].to_numpy()
    hi = s * (df["high"] if side == "long" else df["low"]).to_numpy()
    lo = s * (df["low"] if side == "long" else df["high"]).to_numpy()
    e27 = s * df["ema27"].to_numpy()
    e200 = s * df["ema200"].to_numpy()
    slope = s * df["slope200"].to_numpy()
    is_swing = swing_flags(hi, swing_w)

    zones: list[dict] = []
    total = len(df)
    run_ext = -np.inf
    leg_start = None
    i = WARMUP

    while i < total - 1:
        if close[i] >= e27[i]:
            if not np.isfinite(run_ext):
                leg_start = i
            run_ext = max(run_ext, hi[i])
            i += 1
            continue

        ctx = e27[i] > e200[i] and np.isfinite(slope[i]) and slope[i] > 0
        if not (ctx and np.isfinite(run_ext) and run_ext > close[i]):
            run_ext, leg_start = -np.inf, None
            i += 1
            continue

        t0 = i
        level, src = run_ext, "leg_max"
        if level_mode == "swing" and leg_start is not None:
            # последний свинг-хай ноги, подтверждённый w барами до t0
            cand = [k for k in range(leg_start, t0 - swing_w)
                    if is_swing[k] and hi[k] > close[t0]]
            if cand:
                level, src = hi[cand[-1]], "swing"

        j, outcome, end = t0 + 1, None, None
        while j < total:
            if e27[j] <= e200[j]:
                outcome, end = "context", j
                break
            if lo[j] <= e200[j]:
                outcome, end = "ema200", j
                break
            if close[j] > level:
                outcome, end = "breakout", j
                break
            j += 1
        if end is None:
            break

        if end - t0 >= min_bars:
            seg = slice(t0, end + 1)
            zones.append({
                "side": side,
                "start": df["timestamp_utc"].iloc[t0],
                "end": df["timestamp_utc"].iloc[end],
                "bars": end - t0,
                "outcome": outcome,
                "level": s * level,
                "level_src": src,
                "leg_max": s * run_ext,
                "range_pct": (df["high"].to_numpy()[seg].max()
                              - df["low"].to_numpy()[seg].min())
                             / df["close"].to_numpy()[seg].mean() * 100,
                "start_idx": t0,
            })
        run_ext, leg_start = -np.inf, None
        i = end + 1

    return pd.DataFrame(zones)


def line(z: pd.DataFrame, label: str) -> None:
    if z.empty:
        print(f"{label}: зон нет")
        return
    vc = z.outcome.value_counts()
    br = vc.get("breakout", 0)
    sw = (z.level_src == "swing").sum() if "level_src" in z else 0
    print(f"{label}: {len(z):3d} зон | breakout {br:3d} ({100 * br / len(z):3.0f}%) | "
          f"ema200 {vc.get('ema200', 0):3d} | баров мед {z.bars.median():3.0f} | "
          f"размах мед {z.range_pct.median():4.1f}% | свинг задал level в {sw:3d}")


def compare(df: pd.DataFrame, side: str, widths: tuple[int, ...]) -> None:
    base = detect(df, side, "leg_max")
    line(base, f"  {side:5} leg_max     ")
    b_idx = set(base.start_idx)
    for w in widths:
        z = detect(df, side, "swing", w)
        line(z, f"  {side:5} swing w={w:<2}  ")
        if z.empty or base.empty:
            continue
        common = b_idx & set(z.start_idx)
        m = (base[base.start_idx.isin(common)].set_index("start_idx")
             .join(z[z.start_idx.isin(common)].set_index("start_idx"),
                   rsuffix="_s"))
        diff_lvl = (m.level - m.level_s).abs() / m.level * 100
        moved = diff_lvl > 0.01
        flipped = (m.outcome != m.outcome_s)
        print(f"          общих стартов {len(common):3d} из {len(base)}/{len(z)} | "
              f"level сдвинулся у {moved.sum():3d} (мед {diff_lvl[moved].median():4.2f}%) | "
              f"исход изменился у {flipped.sum():3d}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="4h")
    p.add_argument("--suffix", default="_ext")
    p.add_argument("--widths", default="2,3,4,5,8")
    p.add_argument("--show", default=None,
                   help="дата YYYY-MM-DD: показать зону, накрывающую её")
    args = p.parse_args(argv)

    widths = tuple(int(x) for x in args.widths.split(","))
    df = add_features(load(args.tf, args.suffix))
    print(f"{args.tf} {df.timestamp_utc.iloc[0].date()}..{df.timestamp_utc.iloc[-1].date()}, "
          f"{len(df)} баров")
    for side in ("long", "short"):
        compare(df, side, widths)

    if args.show:
        d = pd.Timestamp(args.show, tz="UTC")
        print(f"\nзоны, накрывающие {args.show}:")
        for mode, w in [("leg_max", 0)] + [("swing", w) for w in widths]:
            z = detect(df, "long", mode, max(w, 1))
            hit = z[(z.start <= d + pd.Timedelta(days=1)) & (z.end >= d)]
            for _, r in hit.iterrows():
                print(f"  {mode:8} w={w}: {r.start:%Y-%m-%d %H:%M}..{r.end:%m-%d %H:%M} "
                      f"| level {r.level:.4f} ({r.level_src}) | нога {r.leg_max:.4f} "
                      f"| {r.bars:3.0f} баров | {r.outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
