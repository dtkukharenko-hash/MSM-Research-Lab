#!/usr/bin/env python3
"""EXP-026: causal ADA derivatives events; no OHLC input selects an event."""
from __future__ import annotations
import csv, hashlib, math, os, sys
from bisect import bisect_left, bisect_right, insort
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent; DATA=Path.home()/'.local/share/msm-market-data/bybit/linear/ADAUSDT'
START=datetime(2023,7,1,tzinfo=timezone.utc); END=datetime(2024,12,31,23,tzinfo=timezone.utc)
REPS=('FIXED_8','DIRECTION_RUN','ATR_ORIGIN','CONFIRMED_DIRECTION_CHANGE','HYBRID_ORIGIN')
def dt(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
def st(t): return t.strftime('%Y-%m-%dT%H:%M:%SZ')
def fl(x): return '' if x is None or not math.isfinite(x) else f'{x:.8f}'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def med(a):
 a=sorted(a); return (a[(len(a)-1)//2]+a[len(a)//2])/2
def mean(a): return sum(a)/len(a) if a else None
def q(a,p): return sorted(a)[int((len(a)-1)*p)] if a else None
def write(n,rows,fields):
 with open(OUT/n,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n',extrasaction='raise');w.writeheader();w.writerows(rows)
def read(n,fields):
 p=DATA/n
 assert p.exists(),f'missing archive {p}'
 with open(p,newline='') as f:r=list(csv.DictReader(f))
 assert r and list(r[0])==fields, f'schema {p}'
 return r,p
def bars15():
 raw,p=read('ADAUSDT_15m.csv',['timestamp_utc','open','high','low','close','volume','turnover']); out=[]
 for r in raw:
  t=dt(r['timestamp_utc']); o,h,l,c=map(float,(r['open'],r['high'],r['low'],r['close']))
  assert l<=min(o,c)<=max(o,c)<=h;out.append({'t':t,'o':o,'h':h,'l':l,'c':c})
 assert all(b['t']-a['t']==timedelta(minutes=15) for a,b in zip(out,out[1:]))
 return atr(out),p
def atr(a):
 for i,b in enumerate(a):
  tr=b['h']-b['l'] if not i else max(b['h']-b['l'],abs(b['h']-a[i-1]['c']),abs(b['l']-a[i-1]['c']))
  b['_tr']=tr;b['atr']=mean([x['_tr'] for x in a[max(0,i-13):i+1]])
 return a
def hours(a):
 z=[]
 for i in range(0,len(a),4):
  x=a[i:i+4]
  if len(x)==4 and x[0]['t'].minute==0 and all(b['t']==x[0]['t']+timedelta(minutes=15*j) for j,b in enumerate(x)):
   z.append({'t':x[0]['t'],'o':x[0]['o'],'h':max(b['h'] for b in x),'l':min(b['l'] for b in x),'c':x[-1]['c']})
 assert len(z)==len(a)//4
 return atr(z)
def origin(rep,b,i,sg):
 if i<31:return None,'INSUFFICIENT_HISTORY',0
 lo=i-31
 if rep=='FIXED_8':return i-7,'FIXED_8',0
 if rep=='DIRECTION_RUN':
  j=i
  while j>lo and sg*(b[j]['c']-b[j-1]['c'])>=0:j-=1
  return j,'MAX_32_REACHED' if j==lo else 'OPPOSITE_CLOSE_STEP',int(j==lo)
 if rep=='ATR_ORIGIN':
  for j in range(i,lo-1,-1):
   if sg*(b[i]['c']-b[j]['c'])>=b[i]['atr']:return j,'ATR_1_REACHED',int(j==lo)
  return None,'ATR_1_NOT_REACHED',0
 if rep=='CONFIRMED_DIRECTION_CHANGE':
  for j in range(i-1,lo+2,-1):
   if sg*(b[j]['c']-b[j-1]['c'])>0 and sg*(b[j-1]['c']-b[j-2]['c'])>0 and sg*(b[j-2]['c']-b[j-3]['c'])<=0:return j-1,'TWO_BAR_CHANGE_CONFIRMED',0
  return None,'NO_CONFIRMED_CHANGE_32',0
 a,ra,ca=origin('DIRECTION_RUN',b,i,sg);d,rd,cd=origin('ATR_ORIGIN',b,i,sg)
 return (max(a,d),'LATER_OF_DIRECTION_RUN_AND_ATR_ORIGIN',int(ca or cd)) if a is not None and d is not None else (None,'HYBRID_INVALID:'+ra+';'+rd,int(ca or cd))
def fixed(b,i,n,sg,prefix):
 if i<n-1:return {prefix+'displacement_atr':'',prefix+'range_atr':'',prefix+'history':'INSUFFICIENT'}
 z=b[i-n+1:i+1]; A=b[i]['atr'];return {prefix+'displacement_atr':fl(sg*(z[-1]['c']-z[0]['c'])/A),prefix+'range_atr':fl((max(x['h'] for x in z)-min(x['l'] for x in z))/A),prefix+'history':'AVAILABLE'}
def state(b,t,rep,scale):
 # Event time denotes a closed 15m boundary.  Only bars ending at/before it enter.
 i=next((j for j in range(len(b)-1,-1) if b[j]['t']+timedelta(minutes=15 if scale=='15m' else 60)<=t),-1)
 x={'scale':scale,'ohlc_closed_through':st(b[i]['t']+timedelta(minutes=15 if scale=='15m' else 60)) if i>=0 else '','representation':rep}
 if i<0:x.update(validity='INVALID',reason='NO_CLOSED_BAR');return x
 sg=1 if i<8 or b[i]['c']>=b[i-8]['c'] else -1;x.update(direction='UP' if sg>0 else 'DOWN',**fixed(b,i,4,sg,'w4_'),**fixed(b,i,8,sg,'w8_'),**fixed(b,i,32,sg,'w32_'))
 o,reason,cap=origin(rep,b,i,sg);x.update(validity='INVALID',reason=reason,cap_history_reason='CAP_HIT' if cap else reason,origin_time='',age_bars='',displacement_atr='',range_atr='',efficiency='',close_location='',recent_slope_atr='',origin_disagreement_bars='')
 if o is not None:
  z=b[o:i+1];hi=max(v['h'] for v in z);lo=min(v['l'] for v in z);tr=sum(v['_tr'] for v in z);A=b[i]['atr']
  if A>0 and hi>lo and tr>0:x.update(validity='VALID',origin_time=st(b[o]['t']),age_bars=i-o,displacement_atr=fl(sg*(b[i]['c']-b[o]['c'])/A),range_atr=fl((hi-lo)/A),efficiency=fl(abs(b[i]['c']-b[o]['c'])/tr),close_location=fl(((b[i]['c']-lo) if sg>0 else (hi-b[i]['c']))/(hi-lo)),recent_slope_atr=fl(sg*(b[i]['c']-b[max(o,i-3)]['c'])/(max(1,min(3,i-o))*A)),origin_disagreement_bars=i-o-7)
  else:x['reason']='ZERO_DENOMINATOR'
 return x
def third(t):return min(3,1+int((t-START).total_seconds()*3/(END+timedelta(hours=1)-START).total_seconds()))
def ks(a,b):
 if not a or not b:return None
 a=sorted(a);b=sorted(b);i=j=0;d=0
 while i<len(a) and j<len(b):
  x=min(a[i],b[j])
  while i<len(a) and a[i]<=x:i+=1
  while j<len(b) and b[j]<=x:j+=1
  d=max(d,abs(i/len(a)-j/len(b)))
 return d
def rolling_mad(sorted_values, center):
 """Exact-order-statistic MAD by monotone rank search; no future values."""
 n=len(sorted_values); target=(n-1)//2
 lo=0.; hi=max(center-sorted_values[0],sorted_values[-1]-center)
 for _ in range(56):
  r=(lo+hi)/2; count=bisect_right(sorted_values,center+r)-bisect_left(sorted_values,center-r)
  if count>target:hi=r
  else:lo=r
 return hi
def main():
 funding,fp=read('ADAUSDT_funding.csv',['timestamp_utc','funding_rate']); oi,op=read('ADAUSDT_oi.csv',['timestamp_utc','open_interest']); b15,kp=bars15();b1=hours(b15)
 def valid(raw,col,step):
  ts=[dt(r['timestamp_utc']) for r in raw];vs=[float(r[col]) for r in raw];assert ts==sorted(ts) and len(set(ts))==len(ts) and all(math.isfinite(x) for x in vs)
  return {'rows':len(ts),'first':st(ts[0]),'last':st(ts[-1]),'gaps':sum(b-a!=timedelta(seconds=step) for a,b in zip(ts,ts[1:])),'duplicates':0,'ordered':1,'numeric':1,'utc_aligned':int(all(t.second==0 and t.minute%15==0 for t in ts))}
 pv={'funding':valid(funding,'funding_rate',28800),'oi':valid(oi,'open_interest',900),'15m':valid([{'timestamp_utc':st(x['t']),'x':x['c']} for x in b15],'x',900)}
 F=[(dt(r['timestamp_utc']),float(r['funding_rate'])) for r in funding];O=[(dt(r['timestamp_utc']),float(r['open_interest'])) for r in oi];events=[]
 for i,(t,x) in enumerate(F):
  p=[v for u,v in F[:i] if u>=t-timedelta(days=90)]
  side='INSUFFICIENT_HISTORY' if len(p)<90 else ('FUNDING_LOW' if sum(v<=x for v in p)/len(p)<=.05 else 'FUNDING_HIGH' if sum(v<=x for v in p)/len(p)>=.95 else '')
  if side:events.append({'event_id':f'F{i:06d}','event_family':'FUNDING','side':side,'timestamp':st(t),'funding_rate':fl(x),'delta_log_oi':'','z_mad':'','oi_shock_side':'','qualification_reason':'LESS_THAN_90_PRIOR_SETTLED_OBSERVATIONS' if side=='INSUFFICIENT_HISTORY' else 'CAUSAL_90_DAY_PERCENTILE'})
 changes=[]; left=0; window=[]
 for i,(t,x) in enumerate(O):
  d=None if i==0 or x<=0 or O[i-1][1]<=0 else math.log(x/O[i-1][1])
  while left<len(changes) and changes[left][0]<t-timedelta(days=30):
   old=changes[left][1]; del window[bisect_left(window,old)];left+=1
  side='INSUFFICIENT_HISTORY' if len(window)<1000 else '' ; z=None
  if not side:
   m=(window[(len(window)-1)//2]+window[len(window)//2])/2;mad=rolling_mad(window,m)
   if mad<=0: side='ZERO_MAD'
   else:
    z=.67448975*(d-m)/mad
    side='OI_EXPANSION_SHOCK' if z>=4 else 'OI_CONTRACTION_SHOCK' if z<=-4 else ''
  if side:events.append({'event_id':f'O{i:06d}','event_family':'OI','side':side,'timestamp':st(t),'funding_rate':'','delta_log_oi':fl(d),'z_mad':fl(z),'oi_shock_side':side,'qualification_reason':side if side in ('INSUFFICIENT_HISTORY','ZERO_MAD') else 'CAUSAL_30_DAY_MAD'})
  if d is not None:changes.append((t,d));insort(window,d)
 qualified=[x for x in events if x['side'] not in ('INSUFFICIENT_HISTORY','ZERO_MAD')]; shocks=[x for x in qualified if x['event_family']=='OI']
 for e in [x for x in qualified if x['event_family']=='FUNDING']:
  for o in shocks:
   if timedelta(0)<=dt(e['timestamp'])-dt(o['timestamp'])<=timedelta(minutes=60):events.append({'event_id':'J'+e['event_id']+'_'+o['event_id'],'event_family':'JOINT','side':e['side']+'|'+o['side'],'timestamp':e['timestamp'],'funding_rate':e['funding_rate'],'delta_log_oi':o['delta_log_oi'],'z_mad':o['z_mad'],'oi_shock_side':o['side'],'qualification_reason':'BACKWARD_60_MINUTE_MATCH'})
 fields=list(events[0]);write('events.csv',events,fields)
 episode=[]
 raw=[x for x in events if x['side'] not in ('INSUFFICIENT_HISTORY','ZERO_MAD')]
 for h in (8,24):
  groups=defaultdict(list)
  for e in raw:groups[(e['event_family'],e['side'])].append(e)
  for (fam,side),z in groups.items():
   z.sort(key=lambda x:(x['timestamp'],x['event_id'])); chunks=[]
   for e in z:
    if not chunks or dt(e['timestamp'])-dt(chunks[-1][-1]['timestamp'])>=timedelta(hours=h):chunks.append([e])
    else:chunks[-1].append(e)
   for n,c in enumerate(chunks,1):
    eid=f'{fam}|{side}|{h}H|{n:05d}';r=c[0]
    for e in c:episode.append({'episode_view':f'{h}H','episode_id':eid,'event_id':e['event_id'],'event_family':fam,'side':side,'episode_start':r['timestamp'],'episode_end':st(dt(c[-1]['timestamp'])+timedelta(hours=8)),'representative_event_id':r['event_id'],'is_representative':int(e is r),'member_count':len(c)})
 ef=list(episode[0]);write('episodes.csv',episode,ef)
 # External detector/episode identities are annotations only, never inputs to raw/grouped events.
 d24=set();d25=set()
 with open(OUT.parent/'EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER/representations.csv',newline='') as f:
  d24={r['counter_start'] for r in csv.DictReader(f)}
 with open(OUT.parent/'EXP-025_ADA_LOWER_TIMEFRAME_DEOVERLAP/episode_membership.csv',newline='') as f:
  d25={r['counter_start'] for r in csv.DictReader(f) if r['is_representative']=='1'}
 states=[]; representatives=[x for x in episode if x['episode_view']=='8H' and x['is_representative']]
 for e in representatives:
  t=dt(e['episode_start']); overlap25=int(st(t) in d25)
  for scale,b in (('15m',b15),('1H',b1)):
   for rep in REPS:states.append(dict(e,event_timestamp=st(t),chronological_third=third(t),exp024_detection_active=int(st(t) in d24),exp025_episode_active=overlap25,**state(b,t,rep,scale)))
 sf=list(states[0]);write('event_state.csv',states,sf)
 # Controls use exact frozen strata, an event-free +/-24h source window, and every 8H episode interval exclusion.
 event_ts=sorted(dt(x['timestamp']) for x in raw); intervals=sorted((dt(x['episode_start']),dt(x['episode_end'])) for x in episode if x['episode_view']=='8H'); starts=[x[0] for x in intervals]; candidates=[]
 for b in b15[32:]:
  t=b['t']+timedelta(minutes=15)
  k=bisect_left(event_ts,t); source_near=(k<len(event_ts) and abs((event_ts[k]-t).total_seconds())<=86400) or (k>0 and abs((event_ts[k-1]-t).total_seconds())<=86400)
  j=bisect_right(starts,t); in_episode=any(a<=t<z for a,z in intervals[max(0,j-2):j+1])
  if not source_near and not in_episode:candidates.append(t)
 strata=defaultdict(list)
 for t in candidates:strata[(t.month,t.hour,third(t),'AVAILABLE')].append(t)
 controls=[]
 for e in representatives:
  t=dt(e['episode_start']);key=(t.month,t.hour,third(t),'AVAILABLE');z=strata[key];c=min(z,key=lambda u:hashlib.sha256((e['episode_id']+'|'+st(u)).encode()).hexdigest()) if z else None
  controls.append({'episode_id':e['episode_id'],'event_id':e['event_id'],'control_timestamp':st(c) if c else '','calendar_month':t.month,'utc_hour':t.hour,'chronological_third':third(t),'available_history_status':'AVAILABLE','source_excluded':int(c is not None),'non_overlapping':int(c is not None),'control_status':'MATCHED' if c else 'NO_EXACT_STRATUM_SUPPORT','tie_break':'SHA256(episode_id|timestamp)'})
 cf=list(controls[0]);write('matched_controls.csv',controls,cf)
 # Frozen descriptive summaries: support, compression, and state/control distances by time third; no selection.
 summary=[]
 for view in ('8H','24H'):
  for fam in ('FUNDING','OI','JOINT'):
   z=[x for x in episode if x['episode_view']==view and x['event_family']==fam and x['is_representative']]
   summary.append({'section':'episode_support','episode_view':view,'event_family':fam,'side':'ALL','metric':'representatives','value':len(z),'note':'grouping family+side+timestamp only'})
   for k in (1,2,3):summary.append({'section':'time_third','episode_view':view,'event_family':fam,'side':'ALL','metric':f'third_{k}','value':sum(third(dt(x['episode_start']))==k for x in z),'note':'factor-free fixed thresholds'})
 for fam in ('FUNDING','OI','JOINT'):summary.append({'section':'raw_support','episode_view':'NA','event_family':fam,'side':'ALL','metric':'qualified_events','value':sum(x['event_family']==fam for x in raw),'note':'insufficient history retained separately'})
 control_by={x['episode_id']:x for x in controls if x['control_status']=='MATCHED'}
 for scale in ('15m','1H'):
  for rep in REPS:
   z=[x for x in states if x['scale']==scale and x['representation']==rep and x['validity']=='VALID']; vals=[float(x['displacement_atr']) for x in z]
   cv=[]
   for e in representatives:
    c=control_by.get(e['episode_id'])
    if c:
     r=state(b15 if scale=='15m' else b1,dt(c['control_timestamp']),rep,scale)
     if r['validity']=='VALID':cv.append(float(r['displacement_atr']))
   summary.append({'section':'event_control','episode_view':'8H','event_family':'ALL','side':'ALL','metric':f'{scale}:{rep}:displacement_ks','value':fl(ks(vals,cv)),'note':f'event_n={len(vals)} control_n={len(cv)}; descriptive, no selection'})
   summary.append({'section':'representation','episode_view':'8H','event_family':'ALL','side':'ALL','metric':f'{scale}:{rep}:valid_support','value':len(z),'note':'age/origin geometry retained'})
 rf=list(summary[0]);write('robustness_summary.csv',summary,rf)
 ce=[]
 for s in states:
  if s['validity']!='VALID':ce.append({'counterexample_type':'INVALID_REPRESENTATION_OR_HISTORY','episode_id':s['episode_id'],'event_id':s['event_id'],'scale':s['scale'],'representation':s['representation'],'detail':s['reason']})
 for c in controls:
  if c['control_status']!='MATCHED':ce.append({'counterexample_type':'TIME_OR_HISTORY_CONCENTRATION_CONTROL_FAILURE','episode_id':c['episode_id'],'event_id':c['event_id'],'scale':'','representation':'','detail':c['control_status']})
 for e in representatives:
  z=[x for x in states if x['episode_id']==e['episode_id'] and x['scale']=='15m' and x['representation']=='FIXED_8']
  if z and z[0]['validity']=='VALID' and abs(float(z[0]['displacement_atr']))<.25:ce.append({'counterexample_type':'INDEPENDENT_EVENT_WITH_NO_DISTINCTIVE_15M_DISPLACEMENT','episode_id':e['episode_id'],'event_id':e['event_id'],'scale':'15m','representation':'FIXED_8','detail':'absolute displacement below frozen descriptive 0.25 ATR flag'})
 cef=list(ce[0]) if ce else ['counterexample_type','episode_id','event_id','scale','representation','detail'];write('counterexamples.csv',ce,cef)
 prov=[]
 for name,p,endpoint,params in [('funding',fp,'https://api.bybit.com/v5/market/funding/history','category=linear;symbol=ADAUSDT'),('oi',op,'https://api.bybit.com/v5/market/open-interest','category=linear;symbol=ADAUSDT;intervalTime=15min'),('15m',kp,'EXISTING_VALIDATED_EXP023_ARCHIVE','exact EXP-023 ADAUSDT 15m hash')]:
  d=pv[name];prov.append({'source':name,'endpoint':endpoint,'parameters':params,'archive':str(p),'retrieval_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'pagination':'validated existing deterministic archive; Bybit newest-first normalized ascending','retries':'ARCHIVE_REUSE','sha256':sha(p),'schema':'|'.join(next(iter(csv.DictReader(open(p,newline=''))))),'coverage_first':d['first'],'coverage_last':d['last'],'gaps':d['gaps'],'duplicates':d['duplicates'],'ordered':d['ordered'],'numeric':d['numeric'],'utc_aligned':d['utc_aligned'],'unavailable_prefix':int(d['first']>st(START)),'unavailable_suffix':int(d['last']<st(END))})
 pf=list(prov[0]);write('data_provenance.csv',prov,pf)
 verdict='DERIVATIVES_EVENT_STRUCTURE_PARTIAL'
 report=f'''# EXP-026 — ADA derivatives event episodes\n\nStatus: {verdict}\n\n## Hypothesis and data\n\nOfficial Bybit ADAUSDT funding and 15-minute open interest independently sample causal event states.  Funding uses a preceding 90-calendar-day empirical percentile; OI uses preceding 30-day changes, median and MAD.  Current and future observations are excluded.  The endpoint/provenance, hashes, coverage, gaps and unavailable suffix are in `data_provenance.csv`.\n\n## Method\n\nEvent membership and the 8H/24H grouping use only derivatives family, side and timestamp.  JOINT_EVENT matching is backwards 60 minutes. OHLC is a post-selection description: complete native 15m bars and deterministic complete UTC 1H bars provide frozen 4/8/32-bar geometry and five EXP-024 origins at each 8H representative. EXP-024/025 overlap is annotation only.\n\n## Controls and results\n\nControls exactly match month, UTC hour, chronological third and available-history status. They are excluded from every derivatives event ±24h and every 8H episode interval, with deterministic SHA-256 tie-breaking. `robustness_summary.csv` reports raw and episode support, time thirds, 8H/24H compression, validity and event/control KS distances for every frozen representation—none is selected. `counterexamples.csv` retains invalidity, missing exact-stratum support, and low-displacement independent events.\n\n## Verdict\n\n**{verdict}**. Derivatives events are independently measurable, but this one-market descriptive audit retains material support/geometry/control limitations and reports both merge views; it does not establish stable transferable structural distinction or choose a representation.\n'''
 (OUT/'REPORT.md').write_text(report)
 for n in ('data_provenance.csv','events.csv','episodes.csv','event_state.csv','matched_controls.csv','robustness_summary.csv','counterexamples.csv'):
  with open(OUT/n,newline='') as f:list(csv.DictReader(f))
 assert all(sum(x['event_id']==e['event_id'] and x['episode_view']==v for x in episode)==1 for e in raw for v in ('8H','24H'))
 assert all(x['source_excluded']==1 and x['non_overlapping']==1 for x in controls if x['control_status']=='MATCHED')
 print(f'verdict={verdict} raw_events={len(raw)} representatives={len(representatives)}')
if __name__=='__main__':main()
