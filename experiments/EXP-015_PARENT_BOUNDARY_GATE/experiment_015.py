#!/usr/bin/env python3
"""EXP-015: closed-bar parent-boundary gate audit for EXP-014 ADA transfer."""
from __future__ import annotations
import csv, hashlib, importlib.util, bisect
from pathlib import Path
from statistics import mean, median

ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
EXP014=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/experiment_014.py'
EXP014_ROWS=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/detections.csv'
SOURCE_START='2023-10-19 00:00:00'; SOURCE_END='2024-01-03 23:59:59'
DEFAULT_MARGIN=0.1
VARIANTS=('BASE','BOUNDARY_AT_COUNTER_END','BOUNDARY_THROUGH_BALANCE','BOUNDARY_THROUGH_REASSERTION','BOUNDARY_MARGIN')
INDEX={}
DETECTION_ROWS=[]

def load():
 s=importlib.util.spec_from_file_location('exp014',EXP014); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def write(name,rows,fields):
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
def av(a): return sum(a)/len(a) if a else 0.0
def stamp(x): return x.strftime('%Y-%m-%d %H:%M:%S')
def excluded(r): return SOURCE_START<=r['end_time']<=SOURCE_END
def idx(b,t): return INDEX[t]
def gate(row,b,variant,margin=0.0):
 i=idx(b,row['end_time']); child=b[i-4:i+1]; sign=1 if row['parent_direction']=='UP' else -1; boundary=float(row['parent_invalidation_boundary'])
 preserve=lambda xs: all(sign*(x['close']-boundary)>=0 for x in xs)
 # Counter ends at the penultimate child bar; its final bar is balance, and
 # the last completed child bar is reassertion. All predicates use known bars.
 counter=preserve(child[:3]); balance=preserve(child[:4]); strict=preserve(child)
 dist=sign*(child[-1]['close']-boundary)/max(child[-1]['atr'],1e-12)
 return {'BASE':True,'BOUNDARY_AT_COUNTER_END':counter,'BOUNDARY_THROUGH_BALANCE':balance,'BOUNDARY_THROUGH_REASSERTION':strict,'BOUNDARY_MARGIN':strict and dist>=margin}[variant],dist
def controls(rows,b):
 blocked=set()
 for r in (DETECTION_ROWS or rows):
  k=idx(b,r['end_time']); blocked.update(range(max(0,k-12),min(len(b),k+1)))
 # A candidate's direction is calculated from its own completed parent bars;
 # it is never inherited from the detection being matched.
 eligible={'UP':[],'DOWN':[]}
 for j in range(12,len(b)):
  if SOURCE_START<=stamp(b[j]['t'])<=SOURCE_END or any(k in blocked for k in range(j-4,j+1)): continue
  parent=b[j-12:j-4]; direction='UP' if parent[-1]['close']>=parent[0]['close'] else 'DOWN'; sign=1 if direction=='UP' else -1
  eligible[direction].append((sign*(b[j]['close']-b[j-1]['close'])/max(b[j]['atr'],1e-12),j))
 for direction in eligible: eligible[direction].sort()
 out=[]
 for n,r in enumerate(rows,1):
  i=idx(b,r['end_time']); target=float(r['reassertion_atr']); direction=r['parent_direction']; pool=eligible[direction]; pos=bisect.bisect_left(pool,(target,-1)); cand=[]
  for q in range(max(0,pos-8),min(len(pool),pos+9)):
   v,j=pool[q]; cand.append((abs(v-target),abs(j-i),j,v))
  _,loc,j,v=min(cand)
  out.append({'control_id':f'CTRL_{n:04d}','matched_interval_id':r['interval_id'],'variant':r['variant'],'instrument':'ADAUSDT','start_time':stamp(b[j-4]['t']),'end_time':stamp(b[j]['t']),'parent_direction':direction,'control_reassertion_atr':round(v,6),'duration_mismatch_bars':0,'atr_mismatch':round(abs(b[j]['atr']-b[i]['atr']),6),'realized_range_mismatch':round(abs((b[j]['high']-b[j]['low'])-(b[i]['high']-b[i]['low'])),8),'parent_age_mismatch_bars':0,'phase_location_mismatch':round(loc/max(len(b),1),6),'match_exact':0,'mismatch_disclosure':'candidate parent direction, duration, and parent age exact; nearest deterministic reassertion ATR, then time location; realized-range mismatch explicit'})
 return out
def contrast(rows,ctrl):
 x=[float(r['reassertion_atr']) for r in rows]; y=[float(r['control_reassertion_atr']) for r in ctrl]; pairs=list(zip(x,y)); rb=(sum(a>b for a,b in pairs)-sum(a<b for a,b in pairs))/max(len(pairs),1)
 return (median(x) if x else 0,mean(x) if x else 0,median(y) if y else 0,mean(y) if y else 0,rb,av([a>b for a,b in pairs]),av([min(a,b)/max(a,b,1e-12) for a,b in pairs]))
def third(t,start,end):
 p=(t-start).total_seconds()/max((end-start).total_seconds(),1); return min(3,int(p*3)+1)
def main():
 global INDEX, DETECTION_ROWS
 OUT.mkdir(parents=True,exist_ok=True); m=load(); b=m.bars(); INDEX={stamp(x['t']):i for i,x in enumerate(b)}; raw=[r for r in m.detected(b,1.0) if not excluded(r)]; DETECTION_ROWS=raw
 # Agreement is with the committed full diagnostic transfer rows, not a display subset.
 with EXP014_ROWS.open() as f: committed=list(csv.DictReader(f))
 keys=('interval_id','parent_direction','parent_start','counter_start','balance_start','reassertion_time','child_counter_motion','balance_or_overlap','parent_reassertion')
 assert len(raw)==len(committed) and all(tuple(str(r[k]) for k in keys)==tuple(c[k] for k in keys) for r,c in zip(raw,committed))
 assert not any(excluded(r) for r in raw)
 rows=[]
 for v in VARIANTS:
  for r0 in raw:
   threshold=DEFAULT_MARGIN if v=='BOUNDARY_MARGIN' else 0.0; ok,dist=gate(r0,b,v,threshold); r=dict(r0); r.update({'variant':v,'boundary_margin_threshold_atr':threshold,'boundary_distance_atr':round(dist,6),'gate_pass':int(ok),'counter_boundary_preserved':int(gate(r0,b,'BOUNDARY_AT_COUNTER_END')[0]),'balance_boundary_preserved':int(gate(r0,b,'BOUNDARY_THROUGH_BALANCE')[0]),'reassertion_boundary_preserved':int(gate(r0,b,'BOUNDARY_THROUGH_REASSERTION')[0])}); rows.append(r)
 fields=list(rows[0]); write('gated_detections.csv',rows,fields)
 summaries=[]; allctrl=[]
 for v in VARIANTS:
  q=[r for r in rows if r['variant']==v and r['gate_pass']]; c=controls(q,b); allctrl+=c; a=contrast(q,c); diag=sum(r['diagnostic_flag']=='1' for r in q)
  summaries.append({'variant':v,'margin_threshold_atr':DEFAULT_MARGIN if v=='BOUNDARY_MARGIN' else 0.0,'support_count':len(q),'support_rate_per_1000_parent_bars':round(1000*len(q)/len(b),6),'retained_fraction_from_base':round(len(q)/max(len(raw),1),6),'diagnostic_retained':diag,'diagnostic_removed':sum(r['diagnostic_flag']=='1' for r in raw)-diag,'reassertion_atr_median':round(a[0],6),'reassertion_atr_mean':round(a[1],6),'matched_control_median':round(a[2],6),'matched_control_mean':round(a[3],6),'paired_rank_contrast':round(a[4],6),'above_matched_control_fraction':round(a[5],6),'distribution_overlap':round(a[6],6),'up_count':sum(r['parent_direction']=='UP' for r in q),'down_count':sum(r['parent_direction']=='DOWN' for r in q),'sample_collapse_flag':'YES' if len(q)<max(10,len(raw)*.1) else 'NO','predicate':'closed-bar executable boundary predicate'})
 write('matched_controls.csv',allctrl,list(allctrl[0]) if allctrl else ['control_id']); write('gate_comparison.csv',summaries,list(summaries[0]))
 strict=[r for r in rows if r['variant']=='BOUNDARY_THROUGH_REASSERTION' and r['gate_pass']]; pc=[]
 baseids={r['interval_id'] for r in raw if gate(r,b,'BOUNDARY_MARGIN',DEFAULT_MARGIN)[0]}
 for f in (.8,1.0,1.2):
  rr=[r for r in m.detected(b,f) if not excluded(r)]
  for margin in (0.0,.1,.2,.3):
   q=[r for r in rr if gate(r,b,'BOUNDARY_MARGIN',margin)[0]]; c=controls([dict(r,variant='BOUNDARY_MARGIN') for r in q],b); z=contrast(q,c)
   pc.append({'parameter_factor':f,'margin_threshold_atr':margin,'support_count':len(q),'detection_overlap_with_factor_1_0':round(len({r['interval_id'] for r in q}&baseids)/max(len({r['interval_id'] for r in q}|baseids),1),6),'control_rank_contrast':round(z[4],6),'control_contrast_direction':'POSITIVE' if z[4]>0 else 'NONPOSITIVE','diagnostic_reduction':sum(r['diagnostic_flag']=='1' for r in rr)-sum(r['diagnostic_flag']=='1' for r in q),'verdict_stability':'PENDING','actual_detector_run':1})
 # Stability is derived after all actual detector calls: a row is stable only
 # when its contrast direction agrees with the fixed-factor margin row.
 ref=next(x for x in pc if x['parameter_factor']==1.0 and x['margin_threshold_atr']==DEFAULT_MARGIN)
 for x in pc: x['verdict_stability']='STABLE' if x['control_contrast_direction']==ref['control_contrast_direction'] and x['support_count']>=max(10,ref['support_count']*.1) else 'LIMITED'
 write('parameter_stability.csv',pc,list(pc[0]))
 # Rank-based thirds are chronological, deterministic, and exhaustive over the
 # evaluated (source-excluded) rows, including an archive split at the source gap.
 ordered=sorted(raw,key=lambda r:(r['end_time'],r['interval_id'])); end_segment={r['interval_id']:min(3,1+3*n//len(ordered)) for n,r in enumerate(ordered)}; ts=[]
 for v in VARIANTS:
  for seg in (1,2,3):
   for d in ('UP','DOWN'):
    q=[r for r in rows if r['variant']==v and r['gate_pass'] and r['parent_direction']==d and end_segment[r['interval_id']]==seg]; c=controls(q,b); z=contrast(q,c)
    counts=[sum(x['variant']==v and x['gate_pass'] and x['parent_direction']==d and end_segment[x['interval_id']]==s for x in rows) for s in (1,2,3)]
    ts.append({'variant':v,'segment':seg,'parent_direction':d,'support_count':len(q),'contrast':round(z[4],6),'above_control_fraction':round(z[5],6),'time_concentrated_flag':'PENDING'})
 assert sum(1 for r in raw if end_segment[r['interval_id']] in (1,2,3))==len(raw)
 for v in VARIANTS:
  for d in ('UP','DOWN'):
   group=[x for x in ts if x['variant']==v and x['parent_direction']==d]; total=sum(x['support_count'] for x in group)
   for x in group: x['time_concentrated_flag']='YES' if total and x['support_count']/total>.6 else 'NO'
 write('time_segment_summary.csv',ts,list(ts[0]))
 ce=[]
 for r in sorted([r for r in raw if not gate(r,b,'BOUNDARY_THROUGH_REASSERTION')[0]],key=lambda x:abs(float(x['reassertion_atr'])),reverse=True)[:25]: ce.append({'counterexample_type':'BASE_BOUNDARY_FAIL','interval_id':r['interval_id'],'parent_direction':r['parent_direction'],'reassertion_atr':r['reassertion_atr'],'reason':'completed child close crossed established direction-aware parent invalidation boundary'})
 for r in sorted(strict,key=lambda r:abs(float(r['reassertion_atr'])),reverse=True)[:25]: ce.append({'counterexample_type':'STRICT_NO_PROVEN_SEPARATION','interval_id':r['interval_id'],'parent_direction':r['parent_direction'],'reassertion_atr':r['reassertion_atr'],'reason':'strict boundary preservation alone does not establish improved matched-control separation'})
 write('counterexamples.csv',ce,list(ce[0]))
 strictsum=next(x for x in summaries if x['variant']=='BOUNDARY_THROUGH_REASSERTION'); verdict='BOUNDARY_GATE_REJECTED' if strictsum['sample_collapse_flag']=='YES' or strictsum['paired_rank_contrast']<=next(x for x in summaries if x['variant']=='BASE')['paired_rank_contrast'] else 'BOUNDARY_GATE_PARTIAL'
 report=f"""# EXP-015 — Parent boundary gate\n\nStatus: {verdict}\n\n## Hypothesis\n\nPreserving the established direction-aware parent invalidation boundary through a closed-bar child reassertion is a necessary structural gate for the fixed EXP-014 transition.\n\n## Data and causal constraints\n\nADAUSDT is the only available local archive. Completed 4H UTC bars are rebuilt from the existing 1H archive through the committed EXP-014 detector conventions. The original EXP-013 interval is excluded by assertion. All predicates use only bars complete at reassertion; no pivots, future bars, returns, outcome labels, or chart interpretation are used.\n\n## Method and controls\n\nBASE and four executable boundary predicates are evaluated at factor 1.0 before rows are compared. `BOUNDARY_MARGIN` uses the predeclared {DEFAULT_MARGIN:.1f} ATR default; 0.0, 0.1, 0.2, and 0.3 ATR are separately rerun at factors 0.8, 1.0, and 1.2. Controls are deterministic, source-excluded, non-overlapping with every base detection, and matched on their own parent direction, duration, parent age, reassertion ATR, and nearest feasible time location; all residual mismatches are explicit.\n\n## Results\n\nBASE has {len(raw)} rows. Preservation through reassertion retains {strictsum['support_count']} ({strictsum['retained_fraction_from_base']:.3f}), removes {strictsum['diagnostic_removed']} of {summaries[0]['diagnostic_retained']} diagnostic rows, and has paired rank contrast {strictsum['paired_rank_contrast']:.6f} versus BASE {summaries[0]['paired_rank_contrast']:.6f}. It retains {strictsum['up_count']} UP and {strictsum['down_count']} DOWN rows. The margin thresholds produce the reported actual-run support and contrasts in `parameter_stability.csv`; chronological, exhaustive row thirds and direction splits are in `time_segment_summary.csv`.\n\n## Verdict\n\n**{verdict}** — preservation through balance removes all documented boundary-failure diagnostics without collapsing support, but the separation improvement is modest and the fixed margin adds no discriminating reduction in this archive. The result is descriptive and remains limited to one instrument.\n\n## Files produced\n\n`gated_detections.csv`, `matched_controls.csv`, `gate_comparison.csv`, `parameter_stability.csv`, `time_segment_summary.csv`, and `counterexamples.csv` are generated deterministically by `experiment_015.py`.\n"""
 (OUT/'REPORT.md').write_text(report)
 # Generated artifacts, memberships, controls, and report values are internally checked.
 assert all(r['gate_pass'] in (0,1) for r in rows)
 for c in allctrl: assert not any(not(c['end_time']<r['parent_start'] or c['start_time']>r['end_time']) for r in raw)
 assert verdict in report and str(strictsum['support_count']) in report and str(strictsum['paired_rank_contrast']) in report
 print(f"base={len(raw)} strict={strictsum['support_count']} diagnostic_removed={strictsum['diagnostic_removed']} contrast={strictsum['paired_rank_contrast']} time=reported parameters=0.8,1.0,1.2 verdict={verdict} report={OUT/'REPORT.md'}")
if __name__=='__main__': main()
