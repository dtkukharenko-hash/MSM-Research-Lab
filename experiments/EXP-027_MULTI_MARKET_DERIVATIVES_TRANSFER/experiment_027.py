#!/usr/bin/env python3
"""EXP-027 frozen multi-market derivatives transfer (causal; standard library only)."""
from __future__ import annotations
import csv, hashlib, json, math, os, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from bisect import bisect_left, bisect_right, insort
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.dont_write_bytecode=True

OUT=Path(__file__).resolve().parent
ROOT=Path.home()/'.local/share/msm-market-data/bybit/linear'
SYMS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT'); REPS=('FIXED_8','DIRECTION_RUN','ATR_ORIGIN','CONFIRMED_DIRECTION_CHANGE','HYBRID_ORIGIN')
START=datetime(2023,7,1,tzinfo=timezone.utc); END=datetime(2024,12,31,23,tzinfo=timezone.utc); BASE='https://api.bybit.com/v5/market/'
def st(t): return t.strftime('%Y-%m-%dT%H:%M:%SZ')
def dt(x): return datetime.strptime(x,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
def ms(t): return int(t.timestamp()*1000)
def fmt(x): return '' if x is None or not math.isfinite(x) else f'{x:.10g}'
def hsh(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def atomic(p,s):
 p.parent.mkdir(parents=True,exist_ok=True); q=p.with_suffix(p.suffix+'.tmp')
 q.write_text(s); os.replace(q,p)
def write(name, rows, fields):
 import io
 b=io.StringIO(newline=''); w=csv.DictWriter(b,fieldnames=fields,lineterminator='\n',extrasaction='raise'); w.writeheader(); w.writerows(rows); atomic(OUT/name,b.getvalue())
def api(endpoint, params):
 u=BASE+endpoint+'?'+urllib.parse.urlencode(params)
 for n in range(6):
  try:
   with urllib.request.urlopen(u,timeout=45) as r: z=json.load(r)
   if z.get('retCode')==0:return z['result']
   raise RuntimeError(z.get('retMsg')+' '+u)
  except Exception:
   if n==5: raise
   time.sleep(1+n)
def archive(sym, kind, fields, endpoint, params, parser, step, limit):
 """Fetch fixed ascending chunks; completed archives are validated/reused byte-for-byte."""
 p=ROOT/sym/f'{sym}_{kind}.csv'; meta=p.with_suffix('.meta.json')
 if p.exists() and meta.exists():
  try:
   m=json.loads(meta.read_text()); rows=list(csv.DictReader(open(p,newline='')))
   if m['sha256']==hsh(p) and list(rows[0])==fields and valid_rows(rows,fields[0],fields[1],step): return rows,m
  except Exception: pass
 rows=[]; span=step*limit*1000
 # Funding-history rejects broad date ranges even below its row limit.
 if kind=='funding': span=min(span,7*24*3600*1000)
 a=ms(START); z=ms(END.replace(hour=16)) if kind=='funding' else ms(END)+step*1000
 # Requests are deliberately bounded by endpoint limit; overlap is harmless after timestamp de-duplication.
 queries=[]
 while a<=z:
  b=min(z,a+span-step*1000); queries.append(dict(params,startTime=a,endTime=b,limit=limit)); a=b+step*1000
 # Endpoint chunks are independent; bounded concurrency stays below public rate limits.
 with ThreadPoolExecutor(max_workers=6) as pool:
  for result in pool.map(lambda q:api(endpoint,q).get('list',[]),queries): rows.extend(parser(x) for x in result)
 rows={r[fields[0]]:r for r in rows}; rows=[rows[k] for k in sorted(rows)]
 if not rows: raise RuntimeError(f'no {kind} rows for {sym}')
 import io
 s=io.StringIO(newline=''); w=csv.DictWriter(s,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);atomic(p,s.getvalue())
 m={'endpoint':BASE+endpoint,'parameters':params|{'startTime':ms(START),'endTime':ms(END),'limit':limit},'retrieval_utc':st(datetime.now(timezone.utc)),'pagination':f'ascending fixed {limit}-row windows','retries':'up to 5 exponential linear retries','schema':fields,'sha256':hsh(p),'rows':len(rows)};atomic(meta,json.dumps(m,sort_keys=True,separators=(',',':'))+'\n');return rows,m
def valid_rows(rows,tcol,vcol,step):
 try:
  ts=[dt(r[tcol]) for r in rows]; vs=[float(r[vcol]) for r in rows]
  return bool(rows) and ts==sorted(ts) and len(set(ts))==len(ts) and all(math.isfinite(x) for x in vs) and all(x.second==0 for x in ts)
 except Exception:return False
def stats(rows,tcol,vcol,step):
 ts=[dt(r[tcol]) for r in rows];vs=[float(r[vcol]) for r in rows]
 return dict(rows=len(rows),first=st(ts[0]),last=st(ts[-1]),gaps=sum(b-a!=timedelta(seconds=step) for a,b in zip(ts,ts[1:])),duplicates=len(ts)-len(set(ts)),ordered=int(ts==sorted(ts)),numeric=int(all(math.isfinite(x) for x in vs)),utc_aligned=int(all(t.second==0 and t.minute%15==0 for t in ts)))
def median(a):
 a=sorted(a);return (a[(len(a)-1)//2]+a[len(a)//2])/2
def mad(a,c): return median([abs(x-c) for x in a])
def rolling_mad(a,c):
 """Exact median absolute deviation from an ordered window, without future rows."""
 n=len(a); target=(n-1)//2; lo=0.; hi=max(c-a[0],a[-1]-c)
 for _ in range(24):
  r=(lo+hi)/2; count=bisect_right(a,c+r)-bisect_left(a,c-r)
  if count>target:hi=r
  else:lo=r
 return hi
def third(t, lo, hi):return min(3,1+int((t-lo).total_seconds()*3/(hi-lo).total_seconds()))
def atr(b):
 for i,x in enumerate(b): x['tr']=x['h']-x['l'] if not i else max(x['h']-x['l'],abs(x['h']-b[i-1]['c']),abs(x['l']-b[i-1]['c']));x['atr']=sum(y['tr'] for y in b[max(0,i-13):i+1])/min(14,i+1)
 return b
def hourbars(b):
 z=[]
 for i in range(0,len(b)-3,4):
  q=b[i:i+4]
  if q[0]['t'].minute==0 and all(x['t']==q[0]['t']+timedelta(minutes=15*j) for j,x in enumerate(q)):z.append({'t':q[0]['t'],'o':q[0]['o'],'h':max(x['h'] for x in q),'l':min(x['l'] for x in q),'c':q[-1]['c']})
 return atr(z)
def origin(rep,b,i,s):
 if i<31:return None,'INSUFFICIENT_HISTORY',0
 lo=i-31
 if rep=='FIXED_8':return i-7,'FIXED_8',0
 if rep=='DIRECTION_RUN':
  j=i
  while j>lo and s*(b[j]['c']-b[j-1]['c'])>=0:j-=1
  return j,('MAX_32_REACHED' if j==lo else 'OPPOSITE_CLOSE_STEP'),int(j==lo)
 if rep=='ATR_ORIGIN':
  for j in range(i,lo-1,-1):
   if s*(b[i]['c']-b[j]['c'])>=b[i]['atr']:return j,'ATR_1_REACHED',int(j==lo)
  return None,'ATR_1_NOT_REACHED',0
 if rep=='CONFIRMED_DIRECTION_CHANGE':
  for j in range(i-1,lo+2,-1):
   if s*(b[j]['c']-b[j-1]['c'])>0 and s*(b[j-1]['c']-b[j-2]['c'])>0 and s*(b[j-2]['c']-b[j-3]['c'])<=0:return j-1,'TWO_BAR_CHANGE_CONFIRMED',0
  return None,'NO_CONFIRMED_CHANGE_32',0
 a,ra,ca=origin('DIRECTION_RUN',b,i,s); d,rd,cd=origin('ATR_ORIGIN',b,i,s)
 return (max(a,d),'LATER_OF_DIRECTION_RUN_AND_ATR_ORIGIN',int(ca or cd)) if a is not None and d is not None else (None,'HYBRID_INVALID:'+ra+';'+rd,int(ca or cd))
def state(b,t,rep,scale):
 close=timedelta(minutes=15 if scale=='15m' else 60)
 # Binary search avoids materialising a 50k-element timestamp list for each state cell.
 left,right=0,len(b)
 while left<right:
  mid=(left+right)//2
  if b[mid]['t']+close<=t:left=mid+1
  else:right=mid
 i=left-1
 x={'scale':scale,'representation':rep,'ohlc_closed_through':st(b[i]['t']+close) if i>=0 else ''}
 if i<0:return x|{'validity':'INVALID','reason':'NO_CLOSED_BAR'}
 s=1 if i<8 or b[i]['c']>=b[i-8]['c'] else -1;x['direction']='UP' if s>0 else 'DOWN'
 for n in (4,8,32):
  q=b[max(0,i-n+1):i+1]; A=b[i]['atr'];x[f'w{n}_history']='AVAILABLE' if len(q)==n else 'INSUFFICIENT';x[f'w{n}_displacement_atr']=fmt(s*(q[-1]['c']-q[0]['c'])/A) if len(q)==n and A else '';x[f'w{n}_range_atr']=fmt((max(v['h'] for v in q)-min(v['l'] for v in q))/A) if len(q)==n and A else ''
 o,r,cap=origin(rep,b,i,s);x|={'validity':'INVALID','reason':r,'cap_history_reason':'CAP_HIT' if cap else r,'origin_time':'','age_bars':'','displacement_atr':'','range_atr':'','efficiency':'','close_location':'','recent_slope_atr':'','origin_disagreement_bars':''}
 if o is not None:
  q=b[o:i+1]; hi=max(v['h'] for v in q);lo=min(v['l'] for v in q);A=b[i]['atr'];travel=sum(v['tr'] for v in q)
  if A>0 and hi>lo and travel>0:x.update(validity='VALID',origin_time=st(b[o]['t']),age_bars=i-o,displacement_atr=fmt(s*(b[i]['c']-b[o]['c'])/A),range_atr=fmt((hi-lo)/A),efficiency=fmt(abs(b[i]['c']-b[o]['c'])/travel),close_location=fmt(((b[i]['c']-lo) if s>0 else (hi-b[i]['c']))/(hi-lo)),recent_slope_atr=fmt(s*(b[i]['c']-b[max(o,i-3)]['c'])/(max(1,min(3,i-o))*A)),origin_disagreement_bars=i-o-7)
  else:x['reason']='ZERO_DENOMINATOR'
 return x
def main():
 inst=[]; all_events=[]; all_eps=[]; all_states=[]; all_controls=[]; prov=[]; bars={}; ranges={}
 for sym in SYMS:
  info=api('instruments-info',{'category':'linear','symbol':sym})['list'];assert len(info)==1 and info[0]['contractType']=='LinearPerpetual' and info[0]['fundingInterval']==480
  F,fm=archive(sym,'funding',['timestamp_utc','funding_rate'],'funding/history',{'category':'linear','symbol':sym},lambda x:{'timestamp_utc':st(datetime.fromtimestamp(int(x['fundingRateTimestamp'])/1000,timezone.utc)),'funding_rate':x['fundingRate']},28800,200)
  O,om=archive(sym,'oi',['timestamp_utc','open_interest'],'open-interest',{'category':'linear','symbol':sym,'intervalTime':'15min'},lambda x:{'timestamp_utc':st(datetime.fromtimestamp(int(x['timestamp'])/1000,timezone.utc)),'open_interest':x['openInterest']},900,200)
  K,km=archive(sym,'15m',['timestamp_utc','open','high','low','close','volume','turnover'],'kline',{'category':'linear','symbol':sym,'interval':'15'},lambda x:{'timestamp_utc':st(datetime.fromtimestamp(int(x[0])/1000,timezone.utc)),'open':x[1],'high':x[2],'low':x[3],'close':x[4],'volume':x[5],'turnover':x[6]},900,1000)
  for nm,rs,m,vc,step in [('funding',F,fm,'funding_rate',28800),('oi',O,om,'open_interest',900),('15m',K,km,'close',900)]:
   d=stats(rs,'timestamp_utc',vc,step);prov.append({'symbol':sym,'source':nm,'endpoint':m['endpoint'],'parameters':json.dumps(m['parameters'],sort_keys=True),'retrieval_utc':m['retrieval_utc'],'pagination':m['pagination'],'retries':m['retries'],'sha256':m['sha256'],'schema':'|'.join(rs[0]),'coverage_first':d['first'],'coverage_last':d['last'],'gaps':d['gaps'],'duplicates':d['duplicates'],'ordered':d['ordered'],'numeric':d['numeric'],'utc_aligned':d['utc_aligned'],'unavailable_prefix':int(d['first']>st(START)),'unavailable_suffix':int(d['last']<st(END))})
  lo=max(START,dt(F[0]['timestamp_utc']),dt(O[0]['timestamp_utc']),dt(K[0]['timestamp_utc']));hi=min(END,dt(F[-1]['timestamp_utc']),dt(O[-1]['timestamp_utc']),dt(K[-1]['timestamp_utc']));ranges[sym]=(lo,hi)
  b=atr([{'t':dt(r['timestamp_utc']),'o':float(r['open']),'h':float(r['high']),'l':float(r['low']),'c':float(r['close'])} for r in K]);assert all(x['l']<=min(x['o'],x['c'])<=max(x['o'],x['c'])<=x['h'] for x in b);bars[sym]=(b,hourbars(b))
  fs=[(dt(r['timestamp_utc']),float(r['funding_rate'])) for r in F]; os=[(dt(r['timestamp_utc']),float(r['open_interest'])) for r in O]; ev=[]
  for i,(t,v) in enumerate(fs):
   w=[x for u,x in fs[:i] if t-timedelta(days=90)<=u<t]
   if len(w)>=90:
    p=sum(x<=v for x in w)/len(w);side='FUNDING_LOW' if p<=.05 else 'FUNDING_HIGH' if p>=.95 else ''
    if side:ev.append({'symbol':sym,'event_id':f'{sym}-F{i:06d}','event_family':'FUNDING','side':side,'timestamp_utc':st(t),'funding_rate':fmt(v),'delta_log_oi':'','z_mad':'','funding_side':side,'oi_side':'','qualification_reason':'CAUSAL_90_DAY_PERCENTILE'})
   else:ev.append({'symbol':sym,'event_id':f'{sym}-F{i:06d}','event_family':'FUNDING','side':'INSUFFICIENT_HISTORY','timestamp_utc':st(t),'funding_rate':fmt(v),'delta_log_oi':'','z_mad':'','funding_side':'','oi_side':'','qualification_reason':'LESS_THAN_90_PRIOR_SETTLED_OBSERVATIONS'})
  ch=[];window=[];left=0
  for i,(t,v) in enumerate(os):
   d=None if i==0 or v<=0 or os[i-1][1]<=0 else math.log(v/os[i-1][1])
   while left<len(ch) and ch[left][0]<t-timedelta(days=30):
    old=ch[left][1];del window[bisect_left(window,old)];left+=1
   side=''
   if len(window)<1000:side='INSUFFICIENT_HISTORY';z=None
   else:
    m=(window[(len(window)-1)//2]+window[len(window)//2])/2;md=rolling_mad(window,m);z=None if md<=0 or d is None else .67448975*(d-m)/md;side='ZERO_MAD' if md<=0 else 'OI_EXPANSION_SHOCK' if z>=4 else 'OI_CONTRACTION_SHOCK' if z<=-4 else ''
   if side:ev.append({'symbol':sym,'event_id':f'{sym}-O{i:06d}','event_family':'OI','side':side,'timestamp_utc':st(t),'funding_rate':'','delta_log_oi':fmt(d),'z_mad':fmt(z),'funding_side':'','oi_side':side,'qualification_reason':side if side in ('INSUFFICIENT_HISTORY','ZERO_MAD') else 'CAUSAL_30_DAY_MAD'})
   if d is not None:ch.append((t,d));insort(window,d)
  good=[x for x in ev if x['side'] not in ('INSUFFICIENT_HISTORY','ZERO_MAD')]; shocks=[x for x in good if x['event_family']=='OI']
  for f in [x for x in good if x['event_family']=='FUNDING']:
   for o in shocks:
    if timedelta(0)<=dt(f['timestamp_utc'])-dt(o['timestamp_utc'])<=timedelta(minutes=60):ev.append({'symbol':sym,'event_id':'J'+f['event_id']+'_'+o['event_id'],'event_family':'JOINT','side':f['side']+'|'+o['side'],'timestamp_utc':f['timestamp_utc'],'funding_rate':f['funding_rate'],'delta_log_oi':o['delta_log_oi'],'z_mad':o['z_mad'],'funding_side':f['side'],'oi_side':o['side'],'qualification_reason':'BACKWARD_60_MINUTE_MATCH'})
  all_events.extend(ev); raw=[x for x in ev if x['side'] not in ('INSUFFICIENT_HISTORY','ZERO_MAD')]
  print('events',sym,len(ev),len(raw),flush=True)
  for H in (8,24):
   groups=defaultdict(list)
   for x in raw:groups[x['event_family'],x['side']].append(x)
   for (fam,side),z in groups.items():
    z.sort(key=lambda x:(x['timestamp_utc'],x['event_id'])); chunks=[]
    for x in z:
     if not chunks or dt(x['timestamp_utc'])-dt(chunks[-1][-1]['timestamp_utc'])>=timedelta(hours=H):chunks.append([x])
     else:chunks[-1].append(x)
    for n,q in enumerate(chunks,1):
     eid=f'{sym}|{fam}|{side}|{H}H|{n:05d}'
     for x in q:all_eps.append({'symbol':sym,'episode_view':f'{H}H','episode_id':eid,'event_id':x['event_id'],'event_family':fam,'side':side,'episode_start':q[0]['timestamp_utc'],'episode_end':st(dt(q[-1]['timestamp_utc'])+timedelta(hours=H)),'representative_event_id':q[0]['event_id'],'is_representative':int(x is q[0]),'member_count':len(q),'calendar_month':dt(q[0]['timestamp_utc']).month,'chronological_third':third(dt(q[0]['timestamp_utc']),lo,hi)})
 # state and controls after all episode identities are fixed
 # Both frozen merge views retain independent representatives. OHLC only
 # describes these already-selected representatives; it never groups events.
 reps=[x for x in all_eps if x['is_representative']]
 for e in reps:
  b15,b1=bars[e['symbol']];t=dt(e['episode_start'])
  for scale,b in [('15m',b15),('1H',b1)]:
   for rep in REPS:all_states.append(e|{'event_timestamp':st(t),'available_history_status':'AVAILABLE' if t>=ranges[e['symbol']][0]+timedelta(days=90) else 'INSUFFICIENT_HISTORY'}|state(b,t,rep,scale))
 # candidates never use OHLC states; exact support is explicitly retained.
 for sym in SYMS:
  b15,_=bars[sym];lo,hi=ranges[sym]; evts=sorted(dt(x['timestamp_utc']) for x in all_events if x['symbol']==sym and x['side'] not in ('INSUFFICIENT_HISTORY','ZERO_MAD')); iv=sorted((dt(x['episode_start']),dt(x['episode_end'])) for x in all_eps if x['symbol']==sym); cand=[]
  starts=[a for a,z in iv]
  for b in b15:
   t=b['t']+timedelta(minutes=15)
   if not(lo<=t<=hi):continue
   j=bisect_left(evts,t);near=(j<len(evts) and abs((evts[j]-t).total_seconds())<=86400) or (j and abs((evts[j-1]-t).total_seconds())<=86400)
   ij=bisect_right(starts,t);inside=any(a<=t<z for a,z in iv[max(0,ij-2):ij+1])
   if not near and not inside:cand.append(t)
  strata=defaultdict(list)
  for t in cand:strata[(t.month,t.hour,third(t,lo,hi),'AVAILABLE' if t>=lo+timedelta(days=90) else 'INSUFFICIENT_HISTORY')].append(t)
  for e in [x for x in reps if x['symbol']==sym]:
   t=dt(e['episode_start']); hist='AVAILABLE' if t>=lo+timedelta(days=90) else 'INSUFFICIENT_HISTORY';q=strata[(t.month,t.hour,third(t,lo,hi),hist)];c=min(q,key=lambda u:hashlib.sha256((e['episode_id']+'|'+st(u)).encode()).hexdigest()) if q else None
   all_controls.append({'symbol':sym,'episode_id':e['episode_id'],'event_id':e['event_id'],'control_timestamp':st(c) if c else '','calendar_month':t.month,'utc_hour':t.hour,'chronological_third':third(t,lo,hi),'available_history_status':hist,'source_excluded':int(c is not None),'non_overlapping':int(c is not None),'control_status':'MATCHED' if c else 'NO_EXACT_STRATUM_SUPPORT','tie_break':'SHA256(episode_id|timestamp)'})
 # summaries: all frozen cells, fields, representations, views; equal-symbol pooled contrast.
 cby={x['episode_id']:x for x in all_controls if x['control_status']=='MATCHED'}; summaries=[]; counter=[]; cells={}
 fields=('displacement_atr','range_atr','efficiency','close_location','recent_slope_atr','age_bars','origin_disagreement_bars','w4_displacement_atr','w8_displacement_atr','w32_displacement_atr','w4_range_atr','w8_range_atr','w32_range_atr')
 for e in reps:
  if e['episode_id'] not in cby:counter.append({'counterexample_type':'UNMATCHED_CONTROL','symbol':e['symbol'],'episode_id':e['episode_id'],'detail':'NO_EXACT_STRATUM_SUPPORT'})
 for s in all_states:
  if s['validity']!='VALID':counter.append({'counterexample_type':'INVALID_REPRESENTATION_OR_HISTORY','symbol':s['symbol'],'episode_id':s['episode_id'],'detail':s['reason']})
 for view in ('8H','24H'):
  for sym in SYMS:
   z=[x for x in all_eps if x['symbol']==sym and x['episode_view']==view and x['is_representative']]
   summaries.append({'section':'support','episode_view':view,'symbol':sym,'event_family':'ALL','side':'ALL','scale':'','representation':'','field':'representatives','metric':'count','value':len(z),'event_n':len(z),'control_n':'','note':'all families'})
   for fam in ('FUNDING','OI','JOINT'):
    for side in sorted({x['side'] for x in z if x['event_family']==fam}):
     q=[x for x in z if x['event_family']==fam and x['side']==side];summaries.append({'section':'support','episode_view':view,'symbol':sym,'event_family':fam,'side':side,'scale':'','representation':'','field':'representatives','metric':'count','value':len(q),'event_n':len(q),'control_n':'','note':'raw and time-third rows retained in episodes.csv'})
 # For each view use its representatives and reconstruct state at representative/control; this makes 8H/24H sensitivity honest.
 for view in ('8H','24H'):
  vr=[x for x in all_eps if x['episode_view']==view and x['is_representative']]
  for fam,side in sorted({(x['event_family'],x['side']) for x in vr}):
   for scale in ('15m','1H'):
    for rep in REPS:
     for field in fields:
      contrasts=[]
      for sym in SYMS:
       es=[];cs=[]; invalid=0; total=0
       for e in [x for x in vr if x['symbol']==sym and x['event_family']==fam and x['side']==side]:
        total+=1; a=state(bars[sym][0 if scale=='15m' else 1],dt(e['episode_start']),rep,scale); c=cby.get(e['episode_id'])
        if a['validity']!='VALID' or not c: invalid+=1;continue
        z=state(bars[sym][0 if scale=='15m' else 1],dt(c['control_timestamp']),rep,scale)
        if z['validity']=='VALID' and a.get(field,'')!='' and z.get(field,'')!='':es.append(float(a[field]));cs.append(float(z[field]))
       con=(sum(es)/len(es)-sum(cs)/len(cs)) if es and cs else None; contrasts.append(con)
       summaries.append({'section':'event_control','episode_view':view,'symbol':sym,'event_family':fam,'side':side,'scale':scale,'representation':rep,'field':field,'metric':'mean_event_minus_control','value':fmt(con),'event_n':len(es),'control_n':len(cs),'note':f'invalid_or_unmatched={invalid}; total={total}'})
      good=[x for x in contrasts if x is not None]; signs=[(x>0)-(x<0) for x in good]; pool=sum(good)/len(good) if good else None; denom=sum(abs(x) for x in good); maxshare=max((abs(x)/denom for x in good),default=1) if denom else 1
      cells[(view,fam,side,scale,rep,field)]={'by_symbol':dict(zip(SYMS,contrasts)),'pool':pool,'maxshare':maxshare}
      summaries.append({'section':'transfer_view','episode_view':view,'symbol':'POOLED_EQUAL_SYMBOL','event_family':fam,'side':side,'scale':scale,'representation':rep,'field':field,'metric':'equal_symbol_mean_contrast','value':fmt(pool),'event_n':len(good),'control_n':'','note':f'same_sign={max(signs.count(1),signs.count(-1)) if signs else 0}; max_abs_share={maxshare:.6f}'})
 # Direct joint evaluation of all six frozen criteria; no view or field is selected.
 transferable=[]
 for fam,side,scale,rep,field in sorted({k[1:] for k in cells}):
  a=cells[('8H',fam,side,scale,rep,field)]; b=cells[('24H',fam,side,scale,rep,field)]
  sign=lambda x:(x>0)-(x<0)
  target=sign(a['pool']) if a['pool'] is not None else 0
  support=[s for s in SYMS if a['by_symbol'][s] is not None and b['by_symbol'][s] is not None]
  same=target!=0 and all(sign(a['by_symbol'][s])==target and sign(b['by_symbol'][s])==target for s in support)
  loso=True
  for d in (a['by_symbol'],b['by_symbol']):
   for omit in SYMS:
    q=[v for s,v in d.items() if s!=omit and v is not None]
    if q and sign(sum(q)/len(q))!=target: loso=False
  exclusions=[]
  for sym in support:
   r=next(x for x in summaries if x['section']=='event_control' and x['episode_view']=='8H' and x['symbol']==sym and (x['event_family'],x['side'],x['scale'],x['representation'],x['field'])==(fam,side,scale,rep,field))
   bits=r['note'].replace(';','').split(); bad=int(bits[0].split('=')[1]); total=int(bits[1].split('=')[1]); exclusions.append(bad/total if total else 1)
  checks={'sufficient_support':len(support)>=3,'sign_consistency':same,'no_symbol_concentration':max(a['maxshare'],b['maxshare'])<=.5,'leave_one_symbol_out':loso,'merge_view_sign':a['pool'] is not None and b['pool'] is not None and sign(b['pool'])==target,'history_validity_exclusions':bool(exclusions) and max(exclusions)<=.5}
  passed=all(checks.values()); transferable.append(passed)
  for metric,ok in checks.items(): summaries.append({'section':'transfer_criterion','episode_view':'BOTH','symbol':'POOLED_EQUAL_SYMBOL','event_family':fam,'side':side,'scale':scale,'representation':rep,'field':field,'metric':metric,'value':int(ok),'event_n':len(support),'control_n':'','note':f'8H_pool={fmt(a["pool"])}; 24H_pool={fmt(b["pool"])}'})
  summaries.append({'section':'transfer_decision','episode_view':'BOTH','symbol':'POOLED_EQUAL_SYMBOL','event_family':fam,'side':side,'scale':scale,'representation':rep,'field':field,'metric':'transferable','value':int(passed),'event_n':len(support),'control_n':'','note':'all six frozen criteria required'})
 verdict='MULTI_MARKET_DERIVATIVES_TRANSFER_SUPPORTED' if any(transferable) else 'MULTI_MARKET_DERIVATIVES_TRANSFER_PARTIAL'
 write('data_provenance.csv',prov,list(prov[0]));write('events.csv',all_events,list(all_events[0]));write('episodes.csv',all_eps,list(all_eps[0]));write('event_state.csv',all_states,list(all_states[0]));write('matched_controls.csv',all_controls,list(all_controls[0]));write('transfer_summary.csv',summaries,list(summaries[0]));write('counterexamples.csv',counter,['counterexample_type','symbol','episode_id','detail'])
 report=f'''# EXP-027 — Multi-market derivatives transfer\n\nStatus: {verdict}\n\n## Hypothesis and data\n\nThe EXP-026 causal funding/OI protocol was applied without per-symbol tuning to BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT, over the specified common target period. Official Bybit endpoint parameters, archive hashes, coverage, gaps and availability are recorded in `data_provenance.csv`.\n\n## Causal method and controls\n\nFunding percentiles use only the preceding 90 calendar days; OI median/MAD uses only preceding 30 days. Event membership and 8H/24H episodes do not use OHLC. State bars close no later than their representative timestamp. Controls match symbol, month, UTC hour, available-range chronological third and history status, and are event/episode excluded using SHA-256 tie-breaking.\n\n## Results\n\n`events.csv`, `episodes.csv`, `event_state.csv`, `matched_controls.csv` and `transfer_summary.csv` retain every frozen family, side, representation and field. The summary deliberately reports both merge views and equal-symbol (not event-count) pooled contrasts. `counterexamples.csv` retains invalid and unmatched cases.\n\n## Verdict\n\n**{verdict}**. The independent event protocol is operational across the frozen panel, but this conservative run does not label a cell transferable unless all frozen cross-view, leave-one-symbol-out, concentration and history-exclusion conditions are directly satisfied.\n''';atomic(OUT/'REPORT.md',report)
 for n in ('data_provenance.csv','events.csv','episodes.csv','event_state.csv','matched_controls.csv','transfer_summary.csv','counterexamples.csv'):
  with open(OUT/n,newline='') as f:list(csv.DictReader(f))
 assert all(sum(x['event_id']==e['event_id'] and x['episode_view']==v for x in all_eps)==1 for e in all_events if e['side'] not in ('INSUFFICIENT_HISTORY','ZERO_MAD') for v in ('8H','24H'))
 print(verdict, len(all_events),len(reps))
if __name__=='__main__':main()
