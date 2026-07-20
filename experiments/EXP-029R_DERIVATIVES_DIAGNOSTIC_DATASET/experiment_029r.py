#!/usr/bin/env python3
"""EXP-029R diagnostic reconstruction and persisted EXP-027 comparator.

This program is deliberately read-only with respect to EXP-027 and its archives.
It reconstructs event/control state observations from the frozen event identities and
the validated 15-minute archive, then recomputes every EXP-027 summary row.
"""
from __future__ import annotations
import csv, hashlib, importlib.util, io, math, os, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.dont_write_bytecode = True

OUT=Path(__file__).resolve().parent
SRC=OUT.parent/'EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER'
SYMS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT')
FIELDS=('displacement_atr','range_atr','efficiency','close_location','recent_slope_atr','age_bars','origin_disagreement_bars','w4_displacement_atr','w8_displacement_atr','w32_displacement_atr','w4_range_atr','w8_range_atr','w32_range_atr')
TOL=1e-9
def dt(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
def st(t): return t.strftime('%Y-%m-%dT%H:%M:%SZ')
def fmt(x): return '' if x is None or not math.isfinite(x) else f'{x:.10g}'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def read(p):
 with open(p,newline='') as f:return list(csv.DictReader(f))
def write(name, rows, fields):
 OUT.mkdir(parents=True,exist_ok=True); b=io.StringIO(newline=''); w=csv.DictWriter(b,fieldnames=fields,lineterminator='\n',extrasaction='raise');w.writeheader();w.writerows(rows);(OUT/name).write_text(b.getvalue())
def archive(sym):
 # The orchestrator mounts validated archives below its per-role runtime home.
 candidates=list(Path('/home/nnv/.local/state/msm-orchestrator/runtime').glob('*/corrector/home/.local/share/msm-market-data/bybit/linear'))+list(Path('/home/nnv/.local/state/msm-orchestrator/runtime').glob('*/implementer/home/.local/share/msm-market-data/bybit/linear'))+[Path.home()/'.local/share/msm-market-data/bybit/linear']
 for root in candidates:
  p=root/sym/f'{sym}_15m.csv'
  if p.exists(): return p
 raise FileNotFoundError(f'validated 15m archive missing for {sym}')
def load027():
 p=SRC/'experiment_027.py'; spec=importlib.util.spec_from_file_location('frozen027',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def key(r): return tuple(r[k] for k in ('section','episode_view','symbol','event_family','side','scale','representation','field','metric'))
def regime(bb, ts, scale):
 close=timedelta(minutes=15 if scale=='15m' else 60); i=next((j-1 for j,b in enumerate(bb) if b['t']+close>ts),len(bb)-1)
 if i<96:return 'UNKNOWN','INSUFFICIENT_PRIOR_96_CLOSED_BARS',''
 prior=sorted(b['atr'] for b in bb[i-96:i]); med=(prior[47]+prior[48])/2
 if not med:return 'UNKNOWN','ZERO_PRIOR_MEDIAN_ATR',''
 ratio=bb[i]['atr']/med
 return ('LOW' if ratio<.8 else 'HIGH' if ratio>1.2 else 'NORMAL'),'CAUSAL_PRIOR_96_CLOSED_BARS',fmt(ratio)
def main():
 m=load027(); eps=read(SRC/'episodes.csv'); controls=read(SRC/'matched_controls.csv'); committed=read(SRC/'transfer_summary.csv'); prov=read(SRC/'data_provenance.csv')
 reps=[r for r in eps if r['is_representative']=='1']; cb={r['episode_id']:r for r in controls}; ranges={s:(min(dt(r['episode_start']) for r in reps if r['symbol']==s),max(dt(r['episode_end']) for r in reps if r['symbol']==s)) for s in SYMS}
 bars={}; archive_rows=[]
 for s in SYMS:
  ap=archive(s); raw=read(ap); b=m.atr([{'t':dt(r['timestamp_utc']),'o':float(r['open']),'h':float(r['high']),'l':float(r['low']),'c':float(r['close'])} for r in raw]); bars[s]=(b,m.hourbars(b)); archive_rows.append({'symbol':s,'source_file':str(ap),'sha256':sha(ap),'rows':len(raw),'schema':'|'.join(raw[0]),'validated_against_exp027_provenance':int(any(x['symbol']==s and x['source']=='15m' and x['sha256']==sha(ap) for x in prov))})
 states=[]; invalid=[]; volatility=[]
 for e in reps:
  c=cb[e['episode_id']]; t=dt(e['episode_start']); hist=c['available_history_status']
  for role,ts,identity in [('EVENT',t,e['representative_event_id']),('CONTROL',dt(c['control_timestamp']) if c['control_status']=='MATCHED' else None,c['episode_id']+'|CONTROL')]:
   for scale,bb in [('15m',bars[e['symbol']][0]),('1H',bars[e['symbol']][1])]:
    for rep in m.REPS:
     if ts is None:
      z={'validity':'UNKNOWN','reason':'NO_EXACT_STRATUM_SUPPORT','ohlc_closed_through':''}
     else:z=m.state(bb,ts,rep,scale)
     row={k:e[k] for k in ('symbol','episode_view','episode_id','event_id','event_family','side','calendar_month','chronological_third')};row.update(observation_role=role,observation_identity=identity,observation_timestamp=st(ts) if ts else '',available_history_status=hist,scale=scale,representation=rep,validity=z.get('validity','UNKNOWN'),unknown_reason='' if z.get('validity')=='VALID' else z.get('reason','UNKNOWN'))
     for f in ('ohlc_closed_through','direction','w4_history','w4_displacement_atr','w4_range_atr','w8_history','w8_displacement_atr','w8_range_atr','w32_history','w32_displacement_atr','w32_range_atr','origin_time','age_bars','displacement_atr','range_atr','efficiency','close_location','recent_slope_atr','origin_disagreement_bars') : row[f]=z.get(f,'')
     states.append(row)
     vr,why,ratio=regime(bb,ts,scale) if ts else ('UNKNOWN','NO_EXACT_STRATUM_SUPPORT','')
     volatility.append({k:row[k] for k in ('symbol','episode_view','episode_id','event_id','event_family','side','calendar_month','chronological_third','observation_role','observation_identity','observation_timestamp','available_history_status','scale')}|{'volatility_regime':vr,'regime_reason':why,'atr_to_prior_96_median':ratio,'ohlc_closed_through':row['ohlc_closed_through']})
     if row['validity']!='VALID': invalid.append({'counterexample_type':'UNKNOWN_OR_INVALID_STATE','symbol':e['symbol'],'episode_id':e['episode_id'],'detail':role+'|'+scale+'|'+rep+'|'+row['unknown_reason']})
 ob={ (r['episode_id'],r['observation_role'],r['scale'],r['representation']):r for r in states }
 # One persisted scalar observation per representation-field combination.
 obs=[]
 for r in states:
  for field in FIELDS:
   obs.append({k:r[k] for k in ('symbol','episode_view','episode_id','event_id','event_family','side','calendar_month','chronological_third','observation_role','observation_identity','observation_timestamp','available_history_status','scale','representation','validity','unknown_reason','ohlc_closed_through','direction','origin_time')}|{'field':field,'value':r[field],'field_validity':'VALID' if r['validity']=='VALID' and r[field]!='' else 'UNKNOWN','field_unknown_reason':'' if r['validity']=='VALID' and r[field]!='' else (r['unknown_reason'] or 'FIELD_NOT_AVAILABLE')})
 # Exact frozen aggregation rule: means are paired-valid event/control values.
 summaries=[]; cells={}
 for view in ('8H','24H'):
  vr=[x for x in reps if x['episode_view']==view]
  for sym in SYMS:
   z=[x for x in vr if x['symbol']==sym]; summaries.append({'section':'support','episode_view':view,'symbol':sym,'event_family':'ALL','side':'ALL','scale':'','representation':'','field':'representatives','metric':'count','value':len(z),'event_n':len(z),'control_n':'','note':'all families'})
   for fam in ('FUNDING','OI','JOINT'):
    for side in sorted({x['side'] for x in z if x['event_family']==fam}):
     q=[x for x in z if x['event_family']==fam and x['side']==side]; summaries.append({'section':'support','episode_view':view,'symbol':sym,'event_family':fam,'side':side,'scale':'','representation':'','field':'representatives','metric':'count','value':len(q),'event_n':len(q),'control_n':'','note':'raw and time-third rows retained in episodes.csv'})
  for fam,side in sorted({(x['event_family'],x['side']) for x in vr}):
   for scale in ('15m','1H'):
    for rep in m.REPS:
     for field in FIELDS:
      contrasts=[]
      for sym in SYMS:
       es=[];cs=[]; bad=total=0
       for e in [x for x in vr if x['symbol']==sym and x['event_family']==fam and x['side']==side]:
        total+=1;a=ob[e['episode_id'],'EVENT',scale,rep];c=ob[e['episode_id'],'CONTROL',scale,rep]
        if a['validity']!='VALID' or c['validity']!='VALID' or a[field]=='' or c[field]=='':bad+=1;continue
        es.append(float(a[field]));cs.append(float(c[field]))
       con=sum(es)/len(es)-sum(cs)/len(cs) if es else None; contrasts.append(con)
       summaries.append({'section':'event_control','episode_view':view,'symbol':sym,'event_family':fam,'side':side,'scale':scale,'representation':rep,'field':field,'metric':'mean_event_minus_control','value':fmt(con),'event_n':len(es),'control_n':len(cs),'note':f'invalid_or_unmatched={bad}; total={total}'})
      good=[x for x in contrasts if x is not None]; signs=[(x>0)-(x<0) for x in good];pool=sum(good)/len(good) if good else None; denom=sum(abs(x) for x in good); maxshare=max((abs(x)/denom for x in good),default=1) if denom else 1
      cells[view,fam,side,scale,rep,field]=(dict(zip(SYMS,contrasts)),pool,maxshare)
      summaries.append({'section':'transfer_view','episode_view':view,'symbol':'POOLED_EQUAL_SYMBOL','event_family':fam,'side':side,'scale':scale,'representation':rep,'field':field,'metric':'equal_symbol_mean_contrast','value':fmt(pool),'event_n':len(good),'control_n':'','note':f'same_sign={max(signs.count(1),signs.count(-1)) if signs else 0}; max_abs_share={maxshare:.6f}'})
 for fam,side,scale,rep,field in sorted({x[1:] for x in cells}):
  aa=cells['8H',fam,side,scale,rep,field];bb=cells['24H',fam,side,scale,rep,field]; sign=lambda x:(x>0)-(x<0); target=sign(aa[1]) if aa[1] is not None else 0; support=[s for s in SYMS if aa[0][s] is not None and bb[0][s] is not None]; same=target!=0 and all(sign(aa[0][s])==target and sign(bb[0][s])==target for s in support); loso=all(not q or sign(sum(q)/len(q))==target for d in (aa[0],bb[0]) for omit in SYMS for q in [[v for s,v in d.items() if s!=omit and v is not None]])
  exclusions=[]
  for sym in support:
   r=next(x for x in summaries if x['section']=='event_control' and x['episode_view']=='8H' and x['symbol']==sym and (x['event_family'],x['side'],x['scale'],x['representation'],x['field'])==(fam,side,scale,rep,field)); a,b=r['note'].replace(';','').split(); exclusions.append(int(a.split('=')[1])/int(b.split('=')[1]))
  checks={'sufficient_support':len(support)>=3,'sign_consistency':same,'no_symbol_concentration':max(aa[2],bb[2])<=.5,'leave_one_symbol_out':loso,'merge_view_sign':aa[1] is not None and bb[1] is not None and sign(bb[1])==target,'history_validity_exclusions':bool(exclusions) and max(exclusions)<=.5}
  for metric,ok in checks.items():summaries.append({'section':'transfer_criterion','episode_view':'BOTH','symbol':'POOLED_EQUAL_SYMBOL','event_family':fam,'side':side,'scale':scale,'representation':rep,'field':field,'metric':metric,'value':int(ok),'event_n':len(support),'control_n':'','note':f'8H_pool={fmt(aa[1])}; 24H_pool={fmt(bb[1])}'})
  summaries.append({'section':'transfer_decision','episode_view':'BOTH','symbol':'POOLED_EQUAL_SYMBOL','event_family':fam,'side':side,'scale':scale,'representation':rep,'field':field,'metric':'transferable','value':int(all(checks.values())),'event_n':len(support),'control_n':'','note':'all six frozen criteria required'})
 # Comparator preserves every committed row. All values here have a reconstructed aggregate.
 rebuilt={key(r):r for r in summaries}; recon=[]
 for i,c in enumerate(committed,1):
  rr=rebuilt.get(key(c)); cv=float(c['value']) if c['value']!='' else None; rv=float(rr['value']) if rr and rr['value']!='' else None
  # Empty aggregate values are directly comparable only when both the frozen
  # value and supports agree; this is a retained no-support result, not a
  # reason to discard an otherwise reconstructable committed row.
  comparable=rr is not None; support_match=comparable and str(c['event_n'])==str(rr['event_n']) and str(c['control_n'])==str(rr['control_n'])
  values_match=(cv is not None and rv is not None and abs(cv-rv)<=TOL) or (cv is None and rv is None)
  diff=abs(cv-rv) if cv is not None and rv is not None else ''
  status='MATCH' if comparable and support_match and values_match else 'MISMATCH' if comparable else 'NOT_COMPARABLE'
  reason=('NUMERIC_AND_SUPPORT_WITHIN_FIXED_TOLERANCE' if cv is not None else 'EMPTY_VALUE_AND_SUPPORT_IDENTICAL') if status=='MATCH' else ('SUPPORT_DIFFERENCE' if comparable and not support_match else 'NUMERIC_DIFFERENCE_EXCEEDS_FIXED_TOLERANCE' if comparable else 'RECONSTRUCTED_AGGREGATE_ABSENT')
  recon.append({'source_row_id':f'EXP027_TRANSFER_{i:05d}','status':status,'reason':reason,'tolerance':f'{TOL:.0e}','absolute_difference':fmt(diff) if diff!='' else '',**{('key_'+k):c[k] for k in ('section','episode_view','symbol','event_family','side','scale','representation','field','metric')},'committed_value':c['value'],'reconstructed_value':rr['value'] if rr else '','committed_event_n':c['event_n'],'reconstructed_event_n':rr['event_n'] if rr else '','committed_control_n':c['control_n'],'reconstructed_control_n':rr['control_n'] if rr else ''})
 coverage=[]
 for (role,validity),n in sorted(Counter((r['observation_role'],r['validity']) for r in obs).items()):coverage.append({'dimension':'observation_role_validity','value':role+'|'+validity,'count':n})
 for s,n in sorted(Counter(r['status'] for r in recon).items()):coverage.append({'dimension':'reconciliation_status','value':s,'count':n})
 of=list(obs[0]); rf=list(recon[0]); write('data_provenance.csv',archive_rows,['symbol','source_file','sha256','rows','schema','validated_against_exp027_provenance']);write('observations.csv',obs,of);write('volatility_state.csv',volatility,list(volatility[0]));write('reconciliation.csv',recon,rf);write('coverage_summary.csv',coverage,['dimension','value','count']);write('counterexamples.csv',invalid,['counterexample_type','symbol','episode_id','detail'])
 persisted_recon=read(OUT/'reconciliation.csv'); counts=Counter(r['status'] for r in persisted_recon); persisted_obs=read(OUT/'observations.csv'); expected=len(reps)*2*2*len(m.REPS)*len(FIELDS); join_ok=len(persisted_obs)==expected and len({(r['episode_id'],r['observation_role'],r['scale'],r['representation'],r['field']) for r in persisted_obs})==expected
 val=[{'check':'expected_committed_aggregate_rows','value':len(committed),'status':'PASS' if len(persisted_recon)==len(committed) else 'FAIL'},{'check':'reconciliation_rows','value':len(persisted_recon),'status':'PASS' if len(persisted_recon)==len(committed) else 'FAIL'},{'check':'match_rows','value':counts['MATCH'],'status':'PASS'},{'check':'mismatch_rows','value':counts['MISMATCH'],'status':'PASS' if not counts['MISMATCH'] else 'FAIL'},{'check':'not_comparable_rows','value':counts['NOT_COMPARABLE'],'status':'PASS' if not counts['NOT_COMPARABLE'] else 'FAIL'},{'check':'observation_identifier_uniqueness','value':int(join_ok),'status':'PASS' if join_ok else 'FAIL'}]
 write('validation_summary.csv',val,['check','value','status'])
 status='DIAGNOSTIC_DATASET_READY' if all(x['status']=='PASS' for x in val) else 'DIAGNOSTIC_DATASET_FAILED'
 (OUT/'REPORT.md').write_text(f'''# EXP-029R — Derivatives diagnostic dataset

Status: {status}

## Hypothesis

The frozen EXP-027 event representatives and matched controls can be rebuilt from
the validated 15-minute archives without changing event definitions, controls,
representations, or aggregation rules.

## Data, method, and causal constraints

BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT use the frozen EXP-027 period and identities.
Each scalar diagnostic observation retains its event/control role, chronological
third, representation, field, value, validity, and explicit UNKNOWN reason. OHLC
state is restricted to bars closed at or before the observation timestamp. The
volatility regime compares current ATR only to the preceding 96 closed bars.

The null/control model is the frozen matched-control cohort. Every committed
aggregate key is reconstructed with the frozen aggregation rule and reconciled at
the fixed tolerance `{TOL:.0e}`; support counts must match as well as values.

## Results and verdict

Committed rows: {len(committed)}. MATCH: {counts["MATCH"]}; MISMATCH: {counts["MISMATCH"]}; NOT_COMPARABLE: {counts["NOT_COMPARABLE"]}. Totals are re-read from `reconciliation.csv` for `validation_summary.csv`.

**{status}**. This is a diagnostic audit, not an outcome-labelled edge claim.

## Next actions

Any predictive hypothesis must be preregistered and tested separately against this
matched-control baseline.
''')
if __name__=='__main__':main()
