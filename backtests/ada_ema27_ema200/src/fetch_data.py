"""Загрузчик свечей ADAUSDT (Bybit v5, linear) -> parquet с колонками ema27/ema200.

Ветка backtest/ada-ema27-ema200. Инструмент и индикаторы зафиксированы CLAUDE.md:
ADAUSDT, окно 2023-07-01..2024-12-31, только EMA27 и EMA200.

Два источника, в порядке приоритета:
  1. локальный кэш DATA-002 (--source cache) — уже провалидированные CSV,
     пути и sha256 зафиксированы в data/readiness/DATA-002_ADAUSDT_2023_2025/;
  2. Bybit V5 /v5/market/kline (--source api) — постраничная выгрузка.

EMA считается на расширенном окне (warmup), затем результат обрезается до
целевого окна: иначе первые ~200 баров EMA200 были бы смещены.

Примеры:
    python3 fetch_data.py --tf 1h
    python3 fetch_data.py --tf 15m --source api --out ../results/ADAUSDT_15m.parquet
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

BYBIT_KLINE_URL = "https://api.bybit.com/v5/market/kline"
CATEGORY = "linear"
SYMBOL = "ADAUSDT"

# Целевое окно бэктеста (end — исключающая граница).
WINDOW_START = "2023-07-01T00:00:00Z"
WINDOW_END_EXCLUSIVE = "2025-01-01T00:00:00Z"

EMA_FAST = 27
EMA_SLOW = 200

# Кэш DATA-002 (read-only, вне репозитория).
CACHE_DIR = Path.home() / ".local/share/msm-market-data/bybit/linear/ADAUSDT"

# tf -> (интервал Bybit, длительность бара)
TIMEFRAMES = {
    "15m": ("15", pd.Timedelta(minutes=15)),
    "1h": ("60", pd.Timedelta(hours=1)),
    "4h": ("240", pd.Timedelta(hours=4)),
    "1d": ("D", pd.Timedelta(days=1)),
}

OHLCV = ["open", "high", "low", "close", "volume", "turnover"]


def _to_utc(ts: str) -> pd.Timestamp:
    return pd.Timestamp(ts, tz="UTC")


def load_from_cache(tf: str) -> pd.DataFrame:
    """Читает провалидированный CSV DATA-002 целиком (2023-01-01..2026-01-01)."""
    path = CACHE_DIR / f"{SYMBOL}_{tf}_2023_2025.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"кэш DATA-002 не найден: {path}. Используйте --source api."
        )
    df = pd.read_csv(path)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df.sort_values("timestamp_utc").reset_index(drop=True)


def fetch_from_api(
    tf: str,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    limit: int = 1000,
    pause_s: float = 0.15,
    max_retries: int = 5,
) -> pd.DataFrame:
    """Постраничная выгрузка Bybit V5.

    Bybit отдаёт бары по убыванию времени, максимум `limit` за запрос. Идём
    вперёд от `start`, каждый раз сдвигая курсор на бар после последнего
    полученного, пока не дойдём до `end_exclusive`.
    """
    import requests

    interval, bar = TIMEFRAMES[tf]
    rows: list[list[str]] = []
    cursor = start
    seen: set[int] = set()

    while cursor < end_exclusive:
        params = {
            "category": CATEGORY,
            "symbol": SYMBOL,
            "interval": interval,
            "start": int(cursor.timestamp() * 1000),
            "end": int(end_exclusive.timestamp() * 1000) - 1,
            "limit": limit,
        }
        payload = None
        for attempt in range(max_retries):
            try:
                resp = requests.get(BYBIT_KLINE_URL, params=params, timeout=30)
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("retCode") != 0:
                    raise RuntimeError(f"Bybit retCode={payload.get('retCode')}: "
                                       f"{payload.get('retMsg')}")
                break
            except Exception as exc:  # сетевой сбой или троттлинг — backoff
                if attempt == max_retries - 1:
                    raise
                print(f"  retry {attempt + 1}/{max_retries} @ {cursor}: {exc}",
                      file=sys.stderr)
                time.sleep(2 ** attempt)

        batch = payload["result"]["list"]
        if not batch:
            break

        # Ответ отсортирован по убыванию — разворачиваем.
        batch = sorted(batch, key=lambda r: int(r[0]))
        fresh = [r for r in batch if int(r[0]) not in seen]
        if not fresh:
            break
        seen.update(int(r[0]) for r in fresh)
        rows.extend(fresh)

        last_open = pd.Timestamp(int(fresh[-1][0]), unit="ms", tz="UTC")
        cursor = last_open + bar
        print(f"  {tf}: {len(rows)} баров, курсор {cursor}", file=sys.stderr)
        time.sleep(pause_s)

    if not rows:
        raise RuntimeError(f"Bybit вернул пустой ответ для {tf} {start}..{end_exclusive}")

    df = pd.DataFrame(rows, columns=["ts_ms", *OHLCV])
    df["timestamp_utc"] = pd.to_datetime(df["ts_ms"].astype("int64"), unit="ms", utc=True)
    df[OHLCV] = df[OHLCV].astype("float64")
    df = df.drop(columns="ts_ms")
    return df[["timestamp_utc", *OHLCV]].sort_values("timestamp_utc").reset_index(drop=True)


def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[f"ema{EMA_FAST}"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    df[f"ema{EMA_SLOW}"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()
    return df


def validate(df: pd.DataFrame, tf: str, start: pd.Timestamp,
             end_exclusive: pd.Timestamp) -> None:
    """Падает, если сетка баров неполная — молчаливые дыры недопустимы."""
    bar = TIMEFRAMES[tf][1]
    ts = df["timestamp_utc"]
    problems = []

    dups = int(ts.duplicated().sum())
    if dups:
        problems.append(f"дубликатов таймстемпов: {dups}")

    diffs = ts.diff().dropna()
    bad = diffs[diffs != bar]
    if len(bad):
        first_gaps = [str(ts[i - 1]) for i in bad.index[:5]]
        problems.append(f"разрывов сетки: {len(bad)}, первые после {first_gaps}")

    expected = int((end_exclusive - start) / bar)
    if len(df) != expected:
        problems.append(f"строк {len(df)}, ожидалось {expected}")

    if ts.iloc[0] != start:
        problems.append(f"первый бар {ts.iloc[0]}, ожидался {start}")
    if ts.iloc[-1] != end_exclusive - bar:
        problems.append(f"последний бар {ts.iloc[-1]}, ожидался {end_exclusive - bar}")

    if df[OHLCV].isna().any().any():
        problems.append("есть NaN в OHLCV")

    if problems:
        raise ValueError(f"{tf}: " + "; ".join(problems))


def write(df: pd.DataFrame, out: Path) -> Path:
    """Пишет parquet; если движка нет — CSV рядом, с явным предупреждением."""
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(out, index=False)
        return out
    except ImportError as exc:
        fallback = out.with_suffix(".csv")
        print(
            f"ВНИМАНИЕ: parquet-движок недоступен ({exc}); пишу CSV -> {fallback}. "
            f"Установите pyarrow, чтобы получить parquet.",
            file=sys.stderr,
        )
        df.to_csv(fallback, index=False)
        return fallback


def build(tf: str, source: str, start: pd.Timestamp, end_exclusive: pd.Timestamp,
          warmup_bars: int) -> pd.DataFrame:
    bar = TIMEFRAMES[tf][1]
    warmup_start = start - bar * warmup_bars

    if source == "cache":
        raw = load_from_cache(tf)
    else:
        raw = fetch_from_api(tf, warmup_start, end_exclusive)

    # EMA на warmup-окне, затем обрезка до целевого.
    ext = raw[(raw["timestamp_utc"] >= warmup_start)
              & (raw["timestamp_utc"] < end_exclusive)].reset_index(drop=True)
    if ext.empty:
        raise RuntimeError(f"{tf}: нет данных в окне {warmup_start}..{end_exclusive}")
    if ext["timestamp_utc"].iloc[0] > warmup_start:
        print(f"ВНИМАНИЕ: {tf}: warmup укорочен, данные начинаются "
              f"{ext['timestamp_utc'].iloc[0]} вместо {warmup_start}", file=sys.stderr)

    ext = add_emas(ext)
    df = ext[ext["timestamp_utc"] >= start].reset_index(drop=True)
    validate(df, tf, start, end_exclusive)
    return df


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tf", default="1h", choices=sorted(TIMEFRAMES),
                   help="таймфрейм (по умолчанию 1h)")
    p.add_argument("--source", default="cache", choices=["cache", "api"],
                   help="cache = провалидированный DATA-002, api = Bybit V5")
    p.add_argument("--start", default=WINDOW_START)
    p.add_argument("--end", default=WINDOW_END_EXCLUSIVE,
                   help="исключающая правая граница")
    p.add_argument("--warmup-bars", type=int, default=EMA_SLOW * 3,
                   help="баров до --start для прогрева EMA200 (по умолчанию 600)")
    p.add_argument("--out", type=Path, default=None,
                   help="путь parquet (по умолчанию ../data/ADAUSDT_<tf>.parquet)")
    args = p.parse_args(argv)

    start, end_exclusive = _to_utc(args.start), _to_utc(args.end)
    out = args.out or (Path(__file__).resolve().parent.parent / "data"
                       / f"{SYMBOL}_{args.tf}.parquet")

    df = build(args.tf, args.source, start, end_exclusive, args.warmup_bars)
    written = write(df, out)
    print(f"{args.tf}: {len(df)} баров {df['timestamp_utc'].iloc[0]}"
          f"..{df['timestamp_utc'].iloc[-1]} -> {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
