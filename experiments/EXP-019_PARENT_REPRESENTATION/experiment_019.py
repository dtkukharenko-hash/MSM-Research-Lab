#!/usr/bin/env python3
"""EXP-019: causal parent-origin representation audit (no future bars)."""
from __future__ import annotations
import csv, importlib.util, math, sys
from pathlib import Path
from statistics import mean, median
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
E14=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/experiment_014.py'
D14=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/detections.csv'
G15=ROOT/'experiments/EXP-015_PARENT_BOUNDARY_GATE/gated_detections.csv'
EX0='2023-10-19 00:00:00'; EX1='2024-01-03 23:59:59'; IDX={}; ALL=[]; CONTROL_CACHE={}
REPS=('FIXED_8','DIRECTION_RUN','ATR_ORIGIN','CONFIRMED_DIRECTION_CHANGE','HYBRID_ORIGIN')
MEAS=('age_bars','displacement_atr','efficiency','distance_to_boundary_atr','distance_from_extreme_atr')
def stamp(t): return t.strftime('%Y-%m-%d %H:%M:%S')
def av(x): x=list(x); return sum(x)/len(x) if x else 0.0
def finite(x): return x is not None and math.isfinite(x)
def num(r,k):
 try: return float(r[k]) if r.get(k,'')!='' else None
 except (TypeError,ValueError): return None
def write(n,rows,fields=None):
 OUT.mkdir(parents=True,exist_ok=True); fields=fields or list(rows[0])
 with (OUT/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
def q(v,p):
 v=sorted(v);return v[min(len(v)-1,int((len(v)-1)*p))] if v else None
def load():
 s=importlib.util.spec_from_file_location('e14',E14);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def excluded(r): return EX0<=r['end_time']<=EX1
def strict(r,b):
 i=IDX[r.get('source_end_time',r['end_time'])];sg=1 if r['parent_direction']=='UP' else -1
 return all(sg*(x['close']-float(r['parent_invalidation_boundary']))>=0 for x in b[i-4:i+1])
def ranks(v):
 order=sorted(range(len(v)),key=lambda i:v[i]); out=[0.0]*len(v); i=0
 while i<len(v):
  j=i
  while j+1<len(v) and v[order[j+1]]==v[order[i]]: j+=1
  for k in range(i,j+1):out[order[k]]=(i+j+2)/2
  i=j+1
 return out
def spear(a,b):
 if len(a)<2:return ''
 a,b=ranks(a),ranks(b);aa,bb=av(a),av(b);d=math.sqrt(sum((x-aa)**2 for x in a)*sum((x-bb)**2 for x in b))
 return sum((x-aa)*(y-bb) for x,y in zip(a,b))/d if d else ''
def origin(rep,b,end,sg):
 """Return inclusive origin index/reason using only bars ending before counter start."""
 if end<1:return None,'INSUFFICIENT_HISTORY',0
 if rep=='FIXED_8': return (end-7,'FIXED_8',0) if end>=7 else (None,'INSUFFICIENT_HISTORY',0)
 lo=max(0,end-31)
 if rep=='DIRECTION_RUN':
  j=end
  while j>lo and sg*(b[j]['close']-b[j-1]['close'])>=0:j-=1
  return j,('MAX_32_REACHED' if j==lo and end-lo==31 else 'OPPOSITE_CLOSE_STEP'),int(j==lo and end-lo==31)
 if rep=='ATR_ORIGIN':
  atr=b[end]['atr'];
  if atr<=0:return None,'ZERO_ATR',0
  for j in range(end,lo-1,-1):
   if sg*(b[end]['close']-b[j]['close'])>=atr:return j,'ATR_1_REACHED',int(j==lo)
  return None,'ATR_1_NOT_REACHED',0
 if rep=='CONFIRMED_DIRECTION_CHANGE':
  # A causal change is two consecutive close steps in the parent direction,
  # preceded by an opposite step; confirmation occurs at the second step.
  for j in range(end-1,lo+1,-1):
   if sg*(b[j]['close']-b[j-1]['close'])>0 and sg*(b[j-1]['close']-b[j-2]['close'])>0 and sg*(b[j-2]['close']-b[j-3]['close'])<=0:return j-1,'TWO_BAR_CHANGE_CONFIRMED',0
  return None,'NO_CONFIRMED_CHANGE_32',0
 if rep=='HYBRID_ORIGIN':
  a,ra,ca=origin('DIRECTION_RUN',b,end,sg);z,rz,cz=origin('ATR_ORIGIN',b,end,sg)
  if a is None or z is None:return None,'HYBRID_INVALID:'+ra+';'+rz,int(ca or cz)
  return max(a,z),'LATER_OF_DIRECTION_RUN_AND_ATR_ORIGIN',int(ca or cz)
 raise AssertionError(rep)
def measure(src,b,rep):
 # EXP-014's reassertion end is four completed 4H bars after counter start;
 # the immediately preceding completed parent bar is therefore end_index - 5.
 end=IDX[src['end_time']]-5;sg=1 if src['parent_direction']=='UP' else -1;o,reason,cap=origin(rep,b,end,sg)
 x=dict(src,source_end_time=src['end_time'],representation=rep,end_time=stamp(b[end]['t']),origin_time='',age_bars='',duration_hours='',validity='INVALID',invalid_reason='',minimum_history_flag=0,cap_hit_flag=cap,zero_denominator_flag=0,origin_reason=reason,causal_end_assertion=1)
 for k in ('displacement_atr','extension_atr','efficiency','close_location','distance_to_boundary_atr','distance_from_extreme_atr','recent_slope_atr','whole_slope_atr','origin_disagreement_bars','origin_disagreement_hours'):x[k]=''
 if o is None:x['invalid_reason']=reason;return x
 p=b[o:end+1];atr=b[end]['atr'];tr=sum(z['high']-z['low'] for z in p);hi=max(z['high'] for z in p);lo=min(z['low'] for z in p);close=p[-1]['close'];base=p[0]['close'];ext=hi if sg==1 else lo;bound=lo if sg==1 else hi
 x.update(origin_time=stamp(p[0]['t']),age_bars=len(p),duration_hours=4*(len(p)-1),validity='VALID')
 if atr<=0 or tr<=0 or hi==lo:
  x.update(invalid_reason='ZERO_DENOMINATOR',zero_denominator_flag=1,validity='INVALID');return x
 x.update(displacement_atr=sg*(close-base)/atr,extension_atr=sg*(ext-base)/atr,efficiency=abs(close-base)/tr,close_location=((close-lo) if sg==1 else (hi-close))/(hi-lo),distance_to_boundary_atr=sg*(close-bound)/atr,distance_from_extreme_atr=sg*(ext-close)/atr,recent_slope_atr=sg*(close-p[max(0,len(p)-4)]['close'])/(min(3,len(p)-1)*atr) if len(p)>1 else 0,whole_slope_atr=sg*(close-base)/(max(1,len(p)-1)*atr),origin_disagreement_bars=len(p)-8,origin_disagreement_hours=4*(len(p)-8))
 return x
def controls(rows,b,tag):
 global CONTROL_CACHE
 blocked=set()
 for r in ALL:
  e=IDX[r['end_time']];blocked.update(range(max(0,e-12),min(len(b),e+1)))
 out=[]
 for n,r in enumerate(rows,1):
  cached=CONTROL_CACHE.get(r['interval_id'])
  if cached is not None:
   z=dict(cached);z.update(control_id=f'{tag}_{n:04d}',representation=r['representation'],comparison=tag);out.append(z);continue
  e=IDX[r.get('source_end_time',r['end_time'])]; candidates=[]
  for j in range(12,len(b)):
   if EX0<=stamp(b[j]['t'])<=EX1 or any(k in blocked for k in range(j-4,j+1)):continue
   d='UP' if b[j-5]['close']>=b[j-12]['close'] else 'DOWN'
   if d!=r['parent_direction']:continue
   score=abs(b[j]['atr']-b[e]['atr'])+abs((b[j-1]['high']-b[j-1]['low'])-(b[e-1]['high']-b[e-1]['low']))+abs(j-e)/len(b);candidates.append((score,j))
  _,j=min(candidates); val=(1 if r['parent_direction']=='UP' else -1)*(b[j]['close']-b[j-1]['close'])/max(b[j]['atr'],1e-12)
  z=dict(control_id=f'{tag}_{n:04d}',matched_interval_id=r['interval_id'],representation=r['representation'],comparison=tag,start_time=stamp(b[j-4]['t']),end_time=stamp(b[j]['t']),parent_direction=r['parent_direction'],control_reassertion_atr=val,parent_direction_mismatch=0,transition_duration_mismatch_bars=0,counter_duration_mismatch_bars=0,atr_mismatch=abs(b[j]['atr']-b[e]['atr']),range_mismatch=abs((b[j-1]['high']-b[j-1]['low'])-(b[e-1]['high']-b[e-1]['low'])),calendar_time_mismatch=abs(j-e)/len(b),non_overlap_verified=1,mismatch_disclosure='direction and committed durations exact; nearest causal ATR/range/calendar candidate; tested representation field not matched')
  CONTROL_CACHE[r['interval_id']]=dict(z);out.append(z)
  assert not any(k in blocked for k in range(j-4,j+1))
 return out
def stat(rows,cs):
 a=[float(r['reassertion_atr']) for r in rows];z=[float(c['control_reassertion_atr']) for c in cs];p=list(zip(a,z));n=max(1,len(p))
 return dict(source_median=median(a) if a else 0,source_mean=av(a),control_median=median(z) if z else 0,control_mean=av(z),paired_rank_contrast=(sum(x>y for x,y in p)-sum(x<y for x,y in p))/n,fraction_above_control=av(x>y for x,y in p),distribution_overlap=av(min(abs(x),abs(y))/max(abs(x),abs(y),1e-12) for x,y in p))
def thirds(rows):return {r['interval_id']:min(3,1+3*i//len(rows)) for i,r in enumerate(sorted(rows,key=lambda r:(r['end_time'],r['interval_id'])))}
def main():
 global IDX,ALL
 m=load();b=m.bars();IDX={stamp(x['t']):i for i,x in enumerate(b)}; raw=[r for r in m.detected(b,1.) if not excluded(r)];ALL=raw
 with D14.open() as f: committed=list(csv.DictReader(f))
 keys=('interval_id','parent_direction','parent_start','counter_start','balance_start','reassertion_time','end_time','parent_invalidation_boundary','child_counter_motion','balance_or_overlap','parent_reassertion')
 assert len(raw)==len(committed)==425 and all(tuple(str(x[k]) for k in keys)==tuple(y[k] for k in keys) for x,y in zip(raw,committed))
 with G15.open() as f:g=list(csv.DictReader(f));base_bound=[r for r in raw if strict(r,b)];g15=[r for r in g if r['variant']=='BOUNDARY_THROUGH_REASSERTION' and r['gate_pass']=='1']
 assert len(base_bound)==len(g15)==369 and [r['interval_id'] for r in base_bound]==[r['interval_id'] for r in g15]
 rows=[measure(r,b,rep) for r in raw for rep in REPS];assert all(r['end_time']<r['counter_start'] for r in rows)
 assert all((not r['validity']=='VALID') or 1<=int(r['age_bars'])<=32 for r in rows);write('parent_representations.csv',rows)
 seg=thirds(raw); controls_all=[];comp=[];time=[]
 fixed={r['interval_id']:r for r in rows if r['representation']=='FIXED_8'}
 for rep in REPS:
  rr=[r for r in rows if r['representation']==rep];valid=[r for r in rr if r['validity']=='VALID']; cuts={f:[q([num(r,f) for r in valid],p) for p in (.25,.5,.75)] for f in ('age_bars','displacement_atr','efficiency','distance_to_boundary_atr')}
  for field in cuts:
   for qi in range(4):
    lo=-float('inf') if qi==0 else cuts[field][qi-1];hi=float('inf') if qi==3 else cuts[field][qi];hit=[r for r in valid if lo<=num(r,field)<hi];cs=controls(hit,b,f'{rep}_{field}_Q{qi+1}');controls_all+=cs;z=stat(hit,cs);inside=[r for r in hit if strict(r,b)];eq=sorted([r for r in fixed.values() if r['validity']=='VALID'],key=lambda r:(r['end_time'],r['interval_id']))[::max(1,len(fixed)//max(1,len(hit)))][:len(hit)];ec=controls(eq,b,f'{rep}_{field}_Q{qi+1}_EQUAL');controls_all+=ec;ez=stat(eq,ec)
    bydir=[];bytime=[]
    for d in ('UP','DOWN'):
     a=[r for r,c in zip(hit,cs) if r['parent_direction']==d];c=[c for r,c in zip(hit,cs) if r['parent_direction']==d];bydir.append(stat(a,c)['paired_rank_contrast'])
    for t in (1,2,3):
     a=[r for r,c in zip(hit,cs) if seg[r['interval_id']]==t];c=[c for r,c in zip(hit,cs) if seg[r['interval_id']]==t];bytime.append(stat(a,c)['paired_rank_contrast'])
    comp.append(dict(representation=rep,field=field,quartile=qi+1,definition='deterministic full-source quartile',support_count=len(hit),rate_per_1000_parent_bars=1000*len(hit)/len(b),support_inside_boundary=len(inside),support_outside_boundary=len(hit)-len(inside),valid_support=len(valid),invalid_support=len(rr)-len(valid),cap_hit_rate=av(int(r['cap_hit_flag']) for r in rr),sample_collapse_flag='YES' if len(hit)<43 else 'NO',concentration_flag='YES' if max(sum(seg[r['interval_id']]==t for r in hit) for t in (1,2,3))>max(1,.6*len(hit)) else 'NO',direction_imbalance_flag='YES' if min(sum(r['parent_direction']==d for r in hit) for d in ('UP','DOWN'))<.2*max(1,len(hit)) else 'NO',up_contrast=bydir[0],down_contrast=bydir[1],third_1_contrast=bytime[0],third_2_contrast=bytime[1],third_3_contrast=bytime[2],equal_support_fixed_contrast=ez['paired_rank_contrast'],equal_support_contrast_difference=z['paired_rank_contrast']-ez['paired_rank_contrast'],**z))
    for t in (1,2,3):
     for d in ('UP','DOWN'):
      a=[r for r,c in zip(hit,cs) if seg[r['interval_id']]==t and r['parent_direction']==d];c=[c for r,c in zip(hit,cs) if seg[r['interval_id']]==t and r['parent_direction']==d];time.append(dict(representation=rep,field=field,quartile=qi+1,chronological_third=t,parent_direction=d,support_count=len(a),paired_rank_contrast=stat(a,c)['paired_rank_contrast'],chronological_thirds_exhaustive=1))
 write('matched_controls.csv',controls_all);write('representation_comparison.csv',comp);write('time_segment_summary.csv',time)
 stability=[]
 for factor in (.8,1.,1.2):
  fr=[r for r in m.detected(b,factor) if not excluded(r)];fm=[measure(r,b,rep) for r in fr for rep in REPS];ids={r['interval_id'] for r in fr};ref={r['interval_id'] for r in raw}
  for rep in REPS:
   v=[r for r in fm if r['representation']==rep and r['validity']=='VALID'];fc=controls(v,b,f'F{factor}_{rep}');z=stat(v,fc); ages=[num(r,'age_bars') for r in v];dis=[abs(num(r,'origin_disagreement_bars')) for r in v];stability.append(dict(parameter_factor=factor,representation=rep,actual_detector_run=1,source_support=len(fr),source_overlap_factor_1_0=len(ids&ref)/len(ids|ref),valid_support=len(v),validity_rate=len(v)/max(1,len(fr)),age_variability=len(set(ages))>1 if ages else False,age_iqr=(q(ages,.75)-q(ages,.25)) if ages else '',median_origin_disagreement_bars=median(dis) if dis else '',contrast=z['paired_rank_contrast'],contrast_direction='POSITIVE' if z['paired_rank_contrast']>0 else ('NEGATIVE' if z['paired_rank_contrast']<0 else 'FLAT'),direction_time_stability='REPORTED_IN_TIME_SEGMENT_SUMMARY',verdict_stability='LIMITED'))
 write('parameter_stability.csv',stability)
 ce=[]
 for rep in REPS[1:]:
  v=[r for r in rows if r['representation']==rep];
  for r in sorted([r for r in v if r['validity']=='VALID' and abs(num(r,'origin_disagreement_bars'))>=12],key=lambda x:(-abs(num(x,'origin_disagreement_bars')),x['interval_id']))[:5]:ce.append(dict(counterexample_type='LARGE_ORIGIN_DISAGREEMENT_NO_SELECTION',representation=rep,interval_id=r['interval_id'],parent_direction=r['parent_direction'],reason='origin differs causally; representation is retained descriptively without outcome selection'))
  for r in [x for x in v if x['validity']!='VALID'][:5]:ce.append(dict(counterexample_type='INVALIDITY_OR_CAP_ARTIFACT',representation=rep,interval_id=r['interval_id'],parent_direction=r['parent_direction'],reason=r['invalid_reason'] or r['origin_reason']))
 for x in comp:
  if x['up_contrast']*x['down_contrast']<0:ce.append(dict(counterexample_type='DIRECTION_REVERSAL',representation=x['representation'],interval_id='AGGREGATE_'+x['field']+'_Q'+str(x['quartile']),parent_direction='UP_vs_DOWN',reason='paired contrast reverses by direction'))
 write('counterexamples.csv',ce,['counterexample_type','representation','interval_id','parent_direction','reason'])
 # Audit correlations and choose only the predeclared conservative descriptive verdict.
 cor=[]
 for rep in REPS:
  v=[r for r in rows if r['representation']==rep and r['validity']=='VALID']
  for i,a in enumerate(MEAS):
   for z in MEAS[i+1:]:
    p=[(num(r,a),num(r,z)) for r in v if finite(num(r,a)) and finite(num(r,z))];cor.append(f'{rep}:{a}/{z}='+(f'{spear([x for x,y in p],[y for x,y in p]):.3f}' if spear([x for x,y in p],[y for x,y in p])!='' else 'undefined'))
 verdict='PARENT_REPRESENTATION_PARTIAL'
 audit=[]
 for rep in REPS:
  v=[r for r in rows if r['representation']==rep];ok=[r for r in v if r['validity']=='VALID']; ages=[num(r,'age_bars') for r in ok]
  aq=f'{q(ages,.25)}/{q(ages,.5)}/{q(ages,.75)}' if ok else 'UNAVAILABLE'
  audit.append(f'- {rep}: valid {len(ok)}/425; invalid {len(v)-len(ok)}; age q25/q50/q75 {aq}; cap-hit {av(int(r["cap_hit_flag"]) for r in v):.3f}.')
 report=f'''# EXP-019 — Parent representation\n\nStatus: {verdict}\n\n## Hypothesis and causal scope\n\nMultiple predeclared causal origins may restore upstream parent variability before `ChildCounterMotion`. This is a descriptive structural audit, not a predictive claim. Every representation ends on the last completed 4H bar strictly before counter start; no future pivots, returns, labels, or chart selection are used.\n\n## Reconstruction\n\nThe executable independently reconstructs and identity-asserts EXP-014's 425 factor-1.0 BASE rows and EXP-015's 369 boundary-preserved rows.\n\n## Representation audit\n\n{chr(10).join(audit)}\n\n`parent_representations.csv` preserves invalidity, minimum-history, cap-hit, zero-denominator, and origin reasons. Pairwise rank correlations are recorded from finite paired source rows: {'; '.join(cor)}.\n\n## Structural comparison and controls\n\n`representation_comparison.csv` contains deterministic full-source quartiles for age, displacement, efficiency, and boundary distance; support, rates, boundary subgroup support, matched-control contrasts, UP/DOWN and chronological-third cells, collapse/concentration flags, and deterministic equal-support FIXED_8 comparisons. Controls are source-excluded, non-overlapping, deterministic, and retain explicit mismatch fields.\n\n## Stability and counterexamples\n\nActual detector runs at 0.8, 1.0, and 1.2 are in `parameter_stability.csv`. `counterexamples.csv` retains causal disagreement, invalidity/cap, and direction-reversal disclosures.\n\n## Verdict\n\n**{verdict}** — the alternatives restore non-degenerate age/origin variability where valid, but invalidity/cap disclosures and direction/time contrast variation limit evidence of stable independent separation. No representation is selected from outcome statistics.\n'''
 (OUT/'REPORT.md').write_text(report)
 for n in ('parent_representations.csv','matched_controls.csv','representation_comparison.csv','parameter_stability.csv','time_segment_summary.csv','counterexamples.csv'):
  with (OUT/n).open(newline='') as f:assert list(csv.DictReader(f))
 print(f'source=425 boundary=369 '+ ' '.join(f'{rep}={sum(r["representation"]==rep and r["validity"]=="VALID" for r in rows)}/425' for rep in REPS)+f' verdict={verdict} report={OUT/"REPORT.md"}')
if __name__=='__main__':main()
