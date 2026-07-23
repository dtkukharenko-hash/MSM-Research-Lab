"""Побарный эмулятор Pine-машины ada_zones_long.pine — сверка с zones_both.detect.

Pine не умеет смотреть вперёд, поэтому событие копится в pend*-переменных и
зона открывается задним числом. Нужно убедиться, что итог совпадает с питоном,
который считает серию закрытий forward-сканом.
"""
import pathlib
import sys
import math

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zones import add_features, load          # noqa: E402
from zones_both import detect                 # noqa: E402

WARMUP, MIN_BARS = 31, 3


def pine(df, confirm_bars=2, min_bars=MIN_BARS):
    o, h, lo, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e27, e200, slope = (df[k].to_numpy() for k in ("ema27", "ema200", "slope200"))
    nan = math.nan
    inZone, runMax, level, startBI = False, nan, nan, -1
    zoneLo = nan
    belowN, pendBI, pendLevel, pendHi, pendLo, pendOk = 0, -1, nan, nan, nan, False
    out = []

    for bi in range(WARMUP, len(df)):
        doClose, outcome = False, ""
        if not inZone:
            if c[bi] >= e27[bi]:
                if belowN > 0 and pendOk:
                    runMax = max(runMax, pendHi)
                belowN, pendOk = 0, False
                runMax = h[bi] if math.isnan(runMax) else max(runMax, h[bi])
            else:
                belowN += 1
                if belowN == 1:
                    ctx = (e27[bi] > e200[bi] and np.isfinite(slope[bi])
                           and slope[bi] > 0)
                    pendOk = ctx and not math.isnan(runMax) and runMax > c[bi]
                    pendLevel, pendBI = runMax, bi
                    pendHi, pendLo = h[bi], lo[bi]
                    if not pendOk:
                        runMax = nan
                elif pendOk:
                    pendHi, pendLo = max(pendHi, h[bi]), min(pendLo, lo[bi])
                    if lo[bi] <= e200[bi]:
                        pendOk, runMax = False, nan

                if pendOk and belowN >= confirm_bars:
                    inZone, level, startBI = True, pendLevel, pendBI
                    zoneLo = pendLo
                    belowN, pendOk = 0, False
        else:
            zoneLo = min(zoneLo, lo[bi])
            if lo[bi] <= e200[bi]:
                doClose, outcome = True, "ema200"
            elif c[bi] > level:
                doClose, outcome = True, "breakout"

        if doClose:
            zbars = bi - startBI
            if zbars >= min_bars:
                out.append({"start": df.timestamp_utc.iloc[startBI],
                            "end": df.timestamp_utc.iloc[bi],
                            "bars": zbars, "outcome": outcome,
                            "level": level, "start_idx": startBI})
            inZone, runMax, belowN, pendOk = False, nan, 0, False
    return pd.DataFrame(out)


for tf in ("4h", "1h"):
    df = add_features(load(tf, "_ext"))
    for cb in (1, 2, 3):
        p = pine(df, cb)
        z = detect(df, "long", confirm_bars=cb)
        sp, sz = set(p.start_idx), set(z.start_idx)
        same = sp == sz
        print(f"{tf} cb={cb}: pine {len(p):3d} | python {len(z):3d} | "
              f"старты {'СОВПАЛИ' if same else 'РАЗОШЛИСЬ'}", end="")
        if not same:
            only_p, only_z = sorted(sp - sz), sorted(sz - sp)
            print(f" | только pine {len(only_p)}, только python {len(only_z)}")
            for k in only_p[:4]:
                r = p[p.start_idx == k].iloc[0]
                print(f"    pine  {r.start:%Y-%m-%d %H:%M} {r.bars:3.0f}б {r.outcome}")
            for k in only_z[:4]:
                r = z[z.start_idx == k].iloc[0]
                print(f"    pyth  {r.start:%Y-%m-%d %H:%M} {r.bars:3.0f}б {r.outcome}")
        else:
            m = p.set_index("start_idx").join(z.set_index("start_idx"), rsuffix="_z")
            bad = (m.bars != m.bars_z) | (m.outcome != m.outcome_z)
            print(f" | расхождений по исходу/длине: {int(bad.sum())}")
