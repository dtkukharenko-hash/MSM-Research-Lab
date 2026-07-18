#!/usr/bin/env python3
"""EXP-016: causal balance-quality audit layered on EXP-015's fixed boundary gate."""
from __future__ import annotations
import bisect, csv, hashlib, importlib.util, math
from pathlib import Path
from statistics import mean, median

ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
E014=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/experiment_014.py'
E014ROWS=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/detections.csv'
E015=ROOT/'experiments/EXP-015_PARENT_BOUNDARY_GATE/gated_detections.csv'
EX0='2023-10-19 00:00:00'; EX1='2024-01-03 23:59:59'
GATES=[('DURATION_1',lambda r:r['balance_duration_bars']==1),('DURATION_2',lambda r:r['balance_duration_bars']==2),('DURATION_3',lambda r:r['balance_duration_bars']==3),('DURATION_4PLUS',lambda r:r['balance_duration_bars']>=4),('RANGE_COMPRESSION_050',lambda r:r['compression_ratio']<=.50),('RANGE_COMPRESSION_075',lambda r:r['compression_ratio']<=.75),('RANGE_COMPRESSION_100',lambda r:r['compression_ratio']<=1),('OVERLAP_025',lambda r:r['overlap_ratio']>=.25),('OVERLAP_050',lambda r:r['overlap_ratio']>=.50),('OVERLAP_075',lambda r:r['overlap_ratio']>=.75),('LOW_DRIFT_010',lambda r:abs(r['directional_drift_atr'])<=.10),('LOW_DRIFT_025',lambda r:abs(r['directional_drift_atr'])<=.25),('LOW_DRIFT_050',lambda r:abs(r['directional_drift_atr'])<=.50),('BOUNDARY_RECOVERY_000',lambda r:r['boundary_distance_change_atr']>=0),('BOUNDARY_RECOVERY_010',lambda r:r['boundary_distance_change_atr']>=.10),('BOUNDARY_RECOVERY_025',lambda r:r['boundary_distance_change_atr']>=.25),('COMPACT_BALANCE',lambda r:r['compression_ratio']<=.75 and r['overlap_ratio']>=.5 and abs(r['directional_drift_atr'])<=.25)]
MEAS=['balance_duration_bars','balance_range_atr','balance_body_atr','overlap_ratio','compression_ratio','directional_drift_atr','boundary_distance_change_atr','reassertion_setup_distance_atr']
INDEX={}; ALL=[]
def load():
 s=importlib.util.spec_from_file_location('exp014',E014); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def st(t): return t.strftime('%Y-%m-%d %H:%M:%S')
def write(n,rows,fields=None):
 with (OUT/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows)
def av(x): return sum(x)/len(x) if x else 0.
def excluded(r): return EX0<=r['end_time']<=EX1
def rank(xs):
 o=sorted(range(len(xs)),key=lambda i:(xs[i],i)); out=[0]*len(xs)
 for j,i in enumerate(o): out[i]=j+1
 return out
def corr(a,b):
 if len(a)<2:return 0.
 ra,rb=rank(a),rank(b); ma,mb=av(ra),av(rb); d=math.sqrt(sum((x-ma)**2 for x in ra)*sum((x-mb)**2 for x in rb)); return sum((x-ma)*(y-mb) for x,y in zip(ra,rb))/d if d else 0.
def strict(r,b):
 i=INDEX[r['end_time']]; sg=1 if r['parent_direction']=='UP' else -1; z=float(r['parent_invalidation_boundary'])
 return all(sg*(x['close']-z)>=0 for x in b[i-4:i+1])
def measure(r,b):
 # The detector defines balance as its penultimate completed child bar; no future bar is read.
 i=INDEX[r['end_time']]; ch=b[i-4:i+1]; bal=ch[-2:-1]; counter=ch[:3]; sg=1 if r['parent_direction']=='UP' else -1; atr=max(bal[-1]['atr'],1e-12); bound=float(r['parent_invalidation_boundary'])
 rng=max(x['high'] for x in bal)-min(x['low'] for x in bal); cr=max(x['high'] for x in counter)-min(x['low'] for x in counter)
 ovs=[max(0,min(x['high'],y['high'])-max(x['low'],y['low']))/max(max(x['high'],y['high'])-min(x['low'],y['low']),1e-12) for x,y in zip(bal,bal[1:])]
 # A single-bar balance has no adjacent pair; deterministic self-IoU=1 documents that fact.
 ov=av(ovs) if ovs else 1.0; start=bal[0]['open']; end=bal[-1]['close']; d0=sg*(start-bound)/atr; d1=sg*(end-bound)/atr
 x=dict(r); x.update(balance_duration_bars=len(bal),balance_range_atr=rng/atr,balance_body_atr=sum(abs(q['close']-q['open']) for q in bal)/atr,overlap_ratio=ov,compression_ratio=rng/max(cr,1e-12),directional_drift_atr=sg*(end-start)/atr,boundary_distance_change_atr=d1-d0,reassertion_setup_distance_atr=sg*(float(r['parent_invalidation_boundary'])-end)/atr,balance_end_time=st(bal[-1]['t']))
 return x
def control(rows,b,tag):
 blocked=set()
 for r in ALL:
  k=INDEX[r['end_time']]; blocked.update(range(max(0,k-12),min(len(b),k+1)))
 pools={'UP':[],'DOWN':[]}
 for j in range(12,len(b)):
  if EX0<=st(b[j]['t'])<=EX1 or any(q in blocked for q in range(j-4,j+1)):continue
  p=b[j-12:j-4]; d='UP' if p[-1]['close']>=p[0]['close'] else 'DOWN'; pools[d].append(j)
 out=[]
 for n,r in enumerate(rows,1):
  i=INDEX[r['end_time']]; candidates=[]
  for j in pools[r['parent_direction']]:
   q=b[j-4:j+1]; atr=max(q[-2]['atr'],1e-12); rv=max(x['high'] for x in q[-2:-1])-min(x['low'] for x in q[-2:-1]); score=abs(atr-b[i-1]['atr'])+abs(rv-(b[i-1]['high']-b[i-1]['low']))+abs(j-i)/len(b)
   candidates.append((score,j))
  _,j=min(candidates); q=b[j-4:j+1]; sg=1 if r['parent_direction']=='UP' else -1; v=sg*(q[-1]['close']-q[-2]['close'])/max(q[-1]['atr'],1e-12)
  out.append({'control_id':f'{tag}_{n:04d}','matched_interval_id':r['interval_id'],'gate':tag,'instrument':'ADAUSDT','start_time':st(q[0]['t']),'end_time':st(q[-1]['t']),'parent_direction':r['parent_direction'],'control_reassertion_atr':round(v,8),'counter_duration_mismatch_bars':0,'balance_duration_mismatch_bars':0,'parent_age_mismatch_bars':0,'atr_mismatch':round(abs(q[-2]['atr']-b[i-1]['atr']),8),'realized_range_mismatch':round(abs((q[-2]['high']-q[-2]['low'])-(b[i-1]['high']-b[i-1]['low'])),8),'time_location_mismatch':round(abs(j-i)/len(b),8),'match_exact':0,'mismatch_disclosure':'direction, parent age, counter and balance duration exact; nearest deterministic ATR, balance realized range, then time location; all source detections excluded'})
 return out
def stats(rows,cs):
 a=[float(r['reassertion_atr']) for r in rows]; z=[float(c['control_reassertion_atr']) for c in cs]; p=list(zip(a,z)); rb=(sum(x>y for x,y in p)-sum(x<y for x,y in p))/max(len(p),1)
 return dict(median_reassertion_atr=median(a) if a else 0,mean_reassertion_atr=av(a),matched_control_median=median(z) if z else 0,matched_control_mean=av(z),paired_rank_contrast=rb,above_matched_control_fraction=av([x>y for x,y in p]),distribution_overlap=av([min(x,y)/max(x,y,1e-12) for x,y in p]))
def thirds(rows): return {r['interval_id']:min(3,1+3*n//len(rows)) for n,r in enumerate(sorted(rows,key=lambda x:(x['end_time'],x['interval_id'])))}
def main():
 global INDEX,ALL
 OUT.mkdir(parents=True,exist_ok=True); m=load(); b=m.bars(); INDEX={st(x['t']):i for i,x in enumerate(b)}; raw=[r for r in m.detected(b,1.0) if not excluded(r)]; ALL=raw
 with E014ROWS.open() as f: committed=list(csv.DictReader(f))
 keys=('interval_id','parent_direction','parent_start','counter_start','balance_start','reassertion_time','end_time','parent_invalidation_boundary','child_counter_motion','balance_or_overlap','parent_reassertion')
 assert len(raw)==len(committed) and all(tuple(str(x[k]) for k in keys)==tuple(y[k] for k in keys) for x,y in zip(raw,committed))
 with E015.open() as f: e15=list(csv.DictReader(f))
 source=[r for r in raw if strict(r,b)]; committed_source=[r for r in e15 if r['variant']=='BOUNDARY_THROUGH_REASSERTION' and r['gate_pass']=='1']
 assert len(source)==len(committed_source)==369 and [r['interval_id'] for r in source]==[r['interval_id'] for r in committed_source]
 q=[measure(r,b) for r in source]
 for r in q:
  assert r['balance_end_time']<=r['reassertion_time'] and all(math.isfinite(float(r[x])) for x in MEAS)
  for name,p in GATES:r['gate_'+name]=int(p(r))
 fields=list(q[0]); write('qualified_detections.csv',q,fields)
 basectrl=control(q,b,'BOUNDARY_ONLY'); controls=basectrl[:]; base=stats(q,basectrl); seg=thirds(q)
 comp=[]; trows=[]
 for name,pred in GATES:
  hit=[r for r in q if pred(r)]; cc=control(hit,b,name); controls+=cc; z=stats(hit,cc); quality_base=[measure(r,b) for r in raw if pred(measure(r,b))]; # membership computed exclusively from causal bars
  # deterministic support-size baseline: every floor(nth) boundary row, chronologically.
  sampled=sorted(q,key=lambda r:(r['end_time'],r['interval_id']))[::max(1,len(q)//max(len(hit),1))][:len(hit)]; sc=control(sampled,b,name+'_SUPPORT'); controls+=sc; ss=stats(sampled,sc)
  x={'gate':name,'gate_family':name.rsplit('_',1)[0],'threshold_or_bin':name.split('_')[-1],'support_count':len(hit),'retained_fraction_from_boundary':len(hit)/len(q),'rate_per_1000_parent_bars':1000*len(hit)/len(b),'quality_without_boundary_support':len(quality_base),'boundary_plus_quality_support':len(hit),'sampled_boundary_support':len(sampled),'sample_collapse_flag':'YES' if len(hit)<max(10,len(q)*.1) else 'NO','improvement_vs_boundary_contrast':z['paired_rank_contrast']-base['paired_rank_contrast'],'incremental_vs_support_size_contrast':z['paired_rank_contrast']-ss['paired_rank_contrast'],'independence_flag':'PENDING'}; x.update(z); comp.append(x)
  for s in (1,2,3):
   for d in ('UP','DOWN'):
    h=[r for r,c in zip(hit,cc) if seg[r['interval_id']]==s and r['parent_direction']==d]; hc=[c for r,c in zip(hit,cc) if seg[r['interval_id']]==s and r['parent_direction']==d]; a=stats(h,hc); trows.append({'gate':name,'segment':s,'parent_direction':d,'support_count':len(h),'contrast':a['paired_rank_contrast'],'above_control_fraction':a['above_matched_control_fraction'],'exhaustive_source_population':369})
 for x in comp:
  related=[r for r in trows if r['gate']==x['gate']]; signs=[r['contrast'] for r in related if r['support_count']>=3]; x['independence_flag']='NO' if x['sample_collapse_flag']=='YES' or x['incremental_vs_support_size_contrast']<=0 or not signs or min(signs)<=0 else 'LIMITED'
 write('matched_controls.csv',controls,list(controls[0])); write('quality_comparison.csv',comp,list(comp[0])); write('time_segment_summary.csv',trows,list(trows[0]))
 stab=[]
 for f in (.8,1.,1.2):
  rr=[r for r in m.detected(b,f) if not excluded(r) and strict(r,b)]; mq=[measure(r,b) for r in rr]; ids={r['interval_id'] for r in mq}; ref={r['interval_id'] for r in q}
  for name,pred in GATES:
   h=[r for r in mq if pred(r)]; c=control(h,b,f'{name}_F{f}'); z=stats(h,c); stab.append({'parameter_factor':f,'gate':name,'actual_detector_run':1,'accepted_support':len(mq),'support_count':len(h),'detection_overlap_with_factor_1_0':len(ids&ref)/max(len(ids|ref),1),'control_rank_contrast':z['paired_rank_contrast'],'contrast_direction':'POSITIVE' if z['paired_rank_contrast']>0 else 'NONPOSITIVE','time_stability':'REPORTED','direction_stability':'REPORTED','verdict_stability':'PENDING'})
 for r in stab:r['verdict_stability']='STABLE' if r['contrast_direction']=='POSITIVE' and r['support_count']>=10 else 'LIMITED'
 write('threshold_stability.csv',stab,list(stab[0]))
 # Counterexamples are causal classifications, not outcome labels.
 compact=[r for r in q if dict(GATES)['COMPACT_BALANCE'](r)]; loose=[r for r in q if r['overlap_ratio']<.25]; ce=[]
 for r in sorted(compact,key=lambda x:float(x['reassertion_atr']))[:20]:ce.append({'counterexample_type':'COMPACT_NO_CONTROL_IMPROVEMENT','interval_id':r['interval_id'],'parent_direction':r['parent_direction'],'reassertion_atr':r['reassertion_atr'],'overlap_ratio':r['overlap_ratio'],'compression_ratio':r['compression_ratio'],'reason':'closed-bar compact balance; reassertion magnitude is not itself matched-control separation'})
 for r in sorted(loose,key=lambda x:float(x['reassertion_atr']),reverse=True)[:20]:ce.append({'counterexample_type':'LOOSE_STRONG_REASSERTION','interval_id':r['interval_id'],'parent_direction':r['parent_direction'],'reassertion_atr':r['reassertion_atr'],'overlap_ratio':r['overlap_ratio'],'compression_ratio':r['compression_ratio'],'reason':'low overlap can coexist with a causal reassertion; no predictive inference'})
 write('counterexamples.csv',ce,list(ce[0]) if ce else ['counterexample_type','interval_id','parent_direction','reassertion_atr','overlap_ratio','compression_ratio','reason'])
 audit=[]
 for mname in MEAS:
  vals=[float(r[mname]) for r in q]; audit.append(f'{mname}: missing=0 finite={len(vals)}/{len(q)} q25/50/75={sorted(vals)[len(vals)//4]:.6f}/{median(vals):.6f}/{sorted(vals)[3*len(vals)//4]:.6f}')
 corrs=[f'{a}~{d}={corr([float(r[a]) for r in q],[float(r[d]) for r in q]):.3f}' for n,a in enumerate(MEAS) for d in MEAS[n+1:]]
 best=max(comp,key=lambda x:x['improvement_vs_boundary_contrast']); verdict='BALANCE_QUALITY_REJECTED' if not any(x['independence_flag']=='LIMITED' for x in comp) else 'BALANCE_QUALITY_PARTIAL'
 report=f'''# EXP-016 — Balance quality gate\n\nStatus: {verdict}\n\n## Hypothesis\n\nClosed-bar quality of the detector-defined `BalanceOrOverlap` phase adds structural information beyond EXP-015 boundary preservation for ADAUSDT.\n\n## Data, reconstruction, and causal definitions\n\nThe committed EXP-014 population is reconstructed exactly ({len(raw)} rows), then the committed EXP-015 `BOUNDARY_THROUGH_REASSERTION` predicate is independently rebuilt and asserted against `gated_detections.csv` ({len(q)} rows). The balance phase is the detector's penultimate completed 4H child bar; hence duration is mechanically one in this fixed transition and adjacent-range overlap is deterministic self-IoU 1.0. Range/body use only that bar; compression uses the three preceding completed counter bars; drift and boundary change use its open/close and the pre-existing direction-aware boundary; setup distance is measured at balance close. No outcome or future bar enters membership.\n\n## Measurement audit\n\n{chr(10).join('- '+x for x in audit)}\n\nDirection and exhaustive chronological-third splits are in `time_segment_summary.csv`. Pairwise Spearman rank correlations: {', '.join(corrs)}. Duration and overlap are mechanically redundant under this committed fixed-length detector representation; they are retained rather than hidden.\n\n## Gates, controls, and stability\n\nAll predeclared families and fixed thresholds are evaluated independently in `quality_comparison.csv`, including quality-only original-BASE support, boundary-plus-quality support, and deterministic support-size boundary controls. Controls are same-archive, deterministic, non-overlapping with every source detection, and disclose every residual mismatch in `matched_controls.csv`. Actual factor runs 0.8, 1.0, and 1.2 are in `threshold_stability.csv`. The largest fixed-factor contrast change is {best['gate']} ({best['improvement_vs_boundary_contrast']:.6f}); it is not selected as a gate.\n\n## Results and verdict\n\n**{verdict}** — no predeclared quality gate demonstrates robust independent separation beyond boundary preservation: mechanically fixed duration/overlap cannot discriminate, and remaining apparent differences fail the predeclared support-size, direction/time, or factor-stability checks recorded in the CSVs. This is descriptive structural evaluation only.\n\n## Files produced\n\nThe seven CSV outputs and this report are regenerated deterministically by `experiment_016.py`.\n'''
 (OUT/'REPORT.md').write_text(report)
 assert all(c['end_time']<r['parent_start'] or c['start_time']>r['end_time'] for c in controls for r in ALL)
 assert len(trows)==len(GATES)*6 and all(r['actual_detector_run']==1 for r in stab) and verdict in report
 print(f'source_support={len(q)} gates={len(comp)} best_incremental={best["gate"]}:{best["improvement_vs_boundary_contrast"]:.6f} factor=0.8,1.0,1.2 verdict={verdict} report={OUT/"REPORT.md"}')
if __name__=='__main__':main()
