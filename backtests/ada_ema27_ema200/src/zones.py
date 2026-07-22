"""Детектор зон консолидации: конверт EMA27 +/- c*ATR(t0)*sqrt(n).

Принцип построения (см. notes/data_audit.md и разбор трёх размеченных зон):
высота зоны не задаётся константой, а растёт как sqrt(времени) от точки
закрепления t0, с масштабом от ATR, замороженного на t0. Поэтому в начале
движения зона узкая, к концу — широкая, без подгонки под участок.

Сегментация последовательная и непересекающаяся: зона живёт от t0, пока
close внутри конверта; как только вышла — зона закрыта, следующий кандидат
на якорь — бар после выхода.

Look-ahead отсутствует: ATR берётся на t0, EMA — текущие, будущее не читается.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Полуширина конверта = C_HALF * ATR% * sqrt(n). Полный диапазон зоны при этом
# примерно 2*C_HALF*ATR*sqrt(n), что сопоставимо с k из разбора Z2/Z3 (0.67/0.80).
# Полуширина = ATR% * (A_FLOOR + C_HALF*sqrt(n)). Слагаемое A_FLOOR — базовый шум
# вокруг EMA27: без него конверт при малых n уже обычных колебаний и любая зона
# умирает на первых барах (проверено: при A_FLOOR=0 детектор не находит ничего).
A_FLOOR = 1.5
C_HALF = 0.25
MIN_BARS = 30          # короче — не зона, а обычный ход тренда (ср. Z1, N=18)
SLOPE_LOOKBACK = 30    # горизонт для наклона EMA200, баров


def load(tf: str, suffix: str = "") -> pd.DataFrame:
    """suffix='_ext' — расширенный период по 2025 включительно."""
    path = DATA_DIR / f"ADAUSDT_{tf}{suffix}.parquet"
    if not path.exists():
        path = path.with_suffix(".csv")
    if not path.exists():
        raise FileNotFoundError(f"нет данных {path}; сначала запустите fetch_data.py --tf {tf}")
    df = (pd.read_parquet(path) if path.suffix == ".parquet"
          else pd.read_csv(path, parse_dates=["timestamp_utc"]))
    return df.reset_index(drop=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    prev_close = df["close"].shift()
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["atr_pct"] = df["atr"] / df["close"] * 100

    n = SLOPE_LOOKBACK
    df["slope200"] = (df["ema200"] / df["ema200"].shift(n) - 1) * 100
    df["accel200"] = df["slope200"] - df["slope200"].shift(n)
    df["spread"] = (df["ema27"] - df["ema200"]) / df["ema200"] * 100
    return df


def detect(df: pd.DataFrame, c_half: float = C_HALF, min_bars: int = MIN_BARS,
           a_floor: float = A_FLOOR, long_only: bool = True) -> pd.DataFrame:
    """Последовательная сегментация. Возвращает таблицу закрытых зон."""
    close = df["close"].to_numpy()
    high, low = df["high"].to_numpy(), df["low"].to_numpy()
    ema27 = df["ema27"].to_numpy()
    atr_pct = df["atr_pct"].to_numpy()
    spread = df["spread"].to_numpy()

    zones = []
    i = SLOPE_LOOKBACK * 2  # прогрев признаков
    total = len(df)

    while i < total - 1:
        # Якорь ставим только в лонговом контексте (EMA27 выше EMA200).
        if long_only and not (spread[i] > 0):
            i += 1
            continue
        if not np.isfinite(atr_pct[i]) or atr_pct[i] <= 0:
            i += 1
            continue

        # Якорь — ЗАМОРОЖЕННЫЙ уровень EMA27 на t0, а не скользящая EMA27.
        # Вокруг скользящей средней отклонение не растёт с n (она сама идёт за
        # ценой), и конверт не пробивается никогда. Фиксированный уровень даёт
        # горизонтальный прямоугольник — то, что и рисуется на графике.
        t0, atr0, center = i, atr_pct[i], ema27[i]
        j, exit_dir, exit_idx = t0 + 1, None, None

        while j < total:
            n = j - t0
            half = atr0 / 100 * (a_floor + c_half * np.sqrt(n))   # доля от цены
            dev = (close[j] - center) / center
            if dev > half:
                exit_dir, exit_idx = "up", j
                break
            if dev < -half:
                exit_dir, exit_idx = "down", j
                break
            j += 1

        if exit_idx is None:      # зона не разрешилась до конца данных
            break

        length = exit_idx - t0
        if length >= min_bars:
            seg = slice(t0, exit_idx + 1)
            rng = (high[seg].max() - low[seg].min()) / close[seg].mean() * 100
            zones.append({
                "start": df["timestamp_utc"].iloc[t0],
                "end": df["timestamp_utc"].iloc[exit_idx],
                "bars": length,
                "range_pct": rng,
                "k_full": rng / (np.nanmean(atr_pct[seg]) * np.sqrt(length)),
                "atr0_pct": atr0,
                "exit_dir": exit_dir,
                "slope200": df["slope200"].iloc[exit_idx],
                "accel200": df["accel200"].iloc[exit_idx],
                "spread": df["spread"].iloc[exit_idx],
                "exit_idx": exit_idx,
            })

        i = exit_idx + 1

    return pd.DataFrame(zones)


def forward_returns(df: pd.DataFrame, zones: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Доходность через `horizon` баров после выхода из зоны, %."""
    close = df["close"].to_numpy()
    zones = zones.copy()
    idx = zones["exit_idx"].to_numpy()
    end = np.minimum(idx + horizon, len(close) - 1)
    zones[f"fwd{horizon}"] = (close[end] / close[idx] - 1) * 100
    return zones


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="4h")
    p.add_argument("--c-half", type=float, default=C_HALF)
    p.add_argument("--a-floor", type=float, default=A_FLOOR)
    p.add_argument("--min-bars", type=int, default=MIN_BARS)
    p.add_argument("--horizon", type=int, default=30)
    args = p.parse_args(argv)

    df = add_features(load(args.tf))
    zones = detect(df, args.c_half, args.min_bars, args.a_floor)
    if zones.empty:
        print("зон не найдено")
        return 0
    zones = forward_returns(df, zones, args.horizon)

    pd.set_option("display.width", 200)
    cols = ["start", "end", "bars", "range_pct", "k_full", "exit_dir",
            "slope200", "accel200", f"fwd{args.horizon}"]
    print(zones[cols].to_string(index=False,
                                formatters={c: "{:.2f}".format for c in
                                            ["range_pct", "k_full", "slope200",
                                             "accel200", f"fwd{args.horizon}"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
