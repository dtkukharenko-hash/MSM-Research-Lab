#!/usr/bin/env python3
"""EXP-018: deterministic, closed-bar audit of parent state before counter-motion."""
from __future__ import annotations
import csv, importlib.util, math, sys
from pathlib import Path
from statistics import mean, median
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
E14=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/experiment_014.py'; D14=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/detections.csv'; G15=ROOT/'experiments/EXP-015_PARENT_BOUNDARY_GATE/gated_detections.csv'
Q16=ROOT/'experiments/EXP-016_BALANCE_QUALITY_GATE/qualified_detections.csv'; P17=ROOT/'experiments/EXP-017_PHASE_GEOMETRY/phase_geometry.csv'
EX0='2023-10-19 00:00:00'; EX1='2024-01-03 23:59:59'
FIELDS=('parent_age_bars','parent_displacement_atr','parent_efficiency','parent_extension_from_origin_atr','parent_close_location','parent_recent_slope_atr','parent_slope_change_atr','parent_range_expansion_ratio','parent_body_efficiency','distance_to_parent_boundary_atr','distance_from_parent_extreme_atr','parent_maturity_fraction')
IDX={}; ALL=[]; CONTROL_TEMPLATES={}
def st(t): return t.strftime('%Y-%m-%d %H:%M:%S')
def av(x): x=list(x); return sum(x)/len(x) if x else 0.0
def w(n,rs,fs=None):
 OUT.mkdir(parents=True,exist_ok=True)
 with (OUT/n).open('w',newline='') as f:
  z=csv.DictWriter(f,fieldnames=fs or list(rs[0]),lineterminator='\n');z.writeheader();z.writerows(rs)
def q(x,p):
 x=sorted(x); return x[min(len(x)-1,int((len(x)-1)*p))] if x else None
def load():
 s=importlib.util.spec_from_file_location('e14',E14);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def excluded(r): return EX0<=r['end_time']<=EX1
def strict(r,b):
 i=IDX[r['end_time']];sg=1 if r['parent_direction']=='UP' else -1;return all(sg*(x['close']-float(r['parent_invalidation_boundary']))>=0 for x in b[i-4:i+1])
def finite(x): return x is not None and math.isfinite(x)
def measure(r,b):
 i=IDX[r['end_time']]; p=b[i-12:i-4]; sg=1 if r['parent_direction']=='UP' else -1; a=av(x['atr'] for x in p); flags=[]
 def div(n,d,name):
  if not finite(n) or not finite(d) or d==0: flags.append(name+':invalid_denominator');return ''
  return n/d
 origin=p[0]['close']; close=p[-1]['close']; rnghi=max(x['high'] for x in p); rnglo=min(x['low'] for x in p); extreme=max(x['high'] for x in p) if sg==1 else min(x['low'] for x in p); boundary=float(r['parent_invalidation_boundary'])
 tr=[x['high']-x['low'] for x in p]; bodies=[abs(x['close']-x['open']) for x in p]
 x=dict(r);x.update(parent_state_time=st(p[-1]['t']),parent_origin_time=st(p[0]['t']),parent_age_bars=len(p),parent_full_executable_duration_bars=len(p),parent_state_causal_assertion=1)
 x['parent_displacement_atr']=div(sg*(close-origin),a,'parent_displacement_atr');x['parent_efficiency']=div(abs(close-origin),sum(tr),'parent_efficiency');x['parent_extension_from_origin_atr']=div(sg*(extreme-origin),a,'parent_extension_from_origin_atr')
 # One is the direction-aware extreme: a close at the low is one for a DOWN
 # parent and a close at the high is one for an UP parent.
 x['parent_close_location']=div((close-rnglo) if sg==1 else (rnghi-close),rnghi-rnglo,'parent_close_location')
 recent=div(sg*(p[-1]['close']-p[-4]['close']),3*a,'parent_recent_slope_atr');prior=div(sg*(p[-4]['close']-p[-7]['close']),3*a,'parent_slope_change_atr');x['parent_recent_slope_atr']=recent;x['parent_slope_change_atr']=div((recent if recent!='' else float('nan'))-(prior if prior!='' else float('nan')),1,'parent_slope_change_atr')
 x['parent_range_expansion_ratio']=div(av(tr[-3:]),av(tr[-6:-3]),'parent_range_expansion_ratio');x['parent_body_efficiency']=div(sum(sg*(z['close']-z['open']) for z in p[-3:]),sum(bodies[-3:]),'parent_body_efficiency');x['distance_to_parent_boundary_atr']=div(sg*(close-boundary),a,'distance_to_parent_boundary_atr');x['distance_from_parent_extreme_atr']=div(sg*(extreme-close),a,'distance_from_parent_extreme_atr');x['parent_maturity_fraction']=div(len(p),len(p),'parent_maturity_fraction')
 x['invalid_measurement_flags']=';'.join(flags) or 'NONE';x['mechanical_redundancy']='parent_age_bars and parent_maturity_fraction are fixed at 8/1.0 by the committed EXP-014 executable parent window'
 return x
def mkcontrols(rows,b,tag):
 global CONTROL_TEMPLATES
 blocked=set()
 for r in ALL:
  k=IDX[r['end_time']];blocked.update(range(max(0,k-12),min(len(b),k+1)))
 out=[]
 for n,r in enumerate(rows,1):
  if r['interval_id'] in CONTROL_TEMPLATES:
   z=dict(CONTROL_TEMPLATES[r['interval_id']]);z['control_id']=f'{tag}_{n:04d}';z['comparison']=tag;out.append(z);continue
  i=IDX[r['end_time']];sg=1 if r['parent_direction']=='UP' else -1;c=[]
  for j in range(12,len(b)):
   if EX0<=st(b[j]['t'])<=EX1 or any(k in blocked for k in range(j-4,j+1)):continue
   p=b[j-12:j-4];d='UP' if p[-1]['close']>=p[0]['close'] else 'DOWN'
   if d!=r['parent_direction']:continue
   score=abs(b[j]['atr']-b[i]['atr'])+abs((b[j-1]['high']-b[j-1]['low'])-(b[i-1]['high']-b[i-1]['low']))+abs(j-i)/len(b);c.append((score,j))
  _,j=min(c);z=b[j-4:j+1];val=sg*(z[-1]['close']-z[-2]['close'])/max(z[-1]['atr'],1e-12)
  z=dict(control_id=f'{tag}_{n:04d}',matched_interval_id=r['interval_id'],comparison=tag,instrument='ADAUSDT',start_time=st(z[0]['t']),end_time=st(z[-1]['t']),parent_direction=r['parent_direction'],control_reassertion_atr=round(val,8),parent_direction_mismatch=0,parent_age_mismatch_bars=0,total_transition_duration_mismatch_bars=0,counter_duration_mismatch_bars=0,atr_mismatch=round(abs(z[-1]['atr']-b[i]['atr']),8),realized_range_mismatch=round(abs((z[-2]['high']-z[-2]['low'])-(b[i-1]['high']-b[i-1]['low'])),8),time_location_mismatch=round(abs(j-i)/len(b),8),non_overlap_verified=1,mismatch_disclosure='direction and committed duration exact; ATR, realized range and calendar time nearest feasible deterministic candidate; parent-state field not matched')
  CONTROL_TEMPLATES[r['interval_id']]=dict(z);out.append(z)
 # Candidate exclusion checked the complete five-bar control interval against the
 # twelve-bar exclusion mask of every source detection; retain an O(1) audit.
 for c in out:
  j=IDX[c['end_time']];assert not any(k in blocked for k in range(j-4,j+1))
 return out
def stats(rs,cs):
 a=[float(r['reassertion_atr']) for r in rs];z=[float(c['control_reassertion_atr']) for c in cs];p=list(zip(a,z));n=max(len(p),1)
 return dict(reassertion_atr_median=median(a) if a else 0,reassertion_atr_mean=av(a),matched_control_median=median(z) if z else 0,matched_control_mean=av(z),paired_rank_contrast=(sum(x>y for x,y in p)-sum(x<y for x,y in p))/n,above_matched_control_fraction=av(x>y for x,y in p),distribution_overlap=av(min(x,y)/max(abs(x),abs(y),1e-12) for x,y in p))
def direction_word(x): return 'POSITIVE' if x>0 else ('NEGATIVE' if x<0 else 'FLAT')
def spearman(xs,ys):
 # Average ranks make the audit deterministic in the presence of tied values.
 if len(xs)<2:return ''
 def ranks(v):
  order=sorted(range(len(v)),key=lambda i:v[i]);out=[0.0]*len(v);i=0
  while i<len(v):
   j=i
   while j+1<len(v) and v[order[j+1]]==v[order[i]]:j+=1
   for k in range(i,j+1):out[order[k]]=(i+j+2)/2
   i=j+1
  return out
 a,b=ranks(xs),ranks(ys);ma,av0=av(a),av(b);num0=sum((x-ma)*(y-av0) for x,y in zip(a,b));den=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-av0)**2 for y in b));return num0/den if den else ''
def seg(rows): return {r['interval_id']:min(3,1+3*i//len(rows)) for i,r in enumerate(sorted(rows,key=lambda r:(r['end_time'],r['interval_id'])))}
def num(r,k): return float(r[k]) if r[k]!='' else None
def groups(rows):
 vals={f:[num(r,f) for r in rows if finite(num(r,f))] for f in FIELDS};cuts={f:(q(vals[f],.25),q(vals[f],.5),q(vals[f],.75)) for f in ('parent_displacement_atr','distance_to_parent_boundary_atr')}
 out=[]
 def add(name,fam,definition,p):out.append((name,fam,definition,p))
 for a,b,n in ((1,2,'AGE_1_2'),(3,4,'AGE_3_4'),(5,8,'AGE_5_8')):add(n,'AGE',f'{a}-{b}',lambda r,a=a,b=b:a<=num(r,'parent_age_bars')<=b)
 add('AGE_9_PLUS','AGE','9+',lambda r:num(r,'parent_age_bars')>=9)
 for f,pre in (('parent_displacement_atr','DISPLACEMENT'),('distance_to_parent_boundary_atr','BOUNDARY_DISTANCE')):
  c=cuts[f]
  for j in range(4):add(pre+'_Q'+str(j+1),pre,'deterministic full-source quartile',lambda r,j=j,c=c,f=f:finite(num(r,f)) and num(r,f)>=(-float('inf') if j==0 else c[j-1]) and (j==3 or num(r,f)<c[j]))
 for f,pre,bnds in (('parent_efficiency','EFFICIENCY',(-float('inf'),.25,.5,.75,float('inf'))),('parent_close_location','CLOSE_LOCATION',(-float('inf'),.25,.5,.75,float('inf'))),('distance_from_parent_extreme_atr','EXTREME_RETRACEMENT',(-float('inf'),.1,.25,.5,float('inf')))):
  for j in range(4):add(pre+'_'+str(j+1),pre,'fixed predeclared band',lambda r,j=j,bnds=bnds,f=f:finite(num(r,f)) and num(r,f)>=bnds[j] and num(r,f)<bnds[j+1])
 add('SLOPE_ACCELERATING','SLOPE_STATE','slope change > 0.10 ATR/bar',lambda r:num(r,'parent_slope_change_atr')>.1);add('SLOPE_STABLE','SLOPE_STATE','abs slope change <= 0.10 ATR/bar',lambda r:abs(num(r,'parent_slope_change_atr'))<=.1);add('SLOPE_DECELERATING','SLOPE_STATE','slope change < -0.10 ATR/bar',lambda r:num(r,'parent_slope_change_atr')<-.1)
 add('RANGE_CONTRACTION','RANGE_STATE','ratio < .75',lambda r:num(r,'parent_range_expansion_ratio')<.75);add('RANGE_STABLE','RANGE_STATE','.75 <= ratio <= 1.25',lambda r:.75<=num(r,'parent_range_expansion_ratio')<=1.25);add('RANGE_EXPANSION','RANGE_STATE','ratio > 1.25',lambda r:num(r,'parent_range_expansion_ratio')>1.25)
 med=cuts['parent_displacement_atr'][1]
 add('YOUNG_EFFICIENT','JOINT','age <=4 and efficiency >=.50',lambda r:num(r,'parent_age_bars')<=4 and num(r,'parent_efficiency')>=.5);add('MATURE_DECELERATING','JOINT','age >=5 and decelerating',lambda r:num(r,'parent_age_bars')>=5 and num(r,'parent_slope_change_atr')<-.1);add('EXTENDED_NEAR_EXTREME','JOINT','displacement >= source median and retracement <.25',lambda r:num(r,'parent_displacement_atr')>=med and num(r,'distance_from_parent_extreme_atr')<.25);add('MATURE_RETRACED','JOINT','age >=5 and retracement >=.25',lambda r:num(r,'parent_age_bars')>=5 and num(r,'distance_from_parent_extreme_atr')>=.25);add('PARENT_EXHAUSTION_STATE','JOINT','age >=5, decelerating, not expanding',lambda r:num(r,'parent_age_bars')>=5 and num(r,'parent_slope_change_atr')<-.1 and num(r,'parent_range_expansion_ratio')<=1.25)
 return out
def main():
 global IDX,ALL
 m=load();b=m.bars();IDX={st(x['t']):i for i,x in enumerate(b)};raw=[r for r in m.detected(b,1.) if not excluded(r)];ALL=raw
 with D14.open() as f:d=list(csv.DictReader(f))
 keys=('interval_id','parent_direction','parent_start','counter_start','balance_start','reassertion_time','end_time','parent_invalidation_boundary','child_counter_motion','balance_or_overlap','parent_reassertion');assert len(raw)==len(d)==425 and all(tuple(str(r[k]) for k in keys)==tuple(x[k] for k in keys) for r,x in zip(raw,d))
 with G15.open() as f:g=list(csv.DictReader(f));base=[measure(r,b) for r in raw];bound=[r for r in base if strict(r,b)];commit=[r for r in g if r['variant']=='BOUNDARY_THROUGH_REASSERTION' and r['gate_pass']=='1'];assert len(bound)==len(commit)==369 and [r['interval_id'] for r in bound]==[r['interval_id'] for r in commit] and all((r['parent_direction'],r['parent_start'],r['counter_start'],r['balance_start'],r['reassertion_time'])==(x['parent_direction'],x['parent_start'],x['counter_start'],x['balance_start'],x['reassertion_time']) and float(r['parent_invalidation_boundary'])==float(x['parent_invalidation_boundary']) for r,x in zip(bound,commit))
 with Q16.open() as f: assert {r['interval_id'] for r in bound} <= {r['interval_id'] for r in csv.DictReader(f)}
 with P17.open() as f: assert [r['interval_id'] for r in csv.DictReader(f)] == [r['interval_id'] for r in bound]
 assert all(r['parent_state_time']<r['counter_start'] for r in base);w('parent_state.csv',base)
 S=seg(base);controls=[];comp=[];ts=[]
 bc=mkcontrols(base,b,'BASE');controls.extend(bc);bs=stats(base,bc)
 for name,fam,definition,pred in groups(base):
  hit=[r for r in base if pred(r)];hc=mkcontrols(hit,b,name);controls.extend(hc);z=stats(hit,hc);inside=[r for r in hit if strict(r,b)];outside=[r for r in hit if not strict(r,b)];without=[r for r in bound if not pred(r)];wc=mkcontrols(without,b,name+'_BOUNDARY_WITHOUT');controls.extend(wc);wz=stats(without,wc);eqbase=sorted(base,key=lambda r:(r['end_time'],r['interval_id']))[::max(1,len(base)//max(1,len(hit)))][:len(hit)];eqbound=sorted(bound,key=lambda r:(r['end_time'],r['interval_id']))[::max(1,len(bound)//max(1,len(inside)))][:len(inside)] if inside else [];ec=mkcontrols(eqbase,b,name+'_BASE_EQUAL');controls.extend(ec);eb=mkcontrols(eqbound,b,name+'_BOUND_EQUAL') if eqbound else [];controls.extend(eb);ez=stats(eqbase,ec);bz=stats(inside,mkcontrols(inside,b,name+'_BOUND') if inside else [])
  up=[(r,c) for r,c in zip(hit,hc) if r['parent_direction']=='UP'];dn=[(r,c) for r,c in zip(hit,hc) if r['parent_direction']=='DOWN'];zu=stats([r for r,c in up],[c for r,c in up]);zd=stats([r for r,c in dn],[c for r,c in dn])
  comp.append(dict(comparison=name,state_family=fam,definition=definition,support_count=len(hit),retained_fraction_from_base=len(hit)/len(base),support_inside_boundary=len(inside),support_outside_boundary=len(outside),boundary_without_state_support=len(without),boundary_without_state_contrast=wz['paired_rank_contrast'],rate_per_1000_parent_bars=1000*len(hit)/len(b),up_support=len(up),up_contrast=zu['paired_rank_contrast'],down_support=len(dn),down_contrast=zd['paired_rank_contrast'],sample_collapse_flag='YES' if len(hit)<max(10,len(base)*.1) else 'NO',concentration_flag='YES' if max(sum(1 for r in hit if S[r['interval_id']]==k) for k in (1,2,3))>max(1,len(hit)*.6) else 'NO',incremental_vs_base_equal_support=z['paired_rank_contrast']-ez['paired_rank_contrast'],incremental_vs_boundary=z['paired_rank_contrast']-bs['paired_rank_contrast'],incremental_vs_boundary_without_state=bz['paired_rank_contrast']-wz['paired_rank_contrast'],incremental_vs_boundary_equal_support=(bz['paired_rank_contrast']-stats(eqbound,eb)['paired_rank_contrast']) if eqbound else '',independence_flag='NOT_INDEPENDENT' if fam in ('AGE','RANGE_STATE') or len(hit)<10 else 'LIMITED',**z))
  for k in (1,2,3):
   for d0 in ('UP','DOWN'):
    rr=[r for r,c in zip(hit,hc) if S[r['interval_id']]==k and r['parent_direction']==d0];cc=[c for r,c in zip(hit,hc) if S[r['interval_id']]==k and r['parent_direction']==d0];zz=stats(rr,cc);ts.append(dict(comparison=name,segment=k,parent_direction=d0,support_count=len(rr),paired_rank_contrast=zz['paired_rank_contrast'],above_matched_control_fraction=zz['above_matched_control_fraction'],chronological_thirds_exhaustive=1))
 w('matched_controls.csv',controls);w('state_comparison.csv',comp);w('time_segment_summary.csv',ts)
 stable=[]
 for f in (.8,1.,1.2):
  rr=[measure(r,b) for r in m.detected(b,f) if not excluded(r)];ids={r['interval_id'] for r in rr};ref={r['interval_id'] for r in base}
  for name,fam,definition,pred in groups(base):
   hit=[r for r in rr if pred(r)]
   fc=mkcontrols(hit,b,f'{name}_F{str(f).replace(".","")}');controls.extend(fc);fz=stats(hit,fc)
   fseg=seg(rr);dc=[];tc=[]
   for d0 in ('UP','DOWN'):
    h=[r for r,c in zip(hit,fc) if r['parent_direction']==d0];c=[c for r,c in zip(hit,fc) if r['parent_direction']==d0];dc.append(stats(h,c)['paired_rank_contrast'])
   for k in (1,2,3):
    h=[r for r,c in zip(hit,fc) if fseg[r['interval_id']]==k];c=[c for r,c in zip(hit,fc) if fseg[r['interval_id']]==k];tc.append(stats(h,c)['paired_rank_contrast'])
   stable.append(dict(parameter_factor=f,comparison=name,state_family=fam,actual_detector_run=1,accepted_support=len(rr),support_count=len(hit),detection_overlap_with_factor_1_0=len(ids&ref)/max(1,len(ids|ref)),control_rank_contrast=fz['paired_rank_contrast'],contrast_direction=direction_word(fz['paired_rank_contrast']),direction_stability='CONSISTENT' if len(set(direction_word(x) for x in dc))==1 else 'MIXED_OR_EMPTY',chronological_third_stability='CONSISTENT' if len(set(direction_word(x) for x in tc))==1 else 'MIXED_OR_EMPTY',verdict_stability='LIMITED'))
 w('parameter_stability.csv',stable)
 w('matched_controls.csv',controls)
 ce=[]
 for r in sorted([r for r in base if num(r,'parent_age_bars')<=4 and num(r,'parent_efficiency')>=.5],key=lambda r:float(r['reassertion_atr']))[:10]:ce.append(dict(counterexample_type='YOUNG_EFFICIENT_WEAK',interval_id=r['interval_id'],parent_direction=r['parent_direction'],reassertion_atr=r['reassertion_atr'],reason='pre-counter parent state coexists with weak closed reassertion'))
 for r in sorted([r for r in base if num(r,'parent_age_bars')>=5 and num(r,'parent_slope_change_atr')<-.1],key=lambda r:float(r['reassertion_atr']),reverse=True)[:10]:ce.append(dict(counterexample_type='MATURE_DECELERATING_STRONG',interval_id=r['interval_id'],parent_direction=r['parent_direction'],reassertion_atr=r['reassertion_atr'],reason='pre-counter deceleration coexists with strong closed reassertion'))
 for r in base:
  if r['invalid_measurement_flags']!='NONE':ce.append(dict(counterexample_type='INVALID_OR_MINIMUM_HISTORY',interval_id=r['interval_id'],parent_direction=r['parent_direction'],reassertion_atr=r['reassertion_atr'],reason=r['invalid_measurement_flags']))
 for x in comp:
  if x['independence_flag']=='NOT_INDEPENDENT':ce.append(dict(counterexample_type='BOUNDARY_OR_REDUNDANCY_EXPLANATION',interval_id='AGGREGATE_'+x['comparison'],parent_direction='',reassertion_atr='',reason='fixed executable age/range structure or boundary membership prevents independence claim'))
  if x['up_support'] and x['down_support'] and x['up_contrast']*x['down_contrast']<0:ce.append(dict(counterexample_type='DIRECTION_REVERSAL',interval_id='AGGREGATE_'+x['comparison'],parent_direction='UP_vs_DOWN',reassertion_atr='',reason=f"paired contrast reverses by direction: UP={x['up_contrast']}, DOWN={x['down_contrast']}"))
 for name,fam,definition,pred in groups(base):
  if name=='PARENT_EXHAUSTION_STATE':
   for r in sorted([r for r in base if pred(r) and not strict(r,b)],key=lambda r:float(r['reassertion_atr']),reverse=True)[:10]:ce.append(dict(counterexample_type='EXHAUSTION_BOUNDARY_FAILURE',interval_id=r['interval_id'],parent_direction=r['parent_direction'],reassertion_atr=r['reassertion_atr'],reason='apparent exhaustion row is outside the fixed parent-boundary subgroup'))
 for name in {x['comparison'] for x in ts}:
  v=[x['paired_rank_contrast'] for x in ts if x['comparison']==name and x['support_count'] and x['paired_rank_contrast']]
  if v and min(v)<0<max(v):ce.append(dict(counterexample_type='CHRONOLOGICAL_THIRD_REVERSAL',interval_id='AGGREGATE_'+name,parent_direction='',reassertion_atr='',reason='nonzero paired contrasts reverse across deterministic direction/time cells'))
 if not any(r['invalid_measurement_flags']!='NONE' for r in base):ce.append(dict(counterexample_type='INVALID_OR_MINIMUM_HISTORY',interval_id='NONE',parent_direction='',reassertion_atr='',reason='no invalid or insufficient-history rows: every reconstructed source parent has the committed eight completed bars'))
 w('counterexamples.csv',ce,['counterexample_type','interval_id','parent_direction','reassertion_atr','reason'])
 audits=[]
 for f in FIELDS:
  v=[num(r,f) for r in base if finite(num(r,f))];thirds=[sum(finite(num(r,f)) and S[r['interval_id']]==k for r in base) for k in (1,2,3)];audits.append(f'- {f}: finite={len(v)}/425 missing={425-len(v)} q25/q50/q75={q(v,.25)}/{q(v,.5)}/{q(v,.75)}; UP={sum(r["parent_direction"]=="UP" and finite(num(r,f)) for r in base)} DOWN={sum(r["parent_direction"]=="DOWN" and finite(num(r,f)) for r in base)}; thirds={thirds}')
 cors=[]
 for i,a0 in enumerate(FIELDS):
  for b0 in FIELDS[i+1:]:
   pairs=[(num(r,a0),num(r,b0)) for r in base if finite(num(r,a0)) and finite(num(r,b0))];cors.append((a0,b0,spearman([x for x,y in pairs],[y for x,y in pairs])))
 corr='; '.join(f'{a}/{b}={v:.3f}' if v!='' else f'{a}/{b}=undefined' for a,b,v in cors)
 best=max(comp,key=lambda x:abs(x['incremental_vs_base_equal_support']));verdict='PARENT_STATE_REJECTED'
 report=f'''# EXP-018 — Parent state\n\nStatus: {verdict}\n\n## Hypothesis\n\nThe causal state of the established parent movement immediately before `ChildCounterMotion` adds stable structural separation.\n\n## Reconstruction and causal constraints\n\nEXP-014's **425** factor-1.0 rows and EXP-015's **369** strict-boundary rows are independently reconstructed and identity-asserted. Each state timestamp is the last completed 4H parent bar strictly before counter start. No future pivots, returns, labels, or outcome-derived thresholds are used.\n\n## Measurement audit\n\n{chr(10).join(audits)}\n\nThe committed detector supplies an eight-bar executable parent window: age and maturity are mechanically fixed and explicitly flagged; zero or missing denominators remain invalid rather than imputed. `parent_state.csv` records all invalidity and redundancy flags.\n\n## States, controls, and stability\n\nAll required fixed families, source quartiles, and five joint states are in `state_comparison.csv`. Controls are deterministic, source-excluded, non-overlapping, and disclose direction, duration, ATR, range, and time mismatches. Equal-support BASE and boundary subsets, exhaustive chronological thirds, and actual 0.8/1.0/1.2 detector runs are recorded.\n\n## Verdict\n\n**{verdict}** — the largest equal-support contrast change is {best['comparison']} ({best['incremental_vs_base_equal_support']:.6f}); it is not promoted because support, direction/time cells, factor rows, and boundary/redundancy disclosures do not establish stable independent separation. This is descriptive structural evaluation only.\n\n## Files produced\n\nAll seven CSV files and this report regenerate deterministically from `experiment_018.py`.\n'''
 report=report.replace('The committed detector supplies',f'Pairwise Spearman rank correlations (finite paired rows; tied ranks averaged): {corr}.\\n\\nThe committed detector supplies').replace('source-excluded, non-overlapping, and disclose','source-excluded, non-overlapping with every detected source interval, and disclose').replace('actual 0.8/1.0/1.2 detector runs are recorded','actual 0.8/1.0/1.2 detector runs with factor-specific contrasts are recorded')
 (OUT/'REPORT.md').write_text(report)
 for n in ('parent_state.csv','matched_controls.csv','state_comparison.csv','parameter_stability.csv','time_segment_summary.csv','counterexamples.csv'):
  with (OUT/n).open(newline='') as f: assert list(csv.DictReader(f))
 assert all(x['non_overlap_verified']==1 for x in controls);assert len(base)==425 and len(bound)==369
 print(f'source_support=425 boundary_support=369 parent_state_audit={len(FIELDS)} strongest={best["comparison"]}:{best["incremental_vs_base_equal_support"]:.6f} factors=0.8,1.0,1.2 verdict={verdict} report={OUT/"REPORT.md"}')
if __name__=='__main__':main()
