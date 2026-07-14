#!/usr/bin/env python3
"""EXP-011B: discover LONG conflict windows on ADAUSDT 4H.

Uses saved EXP-011 Binance spot 4H OHLC. No Irobot, ZigZag, clustering,
BACKBONE_C selection, backtest, PnL, entries, exits, stops, or future outcomes.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-011B_LONG_CONFLICT_WINDOWS"
OUT = EXP / "artifacts"
SOURCE = ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv"
START = pd.Timestamp("2023-10-18 00:00:00")
END = pd.Timestamp("2024-01-08 23:59:59.999")
MERGE_GAP_BARS = 6
MERGE_EMA200_MAJORITY = 2.0 / 3.0


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def load_ohlc() -> pd.DataFrame:
    df = pd.read_csv(SOURCE, parse_dates=["open_time", "close_time"])
    required = ["open_time", "close_time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing OHLC columns: {missing}")
    if not df["open_time"].is_monotonic_increasing:
        raise RuntimeError("4H OHLC is not sorted by open_time")
    if df["open_time"].duplicated().any():
        raise RuntimeError("4H OHLC has duplicate open_time values")
    if df["open_time"].max() >= pd.Timestamp("2025-01-01") or df["close_time"].max() >= pd.Timestamp("2025-01-01"):
        raise RuntimeError("Forbidden 2025+ data detected in source")
    deltas = df["open_time"].diff().dropna()
    if not deltas.eq(pd.Timedelta(hours=4)).all():
        raise RuntimeError("4H OHLC is not continuous")
    if df["open_time"].dt.hour.mod(4).ne(0).any():
        raise RuntimeError("4H OHLC is not aligned to UTC 4H buckets")
    durations = df["close_time"] - df["open_time"]
    if not durations.eq(pd.Timedelta(hours=4) - pd.Timedelta(milliseconds=1)).all():
        raise RuntimeError("4H OHLC contains incomplete bars")
    if df["open_time"].min() > START or df["close_time"].max() < END:
        raise RuntimeError("4H OHLC does not cover the full research period")
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
    out["long_context"] = (out["ema27"] > out["ema200"]) & (out["ema200_slope_6"] > 0)
    out["core_trigger"] = (
        out["long_context"]
        & (out["ema27_change_1"] < 0)
        & ((out["ema27_change_2"] < 0) | (out["ema27_slope_3"] < 0))
        & (out["close"] < out["ema27"])
    )
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
            if reset_bar:
                reset_run.append(j)
            else:
                reset_run = []
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
        diag = diagnostic_pretrigger(df, start_i)
        duration = end_i - start_i + 1
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
                "duration_4h_bars": duration,
                "start_pos": start_i,
                "end_pos": end_i,
                **diag,
            }
        )
        i = end_i + 1
    return pd.DataFrame(events), df


def should_merge(df: pd.DataFrame, prev: pd.Series, cur: pd.Series) -> bool:
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


def build_sections(events: pd.DataFrame, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if events.empty:
        return pd.DataFrame(), events, df
    groups: list[list[int]] = [[0]]
    for idx in range(1, len(events)):
        if should_merge(df, events.iloc[groups[-1][-1]], events.iloc[idx]):
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
        end_reasons = evs["end_reason"].tolist()
        end_reason = end_reasons[-1]
        sections.append(
            {
                "section_id": sid,
                "start_time": first["close_time"],
                "end_time": sub.iloc[-1]["close_time"],
                "duration_4h_bars": int(len(sub)),
                "raw_event_count": int(len(evs)),
                "technical_end_reason": end_reason,
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
                "open_at_period_end": bool(end_reason == "OPEN_AT_PERIOD_END"),
            }
        )
        for idx in group:
            events.at[idx, "section_id"] = sid
        mask = df["raw_event_id"].isin(evs["raw_event_id"])
        df.loc[mask, "section_id"] = sid
    return pd.DataFrame(sections), events, df


def pine_script(sections: pd.DataFrame, events: pd.DataFrame) -> str:
    section_options = ", ".join([f'"{x}"' for x in ["ALL", *sections["section_id"].tolist()]])
    ids = ", ".join([f'"{x}"' for x in sections["section_id"]])
    starts = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["start_time"])
    ends = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in sections["end_time"])
    trig_ids = ", ".join([f'"{x}"' for x in events["section_id"]])
    trig_times = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in events["trigger_time"])
    return f'''//@version=6
indicator("EXP-011B Long Conflict Windows", overlay=true, max_labels_count=500, max_lines_count=500, max_boxes_count=100)

showWindowArea = input.bool(true, "showWindowArea")
showWindowStart = input.bool(true, "showWindowStart")
showWindowEnd = input.bool(true, "showWindowEnd")
showSectionId = input.bool(true, "showSectionId")
showRawTriggers = input.bool(true, "showRawTriggers")
showOnlySelectedSection = input.bool(false, "showOnlySelectedSection")
selectedSection = input.string("ALL", "selectedSection", options=[{section_options}])

var string[] sectionIds = array.from({ids})
var int[] sectionStarts = array.from({starts})
var int[] sectionEnds = array.from({ends})
var string[] triggerSectionIds = array.from({trig_ids})
var int[] triggerTimes = array.from({trig_times})

f_visible(string id) =>
    selectedSection == "ALL" or id == selectedSection

for i = 0 to array.size(sectionIds) - 1
    string sid = array.get(sectionIds, i)
    int st = array.get(sectionStarts, i)
    int en = array.get(sectionEnds, i)
    bool visible = f_visible(sid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(sid) : visible
    bool atStart = time >= st and time[1] < st
    bool atEnd = time >= en and time[1] < en
    if visible and showWindowArea and atStart
        box.new(st, high, en, low, xloc=xloc.bar_time, bgcolor=color.new(color.yellow, 88), border_color=color.new(color.yellow, 25), extend=extend.none)
    if visible and showWindowStart and atStart
        line.new(st, low, st, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.green, 0), style=line.style_solid, width=1)
        if showSectionId
            label.new(st, high, sid, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.green, 0), textcolor=color.white, size=size.small)
    if visible and showWindowEnd and atEnd
        line.new(en, low, en, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.red, 0), style=line.style_solid, width=1)

for j = 0 to array.size(triggerTimes) - 1
    string sid = array.get(triggerSectionIds, j)
    int tt = array.get(triggerTimes, j)
    bool visible = f_visible(sid) and (not showOnlySelectedSection or selectedSection != "ALL")
    visible := selectedSection == "ALL" ? f_visible(sid) : visible
    bool atTrigger = time >= tt and time[1] < tt
    if visible and showRawTriggers and atTrigger
        label.new(tt, low, "raw", xloc=xloc.bar_time, style=label.style_label_up, color=color.new(color.gray, 0), textcolor=color.white, size=size.tiny)
'''


def manual_review_template(sections: pd.DataFrame) -> pd.DataFrame:
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


def write_report(period: pd.DataFrame, events: pd.DataFrame, sections: pd.DataFrame) -> None:
    counts = events["end_reason"].value_counts() if not events.empty else pd.Series(dtype=int)
    section_lines = "\n".join(
        f"- `{r.section_id}`: `{r.start_time}` -> `{r.end_time}`, raw events `{r.raw_event_count}`, end `{r.technical_end_reason}`"
        for r in sections.itertuples()
    )
    report = f"""# EXP-011B — LONG CONFLICT WINDOW DISCOVERY

Status: AWAITING_TW_BOUNDARY_REVIEW

Verdict: AWAITING_TW_BOUNDARY_REVIEW

## Data

Source OHLC: `{SOURCE.relative_to(ROOT)}`

Exchange/source: Binance public spot klines inherited from EXP-011. Symbol: ADAUSDT. Manual TradingView review is expected on Bybit ADAUSDT Perpetual Contract 4H, so one or more bars may differ between sources.

Research period: `2023-10-18 00:00:00 UTC` through `2024-01-08 23:59:59 UTC`. Bars in period: `{len(period)}`.

## Counts

- CORE_CONFLICT_TRIGGER: `{int(period['core_trigger'].sum())}`
- Raw conflicts: `{len(events)}`
- LONG CONFLICT sections: `{len(sections)}`
- FULL_RESET_CONFIRMED: `{int(counts.get('FULL_RESET_CONFIRMED', 0))}`
- EMA_CROSS: `{int(counts.get('EMA_CROSS', 0))}`
- OPEN_AT_PERIOD_END: `{int(counts.get('OPEN_AT_PERIOD_END', 0))}`

## Sections

{section_lines if section_lines else "No sections found."}

## Merge Parameters

- Max gap between raw conflicts: `{MERGE_GAP_BARS}` 4H bars
- Gap must preserve `ema27 > ema200`
- At least `{MERGE_EMA200_MAJORITY:.2f}` of gap bars must have `ema200_slope_6 >= 0`

## Constraints

SHORT context was not analyzed. Data after `2024-01-08 23:59:59 UTC` was not used. Pine does not draw EMA27 or EMA200. No continuation/reversal/transition classification is made.

No ZigZag, clustering, BACKBONE_C, previous high/low condition, Irobot, PnL, backtest, entry, exit, stop, risk, or future outcome was used. `docs/DEFINITIONS.md` was not changed.
"""
    (EXP / "REPORT.md").write_text(report)


def main() -> None:
    ensure_dirs()
    full = add_features(load_ohlc())
    period = full[(full["open_time"] >= START) & (full["close_time"] <= END)].copy().reset_index(drop=True)
    events, features = find_raw_events(period)
    features["section_id"] = ""
    sections, events, features = build_sections(events, features)
    events_out = events.drop(columns=["start_pos", "end_pos"], errors="ignore")
    features_out = features[
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
    sections.to_csv(OUT / "long_conflict_sections.csv", index=False)
    features_out.to_csv(OUT / "conflict_bar_features.csv", index=False)
    manual_review_template(sections).to_csv(OUT / "manual_boundary_review.csv", index=False)
    (OUT / "LONG_CONFLICT_WINDOWS.pine").write_text(pine_script(sections, events))
    write_report(period, events, sections)
    print(
        json.dumps(
            {
                "status": "AWAITING_TW_BOUNDARY_REVIEW",
                "bars_4h": len(period),
                "core_triggers": int(period["core_trigger"].sum()),
                "raw_conflicts": len(events),
                "sections": len(sections),
                "end_reasons": events["end_reason"].value_counts().to_dict() if not events.empty else {},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
