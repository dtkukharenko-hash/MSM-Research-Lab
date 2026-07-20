#!/usr/bin/env python3
"""Acquire and independently validate the frozen DATA-001 Bybit 2025 panel.

Only Python's standard library is used.  This program intentionally writes market
archives outside the repository and writes the six DATA-001 evidence files here.
"""
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
START = 1735689600000  # 2025-01-01T00:00:00Z
END = 1767225600000    # exclusive 2026-01-01T00:00:00Z
API = "https://api.bybit.com/v5/market/"
OUT = Path(__file__).resolve().parent
ROOT = Path(os.environ["MSM_MARKET_DATA_ROOT"]).resolve()
PROVENANCE = OUT.parents[2] / "experiments" / "EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET" / "data_provenance.csv"
SPECS = {
    "15m": {"resource": "kline", "params": {"category": "linear", "interval": "15"}, "header": ("timestamp_utc", "open", "high", "low", "close", "volume", "turnover"), "step": 900000, "expected": 35040, "limit": 1000, "file": "_15m.csv"},
    "funding": {"resource": "funding/history", "params": {"category": "linear"}, "header": ("timestamp_utc", "funding_rate"), "step": 28800000, "expected": 1095, "limit": 200, "file": "_funding.csv"},
    "oi": {"resource": "open-interest", "params": {"category": "linear", "intervalTime": "15min"}, "header": ("timestamp_utc", "open_interest"), "step": 900000, "expected": 35040, "limit": 200, "file": "_oi.csv"},
}

def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".data001-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
        dfd = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if os.path.exists(name): os.unlink(name)

def request(kind, symbol, start, end):
    spec = SPECS[kind]
    q = dict(spec["params"], symbol=symbol, startTime=str(start), endTime=str(end - 1), limit=str(spec["limit"]))
    url = API + spec["resource"] + "?" + urlencode(q)
    last = ""
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": "MSM-Research-Lab/DATA-001"}), timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
            if payload.get("retCode") != 0:
                raise RuntimeError("retCode=%s retMsg=%s" % (payload.get("retCode"), payload.get("retMsg")))
            return payload.get("result", {}).get("list", []), attempt + 1, "HTTP_200"
        except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError) as e:
            last = "%s: %s" % (type(e).__name__, str(e)[:180])
            if attempt == 3: break
            time.sleep(1 + attempt * 2)
    return None, 4, last

def parse_record(kind, item):
    if kind == "15m":
        return (int(item[0]),) + tuple(str(x) for x in item[1:7])
    if kind == "funding":
        return int(item["fundingRateTimestamp"]), str(item["fundingRate"])
    return int(item["timestamp"]), str(item["openInterest"])

def numerically_valid(values):
    try:
        return all(Decimal(x).is_finite() for x in values)
    except (InvalidOperation, ValueError):
        return False

def endpoint(kind): return API + SPECS[kind]["resource"]

def canonical_path(symbol, kind):
    return ROOT / "bybit" / "linear" / symbol / (symbol + SPECS[kind]["file"])

def existing_provenance():
    result = {}
    with open(PROVENANCE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f): result[(r["symbol"], r["source_kind"])] = r
    return result

def read_base(path, kind, expected_sha):
    if not path.exists() or sha(path) != expected_sha: return [], "MISSING_OR_HASH_MISMATCH"
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        if tuple(next(reader, [])) != SPECS[kind]["header"]: return [], "INVALID_SCHEMA"
        for r in reader:
            try: rows.append((int(datetime.strptime(r[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()*1000),) + tuple(r[1:]))
            except (ValueError, IndexError): return [], "INVALID_ROW"
    return rows, "BYTE_VALIDATED"

def validate(symbol, kind):
    spec, path = SPECS[kind], canonical_path(symbol, kind)
    d = {"symbol": symbol, "source_kind": kind, "official_endpoint": endpoint(kind), "canonical_path": str(path), "canonical_sha256": "", "schema": "|".join(spec["header"]), "requested_first": iso(START), "requested_last": iso(END-spec["step"]), "actual_first": "", "actual_last": "", "row_count_2025": 0, "expected_row_count": spec["expected"], "duplicate_count": 0, "conflicting_duplicate_count": 0, "gap_count": 0, "off_grid_count": 0, "invalid_numeric_count": 0, "source_status": "MISSING", "reason": "canonical file absent"}
    gaps = []
    if not path.exists(): return d, gaps
    d["canonical_sha256"] = sha(path)
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f); header = tuple(next(reader, [])); raw = list(reader)
        if header != spec["header"]: d.update(source_status="INVALID", reason="incompatible schema"); return d, gaps
        vals, seen = {}, {}
        for r in raw:
            try: ms = int(datetime.strptime(r[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()*1000)
            except (ValueError, IndexError): d["invalid_numeric_count"] += 1; continue
            if START <= ms < END:
                values = tuple(r[1:])
                if len(values) != len(header)-1 or not numerically_valid(values): d["invalid_numeric_count"] += 1
                if ms in seen:
                    d["duplicate_count"] += 1
                    if seen[ms] != values: d["conflicting_duplicate_count"] += 1; gaps.append((symbol, kind, iso(ms), "CONFLICTING_DUPLICATE"))
                else: seen[ms] = values
                if (ms-START) % spec["step"]: d["off_grid_count"] += 1
        expected = set(range(START, END, spec["step"]))
        actual = set(seen)
        for ms in sorted(expected-actual): gaps.append((symbol, kind, iso(ms), "MISSING_EXPECTED_TIMESTAMP"))
        d["gap_count"] = len(expected-actual)
        ordered = sorted(actual & expected)
        d["row_count_2025"] = len(ordered)
        if ordered: d["actual_first"], d["actual_last"] = iso(ordered[0]), iso(ordered[-1])
        if (d["row_count_2025"] == spec["expected"] and not d["duplicate_count"] and not d["conflicting_duplicate_count"] and not d["gap_count"] and not d["off_grid_count"] and not d["invalid_numeric_count"]): d.update(source_status="READY", reason="all frozen checks passed")
        else: d.update(source_status="PARTIAL", reason="row/grid/duplicate/numeric validation failed")
    except (OSError, csv.Error) as e: d.update(source_status="INVALID", reason="read error: %s" % str(e)[:120])
    return d, gaps

def csv_bytes(header, rows):
    # newline is fixed for reproducible hashes on all hosts.
    import io
    s = io.StringIO(newline="")
    w = csv.writer(s, lineterminator="\n"); w.writerow(header)
    for row in rows: w.writerow((iso(row[0]),) + tuple(row[1:]))
    return s.getvalue().encode("utf-8")

def main():
    provenance = existing_provenance()
    requests, states = [], {}
    # Phase 1: local preflight and bounded official start/end probes; no bulk yet.
    for symbol in SYMBOLS:
        for kind, spec in SPECS.items():
            p = provenance[(symbol, kind)]
            base, local = read_base(Path(p["source_file"]), kind, p["sha256"])
            start_list, start_n, start_status = request(kind, symbol, START, min(END, START + spec["step"] * min(spec["limit"], 2)))
            end_list, end_n, end_status = request(kind, symbol, max(START, END - spec["step"] * min(spec["limit"], 2)), END)
            available = start_list is not None and end_list is not None and bool(start_list) and bool(end_list)
            states[(symbol,kind)] = {"base": base, "local": local, "available": available, "requests": start_n+end_n, "records": (len(start_list) if start_list else 0)+(len(end_list) if end_list else 0), "start": start_status, "end": end_status}
    # Phase 2: deterministic bounded retrieval only where both probes found records.
    for symbol in SYMBOLS:
        for kind, spec in SPECS.items():
            st = states[(symbol,kind)]; bulk = "NO"
            records = {}; final = "NOT_RUN"
            if st["available"]:
                bulk = "YES"; ok = True
                for lo in range(START, END, spec["step"] * spec["limit"]):
                    hi = min(END, lo + spec["step"] * spec["limit"])
                    data, n, status = request(kind, symbol, lo, hi); st["requests"] += n
                    if data is None: ok = False; final = status; break
                    for item in data:
                        row = parse_record(kind, item); ms = row[0]
                        if lo <= ms < hi:
                            if ms in records and records[ms] != row: ok = False; final = "CONFLICTING_API_DUPLICATE"; break
                            records[ms] = row
                    st["records"] += len(data)
                    if not ok: break
                if ok:
                    merged = {r[0]: r for r in st["base"]}; merged.update(records)
                    rows = [merged[k] for k in sorted(merged)]
                    path = canonical_path(symbol, kind)
                    # Validate replacement before it can replace a valid archive.
                    data = csv_bytes(spec["header"], rows)
                    temp = path.with_suffix(path.suffix + ".candidate")
                    atomic_bytes(temp, data)
                    try:
                        # Candidate must at least contain the complete requested grid.
                        expected = set(range(START, END, spec["step"]))
                        parsed_candidate = list(csv.reader(data.decode().splitlines()))
                        got = {int(datetime.strptime(r[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()*1000) for r in parsed_candidate[1:]}
                        if not expected.issubset(got): raise RuntimeError("candidate missing expected timestamps")
                        os.replace(temp, path); final = "SUCCESS"
                        meta = {"endpoint": endpoint(kind), "frozen_request_parameters": dict(spec["params"], symbol=symbol), "schema": list(spec["header"]), "row_count": len(rows), "first_timestamp": iso(rows[0][0]), "last_timestamp": iso(rows[-1][0]), "gap_count_2025": len(expected-set(records)), "sha256": sha(path)}
                        atomic_bytes(path.with_suffix(path.suffix + ".meta.json"), (json.dumps(meta, sort_keys=True, separators=(",", ":")) + "\n").encode())
                    finally:
                        if temp.exists(): temp.unlink()
            else: final = "PROBE_UNAVAILABLE"
            requests.append({"symbol":symbol,"source_kind":kind,"local_preflight_status":st["local"],"begin_probe_status":st["start"],"end_probe_status":st["end"],"bulk_acquisition_ran":bulk,"request_count":st["requests"],"records_received":st["records"],"final_endpoint_status":final})
    manifests, gaps = [], []
    for symbol in SYMBOLS:
        for kind in SPECS:
            row, g = validate(symbol, kind); manifests.append(row); gaps.extend(g)
    def write_repo(name, header, rows):
        import io
        s = io.StringIO(newline=""); w = csv.DictWriter(s, fieldnames=header, lineterminator="\n"); w.writeheader(); w.writerows(rows); atomic_bytes(OUT/name, s.getvalue().encode())
    manifest_header = list(manifests[0])
    write_repo("readiness_manifest.csv", manifest_header, manifests)
    atomic_bytes(OUT/"gaps.csv", csv_bytes(("symbol","source_kind","timestamp_utc","issue"), [(0,)+x for x in []]))
    # csv_bytes is timestamp-specific; write the gaps header/records directly.
    import io
    gs=io.StringIO(newline=""); gw=csv.writer(gs,lineterminator="\n"); gw.writerow(("symbol","source_kind","timestamp_utc","issue")); gw.writerows(gaps); atomic_bytes(OUT/"gaps.csv",gs.getvalue().encode())
    write_repo("request_summary.csv", list(requests[0]), requests)
    ready = sum(x["source_status"] == "READY" for x in manifests)
    failures = ["%s %s: %s (%s)" % (x["symbol"],x["source_kind"],x["source_status"],x["reason"]) for x in manifests if x["source_status"] != "READY"]
    report = "# DATA-001 Bybit 2025 readiness\n\nOverall status: %s\n\nDATA_READY=%s\n\nFrozen panel: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT; Bybit V5 linear; 2025-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z.\n\nREADY sources: %d/12.\n\n## Failures\n\n%s\n\nThe manifest independently validates the 2025 slice; gaps.csv lists every missing expected timestamp and conflicting duplicate. request_summary.csv records the mandatory preflight probes and acquisition outcomes.\n" % ("READY" if ready == 12 else "NOT_READY", "YES" if ready == 12 else "NO", ready, "\n".join("- "+x for x in failures) if failures else "- None")
    atomic_bytes(OUT/"REPORT.md", report.encode())
    hash_rows=[]
    for p in (OUT/"REPORT.md",OUT/"readiness_manifest.csv",OUT/"gaps.csv",OUT/"request_summary.csv",OUT/"data_001.py"):
        hash_rows.append({"path":str(p.relative_to(OUT.parents[2])),"sha256":sha(p)})
    for symbol in SYMBOLS:
        for kind in SPECS:
            p=canonical_path(symbol,kind); hash_rows.append({"path":str(p),"sha256":sha(p) if p.exists() else "MISSING"})
    write_repo("run_hashes.csv", ["path","sha256"], hash_rows)
    print("DATA_READY=%s" % ("YES" if ready == 12 else "NO"))

if __name__ == "__main__": main()
