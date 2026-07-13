#!/usr/bin/env python3
"""Score EXP-011B after human_labels.csv has been filled.

This script is for Phase 2 only. It validates label completeness before
unblinding with blind_key.csv.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments/EXP-011B_BLIND_BACKBONE_VALIDATION"
OUT = EXP / "artifacts"
VALID_LABELS = {"ACTIVE", "FLATTENING", "AMBIGUOUS"}
VALID_CONFIDENCE = {"1", "2", "3"}
BINARY = {"ACTIVE", "FLATTENING"}


def load_and_validate() -> pd.DataFrame:
    labels = pd.read_csv(OUT / "human_labels.csv", dtype=str).fillna("")
    key = pd.read_csv(OUT / "blind_key.csv", dtype=str).fillna("")
    expected = set(key["blind_id"])
    actual = set(labels["blind_id"])
    if actual != expected:
        raise RuntimeError(f"human_labels.csv blind_id mismatch. Missing={sorted(expected - actual)} Unknown={sorted(actual - expected)}")
    if labels["blind_id"].duplicated().any():
        dup = labels.loc[labels["blind_id"].duplicated(), "blind_id"].tolist()
        raise RuntimeError(f"Duplicate blind_id values: {dup}")
    bad_labels = sorted(set(labels["human_label"]) - VALID_LABELS)
    if bad_labels:
        raise RuntimeError(f"Invalid human_label values: {bad_labels}")
    bad_conf = sorted(set(labels["confidence"]) - VALID_CONFIDENCE)
    if bad_conf:
        raise RuntimeError(f"Invalid confidence values: {bad_conf}")
    if (labels["human_label"] == "").any() or (labels["confidence"] == "").any():
        raise RuntimeError("All human_label and confidence rows must be filled before scoring.")
    return labels.merge(key, on="blind_id", how="inner")


def binary_subset(df: pd.DataFrame) -> pd.DataFrame:
    out = df[df["model_label"].isin(BINARY) & df["human_label"].isin(BINARY)].copy()
    out["agreement"] = out["human_label"] == out["model_label"]
    return out


def safe_div(a: float, b: float) -> float:
    return float(a / b) if b else math.nan


def metrics_for(df: pd.DataFrame, name: str) -> dict[str, object]:
    total = len(df)
    if total == 0:
        return {"slice": name, "valid_binary_reviewed": 0}
    tp_a = int(((df["model_label"] == "ACTIVE") & (df["human_label"] == "ACTIVE")).sum())
    fn_a = int(((df["model_label"] == "ACTIVE") & (df["human_label"] == "FLATTENING")).sum())
    fp_a = int(((df["model_label"] == "FLATTENING") & (df["human_label"] == "ACTIVE")).sum())
    tn_a = int(((df["model_label"] == "FLATTENING") & (df["human_label"] == "FLATTENING")).sum())
    recall_a = safe_div(tp_a, tp_a + fn_a)
    recall_f = safe_div(tn_a, tn_a + fp_a)
    precision_a = safe_div(tp_a, tp_a + fp_a)
    precision_f = safe_div(tn_a, tn_a + fn_a)
    raw = float((df["human_label"] == df["model_label"]).mean())
    bal = float(pd.Series([recall_a, recall_f]).dropna().mean()) if not pd.Series([recall_a, recall_f]).dropna().empty else math.nan
    actual_a = int((df["model_label"] == "ACTIVE").sum())
    actual_f = int((df["model_label"] == "FLATTENING").sum())
    pred_a = int((df["human_label"] == "ACTIVE").sum())
    pred_f = int((df["human_label"] == "FLATTENING").sum())
    pe = safe_div(actual_a * pred_a + actual_f * pred_f, total * total)
    kappa = safe_div(raw - pe, 1 - pe) if pe != 1 else math.nan
    return {
        "slice": name,
        "valid_binary_reviewed": total,
        "raw_agreement": raw,
        "balanced_accuracy": bal,
        "cohens_kappa": kappa,
        "precision_ACTIVE": precision_a,
        "recall_ACTIVE": recall_a,
        "precision_FLATTENING": precision_f,
        "recall_FLATTENING": recall_f,
    }


def main() -> None:
    df = load_and_validate()
    ambiguous_count = int((df["human_label"] == "AMBIGUOUS").sum())
    ambiguous_fraction = float(ambiguous_count / len(df)) if len(df) else math.nan
    binary = binary_subset(df)
    metrics = metrics_for(binary, "all_binary")
    metrics.update({"total_reviewed": int(len(df)), "ambiguous_count": ambiguous_count, "ambiguous_fraction": ambiguous_fraction})
    pd.DataFrame([metrics]).to_csv(OUT / "blind_validation_metrics.csv", index=False)

    conf = pd.crosstab(binary["model_label"], binary["human_label"]).reindex(index=["ACTIVE", "FLATTENING"], columns=["ACTIVE", "FLATTENING"], fill_value=0)
    conf.to_csv(OUT / "confusion_matrix.csv")

    confidence_rows = []
    for c in ["1", "2", "3"]:
        confidence_rows.append(metrics_for(binary[binary["confidence"] == c], f"confidence_{c}"))
    pd.DataFrame(confidence_rows).to_csv(OUT / "confidence_metrics.csv", index=False)

    direction_rows = []
    for d in ["UP", "DOWN"]:
        direction_rows.append(metrics_for(binary[binary["direction_4h"] == d], f"direction_{d}"))
    pd.DataFrame(direction_rows).to_csv(OUT / "up_down_metrics.csv", index=False)

    type_rows = []
    for source_type in sorted(df["source_type"].unique()):
        type_rows.append(metrics_for(binary[binary["source_type"] == source_type], source_type))
    pd.DataFrame(type_rows).to_csv(OUT / "type_metrics.csv", index=False)

    unblind = df.copy()
    unblind["agreement"] = unblind["human_label"] == unblind["model_label"]
    unblind.rename(columns={"original_start_time": "start_time", "original_end_time": "end_time"})[
        ["blind_id", "human_label", "confidence", "model_label", "agreement", "source_type", "direction_4h", "start_time", "end_time", "comment"]
    ].to_csv(OUT / "unblinded_results.csv", index=False)
    unblind[~unblind["agreement"]][
        ["blind_id", "human_label", "confidence", "model_label", "source_type", "direction_4h", "original_start_time", "original_end_time", "comment"]
    ].to_csv(OUT / "disagreement_cases.csv", index=False)
    print(pd.DataFrame([metrics]).to_string(index=False))


if __name__ == "__main__":
    main()
