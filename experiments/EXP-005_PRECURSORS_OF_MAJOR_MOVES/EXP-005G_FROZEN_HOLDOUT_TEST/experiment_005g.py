#!/usr/bin/env python3
"""EXP-005G: blocked frozen holdout test due to missing event definition."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/EXP-005_PRECURSORS_OF_MAJOR_MOVES"
EXP_F = EXP / "EXP-005F_EMA_CONTEXT_INCREMENT/artifacts"
OUT = EXP / "EXP-005G_FROZEN_HOLDOUT_TEST/artifacts"

RESEARCH_START = "2023-07-01 00:00 UTC"
RESEARCH_END = "2025-07-01 00:00 UTC"
HOLDOUT_START = "2025-07-01 04:00 UTC"
HOLDOUT_END = "2026-07-01 00:00 UTC"

MODEL3_FEATURES = [
    "pre_net_return_atr",
    "price_minus_ema27_atr",
    "ema27_slope_5",
    "ema27_slope_10",
    "ema27_slope_change",
    "fraction_last10_above_ema27",
    "number_of_ema27_crosses_last20",
    "distance_change_to_ema27_last10",
    "price_minus_ema200_atr",
    "ema200_slope_10",
    "ema200_slope_30",
    "fraction_last30_above_ema200",
    "number_of_ema200_crosses_last50",
    "distance_change_to_ema200_last20",
    "ema27_minus_ema200_atr",
    "ema27_above_ema200",
    "ema27_ema200_distance_change_last20",
    "price_between_ema27_ema200",
    "ema27_turning_against_previous_state",
]


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def png_write(path: Path, width: int, height: int, color: tuple[int, int, int] = (245, 245, 245)) -> None:
    raw = bytearray()
    for _ in range(height):
        raw.append(0)
        for _ in range(width):
            raw.extend(color)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path: Path) -> None:
    lines = [
        "EXP-005G Frozen Holdout Test",
        "Verdict: HOLDOUT_BLOCKED_BY_EVENT_DEFINITION",
        "Holdout labels and outcomes were not opened.",
        "Reason: EXP-005A/EXP-005B do not define a causal, exact event-generation algorithm.",
    ]
    content = ["BT", "/F1 12 Tf", "50 760 Td"]
    for i, line in enumerate(lines):
        if i:
            content.append("0 -20 Td")
        content.append(f"({pdf_escape(line)}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("utf-8")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    )
    path.write_bytes(bytes(out))


def main() -> None:
    ensure_dirs()

    frozen_spec = {
        "experiment": "EXP-005G_FROZEN_HOLDOUT_TEST",
        "verdict": "HOLDOUT_BLOCKED_BY_EVENT_DEFINITION",
        "research_period": {"start": RESEARCH_START, "end": RESEARCH_END},
        "holdout_period": {"start": HOLDOUT_START, "end": HOLDOUT_END},
        "holdout_outcomes_opened": False,
        "blocked_before_holdout_labeling": True,
        "model_source": "EXP-005F Model 3",
        "target": {"MAJOR": 1, "MATCHED_NON_MAJOR": 0},
        "model": {
            "type": "logistic_regression",
            "penalty": "L2",
            "C": 1.0,
            "class_weight": "balanced",
            "scaler_fit": "research_events_only",
            "threshold": 0.5,
            "threshold_optimized": False,
        },
        "feature_timing": "t-1 closed bars only; event bar excluded",
        "features": MODEL3_FEATURES,
        "blocker": {
            "summary": "EXP-005A/EXP-005B do not provide a causal, exact event-generation algorithm.",
            "missing_items": [
                "numeric major movement thresholds",
                "causal candidate turn rule",
                "complete holdout candidate event-point generation rule",
                "exact matched-control selection algorithm",
                "formal CENSORED/UNKNOWN label rules",
                "exact outcome horizon and completion rules for major/non-major labeling",
            ],
            "evidence": [
                "EXP-005A uses retrospective OHLC close turning region and 120-bar local context wording.",
                "EXP-005B uses similar prior volatility/net return/efficiency/range/duration and no comparable major movement, without exact constants.",
            ],
        },
    }
    (OUT / "frozen_specification.json").write_text(json.dumps(frozen_spec, indent=2), encoding="utf-8")

    research = pd.read_csv(EXP_F / "events_with_ema_features.csv")
    research.to_csv(OUT / "research_training_events.csv", index=False)

    blocked_row = {
        "event_id": "BLOCKED",
        "event_time": "",
        "direction": "",
        "event_point_rule": "NOT_GENERATED",
        "causal_available": "false",
        "unknown_reason": "HOLDOUT_BLOCKED_BY_EVENT_DEFINITION: EXP-005A/EXP-005B event-generation is not causal and exact enough to enumerate holdout candidates without new choices.",
    }
    write_csv(
        OUT / "holdout_candidate_events.csv",
        ["event_id", "event_time", "direction", "event_point_rule", "causal_available", "unknown_reason"],
        [blocked_row],
    )
    write_csv(
        OUT / "holdout_labeled_events.csv",
        ["event_id", "event_time", "direction", "outcome_label", "label_status", "reason"],
        [
            {
                "event_id": "BLOCKED",
                "event_time": "",
                "direction": "",
                "outcome_label": "UNKNOWN",
                "label_status": "NOT_LABELED",
                "reason": "Holdout candidate events were not causally generated; holdout labels were not opened.",
            }
        ],
    )
    write_csv(OUT / "holdout_features.csv", ["event_id", *MODEL3_FEATURES, "status"], [{"event_id": "BLOCKED", "status": "NOT_COMPUTED"}])
    write_csv(
        OUT / "holdout_predictions.csv",
        ["event_id", "model", "predicted_probability", "status", "reason"],
        [{"event_id": "BLOCKED", "model": "Model 3", "predicted_probability": "", "status": "NOT_SCORED", "reason": "No causal holdout event set."}],
    )

    metric_row = {
        "model": "Model 3",
        "roc_auc": "",
        "pr_auc": "",
        "balanced_accuracy": "",
        "brier_score": "",
        "log_loss": "",
        "major_prevalence": "",
        "status": "BLOCKED",
        "reason": "HOLDOUT_BLOCKED_BY_EVENT_DEFINITION",
    }
    for name in [
        "holdout_metrics.csv",
        "model_comparison.csv",
        "leave_one_event_out.csv",
        "leave_one_major_out.csv",
        "direction_results.csv",
        "start_shift_results.csv",
        "calibration_table.csv",
    ]:
        write_csv(OUT / name, list(metric_row.keys()), [metric_row])

    for name in ["holdout_roc.png", "holdout_pr.png", "holdout_calibration.png", "holdout_probability_distribution.png"]:
        png_write(OUT / name, 640, 400)

    pine = """//@version=6
indicator("EXP-005G Holdout Review - BLOCKED", overlay=true)

// EXP-005G did not generate holdout event points because EXP-005A/005B
// do not define an exact causal event-generation algorithm.
// No model is calculated here and no holdout labels were opened.
ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
plot(ema27, "EMA27", color=color.new(color.teal, 0), linewidth=2)
plot(ema200, "EMA200", color=color.new(color.orange, 0), linewidth=2)
holdoutStart = timestamp("Etc/UTC", 2025, 7, 1, 4, 0)
holdoutEnd = timestamp("Etc/UTC", 2026, 7, 1, 0, 0)
bgcolor(time >= holdoutStart and time <= holdoutEnd ? color.new(color.gray, 86) : na)
"""
    (OUT / "HOLDOUT_REVIEW.pine").write_text(pine, encoding="utf-8")
    write_pdf(OUT / "HOLDOUT_OVERVIEW.pdf")

    print("EXP-005G blocked before holdout label access")


if __name__ == "__main__":
    main()
