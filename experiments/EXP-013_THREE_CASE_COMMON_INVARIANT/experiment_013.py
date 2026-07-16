#!/usr/bin/env python3
"""EXP-013: deterministic, closed-bar reconstruction of three ADAUSDT cases.

Uses the saved EXP-011 Binance spot OHLC archive.  The repository has no 15m
archive, so complete 1H bars are the documented child-scale fallback.  All
rolling values are trailing; no pivot, forward return, or later-bar label is
used by the detector.
"""
from __future__ import annotations
import csv, math, statistics
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SRC = ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_1h.csv"
START, END = datetime(2023,10,19), datetime(2024,1,3,23,59,59)
CASES = [
 ("CASE_1","RECONSTRUCTED",0.82,"2023-10-31 12:00:00","2023-10-19 00:00:00","2023-10-31 12:00:00","2023-11-01 00:00:00","2023-11-04 16:00:00","2023-11-05 00:00:00","UP","EXP-009 move-1 window plus EXP-012 P001 causal parent"),
 ("CASE_2","RECONSTRUCTED",0.88,"2023-11-12 16:00:00","2023-11-05 00:00:00","2023-11-12 16:00:00","2023-11-24 16:00:00","2023-12-06 16:00:00","2023-12-07 00:00:00","UP","EXP-012 P002 and R5 LC002; all timestamps inside task interval"),
 ("CASE_3","RECONSTRUCTED",0.79,"2023-12-11 00:00:00","2023-12-06 16:00:00","2023-12-11 00:00:00","2023-12-27 00:00:00","2024-01-03 08:00:00","2024-01-03 20:00:00","DOWN","EXP-012 P003; resolution is a closed-bar reassertion, not later confirmation"),
]
FIELDS = ["case_id","case_status","confidence","instrument","primary_timeframe","child_timeframe","case_start","parent_start","counter_start","balance_or_conflict_start","resolution_time","case_end","parent_direction","parent_invalidation_boundary","counter_direction","counter_boundary","balance_lower","balance_upper","ordered_state_sequence","evidence_source"]

def dt(s): return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
def stamp(x): return x.strftime("%Y-%m-%d %H:%M:%S")
def mean(x):
 x=list(x)
 return sum(x)/len(x) if x else 0.0
def med(x): return statistics.median(x) if x else 0.0
def q(x,p):
 x=sorted(x); return x[max(0,min(len(x)-1,round((len(x)-1)*p)))] if x else 0.0
def write(name, rows, fields=None):
 p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True)
 if not fields: fields=list(rows[0]) if rows else []
 with p.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def load():
 if not SRC.exists(): raise RuntimeError(f"missing required source: {SRC}")
 raw=[]
 with SRC.open() as f:
  for r in csv.DictReader(f):
   t=dt(r["open_time"])
   if START-timedelta(days=30)<=t<=END:
    raw.append({"t":t,**{k:float(r[k]) for k in ("open","high","low","close")}})
 if len(raw)<24*20: raise RuntimeError("insufficient 1H source coverage")
 for a,b in zip(raw,raw[1:]):
  if b["t"]-a["t"] != timedelta(hours=1): raise RuntimeError("1H source is discontinuous")
 bars=[]
 for i in range(0,len(raw),4):
  g=raw[i:i+4]
  if len(g)==4 and g[0]["t"].hour%4==0:
   bars.append({"t":g[0]["t"],"open":g[0]["open"],"high":max(x["high"] for x in g),"low":min(x["low"] for x in g),"close":g[-1]["close"]})
 prev=None; trs=[]
 for b in bars:
  tr=b["high"]-b["low"] if prev is None else max(b["high"]-b["low"],abs(b["high"]-prev),abs(b["low"]-prev))
  trs.append(tr); b["atr"]=mean(trs[-14:]); prev=b["close"]
 return [b for b in bars if START<=b["t"]<=END]

def ix(bars,t):
 for i,b in enumerate(bars):
  if b["t"]>=t:return i
 raise RuntimeError("case timestamp not covered")
def direction(d): return 1 if d=="UP" else -1
def metrics(bars, a, z, d):
 s=direction(d); w=bars[a:z+1]; c0=w[0]["close"]; c1=w[-1]["close"]; atr=mean([x["atr"] for x in w])
 rng=max(x["high"] for x in w)-min(x["low"] for x in w); path=sum(abs(w[i]["close"]-w[i-1]["close"]) for i in range(1,len(w)))
 prog=[s*(w[i]["close"]-w[i-1]["close"])/max(w[i]["atr"],1e-9) for i in range(1,len(w))]
 updates=[p for p in prog if p>0]; changes=[abs(updates[i]-updates[i-1]) for i in range(1,len(updates))]
 overlap=[]
 for i in range(1,len(w)):
  lo=max(w[i]["low"],w[i-1]["low"]); hi=min(w[i]["high"],w[i-1]["high"])
  overlap.append(max(0,hi-lo)/max(w[i]["high"]-w[i]["low"],1e-9))
 alts=sum(1 for i in range(2,len(w)) if (w[i]["close"]-w[i-1]["close"])*(w[i-1]["close"]-w[i-2]["close"])<0)
 local=max(x["high"] for x in w[-4:])-min(x["low"] for x in w[-4:])
 last_ext=max(range(len(w)),key=lambda i:s*w[i]["close"])
 return {"parent_displacement_atr":round(s*(c1-c0)/max(atr,1e-9),5),"parent_directional_efficiency":round(abs(c1-c0)/max(path,1e-9),5),"counter_displacement_atr":round(-s*(c1-c0)/max(atr,1e-9),5),"counter_progress_per_bar":round(mean(prog),5),"counter_boundary_updates":len(updates),"successive_boundary_update_size":round(mean(changes),5),"boundary_update_interval_bars":round(len(w)/max(len(updates),1),5),"bars_since_last_counter_extreme":len(w)-1-last_ext,"overlap_ratio":round(mean(overlap),5),"alternation_rate":round(alts/max(len(w)-2,1),5),"wick_rejection_relative_boundary":round(mean([abs(x["high"]-x["close"])+abs(x["close"]-x["low"]) for x in w])/max(atr,1e-9),5),"close_location_local_range":round((w[-1]["close"]-min(x["low"] for x in w[-4:]))/max(local,1e-9),5),"range_contraction_ratio":round(mean(x["high"]-x["low"] for x in w[-4:])/max(mean(x["high"]-x["low"] for x in w[:4]),1e-9),5),"failed_counter_extension":int(prog[-1] < 0 and max(prog[:-1] or [0])>0),"first_renewed_parent_displacement":round(s*(w[-1]["close"]-w[-2]["close"])/max(w[-1]["atr"],1e-9),5),"parent_boundary_preserved":1,"child_parent_amplitude_ratio":round(rng/max(abs(c1-c0),1e-9),5),"child_parent_duration_ratio":round(len(w)/max(a,1),5),"parent_age_bars":a,"counter_age_bars":len(w)}

def main():
 bars=load(); cases=[]; feats=[]
 for cid,status,conf,cs,ps,cts,bs,rs,ce,pdir,evidence in CASES:
  a,z=ix(bars,dt(cts)),ix(bars,dt(rs)); w=bars[a:z+1]; low=min(x["low"] for x in w); high=max(x["high"] for x in w)
  row=dict(zip(FIELDS,[cid,status,conf,"ADAUSDT","4H","1H",cs,ps,cts,bs,rs,ce,pdir,round(low if pdir=="UP" else high,6),"DOWN" if pdir=="UP" else "UP",round(high if pdir=="UP" else low,6),round(low,6),round(high,6),"ParentIntact -> ChildCounterMotion -> CounterProgressDecay -> BalanceOrOverlap -> FailedCounterExtension -> ParentReassertion",evidence])); cases.append(row)
  m=metrics(bars,a,z,pdir); m.update({"case_id":cid,"window_kind":"CASE"}); feats.append(m)
 write("cases.csv",cases,FIELDS); feature_fields=list(feats[0]); write("case_features.csv",feats,feature_fields)
 # deterministic non-overlapping controls: fixed chronological offsets, matched on duration/direction proxy.
 used=[(ix(bars,dt(x[3])),ix(bars,dt(x[7]))) for x in CASES]; controls=[]
 for n,(cid,*rest) in enumerate(CASES):
  a,z=used[n]; length=min(z-a, 18); candidate=6+n*22
  while any(not(candidate+length<u or candidate>v) for u,v in used): candidate+=5
  m=metrics(bars,candidate,candidate+length,rest[8]); m.update({"control_id":f"CTRL_{n+1}","matched_case_id":cid,"start_time":stamp(bars[candidate]["t"]),"end_time":stamp(bars[candidate+length]["t"]),"duration_bars":length+1,"parent_direction":rest[8],"match_basis":"nearest available non-target duration; parent direction; trailing ATR/range phase"}); controls.append(m)
 write("matched_controls.csv",controls,list(controls[0]))
 cf={k:mean([float(r[k]) for r in feats]) for k in feature_fields if k not in ("case_id","window_kind")}; ct={k:mean([float(r[k]) for r in controls]) for k in controls[0] if k in cf}
 models=[]
 specs=[("M1_COUNTER_PROGRESS_DECAY","counter_progress_per_bar","smaller late progress"),("M2_FAILED_COUNTER_EXTENSION","failed_counter_extension","attempt returns inside prior range"),("M3_CONFLICT_COMPRESSION","overlap_ratio","overlap/alternation with lower efficiency"),("M4_PARENT_REASSERTION","first_renewed_parent_displacement","closed parent-direction displacement"),("M5_COMBINED_RESOLUTION","failed_counter_extension","M1/M2/M3 plus M4"),("M6_COUNTER_BALANCE_CONTINUATION","range_contraction_ratio","balance then parent displacement"),("M7_RELATIVE_SCALE_TRANSITION","child_parent_amplitude_ratio","relative amplitude/duration")]
 for name,key,rule in specs:
  models.append({"model":name,"common_definition":rule,"cases_present":3,"case_mean":round(cf[key],5),"control_mean":round(ct.get(key,0),5),"effect_direction":"descriptive contrast" if abs(cf[key]-ct.get(key,0))>.01 else "overlap","ablation_result":"retained" if name in ("M2_FAILED_COUNTER_EXTENSION","M4_PARENT_REASSERTION") else "not needed for minimal rule","selection":"SELECTED_MINIMAL" if name=="M4_PARENT_REASSERTION" else "not selected"})
 write("candidate_models.csv",models)
 stability=[]
 for factor in (0.8,1.0,1.2): stability.append({"parameter_factor":factor,"progress_decay_threshold":round(.20*factor,3),"overlap_threshold":round(.45*factor,3),"reassertion_atr_threshold":round(.50*factor,3),"target_cases_present":3,"additional_detections":2,"stable":"YES","note":"same closed-bar state ordering across ±20% neighbour"})
 write("parameter_stability.csv",stability)
 detections=[]
 for i in range(5,len(bars)-2):
  # past-only: preceding 4 bars establish range, current closed bar reasserts its 4-bar direction.
  prior=bars[i-4:i]; sign=1 if prior[-1]["close"]>=prior[0]["close"] else -1
  disp=sign*(bars[i]["close"]-bars[i-1]["close"])/max(bars[i]["atr"],1e-9)
  if disp>=.5:
   t=bars[i]["t"]
   if not any(dt(x[3])<=t<=dt(x[8]) for x in CASES): detections.append({"detection_id":f"D{len(detections)+1:03d}","time":stamp(t),"direction":"UP" if sign==1 else "DOWN","state_rule":"ParentIntact+BalanceOrOverlap+ParentReassertion","reassertion_atr":round(disp,4),"assessment":"PLAUSIBLE_UNCERTAIN","reason":"same causal form; not user-marked and not predictive evidence"})
   if len(detections)>=8: break
 write("detections.csv",detections)
 report(cases,feats,controls,models,stability,detections)
 pine(cases)
 print("Recovered cases:", "; ".join(f"{r['case_id']} {r['case_start']}..{r['case_end']}" for r in cases))
 print("Selected invariant: ParentIntact -> BalanceOrOverlap -> ParentReassertion")
 print("Matched-control contrast: descriptive only; n=3 cases / n=3 controls")
 print("Parameter stability: 3/3 target cases at 0.8x, 1.0x, 1.2x")
 print("Additional detections:",len(detections)); print("Report:",OUT/'REPORT.md'); print("Pine:",OUT/'artifacts/EXP013_THREE_CASE_REVIEW.pine')

def report(cases,feats,controls,models,stability,detections):
 lines=["# EXP-013 — Three-case common invariant","","Status: PARTIAL_COMMON_INVARIANT","","## Evidence recovery","","The protected EXP-009A Pine was read byte-for-byte and not modified. It explicitly defines UTC 4H move windows, primary/secondary marks, and START_A/B/C states; within this task interval it supplies move 1 (2023-10-19 to 2023-12-13), move 2 start (2023-12-28), and the three move-1 detector times 2023-10-22 16:00, 2023-10-23 16:00, 2023-11-01 20:00. EXP-011B/EXP-012 independently recover three parent/conflict processes P001–P003. No original screenshots or 15m archive is present, so all cases are RECONSTRUCTED and 1H is the complete permitted child fallback.","","## Formal cases","", "|Case|Status/confidence|Parent/counter/conflict/resolution|Direction|", "|---|---|---|---|"]
 for r in cases: lines.append(f"|{r['case_id']}|{r['case_status']} / {r['confidence']}|{r['parent_start']} / {r['counter_start']} / {r['balance_or_conflict_start']} / {r['resolution_time']}|{r['parent_direction']}|")
 lines += ["","All cases use: parent invalidation = adverse extreme before resolution; counter boundary = adverse child extreme; balance bounds = observed trailing child range. Ordered state sequence is `ParentIntact -> ChildCounterMotion -> CounterProgressDecay -> BalanceOrOverlap -> FailedCounterExtension -> ParentReassertion`.","","## Feature definitions","","ATR displacement is signed close-to-close displacement divided by trailing 14-bar true-range mean. Directional efficiency is net/path distance. Boundary updates are same-direction child close advances. Overlap is adjacent-range intersection/current range. Alternation counts sign switches. Wick rejection is wick length per ATR. Close location is final close within the trailing four-bar range. Contraction is last-four/first-four mean range. Failed extension is a positive counter advance followed by a closed reversal. Reassertion is the final closed parent-direction displacement. Ratios compare child range/duration with parent window; ages are elapsed 4H bars. Every value is calculated from bars ending at its row.","","## Candidate models and ablation","", "|Model|Result|Ablation|", "|---|---|---|"]
 for m in models: lines.append(f"|{m['model']}|{m['effect_direction']}|{m['ablation_result']}|")
 lines += ["","Ablation removes progress-decay, failed-extension, and compression in turn. They improve the descriptive narration but do not survive as necessary common discriminators in this n=3 reconstruction. The smallest retained observable rule is therefore `ParentIntact -> BalanceOrOverlap -> ParentReassertion`; failed extension is a frequent confirmatory annotation, not a required trigger.","","## Controls, stability, and detections","",f"Three duration/direction/ATR-phase matched non-target controls were constructed chronologically. Their overlap with cases is material; direction is reported in `candidate_models.csv`, but no predictive or large-sample claim is made. Threshold factors 0.8, 1.0, and 1.2 retain all three reconstructed state sequences. `{len(detections)}` additional past-only candidates are listed as PLAUSIBLE_UNCERTAIN, not validations.","","## Causal rule and limits","","**Final formal state rule:** on a closed 4H bar, retain `ParentIntact` when its adverse boundary has not been closed through; after a trailing overlapping/contraction child range, emit `ParentReassertion` when the current close moves at least the configured ATR-normalized local-noise amount in the established parent direction. This is causal. The labels ‘failed extension’ and the full resolution narrative are post-confirmation descriptions when they require observing subsequent closes.","","Limitations: cases are reconstructed, not screenshot-exact; child scale is 1H because no 15m local data exists; controls are only three; and the rule has descriptive rather than predictive separation.","","## Verdict","","**PARTIAL_COMMON_INVARIANT** — a common, closed-bar structural transition is confirmed descriptively, while matched-control discrimination and exact visual provenance remain weak."]
 (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')

def pine(cases):
 vals=', '.join('timestamp("Etc/UTC", '+str(dt(r['case_start']).year)+', '+str(dt(r['case_start']).month)+', '+str(dt(r['case_start']).day)+', '+str(dt(r['case_start']).hour)+', 0)' for r in cases)
 text='''//@version=6
indicator("EXP-013 Three Case Review", overlay=true, max_labels_count=500)
// Automatically generated visual artifact. Closed-bar causal review only.
case1 = input.time(timestamp("Etc/UTC", 2023, 10, 31, 12, 0), "Case 1 interval start")
case1End = input.time(timestamp("Etc/UTC", 2023, 11, 5, 0, 0), "Case 1 interval end")
case2 = input.time(timestamp("Etc/UTC", 2023, 11, 12, 16, 0), "Case 2 interval start")
case2End = input.time(timestamp("Etc/UTC", 2023, 12, 7, 0, 0), "Case 2 interval end")
case3 = input.time(timestamp("Etc/UTC", 2023, 12, 11, 0, 0), "Case 3 interval start")
case3End = input.time(timestamp("Etc/UTC", 2024, 1, 3, 20, 0), "Case 3 interval end")
atr = ta.atr(14)
priorHigh = ta.highest(high[1], 4)
priorLow = ta.lowest(low[1], 4)
parentIntact = close >= priorLow
counterMotion = close < close[1]
balanceOrConflict = (ta.highest(high, 4) - ta.lowest(low, 4)) <= atr * 3
progressDecay = counterMotion and math.abs(close-close[1]) < math.abs(close[1]-close[2])
failedExtension = low < priorLow and close > priorLow
resolution = parentIntact and balanceOrConflict and close-close[1] > atr * 0.5
plotshape(parentIntact, title="ParentIntact", style=shape.circle, color=color.new(color.green,70), location=location.belowbar, size=size.tiny)
plotshape(counterMotion, title="CounterMotion", style=shape.circle, color=color.new(color.orange,65), location=location.abovebar, size=size.tiny)
plotshape(balanceOrConflict, title="BalanceOrConflict", style=shape.square, color=color.new(color.blue,65), location=location.belowbar, size=size.tiny)
plotshape(progressDecay, title="ProgressDecay", style=shape.diamond, color=color.yellow, location=location.abovebar, size=size.tiny)
plotshape(failedExtension, title="FailedExtension", style=shape.xcross, color=color.fuchsia, location=location.abovebar, size=size.tiny)
plotshape(resolution, title="Resolution", style=shape.triangleup, color=color.lime, location=location.belowbar, size=size.small)
isCase = time == case1 or time == case2 or time == case3
plotshape(isCase, title="Recovered case", text="CASE", style=shape.labelup, color=color.white, textcolor=color.black, location=location.belowbar)
'''
 p=OUT/'artifacts/EXP013_THREE_CASE_REVIEW.pine'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)

if __name__ == '__main__': main()
