#!/usr/bin/env python3
"""Acquire and audit official Bybit linear ADAUSDT lower-timeframe candles.

This program deliberately has no market-structure logic.  It is a reproducible
data boundary: it fetches only the documented V5 kline endpoint, stores raw
files outside the repository, and builds the committed audit package from those
files.  Re-running it is safe; valid cached rows are reused and output timestamps
are fixed to the frozen acquisition metadata rather than wall-clock time.
"""
from __future__ import annotations
import csv, hashlib, json, math, os, tempfile, time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RAW = Path.home()/'.local/share/msm-market-data/bybit/linear/ADAUSDT'
ENDPOINT = 'https://api.bybit.com/v5/market/kline'
SOURCE_1H = ROOT/'experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_1h.csv'
INTERVALS = {'3': 180, '5': 300, '15': 900}
SCHEMA = ['timestamp_utc','open','high','low','close','volume','turnover']
TOL = Decimal('0.00000001')

def iso(ms): return datetime.fromtimestamp(ms/1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def stamp(s): return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def dec(x):
    d=Decimal(str(x))
    if not d.is_finite(): raise ValueError('non-finite')
    return d
def canon(x):
    d=dec(x)
    s=format(d.normalize(), 'f')
    return '0' if s in ('-0','') else s
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def load_1h():
    rows=[]
    with open(SOURCE_1H, newline='') as f:
        for r in csv.DictReader(f):
            # EXP-021 established these naive ISO source timestamps are UTC.
            rows.append({'t':stamp(r['open_time']+'Z'),'o':dec(r['open']),'h':dec(r['high']),'l':dec(r['low']),'c':dec(r['close'])})
    return rows
def read_raw(path):
    if not path.exists(): return []
    with open(path,newline='') as f:
        rd=csv.DictReader(f)
        if rd.fieldnames != SCHEMA: raise ValueError('raw schema mismatch: '+str(rd.fieldnames))
        return [{'t':stamp(r['timestamp_utc']),'o':dec(r['open']),'h':dec(r['high']),'l':dec(r['low']),'c':dec(r['close']),'v':dec(r['volume']),'q':dec(r['turnover'])} for r in rd]
def valid_cached(rows, step):
    return all(rows[i]['t']>rows[i-1]['t'] and rows[i]['t']% (step*1000)==0 for i in range(1,len(rows))) and all(r['t']%(step*1000)==0 for r in rows)
def fetch(params, log):
    query=urlencode(params); url=ENDPOINT+'?'+query
    err=''
    for n in range(5):
        try:
            req=Request(url, headers={'User-Agent':'MSM-Research-Lab/EXP-023'})
            with urlopen(req, timeout=30) as resp: payload=json.loads(resp.read().decode())
            if payload.get('retCode') != 0: raise ValueError('API return '+str(payload.get('retCode'))+': '+str(payload.get('retMsg')))
            data=payload.get('result',{})
            if data.get('category') not in (None,'linear') or data.get('symbol') not in (None,'ADAUSDT'): raise ValueError('response identity mismatch')
            log.append(['API',params['interval'],query,n+1,'OK','',len(data.get('list',[])),datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')])
            return data.get('list',[])
        except (HTTPError,URLError,TimeoutError,ValueError,json.JSONDecodeError) as e:
            err=str(e); log.append(['API',params['interval'],query,n+1,'ERROR',err,0,datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')])
            if n==4: break
            time.sleep(0.5*(2**n))
    raise RuntimeError(err)
def acquire(interval, start, end, log):
    step=INTERVALS[interval]*1000; path=RAW/f'ADAUSDT_{interval}m.csv'; RAW.mkdir(parents=True,exist_ok=True)
    try: cached=read_raw(path)
    except Exception as e: cached=[]; log.append(['LOCAL',interval,str(path),0,'INVALID_CACHE',str(e),0,''])
    if cached and valid_cached(cached, INTERVALS[interval]):
        log.append(['LOCAL',interval,str(path),0,'VALID_CACHE','',len(cached),''])
    else: cached=[]
    by={r['t']:r for r in cached if start<=r['t']<=end}
    # Reverse chronological V5 pages, bounded at the desired frozen end.  Pages
    # overlap only at boundaries by design and are deduplicated by open timestamp.
    cursor=end
    seen=set(); lower=start
    # A validated contiguous cache is the safe-resume fast path.  Incomplete
    # caches are re-queried over the frozen range, so missing timestamps cannot
    # be silently treated as valid coverage.
    complete_cache = len(by) == ((end-start)//step)+1 and all(t in by for t in range(start,end+1,step))
    while cursor>=lower and not complete_cache:
        page=fetch({'category':'linear','symbol':'ADAUSDT','interval':interval,'start':str(lower),'end':str(cursor),'limit':'1000'},log)
        if not page: break
        parsed=[]
        for x in page:
            if not isinstance(x,list) or len(x)<7: raise RuntimeError('malformed kline row')
            t=int(x[0]); parsed.append((t,{'t':t,'o':dec(x[1]),'h':dec(x[2]),'l':dec(x[3]),'c':dec(x[4]),'v':dec(x[5]),'q':dec(x[6])}))
        oldest=min(t for t,_ in parsed)
        if oldest in seen and len(page)>=1000: raise RuntimeError('non-monotonic pagination loop')
        seen.add(oldest)
        for t,r in parsed:
            if start<=t<=end: by[t]=r
        if oldest<=lower or len(page)<1000: break
        cursor=oldest-step
    now=int(time.time()*1000); rows=[r for t,r in sorted(by.items()) if t+step<=now]
    # Do not replace a cache with a partial result after an acquisition error.
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=RAW); os.close(fd)
    try:
        with open(tmp,'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=SCHEMA,lineterminator='\n'); w.writeheader()
            for r in rows: w.writerow({'timestamp_utc':iso(r['t']),'open':canon(r['o']),'high':canon(r['h']),'low':canon(r['l']),'close':canon(r['c']),'volume':canon(r['v']),'turnover':canon(r['q'])})
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return rows,path
def audit(rows, step, start, end, path):
    ts=[r['t'] for r in rows]; c=Counter(ts); dup=sum(n-1 for n in c.values() if n>1)
    nonmono=sum(ts[i]<=ts[i-1] for i in range(1,len(ts)))
    expected=list(range(start, end+1, step*1000)); actual=set(ts); missing=[t for t in expected if t not in actual]
    gaps=[]
    for t in missing:
        if not gaps or t!=gaps[-1][-1]+step*1000: gaps.append([t])
        else: gaps[-1].append(t)
    bad_ohlc=bad_price=neg=align=0
    for r in rows:
        if r['t']%(step*1000): align+=1
        if min(r['o'],r['h'],r['l'],r['c'])<=0: bad_price+=1
        if r['h']<max(r['o'],r['c']) or r['l']>min(r['o'],r['c']) or r['h']<r['l']: bad_ohlc+=1
        if r['v']<0 or r['q']<0: neg+=1
    prefix=(iso(start),iso(ts[0]-step*1000)) if ts and ts[0]>start else ('','')
    suffix=(iso(ts[-1]+step*1000),iso(end)) if ts and ts[-1]<end else ('','')
    return {'first':iso(ts[0]) if ts else '', 'last':iso(ts[-1]) if ts else '', 'rows':len(rows),'expected':len(expected),'observed':len(actual),'missing':len(missing),'gaps':gaps,'duplicates':dup,'nonmonotonic':nonmono,'bad_ohlc':bad_ohlc,'nonpositive':bad_price,'negative_vq':neg,'alignment':align,'prefix':prefix,'suffix':suffix,'hash':sha(path) if path.exists() else '','bytes':path.stat().st_size if path.exists() else 0}
def aggregate(rows, component, target):
    buckets={}
    for r in rows: buckets.setdefault((r['t']//(target*1000))*(target*1000),[]).append(r)
    out=[]
    for t,x in sorted(buckets.items()):
        x=sorted(x,key=lambda z:z['t'])
        if len(x)!=target//component or any(x[i]['t']!=t+i*component*1000 for i in range(len(x))): continue
        out.append({'t':t,'o':x[0]['o'],'h':max(z['h'] for z in x),'l':min(z['l'] for z in x),'c':x[-1]['c'],'v':sum(z['v'] for z in x),'q':sum(z['q'] for z in x)})
    return out
def compare(a,b, fields):
    aa={x['t']:x for x in a}; bb={x['t']:x for x in b}; shared=sorted(set(aa)&set(bb)); mism=[]; maxabs=Decimal(0); maxrel=Decimal(0)
    for t in shared:
        for f in fields:
            d=abs(aa[t][f]-bb[t][f]); maxabs=max(maxabs,d); maxrel=max(maxrel,d/(abs(bb[t][f]) if bb[t][f] else Decimal(1)))
            if d>TOL: mism.append(t); break
    return {'overlap':len(shared),'exact':len(shared)-len(mism),'mismatch':len(mism),'maxabs':canon(maxabs),'maxrel':canon(maxrel),'samples':'|'.join(iso(t) for t in mism[:5])}
def write_csv(name, fields, rows):
    with open(OUT/name,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
def main():
    one=load_1h(); start=one[0]['t']; end=one[-1]['t']; logs=[]; raw={}; audits={}; acquisition_error={}
    for iv,sec in INTERVALS.items():
        try: raw[iv],p=acquire(iv,start,end,logs); audits[iv]=audit(raw[iv],sec,start,end,p)
        except Exception as e:
            acquisition_error[iv]=str(e); p=RAW/f'ADAUSDT_{iv}m.csv'; raw[iv]=read_raw(p) if p.exists() else []; audits[iv]=audit(raw[iv],sec,start,end,p); logs.append(['API',iv,'',0,'FAILED',str(e),0,datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')])
    log_fields=['event','interval','request_or_path','attempt','status','detail','rows','retrieval_time_utc']
    # Keep the factual first-download request record when regenerating from a
    # complete cache; replacing it with a new wall-clock cache-read log would
    # make the committed audit non-deterministic and erase retry evidence.
    log_path=OUT/'acquisition_log.csv'
    if not any(x[0]=='API' for x in logs) and log_path.exists():
        with open(log_path,newline='') as f: frozen_logs=list(csv.DictReader(f))
        if frozen_logs and set(['event','interval','request_or_path','attempt','status','detail','rows']).issubset(frozen_logs[0]):
            for row in frozen_logs: row.setdefault('retrieval_time_utc','')
        else: frozen_logs=[dict(zip(log_fields,x)) for x in logs]
    else: frozen_logs=[dict(zip(log_fields,x)) for x in logs]
    write_csv('acquisition_log.csv',log_fields,frozen_logs)
    gaprows=[]; sumrows=[]; statuses={}
    for iv in INTERVALS:
        a=audits[iv]; valid=not any(a[k] for k in ('duplicates','nonmonotonic','bad_ohlc','nonpositive','negative_vq','alignment'))
        full=a['rows']==a['expected'] and not a['missing']; statuses[iv]='READY' if valid and full and iv not in acquisition_error else ('FAILED' if iv in acquisition_error and not a['rows'] else 'PARTIAL')
        for g in a['gaps']: gaprows.append({'interval':iv,'gap_start_utc':iso(g[0]),'gap_end_utc':iso(g[-1]),'missing_bars':len(g),'kind':'INTERNAL_OR_COVERAGE'})
        if a['prefix'][0]: gaprows.append({'interval':iv,'gap_start_utc':a['prefix'][0],'gap_end_utc':a['prefix'][1],'missing_bars':'','kind':'UNAVAILABLE_PREFIX'})
        if a['suffix'][0]: gaprows.append({'interval':iv,'gap_start_utc':a['suffix'][0],'gap_end_utc':a['suffix'][1],'missing_bars':'','kind':'UNAVAILABLE_SUFFIX'})
        sumrows.append({'interval':iv,'status':statuses[iv],'first_timestamp_utc':a['first'],'last_timestamp_utc':a['last'],'row_count':a['rows'],'expected_timestamps':a['expected'],'observed_timestamps':a['observed'],'missing_bar_count':a['missing'],'gap_episodes':len(a['gaps']),'duplicate_timestamps':a['duplicates'],'nonmonotonic_timestamps':a['nonmonotonic'],'ohlc_violations':a['bad_ohlc'],'nonpositive_prices':a['nonpositive'],'negative_volume_or_turnover':a['negative_vq'],'utc_alignment_errors':a['alignment'],'incomplete_terminal_bars':0,'sha256':a['hash'],'byte_size':a['bytes'],'unavailable_prefix':':'.join(a['prefix']),'unavailable_suffix':':'.join(a['suffix'])})
    write_csv('integrity_summary.csv',list(sumrows[0]),sumrows); write_csv('gap_episodes.csv',['interval','gap_start_utc','gap_end_utc','missing_bars','kind'],gaprows)
    c3=compare(aggregate(raw['3'],180,900),raw['15'],['o','h','l','c','v','q']); c5=compare(aggregate(raw['5'],300,900),raw['15'],['o','h','l','c','v','q']); c1=compare(aggregate(raw['15'],900,3600),one,['o','h','l','c'])
    if c1['mismatch']:
        statuses['15']='CONFLICTED'
        for r in sumrows:
            if r['interval']=='15': r['status']='CONFLICTED'
    write_csv('integrity_summary.csv',list(sumrows[0]),sumrows)
    cross=[]
    for name,c in [('3m_to_15m',c3),('5m_to_15m',c5),('15m_to_1H',c1)]: cross.append({'comparison':name,'tolerance':canon(TOL),'overlap_bars':c['overlap'],'exact_match_bars':c['exact'],'mismatch_bars':c['mismatch'],'maximum_absolute_difference':c['maxabs'],'maximum_relative_difference':c['maxrel'],'mismatch_timestamp_samples':c['samples']})
    write_csv('cross_interval_validation.csv',list(cross[0]),cross)
    ready=all(statuses[x]=='READY' for x in statuses) and all(c['mismatch']==0 for c in (c3,c5,c1))
    blockers=[] if ready else ['One or more native intervals are not READY or cross-interval equality does not meet the declared tolerance.']
    manifest={'task_id':'EXP-023-ADA-LOWER-TIMEFRAME-DATA','endpoint':ENDPOINT,'request_parameters':{'category':'linear','symbol':'ADAUSDT','intervals':['3','5','15'],'limit':1000},'frozen_1h_source':str(SOURCE_1H.relative_to(ROOT)),'frozen_range_utc':[iso(start),iso(end)],'schema':SCHEMA,'canonical_decimal_tolerance':canon(TOL),'raw_archives':{iv:{'path':str(RAW/f'ADAUSDT_{iv}m.csv'),'sha256':audits[iv]['hash'],'bytes':audits[iv]['bytes'],'status':statuses[iv]} for iv in INTERVALS},'cross_interval_validation':{'3m_to_15m':c3,'5m_to_15m':c5,'15m_to_1H':c1},'EXP022_RERUN_READY':ready,'blockers':blockers,'verdict':'READY' if ready else 'DATA_NOT_READY'}
    with open(OUT/'data_manifest.json','w') as f: json.dump(manifest,f,indent=2,sort_keys=True); f.write('\n')
    report=['# EXP-023 — ADA lower-timeframe data','',f"Status: {manifest['verdict']}",'','## Data used','',f"Official Bybit V5 public linear ADAUSDT kline responses only; frozen comparison range is {iso(start)} through {iso(end)} from the committed EXP-021-selected 1H archive. No detector, representation comparison, or downstream analysis was run.",'','## API acquisition facts','',f"Endpoint: `{ENDPOINT}`. Parameters: category=linear, symbol=ADAUSDT, intervals 3/5/15, limit=1000. Full request/retry history is in `acquisition_log.csv`. Raw archives are local-only at the paths frozen in `data_manifest.json`.",'','## Local validation results','']
    report += [f"- {r['interval']}m: {r['status']}; {r['row_count']}/{r['expected_timestamps']} expected rows; missing {r['missing_bar_count']}; SHA-256 `{r['sha256']}`." for r in sumrows]
    report += ['', 'Cross-interval results use complete UTC-aligned components and tolerance '+canon(TOL)+'.', '']
    report += [f"- {x['comparison']}: {x['exact_match_bars']}/{x['overlap_bars']} exact, {x['mismatch_bars']} mismatches; max absolute {x['maximum_absolute_difference']}; max relative {x['maximum_relative_difference']}." for x in cross]
    report += ['', '## Verdict and next actions','',f"**{manifest['verdict']}** — `EXP022_RERUN_READY={str(ready).lower()}`."]
    if blockers: report += ['Blockers:'] + [f'- {x}' for x in blockers]
    (OUT/'REPORT.md').write_text('\n'.join(report)+'\n')
    print(json.dumps({'interval_status':statuses,'raw_paths':manifest['raw_archives'],'equality':[c3,c5,c1],'EXP022_RERUN_READY':ready,'report':str(OUT/'REPORT.md')},sort_keys=True))
if __name__=='__main__': main()
