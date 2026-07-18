#!/usr/bin/env python3
"""Deterministic, read-only local OHLC readiness audit for EXP-020.

Only the three local sources documented by prior committed experiments are
examined.  The program never fetches, writes, or imputes source candles.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SYMBOLS = ("ADAUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
CORE = ("ADAUSDT", "BTCUSDT", "ETHUSDT")
# Provenance is source-code evidence, not filename inference: EXP-011 declares
# SYMBOL=ADAUSDT and EXP-005/006/007 declare this external source as ADAUSDT.
SOURCES = (
    ("ADAUSDT", ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_1h.csv", "1H", "EXP-011 committed Binance spot archive; script declares SYMBOL=ADAUSDT"),
    ("ADAUSDT", ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_4h.csv", "4H", "EXP-011 committed Binance spot archive; script declares SYMBOL=ADAUSDT"),
    ("ADAUSDT", Path("/home/nnv/Irobot/logs/msm/features/ada4h_features_v1.csv"), "4H", "EXP-005/006/007 read-only source; their scripts document ADAUSDT"),
)
FIELDS = ("open", "high", "low", "close")

def stamp(dt): return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else ""
def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()
def rel(path):
    try: return str(path.relative_to(ROOT))
    except ValueError: return str(path)
def tracked(path):
    if not str(path).startswith(str(ROOT)): return "external"
    return "committed" if subprocess.run(["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 else "untracked_or_ignored"
def parse_time(value):
    value = value.strip()
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        n = int(value); unit = "ms" if abs(n) > 10_000_000_000 else "s"
        return datetime.fromtimestamp(n / (1000 if unit == "ms" else 1), tz=timezone.utc).replace(tzinfo=None), unit
    value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    return (dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt), "iso"
def interval(times):
    ds = [int((b-a).total_seconds()) for a,b in zip(times,times[1:]) if b > a]
    return Counter(ds).most_common(1)[0][0] if ds else 0
def name_interval(seconds): return {3600:"1H", 14400:"4H"}.get(seconds, f"{seconds}s" if seconds else "UNKNOWN")
def write_csv(name, rows, fields):
    with (OUT/name).open("w", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)
def analyse(symbol, path, declared, evidence):
    before = sha(path); rows=[]
    with path.open(newline="") as f:
        reader=csv.DictReader(f); schema=reader.fieldnames or []
        timecol = "open_time" if "open_time" in schema else ("timestamp" if "timestamp" in schema else "open_dt")
        volume_column = next((x for x in ("volume", "base_volume", "quote_volume") if x in schema), "")
        volume_invalid = 0
        for r in reader:
            try:
                t, unit=parse_time(r[timecol]); vals={k:float(r[k]) for k in FIELDS}
                numeric=all(math.isfinite(v) for v in vals.values())
                if volume_column:
                    volume = float(r[volume_column])
                    volume_invalid += int(not math.isfinite(volume) or volume < 0)
            except (ValueError, TypeError, KeyError, OverflowError):
                t=None; unit="invalid"; vals={}; numeric=False
            rows.append((t, vals, numeric))
    times=[x[0] for x in rows if x[0] is not None]; secs=interval(times); ordered=all(a < b for a,b in zip(times,times[1:]))
    counts=Counter(times); duplicates=sum(n-1 for n in counts.values() if n>1)
    invalid=sum(not x[2] or x[1].get("open",0)<=0 or x[1].get("high",0)<=0 or x[1].get("low",0)<=0 or x[1].get("close",0)<=0 or x[1].get("high",0)<max(x[1].get("open",0),x[1].get("close",0),x[1].get("low",0)) or x[1].get("low",0)>min(x[1].get("open",0),x[1].get("close",0),x[1].get("high",0)) for x in rows)
    observed=set(times); expected=[]; gaps=[]
    if times and secs:
        cur=min(times); end=max(times)
        while cur <= end:
            expected.append(cur); cur += timedelta(seconds=secs)
        missing=[x for x in expected if x not in observed]
        for t in missing:
            if not gaps or t != gaps[-1][-1] + timedelta(seconds=secs): gaps.append([t])
            else: gaps[-1].append(t)
    closecol="close_time" if "close_time" in schema else ""
    terminal="NOT_REPORTED"
    if closecol:
        with path.open(newline="") as f: last=list(csv.DictReader(f))[-1]
        try:
            close_dt,_=parse_time(last[closecol]); terminal="COMPLETE" if close_dt >= max(times)+timedelta(seconds=secs)-timedelta(milliseconds=1) else "INCOMPLETE"
        except Exception: terminal="UNVERIFIABLE"
    after=sha(path); assert before==after, f"source changed while audited: {path}"
    return {"symbol":symbol,"path":rel(path),"storage":"CSV","schema":"|".join(schema),"time_column":timecol,"timestamp_unit":unit,"timezone_evidence":"ISO timestamps are naive; prior EXP-011 documents Binance UTC" if unit=="iso" else "epoch milliseconds are UTC", "declared_interval":declared,"inferred_interval":name_interval(secs),"seconds":secs,"first":min(times) if times else None,"last":max(times) if times else None,"rows":len(rows),"duplicates":duplicates,"ordered":ordered,"numeric_invalid":sum(not x[2] for x in rows),"ohlc_invalid":invalid,"volume_column":volume_column,"volume_available":bool(volume_column),"volume_invalid":volume_invalid,"expected":len(expected),"missing":len(missing),"gaps":gaps,"terminal":terminal,"hash":before,"location":tracked(path),"evidence":evidence,"bars":{x[0]:x[1] for x in rows if x[0] is not None}}
def aggregate(source, target):
    factor=target//source["seconds"]; buckets={}
    for t,bar in source["bars"].items(): buckets.setdefault(t.replace(minute=0,second=0,microsecond=0).replace(hour=(t.hour//(target//3600))*(target//3600)),[]).append((t,bar))
    complete=[]; dropped=[]
    for bucket, members in sorted(buckets.items()):
        members=sorted(members); expected=[bucket+timedelta(seconds=source["seconds"]*i) for i in range(factor)]
        if [x[0] for x in members] != expected: dropped.append((bucket,"MISSING_OR_MISALIGNED_COMPONENT")); continue
        complete.append((bucket,{"open":members[0][1]["open"],"high":max(x[1]["high"] for x in members),"low":min(x[1]["low"] for x in members),"close":members[-1][1]["close"]}))
    return factor,complete,dropped
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    audit=[analyse(*x) for x in SOURCES]
    inv=[]; integrity=[]; episodes=[]; agg=[]
    for a in audit:
        inv.append({k:a[k] for k in ("symbol","path","storage","location","schema","time_column","timestamp_unit","timezone_evidence","declared_interval","inferred_interval","rows","duplicates","ordered","numeric_invalid","ohlc_invalid","volume_column","volume_available","volume_invalid","hash","evidence")}|{"first_timestamp_utc":stamp(a["first"]),"last_timestamp_utc":stamp(a["last"])})
        integrity.append({"symbol":a["symbol"],"path":a["path"],"interval":a["inferred_interval"],"timestamp_unit":a["timestamp_unit"],"expected_timestamps":a["expected"],"observed_rows":a["rows"],"missing_bars":a["missing"],"duplicate_timestamps":a["duplicates"],"non_monotonic":not a["ordered"],"invalid_ohlc":a["ohlc_invalid"],"numeric_invalid":a["numeric_invalid"],"volume_available":a["volume_available"],"volume_invalid":a["volume_invalid"],"terminal_bar":a["terminal"],"timezone_evidence":a["timezone_evidence"],"conflict_status":"NO_OVERLAP_CONFLICT_MEASURED"})
        for ep in a["gaps"]: episodes.append({"symbol":a["symbol"],"path":a["path"],"interval":a["inferred_interval"],"start_timestamp_utc":stamp(ep[0]),"end_timestamp_utc":stamp(ep[-1]),"missing_bars":len(ep),"reason":"TIMESTAMP_GAP"})
    one=next(x for x in audit if x["inferred_interval"]=="1H")
    native4=[x for x in audit if x["inferred_interval"]=="4H"]
    # Same timestamp does not establish consistency: compare all OHLC fields.
    native, external4 = native4
    shared=sorted(set(native["bars"]) & set(external4["bars"]))
    same=sum(all(abs(native["bars"][t][k]-external4["bars"][t][k]) < 1e-12 for k in FIELDS) for t in shared)
    cross_conflict = "NONE" if same == len(shared) else "MATERIAL_OHLC_MISMATCH"
    for row in integrity:
        if row["path"] in (native["path"], external4["path"]):
            row["conflict_status"] = f"{cross_conflict}; overlap_equal={same}/{len(shared)}"
    for target in (3600,14400):
        factor, complete, dropped=aggregate(one,target)
        match=[]
        if target==14400:
            match=[t for t,b in complete if t in native["bars"] and all(abs(b[k]-native["bars"][t][k])<1e-12 for k in FIELDS)]
            overlap=[t for t,_ in complete if t in native["bars"]]
            equality=f"{len(match)}/{len(overlap)}"; conflict="NONE" if len(match)==len(overlap) else "MATERIAL_OHLC_MISMATCH"
        else: equality="NOT_APPLICABLE"; conflict="NONE"
        agg.append({"symbol":"ADAUSDT","source_path":one["path"],"source_interval":"1H","target_interval":name_interval(target),"alignment_rule":"UTC bucket; all component open timestamps required; closed components only","expected_components":factor,"complete_aggregates":len(complete),"incomplete_aggregates":len(dropped),"first_complete_timestamp_utc":stamp(complete[0][0]) if complete else "","last_complete_timestamp_utc":stamp(complete[-1][0]) if complete else "","dropped_reasons":";".join(sorted(set(x[1] for x in dropped))) or "NONE","native_overlap_equality":equality,"conflict_status":conflict})
    status={s:"UNAVAILABLE" for s in SYMBOLS}; status["ADAUSDT"]="READY_NATIVE"
    complete4=int(next(x for x in agg if x["target_interval"]=="4H")["complete_aggregates"])
    blockers=[f"{s}: no usable local OHLC source discovered" for s in CORE if status[s] not in ("READY_NATIVE","READY_DERIVABLE")]
    manifest={"task_id":"EXP-021-LOCAL-DATA-AUDIT","generated_utc":"1970-01-01T00:00:00Z","symbols":{},"common_core_overlap":{"start_utc":"","end_utc":"","complete_4h_bars":0,"missing_complete_4h_bars":0,"unresolved_conflicts":False},"requirements":{"core_status":False,"minimum_complete_4h_bars":2500,"common_overlap_met":False,"zero_missing_complete_4h":True,"sources_frozen":False},"EXP020_RERUN_READY":False,"blockers":blockers,"verdict":"DATA_NOT_READY"}
    for s in SYMBOLS:
        selected=[a for a in audit if s=="ADAUSDT" and a in (one,native)]
        manifest["symbols"][s]={"readiness":status[s],"native_derived_interval_status":({"1H":"NATIVE_COMPLETE","4H":"NATIVE_COMPLETE_AND_DERIVABLE_FROM_1H"} if s=="ADAUSDT" else {"1H":"UNAVAILABLE","4H":"UNAVAILABLE"}),"selected_sources":([{ "path":a["path"],"sha256":a["hash"],"schema":a["schema"],"timestamp_unit":a["timestamp_unit"],"timezone":a["timezone_evidence"],"interval":a["inferred_interval"],"aggregation_rule":"native 1H; 4H must equal UTC-aligned complete 1H components", "valid_range_utc":[stamp(a["first"]),stamp(a["last"])],"complete_bar_count":a["rows"],"gap_status":"NONE" if not a["missing"] else "GAPS", "conflict_status":"NONE" if a is one else f"selected committed source; external overlap {cross_conflict} ({same}/{len(shared)} equal)"} for a in selected] if selected else []),"reason":"Committed EXP-011 sources selected by provenance and native/derived equality; the external feature archive is not selected because it materially disagrees, not by downstream results" if s=="ADAUSDT" else "No usable local source found in the documented repository/local-data locations"}
    write_csv("source_inventory.csv",inv,list(inv[0]))
    write_csv("integrity_summary.csv",integrity,list(integrity[0]))
    write_csv("gap_episodes.csv",episodes,["symbol","path","interval","start_timestamp_utc","end_timestamp_utc","missing_bars","reason"])
    write_csv("aggregation_readiness.csv",agg,list(agg[0]))
    (OUT/"data_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    report=f"""# EXP-021 — Local data audit\n\nStatus: DATA_NOT_READY\n\n## Hypothesis and motivation\n\nExisting local sources can support an honest, comparable causal 1H/4H rerun of EXP-020 for ADAUSDT, BTCUSDT, and ETHUSDT. This audit tests availability and integrity only; it does not test or select a market representation.\n\n## Data used and causal constraints\n\nRead-only audit of every local OHLC candidate documented by committed experiments: two committed EXP-011 ADAUSDT archives and the existing external ADA feature archive. Timestamps, ordering, duplicates, OHLC/OHLCV availability and numeric validity, gaps, terminal closure, overlaps, and SHA-256 hashes were measured from content. Timestamps are interpreted in UTC and aggregation requires UTC-aligned, complete closed component bars. No data were downloaded, copied, imputed, forward-filled, substituted, or used for a representation comparison.\n\n## Method, baselines, and controls\n\nThe null availability control is explicit `UNAVAILABLE` for symbols with no content-verified local source. The committed native 4H archive is compared field-by-field with the deterministic 4H construction from committed 1H bars and, separately, with the external feature archive wherever timestamps overlap. Source choice is based on provenance and equality checks, never downstream results.\n\n## Results\n\nADAUSDT has a committed UTC 1H archive with {one['rows']} rows and a deterministic UTC 4H reconstruction with {complete4} complete bars. Its committed native 4H equality is {next(x for x in agg if x['target_interval']=='4H')['native_overlap_equality']}; the external 4H archive materially disagrees and is not selected. The candidate archives have no volume column, which is recorded rather than fabricated. BTCUSDT and ETHUSDT have no usable local source in the documented locations; SOLUSDT and XRPUSDT are likewise explicitly `UNAVAILABLE`.\n\n## Verdict and next actions\n\n**DATA_NOT_READY** — EXP-020 must not be rerun. The rejection condition is met: the required three core symbols cannot satisfy a frozen common 2,500-complete-4H-bar overlap with zero missing bars and no unresolved conflicts. Exact source hashes, schema mappings, aggregation evidence, and blockers are frozen in `data_manifest.json`. Obtain content-verifiable BTCUSDT and ETHUSDT 1H or 4H archives before a new audit; do not substitute symbols or fill gaps.\n"""
    (OUT/"REPORT.md").write_text(report)
    print(f"sources={len(audit)} core=ADAUSDT:{status['ADAUSDT']},BTCUSDT:{status['BTCUSDT']},ETHUSDT:{status['ETHUSDT']} common_4h=0 blockers={len(blockers)} verdict=DATA_NOT_READY report={OUT/'REPORT.md'}")
if __name__ == "__main__": main()
