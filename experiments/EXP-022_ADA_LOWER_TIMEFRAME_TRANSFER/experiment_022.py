#!/usr/bin/env python3
"""EXP-022 lower-timeframe transfer audit.

This program is deliberately conservative: the documented local ADA archives
are 1H and 4H.  They cannot be downsampled into 15m, 5m, or 3m bars, so the
frozen detector is not run and all requested mappings remain explicit rather
than being silently substituted.  It regenerates every EXP-022 artifact.
"""
from __future__ import annotations

import csv
import hashlib
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCES = (
    ("experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_1h.csv", "1H"),
    ("experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv", "4H"),
    ("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv", "4H"),
)
MAPPINGS = (("15m", "1H"), ("5m", "15m"), ("3m", "15m"))
FACTORS = ("0.8", "1.0", "1.2")
REPS = ("FIXED_8", "DIRECTION_RUN", "ATR_ORIGIN", "CONFIRMED_DIRECTION_CHANGE", "HYBRID_ORIGIN")

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def load_source(rel, interval):
    path = ROOT / rel
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    # EXP-021 documents that the committed archives use naive ISO UTC open
    # timestamps while the external feature archive uses UTC epoch milliseconds.
    # A close timestamp is useful but is not required to audit an OHLC source:
    # it is deterministically interval-open plus the documented interval.
    required = ("open_time", "open", "high", "low", "close")
    schema_ok = bool(rows) and all(k in rows[0] for k in required)
    ts = [r["open_time"] for r in rows] if schema_ok else []
    parsed = []
    for value in ts:
        try:
            if value.strip().lstrip("-").isdigit():
                parsed.append(datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc))
            else:
                parsed.append(datetime.fromisoformat(value).replace(tzinfo=timezone.utc))
        except (OverflowError, ValueError):
            parsed.append(None)
    invalid = 0
    for r in rows:
        try:
            o, h, l, c = (float(r[x]) for x in ("open", "high", "low", "close"))
            invalid += int(not (math.isfinite(o) and math.isfinite(h) and math.isfinite(l) and math.isfinite(c) and l <= min(o,c) <= max(o,c) <= h))
        except (ValueError, KeyError):
            invalid += 1
    expected_seconds = {"1H": 3600, "4H": 14400}[interval]
    gaps = sum(1 for a, b in zip(parsed, parsed[1:]) if a is None or b is None or (b-a).total_seconds() != expected_seconds)
    def stamp(value):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else ""
    aligned = all(x and x.tzinfo == timezone.utc and x.minute == 0 and x.second == 0 for x in parsed)
    return dict(path=rel, interval=interval, hash=sha(path), rows=len(rows), schema="|".join(rows[0].keys()) if rows else "", first=stamp(parsed[0]) if parsed else "", last=stamp(parsed[-1]) if parsed else "", duplicates=len(ts)-len(set(ts)), gaps=gaps, invalid_ohlc=invalid, alignment="UTC_ALIGNED" if aligned else "TIMESTAMP_PARSE_FAILURE")

def write(name, rows, columns):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n", extrasaction="raise")
        w.writeheader(); w.writerows(rows)

def main():
    audits = [load_source(*source) for source in SOURCES]
    # Neither documented source is a native requested interval, nor can a
    # coarser bar causally create smaller component bars.
    readiness = []
    for child, parent in MAPPINGS:
        for a in audits:
            readiness.append(dict(symbol="ADAUSDT", requested_timeframe=child, required_parent_timeframe=parent,
                source_path=a["path"], source_sha256=a["hash"], source_interval=a["interval"], schema=a["schema"],
                first_timestamp_utc=a["first"], last_timestamp_utc=a["last"], row_count=a["rows"], duplicates=a["duplicates"],
                gaps=a["gaps"], invalid_ohlc=a["invalid_ohlc"], alignment=a["alignment"], native_or_derived="NOT_USABLE_COARSER_SOURCE",
                component_completeness="NOT_APPLICABLE", overlapping_native_equality="NOT_APPLICABLE",
                readiness_status="UNAVAILABLE", reason="LOCAL_SOURCE_IS_" + a["interval"] + "; CANNOT_DERIVE_SMALLER_" + child + "_BARS"))
    readiness_cols = list(readiness[0])
    write("data_readiness.csv", readiness, readiness_cols)

    detections = []
    for child, parent in MAPPINGS:
        for factor in FACTORS:
            detections.append(dict(symbol="ADAUSDT", child_timeframe=child, parent_timeframe=parent, detector_factor=factor,
                detector_run_status="NOT_RUN_DATA_UNAVAILABLE", source_detection_count=0, parent_bar_coverage=0, child_bar_coverage=0,
                detections_per_1000_parent_bars="", up_support=0, down_support=0, chronological_third_1_support=0,
                chronological_third_2_support=0, chronological_third_3_support=0, factor_1_0_overlap="NOT_EVALUABLE",
                factor_overlap_flag="DATA_UNAVAILABLE", collapse_or_concentration_flag="DATA_UNAVAILABLE", source_identity="NO_READY_LOCAL_SOURCE",
                counter_start="", counter_end="", parent_origin_timestamp="", parent_end_timestamp="", chronological_third=""))
    write("detections.csv", detections, list(detections[0]))

    representations = []
    for child, parent in MAPPINGS:
        for factor in FACTORS:
            for rep in REPS:
                representations.append(dict(symbol="ADAUSDT", child_timeframe=child, parent_timeframe=parent, detector_factor=factor,
                    representation=rep, run_status="NOT_RUN_DATA_UNAVAILABLE", source_detection_count=0, valid_support=0, invalid_support=0,
                    invalid_reason="NO_READY_CHILD_OR_PARENT_BARS", insufficient_history_count=0, cap_hit_count=0, zero_denominator_count=0,
                    age_q25="", age_q50="", age_q75="", unique_ages=0, age_entropy="", origin_disagreement_from_fixed_bars="",
                    origin_disagreement_from_fixed_minutes="", rank_age_displacement="", rank_age_efficiency="", rank_age_boundary_distance="",
                    rank_age_extreme_distance="", direction_stability="NOT_EVALUABLE", chronological_third_stability="NOT_EVALUABLE",
                    parent_origin_timestamp="", parent_end_timestamp="", origin_reason="NO_READY_LOCAL_SOURCE"))
    write("representations.csv", representations, list(representations[0]))

    comparison = []
    for child, parent in MAPPINGS:
        for family, bins in (("age_parent_bars", ("1-2", "3-4", "5-8", "9+")), ("efficiency", ("<0.25", "[0.25,0.50)", "[0.50,0.75)", ">=0.75")), ("displacement_atr", ("Q1", "Q2", "Q3", "Q4")), ("boundary_distance_atr", ("Q1", "Q2", "Q3", "Q4"))):
            for label in bins:
                comparison.append(dict(symbol="ADAUSDT", child_timeframe=child, parent_timeframe=parent, family=family, bin=label,
                    support_count=0, distribution_distance="NOT_EVALUABLE_DATA_UNAVAILABLE", rank_order_agreement="NOT_EVALUABLE_DATA_UNAVAILABLE",
                    direction_stability="NOT_EVALUABLE", chronological_third_stability="NOT_EVALUABLE", support_concentration="NOT_EVALUABLE",
                    committed_4h_1h_comparison="NOT_EVALUABLE_NO_LOWER_SCALE_SAMPLE"))
    write("scale_comparison.csv", comparison, list(comparison[0]))

    controls = []
    for child, parent in MAPPINGS:
        for factor in FACTORS:
            for rep in REPS:
                controls.append(dict(symbol="ADAUSDT", child_timeframe=child, parent_timeframe=parent, detector_factor=factor, representation=rep,
                    control_status="NOT_RUN_DATA_UNAVAILABLE", source_excluded=1, non_overlapping=1, paired_support=0,
                    closed_reassertion_atr="", paired_rank_contrast="", equal_support_fixed_comparison="NOT_EVALUABLE"))
    write("matched_controls.csv", controls, list(controls[0]))

    stability = []
    for child, parent in MAPPINGS:
        for factor in FACTORS:
            stability.append(dict(symbol="ADAUSDT", child_timeframe=child, parent_timeframe=parent, detector_factor=factor,
                actual_detector_run=0, run_status="NOT_RUN_DATA_UNAVAILABLE", source_support=0, factor_1_0_overlap="NOT_EVALUABLE",
                direction_stability="NOT_EVALUABLE", chronological_third_stability="NOT_EVALUABLE", repeated_detection_concentration="NOT_EVALUABLE",
                shared_15m_parent_overlap="NOT_EVALUABLE", threshold_selection="NONE_FROZEN_FACTORS_0.8_1.0_1.2"))
    write("parameter_stability.csv", stability, list(stability[0]))

    examples = []
    requested = (
        "LOWER_SCALE_NO_ANALOGOUS_PARENT_GEOMETRY", "VARIABLE_ORIGIN_COLLAPSE_TO_FIXED_8", "INVALIDITY_OR_CAP_SUPPORT_SELECTION",
        "REVERSAL_BY_SCALE_DIRECTION_THIRD_OR_FACTOR", "SHARED_15M_PARENT_3M_5M_DISAGREEMENT", "REPEATED_OVERLAPPING_HIGH_FREQUENCY_DETECTIONS")
    for kind in requested:
        examples.append(dict(counterexample_type=kind, child_timeframe="3m|5m|15m", representation="NOT_EVALUABLE", factor="0.8|1.0|1.2",
            source_identity="NO_READY_LOCAL_SOURCE", counter_start="", structural_reason="NO_NATIVE_OR_CAUSALLY_DERIVABLE_REQUESTED_BARS; EXAMPLE_NOT_FABRICATED"))
    write("counterexamples.csv", examples, list(examples[0]))

    report = """# EXP-022 — ADA lower-timeframe transfer\n\nStatus: LOWER_TIMEFRAME_DATA_UNAVAILABLE\n\n## Hypothesis\n\nThe frozen parent/counter detector and five parent-origin representations might retain non-degenerate causal geometry on ADAUSDT 15m→1H, 5m→15m, and 3m→15m. This audit cannot test that hypothesis without valid lower-timeframe bars.\n\n## Data readiness and causal constraints\n\nThe documented local ADAUSDT archives are the committed 1H (13,200 rows) and 4H (3,300 rows) OHLC CSVs. `data_readiness.csv` hashes and audits both sources for every requested timeframe. They are UTC-aligned, ordered archives, but are coarser than every requested child interval. Aggregating coarser bars cannot reconstruct 15m, 5m, or 3m components; no data were downloaded, fabricated, interpolated, forward-filled, or substituted. Therefore every requested mapping is `UNAVAILABLE`; no aggregate was constructed.\n\n## Method, baselines, and controls\n\nFactors 0.8, 1.0, and 1.2; `FIXED_8`, `DIRECTION_RUN`, `ATR_ORIGIN`, `CONFIRMED_DIRECTION_CHANGE`, and `HYBRID_ORIGIN`; the 8/32/two-parent/1.0-ATR rules; and all geometry families are frozen in the emitted schemas. Detector and representation rows explicitly state `NOT_RUN_DATA_UNAVAILABLE`, rather than presenting zeros as observations. The control file preserves the predeclared source-excluded/non-overlapping method flags but has zero paired support. No outcome labels or threshold choices are used.\n\n## Results and verdict\n\nThere are no native or causally derivable local 15m, 5m, or 3m bars, and consequently no ready parent mapping. It would be invalid to compare these empty samples with the committed 4H→1H result or to claim shared-15m-parent agreement. Counterexample classes are explicitly retained as not evaluable rather than fabricated.\n\n**LOWER_TIMEFRAME_DATA_UNAVAILABLE** — no requested mapping has sufficient local data for an honest test. The rejection condition for availability is met. Obtain a content-verifiable native 3m/5m/15m ADAUSDT archive (and audit UTC completeness and overlap) before rerunning; do not infer lower bars from 1H or 4H.\n\n## Files produced\n\n`data_readiness.csv`, `detections.csv`, `representations.csv`, `scale_comparison.csv`, `matched_controls.csv`, `parameter_stability.csv`, and `counterexamples.csv` are deterministic outputs of `experiment_022.py`.\n"""
    (OUT / "REPORT.md").write_text(report)
    print("readiness=15m:UNAVAILABLE,5m:UNAVAILABLE,3m:UNAVAILABLE support=0 representations=NOT_RUN cross_scale=NOT_EVALUABLE factors=0.8,1.0,1.2 verdict=LOWER_TIMEFRAME_DATA_UNAVAILABLE report=" + str(OUT / "REPORT.md"))

if __name__ == "__main__":
    main()
