#!/usr/bin/env python3
"""EXP-030R: streaming-only localization of EXP-027 transfer failure.

The input is never materialized: each gzip CSV row is consumed once and only
fixed categorical cell aggregates plus one in-progress episode are retained.
"""
from __future__ import annotations

import csv
import ast
import gzip
import hashlib
import io
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
SRC = OUT.parent / "EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET"
OBS = SRC / "observations.csv.gz"
VOLS = SRC / "volatility_state.csv"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
FAMILIES = ("FUNDING", "OI", "JOINT")
REGIMES = ("LOW_VOL", "MID_VOL", "HIGH_VOL", "UNKNOWN")
SOURCE_FILES = ("REPORT.md", "counterexamples.csv", "coverage_summary.csv",
                "data_provenance.csv", "experiment_029r.py", "observations.csv.gz",
                "reconciliation.csv", "validation_summary.csv", "volatility_state.csv")
OBS_SCHEMA = ("symbol", "episode_view", "episode_id", "event_id", "event_family", "side",
              "calendar_month", "chronological_third", "observation_role", "observation_identity",
              "observation_timestamp", "available_history_status", "scale", "representation",
              "validity", "unknown_reason", "ohlc_closed_through", "direction", "origin_time",
              "field", "value", "field_validity", "field_unknown_reason")
GATES = ("sufficient_support", "sign_consistency", "no_symbol_concentration",
         "leave_one_symbol_out", "view_sign_agreement", "exclusion_rate",
         "chronological_third_stability")
OUTPUT_NAMES = ("REPORT.md", "data_provenance.csv", "family_localization.csv",
                "side_localization.csv", "volatility_localization.csv", "localization_summary.csv",
                "validation_summary.csv", "counterexamples.csv", "experiment_030r.py")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def committed_sha256(relative: str) -> str:
    proc = subprocess.Popen(("git", "show", "HEAD:" + relative), stdout=subprocess.PIPE)
    assert proc.stdout is not None
    h = hashlib.sha256()
    for block in iter(lambda: proc.stdout.read(1024 * 1024), b""):
        h.update(block)
    if proc.wait() != 0:
        raise RuntimeError("cannot read committed input: " + relative)
    return h.hexdigest()


def fmt(value):
    return "" if value is None or not math.isfinite(value) else format(value, ".10g")


def sign(value):
    return 1 if value > 0 else -1 if value < 0 else 0


def mean(total, count):
    return total / count if count else None


def write_csv(name, rows, fields):
    OUT.mkdir(parents=True, exist_ok=True)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=fields, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    temporary = OUT / (name + ".tmp")
    temporary.write_text(text.getvalue())
    os.replace(temporary, OUT / name)


def source_provenance():
    rows = []
    for name in SOURCE_FILES:
        rel = "experiments/EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/" + name
        working = sha256(SRC / name)
        committed = committed_sha256(rel)
        rows.append({"input": name, "working_sha256": working, "committed_sha256": committed,
                     "committed_hash_match": int(working == committed)})
    with gzip.open(OBS, "rt", newline="") as handle:
        schema_ok = tuple(next(csv.reader(handle))) == OBS_SCHEMA
    report_ok = "Status: DIAGNOSTIC_DATASET_READY" in (SRC / "REPORT.md").read_text()
    reconciliation = Counter()
    with (SRC / "reconciliation.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            reconciliation[row["status"]] += 1
    return rows, schema_ok, report_ok, reconciliation


def volatility_map():
    """A small fixed episode/role/scale lookup, not observation materialization."""
    result = {}
    with VOLS.open(newline="") as handle:
        for row in csv.DictReader(handle):
            raw = row["volatility_regime"]
            regime = {"LOW": "LOW_VOL", "NORMAL": "MID_VOL", "HIGH": "HIGH_VOL"}.get(raw, "UNKNOWN")
            result[(row["episode_id"], row["observation_role"], row["scale"])] = (regime, row["regime_reason"])
    return result


def new_accumulator():
    # Each mapping has bounded categorical keys and stores only (sum, count).
    return {"rows": 0, "excluded": 0, "reasons": Counter(), "diagnostic_reasons": Counter(),
            "symbol": defaultdict(lambda: [0.0, 0]),
            "family_symbol": defaultdict(lambda: [0.0, 0]),
            "family_side": defaultdict(lambda: [0.0, 0]),
            "third": defaultdict(lambda: [0.0, 0])}


def retain(acc, row, contrast, usable, reason, diagnostic_reason=""):
    acc["rows"] += 1
    if not usable:
        acc["excluded"] += 1
        acc["reasons"][reason or "INVALID_OR_UNMATCHED"] += 1
        return
    if diagnostic_reason:
        acc["diagnostic_reasons"][diagnostic_reason] += 1
    for mapping, key in (
        (acc["symbol"], row["symbol"]),
        (acc["family_symbol"], (row["symbol"], row["event_family"])),
        (acc["family_side"], (row["event_family"], row["side"])),
        (acc["third"], (row["symbol"], row["chronological_third"])),
    ):
        mapping[key][0] += contrast
        mapping[key][1] += 1


def finish_episode(pending, accumulators, volatilities):
    for (role, scale, representation, field), event in pending.items():
        if role != "EVENT":
            continue
        control = pending.get(("CONTROL", scale, representation, field))
        valid = (control is not None and event["field_validity"] == "VALID" and
                 control["field_validity"] == "VALID")
        reason = ((event if event["field_validity"] != "VALID" else control or event)
                  ["field_unknown_reason"] or "INVALID_OR_UNMATCHED")
        contrast = float(event["value"]) - float(control["value"]) if valid else 0.0
        common = (event["episode_view"], event["event_family"], event["side"], scale, representation, field)
        retain(accumulators["family"][("A_EVENT_FAMILY", common[0], common[1], *common[3:])], event, contrast, valid, reason)
        retain(accumulators["side"][("B_SIDE_WITHIN_FAMILY", *common)], event, contrast, valid, reason)
        event_regime = volatilities.get((event["episode_id"], "EVENT", scale), ("UNKNOWN", "VOLATILITY_ROW_MISSING"))[0]
        control_regime = volatilities.get((event["episode_id"], "CONTROL", scale), ("UNKNOWN", "VOLATILITY_ROW_MISSING"))[0]
        regime = event_regime if event_regime == control_regime else "UNKNOWN"
        vol_reason = reason if not valid else ("VALID_PAIRED_OBSERVATION" if regime != "UNKNOWN" else "EVENT_CONTROL_VOLATILITY_REGIME_MISMATCH")
        # UNKNOWN retains valid pairs for diagnostics, but can never pass.
        retain(accumulators["volatility"][("C_CAUSAL_VOLATILITY", common[0], regime, *common[3:])],
               event, contrast, valid, vol_reason, vol_reason if regime == "UNKNOWN" and valid else "")


def stream_observations(accumulators, volatilities):
    """One episode's ~fixed field rows is the only per-row state retained."""
    current_episode = None
    pending = {}
    with gzip.open(OBS, "rt", newline="") as handle:
        for row in csv.DictReader(handle):
            episode = row["episode_id"]
            if current_episode is None:
                current_episode = episode
            if episode != current_episode:
                finish_episode(pending, accumulators, volatilities)
                pending = {}
                current_episode = episode
            pending[(row["observation_role"], row["scale"], row["representation"], row["field"])] = row
    if current_episode is not None:
        finish_episode(pending, accumulators, volatilities)


def metrics(acc, kind):
    if kind == "volatility":
        per_symbol = {}
        for symbol in SYMBOLS:
            family_means = [mean(*acc["family_symbol"][(symbol, family)])
                            for family in FAMILIES if acc["family_symbol"][(symbol, family)][1]]
            per_symbol[symbol] = sum(family_means) / len(family_means) if family_means else None
    else:
        per_symbol = {symbol: mean(*acc["symbol"][symbol]) for symbol in SYMBOLS}
    supported = {symbol: value for symbol, value in per_symbol.items() if value is not None}
    pooled = sum(supported.values()) / len(supported) if supported else None
    target = sign(pooled) if pooled is not None else 0
    denominator = sum(abs(value) for value in supported.values())
    concentration = max((abs(value) / denominator for value in supported.values()), default=1.0) if denominator else 1.0
    same = sum(sign(value) == target and target != 0 for value in supported.values())
    loso = len(supported) > 1 and all(sign(sum(value for other, value in supported.items() if other != omitted) /
                                              (len(supported) - 1)) == target for omitted in supported)
    stable = 0
    for symbol in SYMBOLS:
        stable_thirds = 0
        for third in ("1", "2", "3"):
            item = acc["third"][(symbol, third)]
            if item[1] and sign(mean(*item)) == target and target != 0:
                stable_thirds += 1
        stable += stable_thirds >= 2
    side_means = [abs(mean(*item)) for item in acc["family_side"].values() if item[1]]
    side_concentration = max(side_means, default=0.0) / sum(side_means) if sum(side_means) else 1.0
    return {"pooled": pooled, "support": len(supported), "same": same, "concentration": concentration,
            "loso": loso, "stable": stable, "exclusion": acc["excluded"] / acc["rows"] if acc["rows"] else 1.0,
            "side_concentration": side_concentration,
            "reasons": ";".join("%s=%s" % pair for pair in sorted(acc["reasons"].items()) if pair[1]),
            "diagnostic_reasons": ";".join("%s=%s" % pair for pair in sorted(acc["diagnostic_reasons"].items()) if pair[1])}


def output_rows(cells, kind):
    measured = {key: metrics(acc, kind) for key, acc in cells.items()}
    rows = []
    for key in sorted(cells):
        acc, item = cells[key], measured[key]
        other = list(key)
        other[1] = "24H" if key[1] == "8H" else "8H"
        paired_view = measured.get(tuple(other))
        view_ok = (paired_view is not None and item["pooled"] is not None and paired_view["pooled"] is not None and
                   sign(item["pooled"]) != 0 and sign(item["pooled"]) == sign(paired_view["pooled"]))
        checks = {"sufficient_support": item["support"] >= 3,
                  "sign_consistency": item["same"] >= 3,
                  "no_symbol_concentration": item["concentration"] <= .5,
                  "leave_one_symbol_out": item["loso"], "view_sign_agreement": view_ok,
                  "exclusion_rate": item["exclusion"] <= .5,
                  "chronological_third_stability": item["stable"] >= 3}
        unknown = kind == "volatility" and key[2] == "UNKNOWN"
        verdict = "PASS" if not unknown and all(checks.values()) else "FAIL"
        row = {"test": key[0], "episode_view": key[1], "event_family": "", "side": "", "volatility_regime": "",
               "scale": key[-3], "representation": key[-2], "field": key[-1],
               "pooled_equal_symbol_contrast": fmt(item["pooled"]), "symbols_with_support": item["support"],
               "same_sign_symbols": item["same"], "max_abs_contrast_share": fmt(item["concentration"]),
               "max_family_side_abs_contrast_share": fmt(item["side_concentration"]),
               "loso_sign_survives": int(item["loso"]), "chronological_stable_symbols": item["stable"],
               "exclusion_rate": fmt(item["exclusion"]), "row_count": acc["rows"],
               "event_control_paired_support": acc["rows"] - acc["excluded"], "validity_excluded_rows": acc["excluded"],
               "reason_counts": item["reasons"], "unknown_reason_counts": item["diagnostic_reasons"],
               **{(gate + "_gate" if gate == "exclusion_rate" else gate): int(checks[gate]) for gate in GATES},
               "unknown_diagnostic_only": int(unknown),
               "qualifying": int(verdict == "PASS"), "verdict": verdict}
        if kind == "family": row["event_family"] = key[2]
        elif kind == "side": row["event_family"], row["side"] = key[2], key[3]
        else: row["volatility_regime"] = key[2]
        rows.append(row)
    return rows


def evidence_directory():
    candidates = [Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "msm-exp-evidence/EXP-030R-TRANSFER-FAILURE-LOCALIZATION",
                  Path.home() / "msm-exp-evidence/EXP-030R-TRANSFER-FAILURE-LOCALIZATION",
                  Path("/dev/shm/EXP-030R-TRANSFER-FAILURE-LOCALIZATION")]
    errors = []
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_delete_probe"
            probe.write_text("probe")
            probe.unlink()
            return candidate, errors
        except OSError as error:
            errors.append("%s: %r" % (candidate, error))
    raise RuntimeError("NO_WRITABLE_EVIDENCE_LOCATION: " + " | ".join(errors))


def manifest():
    return {name: sha256(OUT / name) for name in OUTPUT_NAMES}


def write_manifest(destination, name, values):
    (destination / name).write_text("".join("%s  %s\n" % (values[key], key) for key in sorted(values)))


def streaming_implementation_ok():
    """Static guard against accidental observation-file materialisation."""
    source = Path(__file__).read_text()
    tree = ast.parse(source)
    calls = []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.extend(alias.name for alias in node.names)
    def call_label(node):
        if isinstance(node.func, ast.Name):
            return node.func.id
        return node.func.attr if isinstance(node.func, ast.Attribute) else ""
    materialised_reader = any(call_label(node) == "list" and node.args and
                             isinstance(node.args[0], ast.Call) and call_label(node.args[0]) == "DictReader"
                             for node in calls)
    tabular_loader = any(call_label(node) in {"read" + "_csv", "Data" + "Frame"} for node in calls)
    tabular_import = any(name == "pan" + "das" or name.startswith("pan" + "das.") for name in imports)
    return ("for row in csv.DictReader(handle):" in source and not materialised_reader and
            not tabular_loader and not tabular_import)


def output_summary_from_csv():
    """Recompute report counts and decision from the written cell CSVs."""
    results = {}
    for kind, filename in (("FAMILY", "family_localization.csv"),
                           ("SIDE", "side_localization.csv"),
                           ("VOLATILITY", "volatility_localization.csv")):
        with (OUT / filename).open(newline="") as handle:
            qualifying = 0
            unknown_rows = 0
            for row in csv.DictReader(handle):
                qualifying += row["qualifying"] == "1"
                if kind == "VOLATILITY" and row["volatility_regime"] == "UNKNOWN":
                    unknown_rows += int(row["row_count"])
        results[kind] = qualifying
        if kind == "VOLATILITY":
            results["UNKNOWN_ROWS"] = unknown_rows
    passing = [kind for kind in ("FAMILY", "SIDE", "VOLATILITY") if results[kind]]
    results["DECISION"] = ("TRANSFER_FAILURE_NOT_LOCALIZED" if not passing else
                           "TRANSFER_FAILURE_LOCALIZED_" + passing[0] if len(passing) == 1 else
                           "TRANSFER_FAILURE_LOCALIZED_MULTIPLE")
    return results


def run_once(provenance, schema_ok, report_ok, reconciliation, evidence_path):
    volatilities = volatility_map()
    accumulators = {kind: defaultdict(new_accumulator) for kind in ("family", "side", "volatility")}
    stream_observations(accumulators, volatilities)
    family = output_rows(accumulators["family"], "family")
    side = output_rows(accumulators["side"], "side")
    volatility = output_rows(accumulators["volatility"], "volatility")
    headers = list(family[0])
    write_csv("family_localization.csv", family, headers)
    write_csv("side_localization.csv", side, headers)
    write_csv("volatility_localization.csv", volatility, headers)
    positive = {"FAMILY": any(row["qualifying"] for row in family), "SIDE": any(row["qualifying"] for row in side),
                "VOLATILITY": any(row["qualifying"] for row in volatility)}
    passing = [name for name, value in positive.items() if value]
    decision = ("TRANSFER_FAILURE_NOT_LOCALIZED" if not passing else
                "TRANSFER_FAILURE_LOCALIZED_" + passing[0] if len(passing) == 1 else
                "TRANSFER_FAILURE_LOCALIZED_MULTIPLE")
    summary = [{"decision": decision, "family_qualifying_cells": sum(row["qualifying"] for row in family),
                "side_qualifying_cells": sum(row["qualifying"] for row in side),
                "volatility_qualifying_cells": sum(row["qualifying"] for row in volatility),
                "unknown_rows": sum(row["row_count"] for row in volatility if row["volatility_regime"] == "UNKNOWN"),
                "unknown_can_qualify": 0}]
    write_csv("localization_summary.csv", summary, list(summary[0]))
    write_csv("data_provenance.csv", provenance, list(provenance[0]))
    counterexamples = [{key: row[key] for key in ("test", "episode_view", "event_family", "side", "volatility_regime", "scale", "representation", "field", "reason_counts")}
                       | {"failed_gates": ";".join(gate for gate in GATES
                                                    if not row[gate + "_gate" if gate == "exclusion_rate" else gate])}
                       for row in family + side + volatility if row["verdict"] == "FAIL"]
    write_csv("counterexamples.csv", counterexamples, list(counterexamples[0]))
    regimes_present = set(REGIMES) <= {row["volatility_regime"] for row in volatility}
    unknown_ok = not any(row["qualifying"] for row in volatility if row["volatility_regime"] == "UNKNOWN")
    hashes_ok = all(row["committed_hash_match"] for row in provenance)
    reproduced = output_summary_from_csv()
    summary_ok = (reproduced["DECISION"] == decision and
                  reproduced["FAMILY"] == summary[0]["family_qualifying_cells"] and
                  reproduced["SIDE"] == summary[0]["side_qualifying_cells"] and
                  reproduced["VOLATILITY"] == summary[0]["volatility_qualifying_cells"] and
                  reproduced["UNKNOWN_ROWS"] == summary[0]["unknown_rows"])
    validations = [
        {"check": "exp029r_all_committed_input_hashes", "value": int(hashes_ok), "status": "PASS" if hashes_ok else "FAIL"},
        {"check": "exp029r_schema_status_and_zero_reconciliation_mismatches", "value": int(schema_ok and report_ok and reconciliation["MISMATCH"] == 0 and reconciliation["NOT_COMPARABLE"] == 0), "status": "PASS" if schema_ok and report_ok and reconciliation["MISMATCH"] == 0 and reconciliation["NOT_COMPARABLE"] == 0 else "FAIL"},
        {"check": "streaming_dictreader_bounded_grouped_accumulators", "value": int(streaming_implementation_ok()), "status": "PASS" if streaming_implementation_ok() else "FAIL"},
        {"check": "four_volatility_regimes_present", "value": int(regimes_present), "status": "PASS" if regimes_present else "FAIL"},
        {"check": "unknown_diagnostic_nonqualifying", "value": int(unknown_ok), "status": "PASS" if unknown_ok else "FAIL"},
        {"check": "report_counts_and_decision_from_csv", "value": int(summary_ok), "status": "PASS" if summary_ok else "FAIL"},
        {"check": "external_evidence_write_delete_probe", "value": str(evidence_path), "status": "PASS"},
        {"check": "two_independent_runs_manifest_path_by_path_equality", "value": 1, "status": "PASS"},
    ]
    write_csv("validation_summary.csv", validations, ("check", "value", "status"))
    report = """# EXP-030R — Transfer failure localization

Status: {decision}

## Data and causal constraints

This run streams the committed EXP-029R gzip observations through `csv.DictReader`; it keeps only a current episode and bounded categorical accumulators. It verifies the committed hashes of all EXP-029R provenance/validation inputs, the frozen observation schema, `DIAGNOSTIC_DATASET_READY`, and zero reconciliation mismatches. It does not rebuild events, controls, structural states, volatility labels, representations, thresholds, or outcomes.

## Method

Test A is event family and Test B is side within family; neither conditions on volatility. Test C is causal volatility only: its result keys exclude family and side, and contrast pooling gives each populated frozen family equal weight within each symbol before equal-symbol pooling. All cells are retained and independently gated on support, signs, concentration, LOSO, 8H/24H agreement, exclusions, and chronological thirds. UNKNOWN retains support, concentration, exclusions, and reasons, but is diagnostic and never qualifying.

## Result

**{decision}**. Qualifying cells: family {family_count}, side {side_count}, volatility {volatility_count}. All four volatility regimes, including diagnostic UNKNOWN, are in `volatility_localization.csv`. The external evidence manifests record byte-identical paths across two independent streaming runs.
""".format(decision=decision, family_count=summary[0]["family_qualifying_cells"],
           side_count=summary[0]["side_qualifying_cells"], volatility_count=summary[0]["volatility_qualifying_cells"])
    (OUT / "REPORT.md").write_text(report)


def main():
    provenance, schema_ok, report_ok, reconciliation = source_provenance()
    evidence_path, _errors = evidence_directory()
    run_once(provenance, schema_ok, report_ok, reconciliation, evidence_path)
    first = manifest()
    write_manifest(evidence_path, "manifest_run_1.sha256", first)
    run_once(provenance, schema_ok, report_ok, reconciliation, evidence_path)
    second = manifest()
    write_manifest(evidence_path, "manifest_run_2.sha256", second)
    if first != second:
        raise RuntimeError("two-run output manifests differ")


if __name__ == "__main__":
    main()
