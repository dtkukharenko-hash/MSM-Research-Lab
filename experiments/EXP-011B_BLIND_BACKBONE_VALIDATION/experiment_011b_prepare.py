#!/usr/bin/env python3
"""EXP-011B Phase 1: prepare blind visual backbone validation.

Uses frozen EXP-011A artifacts only. It does not recalculate or modify
BACKBONE_C, and it does not score human labels.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-011B_BLIND_BACKBONE_VALIDATION"
OUT = EXP / "artifacts"
SRC_A = ROOT / "experiments/EXP-011A_SLOW_BACKBONE_FAST_PHASE/artifacts"
SRC_011 = ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts"
SEED = 11011
FORBIDDEN = pd.Timestamp("2025-01-01 00:00:00")
REVIEW_INSTRUCTION = (
    "Evaluate the 4H EMA200-backbone state: ACTIVE, FLATTENING, or AMBIGUOUS. "
    "Do not classify price direction. Do not treat EMA27 moving toward EMA200 as automatic FLATTENING. "
    "Judge primarily whether EMA200 keeps or loses a stable slope."
)


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def read_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    windows = pd.read_csv(SRC_A / "visual_review_windows.csv", parse_dates=["start_time", "end_time"])
    ms = pd.read_csv(SRC_A / "multiscale_states.csv", parse_dates=["open_time", "close_time"])
    ohlc = pd.read_csv(SRC_011 / "ohlc_1h.csv", parse_dates=["open_time", "close_time"])
    for name, df in [("visual_review_windows", windows), ("multiscale_states", ms), ("ohlc_1h", ohlc)]:
        for col in [c for c in ["start_time", "end_time", "open_time", "close_time"] if c in df.columns]:
            if pd.to_datetime(df[col]).max() >= FORBIDDEN:
                raise RuntimeError(f"{name} contains forbidden 2025+ data")
    return windows, ms, ohlc


def row_from_window(row: pd.Series, source_type: str) -> dict[str, object]:
    model_label = row["backbone_4h"] if row["backbone_4h"] in {"ACTIVE", "FLATTENING", "LOST", "TRANSITION"} else "CONTROL"
    return {
        "source_review_id": row["review_id"],
        "source_type": source_type,
        "model_label": model_label,
        "direction_4h": row["direction_4h"],
        "backbone_4h": row["backbone_4h"],
        "fast_phase_4h": row["fast_phase_4h"],
        "direction_1h": row["direction_1h"],
        "backbone_1h": row["backbone_1h"],
        "fast_phase_1h": row["fast_phase_1h"],
        "original_start_time": row["start_time"],
        "original_end_time": row["end_time"],
    }


def episode_lengths(values: list[str]) -> list[tuple[str, int, int, int]]:
    if not values:
        return []
    out = []
    cur = values[0]
    start = 0
    length = 1
    for i, val in enumerate(values[1:], start=1):
        if val == cur:
            length += 1
        else:
            out.append((cur, start, i - 1, length))
            cur = val
            start = i
            length = 1
    out.append((cur, start, len(values) - 1, length))
    return out


def controls_from_multiscale(ms: pd.DataFrame, existing_months: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    episodes = episode_lengths(ms["multiscale_composite"].tolist())

    def add_control(kind: str, predicate, limit: int) -> None:
        nonlocal rows
        for _, s, e, length in episodes:
            if length < 8:
                continue
            ep = ms.iloc[s : e + 1]
            sample = ep.iloc[0]
            month = sample["open_time"].strftime("%Y-%m")
            if month in existing_months:
                continue
            if not predicate(sample):
                continue
            existing_months.add(month)
            rows.append(
                {
                    "source_review_id": f"CTRL{len(rows)+1:03d}",
                    "source_type": kind,
                    "model_label": sample["backbone_4h"],
                    "direction_4h": sample["direction_4h"],
                    "backbone_4h": sample["backbone_4h"],
                    "fast_phase_4h": sample["fast_phase_4h"],
                    "direction_1h": sample["direction_1h"],
                    "backbone_1h": sample["backbone_1h"],
                    "fast_phase_1h": sample["fast_phase_1h"],
                    "original_start_time": sample["open_time"],
                    "original_end_time": ep.iloc[-1]["close_time"],
                }
            )
            if sum(r["source_type"] == kind for r in rows) >= limit:
                return

    add_control(
        "CONTROL_ACTIVE_ALIGNED",
        lambda r: r["backbone_4h"] == "ACTIVE" and r["direction_relation"] in {"ALIGNED_UP", "ALIGNED_DOWN"},
        1,
    )
    add_control(
        "CONTROL_FLATTENING_NON_OPPOSE",
        lambda r: r["backbone_4h"] == "FLATTENING" and r["direction_relation"] != "LOWER_OPPOSES_PARENT",
        1,
    )
    add_control(
        "CONTROL_TRANSITION",
        lambda r: r["backbone_4h"] == "TRANSITION",
        1,
    )
    add_control(
        "CONTROL_LOST",
        lambda r: r["backbone_4h"] == "LOST",
        1,
    )
    if len(rows) < 4:
        add_control(
            "CONTROL_EXTRA",
            lambda r: r["direction_relation"] != "LOWER_OPPOSES_PARENT",
            4 - len(rows),
        )
    return rows[:4]


def build_blind_set(windows: pd.DataFrame, ms: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for source_type, n in [("TYPE_A", 8), ("TYPE_B", 7), ("TYPE_D", 5), ("TYPE_C", 4)]:
        sub = windows[windows["review_type"] == source_type].head(n)
        for _, row in sub.iterrows():
            rows.append(row_from_window(row, source_type))
    used_months = {pd.Timestamp(r["original_start_time"]).strftime("%Y-%m") for r in rows}
    rows.extend(controls_from_multiscale(ms, used_months))
    rng = random.Random(SEED)
    rng.shuffle(rows)
    for i, row in enumerate(rows, start=1):
        row["blind_id"] = f"BV{i:03d}"
    return pd.DataFrame(rows)


def write_review_files(blind: pd.DataFrame) -> None:
    review = pd.DataFrame(
        {
            "blind_id": blind["blind_id"],
            "start_time": blind["original_start_time"],
            "end_time": blind["original_end_time"],
            "chart_timeframe": "1H",
            "review_instruction": REVIEW_INSTRUCTION,
            "human_label": "",
            "confidence": "",
            "comment": "",
        }
    )
    review.to_csv(OUT / "blind_review_windows.csv", index=False)
    key_cols = [
        "blind_id",
        "source_review_id",
        "source_type",
        "model_label",
        "direction_4h",
        "backbone_4h",
        "fast_phase_4h",
        "direction_1h",
        "backbone_1h",
        "fast_phase_1h",
        "original_start_time",
        "original_end_time",
    ]
    blind[key_cols].to_csv(OUT / "blind_key.csv", index=False)
    labels = pd.DataFrame({"blind_id": blind["blind_id"], "human_label": "", "confidence": "", "comment": ""})
    labels.to_csv(OUT / "human_labels.csv", index=False)


def pine_script(blind: pd.DataFrame) -> str:
    options = ", ".join([f'"{x}"' for x in ["ALL", *blind["blind_id"].tolist()]])
    ids = ", ".join([f'"{x}"' for x in blind["blind_id"]])
    starts = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in blind["original_start_time"])
    ends = ", ".join(str(int(pd.Timestamp(x).timestamp() * 1000)) for x in blind["original_end_time"])
    return f'''//@version=6
indicator("EXP-011B Blind Backbone Review", overlay=true, max_labels_count=500)

showWindowArea = input.bool(true, "showWindowArea")
showWindowStart = input.bool(true, "showWindowStart")
showWindowEnd = input.bool(true, "showWindowEnd")
showBlindId = input.bool(true, "showBlindId")
showOnlySelectedWindow = input.bool(false, "showOnlySelectedWindow")
selectedBlindId = input.string("ALL", "selectedBlindId", options=[{options}])

var string[] ids = array.from({ids})
var int[] starts = array.from({starts})
var int[] ends = array.from({ends})

f_visible(string id) =>
    selectedBlindId == "ALL" or id == selectedBlindId

for i = 0 to array.size(ids) - 1
    string id = array.get(ids, i)
    int st = array.get(starts, i)
    int en = array.get(ends, i)
    bool visible = f_visible(id) and (not showOnlySelectedWindow or selectedBlindId != "ALL")
    visible := selectedBlindId == "ALL" ? f_visible(id) : visible
    bool inWindow = time >= st and time <= en
    bool atStart = time >= st and time[1] < st
    bool atEnd = time >= en and time[1] < en
    if visible and showWindowArea and inWindow
        bgcolor(color.new(color.yellow, 88))
    if visible and showWindowStart and atStart
        line.new(st, low, st, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.green, 0), style=line.style_solid, width=1)
        if showBlindId
            label.new(st, high, id, xloc=xloc.bar_time, style=label.style_label_down, color=color.new(color.green, 0), textcolor=color.white, size=size.small)
    if visible and showWindowEnd and atEnd
        line.new(en, low, en, high, xloc=xloc.bar_time, extend=extend.both, color=color.new(color.red, 0), style=line.style_solid, width=1)
'''


def write_pdf(path: Path, blind: pd.DataFrame) -> None:
    def esc(s: object) -> str:
        return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    pages: list[bytes] = []
    for row in blind.sort_values("blind_id").itertuples():
        lines = [
            "BT",
            "/F1 18 Tf 54 730 Td",
            f"({esc(row.blind_id)}) Tj",
            "/F1 11 Tf 0 -28 Td",
            f"(Chart: ADAUSDT 1H) Tj",
            "0 -18 Td",
            f"(Window start UTC: {esc(row.original_start_time)}) Tj",
            "0 -18 Td",
            f"(Window end UTC: {esc(row.original_end_time)}) Tj",
            "0 -26 Td",
            "(Use TradingView with your own EMA27 and EMA200.) Tj",
            "0 -28 Td",
            "(This PDF intentionally contains only blind navigation information.) Tj",
            "ET",
        ]
        pages.append("\n".join(lines).encode("latin-1", "replace"))
    objs: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    page_refs = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objs.append(f"<< /Type /Pages /Kids [{page_refs}] /Count {len(pages)} >>".encode())
    font_id = 3 + len(pages) * 2
    for i, stream in enumerate(pages):
        page_id = 3 + i * 2
        content_id = page_id + 1
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode())
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(out)


def write_report(blind: pd.DataFrame) -> None:
    counts = blind["source_type"].value_counts()
    report = f"""# EXP-011B — BLIND VISUAL BACKBONE VALIDATION

Status: AWAITING_HUMAN_LABELS

Verdict: AWAITING_HUMAN_LABELS

## Phase 1 Package

Prepared blind review windows for human visual validation of frozen EXP-011A `BACKBONE_C`.

- Blind windows: `{len(blind)}`
- TYPE_A source windows: `{int(counts.get('TYPE_A', 0))}`
- TYPE_B source windows: `{int(counts.get('TYPE_B', 0))}`
- Mirror DOWN windows: `{int(counts.get('TYPE_D', 0))}`
- ACTIVE+ALIGNED windows: `{int(counts.get('TYPE_C', 0))}`
- Control windows: `{int(sum(v for k, v in counts.items() if str(k).startswith('CONTROL')))}`
- Random seed: `{SEED}`

## Frozen Model

`BACKBONE_C` is frozen from EXP-011A. No formulas, thresholds, windows, hysteresis, or persistence rules were changed. EXP-011A artifacts were used read-only.

## Review Mode

Preferred TradingView mode is used. The PDF lists one blind window per page with `blind_id` and UTC interval only. Visual assessment should be done on ADAUSDT 1H in TradingView with the user's own EMA27 and EMA200.

Pine path: `artifacts/BLIND_BACKBONE_REVIEW.pine`

Human label template: `artifacts/human_labels.csv`

Do not open `artifacts/blind_key.csv` until all human labels are complete.

## No Final Verdict

This is Phase 1 only. Final semantic validation requires Phase 2 scoring after `human_labels.csv` is filled.

## Constraints

No Irobot, no 2025+ data, no PnL, no backtest, no entry/exit/stop/risk, no model tuning, and no change to `docs/DEFINITIONS.md`.
"""
    (EXP / "REPORT.md").write_text(report)


def main() -> None:
    ensure_dirs()
    windows, ms, _ = read_sources()
    blind = build_blind_set(windows, ms)
    if len(blind) != 28:
        raise RuntimeError(f"Expected 28 blind windows, got {len(blind)}")
    write_review_files(blind)
    (OUT / "BLIND_BACKBONE_REVIEW.pine").write_text(pine_script(blind))
    write_pdf(OUT / "BLIND_BACKBONE_REVIEW.pdf", blind)
    write_report(blind)
    print(json.dumps({"status": "AWAITING_HUMAN_LABELS", "blind_windows": len(blind), "seed": SEED, "counts": blind["source_type"].value_counts().to_dict()}, indent=2))


if __name__ == "__main__":
    main()
