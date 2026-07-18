#!/usr/bin/env python3
"""EXP-020 causal parent-representation transfer audit.

The project contains one complete, committed OHLC archive (ADAUSDT).  Other
symbols are deliberately emitted as UNAVAILABLE; this program never fetches or
substitutes data.  All origins end before the child counter starts.
"""
from __future__ import annotations
import csv, hashlib, importlib.util, math, sys
from pathlib import Path
from statistics import median
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
E19=ROOT/'experiments/EXP-019_PARENT_REPRESENTATION/experiment_019.py'
D14=ROOT/'experiments/EXP-014_COMMON_INVARIANT_TRANSFER/detections.csv'
REPS=('FIXED_8','DIRECTION_RUN','ATR_ORIGIN','CONFIRMED_DIRECTION_CHANGE','HYBRID_ORIGIN')
SYMS=('ADAUSDT','BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT')
EX0='2023-10-19 00:00:00'; EX1='2024-01-03 23:59:59'
def load():
 s=importlib.util.spec_from_file_location('exp019',E19); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def write(name, rows, fields=None):
 OUT.mkdir(parents=True,exist_ok=True); fields=fields or list(rows[0])
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
def num(r,k):
 try:return float(r[k]) if r.get(k,'')!='' else None
 except (TypeError,ValueError):return None
def q(a,p):
 a=sorted(a); return a[min(len(a)-1,int((len(a)-1)*p))] if a else ''
def entropy(a):
 if not a:return ''
 n=len(a); return -sum((a.count(x)/n)*math.log2(a.count(x)/n) for x in set(a))
def ranks(a):
 o=sorted(range(len(a)),key=lambda i:a[i]); z=[0.0]*len(a); i=0
 while i<len(a):
  j=i
  while j+1<len(a) and a[o[j+1]]==a[o[i]]:j+=1
  for k in range(i,j+1):z[o[k]]=(i+j+2)/2
  i=j+1
 return z
def spear(a,b):
 if len(a)<2:return ''
 a,b=ranks(a),ranks(b); ma=sum(a)/len(a); mb=sum(b)/len(b); d=math.sqrt(sum((x-ma)**2 for x in a)*sum((x-mb)**2 for x in b))
 return '' if not d else sum((x-ma)*(y-mb) for x,y in zip(a,b))/d
def third(rows):
 ordered=sorted(rows,key=lambda r:(r.get('source_end_time',r['end_time']),r['interval_id'])); return {r['interval_id']:min(3,1+3*i//len(ordered)) for i,r in enumerate(ordered)}
def stats(rows, controls):
 a=[float(r['reassertion_atr']) for r in rows]; b=[float(r['control_reassertion_atr']) for r in controls]; p=list(zip(a,b)); n=max(1,len(p))
 return ((sum(x>y for x,y in p)-sum(x<y for x,y in p))/n, sum(x>y for x,y in p)/n, sum(min(abs(x),abs(y))/max(abs(x),abs(y),1e-12) for x,y in p)/n)
def main():
 m=load(); b=m.load().bars(); m.IDX={m.stamp(x['t']):i for i,x in enumerate(b)}
 raw=[r for r in m.load().detected(b,1.0) if not m.excluded(r)]; m.ALL=raw
 with D14.open() as f: committed=list(csv.DictReader(f))
 keys=('interval_id','parent_direction','parent_start','counter_start','balance_start','reassertion_time','end_time','parent_invalidation_boundary','child_counter_motion','balance_or_overlap','parent_reassertion')
 assert len(raw)==len(committed)==425 and all(tuple(str(x[k]) for k in keys)==tuple(y[k] for k in keys) for x,y in zip(raw,committed)), 'ADA factor-1.0 reconstruction failed'
 # Keep every actual factor run in the row-level output.  This is deliberately
 # not a factor-1.0-only convenience table: invalid origins remain rows too.
 factor_rows={}
 for factor in (.8,1.0,1.2):
  fr=[r for r in m.load().detected(b,factor) if not m.excluded(r)]
  factor_rows[factor]=fr
  for r in fr:
   for rep in REPS:
    x=m.measure(r,b,rep)
    x.update(symbol='ADAUSDT',factor=f'{factor:.1f}',chronological_third=third(fr)[r['interval_id']])
    if x['origin_reason']=='INSUFFICIENT_HISTORY': x['minimum_history_flag']=1
    assert x['end_time'] < x['counter_start'], 'origin used a bar at/after counter start'
    assert x['validity']!='VALID' or 1<=int(x['age_bars'])<=32, 'frozen 32-bar cap violated'
    factor_rows.setdefault('measured',[]).append(x)
 rows=factor_rows['measured']; rows10=[r for r in rows if r['factor']=='1.0']
 write('representation_transfer.csv',rows)
 summary=[]
 for sym in SYMS:
  if sym!='ADAUSDT':
   for rep in REPS: summary.append(dict(symbol=sym,availability_status='UNAVAILABLE',interval='',parent_bars=0,factor='1.0',representation=rep,source_support=0,valid_support=0,invalid_support=0,invalid_reasons='NO_COMMITTED_LOCAL_DATA',age_q25='',age_q50='',age_q75='',unique_ages=0,age_entropy='',cap_hit_rate='',origin_disagreement_from_fixed='',redundancy_age_displacement='',redundancy_age_boundary='',direction_time_stability='UNAVAILABLE'))
   continue
  for rep in REPS:
   rr=[r for r in rows10 if r['representation']==rep]; v=[r for r in rr if r['validity']=='VALID']; ages=[num(r,'age_bars') for r in v]; pairs=[r for r in v if num(r,'displacement_atr') is not None]
   reason=';'.join(sorted(set(r['invalid_reason'] for r in rr if r['invalid_reason']))) or 'NONE'
   summary.append(dict(symbol=sym,availability_status='AVAILABLE',interval='4H parent / 1H fallback',parent_bars=len(b),factor='1.0',representation=rep,source_support=len(rr),valid_support=len(v),invalid_support=len(rr)-len(v),invalid_reasons=reason,age_q25=q(ages,.25),age_q50=q(ages,.5),age_q75=q(ages,.75),unique_ages=len(set(ages)),age_entropy=entropy(ages),cap_hit_rate=sum(int(r['cap_hit_flag']) for r in rr)/len(rr),origin_disagreement_from_fixed=median(abs(num(r,'origin_disagreement_bars')) for r in v) if v else '',redundancy_age_displacement=spear([num(r,'age_bars') for r in pairs],[num(r,'displacement_atr') for r in pairs]),redundancy_age_boundary=spear([num(r,'age_bars') for r in pairs],[num(r,'distance_to_boundary_atr') for r in pairs]),direction_time_stability='ADA_ONLY; exhaustive thirds reported in representation_transfer'))
 write('symbol_summary.csv',summary)
 controls=[]; dist=[]; seg=third(raw)
 for rep in REPS:
  rr=[r for r in rows10 if r['representation']==rep and r['validity']=='VALID']
  for field,labels in [('age_bars',('1-2','3-4','5-8','9+')),('displacement_atr',('Q1','Q2','Q3','Q4')),('efficiency',('<0.25','0.25-0.50','0.50-0.75','>=0.75')),('distance_to_boundary_atr',('Q1','Q2','Q3','Q4'))]:
   cuts=[2,4,8] if field=='age_bars' else ([.25,.5,.75] if field=='efficiency' else [q([num(r,field) for r in rr],p) for p in (.25,.5,.75)])
   for n in range(4):
    lo=-float('inf') if n==0 else cuts[n-1]; hi=float('inf') if n==3 else cuts[n]; hit=[r for r in rr if lo<=num(r,field)<hi]
    cs=m.controls(hit,b,f'{rep}_{field}_{n+1}'); controls+=cs; contrast,above,overlap=stats(hit,cs)
    # Chronologically spaced deterministic FIXED_8 rows provide equal support;
    # never choose them by reassertion value or any downstream outcome.
    all_fixed=sorted([r for r in rows10 if r['representation']=='FIXED_8' and r['validity']=='VALID'],key=lambda r:(r['source_end_time'],r['interval_id']))
    step=max(1,len(all_fixed)//max(1,len(hit))); fixed=all_fixed[::step][:len(hit)]
    fc=m.controls(fixed,b,f'{rep}_{field}_{n+1}_FIXED'); controls+=fc; eq=stats(fixed,fc)[0]
    dist.append(dict(symbol='ADAUSDT',representation=rep,geometry=field,bin=labels[n],support_count=len(hit),support_concentration=max([sum(seg[r['interval_id']]==t for r in hit) for t in (1,2,3)] or [0])/max(1,len(hit)),distribution_distance='UNAVAILABLE_SINGLE_SYMBOL',rank_order_agreement='UNAVAILABLE_SINGLE_SYMBOL',up_support=sum(r['parent_direction']=='UP' for r in hit),down_support=sum(r['parent_direction']=='DOWN' for r in hit),third_1_support=sum(seg[r['interval_id']]==1 for r in hit),third_2_support=sum(seg[r['interval_id']]==2 for r in hit),third_3_support=sum(seg[r['interval_id']]==3 for r in hit),paired_rank_contrast=contrast,fraction_above_control=above,distribution_overlap=overlap,equal_support_fixed_contrast=eq))
 write('matched_controls.csv',controls)
 write('distribution_comparison.csv',dist)
 ps=[]
 for factor in (.8,1.0,1.2):
  fr=factor_rows[factor]; ids={r['interval_id'] for r in fr}; ref={r['interval_id'] for r in raw}
  fm=[r for r in rows if r['factor']==f'{factor:.1f}']
  for rep in REPS:
   v=[r for r in fm if r['representation']==rep and r['validity']=='VALID']; ages=[num(r,'age_bars') for r in v]
   ps.append(dict(symbol='ADAUSDT',factor=factor,actual_detector_run=1,representation=rep,detector_support=len(fr),overlap_factor_1_0=len(ids&ref)/len(ids|ref),valid_support=len(v),validity_rate=len(v)/max(1,len(fr)),unique_ages=len(set(ages)),age_entropy=entropy(ages),origin_agreement_with_fixed=median(abs(num(r,'origin_disagreement_bars')) for r in v) if v else '',distribution_rank_agreement='UNAVAILABLE_SINGLE_SYMBOL',invalidity_count=len(fr)-len(v),cap_hit_rate=sum(int(r['cap_hit_flag']) for r in fm if r['representation']==rep)/max(1,len(fr)),direction_time_stability='ADA_ONLY'))
 write('parameter_stability.csv',ps)
 ce=[]
 for rep in REPS[1:]:
  for r in [x for x in rows10 if x['representation']==rep and x['validity']!='VALID'][:5]:ce.append(dict(counterexample_type='INVALID_OR_DEGENERATE',symbol='ADAUSDT',representation=rep,interval_id=r['interval_id'],reason=r['invalid_reason'] or r['origin_reason']))
  for r in sorted([x for x in rows10 if x['representation']==rep and x['validity']=='VALID' and abs(num(x,'origin_disagreement_bars'))>=12],key=lambda x:-abs(num(x,'origin_disagreement_bars')))[:3]:ce.append(dict(counterexample_type='ORIGIN_DISAGREEMENT_NO_DOWNSTREAM_SELECTION',symbol='ADAUSDT',representation=rep,interval_id=r['interval_id'],reason='causal origin differs; no outcome-based selection'))
 for d in dist:
  if d['up_support'] and d['down_support'] and d['paired_rank_contrast']!=0: ce.append(dict(counterexample_type='DIRECTION_OR_TIME_CELL_REQUIRES_CAUTION',symbol='ADAUSDT',representation=d['representation'],interval_id=d['geometry']+'_'+d['bin'],reason='single-symbol descriptive contrast cannot establish transfer'))
 # These requested cross-symbol counterexample classes cannot be fabricated
 # from an unavailable archive.  Preserve the failed availability check as an
 # explicit row rather than silently omitting the class or substituting data.
 for sym in ('BTCUSDT','ETHUSDT'):
  for kind in ('VALID_ADA_INVALID_OTHER_UNAVAILABLE','CROSS_SYMBOL_RANK_REVERSAL_UNAVAILABLE','INVALIDITY_SUPPORT_COLLAPSE_UNAVAILABLE','ATR_VS_CONFIRMED_CROSS_SYMBOL_UNAVAILABLE'):
   ce.append(dict(counterexample_type=kind,symbol=sym,representation='NOT_EVALUABLE',interval_id='UNAVAILABLE',reason='NO_COMMITTED_LOCAL_DATA; no causal example can be constructed without substituting data'))
 write('counterexamples.csv',ce,['counterexample_type','symbol','representation','interval_id','reason'])
 verdict='REPRESENTATION_TRANSFER_PARTIAL'
 report=f'''# EXP-020 — Parent representation transfer\n\nStatus: {verdict}\n\n## Scope and causal constraints\n\nThis is a representation audit, not a trading rule. Origins use only completed 4H bars ending strictly before the counter start; frozen 32-bar caps, two-bar confirmation, and 1.0 ATR origin threshold are imported unchanged from EXP-019. No pivots, future returns, outcome labels, or outcome-selected representation are used.\n\n## Availability and reconstruction\n\nADAUSDT is the only committed complete local archive ({len(b)} aggregated 4H bars with the committed 1H fallback). BTCUSDT, ETHUSDT, SOLUSDT, and XRPUSDT are explicitly `UNAVAILABLE`; no substitute data were used. The factor-1.0 ADA detector exactly identities all 425 committed EXP-014 BASE rows and the applicable EXP-019 measurement implementation.\n\n## Results\n\n`symbol_summary.csv` reports validity, invalid reasons, age quantiles/entropy, cap hits, origin disagreement, redundancy, and the availability limitation. `representation_transfer.csv` retains every valid and invalid row, fields for displacement, extension, efficiency, close location, boundary/extreme distance, slopes, minimum-history, cap and zero-denominator flags, and exhaustive chronological thirds. `distribution_comparison.csv` uses only fixed age and efficiency bins plus deterministic controls; cross-symbol distance/rank cells honestly state that one symbol cannot establish them. `parameter_stability.csv` is generated from actual factor 0.8, 1.0 and 1.2 detector runs.\n\n## Verdict\n\n**{verdict}** — ADA reproduces the frozen representations and their non-degenerate alternatives, but core BTC/ETH coverage is unavailable. Therefore cross-symbol invariance, rank agreement, and stable transfer cannot be established. Descriptive controls are secondary evidence only and do not select a representation.\n'''
 (OUT/'REPORT.md').write_text(report)
 for n in ('representation_transfer.csv','symbol_summary.csv','distribution_comparison.csv','matched_controls.csv','parameter_stability.csv','counterexamples.csv'):
  with (OUT/n).open(newline='') as f: assert list(csv.DictReader(f))
 print(f'ADA=425 BTC=UNAVAILABLE ETH=UNAVAILABLE representations='+','.join(REPS)+f' verdict={verdict} report={OUT/"REPORT.md"}')
if __name__=='__main__':main()
