#!/usr/bin/env python3
"""EXP-008: reference entry labeling inside major ADAUSDT 4H EMA movements.

This script creates qualitative labels and diagnostic artifacts only. It does not
run a backtest, does not compute PnL, and does not open any data after
2024-12-31.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-008_MAJOR_MOVE_ENTRY_LABELING"
OUT = EXP / "artifacts"
DATA = Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv")
EXP007_SIGNALS = ROOT / "experiments/EXP-007_TREND_ALIGNED_ENTRY/artifacts/all_entry_signals.csv"

START = pd.Timestamp("2023-07-01 00:00")
END = pd.Timestamp("2024-12-31 23:59")
FORBIDDEN = pd.Timestamp("2025-01-01 00:00")


ZONE_ORDER = [
    "ZONE_0_BEFORE_MOVE",
    "ZONE_1_BIRTH",
    "ZONE_2_FIRST_PULLBACK",
    "ZONE_3_EARLY_CONTINUATION",
    "ZONE_4_MATURE_MOVE",
    "ZONE_5_LATE_MOVE",
    "ZONE_6_EXHAUSTION_OR_CHOP",
]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(DATA, usecols=["open_dt", "open", "high", "low", "close"])
    df["dt"] = pd.to_datetime(df["open_dt"])
    df = df.sort_values("dt")
    df = df[(df["dt"] >= START) & (df["dt"] <= END)].copy().reset_index(drop=True)
    if df.empty:
        raise RuntimeError("No ADAUSDT 4H data loaded for EXP-008.")
    if df["dt"].max() >= FORBIDDEN:
        raise RuntimeError("EXP-008 attempted to use data after 2024-12-31.")

    prev_close = df["close"].shift(1).fillna(df["close"])
    df["tr"] = np.maximum.reduce(
        [
            (df["high"] - df["low"]).to_numpy(float),
            (df["high"] - prev_close).abs().to_numpy(float),
            (df["low"] - prev_close).abs().to_numpy(float),
        ]
    )
    df["body"] = (df["close"] - df["open"]).abs()
    df["ema27"] = df["close"].ewm(span=27, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["atr14"] = df["tr"].rolling(14, min_periods=1).mean()
    df["ema27_slope_10"] = df["ema27"] - df["ema27"].shift(10)
    df["ema200_slope_20"] = df["ema200"] - df["ema200"].shift(20)
    df["ema_distance_atr"] = (df["ema27"] - df["ema200"]).abs() / df["atr14"].replace(0, np.nan)
    df["price_distance_ema27_atr"] = (df["close"] - df["ema27"]).abs() / df["atr14"].replace(0, np.nan)
    price_side = np.sign(df["close"] - df["ema27"]).replace(0, np.nan).ffill().fillna(0)
    df["ema27_crossings_last10"] = (price_side.diff().abs() > 0).rolling(10, min_periods=1).sum()
    return df


def direction_side(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def find_major_moves(df: pd.DataFrame) -> pd.DataFrame:
    """Build a coarse retrospective map, intentionally limited to major swings.

    This is a reference map, not a boundary detector. The local-extrema window
    and return threshold are fixed before the label pass to prevent the 50-case
    local sample from becoming the implicit movement definition.
    """

    order = 36
    min_abs_return = 0.25
    min_bars = 12
    points: list[list[int | str]] = []
    closes = df["close"].to_numpy(float)
    for i in range(order, len(df) - order):
        window = closes[i - order : i + order + 1]
        if closes[i] == np.max(window):
            points.append([i, "HIGH"])
        elif closes[i] == np.min(window):
            points.append([i, "LOW"])

    alternating: list[list[int | str]] = []
    for i, kind in points:
        if not alternating:
            alternating.append([i, kind])
            continue
        prev_i, prev_kind = alternating[-1]
        if kind == prev_kind:
            replace = (kind == "HIGH" and closes[i] > closes[prev_i]) or (kind == "LOW" and closes[i] < closes[prev_i])
            if replace:
                alternating[-1] = [i, kind]
        else:
            alternating.append([i, kind])

    rows = []
    for start_point, end_point in zip(alternating, alternating[1:]):
        start_i, start_kind = int(start_point[0]), str(start_point[1])
        end_i, end_kind = int(end_point[0]), str(end_point[1])
        start_price = float(df.loc[start_i, "close"])
        end_price = float(df.loc[end_i, "close"])
        duration = end_i - start_i
        total_return = (end_price - start_price) / start_price
        if duration < min_bars or abs(total_return) < min_abs_return:
            continue
        direction = "LONG" if total_return > 0 else "SHORT"
        start_ema_relation = "EMA27_ABOVE_EMA200" if df.loc[start_i, "ema27"] > df.loc[start_i, "ema200"] else "EMA27_BELOW_EMA200"
        confidence = "HIGH" if abs(total_return) >= 0.35 and duration >= 48 else "MEDIUM"
        if duration <= 24:
            confidence = "LOW"
        rows.append(
            {
                "move_id": f"M{len(rows) + 1:02d}",
                "direction": direction,
                "start_i": start_i,
                "end_i": end_i,
                "start_time": df.loc[start_i, "dt"],
                "end_time": df.loc[end_i, "dt"],
                "start_price": start_price,
                "end_price": end_price,
                "duration_bars": duration,
                "return_pct": total_return * 100,
                "ema27_vs_ema200_at_start": start_ema_relation,
                "confidence": confidence,
                "boundary_method": "coarse_retrospective_local_extrema_order36_return25pct",
                "boundary_note": f"{start_kind}_to_{end_kind}; reference labeling only",
            }
        )

    moves = pd.DataFrame(rows)
    if len(moves) > 20:
        raise RuntimeError(f"Major movement map produced {len(moves)} moves, which is too local for EXP-008.")
    return moves


def first_pullback_bounds(df: pd.DataFrame, move: pd.Series) -> tuple[int, int] | None:
    s = direction_side(move["direction"])
    start_i = int(move["start_i"])
    end_i = int(move["end_i"])
    birth_end = start_i + max(2, int((end_i - start_i) * 0.18))
    search_end = start_i + max(6, int((end_i - start_i) * 0.45))
    search_end = min(search_end, end_i)
    pullback_start = None
    for i in range(start_i + 2, search_end + 1):
        if s * (float(df.loc[i, "close"]) - float(df.loc[i - 1, "close"])) < 0:
            pullback_start = i
            break
    if pullback_start is None:
        return None
    pullback_end = pullback_start
    for i in range(pullback_start + 1, search_end + 1):
        if s * (float(df.loc[i, "close"]) - float(df.loc[i - 1, "close"])) > 0:
            pullback_end = i
            break
        pullback_end = i
    if pullback_end <= pullback_start:
        pullback_end = min(search_end, pullback_start + 2)
    if pullback_start > birth_end:
        pullback_start = birth_end
    return pullback_start, pullback_end


def build_zones(df: pd.DataFrame, moves: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, move in moves.iterrows():
        start_i = int(move["start_i"])
        end_i = int(move["end_i"])
        duration = end_i - start_i
        z0_start = max(0, start_i - min(18, max(6, duration // 8)))
        z1_end = start_i + max(2, int(duration * 0.18))
        pb = first_pullback_bounds(df, move)
        if pb:
            z2_start, z2_end = pb
            z1_end = min(z1_end, z2_start)
        else:
            z2_start = z1_end + 1
            z2_end = min(end_i, z2_start + max(1, int(duration * 0.10)))
        z3_end = start_i + max(3, int(duration * 0.38))
        z4_end = start_i + max(4, int(duration * 0.68))
        z5_end = start_i + max(5, int(duration * 0.86))
        zone_defs = [
            ("ZONE_0_BEFORE_MOVE", z0_start, start_i - 1),
            ("ZONE_1_BIRTH", start_i, max(start_i, z1_end)),
            ("ZONE_2_FIRST_PULLBACK", max(start_i, z2_start), min(end_i, z2_end)),
            ("ZONE_3_EARLY_CONTINUATION", min(end_i, z2_end + 1), min(end_i, z3_end)),
            ("ZONE_4_MATURE_MOVE", min(end_i, z3_end + 1), min(end_i, z4_end)),
            ("ZONE_5_LATE_MOVE", min(end_i, z4_end + 1), min(end_i, z5_end)),
            ("ZONE_6_EXHAUSTION_OR_CHOP", min(end_i, z5_end + 1), end_i),
        ]
        for zone, a, b in zone_defs:
            if a > b:
                a = b = min(max(a, start_i), end_i)
            rows.append(
                {
                    "move_id": move["move_id"],
                    "zone": zone,
                    "start_i": int(a),
                    "end_i": int(b),
                    "start_time": df.loc[int(a), "dt"],
                    "end_time": df.loc[int(b), "dt"],
                    "duration_bars": int(max(0, b - a + 1)),
                    "zone_note": "retrospective training label; not live detector",
                }
            )
    return pd.DataFrame(rows)


def zone_at(zones: pd.DataFrame, move_id: str, i: int) -> str:
    z = zones[(zones["move_id"] == move_id) & (zones["start_i"] <= i) & (zones["end_i"] >= i)]
    if z.empty:
        return "OUTSIDE_MOVE"
    return str(z.iloc[0]["zone"])


def feature_row(df: pd.DataFrame, move: pd.Series, zones: pd.DataFrame, i: int) -> dict[str, object]:
    start_i = int(move["start_i"])
    end_i = int(move["end_i"])
    s = direction_side(move["direction"])
    start_price = float(move["start_price"])
    end_price = float(move["end_price"])
    price = float(df.loc[i, "close"])
    atr = float(df.loc[i, "atr14"])
    bars_from_start = i - start_i
    atr_from_start = s * (price - start_price) / atr if atr > 0 else np.nan
    denom = abs(end_price - start_price)
    fraction = abs(price - start_price) / denom if denom > 0 else np.nan
    pb_depth = pullback_depth(df, move, i)
    relation = "EMA27_ABOVE_EMA200" if df.loc[i, "ema27"] > df.loc[i, "ema200"] else "EMA27_BELOW_EMA200"
    return {
        "move_id": move["move_id"],
        "direction": move["direction"],
        "signal_time": df.loc[i, "dt"],
        "executable_time": df.loc[min(i + 1, len(df) - 1), "dt"],
        "price": price,
        "zone": zone_at(zones, str(move["move_id"]), i),
        "ema27_relation_to_ema200": relation,
        "ema27_slope_10": float(df.loc[i, "ema27_slope_10"]),
        "ema200_slope_20": float(df.loc[i, "ema200_slope_20"]),
        "ema_distance_atr": float(df.loc[i, "ema_distance_atr"]),
        "price_distance_ema27_atr": float(df.loc[i, "price_distance_ema27_atr"]),
        "bars_from_move_start": int(bars_from_start),
        "atr_from_move_start": atr_from_start,
        "fraction_move_completed": fraction,
        "pullback_to_ema27": bool(
            (move["direction"] == "LONG" and df.loc[max(start_i, i - 10) : i, "low"].min() <= df.loc[i, "ema27"])
            or (move["direction"] == "SHORT" and df.loc[max(start_i, i - 10) : i, "high"].max() >= df.loc[i, "ema27"])
        ),
        "pullback_depth_atr": pb_depth,
        "new_extremum_after_pullback": bool(new_extremum_after_pullback(df, move, i)),
        "ema27_crossings_last10": float(df.loc[i, "ema27_crossings_last10"]),
    }


def pullback_depth(df: pd.DataFrame, move: pd.Series, i: int) -> float:
    s = direction_side(move["direction"])
    start_i = int(move["start_i"])
    atr = float(df.loc[i, "atr14"])
    if atr <= 0:
        return np.nan
    window = df.loc[start_i:i]
    if s > 0:
        peak = float(window["high"].max())
        current_low = float(df.loc[i, "low"])
        return max(0.0, (peak - current_low) / atr)
    trough = float(window["low"].min())
    current_high = float(df.loc[i, "high"])
    return max(0.0, (current_high - trough) / atr)


def new_extremum_after_pullback(df: pd.DataFrame, move: pd.Series, i: int) -> bool:
    s = direction_side(move["direction"])
    start_i = int(move["start_i"])
    if i <= start_i + 2:
        return False
    prev = df.loc[start_i : i - 1]
    if s > 0:
        return float(df.loc[i, "high"]) > float(prev["high"].max())
    return float(df.loc[i, "low"]) < float(prev["low"].min())


def pick_index_in_zone(zones: pd.DataFrame, move_id: str, zone: str, fallback_start_i: int, fallback_end_i: int, frac: float) -> int:
    z = zones[(zones["move_id"] == move_id) & (zones["zone"] == zone)]
    if z.empty:
        return int(round(fallback_start_i + (fallback_end_i - fallback_start_i) * frac))
    a = int(z.iloc[0]["start_i"])
    b = int(z.iloc[0]["end_i"])
    return int(round(a + max(0, b - a) * frac))


def build_labels(df: pd.DataFrame, moves: pd.DataFrame, zones: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    approved_rows = []
    blocked_rows = []
    for _, move in moves.iterrows():
        move_id = str(move["move_id"])
        start_i = int(move["start_i"])
        end_i = int(move["end_i"])
        primary_i = pick_index_in_zone(zones, move_id, "ZONE_1_BIRTH", start_i, end_i, 0.45)
        secondary_i = pick_index_in_zone(zones, move_id, "ZONE_3_EARLY_CONTINUATION", start_i, end_i, 0.35)
        for label, i in [("PRIMARY_ENTRY", primary_i), ("OPTIONAL_SECONDARY_ENTRY", secondary_i)]:
            row = feature_row(df, move, zones, i)
            row["entry_label"] = label
            row["visual_basis"] = visual_basis(row, label)
            approved_rows.append(row)

        blocked_specs = [
            ("ZONE_4_MATURE_MOVE", "MATURE_MOVE", 0.55),
            ("ZONE_5_LATE_MOVE", "TOO_LATE", 0.50),
            ("ZONE_6_EXHAUSTION_OR_CHOP", "EXHAUSTION", 0.35),
        ]
        prev_allowed = f"{move_id}:PRIMARY_ENTRY"
        for zone, reason, frac in blocked_specs:
            i = pick_index_in_zone(zones, move_id, zone, start_i, end_i, frac)
            row = feature_row(df, move, zones, i)
            row["timestamp"] = row.pop("signal_time")
            row["blocked_reason"] = reason
            row["distance_to_EMA27"] = row["price_distance_ema27_atr"]
            row["previous_allowed_entry_in_move"] = prev_allowed
            row["why_EMA_context_insufficient"] = blocked_basis(row, reason)
            blocked_rows.append(row)
    approved = pd.DataFrame(approved_rows)
    blocked = pd.DataFrame(blocked_rows)
    return approved, blocked


def visual_basis(row: dict[str, object], label: str) -> str:
    if label == "PRIMARY_ENTRY":
        return (
            "early zone; movement direction already visible; EMA context describes direction but label is based on "
            "retrospective major-move birth, not a live signal"
        )
    return (
        "first early-continuation zone after initial pullback; second approved label kept only where it remains before "
        "mature/late zones"
    )


def blocked_basis(row: dict[str, object], reason: str) -> str:
    fraction = float(row["fraction_move_completed"])
    crosses = float(row["ema27_crossings_last10"])
    if reason == "MATURE_MOVE":
        return f"EMA can still point in direction, but {fraction:.2f} of full retrospective movement is already completed."
    if reason == "TOO_LATE":
        return f"Late zone after prior allowed label; EMA context does not show that this is a repeated same-move entry."
    return f"Exhaustion/chop zone; EMA context lags and crossings_last10={crosses:.0f} can understate local instability."


def compare_good_vs_blocked(approved: pd.DataFrame, blocked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    fields = [
        "bars_from_move_start",
        "atr_from_move_start",
        "fraction_move_completed",
        "price_distance_ema27_atr",
        "ema_distance_atr",
        "ema27_crossings_last10",
    ]
    for field in fields:
        good_values = pd.to_numeric(approved[field], errors="coerce")
        bad_field = "distance_to_EMA27" if field == "price_distance_ema27_atr" else field
        bad_values = pd.to_numeric(blocked[bad_field], errors="coerce")
        rows.append(
            {
                "feature": field,
                "approved_median": good_values.median(),
                "blocked_median": bad_values.median(),
                "approved_mean": good_values.mean(),
                "blocked_mean": bad_values.mean(),
                "difference_note": describe_feature_difference(field, good_values.median(), bad_values.median()),
            }
        )
    return pd.DataFrame(rows)


def describe_feature_difference(field: str, good: float, bad: float) -> str:
    if field == "fraction_move_completed":
        return "blocked labels occur after much more of the retrospective move has already happened"
    if field == "bars_from_move_start":
        return "blocked labels are later in bar-count age"
    if field == "price_distance_ema27_atr":
        return "EMA proximity alone is not enough; blocked labels can still be near EMA27"
    if field == "ema27_crossings_last10":
        return "crossing count helps with chop but does not separate all late examples"
    return "context feature compared for descriptive audit only"


def map_exp007_signals(df: pd.DataFrame, moves: pd.DataFrame, zones: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not EXP007_SIGNALS.exists():
        return pd.DataFrame(), pd.DataFrame()
    sig = pd.read_csv(EXP007_SIGNALS)
    sig["entry_time_dt"] = pd.to_datetime(sig["entry_time"])
    sig = sig[(sig["entry_time_dt"] >= START) & (sig["entry_time_dt"] <= END)].copy()
    mapped = []
    for _, row in sig.iterrows():
        t = row["entry_time_dt"]
        move_match = moves[(moves["start_time"] <= t) & (moves["end_time"] >= t)]
        if move_match.empty:
            move_id = "OUTSIDE_MAJOR_MOVE"
            zone = "OUTSIDE_MAJOR_MOVE"
            signal_number = np.nan
        else:
            move = move_match.iloc[0]
            move_id = move["move_id"]
            idx = int(df.index[df["dt"] == t][0]) if (df["dt"] == t).any() else np.nan
            zone = zone_at(zones, str(move_id), int(idx)) if not pd.isna(idx) else "UNKNOWN"
            signal_number = np.nan
        mapped.append(
            {
                "entry_variant": row.get("entry_variant"),
                "signal_time": row.get("signal_time"),
                "entry_time": row.get("entry_time"),
                "direction": row.get("direction"),
                "scope": row.get("scope"),
                "executed": row.get("executed"),
                "blocked": row.get("blocked"),
                "block_reason": row.get("block_reason"),
                "move_id": move_id,
                "zone": zone,
                "signal_number_in_move": signal_number,
            }
        )
    mapped_df = pd.DataFrame(mapped)
    mapped_df = mapped_df.sort_values(["move_id", "entry_time", "entry_variant"]).reset_index(drop=True)
    inside = mapped_df[mapped_df["move_id"] != "OUTSIDE_MAJOR_MOVE"].copy()
    if not inside.empty:
        inside["signal_number_in_move"] = inside.groupby("move_id").cumcount() + 1
        mapped_df.loc[inside.index, "signal_number_in_move"] = inside["signal_number_in_move"]

    diag_rows = []
    for move_id, grp in mapped_df[mapped_df["move_id"] != "OUTSIDE_MAJOR_MOVE"].groupby("move_id"):
        grp = grp.sort_values("entry_time")
        first = grp.iloc[0]
        late = grp[grp["zone"].isin(["ZONE_4_MATURE_MOVE", "ZONE_5_LATE_MOVE", "ZONE_6_EXHAUSTION_OR_CHOP"])]
        diag_rows.append(
            {
                "move_id": move_id,
                "exp007_signal_count": len(grp),
                "first_signal_time": first["entry_time"],
                "first_signal_variant": first["entry_variant"],
                "first_signal_zone": first["zone"],
                "mature_late_exhaustion_signal_count": len(late),
                "one_entry_per_move_keeps_signal": first["entry_time"],
                "one_entry_per_move_discards_count": max(0, len(grp) - 1),
                "diagnosis_note": "diagnostic count only; no PnL or trade simulation computed in EXP-008",
            }
        )
    diagnosis = pd.DataFrame(diag_rows)
    return mapped_df, diagnosis


def pine_timestamp(ts: pd.Timestamp) -> str:
    return f'timestamp("Etc/UTC", {ts.year}, {ts.month}, {ts.day}, {ts.hour}, {ts.minute})'


def write_pine(moves: pd.DataFrame, zones: pd.DataFrame, approved: pd.DataFrame, blocked: pd.DataFrame) -> None:
    path = OUT / "EXP008_MAJOR_MOVE_ENTRY_LABELS.pine"
    lines = [
        "//@version=6",
        'indicator("EXP-008 Major Move Entry Labels", overlay=true, max_lines_count=500, max_labels_count=500)',
        "",
        "// Visual labeling only. Not a strategy, not an auto-detector, and not a mass signal generator.",
        "// Use on ADAUSDT 4H. Recommended TradingView ticker: BYBIT:ADAUSDT.P; fallback: BINANCE:ADAUSDT.",
        'moveNumber = input.int(1, "moveNumber", minval=1, maxval=' + str(len(moves)) + ")",
        'showPrimary = input.bool(true, "showPrimary")',
        'showSecondary = input.bool(true, "showSecondary")',
        'showBlocked = input.bool(true, "showBlocked")',
        'showZones = input.bool(true, "showZones")',
        'showEMA = input.bool(true, "showEMA")',
        'showOnlyOneMove = input.bool(true, "showOnlyOneMove")',
        "",
        "ema27 = ta.ema(close, 27)",
        "ema200 = ta.ema(close, 200)",
        'plot(showEMA ? ema27 : na, "EMA27", color=color.aqua, linewidth=1)',
        'plot(showEMA ? ema200 : na, "EMA200", color=color.orange, linewidth=1)',
        "",
        "var int[] moveNos = array.from(" + ", ".join(str(i + 1) for i in range(len(moves))) + ")",
        "var string[] moveIds = array.from(" + ", ".join(f'"{x}"' for x in moves["move_id"]) + ")",
        "var string[] moveDirs = array.from(" + ", ".join(f'"{x}"' for x in moves["direction"]) + ")",
        "var int[] moveStarts = array.from(" + ", ".join(pine_timestamp(pd.Timestamp(x)) for x in moves["start_time"]) + ")",
        "var int[] moveEnds = array.from(" + ", ".join(pine_timestamp(pd.Timestamp(x)) for x in moves["end_time"]) + ")",
        "",
    ]

    zone_rows = zones.copy()
    lines.extend(
        [
            "var int[] zoneMoveNos = array.from("
            + ", ".join(str(int(moves.index[moves["move_id"] == z["move_id"]][0]) + 1) for _, z in zone_rows.iterrows())
            + ")",
            "var string[] zoneNames = array.from(" + ", ".join(f'"{z}"' for z in zone_rows["zone"]) + ")",
            "var int[] zoneStarts = array.from(" + ", ".join(pine_timestamp(pd.Timestamp(x)) for x in zone_rows["start_time"]) + ")",
            "var int[] zoneEnds = array.from(" + ", ".join(pine_timestamp(pd.Timestamp(x)) for x in zone_rows["end_time"]) + ")",
            "",
        ]
    )

    approved_sorted = approved.sort_values(["move_id", "entry_label"]).reset_index(drop=True)
    blocked_sorted = blocked.sort_values(["move_id", "timestamp"]).reset_index(drop=True)
    lines.extend(
        [
            "var int[] approvedMoveNos = array.from("
            + ", ".join(str(int(moves.index[moves["move_id"] == z["move_id"]][0]) + 1) for _, z in approved_sorted.iterrows())
            + ")",
            "var string[] approvedKinds = array.from(" + ", ".join(f'"{x}"' for x in approved_sorted["entry_label"]) + ")",
            "var int[] approvedTimes = array.from(" + ", ".join(pine_timestamp(pd.Timestamp(x)) for x in approved_sorted["signal_time"]) + ")",
            "var float[] approvedAtrDone = array.from(" + ", ".join(f"{float(x):.4f}" for x in approved_sorted["atr_from_move_start"]) + ")",
            "var float[] approvedFracDone = array.from(" + ", ".join(f"{float(x) * 100:.2f}" for x in approved_sorted["fraction_move_completed"]) + ")",
            "",
            "var int[] blockedMoveNos = array.from("
            + ", ".join(str(int(moves.index[moves["move_id"] == z["move_id"]][0]) + 1) for _, z in blocked_sorted.iterrows())
            + ")",
            "var string[] blockedReasons = array.from(" + ", ".join(f'"{x}"' for x in blocked_sorted["blocked_reason"]) + ")",
            "var int[] blockedTimes = array.from(" + ", ".join(pine_timestamp(pd.Timestamp(x)) for x in blocked_sorted["timestamp"]) + ")",
            "var float[] blockedAtrDone = array.from(" + ", ".join(f"{float(x):.4f}" for x in blocked_sorted["atr_from_move_start"]) + ")",
            "var float[] blockedFracDone = array.from(" + ", ".join(f"{float(x) * 100:.2f}" for x in blocked_sorted["fraction_move_completed"]) + ")",
            "",
        ]
    )

    lines.extend(
        [
            "f_move_visible(int n) =>",
            "    showOnlyOneMove ? n == moveNumber : true",
            "",
            "f_zone_color(string z) =>",
            '    z == "ZONE_0_BEFORE_MOVE" ? color.new(color.gray, 92) : z == "ZONE_1_BIRTH" ? color.new(color.green, 88) : z == "ZONE_2_FIRST_PULLBACK" ? color.new(color.blue, 88) : z == "ZONE_3_EARLY_CONTINUATION" ? color.new(color.teal, 88) : z == "ZONE_4_MATURE_MOVE" ? color.new(color.yellow, 88) : z == "ZONE_5_LATE_MOVE" ? color.new(color.orange, 88) : color.new(color.red, 88)',
            "",
            "var color bg = na",
            "bg := na",
            "for i = 0 to array.size(moveNos) - 1",
            "    int n = array.get(moveNos, i)",
            "    if f_move_visible(n)",
            "        int st = array.get(moveStarts, i)",
            "        int en = array.get(moveEnds, i)",
            "        string mid = array.get(moveIds, i)",
            "        string dir = array.get(moveDirs, i)",
            "        if time == st",
            "            line.new(st, low, st, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.lime, 0), width=2)",
            '            label.new(st, high, mid + " " + dir + " start", xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.lime, 0), textcolor=color.black, size=size.tiny)',
            "        if time == en",
            "            line.new(en, low, en, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.white, 0), width=2, style=line.style_dotted)",
            '            label.new(en, low, mid + " end", xloc=xloc.bar_time, style=label.style_label_up, color=color.new(color.white, 0), textcolor=color.black, size=size.tiny)',
            "",
            "if showZones",
            "    for i = 0 to array.size(zoneMoveNos) - 1",
            "        int n = array.get(zoneMoveNos, i)",
            "        int st = array.get(zoneStarts, i)",
            "        int en = array.get(zoneEnds, i)",
            "        string zn = array.get(zoneNames, i)",
            "        if f_move_visible(n) and time >= st and time <= en",
            "            bg := f_zone_color(zn)",
            "bgcolor(bg)",
            "",
            "for i = 0 to array.size(approvedMoveNos) - 1",
            "    int n = array.get(approvedMoveNos, i)",
            "    string kind = array.get(approvedKinds, i)",
            "    int t = array.get(approvedTimes, i)",
            "    bool isPrimary = kind == \"PRIMARY_ENTRY\"",
            "    bool visible = f_move_visible(n) and ((isPrimary and showPrimary) or (not isPrimary and showSecondary))",
            "    if visible and time == t",
            "        color c = isPrimary ? color.new(color.green, 0) : color.new(color.blue, 0)",
            "        line.new(t, low, t, high, xloc=xloc.bar_time, extend=extend.both, color=c, width=2)",
            '        label.new(t, isPrimary ? low : high, kind + "\\nATR=" + str.tostring(array.get(approvedAtrDone, i), "#.##") + "\\nmove=" + str.tostring(array.get(approvedFracDone, i), "#.#") + "%", xloc=xloc.bar_time, style=isPrimary ? label.style_label_up : label.style_label_down, color=c, textcolor=color.white, size=size.tiny)',
            "",
            "for i = 0 to array.size(blockedMoveNos) - 1",
            "    int n = array.get(blockedMoveNos, i)",
            "    int t = array.get(blockedTimes, i)",
            "    if f_move_visible(n) and showBlocked and time == t",
            "        string reason = array.get(blockedReasons, i)",
            "        line.new(t, low, t, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.red, 0), width=2, style=line.style_dashed)",
            '        label.new(t, low, "BLOCKED\\n" + reason + "\\nATR=" + str.tostring(array.get(blockedAtrDone, i), "#.##") + "\\nmove=" + str.tostring(array.get(blockedFracDone, i), "#.#") + "%", xloc=xloc.bar_time, style=label.style_label_up, color=color.new(color.red, 0), textcolor=color.white, size=size.tiny)',
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def pdf_text(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf_pages(pages: list[str], path: Path, width: int = 792, height: int = 612) -> None:
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for i, content in enumerate(pages):
        content_b = content.encode("latin-1", errors="replace")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/Contents {4 + i * 2} 0 R >>".encode()
        )
        objects.append(f"<< /Length {len(content_b)} >>\nstream\n".encode() + content_b + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def chart_panel(
    df: pd.DataFrame,
    lo: int,
    hi: int,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    move: pd.Series | None = None,
    zones: pd.DataFrame | None = None,
    approved: pd.DataFrame | None = None,
    blocked: pd.DataFrame | None = None,
) -> str:
    win = df.loc[lo:hi]
    ymin = float(win[["low", "ema27", "ema200"]].min().min())
    ymax = float(win[["high", "ema27", "ema200"]].max().max())
    if ymax == ymin:
        ymax = ymin + 1

    def px(idx: int) -> float:
        return x + (idx - lo) / max(1, hi - lo) * w

    def py(val: float) -> float:
        return y + (val - ymin) / (ymax - ymin) * h

    def polyline(col: str, color: str, width: float) -> list[str]:
        cmds = [f"{color} RG {width} w"]
        for j, (idx, val) in enumerate(zip(win.index, win[col].astype(float))):
            cmds.append(f"{px(int(idx)):.2f} {py(float(val)):.2f} {'m' if j == 0 else 'l'}")
        cmds.append("S")
        return cmds

    cmds = [
        f"0.85 0.85 0.85 RG 0.5 w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S",
        f"BT /F1 9 Tf {x:.2f} {y+h+10:.2f} Td ({pdf_text(title)}) Tj ET",
    ]

    if zones is not None:
        shade_colors = {
            "ZONE_1_BIRTH": "0.85 1 0.85",
            "ZONE_2_FIRST_PULLBACK": "0.85 0.92 1",
            "ZONE_3_EARLY_CONTINUATION": "0.85 1 1",
            "ZONE_4_MATURE_MOVE": "1 0.95 0.75",
            "ZONE_5_LATE_MOVE": "1 0.88 0.75",
            "ZONE_6_EXHAUSTION_OR_CHOP": "1 0.82 0.82",
        }
        for _, zrow in zones.iterrows():
            za, zb = int(zrow["start_i"]), int(zrow["end_i"])
            if zb < lo or za > hi:
                continue
            sx = px(max(lo, za))
            ex = px(min(hi, zb))
            color = shade_colors.get(str(zrow["zone"]), "0.93 0.93 0.93")
            cmds.append(f"{color} rg {sx:.2f} {y:.2f} {max(1, ex-sx):.2f} {h:.2f} re f")
    cmds.extend(polyline("close", "0 0 0", 0.8))
    cmds.extend(polyline("ema27", "0 0.55 0.85", 0.6))
    cmds.extend(polyline("ema200", "0.95 0.45 0", 0.6))

    if move is not None:
        si, ei = int(move["start_i"]), int(move["end_i"])
        if lo <= si <= hi:
            cmds.append(f"0 0.65 0 RG 1.1 w {px(si):.2f} {y:.2f} m {px(si):.2f} {y+h:.2f} l S")
        if lo <= ei <= hi:
            cmds.append(f"0.4 0.4 0.4 RG 1 w {px(ei):.2f} {y:.2f} m {px(ei):.2f} {y+h:.2f} l S")
    if approved is not None:
        for _, a in approved.iterrows():
            idx = int(df.index[df["dt"] == pd.Timestamp(a["signal_time"])][0])
            if lo <= idx <= hi:
                color = "0 0.65 0" if a["entry_label"] == "PRIMARY_ENTRY" else "0 0.2 0.9"
                cmds.append(f"{color} RG 1.2 w {px(idx):.2f} {y:.2f} m {px(idx):.2f} {y+h:.2f} l S")
    if blocked is not None:
        for _, b in blocked.iterrows():
            idx = int(df.index[df["dt"] == pd.Timestamp(b["timestamp"])][0])
            if lo <= idx <= hi:
                xx = px(idx)
                cmds.append(f"0.9 0 0 RG 1.1 w {xx:.2f} {y:.2f} m {xx:.2f} {y+h:.2f} l S")
                cmds.append(f"{xx-3:.2f} {y+h-8:.2f} m {xx+3:.2f} {y+h-2:.2f} l S")
                cmds.append(f"{xx+3:.2f} {y+h-8:.2f} m {xx-3:.2f} {y+h-2:.2f} l S")
    return "\n".join(cmds)


def make_pdf(df: pd.DataFrame, moves: pd.DataFrame, zones: pd.DataFrame, approved: pd.DataFrame, blocked: pd.DataFrame) -> None:
    pages: list[str] = []
    overview_cmds = ["BT /F1 14 Tf 36 580 Td (EXP-008 Major Movement Overview) Tj ET"]
    overview_cmds.append(chart_panel(df, 0, len(df) - 1, 36, 80, 720, 460, "ADAUSDT 4H close, EMA27, EMA200"))
    for _, move in moves.iterrows():
        x = 36 + int(move.name) / max(1, len(moves) - 1) * 700
        overview_cmds.append(f"BT /F1 7 Tf {x:.2f} 62 Td ({pdf_text(move['move_id'])}) Tj ET")
    pages.append("\n".join(overview_cmds))

    for _, move in moves.iterrows():
        lo = max(0, int(move["start_i"]) - 24)
        hi = min(len(df) - 1, int(move["end_i"]) + 24)
        move_zones = zones[zones["move_id"] == move["move_id"]]
        move_approved = approved[approved["move_id"] == move["move_id"]]
        move_blocked = blocked[blocked["move_id"] == move["move_id"]]
        title = f"{move['move_id']} {move['direction']} labels and zones"
        cmds = ["BT /F1 14 Tf 36 580 Td (EXP-008 Movement Detail) Tj ET"]
        cmds.append(chart_panel(df, lo, hi, 36, 120, 720, 400, title, move, move_zones, move_approved, move_blocked))
        legend = "green=start/primary, blue=secondary, red=blocked, gray=end; shaded bands=retrospective zones"
        cmds.append(f"BT /F1 8 Tf 36 92 Td ({pdf_text(legend)}) Tj ET")
        pages.append("\n".join(cmds))
    write_pdf_pages(pages, OUT / "EXP008_MAJOR_MOVE_ENTRY_OVERVIEW.pdf")


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if df.empty:
        return "_empty_"
    view = df.copy()
    if max_rows is not None:
        view = view.head(max_rows)
    cols = list(view.columns)
    rows = []
    for _, row in view.iterrows():
        rows.append([str(row[c]).replace("\n", " ") for c in cols])
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = ["| " + " | ".join(vals) + " |" for vals in rows]
    suffix = []
    if max_rows is not None and len(df) > max_rows:
        suffix.append(f"\n_Table truncated to {max_rows} of {len(df)} rows._")
    return "\n".join([header, sep] + body + suffix)


def write_report(
    moves: pd.DataFrame,
    zones: pd.DataFrame,
    approved: pd.DataFrame,
    blocked: pd.DataFrame,
    mapped: pd.DataFrame,
    diagnosis: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    mature_zones = ["ZONE_4_MATURE_MOVE", "ZONE_5_LATE_MOVE", "ZONE_6_EXHAUSTION_OR_CHOP"]
    inside = mapped[mapped["move_id"] != "OUTSIDE_MAJOR_MOVE"] if not mapped.empty else pd.DataFrame()
    mature_share = float(inside["zone"].isin(mature_zones).mean()) if not inside.empty else 0.0
    max_signals = int(diagnosis["exp007_signal_count"].max()) if not diagnosis.empty else 0
    median_signals = float(diagnosis["exp007_signal_count"].median()) if not diagnosis.empty else 0.0
    ambiguous = moves[moves["confidence"] != "HIGH"]["move_id"].tolist()
    verdict = "PARTIAL_ENTRY_STRUCTURE"
    if len(moves) == 0:
        verdict = "DATA_INSUFFICIENT"
    elif moves["confidence"].eq("LOW").sum() >= 3:
        verdict = "GLOBAL_MOVE_BOUNDARIES_AMBIGUOUS"

    lines = [
        "# EXP-008 — Major Move Entry Labeling",
        "",
        "## Scope",
        "",
        "ADAUSDT 4H, 2023-07-01 00:00 UTC -> 2024-12-31 20:00 UTC. Data after 2024-12-31 was not used.",
        "Irobot was used as a read-only data source. No PnL, backtest, stop, exit, optimization, or mass trade generation was performed.",
        "",
        "## Method",
        "",
        "Major movements were marked retrospectively with a coarse local-extrema window of 36 bars and a minimum absolute close-to-close move of 25%.",
        "This method is used only to create a reference visual map. It is not a live boundary detector and not a ZigZag proof.",
        "Each movement received at most one `PRIMARY_ENTRY`, one `OPTIONAL_SECONDARY_ENTRY`, and three blocked examples.",
        "",
        "## Required Answers",
        "",
        f"1. Major movements found: {len(moves)}.",
        f"2. `PRIMARY_ENTRY` labels: {(approved['entry_label'] == 'PRIMARY_ENTRY').sum()}.",
        f"3. `OPTIONAL_SECONDARY_ENTRY` labels: {(approved['entry_label'] == 'OPTIONAL_SECONDARY_ENTRY').sum()}.",
        f"4. `BLOCKED_EXAMPLES`: {len(blocked)}.",
        f"5. EXP-007 signals per major movement: max {max_signals}, median {median_signals:.1f}; details are in `artifacts/one_entry_per_move_diagnosis.csv`.",
        f"6. Share of mapped EXP-007 signals in mature/late/exhaustion zones: {mature_share:.1%}.",
        "7. Early approved labels differ mainly by lower movement age and lower completed-fraction; late blocked labels can still have acceptable EMA direction, so EMA proximity alone does not separate them.",
        "8. EMA27/EMA200 is useful for direction context, but it is not enough to decide timing inside one already-running movement.",
        "9. Timing needs movement age, completed fraction, whether the entry is the first same-move label, and whether the move is already mature or exhausting.",
        "10. The reference rule `maximum one primary entry per major movement` is useful diagnostically: it directly removes repeated same-move signals without changing EMA direction logic.",
        "11. One causal start detector cannot be formulated yet from this label pass; the labels expose timing structure but remain retrospective.",
        f"12. Ambiguous cases: {', '.join(ambiguous) if ambiguous else 'none at current coarse boundary confidence'}.",
        "",
        "## Movement Summary",
        "",
        markdown_table(moves.drop(columns=["start_i", "end_i"])),
        "",
        "## Good vs Blocked Feature Summary",
        "",
        markdown_table(comparison),
        "",
        "## EXP-007 Diagnostic",
        "",
        "Existing EXP-007 signal timestamps were mapped into this reference movement map for diagnosis only. EXP-008 did not recompute trades or PnL.",
    ]
    if not diagnosis.empty:
        lines.extend(["", markdown_table(diagnosis)])
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            verdict,
        ]
    )
    (EXP / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    df = load_ohlc()
    moves = find_major_moves(df)
    zones = build_zones(df, moves)
    approved, blocked = build_labels(df, moves, zones)
    mapped, diagnosis = map_exp007_signals(df, moves, zones)
    comparison = compare_good_vs_blocked(approved, blocked)

    moves.drop(columns=["start_i", "end_i"]).to_csv(OUT / "major_moves.csv", index=False)
    zones.drop(columns=["start_i", "end_i"]).to_csv(OUT / "move_zones.csv", index=False)
    approved.to_csv(OUT / "approved_entries.csv", index=False)
    blocked.to_csv(OUT / "blocked_entries.csv", index=False)
    mapped.to_csv(OUT / "exp007_signals_mapped_to_moves.csv", index=False)
    comparison.to_csv(OUT / "good_vs_blocked_features.csv", index=False)
    diagnosis.to_csv(OUT / "one_entry_per_move_diagnosis.csv", index=False)
    write_pine(moves, zones, approved, blocked)
    make_pdf(df, moves, zones, approved, blocked)
    write_report(moves, zones, approved, blocked, mapped, diagnosis, comparison)
    print(f"EXP-008 complete: {len(moves)} major movements, {len(approved)} approved labels, {len(blocked)} blocked labels")


if __name__ == "__main__":
    main()
