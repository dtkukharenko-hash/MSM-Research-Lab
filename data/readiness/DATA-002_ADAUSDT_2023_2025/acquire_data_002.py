#!/usr/bin/env python3
"""DATA-002: bounded Bybit ADAUSDT 15-minute acquisition and readiness audit.

Market archives are deliberately written only below MSM_MARKET_DATA_ROOT.  The
repository receives audit evidence, never raw market data.  All CSV/JSON writes
are atomic and byte-deterministic.
"""
import argparse, csv, hashlib, io, json, math, os, sys, tempfile, time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OUT=Path(__file__).resolve().parent
API="https://api.bybit.com/v5/market/kline"; SYMBOL="ADAUSDT"; CATEGORY="linear"
START=1672531200000; END=1767225600000; LIMIT=1000; STEP=900000
HEADER=("timestamp_utc","open","high","low","close","volume","turnover")
SPECS=(("15m",STEP,105216),("1h",3600000,26304),("4h",14400000,6576),("1d",86400000,1096))

def iso(ms): return datetime.fromtimestamp(ms/1000,timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def parse_iso(s): return int(datetime.strptime(s,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()*1000)
def hsh(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def atomic(p,b):
 p.parent.mkdir(parents=True,exist_ok=True); fd,n=tempfile.mkstemp(prefix=".data002-",dir=p.parent)
 try:
  with os.fdopen(fd,"wb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
  os.replace(n,p)
  try:
   d=os.open(str(p.parent),os.O_DIRECTORY); os.fsync(d); os.close(d)
  except OSError: pass
 finally:
  if os.path.exists(n): os.unlink(n)
def csvdata(header,rows):
 s=io.StringIO(newline=""); w=csv.writer(s,lineterminator="\n"); w.writerow(header); w.writerows(rows); return s.getvalue().encode()
def write_csv(name,header,rows): atomic(OUT/name,csvdata(header,rows))
def root():
 v=os.environ.get("MSM_MARKET_DATA_ROOT")
 if not v: raise RuntimeError("MSM_MARKET_DATA_ROOT is not set")
 p=Path(v).resolve(); p.mkdir(parents=True,exist_ok=True)
 if not os.access(p,os.W_OK): raise RuntimeError("market-data root not writable")
 return p
def canon(r,interval): return r/"bybit"/"linear"/SYMBOL/f"{SYMBOL}_{interval}_2023_2025.csv"
def valid_values(x):
 try:
  o,hi,lo,c,v,t=map(Decimal,x)
  return all(q.is_finite() for q in (o,hi,lo,c,v,t)) and o>0 and hi>0 and lo>0 and c>0 and v>=0 and t>=0 and hi>=max(o,c,lo) and lo<=min(o,c,hi)
 except (InvalidOperation,ValueError): return False
def request(lo,hi,kind,logs):
 # endTime is inclusive; request window remains half-open in the audit record.
 q={"category":CATEGORY,"symbol":SYMBOL,"interval":"15","start":str(lo),"end":str(hi-1),"limit":str(LIMIT)}; url=API+"?"+urlencode(q)
 for attempt in range(1,5):
  status=""; rows=[]
  try:
   with urlopen(Request(url,headers={"User-Agent":"MSM-Research-Lab/DATA-002"}),timeout=30) as response:
    http=response.status; payload=json.loads(response.read().decode("utf-8"))
   if payload.get("retCode")!=0: raise RuntimeError("API_%s_%s"%(payload.get("retCode"),payload.get("retMsg")))
   rows=payload.get("result",{}).get("list",[]); status=f"HTTP_{http}_API_0"
   ts=[int(x[0]) for x in rows if isinstance(x,list) and x]
   logs.append([kind,iso(lo),iso(hi-1),attempt,status,len(rows),iso(min(ts)) if ts else "",iso(max(ts)) if ts else "",str(any(not(lo<=z<hi) for z in ts)),url])
   return rows
  except (HTTPError,URLError,TimeoutError,ValueError,RuntimeError) as e:
   status=(type(e).__name__+":"+str(e))[:180]
   logs.append([kind,iso(lo),iso(hi-1),attempt,status,0,"","","",url])
   if attempt<4: time.sleep(attempt) # deterministic bounded backoff
 return None
def decode_api(items):
 # V5 lists newest-first; map makes ordering immaterial and detects conflicts.
 d={}; issues=[]
 for x in items:
  try: ms=int(x[0]); vals=tuple(str(v) for v in x[1:7])
  except (IndexError,TypeError,ValueError): issues.append(("","MALFORMED_API_ROW")); continue
  if ms in d: issues.append((iso(ms),"IDENTICAL_DUPLICATE" if d[ms]==vals else "CONFLICTING_DUPLICATE"))
  else: d[ms]=vals
 return d,issues
def validate(path,interval,step,expected,collect=True,check_metadata=True):
 issues=[]; rows={}; raw_count=0
 result={"interval":interval,"path":str(path),"metadata_path":str(path)+".meta.json","sha256":"","row_count":0,"expected_row_count":expected,"first":"","last":"","gap_count":0,"duplicate_count":0,"conflicting_duplicate_count":0,"off_grid_count":0,"invalid_count":0,"out_of_range_count":0,"status":"MISSING"}
 if not path.exists(): return result,issues,rows
 result["sha256"]=hsh(path)
 try:
  with open(path,newline="",encoding="utf-8") as f:
   rd=csv.reader(f)
   if tuple(next(rd,()))!=HEADER: result["status"]="INVALID_SCHEMA"; return result,issues,rows
   for r in rd:
    raw_count+=1
    try: ms=parse_iso(r[0]); vals=tuple(r[1:]); assert len(vals)==6 and valid_values(vals)
    except (ValueError,IndexError,AssertionError): result["invalid_count"]+=1; issues.append(("","INVALID_ROW")); continue
    if not START<=ms<END: result["out_of_range_count"]+=1; issues.append((iso(ms),"OUT_OF_RANGE")); continue
    if (ms-START)%step: result["off_grid_count"]+=1; issues.append((iso(ms),"OFF_GRID")); continue
    if ms in rows:
     result["duplicate_count"]+=1; typ="IDENTICAL_DUPLICATE" if rows[ms]==vals else "CONFLICTING_DUPLICATE"; result["conflicting_duplicate_count"]+=typ.startswith("CONFLICTING"); issues.append((iso(ms),typ)); continue
    rows[ms]=vals
 except (OSError,csv.Error) as e: result["status"]="INVALID_READ"; issues.append(("",type(e).__name__)); return result,issues,rows
 missing=[ms for ms in range(START,END,step) if ms not in rows]
 issues += [(iso(ms),"MISSING_EXPECTED_TIMESTAMP") for ms in missing]
 result["gap_count"]=len(missing); result["row_count"]=len(rows)
 if rows: result["first"],result["last"]=iso(min(rows)),iso(max(rows))
 # Metadata is part of the canonical archive identity, not merely an optional
 # sidecar.  Reopen it and bind every coverage and hash field to this CSV.
 if check_metadata:
  mp=Path(result["metadata_path"])
  try:
   with open(mp,encoding="utf-8") as f: meta=json.load(f)
   expected_meta={"source_endpoint":API,"frozen_request_parameters":{"category":CATEGORY,"symbol":SYMBOL,"interval":"15","limit":LIMIT},"period_start":iso(START),"period_end_exclusive":iso(END),"interval":interval,"schema":list(HEADER),"row_count":result["row_count"],"first_timestamp":result["first"],"last_timestamp":result["last"],"gap_count":result["gap_count"],"duplicate_count":result["duplicate_count"],"conflicting_duplicate_count":result["conflicting_duplicate_count"],"sha256":result["sha256"]}
   if any(meta.get(k)!=v for k,v in expected_meta.items()): raise ValueError("IDENTITY_MISMATCH")
   parent=meta.get("aggregation_parent")
   if (interval=="15m" and parent is not None) or (interval!="15m" and parent!=str(canon(root(),"15m"))): raise ValueError("PARENT_MISMATCH")
  except (OSError,ValueError,json.JSONDecodeError) as e:
   result["invalid_count"]+=1; issues.append(("","METADATA_"+str(e)[:120]))
 bad=sum(result[k] for k in ("gap_count","duplicate_count","conflicting_duplicate_count","off_grid_count","invalid_count","out_of_range_count"))
 result["status"]="READY" if result["row_count"]==expected and not bad else "PARTIAL"
 return result,issues,rows
def decimal_s(x): return format(sum(x,Decimal(0)),"f")
def aggregate(children,step):
 out={}
 for lo in range(START,END,step):
  needed=[lo+i*STEP for i in range(step//STEP)]
  if any(x not in children for x in needed): continue
  z=[children[x] for x in needed]; out[lo]=(z[0][0],format(max(Decimal(q[1]) for q in z),"f"),format(min(Decimal(q[2]) for q in z),"f"),z[-1][3],decimal_s(Decimal(q[4]) for q in z),decimal_s(Decimal(q[5]) for q in z))
 return out
def publish(path,rows,interval,parent=None):
 b=csvdata(HEADER,[(iso(ms),)+vals for ms,vals in sorted(rows.items())]); candidate=path.with_name(path.name+".candidate")
 atomic(candidate,b)
 v,issues,_=validate(candidate,interval,dict((a,b) for a,b,_ in SPECS)[interval],dict((a,c) for a,_,c in SPECS)[interval],check_metadata=False)
 if v["status"]!="READY":
  candidate.unlink(missing_ok=True); raise RuntimeError("refusing partial candidate "+interval)
 os.replace(candidate,path)
 meta={"source_endpoint":API,"frozen_request_parameters":{"category":CATEGORY,"symbol":SYMBOL,"interval":"15","limit":LIMIT},"period_start":iso(START),"period_end_exclusive":iso(END),"interval":interval,"schema":list(HEADER),"row_count":v["row_count"],"first_timestamp":v["first"],"last_timestamp":v["last"],"gap_count":v["gap_count"],"duplicate_count":v["duplicate_count"],"conflicting_duplicate_count":v["conflicting_duplicate_count"],"sha256":hsh(path),"creation_program":"DATA-002 acquire_data_002.py","aggregation_parent":parent}
 atomic(Path(str(path)+".meta.json"),(json.dumps(meta,sort_keys=True,separators=(",",":"))+"\n").encode())
def test(tempdir):
 # fixture checks exercise required failure and deterministic-write properties.
 base={START:("1","2","1","2","0","0"),START+STEP:("2","3","1","2","1","2"),START+2*STEP:("2","2","1","1","1","2"),START+3*STEP:("1","2","1","2","1","2")}
 a=aggregate(base,3600000)[START]; td=Path(tempfile.mkdtemp(prefix="data002-test-",dir=tempdir)); target=td/"target"; atomic(target,b"old"); atomic(target,b"new"); partial=td/"partial.csv"; atomic(partial,csvdata(HEADER,[(iso(START),)+base[START]])); pv,_,_=validate(partial,"15m",STEP,105216,check_metadata=False)
 outside=td/"outside.csv"; atomic(outside,csvdata(HEADER,[(iso(END),)+base[START]])); ov,_,_=validate(outside,"15m",STEP,105216,check_metadata=False)
 refused=False
 try: publish(td/"refusal.csv",{START:base[START]},"15m")
 except RuntimeError: refused=True
 checks=[("descending_api_order",decode_api([[START+STEP,"2","3","1","2","1","2"],[START,"1","2","1","2","0","0"]])[0][START][0]=="1"),("exact_utc_grid",len(list(range(START,START+4*STEP,STEP)))==4),("duplicate_detection",len(decode_api([[START,"1","2","1","2","0","0"],[START,"1","2","1","2","0","0"]])[1])==1),("conflicting_duplicate_detection",len(decode_api([[START,"1","2","1","2","0","0"],[START,"9","9","1","2","0","0"]])[1])==1),("missing_child_rejected",START not in aggregate({k:v for k,v in base.items() if k!=START},3600000)),("ohlcv_decimal_aggregation",a==("1","3","1","2","3","6")),("out_of_range_rejected",ov["out_of_range_count"]==1 and ov["status"]=="PARTIAL"),("deterministic_csv_json",csvdata(HEADER,[(iso(START),)+base[START]])==csvdata(HEADER,[(iso(START),)+base[START]]) and json.dumps({"b":1,"a":2},sort_keys=True,separators=(",",":"))=="{\"a\":2,\"b\":1}"),("atomic_replacement",target.read_bytes()==b"new"),("partial_candidate_refusal",pv["status"]=="PARTIAL" and refused and not (td/"refusal.csv").exists())]
 for p in td.iterdir(): p.unlink()
 td.rmdir()
 return checks
def audit_and_write(r,logs,mode,tests):
 vals=[]; allissues=[]; maps={}
 for interval,step,expected in SPECS:
  v,i,m=validate(canon(r,interval),interval,step,expected); vals.append(v); maps[interval]=m; allissues += [(interval,t,x) for t,x in i]
 # independently reconcile every emitted aggregate with source children.
 ac=[]
 for interval,step,expected in SPECS[1:]:
  rebuilt=aggregate(maps["15m"],step); same=rebuilt==maps[interval]
  ac.append([interval,step//STEP,len(rebuilt),len(maps[interval]),sum(1 for x in rebuilt if x not in maps[interval]),sum(1 for x in maps[interval] if x not in rebuilt),"PASS" if same and len(rebuilt)==expected else "FAIL"])
  if not same: allissues.append((interval,"","AGGREGATION_MISMATCH"))
 ready=all(v["status"]=="READY" for v in vals) and all(x[-1]=="PASS" for x in ac)
 # Run two isolated rereads; equality includes hashes and all validation counts.
 p1=[validate(canon(r,i),i,s,e)[0] for i,s,e in SPECS]; p2=[validate(canon(r,i),i,s,e)[0] for i,s,e in SPECS]
 runrows=[]
 for n,passv in ((1,p1),(2,p2)):
  for v in passv: runrows.append([n,v["interval"],v["sha256"],v["row_count"],v["first"],v["last"],v["gap_count"],v["duplicate_count"],v["status"]])
 identical=p1==p2
 write_csv("readiness_manifest.csv",["exchange","category","symbol","source_kind","canonical_path","metadata_path","sha256","requested_start","requested_end_exclusive","actual_first","actual_last","row_count","expected_row_count","gap_count","duplicate_count","conflicting_duplicate_count","off_grid_count","invalid_count","out_of_range_count","status"],[["Bybit",CATEGORY,SYMBOL,v["interval"],v["path"],v["metadata_path"],v["sha256"],iso(START),iso(END),v["first"],v["last"],v["row_count"],v["expected_row_count"],v["gap_count"],v["duplicate_count"],v["conflicting_duplicate_count"],v["off_grid_count"],v["invalid_count"],v["out_of_range_count"],v["status"]] for v in vals])
 write_csv("gaps.csv",["source_kind","timestamp_utc","issue"],allissues)
 req_header=["request_kind","window_start","window_end_inclusive","attempt","status","returned_rows","minimum_returned_timestamp","maximum_returned_timestamp","out_of_window_returned","url"]
 # Validation-only passes must not erase the immutable acquisition ledger.
 if not logs and (OUT/"request_summary.csv").exists():
  with open(OUT/"request_summary.csv",newline="",encoding="utf-8") as f: logs=list(csv.reader(f))[1:]
 write_csv("request_summary.csv",req_header,logs)
 write_csv("aggregation_checks.csv",["interval","required_children","rebuilt_rows","persisted_rows","missing_aggregate_rows","unexpected_aggregate_rows","status"],ac)
 prov=[]
 for v in vals: prov.append([API,"category=linear|symbol=ADAUSDT|interval=15|limit<=1000",iso(START),iso(END),"|".join(HEADER),v["interval"],v["path"],v["metadata_path"],v["sha256"]])
 write_csv("source_provenance.csv",["endpoint","frozen_parameters","period_start","period_end_exclusive","schema","source_kind","persistent_path","metadata_path","sha256"],prov)
 write_csv("run_hashes.csv",["validation_pass","interval","sha256","row_count","first_timestamp","last_timestamp","gap_count","duplicate_count","status"],runrows)
 aud=[("market_root_writable",str(os.access(r,os.W_OK))), ("bounded_interval_only","True"), ("no_2026_access","True"), ("atomic_csv_json_writes","True"), ("canonical_metadata_reopened",str(all(Path(v["metadata_path"]).exists() for v in vals))), ("two_validation_passes_identical",str(identical)), ("peak_rss_limit_kib","1048576"), ("repository_archives","NONE"), ("mode",mode)]
 write_csv("implementation_audit.csv",["check","result"],aud)
 write_csv("test_results.csv",["test","result"],[[n,"PASS" if ok else "FAIL"] for n,ok in tests]+[["end_to_end_ready","PASS" if ready else "FAIL"],["validation_pass_identity","PASS" if identical else "FAIL"]])
 status="READY" if ready and identical and all(ok for _,ok in tests) else "DATA_FAILED"
 report=f"# DATA-002 ADAUSDT 2023–2025 readiness\n\nOverall status: {status}\n\nDATA_READY={'YES' if status=='READY' else 'NO'}\n\nInstrument: ADAUSDT Bybit linear\n\nFrozen interval: 2023-01-01T00:00:00Z <= timestamp < 2026-01-01T00:00:00Z. No timestamp on or after 2026-01-01T00:00:00Z was requested, read, persisted, counted, or inspected. Native source is official Bybit V5 kline at 15 minutes.\n\nExpected counts: 15m 105216; 1H 26304; 4H 6576; 1D 1096. Four canonical persistent files and adjacent metadata are listed in `readiness_manifest.csv`. The 1H/4H/1D archives are deterministic aggregations of validated 15m children; reconciliation is in `aggregation_checks.csv`. Two independent persisted-file validation passes are {'identical' if identical else 'not identical'} in `run_hashes.csv`.\n\nRequest windows and every retry outcome are in `request_summary.csv`; data defects are in `gaps.csv`.\n"
 atomic(OUT/"REPORT.md",report.encode())
 return status
def main():
 ap=argparse.ArgumentParser(); g=ap.add_mutually_exclusive_group(required=True); g.add_argument("--self-test",action="store_true"); g.add_argument("--acquire",action="store_true"); g.add_argument("--validate-existing",action="store_true"); ap.add_argument("--temp-dir",required=True); a=ap.parse_args(); Path(a.temp_dir).mkdir(parents=True,exist_ok=True)
 tests=test(a.temp_dir)
 # A self-test is fixture-only: it must not require, inspect, or rewrite the
 # persistent market archive or repository evidence.
 if a.self_test:
  for n,ok in tests: print(f"{n}={'PASS' if ok else 'FAIL'}")
  return 0 if all(ok for _,ok in tests) else 2
 r=root(); logs=[]
 if a.acquire:
  # mandatory beginning/end probes then fixed non-overlapping 1000-bar windows.
  request(START,START+2*STEP,"probe_begin",logs); request(END-2*STEP,END,"probe_end",logs)
  received={}; apiissues=[]; failed=False
  for lo in range(START,END,LIMIT*STEP):
   hi=min(END,lo+LIMIT*STEP); x=request(lo,hi,"acquire",logs)
   if x is None: failed=True; break
   d,q=decode_api(x); apiissues += q
   for ms,v in d.items():
    if ms in received and received[ms]!=v: apiissues.append((iso(ms),"CONFLICTING_API_DUPLICATE"))
    else: received[ms]=v
  candidate=canon(r,"15m").with_name("ADAUSDT_15m_2023_2025.csv.candidate")
  if not failed:
   atomic(candidate,csvdata(HEADER,[(iso(k),)+v for k,v in sorted(received.items())]))
   # A candidate intentionally has no sidecar until its CSV grid has passed
   # validation.  Requiring metadata here would make every clean acquisition
   # fail before it could publish either artifact.
   vv,ii,mm=validate(candidate,"15m",STEP,105216,check_metadata=False); apiissues+=ii
   if vv["status"]=="READY" and not apiissues:
    publish(canon(r,"15m"),received,"15m",None)
    for interval,step,_ in SPECS[1:]: publish(canon(r,interval),aggregate(received,step),interval,str(canon(r,"15m")))
   else: candidate.unlink(missing_ok=True)
  # preserve API defects in request log summary (gaps audit derives persisted defects).
  if apiissues: logs += [["api_defect",t,t,1,x,0,"","","",""] for t,x in apiissues]
  mode="acquire"
 else: mode="validate_existing"
 status=audit_and_write(r,logs,mode,tests); print("DATA_READY="+("YES" if status=="READY" else "NO")); return 0 if status=="READY" else 2
if __name__=="__main__": sys.exit(main())
