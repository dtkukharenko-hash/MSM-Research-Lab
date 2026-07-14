#!/usr/bin/env python3
"""EXP-011B R3: LONG dispute episode chains on ADAUSDT 4H.

Uses saved EXP-011 Binance spot 4H OHLC. R3 preserves V1/R2 outputs, adds
episode chains with fixed recovery probation, and does not use Irobot, ZigZag,
clustering, BACKBONE_C, Technical Ratings, backtest, PnL, entries, stops, or
future period data.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-011B_LONG_CONFLICT_WINDOWS"
OUT = EXP / "artifacts"
SOURCE = ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv"
START = pd.Timestamp("2023-10-18 00:00:00")
END = pd.Timestamp("2024-01-08 23:59:59.999")
END_BOUNDARY = pd.Timestamp("2024-01-09 00:00:00")
MERGE_GAP_BARS = 6
MERGE_EMA200_MAJORITY = 2.0 / 3.0
RECOVERY_PROBATION_BARS = 24
NEW_CONFIGURATION_PROBATION_BARS = 8


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(SOURCE, parse_dates=["open_time", "close_time"])
    required = ["open_time", "close_time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing OHLC columns: {missing}")
    if not df["open_time"].is_monotonic_increasing:
        raise RuntimeError("4H OHLC is not sorted")
    if df["open_time"].duplicated().any():
        raise RuntimeError("4H OHLC has duplicate open_time")
    if df["open_time"].max() >= pd.Timestamp("2025-01-01") or df["close_time"].max() >= pd.Timestamp("2025-01-01"):
        raise RuntimeError("Forbidden 2025+ source data detected")
    if not df["open_time"].diff().dropna().eq(pd.Timedelta(hours=4)).all():
        raise RuntimeError("4H OHLC is not continuous")
    if df["open_time"].dt.hour.mod(4).ne(0).any():
        raise RuntimeError("4H OHLC is not UTC 4H aligned")
    durations = df["close_time"] - df["open_time"]
    if not durations.eq(pd.Timedelta(hours=4) - pd.Timedelta(milliseconds=1)).all():
        raise RuntimeError("4H OHLC has incomplete bars")
    if df["open_time"].min() > START or df["close_time"].max() < END:
        raise RuntimeError("4H OHLC does not cover research period")
    return df[required].copy()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema27"] = out["close"].ewm(span=27, adjust=False).mean()
    out["ema200"] = out["close"].ewm(span=200, adjust=False).mean()
    out["ema_gap"] = out["ema27"] - out["ema200"]
    out["ema_gap_pct"] = out["ema_gap"] / out["ema200"].replace(0, np.nan) * 100.0
    out["ema27_change_1"] = out["ema27"] - out["ema27"].shift(1)
    out["ema27_change_2"] = out["ema27"] - out["ema27"].shift(2)
    out["ema27_slope_3"] = (out["ema27"] / out["ema27"].shift(3) - 1.0) / 3.0
    out["ema200_change_1"] = out["ema200"] - out["ema200"].shift(1)
    out["ema200_slope_6"] = (out["ema200"] / out["ema200"].shift(6) - 1.0) / 6.0
    out["ema_gap_change_1"] = out["ema_gap"] - out["ema_gap"].shift(1)
    out["ema_gap_change_3"] = out["ema_gap"] - out["ema_gap"].shift(3)
    out["base_long_context"] = (out["ema27"] > out["ema200"]) & (out["ema200_slope_6"] > 0)
    out["long_context"] = out["base_long_context"]
    out["price_aligned"] = out["close"] > out["ema27"]
    out["fast_aligned"] = out["ema27_change_1"] > 0
    out["gap_aligned"] = out["ema_gap_change_1"] >= 0
    out["alignment_score"] = out[["price_aligned", "fast_aligned", "gap_aligned"]].sum(axis=1).astype(int)
    out["fully_aligned_long_bar"] = out["base_long_context"] & (out["alignment_score"] == 3)
    out["price_discordance"] = out["close"] <= out["ema27"]
    out["fast_discordance"] = out["ema27_change_1"] <= 0
    out["gap_discordance"] = out["ema_gap_change_1"] < 0
    out["discordance_score"] = out[["price_discordance", "fast_discordance", "gap_discordance"]].sum(axis=1).astype(int)
    out["core_trigger"] = (
        out["base_long_context"]
        & (out["ema27_change_1"] < 0)
        & ((out["ema27_change_2"] < 0) | (out["ema27_slope_3"] < 0))
        & (out["close"] < out["ema27"])
    )
    out["recovered_long_bar"] = (
        (out["ema27"] > out["ema200"])
        & (out["ema200_slope_6"] > 0)
        & (out["close"] > out["ema27"])
        & (out["ema27_change_1"] > 0)
        & (out["ema_gap_change_1"] >= 0)
    )
    out["new_down_configuration_bar"] = (
        (out["ema27"] < out["ema200"])
        & (out["close"] < out["ema27"])
        & (out["ema27_change_1"] < 0)
        & (out["ema_gap_change_1"] <= 0)
    )
    out["ema_cross_event"] = (out["ema27"] <= out["ema200"]) & (out["ema27"].shift(1) > out["ema200"].shift(1))
    out["depth"] = np.where(out["ema27"] > out["ema200"], (out["ema27"] - out["close"]) / (out["ema27"] - out["ema200"]), np.nan)
    return out


def diagnostic_pretrigger(df: pd.DataFrame, pos: int) -> dict[str, object]:
    prev = df.iloc[max(0, pos - 6) : pos]
    if prev.empty:
        return {
            "prev6_fraction_close_above_ema27": math.nan,
            "prev6_positive_ema27_change_count": 0,
            "prev6_already_below_ema27": False,
            "prev6_gap_contracting": False,
        }
    return {
        "prev6_fraction_close_above_ema27": float((prev["close"] > prev["ema27"]).mean()),
        "prev6_positive_ema27_change_count": int((prev["ema27_change_1"] > 0).sum()),
        "prev6_already_below_ema27": bool((prev["close"] < prev["ema27"]).any()),
        "prev6_gap_contracting": bool((prev["ema_gap_change_1"] < 0).any()),
    }


def find_raw_events(period: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = period.reset_index(drop=True).copy()
    df["raw_event_id"] = ""
    events: list[dict[str, object]] = []
    active_marks = [False] * len(df)
    i = 0
    while i < len(df):
        row = df.iloc[i]
        prev3_active = any(active_marks[max(0, i - 3) : i])
        if (not bool(row["core_trigger"])) or prev3_active:
            i += 1
            continue
        raw_id = f"RC{len(events)+1:03d}"
        start_i = i
        reset_run: list[int] = []
        end_i = len(df) - 1
        end_reason = "OPEN_AT_PERIOD_END"
        reset_effective_time = pd.NaT
        reset_confirmation_time = pd.NaT
        j = i
        while j < len(df):
            r = df.iloc[j]
            if r["ema27"] <= r["ema200"]:
                end_i = j
                end_reason = "EMA_CROSS"
                break
            reset_bar = bool((r["close"] > r["ema27"]) and (r["ema27_change_1"] > 0) and (r["ema_gap_change_1"] >= 0))
            reset_run = [*reset_run, j] if reset_bar else []
            if len(reset_run) >= 3:
                end_i = j
                end_reason = "FULL_RESET_CONFIRMED"
                reset_effective_time = df.iloc[reset_run[0]]["close_time"]
                reset_confirmation_time = r["close_time"]
                break
            j += 1
        for k in range(start_i, end_i + 1):
            active_marks[k] = True
            df.at[k, "raw_event_id"] = raw_id
        events.append(
            {
                "raw_event_id": raw_id,
                "section_id": "",
                "trigger_time": row["close_time"],
                "trigger_close": row["close"],
                "ema27": row["ema27"],
                "ema200": row["ema200"],
                "ema27_change_1": row["ema27_change_1"],
                "ema27_change_2": row["ema27_change_2"],
                "ema27_slope_3": row["ema27_slope_3"],
                "ema200_slope_6": row["ema200_slope_6"],
                "ema_gap_pct": row["ema_gap_pct"],
                "end_time": df.iloc[end_i]["close_time"],
                "end_reason": end_reason,
                "reset_effective_time": reset_effective_time,
                "reset_confirmation_time": reset_confirmation_time,
                "duration_4h_bars": end_i - start_i + 1,
                "start_pos": start_i,
                "end_pos": end_i,
                **diagnostic_pretrigger(df, start_i),
            }
        )
        i = end_i + 1
    return pd.DataFrame(events), df


def should_merge_v1(df: pd.DataFrame, prev: pd.Series, cur: pd.Series) -> bool:
    gap_start = int(prev["end_pos"]) + 1
    gap_end = int(cur["start_pos"]) - 1
    gap_len = gap_end - gap_start + 1
    if gap_len < 0:
        return True
    if gap_len > MERGE_GAP_BARS:
        return False
    gap = df.iloc[gap_start : gap_end + 1]
    if gap.empty:
        return True
    if not bool((gap["ema27"] > gap["ema200"]).all()):
        return False
    return float((gap["ema200_slope_6"] >= 0).mean()) >= MERGE_EMA200_MAJORITY


def max_consecutive_true(values: pd.Series) -> int:
    best = cur = 0
    for val in values.astype(bool).tolist():
        if val:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def count_recross(close_below: pd.Series) -> int:
    vals = close_below.astype(bool).tolist()
    return int(sum(1 for a, b in zip(vals[:-1], vals[1:]) if a != b))


def build_sections_v1(events: pd.DataFrame, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if events.empty:
        return pd.DataFrame(), events, df
    groups: list[list[int]] = [[0]]
    for idx in range(1, len(events)):
        if should_merge_v1(df, events.iloc[groups[-1][-1]], events.iloc[idx]):
            groups[-1].append(idx)
        else:
            groups.append([idx])
    sections = []
    for n, group in enumerate(groups, start=1):
        sid = f"LC{n:03d}"
        evs = events.iloc[group].copy()
        start_pos = int(evs["start_pos"].min())
        end_pos = int(evs["end_pos"].max())
        sub = df.iloc[start_pos : end_pos + 1].copy()
        first = sub.iloc[0]
        below = sub["close"] < sub["ema27"]
        depths = sub["depth"].dropna()
        sections.append(
            {
                "section_id": sid,
                "start_time": first["close_time"],
                "end_time": sub.iloc[-1]["close_time"],
                "duration_4h_bars": int(len(sub)),
                "raw_event_count": int(len(evs)),
                "technical_end_reason": evs["end_reason"].tolist()[-1],
                "start_close": first["close"],
                "start_ema27": first["ema27"],
                "start_ema200": first["ema200"],
                "start_ema27_slope_3": first["ema27_slope_3"],
                "start_ema200_slope_6": first["ema200_slope_6"],
                "start_ema_gap_pct": first["ema_gap_pct"],
                "bars_close_below_ema27": int(below.sum()),
                "fraction_close_below_ema27": float(below.mean()),
                "bars_close_above_ema27": int((sub["close"] > sub["ema27"]).sum()),
                "recross_count_ema27": count_recross(below),
                "min_close": float(sub["close"].min()),
                "max_close": float(sub["close"].max()),
                "min_ema_gap_pct": float(sub["ema_gap_pct"].min()),
                "max_ema_gap_pct": float(sub["ema_gap_pct"].max()),
                "max_depth": float(depths.max()) if not depths.empty else math.nan,
                "median_depth": float(depths.median()) if not depths.empty else math.nan,
                "max_consecutive_bars_below_ema27": max_consecutive_true(below),
                "ema_cross_reached": bool((evs["end_reason"] == "EMA_CROSS").any()),
                "open_at_period_end": bool(evs["end_reason"].tolist()[-1] == "OPEN_AT_PERIOD_END"),
            }
        )
        for idx in group:
            events.at[idx, "section_id"] = sid
        df.loc[df["raw_event_id"].isin(evs["raw_event_id"]), "section_id"] = sid
    return pd.DataFrame(sections), events, df


def find_last_aligned_run(df: pd.DataFrame, trigger_idx: int) -> dict[str, object]:
    search_start = max(0, trigger_idx - 30)
    for end in range(trigger_idx - 1, search_start + 2, -1):
        window = df.iloc[end - 3 : end + 1]
        if len(window) == 4 and int(window["fully_aligned_long_bar"].sum()) >= 3:
            true_idx = window.index[window["fully_aligned_long_bar"]].tolist()
            run_start = min(true_idx)
            run_end = max(true_idx)
            while run_start - 1 >= 0 and bool(df.iloc[run_start - 1]["fully_aligned_long_bar"]):
                run_start -= 1
            while run_end + 1 < trigger_idx and bool(df.iloc[run_end + 1]["fully_aligned_long_bar"]):
                run_end += 1
            return {
                "last_aligned_run_found": True,
                "last_aligned_run_start_idx": int(run_start),
                "last_aligned_run_end_idx": int(run_end),
                "last_aligned_run_start_open_time": df.iloc[run_start]["open_time"],
                "last_aligned_run_end_open_time": df.iloc[run_end]["open_time"],
                "last_aligned_run_length": int(run_end - run_start + 1),
                "bars_from_aligned_run_to_trigger": int(trigger_idx - run_end),
            }
    return {
        "last_aligned_run_found": False,
        "last_aligned_run_start_idx": -1,
        "last_aligned_run_end_idx": -1,
        "last_aligned_run_start_open_time": pd.NaT,
        "last_aligned_run_end_open_time": pd.NaT,
        "last_aligned_run_length": 0,
        "bars_from_aligned_run_to_trigger": math.nan,
    }


def aligned_restored_3_of_4(df: pd.DataFrame, start: int, end: int) -> bool:
    for i in range(max(start + 3, 3), end + 1):
        if int(df.iloc[i - 3 : i + 1]["fully_aligned_long_bar"].sum()) >= 3:
            return True
    return False


def find_dispute_start(df: pd.DataFrame, trigger_idx: int, run: dict[str, object]) -> tuple[int, bool]:
    if run["last_aligned_run_found"]:
        start = int(run["last_aligned_run_end_idx"]) + 1
    else:
        start = max(0, trigger_idx - 12)
    for i in range(start, trigger_idx + 1):
        row = df.iloc[i]
        strong = bool(row["base_long_context"] and row["discordance_score"] >= 2)
        sequential = (
            i + 1 <= trigger_idx
            and bool(df.iloc[i]["base_long_context"] and df.iloc[i]["discordance_score"] >= 1)
            and bool(df.iloc[i + 1]["base_long_context"] and df.iloc[i + 1]["discordance_score"] >= 1)
        )
        if strong or sequential:
            if run["last_aligned_run_found"] or not aligned_restored_3_of_4(df, i, trigger_idx):
                return i, False
    return trigger_idx, True


def find_resolution(df: pd.DataFrame, trigger_idx: int) -> dict[str, object]:
    for i in range(trigger_idx, len(df)):
        window = df.iloc[max(0, i - 3) : i + 1]
        if len(window) >= 4 and int(window["recovered_long_bar"].sum()) >= 3:
            cand = window.index[window["recovered_long_bar"]].tolist()[0]
            return {
                "resolution_candidate_idx": int(cand),
                "dispute_end_idx": int(i),
                "resolution_kind": "RECOVERED_LONG",
                "confirmation_bars_used": int(window["recovered_long_bar"].sum()),
            }
        if len(window) >= 4 and int(window["new_down_configuration_bar"].sum()) >= 3:
            cand = window.index[window["new_down_configuration_bar"]].tolist()[0]
            return {
                "resolution_candidate_idx": int(cand),
                "dispute_end_idx": int(i),
                "resolution_kind": "NEW_DOWN_CONFIGURATION",
                "confirmation_bars_used": int(window["new_down_configuration_bar"].sum()),
            }
    last = len(df) - 1
    return {
        "resolution_candidate_idx": last,
        "dispute_end_idx": last,
        "resolution_kind": "OPEN_AT_TRAIN_END",
        "confirmation_bars_used": 0,
    }


def primary_windows(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    trigger_indices = df.index[df["core_trigger"]].tolist()
    for n, trig in enumerate(trigger_indices, start=1):
        run = find_last_aligned_run(df, trig)
        dispute_start, fallback = find_dispute_start(df, trig, run)
        res = find_resolution(df, trig)
        rows.append(
            {
                "primary_id": f"PW{n:03d}",
                "core_trigger_idx": int(trig),
                "core_trigger_open_time": df.iloc[trig]["open_time"],
                "dispute_start_idx": int(dispute_start),
                "dispute_end_idx": int(res["dispute_end_idx"]),
                "resolution_candidate_idx": int(res["resolution_candidate_idx"]),
                "resolution_kind": res["resolution_kind"],
                "confirmation_bars_used": res["confirmation_bars_used"],
                "start_fallback_used": bool(fallback),
                **run,
            }
        )
    return pd.DataFrame(rows)


def confirmed_recovered_between(df: pd.DataFrame, start: int, end: int) -> bool:
    if end < start:
        return False
    for i in range(max(start + 3, 3), end + 1):
        if int(df.iloc[i - 3 : i + 1]["recovered_long_bar"].sum()) >= 3:
            return True
    return False


def merge_primary_windows(df: pd.DataFrame, pw: pd.DataFrame) -> list[list[int]]:
    if pw.empty:
        return []
    groups: list[list[int]] = [[0]]
    for idx in range(1, len(pw)):
        prev_group = groups[-1]
        prev_end = int(pw.iloc[prev_group]["dispute_end_idx"].max())
        cur_start = int(pw.iloc[idx]["dispute_start_idx"])
        gap_start = prev_end + 1
        gap_end = cur_start - 1
        overlap = cur_start <= prev_end
        no_recovered = not confirmed_recovered_between(df, gap_start, gap_end)
        gap_len = max(0, gap_end - gap_start + 1)
        few_aligned = int(df.iloc[gap_start : gap_end + 1]["fully_aligned_long_bar"].sum()) < 3 if gap_len else True
        if overlap or no_recovered or (gap_len < 4 and few_aligned):
            groups[-1].append(idx)
        else:
            groups.append([idx])
    return groups


def next_boundary(df: pd.DataFrame, idx: int) -> pd.Timestamp:
    return df.iloc[idx + 1]["open_time"] if idx + 1 < len(df) else END_BOUNDARY


def build_v2_sections(df: pd.DataFrame, pw: pd.DataFrame, old_sections: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    groups = merge_primary_windows(df, pw)
    sections = []
    events = []
    df = df.copy()
    df["section_id"] = ""
    df["section_phase"] = "OUTSIDE_SECTION"
    for sidx, group in enumerate(groups, start=1):
        sid = f"LC{sidx:03d}"
        wins = pw.iloc[group].copy()
        start_idx = int(wins["dispute_start_idx"].min())
        end_idx = int(wins["dispute_end_idx"].max())
        first_trigger_idx = int(wins["core_trigger_idx"].min())
        last_trigger_idx = int(wins["core_trigger_idx"].max())
        last_win = wins.sort_values("dispute_end_idx").iloc[-1]
        res_cand_idx = int(last_win["resolution_candidate_idx"])
        resolution_kind = str(last_win["resolution_kind"])
        aligned_candidates = wins[
            (wins["last_aligned_run_found"])
            & (wins["last_aligned_run_end_idx"] >= 0)
            & (wins["last_aligned_run_end_idx"] < start_idx)
        ].copy()
        run_found = not aligned_candidates.empty
        if run_found:
            chosen_aligned = aligned_candidates.sort_values("last_aligned_run_end_idx").iloc[-1]
            aligned_start = int(chosen_aligned["last_aligned_run_start_idx"])
            aligned_end = int(chosen_aligned["last_aligned_run_end_idx"])
        else:
            aligned_start = -1
            aligned_end = -1
        display_start_idx = max(0, start_idx - 12)
        display_end_idx = min(len(df) - 1, end_idx + 8)
        display_end_boundary = END_BOUNDARY if resolution_kind == "OPEN_AT_TRAIN_END" else min(next_boundary(df, display_end_idx), END_BOUNDARY)
        dispute_end_boundary = next_boundary(df, end_idx)
        if dispute_end_boundary > END_BOUNDARY:
            dispute_end_boundary = END_BOUNDARY
        core_trigger_count = int(len(wins))
        ema_cross_count = int(df.iloc[start_idx : end_idx + 1]["ema_cross_event"].sum())
        old_map = map_old_sections(df, old_sections, start_idx, end_idx)
        sections.append(
            {
                "section_id": sid,
                "display_start_open_time": df.iloc[display_start_idx]["open_time"],
                "last_aligned_run_start_open_time": df.iloc[aligned_start]["open_time"] if aligned_start >= 0 else pd.NaT,
                "last_aligned_run_end_open_time": df.iloc[aligned_end]["open_time"] if aligned_end >= 0 else pd.NaT,
                "dispute_start_open_time": df.iloc[start_idx]["open_time"],
                "first_core_trigger_open_time": df.iloc[first_trigger_idx]["open_time"],
                "last_core_trigger_open_time": df.iloc[last_trigger_idx]["open_time"],
                "resolution_candidate_open_time": df.iloc[res_cand_idx]["open_time"],
                "dispute_end_open_time": df.iloc[end_idx]["open_time"],
                "dispute_end_boundary_time": dispute_end_boundary,
                "display_end_boundary_time": display_end_boundary,
                "resolution_kind": resolution_kind,
                "duration_dispute_bars": int(end_idx - start_idx + 1),
                "duration_display_bars": int(display_end_idx - display_start_idx + 1),
                "core_trigger_count": core_trigger_count,
                "ema_cross_count": ema_cross_count,
                "last_aligned_run_found": run_found,
                "start_fallback_used": bool(wins["start_fallback_used"].any()),
                "bars_added_before_first_trigger": int(first_trigger_idx - start_idx),
                "bars_after_last_trigger": int(end_idx - last_trigger_idx),
                "old_section_mapping": old_map,
                "open_at_train_end": bool(resolution_kind == "OPEN_AT_TRAIN_END"),
                "_start_idx": start_idx,
                "_end_idx": end_idx,
            }
        )
        df.loc[display_start_idx : start_idx - 1, "section_phase"] = "CONTEXT_BEFORE"
        if aligned_start >= 0:
            df.loc[aligned_start:aligned_end, "section_phase"] = "LAST_ALIGNED_RUN"
        df.loc[start_idx : first_trigger_idx - 1, "section_phase"] = "EARLY_DISPUTE"
        df.loc[first_trigger_idx : max(first_trigger_idx, res_cand_idx - 1), "section_phase"] = "POST_TRIGGER_DISPUTE"
        df.loc[res_cand_idx:end_idx, "section_phase"] = "RESOLUTION_CONFIRMATION"
        df.loc[end_idx + 1 : display_end_idx, "section_phase"] = "CONTEXT_AFTER"
        df.loc[start_idx:end_idx, "section_id"] = sid
        add_events(events, sid, df, wins, aligned_start, aligned_end, start_idx, res_cand_idx, end_idx, resolution_kind)
    sections_df = pd.DataFrame(sections)
    return sections_df.drop(columns=["_start_idx", "_end_idx"], errors="ignore"), pd.DataFrame(events), df


def map_old_sections(df: pd.DataFrame, old_sections: pd.DataFrame, start_idx: int, end_idx: int) -> str:
    matches = []
    for row in old_sections.itertuples():
        old_start = pd.Timestamp(row.start_time)
        old_end = pd.Timestamp(row.end_time)
        old_idx = df.index[(df["close_time"] >= old_start) & (df["close_time"] <= old_end)].tolist()
        if old_idx and max(old_idx) >= start_idx and min(old_idx) <= end_idx:
            matches.append(row.section_id)
    return ";".join(matches) if matches else "NO_V1_OVERLAP"


def add_events(events: list[dict[str, object]], sid: str, df: pd.DataFrame, wins: pd.DataFrame, aligned_start: int, aligned_end: int, start_idx: int, res_cand_idx: int, end_idx: int, resolution_kind: str) -> None:
    seq = 1

    def push(event_type: str, idx: int, related: str = "", details: str = "") -> None:
        nonlocal seq
        events.append(
            {
                "section_id": sid,
                "event_type": event_type,
                "event_open_time": df.iloc[idx]["open_time"],
                "event_close_time": df.iloc[idx]["close_time"],
                "event_sequence_number": seq,
                "related_core_trigger_id": related,
                "details": details,
            }
        )
        seq += 1

    if aligned_start >= 0:
        push("LAST_ALIGNED_RUN_START", aligned_start)
        push("LAST_ALIGNED_RUN_END", aligned_end)
    push("DISPUTE_START", start_idx)
    for n, row in enumerate(wins.sort_values("core_trigger_idx").itertuples(), start=1):
        push("CORE_TRIGGER", int(row.core_trigger_idx), f"CORE{n:03d}", row.primary_id)
    for idx in df.index[(df["ema_cross_event"]) & (df.index >= start_idx) & (df.index <= end_idx)].tolist():
        push("EMA_CROSS", int(idx))
    push("RESOLUTION_CANDIDATE", res_cand_idx, details=resolution_kind)
    push("TRAIN_PERIOD_END" if resolution_kind == "OPEN_AT_TRAIN_END" else "DISPUTE_END", end_idx, details=resolution_kind)


def boundary_comparison(df: pd.DataFrame, old_sections: pd.DataFrame, new_sections: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for old in old_sections.itertuples():
        old_idx = df.index[(df["close_time"] >= pd.Timestamp(old.start_time)) & (df["close_time"] <= pd.Timestamp(old.end_time))].tolist()
        if not old_idx:
            continue
        old_start_idx, old_end_idx = min(old_idx), max(old_idx)
        mapped = []
        for new in new_sections.itertuples():
            new_start_idx = df.index[df["open_time"] == pd.Timestamp(new.dispute_start_open_time)].tolist()[0]
            new_end_idx = df.index[df["open_time"] == pd.Timestamp(new.dispute_end_open_time)].tolist()[0]
            if new_end_idx >= old_start_idx and new_start_idx <= old_end_idx:
                mapped.append((new, new_start_idx, new_end_idx))
        if not mapped:
            rows.append(
                {
                    "old_section_id": old.section_id,
                    "new_section_id": "",
                    "old_start_time": old.start_time,
                    "new_dispute_start_time": "",
                    "old_end_time": old.end_time,
                    "new_dispute_end_time": "",
                    "bars_added_left": "",
                    "bars_added_right": "",
                    "old_raw_event_count": old.raw_event_count,
                    "new_core_trigger_count": "",
                    "mapping_comment": "old section has no overlapping R2 section",
                }
            )
        for new, new_start_idx, new_end_idx in mapped:
            rows.append(
                {
                    "old_section_id": old.section_id,
                    "new_section_id": new.section_id,
                    "old_start_time": old.start_time,
                    "new_dispute_start_time": new.dispute_start_open_time,
                    "old_end_time": old.end_time,
                    "new_dispute_end_time": new.dispute_end_open_time,
                    "bars_added_left": int(old_start_idx - new_start_idx),
                    "bars_added_right": int(new_end_idx - old_end_idx),
                    "old_raw_event_count": old.raw_event_count,
                    "new_core_trigger_count": new.core_trigger_count,
                    "mapping_comment": "overlap mapped by bar interval",
                }
            )
    return pd.DataFrame(rows)


def pine_script_r2(sections: pd.DataFrame, events: pd.DataFrame) -> str:
    options = ", ".join([f'"{x}"' for x in ["ALL", *sections["section_id"].tolist()]])
    ids = ", ".join([f'"{x}"' for x in sections["section_id"]])
    starts = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["dispute_start_open_time"])
    ends = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["dispute_end_boundary_time"])
    dstarts = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["display_start_open_time"])
    dends = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["display_end_boundary_time"])
    event_ids = ", ".join([f'"{x}"' for x in events["section_id"]])
    event_types = ", ".join([f'"{x}"' for x in events["event_type"]])
    event_times = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in events["event_open_time"])
    return f'''//@version=6
indicator("EXP-011B Full Long Dispute Sections R2", overlay=true, max_labels_count=500, max_lines_count=500, max_boxes_count=100)

showDisputeArea = input.bool(true, "showDisputeArea")
showDisplayContext = input.bool(true, "showDisplayContext")
showLastAlignedRun = input.bool(true, "showLastAlignedRun")
showDisputeStart = input.bool(true, "showDisputeStart")
showCoreTriggers = input.bool(true, "showCoreTriggers")
showEmaCrossEvents = input.bool(true, "showEmaCrossEvents")
showResolutionCandidate = input.bool(true, "showResolutionCandidate")
showDisputeEnd = input.bool(true, "showDisputeEnd")
showSectionId = input.bool(true, "showSectionId")
showOnlySelectedSection = input.bool(false, "showOnlySelectedSection")
selectedSection = input.string("ALL", "selectedSection", options=[{options}])

var string[] sectionIds = array.from({ids})
var int[] disputeStarts = array.from({starts})
var int[] disputeEnds = array.from({ends})
var int[] displayStarts = array.from({dstarts})
var int[] displayEnds = array.from({dends})
var string[] eventSectionIds = array.from({event_ids})
var string[] eventTypes = array.from({event_types})
var int[] eventTimes = array.from({event_times})

f_visible(string id) =>
    selectedSection == "ALL" or id == selectedSection

f_mark(string eventType) =>
    eventType == "LAST_ALIGNED_RUN_END" ? "A" : eventType == "DISPUTE_START" ? "D" : eventType == "CORE_TRIGGER" ? "T" : eventType == "EMA_CROSS" ? "X" : eventType == "RESOLUTION_CANDIDATE" ? "R" : eventType == "TRAIN_PERIOD_END" ? "O" : eventType == "DISPUTE_END" ? "E" : ""

for i = 0 to array.size(sectionIds) - 1
    string sid = array.get(sectionIds, i)
    bool visible = f_visible(sid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(sid) : visible
    int st = array.get(disputeStarts, i)
    int en = array.get(disputeEnds, i)
    int ds = array.get(displayStarts, i)
    int de = array.get(displayEnds, i)
    bool atDisputeStart = time >= st and time[1] < st
    if visible and showDisplayContext and atDisputeStart
        box.new(ds, high, de, low, xloc=xloc.bar_time, bgcolor=color.new(color.gray, 94), border_color=color.new(color.gray, 78), extend=extend.none)
    if visible and showDisputeArea and atDisputeStart
        box.new(st, high, en, low, xloc=xloc.bar_time, bgcolor=color.new(color.yellow, 86), border_color=color.new(color.yellow, 20), extend=extend.none)
        if showSectionId
            label.new(st, high, sid, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.yellow, 0), textcolor=color.black, size=size.small)

for j = 0 to array.size(eventTimes) - 1
    string sid = array.get(eventSectionIds, j)
    string eventType = array.get(eventTypes, j)
    int tt = array.get(eventTimes, j)
    bool visible = f_visible(sid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(sid) : visible
    bool enabled = eventType == "LAST_ALIGNED_RUN_END" ? showLastAlignedRun : eventType == "DISPUTE_START" ? showDisputeStart : eventType == "CORE_TRIGGER" ? showCoreTriggers : eventType == "EMA_CROSS" ? showEmaCrossEvents : eventType == "RESOLUTION_CANDIDATE" ? showResolutionCandidate : eventType == "DISPUTE_END" or eventType == "TRAIN_PERIOD_END" ? showDisputeEnd : false
    bool atEvent = time >= tt and time[1] < tt
    string mark = f_mark(eventType)
    if visible and enabled and atEvent and mark != ""
        label.new(tt, close, mark, xloc=xloc.bar_time, style=label.style_label_left, color=color.new(color.black, 0), textcolor=color.white, size=size.tiny)
'''


def manual_full_review(sections: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "section_id": sections["section_id"],
            "auto_last_aligned_end": sections["last_aligned_run_end_open_time"],
            "auto_dispute_start": sections["dispute_start_open_time"],
            "auto_first_core_trigger": sections["first_core_trigger_open_time"],
            "auto_resolution_candidate": sections["resolution_candidate_open_time"],
            "auto_dispute_end": sections["dispute_end_open_time"],
            "auto_resolution_kind": sections["resolution_kind"],
            "valid_dispute_section": "",
            "last_aligned_assessment": "",
            "dispute_start_assessment": "",
            "corrected_dispute_start": "",
            "core_trigger_assessment": "",
            "dispute_end_assessment": "",
            "corrected_dispute_end": "",
            "resolution_kind_assessment": "",
            "split_required": "",
            "merge_required": "",
            "merge_with_section": "",
            "missing_preceding_events": "",
            "missing_following_events": "",
            "source_difference_suspected": "",
            "comment": "",
        }
    )


def idx_at(df: pd.DataFrame, ts: object) -> int:
    matches = df.index[df["open_time"] == pd.Timestamp(ts)].tolist()
    if not matches:
        raise RuntimeError(f"open_time not found in period: {ts}")
    return int(matches[0])


def boundary_at(df: pd.DataFrame, idx: int) -> pd.Timestamp:
    return min(next_boundary(df, idx), END_BOUNDARY)


def count_3_of_4_at(df: pd.DataFrame, idx: int, column: str, min_start: int = 0) -> tuple[bool, int]:
    if idx < 3 or idx - min_start < 3:
        return False, -1
    window = df.iloc[idx - 3 : idx + 1]
    if int(window.index.min()) < min_start:
        return False, -1
    good = window.index[window[column]].tolist()
    return len(good) >= 3, int(good[0]) if len(good) >= 3 else -1


def renewed_dispute_reason(df: pd.DataFrame, idx: int) -> tuple[bool, str, int]:
    row = df.iloc[idx]
    if bool(row["core_trigger"]):
        return True, "CORE_TRIGGER", idx
    if idx >= 1 and int((df.iloc[idx - 1 : idx + 1]["discordance_score"] >= 2).sum()) == 2:
        return True, "TWO_DISCORDANT_BARS", idx - 1
    if idx >= 2:
        tri = df.iloc[idx - 2 : idx + 1]
        below = tri.index[tri["close"] < tri["ema27"]].tolist()
        if len(below) >= 2 and bool(row["ema27_change_1"] < 0) and bool(row["ema_gap_change_1"] < 0):
            return True, "THREE_BAR_PRICE_FAST_GAP_DISPUTE", int(below[0])
    if bool(row["ema_cross_event"]):
        return True, "EMA27_CROSS_BELOW_EMA200", idx
    return False, "", idx


def recovery_probation(df: pd.DataFrame, effective_idx: int, detection_idx: int) -> dict[str, object]:
    start_idx = detection_idx + 1
    end_idx = min(len(df) - 1, detection_idx + RECOVERY_PROBATION_BARS)
    probation = df.iloc[start_idx : end_idx + 1]
    out: dict[str, object] = {
        "probation_start_idx": start_idx if start_idx < len(df) else -1,
        "probation_end_idx": end_idx,
        "probation_bars_available": int(len(probation)),
        "status": "CENSORED_BY_TRAIN_END",
        "failure_idx": -1,
        "failure_reason": "",
        "close_above_ema27_count": int((probation["close"] > probation["ema27"]).sum()),
        "ema27_nonnegative_count": int((probation["ema27_change_1"] >= 0).sum()),
        "gap_nonshrinking_count": int((probation["ema_gap_change_1"] >= 0).sum()),
        "final4_aligned_count": int(probation.tail(4)["fully_aligned_long_bar"].sum()) if len(probation) else 0,
    }
    for j in range(start_idx, end_idx + 1):
        failed, reason, fail_idx = renewed_dispute_reason(df, j)
        if failed:
            out.update({"status": "FAILED_RECOVERY", "failure_idx": fail_idx, "failure_reason": reason})
            return out
        if j >= 3 and int((df.iloc[j - 3 : j + 1]["close"] < df.iloc[j - 3 : j + 1]["ema27"]).sum()) >= 3 and bool(df.iloc[j]["ema27_change_1"] < 0):
            out.update({"status": "FAILED_RECOVERY", "failure_idx": j - 3, "failure_reason": "THREE_OF_FOUR_BELOW_EMA27"})
            return out
    if len(probation) < RECOVERY_PROBATION_BARS:
        return out
    confirmed = (
        bool((probation["ema27"] > probation["ema200"]).all())
        and out["close_above_ema27_count"] >= 18
        and out["ema27_nonnegative_count"] >= 16
        and out["gap_nonshrinking_count"] >= 14
        and out["final4_aligned_count"] >= 3
    )
    out["status"] = "CONFIRMED_RECOVERED_LONG" if confirmed else "FAILED_RECOVERY"
    if not confirmed:
        out["failure_idx"] = end_idx
        out["failure_reason"] = "RECOVERY_PROBATION_THRESHOLDS_NOT_MET"
    return out


def new_configuration_probation(df: pd.DataFrame, effective_idx: int, detection_idx: int) -> dict[str, object]:
    start_idx = detection_idx + 1
    end_idx = min(len(df) - 1, detection_idx + NEW_CONFIGURATION_PROBATION_BARS)
    probation = df.iloc[start_idx : end_idx + 1]
    out: dict[str, object] = {
        "probation_end_idx": end_idx,
        "probation_bars_available": int(len(probation)),
        "status": "CENSORED_BY_TRAIN_END",
        "failure_idx": -1,
        "failure_reason": "",
        "ema27_below_ema200_count": int((probation["ema27"] < probation["ema200"]).sum()),
        "close_below_ema27_count": int((probation["close"] < probation["ema27"]).sum()),
        "ema27_nonpositive_count": int((probation["ema27_change_1"] <= 0).sum()),
    }
    for j in range(start_idx, end_idx + 1):
        recovered, _ = count_3_of_4_at(df, j, "recovered_long_bar", effective_idx)
        stable_above = j >= 3 and int((df.iloc[j - 3 : j + 1]["close"] > df.iloc[j - 3 : j + 1]["ema27"]).sum()) >= 3
        if bool(df.iloc[j]["ema27"] > df.iloc[j]["ema200"]):
            out.update({"status": "NEW_CONFIGURATION_FAILED", "failure_idx": j, "failure_reason": "EMA27_RETURNED_ABOVE_EMA200"})
            return out
        if recovered:
            out.update({"status": "NEW_CONFIGURATION_FAILED", "failure_idx": j, "failure_reason": "RECOVERY_ATTEMPT_FORMED"})
            return out
        if stable_above:
            out.update({"status": "NEW_CONFIGURATION_FAILED", "failure_idx": j - 3, "failure_reason": "PRICE_RETURNED_ABOVE_EMA27"})
            return out
    if len(probation) < NEW_CONFIGURATION_PROBATION_BARS:
        return out
    confirmed = (
        out["ema27_below_ema200_count"] >= 7
        and out["close_below_ema27_count"] >= 6
        and out["ema27_nonpositive_count"] >= 6
    )
    out["status"] = "CONFIRMED_NEW_DOWN_CONFIGURATION" if confirmed else "NEW_CONFIGURATION_FAILED"
    if not confirmed:
        out["failure_idx"] = end_idx
        out["failure_reason"] = "NEW_CONFIGURATION_THRESHOLDS_NOT_MET"
    return out


def source_r2_for_span(df: pd.DataFrame, v2_sections: pd.DataFrame, start_idx: int, end_idx: int) -> str:
    matches = []
    for row in v2_sections.itertuples():
        s = idx_at(df, row.dispute_start_open_time)
        e = idx_at(df, row.dispute_end_open_time)
        if e >= start_idx and s <= end_idx:
            matches.append(row.section_id)
    return ";".join(matches)


def build_r3_sections(df: pd.DataFrame, v2_sections: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    r2_starts = [idx_at(df, row.dispute_start_open_time) for row in v2_sections.itertuples()]
    consumed_until = -1
    sections: list[dict[str, object]] = []
    episodes: list[dict[str, object]] = []
    recoveries: list[dict[str, object]] = []
    new_configs: list[dict[str, object]] = []
    events: list[dict[str, object]] = []
    features = df.copy()
    for col, default in [
        ("section_id", ""),
        ("episode_id", ""),
        ("core_trigger_id", ""),
        ("recovery_attempt_id", ""),
        ("new_configuration_attempt_id", ""),
        ("in_dispute", False),
        ("in_recovery_probation", False),
        ("in_new_configuration_probation", False),
        ("recovery_candidate_active", False),
        ("section_phase", "OUTSIDE_SECTION"),
    ]:
        features[col] = default

    def add_event(sid: str, eid: str, event_type: str, idx: int, details: str = "") -> None:
        events.append(
            {
                "section_id": sid,
                "episode_id": eid,
                "event_type": event_type,
                "event_open_time": df.iloc[idx]["open_time"],
                "event_close_time": df.iloc[idx]["close_time"],
                "details": details,
            }
        )

    for r2_pos, start_idx in enumerate(r2_starts):
        if start_idx <= consumed_until:
            continue
        r2_row = v2_sections.iloc[r2_pos]
        sid = f"LC{len(sections)+1:03d}"
        section_start = start_idx
        last_aligned = pd.Timestamp(r2_row["last_aligned_run_end_open_time"])
        first_core_idx = idx_at(df, r2_row["first_core_trigger_open_time"])
        current_episode_start = section_start
        episode_n = 1
        recovery_n = 0
        new_config_n = 0
        section_core_idxs: list[int] = []
        episode_core_idxs: list[int] = []
        failed_recovery_count = 0
        failed_new_config_count = 0
        exit_kind = "OPEN_AT_TRAIN_END"
        effective_idx = len(df) - 1
        confirmation_idx = len(df) - 1
        cursor = section_start
        add_event(sid, f"EP{episode_n:03d}", "DISPUTE_START", section_start)
        add_event(sid, f"EP{episode_n:03d}", "EPISODE_START", current_episode_start)

        while cursor < len(df):
            if bool(df.iloc[cursor]["core_trigger"]):
                cid = f"CORE{len(section_core_idxs)+1:03d}"
                section_core_idxs.append(cursor)
                episode_core_idxs.append(cursor)
                features.loc[cursor, "core_trigger_id"] = cid
                add_event(sid, f"EP{episode_n:03d}", "CORE_TRIGGER", cursor, cid)
            if bool(df.iloc[cursor]["ema_cross_event"]):
                add_event(sid, f"EP{episode_n:03d}", "EMA_CROSS", cursor)

            recovered, recovery_effective = count_3_of_4_at(df, cursor, "recovered_long_bar", current_episode_start)
            if recovered:
                recovery_n += 1
                rid = f"R{recovery_n:03d}"
                recovery = recovery_probation(df, recovery_effective, cursor)
                prob_start = int(recovery["probation_start_idx"])
                prob_end = int(recovery["probation_end_idx"])
                add_event(sid, f"EP{episode_n:03d}", "RECOVERY_ATTEMPT", recovery_effective, rid)
                episode_failure_idx = int(recovery["failure_idx"]) if recovery["status"] == "FAILED_RECOVERY" else -1
                episodes.append(make_episode_row(sid, episode_n, df, current_episode_start, episode_core_idxs, recovery_effective, episode_failure_idx, cursor, "RECOVERY_ATTEMPT"))
                recoveries.append(
                    {
                        "section_id": sid,
                        "episode_id": f"EP{episode_n:03d}",
                        "recovery_attempt_id": rid,
                        "recovery_effective_open_time": df.iloc[recovery_effective]["open_time"],
                        "recovery_detection_open_time": df.iloc[cursor]["open_time"],
                        "probation_start_open_time": df.iloc[prob_start]["open_time"] if prob_start >= 0 and prob_start < len(df) else pd.NaT,
                        "probation_end_open_time": df.iloc[prob_end]["open_time"],
                        "probation_bars_available": recovery["probation_bars_available"],
                        "recovery_status": recovery["status"],
                        "recovery_failure_open_time": df.iloc[int(recovery["failure_idx"])]["open_time"] if int(recovery["failure_idx"]) >= 0 else pd.NaT,
                        "recovery_failure_reason": recovery["failure_reason"],
                        "close_above_ema27_count": recovery["close_above_ema27_count"],
                        "ema27_nonnegative_count": recovery["ema27_nonnegative_count"],
                        "gap_nonshrinking_count": recovery["gap_nonshrinking_count"],
                        "final4_aligned_count": recovery["final4_aligned_count"],
                    }
                )
                features.loc[recovery_effective:cursor, ["recovery_attempt_id", "recovery_candidate_active", "section_phase"]] = [rid, True, "RECOVERY_ATTEMPT"]
                if prob_start >= 0:
                    features.loc[prob_start:prob_end, ["in_recovery_probation", "section_phase"]] = [True, "EXIT_PROBATION"]
                if recovery["status"] == "CONFIRMED_RECOVERED_LONG":
                    exit_kind = "CONFIRMED_RECOVERED_LONG"
                    effective_idx = recovery_effective
                    confirmation_idx = prob_end
                    add_event(sid, f"EP{episode_n:03d}", "EFFECTIVE_EXIT", effective_idx, exit_kind)
                    add_event(sid, f"EP{episode_n:03d}", "EXIT_CONFIRMATION", confirmation_idx, exit_kind)
                    consumed_until = confirmation_idx
                    break
                if recovery["status"] == "CENSORED_BY_TRAIN_END":
                    effective_idx = len(df) - 1
                    confirmation_idx = len(df) - 1
                    add_event(sid, f"EP{episode_n:03d}", "OPEN_AT_TRAIN_END", confirmation_idx)
                    consumed_until = confirmation_idx
                    break
                failed_recovery_count += 1
                fail_idx = int(recovery["failure_idx"])
                add_event(sid, f"EP{episode_n:03d}", "FAILED_RECOVERY", fail_idx, str(recovery["failure_reason"]))
                features.loc[fail_idx, "section_phase"] = "FAILED_RECOVERY"
                episode_n += 1
                current_episode_start = fail_idx
                episode_core_idxs = []
                add_event(sid, f"EP{episode_n:03d}", "EPISODE_START", current_episode_start, str(recovery["failure_reason"]))
                cursor = fail_idx
                continue

            new_down, new_effective = count_3_of_4_at(df, cursor, "new_down_configuration_bar", current_episode_start)
            if new_down:
                new_config_n += 1
                nid = f"N{new_config_n:03d}"
                attempt = new_configuration_probation(df, new_effective, cursor)
                prob_end = int(attempt["probation_end_idx"])
                add_event(sid, f"EP{episode_n:03d}", "NEW_CONFIGURATION_ATTEMPT", new_effective, nid)
                episodes.append(make_episode_row(sid, episode_n, df, current_episode_start, episode_core_idxs, -1, -1, cursor, "NEW_CONFIGURATION_ATTEMPT"))
                new_configs.append(
                    {
                        "section_id": sid,
                        "attempt_id": nid,
                        "effective_open_time": df.iloc[new_effective]["open_time"],
                        "detection_open_time": df.iloc[cursor]["open_time"],
                        "probation_end_open_time": df.iloc[prob_end]["open_time"],
                        "status": attempt["status"],
                        "failure_open_time": df.iloc[int(attempt["failure_idx"])]["open_time"] if int(attempt["failure_idx"]) >= 0 else pd.NaT,
                        "failure_reason": attempt["failure_reason"],
                        "ema27_below_ema200_count": attempt["ema27_below_ema200_count"],
                        "close_below_ema27_count": attempt["close_below_ema27_count"],
                        "ema27_nonpositive_count": attempt["ema27_nonpositive_count"],
                    }
                )
                features.loc[new_effective:cursor, ["new_configuration_attempt_id", "section_phase"]] = [nid, "RECOVERY_ATTEMPT"]
                features.loc[cursor + 1 : prob_end, ["in_new_configuration_probation", "section_phase"]] = [True, "EXIT_PROBATION"]
                if attempt["status"] == "CONFIRMED_NEW_DOWN_CONFIGURATION":
                    exit_kind = "CONFIRMED_NEW_DOWN_CONFIGURATION"
                    effective_idx = new_effective
                    confirmation_idx = prob_end
                    add_event(sid, f"EP{episode_n:03d}", "EFFECTIVE_EXIT", effective_idx, exit_kind)
                    add_event(sid, f"EP{episode_n:03d}", "EXIT_CONFIRMATION", confirmation_idx, exit_kind)
                    consumed_until = confirmation_idx
                    break
                if attempt["status"] == "CENSORED_BY_TRAIN_END":
                    effective_idx = len(df) - 1
                    confirmation_idx = len(df) - 1
                    add_event(sid, f"EP{episode_n:03d}", "OPEN_AT_TRAIN_END", confirmation_idx)
                    consumed_until = confirmation_idx
                    break
                failed_new_config_count += 1
                fail_idx = int(attempt["failure_idx"])
                add_event(sid, f"EP{episode_n:03d}", "NEW_CONFIGURATION_FAILED", fail_idx, str(attempt["failure_reason"]))
                episode_n += 1
                current_episode_start = fail_idx
                episode_core_idxs = []
                add_event(sid, f"EP{episode_n:03d}", "EPISODE_START", current_episode_start, str(attempt["failure_reason"]))
                cursor = fail_idx
                continue
            cursor += 1
        else:
            episodes.append(make_episode_row(sid, episode_n, df, current_episode_start, episode_core_idxs, -1, -1, len(df) - 1, "TRAIN_END"))
            add_event(sid, f"EP{episode_n:03d}", "OPEN_AT_TRAIN_END", len(df) - 1)
            consumed_until = len(df) - 1

        span_end = confirmation_idx
        source_r2 = source_r2_for_span(df, v2_sections, section_start, span_end)
        sections.append(
            {
                "section_id": sid,
                "display_start_open_time": df.iloc[max(0, section_start - 12)]["open_time"],
                "last_aligned_run_end_open_time": last_aligned,
                "dispute_start_open_time": df.iloc[section_start]["open_time"],
                "first_core_trigger_open_time": df.iloc[min(section_core_idxs) if section_core_idxs else first_core_idx]["open_time"],
                "last_core_trigger_open_time": df.iloc[max(section_core_idxs) if section_core_idxs else first_core_idx]["open_time"],
                "effective_exit_open_time": df.iloc[effective_idx]["open_time"],
                "effective_exit_boundary_time": boundary_at(df, effective_idx),
                "exit_confirmation_open_time": df.iloc[confirmation_idx]["open_time"],
                "exit_confirmation_boundary_time": boundary_at(df, confirmation_idx),
                "display_end_boundary_time": boundary_at(df, min(len(df) - 1, confirmation_idx + 8)),
                "exit_kind": exit_kind,
                "duration_dispute_bars": int(effective_idx - section_start + 1),
                "duration_confirmation_bars": int(confirmation_idx - effective_idx),
                "episode_count": episode_n,
                "core_trigger_count": len(section_core_idxs),
                "recovery_attempt_count": recovery_n,
                "failed_recovery_count": failed_recovery_count,
                "new_configuration_attempt_count": new_config_n,
                "failed_new_configuration_count": failed_new_config_count,
                "source_r2_sections": source_r2,
                "open_at_train_end": bool(exit_kind == "OPEN_AT_TRAIN_END"),
            }
        )
        features.loc[section_start:effective_idx, ["section_id", "in_dispute"]] = [sid, True]
        features.loc[section_start:first_core_idx - 1, "section_phase"] = "EARLY_DISPUTE"
        features.loc[first_core_idx:effective_idx, "section_phase"] = features.loc[first_core_idx:effective_idx, "section_phase"].replace("OUTSIDE_SECTION", "DISPUTE_EPISODE")
        features.loc[effective_idx:confirmation_idx, "section_id"] = sid
        features.loc[confirmation_idx + 1 : min(len(df) - 1, confirmation_idx + 8), "section_phase"] = "CONFIRMED_EXIT_CONTEXT"

    sections_df = pd.DataFrame(sections)
    mapping = r2_r3_mapping(sections_df)
    return sections_df, pd.DataFrame(episodes), pd.DataFrame(recoveries), pd.DataFrame(new_configs), pd.DataFrame(events), mapping, features


def make_episode_row(sid: str, episode_n: int, df: pd.DataFrame, start_idx: int, core_idxs: list[int], recovery_idx: int, failure_idx: int, end_idx: int, end_reason: str) -> dict[str, object]:
    sub = df.iloc[start_idx : end_idx + 1]
    depths = sub["depth"].dropna()
    return {
        "section_id": sid,
        "episode_id": f"EP{episode_n:03d}",
        "episode_start_open_time": df.iloc[start_idx]["open_time"],
        "first_core_trigger_open_time": df.iloc[min(core_idxs)]["open_time"] if core_idxs else pd.NaT,
        "last_core_trigger_open_time": df.iloc[max(core_idxs)]["open_time"] if core_idxs else pd.NaT,
        "episode_recovery_attempt_open_time": df.iloc[recovery_idx]["open_time"] if recovery_idx >= 0 else pd.NaT,
        "episode_failure_open_time": df.iloc[failure_idx]["open_time"] if failure_idx >= 0 else pd.NaT,
        "episode_end_open_time": df.iloc[end_idx]["open_time"],
        "episode_end_reason": end_reason,
        "core_trigger_count": len(core_idxs),
        "max_depth": float(depths.max()) if not depths.empty else math.nan,
        "bars_below_ema27": int((sub["close"] < sub["ema27"]).sum()),
        "ema_cross_occurred": bool(sub["ema_cross_event"].any()),
    }


def r2_r3_mapping(sections: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in sections.itertuples():
        sources = str(row.source_r2_sections)
        r2_count = 0 if not sources else len(sources.split(";"))
        rows.append(
            {
                "r3_section_id": row.section_id,
                "source_r2_sections": sources,
                "r3_dispute_start": row.dispute_start_open_time,
                "r3_effective_exit": row.effective_exit_open_time,
                "r3_exit_confirmation": row.exit_confirmation_open_time,
                "r3_exit_kind": row.exit_kind,
                "r2_section_count": r2_count,
                "merged_due_to_failed_recovery": bool(r2_count > 1 and row.failed_recovery_count > 0),
                "recovery_attempt_count": row.recovery_attempt_count,
                "failed_recovery_count": row.failed_recovery_count,
                "mapping_comment": "R2 local recovery failed probation; chained as episodes" if r2_count > 1 else "single R2 section kept after confirmed exit",
            }
        )
    return pd.DataFrame(rows)


def manual_episode_chain_review(sections: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "section_id": sections["section_id"],
            "source_r2_sections": sections["source_r2_sections"],
            "auto_dispute_start": sections["dispute_start_open_time"],
            "auto_effective_exit": sections["effective_exit_open_time"],
            "auto_exit_confirmation": sections["exit_confirmation_open_time"],
            "auto_exit_kind": sections["exit_kind"],
            "episode_count": sections["episode_count"],
            "recovery_attempt_count": sections["recovery_attempt_count"],
            "failed_recovery_count": sections["failed_recovery_count"],
            "section_merge_correct": "",
            "dispute_start_correct": "",
            "episode_boundaries_correct": "",
            "failed_recoveries_correct": "",
            "effective_exit_correct": "",
            "exit_confirmation_correct": "",
            "should_merge_with_previous": "",
            "should_merge_with_next": "",
            "should_split": "",
            "corrected_dispute_start": "",
            "corrected_effective_exit": "",
            "comment": "",
        }
    )


def pine_script_r3(sections: pd.DataFrame, episodes: pd.DataFrame, events: pd.DataFrame) -> str:
    options = ", ".join([f'"{x}"' for x in ["ALL", *sections["section_id"].tolist()]])
    ids = ", ".join([f'"{x}"' for x in sections["section_id"]])
    starts = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["dispute_start_open_time"])
    effective = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["effective_exit_open_time"])
    confirm = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["exit_confirmation_open_time"])
    event_ids = ", ".join([f'"{x}"' for x in events["section_id"]])
    event_types = ", ".join([f'"{x}"' for x in events["event_type"]])
    event_times = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in events["event_open_time"])
    ep_ids = ", ".join([f'"{x}"' for x in episodes["section_id"]])
    ep_starts = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in episodes["episode_start_open_time"])
    return f'''//@version=6
indicator("EXP-011B Long Dispute Episode Chains R3", overlay=true, max_labels_count=500, max_lines_count=500, max_boxes_count=100)

showDisputeArea = input.bool(true, "showDisputeArea")
showExitProbation = input.bool(true, "showExitProbation")
showEpisodeBoundaries = input.bool(true, "showEpisodeBoundaries")
showCoreTriggers = input.bool(true, "showCoreTriggers")
showRecoveryAttempts = input.bool(true, "showRecoveryAttempts")
showFailedRecoveries = input.bool(true, "showFailedRecoveries")
showNewConfigurationAttempts = input.bool(true, "showNewConfigurationAttempts")
showEmaCrossEvents = input.bool(true, "showEmaCrossEvents")
showEffectiveExit = input.bool(true, "showEffectiveExit")
showExitConfirmation = input.bool(true, "showExitConfirmation")
showSectionId = input.bool(true, "showSectionId")
showOnlySelectedSection = input.bool(false, "showOnlySelectedSection")
selectedSection = input.string("ALL", "selectedSection", options=[{options}])

var string[] sectionIds = array.from({ids})
var int[] disputeStarts = array.from({starts})
var int[] effectiveExits = array.from({effective})
var int[] exitConfirmations = array.from({confirm})
var string[] eventSectionIds = array.from({event_ids})
var string[] eventTypes = array.from({event_types})
var int[] eventTimes = array.from({event_times})
var string[] episodeSectionIds = array.from({ep_ids})
var int[] episodeStarts = array.from({ep_starts})

f_visible(string id) =>
    selectedSection == "ALL" or id == selectedSection

f_mark(string eventType) =>
    eventType == "DISPUTE_START" ? "D" : eventType == "CORE_TRIGGER" ? "T" : eventType == "RECOVERY_ATTEMPT" ? "R" : eventType == "FAILED_RECOVERY" ? "F" : eventType == "NEW_CONFIGURATION_ATTEMPT" ? "N" : eventType == "EMA_CROSS" ? "X" : eventType == "EFFECTIVE_EXIT" ? "E" : eventType == "EXIT_CONFIRMATION" ? "C" : eventType == "OPEN_AT_TRAIN_END" ? "O" : ""

f_enabled(string eventType) =>
    eventType == "CORE_TRIGGER" ? showCoreTriggers : eventType == "RECOVERY_ATTEMPT" ? showRecoveryAttempts : eventType == "FAILED_RECOVERY" ? showFailedRecoveries : eventType == "NEW_CONFIGURATION_ATTEMPT" ? showNewConfigurationAttempts : eventType == "EMA_CROSS" ? showEmaCrossEvents : eventType == "EFFECTIVE_EXIT" ? showEffectiveExit : eventType == "EXIT_CONFIRMATION" ? showExitConfirmation : eventType == "DISPUTE_START" ? true : eventType == "OPEN_AT_TRAIN_END" ? true : false

for i = 0 to array.size(sectionIds) - 1
    string sid = array.get(sectionIds, i)
    bool visible = f_visible(sid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(sid) : visible
    int st = array.get(disputeStarts, i)
    int ex = array.get(effectiveExits, i)
    int cn = array.get(exitConfirmations, i)
    bool atStart = time >= st and time[1] < st
    if visible and atStart
        if showDisputeArea
            box.new(st, high, ex, low, xloc=xloc.bar_time, bgcolor=color.new(color.yellow, 86), border_color=color.new(color.yellow, 25), extend=extend.none)
        if showExitProbation
            box.new(ex, high, cn, low, xloc=xloc.bar_time, bgcolor=color.new(color.orange, 91), border_color=color.new(color.orange, 55), extend=extend.none)
        if showSectionId
            label.new(st, high, sid, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.yellow, 0), textcolor=color.black, size=size.small)

for e = 0 to array.size(episodeStarts) - 1
    string sid = array.get(episodeSectionIds, e)
    int tt = array.get(episodeStarts, e)
    bool visible = f_visible(sid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(sid) : visible
    if visible and showEpisodeBoundaries and time >= tt and time[1] < tt
        line.new(tt, low, tt, high, xloc=xloc.bar_time, color=color.new(color.gray, 25), style=line.style_dotted, width=1)

for j = 0 to array.size(eventTimes) - 1
    string sid = array.get(eventSectionIds, j)
    string eventType = array.get(eventTypes, j)
    int tt = array.get(eventTimes, j)
    bool visible = f_visible(sid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(sid) : visible
    string mark = f_mark(eventType)
    if visible and f_enabled(eventType) and mark != "" and time >= tt and time[1] < tt
        label.new(tt, close, mark, xloc=xloc.bar_time, style=label.style_label_left, color=color.new(color.black, 0), textcolor=color.white, size=size.tiny)
'''


def preserve_r2_snapshots() -> None:
    snapshots = [
        ("long_dispute_sections_v2.csv", "long_dispute_sections_v2_snapshot.csv"),
        ("long_dispute_events_v2.csv", "long_dispute_events_v2_snapshot.csv"),
        ("LONG_CONFLICT_WINDOWS.pine", "LONG_CONFLICT_WINDOWS_R2_SNAPSHOT.pine"),
    ]
    for src, dst in snapshots:
        source = OUT / src
        target = OUT / dst
        if source.exists() and not target.exists():
            shutil.copyfile(source, target)


def write_review_instructions() -> None:
    (EXP / "REVIEW_INSTRUCTIONS.md").write_text(
        """# EXP-011B R3 Episode Chain Review

Status: AWAITING_TW_EPISODE_CHAIN_REVIEW

## Workflow

1. Open Bybit ADAUSDT Perpetual Contract.
2. Select 4H.
3. Add your own EMA27 and EMA200.
4. Add `artifacts/LONG_DISPUTE_EPISODE_CHAINS_R3.pine`.
5. Select one R3 `LC` at a time.
6. Review the chain `D -> episode -> R -> possible F -> next episode -> final E -> C`.
7. Fill `artifacts/manual_episode_chain_review.csv`.

## Event Legend

- `D`: DISPUTE_START.
- `T`: CORE_TRIGGER.
- `R`: RECOVERY_ATTEMPT.
- `F`: FAILED_RECOVERY.
- `N`: NEW_CONFIGURATION_ATTEMPT.
- `X`: EMA27/EMA200 cross down.
- `E`: EFFECTIVE_EXIT.
- `C`: EXIT_CONFIRMATION.
- `O`: OPEN_AT_TRAIN_END.

## Check Each R3 LC

- Are internal episodes merged correctly?
- Was the section closed on a real exit rather than a local bounce?
- Are failed recoveries marked at the right return of dispute?
- Is dispute absent after `E` through `C`?
- Does the new clear state persist through `C`?
- Should this section merge with a neighboring LC?
- Should it split into separate sections?

## Do Not Analyze Yet

- Causes of later movement.
- Technical Ratings.
- Forecasts.
- Trading actions.
- Final conflict classification.

## Source Note

Automatic windows use EXP-011 Binance spot 4H OHLC. Manual review is expected on Bybit ADAUSDT Perpetual Contract 4H, so some candles and boundaries may differ by one or more bars.
"""
    )


def write_report(period: pd.DataFrame, v1_sections: pd.DataFrame, v2_sections: pd.DataFrame, comparison: pd.DataFrame) -> None:
    old_count = len(v1_sections)
    new_count = len(v2_sections)
    left_expanded = int((comparison["bars_added_left"].replace("", 0).astype(int) > 0).sum()) if not comparison.empty else 0
    right_expanded = int((comparison["bars_added_right"].replace("", 0).astype(int) > 0).sum()) if not comparison.empty else 0
    avg_added_left = float(comparison["bars_added_left"].replace("", 0).astype(int).clip(lower=0).mean()) if not comparison.empty else 0.0
    avg_added_right = float(comparison["bars_added_right"].replace("", 0).astype(int).clip(lower=0).mean()) if not comparison.empty else 0.0
    old_mapped_to_multi = comparison.groupby("new_section_id")["old_section_id"].nunique() if not comparison.empty else pd.Series(dtype=int)
    merged = int((old_mapped_to_multi > 1).sum())
    split = int((comparison.groupby("old_section_id")["new_section_id"].nunique() > 1).sum()) if not comparison.empty else 0
    counts = v2_sections["resolution_kind"].value_counts()
    section_lines = "\n".join(
        f"- `{r.section_id}`: A `{r.last_aligned_run_end_open_time}`, D `{r.dispute_start_open_time}`, T `{r.first_core_trigger_open_time}` -> `{r.last_core_trigger_open_time}`, R `{r.resolution_candidate_open_time}`, E `{r.dispute_end_open_time}`, `{r.resolution_kind}`"
        for r in v2_sections.itertuples()
    )
    report = f"""# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

Status: AWAITING_TW_FULL_SECTION_REVIEW

Verdict: AWAITING_TW_FULL_SECTION_REVIEW

## Data

Source OHLC: `{SOURCE.relative_to(ROOT)}`

Exchange/source: Binance public spot klines inherited from EXP-011. Symbol: ADAUSDT. Manual TradingView review is expected on Bybit ADAUSDT Perpetual Contract 4H. Structure should be comparable, but individual candles and boundaries may differ by one or more bars.

Research period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`. Bars in period: `{len(period)}`. Pine uses 4H `open_time` boundaries.

## R2 Full Section Revision

V1 started too late because the left boundary was the already-confirmed `CORE_CONFLICT_TRIGGER`. V1 also ended too early because a technical reset or EMA27/EMA200 cross was treated as a right boundary. R2 keeps those as internal events and expands each section to the full dispute process.

- Old LC count: `{old_count}`
- New LC count: `{new_count}`
- Sections expanded left: `{left_expanded}`
- Sections expanded right: `{right_expanded}`
- Sections merged: `{merged}`
- Sections split: `{split}`
- RECOVERED_LONG: `{int(counts.get('RECOVERED_LONG', 0))}`
- NEW_DOWN_CONFIGURATION: `{int(counts.get('NEW_DOWN_CONFIGURATION', 0))}`
- OPEN_AT_TRAIN_END: `{int(counts.get('OPEN_AT_TRAIN_END', 0))}`
- Mean bars added left vs V1 overlaps: `{avg_added_left:.2f}`
- Mean bars added right vs V1 overlaps: `{avg_added_right:.2f}`
- Mean bars before first CORE_TRIGGER: `{v2_sections['bars_added_before_first_trigger'].mean():.2f}`
- Mean bars after last CORE_TRIGGER: `{v2_sections['bars_after_last_trigger'].mean():.2f}`

## R2 Sections

{section_lines if section_lines else "No R2 sections found."}

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. EMA-cross does not close a section automatically. RECOVERED_LONG and NEW_DOWN_CONFIGURATION both require 3-of-4 confirmation. No SHORT model, future validation period, ZigZag, clustering, BACKBONE_C, Technical Ratings, previous high/low hard filter, PnL, backtest, trading action, or `docs/DEFINITIONS.md` change.
"""
    (EXP / "REPORT.md").write_text(report)


def write_report_r3(period: pd.DataFrame, v2_sections: pd.DataFrame, r3_sections: pd.DataFrame, episodes: pd.DataFrame, recoveries: pd.DataFrame, new_configs: pd.DataFrame, mapping: pd.DataFrame) -> None:
    r2_count = len(v2_sections)
    r3_count = len(r3_sections)
    recovery_counts = recoveries["recovery_status"].value_counts() if not recoveries.empty else pd.Series(dtype=int)
    new_counts = new_configs["status"].value_counts() if not new_configs.empty else pd.Series(dtype=int)
    exit_counts = r3_sections["exit_kind"].value_counts() if not r3_sections.empty else pd.Series(dtype=int)
    merged = mapping[mapping["r2_section_count"] > 1] if not mapping.empty else pd.DataFrame()
    merged_lines = "\n".join(f"- `{r.source_r2_sections}` -> `{r.r3_section_id}`" for r in merged.itertuples())
    section_lines = "\n".join(
        f"- `{r.section_id}`: source `{r.source_r2_sections}`, D `{r.dispute_start_open_time}`, E `{r.effective_exit_open_time}`, C `{r.exit_confirmation_open_time}`, `{r.exit_kind}`, episodes `{r.episode_count}`"
        for r in r3_sections.itertuples()
    )
    acceptance = mapping[mapping["source_r2_sections"].astype(str).str.contains("LC002;LC003;LC004", regex=False)]
    acceptance_text = "PASS" if not acceptance.empty else "FAIL"
    lc67 = mapping[mapping["source_r2_sections"].astype(str).str.contains("LC006", regex=False)]
    lc67_text = "; ".join(f"{r.r3_section_id}: {r.source_r2_sections}" for r in lc67.itertuples()) if not lc67.empty else "LC006 not mapped"
    mean_section = float(r3_sections["duration_dispute_bars"].mean()) if not r3_sections.empty else math.nan
    mean_episodes = float(r3_sections["episode_count"].mean()) if not r3_sections.empty else math.nan
    mean_confirm = float(r3_sections["duration_confirmation_bars"].mean()) if not r3_sections.empty else math.nan
    report = f"""# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

Status: AWAITING_TW_EPISODE_CHAIN_REVIEW

Verdict: AWAITING_TW_EPISODE_CHAIN_REVIEW

## Data

Source OHLC: `{SOURCE.relative_to(ROOT)}`

Exchange/source: Binance public spot klines inherited from EXP-011. Symbol: ADAUSDT. Manual TradingView review is expected on Bybit ADAUSDT Perpetual Contract 4H. Structure should be comparable, but individual candles and boundaries may differ by one or more bars.

Research period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59.999 UTC`. Bars in period: `{len(period)}`. Pine uses 4H `open_time` boundaries.

## R3 Dispute Episode Chains

R2 expanded the windows correctly to the left and right, but its `3 of 4 recovered_long_bar` criterion was too short to separate a true exit from an internal bounce. R3 keeps the same causal EMA and CORE_TRIGGER formulas, treats that condition as `RECOVERY_ATTEMPT`, and requires a fixed `{RECOVERY_PROBATION_BARS}`-bar probation before the section can close.

- R2 sections: `{r2_count}`
- R3 sections: `{r3_count}`
- R3 episodes: `{len(episodes)}`
- RECOVERY_ATTEMPT: `{len(recoveries)}`
- FAILED_RECOVERY: `{int(recovery_counts.get('FAILED_RECOVERY', 0))}`
- CONFIRMED_RECOVERED_LONG: `{int(recovery_counts.get('CONFIRMED_RECOVERED_LONG', 0))}`
- NEW_CONFIGURATION_ATTEMPT: `{len(new_configs)}`
- NEW_CONFIGURATION_FAILED: `{int(new_counts.get('NEW_CONFIGURATION_FAILED', 0))}`
- CONFIRMED_NEW_DOWN_CONFIGURATION: `{int(new_counts.get('CONFIRMED_NEW_DOWN_CONFIGURATION', 0))}`
- OPEN_AT_TRAIN_END: `{int(exit_counts.get('OPEN_AT_TRAIN_END', 0))}`
- Mean section duration to effective exit, bars: `{mean_section:.2f}`
- Mean episodes per section: `{mean_episodes:.2f}`
- Mean bars from effective exit to confirmation: `{mean_confirm:.2f}`

## R2 To R3 Merges

{merged_lines if merged_lines else "No R2 sections were merged by R3."}

Acceptance test `LC002 + LC003 + LC004`: `{acceptance_text}`.

LC006/LC007 check: `{lc67_text}`.

## R3 Sections

{section_lines if section_lines else "No R3 sections found."}

## Constraints

No data after `2024-01-08 23:59:59.999 UTC` was used. No date-specific exceptions, ZigZag, clustering, BACKBONE_C, Technical Ratings, forecast, PnL, backtest, trading action, or `docs/DEFINITIONS.md` change. EMA27 and EMA200 are not plotted in the R3 Pine; the Pine only displays fixed timestamps from CSV.
"""
    (EXP / "REPORT.md").write_text(report)


def preserve_v1_snapshot() -> None:
    snapshot = OUT / "long_conflict_sections_v1_snapshot.csv"
    current = OUT / "long_conflict_sections.csv"
    if not snapshot.exists() and current.exists():
        shutil.copyfile(current, snapshot)


def main() -> None:
    ensure_dirs()
    preserve_v1_snapshot()
    preserve_r2_snapshots()
    full = add_features(load_ohlc())
    period = full[(full["open_time"] >= START) & (full["close_time"] <= END)].copy().reset_index(drop=True)
    raw_events, v1_features = find_raw_events(period)
    v1_features["section_id"] = ""
    v1_sections, raw_events, v1_features = build_sections_v1(raw_events, v1_features)

    events_out = raw_events.drop(columns=["start_pos", "end_pos"], errors="ignore")
    v1_features_out = v1_features[
        [
            "open_time",
            "close_time",
            "open",
            "high",
            "low",
            "close",
            "ema27",
            "ema200",
            "ema_gap",
            "ema_gap_pct",
            "ema27_change_1",
            "ema27_change_2",
            "ema27_slope_3",
            "ema200_slope_6",
            "ema_gap_change_1",
            "ema_gap_change_3",
            "depth",
            "long_context",
            "core_trigger",
            "raw_event_id",
            "section_id",
        ]
    ]
    events_out.to_csv(OUT / "raw_conflict_events.csv", index=False)
    v1_sections.to_csv(OUT / "long_conflict_sections.csv", index=False)
    v1_features_out.to_csv(OUT / "conflict_bar_features.csv", index=False)

    pw = primary_windows(period)
    v2_sections, v2_events, v2_features = build_v2_sections(period, pw, v1_sections)
    comparison = boundary_comparison(period, v1_sections, v2_sections)

    v2_features[
        [
            "open_time",
            "close_time",
            "open",
            "high",
            "low",
            "close",
            "ema27",
            "ema200",
            "ema_gap",
            "ema_gap_pct",
            "ema27_change_1",
            "ema27_change_2",
            "ema27_slope_3",
            "ema200_slope_6",
            "ema_gap_change_1",
            "ema_gap_change_3",
            "depth",
            "base_long_context",
            "price_aligned",
            "fast_aligned",
            "gap_aligned",
            "alignment_score",
            "fully_aligned_long_bar",
            "price_discordance",
            "fast_discordance",
            "gap_discordance",
            "discordance_score",
            "core_trigger",
            "recovered_long_bar",
            "new_down_configuration_bar",
            "ema_cross_event",
            "section_id",
            "section_phase",
        ]
    ].to_csv(OUT / "conflict_bar_features_v2.csv", index=False)
    v2_sections.to_csv(OUT / "long_dispute_sections_v2.csv", index=False)
    v2_events.to_csv(OUT / "long_dispute_events_v2.csv", index=False)
    comparison.to_csv(OUT / "boundary_revision_comparison.csv", index=False)
    manual_full_review(v2_sections).to_csv(OUT / "manual_full_section_review.csv", index=False)
    manual_review_template_v1(v1_sections).to_csv(OUT / "manual_boundary_review.csv", index=False)
    (OUT / "LONG_CONFLICT_WINDOWS.pine").write_text(pine_script_r2(v2_sections, v2_events))

    r3_sections, episodes, recoveries, new_configs, r3_events, mapping, r3_features = build_r3_sections(period, v2_sections)
    r3_columns = [
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "ema27",
        "ema200",
        "ema_gap",
        "ema_gap_pct",
        "ema27_change_1",
        "ema27_change_2",
        "ema27_slope_3",
        "ema200_slope_6",
        "ema_gap_change_1",
        "ema_gap_change_3",
        "depth",
        "base_long_context",
        "price_aligned",
        "fast_aligned",
        "gap_aligned",
        "alignment_score",
        "fully_aligned_long_bar",
        "price_discordance",
        "fast_discordance",
        "gap_discordance",
        "discordance_score",
        "core_trigger",
        "recovered_long_bar",
        "new_down_configuration_bar",
        "ema_cross_event",
        "section_id",
        "episode_id",
        "core_trigger_id",
        "recovery_attempt_id",
        "new_configuration_attempt_id",
        "in_dispute",
        "in_recovery_probation",
        "in_new_configuration_probation",
        "recovery_candidate_active",
        "section_phase",
    ]
    write_csv(r3_sections, OUT / "long_dispute_sections_r3.csv")
    write_csv(episodes, OUT / "dispute_episodes_r3.csv")
    write_csv(recoveries, OUT / "recovery_attempts_r3.csv")
    write_csv(new_configs, OUT / "new_configuration_attempts_r3.csv")
    write_csv(r3_events, OUT / "long_dispute_events_r3.csv")
    write_csv(mapping, OUT / "r2_r3_section_mapping.csv")
    write_csv(r3_features[r3_columns], OUT / "conflict_bar_features_r3.csv")
    write_csv(manual_episode_chain_review(r3_sections), OUT / "manual_episode_chain_review.csv")
    (OUT / "LONG_DISPUTE_EPISODE_CHAINS_R3.pine").write_text(pine_script_r3(r3_sections, episodes, r3_events))
    write_review_instructions()
    write_report_r3(period, v2_sections, r3_sections, episodes, recoveries, new_configs, mapping)
    print(
        json.dumps(
            {
                "status": "AWAITING_TW_EPISODE_CHAIN_REVIEW",
                "r2_lc": len(v2_sections),
                "r3_lc": len(r3_sections),
                "episodes": len(episodes),
                "recovery_attempts": len(recoveries),
                "failed_recoveries": int((recoveries["recovery_status"] == "FAILED_RECOVERY").sum()) if not recoveries.empty else 0,
                "confirmed_recovered_long": int((recoveries["recovery_status"] == "CONFIRMED_RECOVERED_LONG").sum()) if not recoveries.empty else 0,
                "new_configuration_attempts": len(new_configs),
                "failed_new_configurations": int((new_configs["status"] == "NEW_CONFIGURATION_FAILED").sum()) if not new_configs.empty else 0,
                "confirmed_new_down_configurations": int((new_configs["status"] == "CONFIRMED_NEW_DOWN_CONFIGURATION").sum()) if not new_configs.empty else 0,
                "open_sections": int((r3_sections["exit_kind"] == "OPEN_AT_TRAIN_END").sum()) if not r3_sections.empty else 0,
            },
            indent=2,
        )
    )


def manual_review_template_v1(sections: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "section_id": sections["section_id"],
            "auto_start_time": sections["start_time"],
            "auto_end_time": sections["end_time"],
            "valid_long_conflict": "",
            "start_assessment": "",
            "corrected_start_time": "",
            "end_assessment": "",
            "corrected_end_time": "",
            "split_required": "",
            "split_comment": "",
            "merge_required": "",
            "merge_with_section": "",
            "missing_section_before": "",
            "missing_section_after": "",
            "comment": "",
        }
    )


if __name__ == "__main__":
    main()
