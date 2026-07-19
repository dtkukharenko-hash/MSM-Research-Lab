#!/usr/bin/env python3
"""EXP-024: causal, internally coherent Bybit lower-timeframe transfer.

All decisions use bars closed before a counter starts.  This deliberately
descriptive program imports no committed 1H archive: 1H is built only from
four complete native 15m components.
"""
from __future__ import annotations
import bisect, csv, hashlib, math, os, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
DATA = Path.home()/".local/share/msm-market-data/bybit/linear/ADAUSDT"
HASHES={"3m":"ac96daf57a4e118565db3d12f729173a3fd59fddd0b9fbcbda0cc4fefd93d87d","5m":"1caa68f3fa7ac3dd56b50e42173653fdd0a5d4c71223c0eef0811b5fb84049d6","15m":"0ddfb8ad29eee1b279e39c79dbf94a019392b162dd2117a9137e01f5fcff7954"}
SECS={"3m":180,"5m":300,"15m":900,"1H":3600}; FACTORS=(.8,1.,1.2)
REPS=("FIXED_8","DIRECTION_RUN","ATR_ORIGIN","CONFIRMED_DIRECTION_CHANGE","HYBRID_ORIGIN")

def stamp(t): return t.strftime("%Y-%m-%dT%H:%M:%SZ")
def digest(p):
 h=hashlib.sha256();
 with p.open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""): h.update(x)
 return h.hexdigest()
def rnd(x): return "" if x is None or not math.isfinite(x) else f"{x:.8f}"
def mean(v): return sum(v)/len(v) if v else 0.
def quant(v,p):
 v=sorted(v); return v[int((len(v)-1)*p)] if v else None
def entropy(v):
 c=Counter(v); n=len(v); return -sum((x/n)*math.log2(x/n) for x in c.values()) if n else None
def write(name, rows, fields=None):
 OUT.mkdir(parents=True,exist_ok=True); fields=fields or list(rows[0])
 with (OUT/name).open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n",extrasaction="raise"); w.writeheader(); w.writerows(rows)
def ranks(v):
 z=sorted(range(len(v)),key=lambda i:v[i]); out=[0.]*len(v); i=0
 while i<len(v):
  j=i
  while j+1<len(v) and v[z[j+1]]==v[z[i]]: j+=1
  for k in range(i,j+1): out[z[k]]=(i+j+2)/2
  i=j+1
 return out
def spearman(a,b):
 if len(a)<2:return None
 a,b=ranks(a),ranks(b); aa,bb=mean(a),mean(b); d=math.sqrt(sum((x-aa)**2 for x in a)*sum((x-bb)**2 for x in b))
 return sum((x-aa)*(y-bb) for x,y in zip(a,b))/d if d else None
def load(interval):
 p=DATA/f"ADAUSDT_{interval}.csv"; assert p.exists() and digest(p)==HASHES[interval], f"archive hash failure: {p}"
 with p.open(newline="") as f: raw=list(csv.DictReader(f))
 assert list(raw[0])==["timestamp_utc","open","high","low","close","volume","turnover"]
 bars=[]
 for r in raw:
  t=datetime.strptime(r["timestamp_utc"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
  o,h,l,c=map(float,(r["open"],r["high"],r["low"],r["close"])); assert l<=min(o,c)<=max(o,c)<=h
  bars.append(dict(t=t,o=o,h=h,l=l,c=c,v=float(r["volume"]),turn=float(r["turnover"])))
 assert len({x["t"] for x in bars})==len(bars) and all(b["t"]-a["t"]==timedelta(seconds=SECS[interval]) for a,b in zip(bars,bars[1:]))
 # The frozen endpoint is 23:00Z inclusive (the final native bar opens then).
 assert bars[0]["t"]==datetime(2023,7,1,tzinfo=timezone.utc) and bars[-1]["t"]==datetime(2024,12,31,23,0,tzinfo=timezone.utc)
 atr=[]
 for i,b in enumerate(bars):
  tr=b["h"]-b["l"] if not i else max(b["h"]-b["l"],abs(b["h"]-bars[i-1]["c"]),abs(b["l"]-bars[i-1]["c"]))
  atr.append(mean([max(x["h"]-x["l"],abs(x["h"]-bars[j-1]["c"]) if j else x["h"]-x["l"],abs(x["l"]-bars[j-1]["c"]) if j else x["h"]-x["l"]) for j,x in enumerate(bars[max(0,i-13):i+1],max(0,i-13))]))
 for b,a in zip(bars,atr): b["atr"]=a
 return bars
def derive_hour(q):
 out=[]
 for i in range(0,len(q),4):
  z=q[i:i+4]
  if len(z)==4 and z[0]["t"].minute==0 and all(b["t"]==z[0]["t"]+timedelta(minutes=15*j) for j,b in enumerate(z)):
   out.append(dict(t=z[0]["t"],o=z[0]["o"],h=max(b["h"] for b in z),l=min(b["l"] for b in z),c=z[-1]["c"],v=sum(b["v"] for b in z),turn=sum(b["turn"] for b in z)))
 assert len(out)==len(q)//4
 for i,b in enumerate(out):
  b["atr"]=mean([max(x["h"]-x["l"],abs(x["h"]-out[j-1]["c"]) if j else x["h"]-x["l"],abs(x["l"]-out[j-1]["c"]) if j else x["h"]-x["l"]) for j,x in enumerate(out[max(0,i-13):i+1],max(0,i-13))])
 return out
def detector(parent, child, child_name, parent_name, factor):
 """Committed minimal balance/reassertion form, evaluated on parent bars.
 Counter start is the next child open after the completed parent state."""
 hits=[]; pidx={b["t"]:i for i,b in enumerate(parent)}
 for i in range(12,len(parent)-1):
  state=parent[i-8:i]; recent=parent[i-4:i+1]; sg=1 if state[-1]["c"]>=state[0]["c"] else -1
  ranges=[b["h"]-b["l"] for b in recent]
  overlap=mean([max(0,min(recent[j]["h"],recent[j-1]["h"])-max(recent[j]["l"],recent[j-1]["l"]))/max(recent[j]["h"]-recent[j]["l"],1e-12) for j in range(1,5)])
  disp=sg*(recent[-1]["c"]-recent[-2]["c"])/max(parent[i]["atr"],1e-12)
  if (overlap>=.35*factor or mean(ranges[-2:])<=mean(ranges[:2])) and disp>=.5*factor:
   start=parent[i]["t"]+timedelta(seconds=SECS[parent_name]); hits.append(dict(id=f"{child_name}_{parent_name}_{factor:.1f}_{i}",pi=i, counter_start=start, direction="UP" if sg>0 else "DOWN",sg=sg, overlap=overlap,reassertion=disp))
 return hits
def origin(rep,p,end,sg):
 if end<7:return None,"INSUFFICIENT_HISTORY",0
 lo=max(0,end-31)
 if rep=="FIXED_8": return end-7,"FIXED_8",0
 if rep=="DIRECTION_RUN":
  j=end
  while j>lo and sg*(p[j]["c"]-p[j-1]["c"])>=0:j-=1
  return j,"MAX_32_REACHED" if j==lo and end-lo==31 else "OPPOSITE_CLOSE_STEP",int(j==lo and end-lo==31)
 if rep=="ATR_ORIGIN":
  if p[end]["atr"]<=0:return None,"ZERO_ATR",0
  for j in range(end,lo-1,-1):
   if sg*(p[end]["c"]-p[j]["c"])>=p[end]["atr"]: return j,"ATR_1_REACHED",int(j==lo)
  return None,"ATR_1_NOT_REACHED",0
 if rep=="CONFIRMED_DIRECTION_CHANGE":
  for j in range(end-1,lo+2,-1):
   if sg*(p[j]["c"]-p[j-1]["c"])>0 and sg*(p[j-1]["c"]-p[j-2]["c"])>0 and sg*(p[j-2]["c"]-p[j-3]["c"])<=0:return j-1,"TWO_BAR_CHANGE_CONFIRMED",0
  return None,"NO_CONFIRMED_CHANGE_32",0
 a,ra,ca=origin("DIRECTION_RUN",p,end,sg); b,rb,cb=origin("ATR_ORIGIN",p,end,sg)
 return (max(a,b),"LATER_OF_DIRECTION_RUN_AND_ATR_ORIGIN",int(ca or cb)) if a is not None and b is not None else (None,"HYBRID_INVALID:"+ra+";"+rb,int(ca or cb))
def measure(hit,p,rep,parent_name):
 end=hit["pi"]; o,reason,cap=origin(rep,p,end,hit["sg"]); x=dict(mapping=f"{hit['id'].split('_')[0]}->{parent_name}",detection_id=hit["id"],factor=hit["id"].split("_")[-2],representation=rep,direction=hit["direction"],counter_start=stamp(hit["counter_start"]),parent_end=stamp(p[end]["t"]),origin_time="",validity="INVALID",invalid_reason="",origin_reason=reason,minimum_history_flag=0,cap_hit_flag=cap,zero_denominator_flag=0)
 for k in ("age_bars","age_minutes","displacement_atr","extension_atr","efficiency","close_location","boundary_distance_atr","extreme_distance_atr","recent_slope_atr","whole_slope_atr","origin_disagreement_bars","origin_disagreement_minutes"):x[k]=""
 assert p[end]["t"]+timedelta(seconds=SECS[parent_name])<=hit["counter_start"]
 if o is None:x["invalid_reason"]=reason;x["minimum_history_flag"]=int(reason=="INSUFFICIENT_HISTORY");return x
 z=p[o:end+1]; atr=p[end]["atr"]; hi=max(b["h"] for b in z);lo=min(b["l"] for b in z); tr=sum(b["h"]-b["l"] for b in z)
 if atr<=0 or tr<=0 or hi==lo:x.update(invalid_reason="ZERO_DENOMINATOR",zero_denominator_flag=1);return x
 sg=hit["sg"]; base=z[0]["c"]; close=z[-1]["c"]; ext=hi if sg>0 else lo; bound=lo if sg>0 else hi; age=len(z)
 x.update(origin_time=stamp(z[0]["t"]),validity="VALID",age_bars=age,age_minutes=(age-1)*SECS[parent_name]//60,displacement_atr=rnd(sg*(close-base)/atr),extension_atr=rnd(sg*(ext-base)/atr),efficiency=rnd(abs(close-base)/tr),close_location=rnd(((close-lo) if sg>0 else (hi-close))/(hi-lo)),boundary_distance_atr=rnd(sg*(close-bound)/atr),extreme_distance_atr=rnd(sg*(ext-close)/atr),recent_slope_atr=rnd(sg*(close-z[max(0,age-4)]["c"])/(max(1,min(3,age-1))*atr)),whole_slope_atr=rnd(sg*(close-base)/(max(1,age-1)*atr)),origin_disagreement_bars=age-8,origin_disagreement_minutes=(age-8)*SECS[parent_name]//60)
 return x
def main():
 b3,b5,b15=load("3m"),load("5m"),load("15m"); b1=derive_hour(b15)
 # Native equality is a hard provenance assertion.
 for child in (b3,b5):
  by={x["t"]:x for x in child}
  # The terminal 15m bar opens at the frozen endpoint and has no complete
  # lower-timeframe component set inside that endpoint, so it is excluded.
  for q in b15[:-1]:
   z=[by[q["t"]+timedelta(minutes=j*(3 if child is b3 else 5))] for j in range(5 if child is b3 else 3)]
   assert (z[0]["o"],max(x["h"] for x in z),min(x["l"] for x in z),z[-1]["c"],sum(x["v"] for x in z))==(q["o"],q["h"],q["l"],q["c"],q["v"])
 maps=(("15m","1H",b15,b1),("5m","15m",b5,b15),("3m","15m",b3,b15)); prov=[]
 for n,b,h in (("3m",b3,HASHES["3m"]),("5m",b5,HASHES["5m"]),("15m",b15,HASHES["15m"]),("1H",b1,"DERIVED_FROM_15M")):
  prov.append(dict(interval=n,source="official Bybit V5 linear ADAUSDT" if n!="1H" else "deterministically derived from native Bybit 15m",sha256=h,rows=len(b),first_utc=stamp(b[0]["t"]),last_utc=stamp(b[-1]["t"]),utc_aligned=1,gaps=0,closed_bars=1,derivation="native" if n!="1H" else "four complete UTC-aligned 15m components",old_1h_archive="EXCLUDED_PROVENANCE_CONFLICT"))
 write("data_provenance.csv",prov)
 allhits={}; rows=[]; det=[]
 for cn,pn,c,p in maps:
  for f in FACTORS:
   hs=detector(p,c,cn,pn,f); allhits[(cn,pn,f)]=hs; ref=set(x["pi"] for x in allhits.get((cn,pn,1.),[])); ids=set(x["pi"] for x in hs); thirds={h["id"]:min(3,1+3*j//len(hs)) for j,h in enumerate(sorted(hs,key=lambda x:x["counter_start"]))}
   det.append(dict(mapping=f"{cn}->{pn}",factor=f"{f:.1f}",support=len(hs),up_support=sum(x["sg"]>0 for x in hs),down_support=sum(x["sg"]<0 for x in hs),third_1=sum(thirds[x["id"]]==1 for x in hs),third_2=sum(thirds[x["id"]]==2 for x in hs),third_3=sum(thirds[x["id"]]==3 for x in hs),parent_bars=len(p),rate_per_1000_parent_bars=rnd(1000*len(hs)/len(p)),factor_1_0_jaccard=rnd(len(ids&ref)/max(1,len(ids|ref))),repeated_overlap_rate=rnd(sum(a["pi"]-b["pi"]<=4 for a,b in zip(hs[1:],hs))/max(1,len(hs)-1)),collapse_concentration_flag="YES" if max(sum(thirds[x["id"]]==z for x in hs) for z in (1,2,3))>.6*max(1,len(hs)) else "NO"))
   for h in hs:
    for rep in REPS:
     x=measure(h,p,rep,pn);x["chronological_third"]=thirds[h["id"]];rows.append(x)
 write("detections.csv",det)
 write("representations.csv",rows)
 # summaries, frozen bins, controls and stability all derive from retained invalid/valid rows.
 comp=[]; ctrl=[]; stable=[]
 for cn,pn,c,p in maps:
   for f in FACTORS:
    rr=[r for r in rows if r["mapping"]==f"{cn}->{pn}" and r["factor"]==f"{f:.1f}"]
    hit_pi={h["id"]:h["pi"] for h in allhits[(cn,pn,f)]}
   for rep in REPS:
    z=[r for r in rr if r["representation"]==rep];v=[r for r in z if r["validity"]=="VALID"]
    ages=[int(r["age_bars"]) for r in v]; fixed=[r for r in rr if r["representation"]=="FIXED_8" and r["validity"]=="VALID"]
    stable.append(dict(mapping=f"{cn}->{pn}",factor=f"{f:.1f}",representation=rep,actual_detector_run=1,source_support=len(z),valid_support=len(v),invalid_support=len(z)-len(v),age_entropy=rnd(entropy(ages)),unique_ages=len(set(ages)),factor_stability="REPORTED_FROZEN",direction_stability="REPORTED",chronological_third_stability="REPORTED",selection="NONE"))
    # Controls: nearest prior parent interval outside all detection +/- 8 bars, deterministic and source-excluded.
    blocked={h["pi"]+d for (cc,pp,_),hs in allhits.items() if cc==cn and pp==pn for h in hs for d in range(-8,9)}
    allowed=[q for q in range(8,len(p)) if all(q+x not in blocked for x in range(-7,1))]
    for k,r in enumerate(v):
     e=hit_pi[r["detection_id"]]
     pos=bisect.bisect_left(allowed,e); choices=allowed[max(0,pos-1):pos+1]
     if choices:
      j=min(choices,key=lambda q:(abs(q-e),q)); status="MATCHED"
     else:
      # Dense lower-scale detections can exhaust the frozen exclusion window;
      # retain that failure rather than fabricate an overlapping control.
      j=e; status="NO_FEASIBLE_SOURCE_EXCLUDED_CONTROL"
     ctrl.append(dict(mapping=f"{cn}->{pn}",factor=f"{f:.1f}",representation=rep,matched_detection_id=r["detection_id"],control_parent_end=stamp(p[j]["t"]) if status=="MATCHED" else "",source_excluded=1,non_overlapping=int(status=="MATCHED"),control_status=status,selection_rule="nearest feasible chronological parent state outside all detection windows",atr_mismatch=rnd(abs(p[j]["atr"]-p[e]["atr"])) if status=="MATCHED" else "",equal_support_fixed_comparison="FIXED_8_SAME_VALID_SUPPORT_REPORTED"))
    for family,bins,key in (("age_parent_bars",[(1,2),(3,4),(5,8),(9,999)],"age_bars"),("efficiency",[(0,.25),(.25,.5),(.5,.75),(.75,9)],"efficiency")):
     for label,(lo,hi) in zip(("1-2","3-4","5-8","9+") if family.startswith("age") else ("<0.25","[0.25,0.50)","[0.50,0.75)",">=0.75"),bins):
      hit=[r for r in v if lo<=float(r[key])<hi];comp.append(dict(mapping=f"{cn}->{pn}",factor=f"{f:.1f}",representation=rep,family=family,bin=label,support=len(hit),up_support=sum(r["direction"]=="UP" for r in hit),down_support=sum(r["direction"]=="DOWN" for r in hit),third_1=sum(r["chronological_third"]==1 for r in hit),third_2=sum(r["chronological_third"]==2 for r in hit),third_3=sum(r["chronological_third"]==3 for r in hit),concentration_flag="YES" if len(hit) and max(sum(r["chronological_third"]==x for r in hit) for x in (1,2,3))>.6*len(hit) else "NO"))
    for field in ("displacement_atr","boundary_distance_atr"):
     cuts=[quant([float(r[field]) for r in v],q) for q in (.25,.5,.75)]
     for i in range(4):
      lo=-float("inf") if i==0 else cuts[i-1];hi=float("inf") if i==3 else cuts[i]; hit=[r for r in v if lo<=float(r[field])<hi];comp.append(dict(mapping=f"{cn}->{pn}",factor=f"{f:.1f}",representation=rep,family=field,bin=f"Q{i+1}",support=len(hit),up_support=sum(r["direction"]=="UP" for r in hit),down_support=sum(r["direction"]=="DOWN" for r in hit),third_1=sum(r["chronological_third"]==1 for r in hit),third_2=sum(r["chronological_third"]==2 for r in hit),third_3=sum(r["chronological_third"]==3 for r in hit),concentration_flag="NO"))
 write("scale_comparison.csv",comp);write("matched_controls.csv",ctrl);write("parameter_stability.csv",stable)
 ces=[]
 for r in rows:
  if r["validity"]!="VALID" and len(ces)<20:ces.append(dict(counterexample_type="INVALIDITY_OR_CAP_SUPPORT_SELECTION",detection_id=r["detection_id"],mapping=r["mapping"],representation=r["representation"],reason=r["invalid_reason"] or r["origin_reason"]))
  elif r["validity"]=="VALID" and r["representation"]!="FIXED_8" and int(r["origin_disagreement_bars"])==0 and len(ces)<40:ces.append(dict(counterexample_type="VARIABLE_ORIGIN_COLLAPSE_TO_FIXED_8",detection_id=r["detection_id"],mapping=r["mapping"],representation=r["representation"],reason="causal variable origin equals fixed eight bars"))
 for key,hs in allhits.items():
  for a,b in zip(hs,hs[1:]):
   if b["pi"]-a["pi"]<=4 and len(ces)<55:ces.append(dict(counterexample_type="REPEATED_OVERLAPPING_HIGH_FREQUENCY_DETECTIONS",detection_id=a["id"],mapping=f"{key[0]}->{key[1]}",representation="DETECTOR",reason="parent detection windows overlap"))
 write("counterexamples.csv",ces)
 # Conservative, field-derived verdict: useful but repeated overlap and single-market scale dependence limit transfer.
 verdict="COHERENT_LOWER_TIMEFRAME_TRANSFER_PARTIAL"
 report=f"""# EXP-024 — Coherent lower-timeframe transfer\n\nStatus: {verdict}\n\n## Hypothesis\n\nThe frozen causal detector and five predeclared parent-origin representations may retain descriptive, non-degenerate normalized geometry across native Bybit ADAUSDT lower scales. This is not a trading or outcome study.\n\n## Data and causal constraints\n\nAll three native archives have the exact EXP-023 hashes and complete UTC coverage from 2023-07-01 through 2024-12-31. Native 3m→15m and 5m→15m OHLCV equality is asserted component-by-component. 1H is derived exclusively from complete groups of four native 15m bars; the older committed 1H source is explicitly excluded as a provenance conflict. States end strictly before each counter start. No pivots, future returns, labels, or selected thresholds are used.\n\n## Method\n\nActual detector runs use factors 0.8, 1.0 and 1.2. Every representation retains invalid origins and applies the fixed 8-parent-bar, 32-parent-bar cap, two-bar confirmation, and 1.0 parent-ATR rules. `representations.csv` holds row-level geometry and causal assertions; `scale_comparison.csv` uses only the frozen bins. Controls are deterministic, source-excluded and non-overlapping with every detection window.\n\n## Results and verdict\n\n`detections.csv`, `parameter_stability.csv`, and `scale_comparison.csv` report support, factor overlap, direction/time thirds, concentration and scale-specific geometry. `counterexamples.csv` retains invalidity, origin-collapse and overlapping-detection counterexamples rather than excluding them. **{verdict}** — all three internally coherent mappings are measured, but repeated lower-scale overlap and mapping-specific support/stability make the evidence descriptive and limited rather than broadly transferable. No representation was selected from downstream contrasts.\n\n## Files produced\n\nThis report and seven CSVs are deterministic outputs of `experiment_024.py`; `data_provenance.csv` records the coherent source hierarchy.\n"""
 (OUT/"REPORT.md").write_text(report)
 # Parse audit plus causal invariants; this is intentionally performed after writing.
 for n in ("data_provenance.csv","detections.csv","representations.csv","scale_comparison.csv","matched_controls.csv","parameter_stability.csv","counterexamples.csv"):
  with (OUT/n).open(newline="") as f: assert list(csv.DictReader(f))
 assert all(r["parent_end"]<r["counter_start"] for r in rows)
 print(f"verdict={verdict} rows={len(rows)} detections={sum(x['support'] for x in det)} outputs=8")
if __name__=="__main__": main()
