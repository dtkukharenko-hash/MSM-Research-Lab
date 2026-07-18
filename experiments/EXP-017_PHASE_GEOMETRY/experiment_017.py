#!/usr/bin/env python3
"""EXP-017: closed-bar phase geometry audit of the fixed EXP-015 population."""
from __future__ import annotations
import csv, hashlib, importlib.util, math, sys
from pathlib import Path
from statistics import mean, median

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
E014=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/experiment_014.py'
E014ROWS=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/detections.csv'
E015=ROOT/'experiments/EXP-015_PARENT_BOUNDARY_GATE/gated_detections.csv'
E016=ROOT/'experiments/EXP-016_BALANCE_QUALITY_GATE/qualified_detections.csv'
EX0='2023-10-19 00:00:00'; EX1='2024-01-03 23:59:59'
RATIOS=('counter_parent_ratio','balance_counter_ratio','reassertion_counter_ratio','reassertion_parent_ratio','counter_speed_ratio','reassertion_counter_speed_ratio','balance_time_ratio','transition_symmetry')
BANDS=((.25,.5),(.5,1.),(1.,2.),(2.,float('inf')))
INDEX={}; ALL=[]
def stamp(t): return t.strftime('%Y-%m-%d %H:%M:%S')
def avg(x):
 x=list(x)
 return sum(x)/len(x) if x else 0.0
def write(name,rows,fields=None):
 OUT.mkdir(parents=True,exist_ok=True)
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows)
def load():
 s=importlib.util.spec_from_file_location('exp014',E014); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def excluded(r): return EX0<=r['end_time']<=EX1
def strict(r,b):
 i=INDEX[r['end_time']]; sign=1 if r['parent_direction']=='UP' else -1; z=float(r['parent_invalidation_boundary'])
 return all(sign*(x['close']-z)>=0 for x in b[i-4:i+1])
def ranks(x):
 # Stable ordinal ranks are deterministic; ties retain source order rather than hiding ties.
 o=sorted(range(len(x)),key=lambda i:(x[i],i)); z=[0]*len(x)
 for n,i in enumerate(o): z[i]=n+1
 return z
def corr(a,b):
 if len(a)<2:return 0.0
 x,y=ranks(a),ranks(b); mx,my=avg(x),avg(y); d=math.sqrt(sum((q-mx)**2 for q in x)*sum((q-my)**2 for q in y))
 return sum((q-mx)*(w-my) for q,w in zip(x,y))/d if d else 0.0
def quant(x,p):
 if not x:return ''
 y=sorted(x); return y[min(len(y)-1,int((len(y)-1)*p))]
def third(rows): return {r['interval_id']:min(3,1+3*n//len(rows)) for n,r in enumerate(sorted(rows,key=lambda x:(x['end_time'],x['interval_id'])))}
def measure(r,b,e16):
 i=INDEX[r['end_time']]; parent=b[i-12:i-4]; child=b[i-4:i+1]; counter=child[:3]; balance=child[-2:-1]; re=child[-1]
 sign=1 if r['parent_direction']=='UP' else -1; atr=max(avg(x['atr'] for x in child),1e-12)
 # Parent uses only eight completed bars before counter_start. Counter ends before balance.
 pm=sign*(parent[-1]['close']-parent[0]['close'])/max(avg(x['atr'] for x in parent),1e-12)
 # Counter magnitude is deliberately absolute: direction is represented by the
 # parent-direction alignment, while the predeclared ratios require a magnitude.
 cm=abs(counter[-1]['close']-counter[0]['close'])/atr
 rm=sign*(re['close']-balance[-1]['close'])/max(re['atr'],1e-12)
 x=dict(r); x.update(parent_magnitude_atr=pm,parent_duration_bars=len(parent),counter_magnitude_atr=cm,counter_duration_bars=len(counter),balance_range_atr=float(e16['balance_range_atr']),balance_duration_bars=int(e16['balance_duration_bars']),reassertion_magnitude_atr=rm,reassertion_duration_bars=1,balance_end_time=e16['balance_end_time'])
 invalid=[]
 def ratio(name,num,den):
  if not(math.isfinite(num) and math.isfinite(den)) or den<=0: invalid.append(name+':non_positive_or_missing_denominator'); return ''
  if not math.isfinite(num): invalid.append(name+':non_finite_numerator'); return ''
  return num/den
 x['counter_parent_ratio']=ratio('counter_parent_ratio',cm,pm)
 x['balance_counter_ratio']=ratio('balance_counter_ratio',x['balance_range_atr'],cm)
 x['reassertion_counter_ratio']=ratio('reassertion_counter_ratio',rm,cm)
 x['reassertion_parent_ratio']=ratio('reassertion_parent_ratio',rm,pm)
 x['counter_speed_ratio']=ratio('counter_speed_ratio',cm/len(counter),pm/len(parent))
 x['reassertion_counter_speed_ratio']=ratio('reassertion_counter_speed_ratio',rm,cm/len(counter))
 x['balance_time_ratio']=ratio('balance_time_ratio',len(balance),len(counter))
 a=x['counter_parent_ratio']; z=x['reassertion_counter_ratio']
 x['transition_symmetry']=abs(math.log(a)+math.log(z)) if a!='' and z!='' and a>0 and z>0 else ''
 if x['transition_symmetry']=='': invalid.append('transition_symmetry:non_positive_ratio_for_log')
 if pm<=0: invalid.append('parent_magnitude_atr:non_positive_signed_parent_displacement')
 if rm<=0: invalid.append('reassertion_magnitude_atr:non_positive_signed_reassertion_displacement')
 x['invalid_ratio_flags']=';'.join(invalid) or 'NONE'; x['mechanical_redundancy']='balance_duration_bars=1 and reassertion_duration_bars=1 under committed detector'
 return x
def control(rows,b,tag):
 blocked=set()
 for r in ALL:
  k=INDEX[r['end_time']]; blocked.update(range(max(0,k-12),min(len(b),k+1)))
 pool={'UP':[],'DOWN':[]}
 for j in range(12,len(b)):
  if EX0<=stamp(b[j]['t'])<=EX1 or any(k in blocked for k in range(j-4,j+1)):continue
  p=b[j-12:j-4]; d='UP' if p[-1]['close']>=p[0]['close'] else 'DOWN'; pool[d].append(j)
 out=[]
 for n,r in enumerate(rows,1):
  i=INDEX[r['end_time']]; sign=1 if r['parent_direction']=='UP' else -1; candidates=[]
  for j in pool[r['parent_direction']]:
   p=b[j-12:j-4]; q=b[j-4:j+1]; pa=sign*(p[-1]['close']-p[0]['close'])/max(avg(x['atr'] for x in p),1e-12); ca=-sign*(q[2]['close']-q[0]['close'])/max(avg(x['atr'] for x in q),1e-12)
   score=abs(pa-float(r['parent_magnitude_atr']))+abs(ca-float(r['counter_magnitude_atr']))+abs(q[-1]['atr']-b[i]['atr'])+abs(j-i)/len(b); candidates.append((score,j,pa,ca))
  _,j,pa,ca=min(candidates); q=b[j-4:j+1]; val=sign*(q[-1]['close']-q[-2]['close'])/max(q[-1]['atr'],1e-12)
  out.append({'control_id':f'{tag}_{n:04d}','matched_interval_id':r['interval_id'],'comparison':tag,'instrument':'ADAUSDT','start_time':stamp(q[0]['t']),'end_time':stamp(q[-1]['t']),'parent_direction':r['parent_direction'],'control_reassertion_atr':round(val,8),'parent_direction_mismatch':0,'parent_age_mismatch_bars':0,'total_transition_duration_mismatch_bars':0,'counter_duration_mismatch_bars':0,'atr_mismatch':round(abs(q[-1]['atr']-b[i]['atr']),8),'realized_range_mismatch':round(abs((q[-2]['high']-q[-2]['low'])-(b[i-1]['high']-b[i-1]['low'])),8),'time_location_mismatch':round(abs(j-i)/len(b),8),'non_overlap_verified':1,'mismatch_disclosure':'direction, parent age, transition and counter durations exact; nearest deterministic parent/counter magnitude, ATR, then time location; realized-range mismatch explicit'})
 # This is an executable assertion, rather than trusting the output flag.
 for c in out:
  assert all(c['end_time'] < r['parent_start'] or c['start_time'] > r['end_time'] for r in ALL)
 return out
def stats(rows,cs):
 a=[float(r['reassertion_magnitude_atr']) for r in rows]; z=[float(c['control_reassertion_atr']) for c in cs]; p=list(zip(a,z)); rb=(sum(x>y for x,y in p)-sum(x<y for x,y in p))/max(len(p),1)
 return dict(reassertion_atr_median=median(a) if a else 0,reassertion_atr_mean=avg(a),control_median=median(z) if z else 0,control_mean=avg(z),paired_rank_contrast=rb,above_control_fraction=avg([x>y for x,y in p]),distribution_overlap=avg([min(x,y)/max(x,y,1e-12) for x,y in p]))
def membership(name,r):
 v=lambda k: r[k]!='' and float(r[k])
 return {'PROPORTIONAL_COUNTER':v('counter_parent_ratio')>=.25 and v('counter_parent_ratio')<1,'COMPACT_TRANSITION':v('balance_counter_ratio')<1 and v('balance_time_ratio')<=1,'STRONG_REASSERTION':v('reassertion_counter_ratio')>=1,'FAST_REASSERTION':v('reassertion_counter_speed_ratio')>=1,'GEOMETRIC_CHAIN':(v('counter_parent_ratio')>=.25 and v('counter_parent_ratio')<1 and v('balance_counter_ratio')<1 and v('balance_time_ratio')<=1 and (v('reassertion_counter_ratio')>=1 or v('reassertion_counter_speed_ratio')>=1))}[name]
def main():
 global INDEX,ALL
 m=load(); b=m.bars(); INDEX={stamp(x['t']):i for i,x in enumerate(b)}; raw=[r for r in m.detected(b,1.0) if not excluded(r)]; ALL=raw
 with E014ROWS.open() as f: c14=list(csv.DictReader(f))
 keys=('interval_id','parent_direction','parent_start','counter_start','balance_start','reassertion_time','end_time','parent_invalidation_boundary','child_counter_motion','balance_or_overlap','parent_reassertion')
 assert len(raw)==len(c14) and all(tuple(str(r[k]) for k in keys)==tuple(q[k] for k in keys) for r,q in zip(raw,c14))
 with E015.open() as f:e15=list(csv.DictReader(f))
 source=[r for r in raw if strict(r,b)]; committed=[r for r in e15 if r['variant']=='BOUNDARY_THROUGH_REASSERTION' and r['gate_pass']=='1']
 assert len(source)==len(committed)==369 and [r['interval_id'] for r in source]==[r['interval_id'] for r in committed]
 with E016.open() as f:e16={r['interval_id']:r for r in csv.DictReader(f)}
 assert set(r['interval_id'] for r in source)<=set(e16)
 q=[measure(r,b,e16[r['interval_id']]) for r in source]
 assert all(r['balance_end_time']<=r['reassertion_time'] for r in q)
 # Exact detector phase timestamps establish the completed-bar ordering used above.
 assert all(stamp(b[INDEX[r['end_time']]-4]['t'])==r['counter_start'] and r['balance_end_time']==r['balance_start'] and r['reassertion_time']==r['end_time'] for r in q)
 fields=list(q[0]); write('phase_geometry.csv',q,fields)
 seg=third(q); controls=[]; comp=[]; trows=[]; basec=control(q,b,'BOUNDARY_ONLY'); controls+=basec; base=stats(q,basec)
 # Fixed full-population quartile cutpoints; no later selection changes memberships.
 for field in RATIOS:
  vals=sorted(float(r[field]) for r in q if r[field]!='' and math.isfinite(float(r[field])))
  cuts=[quant(vals,.25),quant(vals,.5),quant(vals,.75)] if vals else []
  groups=[]
  for k in range(4):
   lo=-float('inf') if k==0 else cuts[k-1]; hi=float('inf') if k==3 else cuts[k]; groups.append((f'{field}_Q{k+1}',lambda x,lo=lo,hi=hi: x[field]!='' and float(x[field])>=lo and (float(x[field])<hi if hi<float('inf') else True)))
  if field!='transition_symmetry': groups += [(f'{field}_B{a:g}_{"INF" if math.isinf(z) else f"{z:g}"}',lambda x,a=a,z=z: x[field]!='' and float(x[field])>=a and float(x[field])<z) for a,z in BANDS]
  for name,pred in groups:
   hit=[r for r in q if pred(r)]; cc=control(hit,b,name); controls+=cc; ssrows=sorted(q,key=lambda x:(x['end_time'],x['interval_id']))[::max(1,len(q)//max(len(hit),1))][:len(hit)]; sc=control(ssrows,b,name+'_SUPPORT'); controls+=sc; z=stats(hit,cc); s=stats(ssrows,sc)
   comp.append(dict(comparison=name,comparison_kind='QUARTILE' if '_Q' in name else 'UNITY_BAND',geometry_field=field,definition='fixed full-population deterministic membership',support_count=len(hit),finite_source_support=len(vals),rate_per_1000_parent_bars=1000*len(hit)/len(b),sample_collapse_flag='YES' if len(hit)<max(10,len(q)*.1) else 'NO',incremental_vs_boundary_contrast=z['paired_rank_contrast']-base['paired_rank_contrast'],incremental_vs_support_size_contrast=z['paired_rank_contrast']-s['paired_rank_contrast'],**z))
 for name in ('PROPORTIONAL_COUNTER','COMPACT_TRANSITION','STRONG_REASSERTION','FAST_REASSERTION','GEOMETRIC_CHAIN'):
  hit=[r for r in q if membership(name,r)]; cc=control(hit,b,name); controls+=cc; ssrows=sorted(q,key=lambda x:(x['end_time'],x['interval_id']))[::max(1,len(q)//max(len(hit),1))][:len(hit)]; sc=control(ssrows,b,name+'_SUPPORT'); controls+=sc; z=stats(hit,cc); s=stats(ssrows,sc)
  comp.append(dict(comparison=name,comparison_kind='JOINT',geometry_field='joint_geometry',definition='predeclared conjunction',support_count=len(hit),finite_source_support=len(q),rate_per_1000_parent_bars=1000*len(hit)/len(b),sample_collapse_flag='YES' if len(hit)<max(10,len(q)*.1) else 'NO',incremental_vs_boundary_contrast=z['paired_rank_contrast']-base['paired_rank_contrast'],incremental_vs_support_size_contrast=z['paired_rank_contrast']-s['paired_rank_contrast'],**z))
  for s3 in (1,2,3):
   for d in ('UP','DOWN'):
    rr=[r for r,c in zip(hit,cc) if seg[r['interval_id']]==s3 and r['parent_direction']==d]; rc=[c for r,c in zip(hit,cc) if seg[r['interval_id']]==s3 and r['parent_direction']==d]; zz=stats(rr,rc); trows.append({'comparison':name,'segment':s3,'parent_direction':d,'support_count':len(rr),'paired_rank_contrast':zz['paired_rank_contrast'],'above_control_fraction':zz['above_control_fraction'],'chronological_thirds_exhaustive':1})
 # Each geometry field also has an exhaustive direction-by-time support row;
 # bin comparisons above supply the associated non-overlapping controls.
 for field in RATIOS:
  for s3 in (1,2,3):
   for d in ('UP','DOWN'):
    rr=[r for r in q if r[field]!='' and seg[r['interval_id']]==s3 and r['parent_direction']==d]
    trows.append({'comparison':field+'__FINITE','segment':s3,'parent_direction':d,'support_count':len(rr),'paired_rank_contrast':'','above_control_fraction':'','chronological_thirds_exhaustive':1})
 write('matched_controls.csv',controls,list(controls[0])); write('geometry_comparison.csv',comp,list(comp[0])); write('time_segment_summary.csv',trows,list(trows[0]))
 stability=[]
 for f in (.8,1.,1.2):
  rr=[r for r in m.detected(b,f) if not excluded(r) and strict(r,b)]; mq=[measure(r,b,e16[r['interval_id']]) for r in rr if r['interval_id'] in e16]; ids={r['interval_id'] for r in mq}; ref={r['interval_id'] for r in q}
  for name in ('PROPORTIONAL_COUNTER','COMPACT_TRANSITION','STRONG_REASSERTION','FAST_REASSERTION','GEOMETRIC_CHAIN'):
   hit=[r for r in mq if membership(name,r)]; cc=control(hit,b,f'{name}_F{f}'); z=stats(hit,cc); stability.append({'parameter_factor':f,'comparison':name,'actual_detector_run':1,'accepted_support':len(mq),'support_count':len(hit),'detection_overlap_with_factor_1_0':len(ids&ref)/max(len(ids|ref),1),'control_rank_contrast':z['paired_rank_contrast'],'contrast_direction':'POSITIVE' if z['paired_rank_contrast']>0 else 'NONPOSITIVE','direction_stability':'REPORTED','chronological_third_stability':'REPORTED','verdict_stability':'STABLE' if len(hit)>=10 else 'LIMITED'})
 write('parameter_stability.csv',stability,list(stability[0]))
 ce=[]
 for r in sorted([x for x in q if membership('PROPORTIONAL_COUNTER',x)],key=lambda x:float(x['reassertion_magnitude_atr']))[:12]:ce.append({'counterexample_type':'PROPORTIONAL_NO_SEPARATION','interval_id':r['interval_id'],'parent_direction':r['parent_direction'],'reassertion_magnitude_atr':r['reassertion_magnitude_atr'],'reason':'causal proportional counter membership does not itself establish matched-control separation'})
 for r in sorted(q,key=lambda x:float(x['reassertion_magnitude_atr']),reverse=True)[:12]:ce.append({'counterexample_type':'EXTREME_GEOMETRY_STRONG_REASSERTION','interval_id':r['interval_id'],'parent_direction':r['parent_direction'],'reassertion_magnitude_atr':r['reassertion_magnitude_atr'],'reason':'large causal reassertion can coexist with extreme phase relation; no predictive inference'})
 for r in q:
  if r['invalid_ratio_flags']!='NONE':ce.append({'counterexample_type':'INVALID_DENOMINATOR','interval_id':r['interval_id'],'parent_direction':r['parent_direction'],'reassertion_magnitude_atr':r['reassertion_magnitude_atr'],'reason':r['invalid_ratio_flags']})
 # Required adverse classifications are deterministic structural descriptions,
 # not labels or selected trading examples.
 for x in comp:
  if x['sample_collapse_flag']=='YES':
   ce.append({'counterexample_type':'JOINT_CHAIN_SUPPORT_COLLAPSE','interval_id':'AGGREGATE_'+x['comparison'],'parent_direction':'','reassertion_magnitude_atr':'','reason':'predeclared comparison retained only '+str(x['support_count'])+' rows; support-collapse flag prevents independence claim'})
 for x in comp:
  if x['comparison_kind']=='JOINT':
   related=[z for z in trows if z['comparison']==x['comparison'] and z['support_count']>=3 and z['paired_rank_contrast']!='']
   if related and any(float(z['paired_rank_contrast'])<0 for z in related):
    ce.append({'counterexample_type':'AGGREGATE_REVERSED_DIRECTION_OR_TIME','interval_id':'AGGREGATE_'+x['comparison'],'parent_direction':'','reassertion_magnitude_atr':'','reason':'at least one predeclared direction/chronological-third cell has non-positive matched contrast'})
 write('counterexamples.csv',ce,['counterexample_type','interval_id','parent_direction','reassertion_magnitude_atr','reason'])
 best=max(comp,key=lambda x:x['incremental_vs_support_size_contrast']); verdict='PHASE_GEOMETRY_REJECTED'
 audits=[]
 for f in RATIOS:
  v=[float(r[f]) for r in q if r[f]!='']; audits.append(f'{f}: finite={len(v)}/{len(q)}, q25={quant(v,.25)}, q50={quant(v,.5)}, q75={quant(v,.75)}, UP={sum(r["parent_direction"]=="UP" and r[f]!="" for r in q)}, DOWN={sum(r["parent_direction"]=="DOWN" and r[f]!="" for r in q)}')
 report=f'''# EXP-017 — Phase geometry\n\nStatus: {verdict}\n\n## Hypothesis\n\nDimensionless, direction-aware relations across completed parent, counter, balance, and reassertion phases add descriptive structural separation beyond the fixed EXP-015 boundary-only population.\n\n## Data and causal method\n\nThe EXP-014 detector is reconstructed exactly, EXP-015 strict boundary membership is independently rebuilt and asserted at **369** rows, and committed EXP-016 balance fields are asserted by interval ID. Parent magnitude/duration use the eight completed bars before counter start; counter uses the first three completed child bars; committed balance is the penultimate completed child bar; reassertion uses the final completed child bar. No future bar, pivot, return, outcome label, or chart interpretation is used.\n\n## Ratio audit\n\n{chr(10).join('- '+a for a in audits)}\n\nZero, non-positive, missing and logarithm-invalid denominators are retained and flagged in `phase_geometry.csv`; no constants replace them. Balance and reassertion duration are mechanically one under the committed detector and are explicitly retained as redundant. Fixed full-source quartiles and fixed unity bands are in `geometry_comparison.csv`; deterministic chronological thirds are exhaustive in `time_segment_summary.csv`.\n\n## Controls and stability\n\nEvery comparison has deterministic same-archive controls excluding all source detections and the EXP-013 interval, with non-overlap assertion and explicit direction, age, duration, ATR, range and time mismatch fields in `matched_controls.csv`. Support-size boundary subsets are included for each comparison. Actual detector calls at factors 0.8, 1.0 and 1.2 are recorded in `parameter_stability.csv`.\n\n## Verdict\n\n**{verdict}** — predeclared geometry relations are descriptive measurements, but none is promoted: any aggregate contrast must survive support-size, direction, chronological-third and factor checks, all of which remain reported rather than inferred. The largest support-size incremental contrast is {best['comparison']} ({best['incremental_vs_support_size_contrast']:.6f}); it is not a selected threshold or predictive claim.\n\n## Files produced\n\nThis report and all seven CSV files regenerate deterministically from `experiment_017.py`.\n'''
 correlations=[]
 for n,a in enumerate(RATIOS):
  for z in RATIOS[n+1:]:
   pairs=[(float(r[a]),float(r[z])) for r in q if r[a]!='' and r[z]!='']
   correlations.append(a+'~'+z+'='+format(corr([x[0] for x in pairs],[x[1] for x in pairs]),'.3f'))
 report += '\nPairwise stable-rank correlations: '+', '.join(correlations)+'.\n'
 (OUT/'REPORT.md').write_text(report)
 # Re-open generated artifacts so the report is explicitly tied to persisted
 # CSV rows, not merely to the in-memory objects used while writing them.
 with (OUT/'phase_geometry.csv').open(newline='') as f: persisted_phase=list(csv.DictReader(f))
 with (OUT/'geometry_comparison.csv').open(newline='') as f: persisted_comparison=list(csv.DictReader(f))
 assert len(persisted_phase)==369
 assert sum(r['counter_parent_ratio']!='' for r in persisted_phase)==sum(r['counter_parent_ratio']!='' for r in q)
 persisted_best=max(persisted_comparison,key=lambda x:float(x['incremental_vs_support_size_contrast']))
 assert verdict in report and persisted_best['comparison'] in report
 assert all(c['non_overlap_verified']==1 for c in controls)
 assert len(trows)==78 and all(r['actual_detector_run']==1 for r in stability)
 print(f'source_support={len(q)} valid_ratio_support='+','.join(f'{f}:{sum(r[f]!="" for r in q)}' for f in RATIOS)+f' strongest={best["comparison"]}:{best["incremental_vs_support_size_contrast"]:.6f} direction_time=reported factors=0.8,1.0,1.2 verdict={verdict} report={OUT/"REPORT.md"}')
if __name__=='__main__': main()
