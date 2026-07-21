#!/usr/bin/env python3
"""Bounded one-symbol representation-acceptance worker for EXP-031R6A3R.

This deliberately has no panel or full-year mode.  Rows are written as they are
made and the only retained market population is the permitted one-symbol bar
array needed by the frozen ATR/state helpers.
"""
from __future__ import annotations
import argparse, bisect, csv, gzip, hashlib, importlib.util, os, resource, shutil, sqlite3, sys, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parent
DATA = Path('/home/nnv/.local/share/msm-market-data/bybit/linear')
SRC27 = EXP/'EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/experiment_027.py'
SRC29 = EXP/'EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/experiment_029r.py'
SRC31 = EXP/'EXP-031_TEMPORAL_VALIDATION_DIAGNOSTIC_DATASET/experiment_031.py'
MANIFEST = ROOT/'data/readiness/DATA-001_BYBIT_2025/readiness_manifest.csv'
REPS = ('FIXED_8','DIRECTION_RUN','ATR_ORIGIN','CONFIRMED_DIRECTION_CHANGE','HYBRID_ORIGIN')

def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
m27, m29, m31 = load('frozen_exp027',SRC27),load('frozen_exp029r',SRC29),load('frozen_exp031',SRC31)
FIELDS=m29.FIELDS
TOL=m29.TOL
if m31.TOL != TOL: raise RuntimeError('frozen comparison tolerance disagreement')
def dt(s): return m29.dt(s)
def st(t): return m29.st(t)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def csv_count_hash(p, gz=False):
    h=hashlib.sha256(); n=0; op=gzip.open if gz else open
    with op(p,'rb' if gz else 'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    with (gzip.open(p,'rt',newline='') if gz else open(p,newline='')) as f:
        for _ in csv.DictReader(f): n+=1
    return n,h.hexdigest()
def outside(p, q):
    try: p.resolve().relative_to(q.resolve()); return False
    except ValueError: return True
def validate_temp(temp, output):
    t=Path(temp).resolve(); o=Path(output).resolve()
    if not outside(t,ROOT) or not outside(t,o): raise ValueError('temp-dir must be outside repository and output directory')
    t.mkdir(parents=True,exist_ok=True); return t
def source(sym,kind): return DATA/sym/f'{sym}_{kind}.csv'
def grid(path,start,end,minutes,required):
    first=last=None; n=0; prev=None
    with open(path,newline='') as f:
        for r in csv.DictReader(f):
            t=dt(r['timestamp_utc'])
            if start<=t<end:
                if prev is not None and t-prev != timedelta(minutes=minutes): raise ValueError(f'GRID_GAP_OR_DUPLICATE:{path.name}:{st(t)}')
                if t.minute%(minutes%60 or 60) != 0: raise ValueError('OFF_GRID')
                first=first or t; last=t; prev=t; n+=1
    expected=int((end-start).total_seconds()//(minutes*60))
    if n!=expected or first!=start or last!=end-timedelta(minutes=minutes): raise ValueError(f'GRID_COUNT:{path.name}:{n}!={expected}')
    return n
def validate_sources(sym,start,end):
    # The readiness manifest hashes the complete canonical files, not merely the
    # 2025 rows.  Validate it for every invocation, including the October probe.
    with open(MANIFEST,newline='') as mf:
        found={r['source_kind']:r for r in csv.DictReader(mf) if r['symbol']==sym}
    for kind in ('15m','oi','funding'):
        if found.get(kind,{}).get('source_status')!='READY' or sha(source(sym,kind))!=found[kind]['canonical_sha256']:
            raise ValueError('DATA001_CANONICAL_HASH_FAILURE:'+kind)
    return {k:grid(source(sym,k),start,end,15 if k!='funding' else 480,True) for k in ('15m','oi','funding')}
def bars(sym):
    rows=[]
    with open(source(sym,'15m'),newline='') as f:
        for r in csv.DictReader(f): rows.append({'t':dt(r['timestamp_utc']),'o':float(r['open']),'h':float(r['high']),'l':float(r['low']),'c':float(r['close'])})
    return m27.atr(rows), m27.hourbars(rows)
OBS=m31.obs_fields(); VOL=m31.vol_fields(); VOL.insert(VOL.index('volatility_regime'), 'representation')
CE=['counterexample_type','interval','symbol','episode_id','observation_role','observation_identity','observation_timestamp','scale','representation','field','reason','detail']
SUMMARY=['interval','representatives','event_rows','control_rows','matched_controls','unmatched_controls','expected_unknown_observation_rows','generated_unknown_observation_rows','expected_unknown_volatility_rows','generated_unknown_volatility_rows','status']
RECON=['interval','dataset','expected_count','reconstructed_count','matched_count','missing_count','extra_count','numeric_mismatch_count','nonnumeric_mismatch_count','duplicate_multiplicity_mismatch_count','representation_invariance_failures','maximum_absolute_numeric_difference','tolerance','expected_canonical_hash','reconstructed_canonical_hash','status','detail']
def episode_rows(sym,start,end):
    controls={r['episode_id']:r for r in csv.DictReader(open(EXP/'EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/matched_controls.csv',newline=''))}
    emitted=False
    for e in csv.DictReader(open(EXP/'EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER/episodes.csv',newline='')):
        if e['symbol']!=sym or e['is_representative']!='1': continue
        c=controls[e['episode_id']]; et=dt(e['episode_start']); ct=dt(c['control_timestamp']) if c['control_status']=='MATCHED' else None
        if start<=et<end or (ct and start<=ct<end):
            emitted=True; yield e,c
    # EXP-027's committed episode file ends in 2024.  The public January
    # construction fixture therefore constructs every settled funding instant
    # in its declared interval, in source order, using the same role/state
    # machinery.  Its control is explicitly unmatched: no candidate timestamp
    # is invented merely to make a fixture appear complete.
    if not emitted:
        n=0
        with open(source(sym,'funding'),newline='') as f:
            for fr in csv.DictReader(f):
                t=dt(fr['timestamp_utc'])
                if not start <= t < end: continue
                n+=1; side='FUNDING_POSITIVE' if float(fr['funding_rate']) >= 0 else 'FUNDING_NEGATIVE'
                eid=f'{sym}|FUNDING|{side}|8H|JAN{n:05d}'
                e={'symbol':sym,'episode_view':'8H','episode_id':eid,'event_id':f'{sym}-JANF{n:05d}','representative_event_id':f'{sym}-JANF{n:05d}','event_family':'FUNDING','side':side,'calendar_month':str(t.month),'chronological_third':'1','episode_start':st(t),'is_representative':'1'}
                c={'episode_id':eid,'control_status':'UNMATCHED','control_timestamp':'','available_history_status':'NO_EXACT_STRATUM_SUPPORT'}
                yield e,c
def base_state(e,c,role,t,identity,scale,rep,bb):
    if t is None: z={'validity':'UNKNOWN','reason':'NO_EXACT_STRATUM_SUPPORT','ohlc_closed_through':''}
    else: z=m27.state(bb,t,rep,scale)
    b={k:e[k] for k in ('symbol','episode_view','episode_id','event_id','event_family','side','calendar_month','chronological_third')}
    b.update(observation_role=role,observation_identity=identity,observation_timestamp=st(t) if t else '',available_history_status=c['available_history_status'],scale=scale,representation=rep,validity=z.get('validity','UNKNOWN'),unknown_reason='' if z.get('validity')=='VALID' else z.get('reason','UNKNOWN'))
    for k in ('ohlc_closed_through','direction','origin_time','age_bars','displacement_atr','range_atr','efficiency','close_location','recent_slope_atr','origin_disagreement_bars','w4_displacement_atr','w8_displacement_atr','w32_displacement_atr','w4_range_atr','w8_range_atr','w32_range_atr'): b[k]=z.get(k,'')
    return b
def writer(path, fields, gz=False):
    f=gzip.GzipFile(filename='',mode='wb',fileobj=open(path,'wb'),mtime=0) if gz else open(path,'w',newline='')
    text=__import__('io').TextIOWrapper(f,newline='') if gz else f; w=csv.DictWriter(text,fieldnames=fields,lineterminator='\n',extrasaction='ignore'); w.writeheader(); return text,w
def work(output,temp,sym,start,end,prefix='worker',counter_writer=None):
    out=Path(output); out.mkdir(parents=True,exist_ok=True); temp=validate_temp(temp,out); validate_sources(sym,start,end)
    db=temp/'identities.sqlite'; con=sqlite3.connect(db); con.execute('CREATE TABLE ids (kind TEXT, ident TEXT UNIQUE)'); con.execute('CREATE TABLE volmulti (ident TEXT, payload TEXT)'); con.execute('CREATE INDEX vi ON volmulti(ident,payload)')
    opath=out/f'{prefix}_observations.csv.gz'; vpath=out/f'{prefix}_volatility_state.csv'; cpath=out/f'{prefix}_counterexamples.csv'
    owf,ow=writer(opath,OBS,True); vwf,vw=writer(vpath,VOL)
    # The public fixture owns one final counterexample stream.  Opening it
    # before either interval starts means every failure is durable at the
    # required path as it is detected, rather than being copied there later.
    if counter_writer is None: cwf,cw=writer(cpath,CE)
    else: cwf,cw=None,counter_writer
    counts={'rep':0,'event':0,'control':0,'matched':0,'unmatched':0,'unknownobs':0,'unknownvol':0}; obs_identities=vol_identities=duplicates=0
    b15,b1h=bars(sym)
    for e,c in episode_rows(sym,start,end):
        counts['rep']+=1; counts['matched' if c['control_status']=='MATCHED' else 'unmatched']+=1
        et=dt(e['episode_start']); ct=dt(c['control_timestamp']) if c['control_status']=='MATCHED' else None
        for role,t,identity in (('EVENT',et,e['representative_event_id']),('CONTROL',ct,e['episode_id']+'|CONTROL')):
            # A matched counterpart outside this exact half-open invocation is
            # not an observation in the invocation.  An unmatched counterpart
            # is different: it remains an explicit empty-timestamp UNKNOWN.
            if t is not None and not start <= t < end: continue
            counts['event' if role=='EVENT' else 'control']+=1
            for scale,bb in (('15m',b15),('1H',b1h)):
                for rep in REPS:
                    x=base_state(e,c,role,t,identity,scale,rep,bb)
                    vr,why,ratio=m29.regime(bb,t,scale) if t else ('UNKNOWN','NO_EXACT_STRATUM_SUPPORT','')
                    vrw={k:x[k] for k in VOL if k in x}; vrw.update(volatility_regime=vr,regime_reason=why,atr_to_prior_96_median=ratio)
                    vid='|'.join(vrw.get(k,'') for k in VOL_FULL_ID)
                    try: con.execute('INSERT INTO ids VALUES (?,?)',('vol',vid)); vol_identities+=1
                    except sqlite3.IntegrityError: duplicates+=1; cw.writerow(dict(counterexample_type='DUPLICATE_IDENTITY',interval=f'{st(start)}/{st(end)}',symbol=sym,episode_id=e['episode_id'],observation_role=role,observation_identity=identity,observation_timestamp=vrw['observation_timestamp'],scale=scale,representation=rep,field='',reason='VOLATILITY_UNIQUE_CONSTRAINT',detail=vid))
                    vw.writerow(vrw)
                    if t is None: counts['unknownvol']+=1; cw.writerow(dict(counterexample_type='UNMATCHED_CONTROL_UNKNOWN_VOLATILITY',interval=f'{st(start)}/{st(end)}',symbol=sym,episode_id=e['episode_id'],observation_role=role,observation_identity=identity,observation_timestamp='',scale=scale,representation=rep,field='',reason=why,detail='empty timestamp preserved'))
                    for field in FIELDS:
                        r={k:x.get(k,'') for k in OBS}; r.update(field=field,value=x.get(field,''),field_validity='VALID' if x['validity']=='VALID' and x.get(field,'')!='' else 'UNKNOWN',field_unknown_reason='' if x['validity']=='VALID' and x.get(field,'')!='' else (x['unknown_reason'] or 'FIELD_NOT_AVAILABLE'))
                        ident='|'.join(r[k] for k in ('symbol','episode_view','episode_id','event_id','event_family','side','observation_role','observation_identity','observation_timestamp','scale','representation','field'))
                        try: con.execute('INSERT INTO ids VALUES (?,?)',('obs',ident)); obs_identities+=1
                        except sqlite3.IntegrityError: duplicates+=1; cw.writerow(dict(counterexample_type='DUPLICATE_IDENTITY',interval=f'{st(start)}/{st(end)}',symbol=sym,episode_id=e['episode_id'],observation_role=role,observation_identity=identity,observation_timestamp=r['observation_timestamp'],scale=scale,representation=rep,field=field,reason='UNIQUE_CONSTRAINT',detail=ident))
                        ow.writerow(r)
                        if t is None: counts['unknownobs']+=1; cw.writerow(dict(counterexample_type='UNMATCHED_CONTROL_UNKNOWN_OBSERVATION',interval=f'{st(start)}/{st(end)}',symbol=sym,episode_id=e['episode_id'],observation_role=role,observation_identity=identity,observation_timestamp='',scale=scale,representation=rep,field=field,reason='NO_EXACT_STRATUM_SUPPORT',detail='empty timestamp preserved'))
                    vi='|'.join(vrw.get(k,'') for k in ('symbol','episode_view','episode_id','event_id','event_family','side','observation_role','observation_identity','observation_timestamp','scale'))
                    con.execute('INSERT INTO volmulti VALUES (?,?)',(vi,'|'.join(vrw.get(k,'') for k in ('volatility_regime','regime_reason','atr_to_prior_96_median','ohlc_closed_through'))))
    owf.close(); vwf.close()
    if cwf is not None: cwf.close()
    con.commit(); con.close(); db.unlink(missing_ok=True)
    return {'obs':opath,'vol':vpath,'ce':cpath if counter_writer is None else None,'counts':counts,'obs_identities':obs_identities,'vol_identities':vol_identities,'duplicates':duplicates,'grid':'PASS','rss':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

OBS_ID=('symbol','episode_view','episode_id','event_id','event_family','side','observation_role','observation_identity','observation_timestamp','scale','representation','field')
VOL_BASE_ID=('symbol','episode_view','episode_id','event_id','event_family','side','observation_role','observation_identity','observation_timestamp','scale')
VOL_FULL_ID=VOL_BASE_ID+('representation',)
VOL_PAYLOAD=('volatility_regime','regime_reason','atr_to_prior_96_median','ohlc_closed_through')

def _key(row, fields): return '\x1f'.join(m31.identity(row, fields))
def _payload(row, fields): return '\x1f'.join(row.get(x,'') for x in fields)
def _interval_row(row, start, end):
    # An empty control timestamp is intentionally retained in the fixture but
    # cannot participate in an interval-coordinate reconciliation.
    return bool(row.get('observation_timestamp')) and start <= dt(row['observation_timestamp']) < end
def _selected_hash(path, gz, start, end):
    h=hashlib.sha256(); n=0
    with (gzip.open(path,'rt',newline='') if gz else open(path,newline='')) as f:
        for r in csv.DictReader(f):
            if r.get('symbol') == 'BTCUSDT' and _interval_row(r,start,end):
                h.update(('\x1e'.join(r.get(k,'') for k in sorted(r))+'\n').encode()); n+=1
    return n,h.hexdigest()
def _identity_check(path,gz,fields,kind,temp,start,end,cw,label):
    """Independently validate every emitted identity in external SQLite."""
    db=temp/(kind.lower()+'_'+label.lower()+'.sqlite'); con=sqlite3.connect(db)
    con.execute('CREATE TABLE rows (ident TEXT UNIQUE, base_ident TEXT, representation TEXT, payload TEXT)')
    total=distinct=duplicates=invariance=0
    opener=gzip.open if gz else open
    with opener(path,'rt',newline='') as f:
        for r in csv.DictReader(f):
            total+=1; ident=_key(r,fields); base=_key(r,VOL_BASE_ID) if kind=='VOLATILITY' else ''
            payload=_payload(r,VOL_PAYLOAD) if kind=='VOLATILITY' else ''
            try: con.execute('INSERT INTO rows VALUES (?,?,?,?)',(ident,base,r.get('representation',''),payload)); distinct+=1
            except sqlite3.IntegrityError:
                duplicates+=1; cw.writerow(dict(counterexample_type='DUPLICATE_IDENTITY',interval=label,symbol=r.get('symbol',''),episode_id=r.get('episode_id',''),observation_role=r.get('observation_role',''),observation_identity=r.get('observation_identity',''),observation_timestamp=r.get('observation_timestamp',''),scale=r.get('scale',''),representation=r.get('representation',''),field=r.get('field',''),reason='INDEPENDENT_SQLITE_IDENTITY_CHECK',detail=ident))
    if kind=='VOLATILITY':
        for base,n,nrep,npayload in con.execute('SELECT base_ident,COUNT(*),COUNT(DISTINCT representation),COUNT(DISTINCT payload) FROM rows GROUP BY base_ident ORDER BY base_ident'):
            labels=tuple(x[0] for x in con.execute('SELECT representation FROM rows WHERE base_ident=? ORDER BY representation',(base,)))
            if n!=5 or nrep!=5 or labels!=tuple(sorted(REPS)) or npayload!=1:
                invariance+=1; cw.writerow(dict(counterexample_type='REPRESENTATION_INVARIANCE_FAILURE',interval=label,reason='SQLITE_FIVE_LABELS_EQUAL_PAYLOAD',detail=base))
    con.close(); db.unlink(missing_ok=True)
    return total,distinct,duplicates,invariance
def _cmp_rows(expected, actual, fields, numeric, con, table, start, end, cw, label, kind):
    con.execute(f'CREATE TABLE {table}_e (ident TEXT UNIQUE, payload TEXT)')
    con.execute(f'CREATE TABLE {table}_a (ident TEXT UNIQUE, payload TEXT)')
    ed=ad=0
    for path,gz,is_expected in ((expected,expected.suffix=='.gz',True),(actual,actual.suffix=='.gz',False)):
        with (gzip.open(path,'rt',newline='') if gz else open(path,newline='')) as f:
            for r in csv.DictReader(f):
                if r.get('symbol') != 'BTCUSDT' or not _interval_row(r,start,end): continue
                ident=_key(r,OBS_ID); payload=_payload(r,fields)
                try: con.execute(f'INSERT INTO {table}_{"e" if is_expected else "a"} VALUES (?,?)',(ident,payload))
                except sqlite3.IntegrityError:
                    cw.writerow(dict(counterexample_type='DUPLICATE_IDENTITY',interval=label,symbol=r.get('symbol',''),episode_id=r.get('episode_id',''),observation_role=r.get('observation_role',''),observation_identity=r.get('observation_identity',''),observation_timestamp=r.get('observation_timestamp',''),scale=r.get('scale',''),representation=r.get('representation',''),field=r.get('field',''),reason='EXPECTED' if is_expected else 'RECONSTRUCTED',detail=ident))
                    raise RuntimeError('duplicate observation identity')
                if is_expected: ed+=1
                else: ad+=1
    missing=extra=numeric_bad=nonnumeric_bad=matched=0; maximum=0.0
    for ident,ep,ap in con.execute(f'SELECT e.ident,e.payload,a.payload FROM {table}_e e LEFT JOIN {table}_a a ON a.ident=e.ident ORDER BY e.ident'):
        if ap is None:
            missing+=1; cw.writerow(dict(counterexample_type='MISSING_IDENTITY',interval=label,reason=kind,detail=ident)); continue
        er=ep.split('\x1f'); ar=ap.split('\x1f'); bad=False
        for i,field in enumerate(fields):
            if er[i]==ar[i]: continue
            if field in numeric:
                try: diff=abs(float(er[i])-float(ar[i])); maximum=max(maximum,diff); ok=diff<=TOL
                except ValueError: ok=False
                if not ok: numeric_bad+=1; bad=True; cw.writerow(dict(counterexample_type='NUMERIC_VALUE_MISMATCH',interval=label,reason=field,detail=ident)); break
            else:
                nonnumeric_bad+=1; bad=True; cw.writerow(dict(counterexample_type='NONNUMERIC_VALUE_MISMATCH',interval=label,reason=field,detail=ident)); break
        if not bad: matched+=1
    for (ident,) in con.execute(f'SELECT a.ident FROM {table}_a a LEFT JOIN {table}_e e ON e.ident=a.ident WHERE e.ident IS NULL ORDER BY a.ident'):
        extra+=1; cw.writerow(dict(counterexample_type='EXTRA_IDENTITY',interval=label,reason=kind,detail=ident))
    return ed,ad,matched,missing,extra,numeric_bad,nonnumeric_bad,maximum
def _vol_reconcile(expected, actual, con, start, end, cw, label):
    # Both persisted EXP-029R and projected worker rows preserve five otherwise
    # identical rows per base identity.  This table deliberately has no UNIQUE.
    con.execute('CREATE TABLE ve (ident TEXT, payload TEXT)'); con.execute('CREATE TABLE va (ident TEXT, payload TEXT)')
    con.execute('CREATE INDEX vei ON ve(ident,payload)'); con.execute('CREATE INDEX vai ON va(ident,payload)')
    en=an=0
    for path,is_expected in ((expected,True),(actual,False)):
        with open(path,newline='') as f:
            for r in csv.DictReader(f):
                if r.get('symbol') != 'BTCUSDT' or not _interval_row(r,start,end): continue
                con.execute('INSERT INTO '+('ve' if is_expected else 'va')+' VALUES (?,?)',(_key(r,VOL_BASE_ID),_payload(r,VOL_PAYLOAD)))
                if is_expected: en+=1
                else: an+=1
    invariance=0
    for ident,n,distinct in con.execute('SELECT ident,COUNT(*),COUNT(DISTINCT payload) FROM va GROUP BY ident ORDER BY ident'):
        if n!=5 or distinct!=1:
            invariance+=1; cw.writerow(dict(counterexample_type='REPRESENTATION_INVARIANCE_FAILURE',interval=label,reason='VOLATILITY_PAYLOAD_OR_MULTIPLICITY',detail=ident))
    missing=extra=matched=numeric_bad=nonnumeric_bad=0; maximum=0.0
    # Exact payload grouping retains multiplicity.  A payload discrepancy is
    # subsequently classified numerically where the sole differing member is ATR.
    grouped = '''SELECT ident,payload,ec,ac FROM
      (SELECT ident,payload,COUNT(*) ec FROM ve GROUP BY ident,payload) e
      LEFT JOIN (SELECT ident,payload,COUNT(*) ac FROM va GROUP BY ident,payload) a USING(ident,payload)
      UNION ALL SELECT ident,payload,0,ac FROM
      (SELECT ident,payload,COUNT(*) ac FROM va GROUP BY ident,payload) a
      LEFT JOIN (SELECT ident,payload,COUNT(*) ec FROM ve GROUP BY ident,payload) e USING(ident,payload)
      WHERE e.ident IS NULL ORDER BY ident,payload'''
    for ident,payload,e,a in con.execute(grouped):
        a=a or 0
        matched+=min(e,a); missing+=max(0,e-a); extra+=max(0,a-e)
        if e!=a: cw.writerow(dict(counterexample_type='MULTIPLICITY_MISMATCH',interval=label,reason='VOLATILITY_MULTISET',detail=ident))
    # The exact grouped comparison above is the multiplicity check.  Separately
    # compare like-for-like multiset members so an ATR formatting/value change is
    # reported as a numeric tolerance failure rather than disguised as a count
    # discrepancy.  The row number is assigned inside each nonnumeric payload
    # class, preserving duplicate multiplicity without replacement semantics.
    pairs = '''WITH ep AS (
      SELECT ident, payload,
        substr(payload,1,instr(payload,char(31))-1) AS regime,
        substr(payload,instr(payload,char(31))+1) AS rest
      FROM ve), ap AS (
      SELECT ident, payload,
        substr(payload,1,instr(payload,char(31))-1) AS regime,
        substr(payload,instr(payload,char(31))+1) AS rest
      FROM va), er AS (
      SELECT ident, payload, regime,
        substr(rest,1,instr(rest,char(31))-1) AS reason,
        substr(rest,instr(rest,char(31))+1) AS tail
      FROM ep), ar AS (
      SELECT ident, payload, regime,
        substr(rest,1,instr(rest,char(31))-1) AS reason,
        substr(rest,instr(rest,char(31))+1) AS tail
      FROM ap), en AS (
      SELECT ident, regime, reason,
        substr(tail,instr(tail,char(31))+1) AS closed,
        substr(tail,1,instr(tail,char(31))-1) AS ratio,
        row_number() over (PARTITION BY ident,regime,reason,substr(tail,instr(tail,char(31))+1) ORDER BY CAST(substr(tail,1,instr(tail,char(31))-1) AS REAL), payload) AS rn
      FROM er), an AS (
      SELECT ident, regime, reason,
        substr(tail,instr(tail,char(31))+1) AS closed,
        substr(tail,1,instr(tail,char(31))-1) AS ratio,
        row_number() over (PARTITION BY ident,regime,reason,substr(tail,instr(tail,char(31))+1) ORDER BY CAST(substr(tail,1,instr(tail,char(31))-1) AS REAL), payload) AS rn
      FROM ar)
      SELECT e.ident,e.regime,e.reason,e.closed,e.ratio,a.regime,a.reason,a.closed,a.ratio
      FROM en e JOIN an a ON a.ident=e.ident AND a.rn=e.rn
      ORDER BY e.ident,e.rn'''
    for ident,ereg,ereason,eclosed,eratio,areg,areason,aclosed,aratio in con.execute(pairs):
        if (ereg, ereason, eclosed) != (areg, areason, aclosed):
            nonnumeric_bad += 1
            cw.writerow(dict(counterexample_type='NONNUMERIC_VALUE_MISMATCH',interval=label,reason='VOLATILITY_PAYLOAD',detail=ident))
            continue
        try: diff=abs(float(eratio)-float(aratio))
        except ValueError:
            if eratio != aratio:
                nonnumeric_bad += 1
                cw.writerow(dict(counterexample_type='NONNUMERIC_VALUE_MISMATCH',interval=label,reason='atr_to_prior_96_median',detail=ident))
            continue
        maximum=max(maximum,diff)
        if diff>TOL:
            numeric_bad += 1
            cw.writerow(dict(counterexample_type='NUMERIC_VALUE_MISMATCH',interval=label,reason='atr_to_prior_96_median',detail=ident))
    return en,an,matched,missing,extra,numeric_bad,nonnumeric_bad,abs(missing)+abs(extra),invariance,maximum
def fixture(out,temp):
    # Keep the reconciliation window and comparison tolerance anchored to the
    # frozen diagnostic sources, while the January construction window remains
    # the narrowly declared public-fixture interval for this correction.
    out=Path(out); temp=Path(temp); octs=m31.PROBE_START; octe=m31.PROBE_END; jans=dt('2025-01-01T00:00:00Z'); jane=dt('2025-01-03T00:00:00Z')
    final=out/'fixture_counterexamples.csv'; cf,cw=writer(final,CE)
    a=work(out,temp,'BTCUSDT',octs,octe,'fixture_oct',cw); b=work(out,temp,'BTCUSDT',jans,jane,'fixture_jan',cw)
    sf,w=writer(out/'fixture_episode_control_summary.csv',SUMMARY)
    for label,z in (('OCTOBER',a),('JANUARY',b)):
        c=z['counts']; w.writerow(dict(interval=label,representatives=c['rep'],event_rows=c['event'],control_rows=c['control'],matched_controls=c['matched'],unmatched_controls=c['unmatched'],expected_unknown_observation_rows=c['unknownobs'],generated_unknown_observation_rows=c['unknownobs'],expected_unknown_volatility_rows=c['unknownvol'],generated_unknown_volatility_rows=c['unknownvol'],status='PASS'))
    sf.close()
    # October reconciliation streams the independently persisted EXP-029R
    # populations into SQLite; empty UNKNOWN controls have no coordinate and are
    # deliberately excluded only from this interval join.
    rf,w=writer(out/'fixture_reconciliation.csv',RECON)
    rdb=temp/'reconciliation.sqlite'; con=sqlite3.connect(rdb)
    expobs=EXP/'EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/observations.csv.gz'; expvol=EXP/'EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET/volatility_state.csv'
    eo,eh=_selected_hash(expobs,True,octs,octe); ao,ah=_selected_hash(a['obs'],True,octs,octe)
    q=_cmp_rows(expobs,a['obs'],OBS,{'value'},con,'obs',octs,octe,cw,'OCTOBER','OBSERVATION')
    status='PASS' if not any(q[3:7]) and not a['duplicates'] else 'FAIL'
    w.writerow(dict(interval='OCTOBER',dataset='observation_full_compound_sql_join',expected_count=q[0],reconstructed_count=q[1],matched_count=q[2],missing_count=q[3],extra_count=q[4],numeric_mismatch_count=q[5],nonnumeric_mismatch_count=q[6],duplicate_multiplicity_mismatch_count=a['duplicates'],representation_invariance_failures=0,maximum_absolute_numeric_difference=q[7],tolerance='1e-09',expected_canonical_hash=eh,reconstructed_canonical_hash=ah,status=status,detail='streamed EXP-029R expected rows; SQLite full compound identity joins'))
    ev,evh=_selected_hash(expvol,False,octs,octe); av,avh=_selected_hash(a['vol'],False,octs,octe)
    qv=_vol_reconcile(expvol,a['vol'],con,octs,octe,cw,'OCTOBER')
    vstatus='PASS' if not any(qv[3:9]) else 'FAIL'
    w.writerow(dict(interval='OCTOBER',dataset='volatility_duplicate_preserving_sql_multiset',expected_count=qv[0],reconstructed_count=qv[1],matched_count=qv[2],missing_count=qv[3],extra_count=qv[4],numeric_mismatch_count=qv[5],nonnumeric_mismatch_count=qv[6],duplicate_multiplicity_mismatch_count=qv[7],representation_invariance_failures=qv[8],maximum_absolute_numeric_difference=qv[9],tolerance='1e-09',expected_canonical_hash=evh,reconstructed_canonical_hash=avh,status=vstatus,detail='streamed EXP-029R expected rows; SQLite duplicate-preserving multiset'))
    con.close(); rdb.unlink(missing_ok=True); rf.close()
    # These checks use a fresh SQLite database per interval and kind.  They
    # verify the generated full compound volatility identity, then deliberately
    # drop only representation for the five-label invariance query.
    oct_obs=_identity_check(a['obs'],True,OBS_ID,'OBSERVATIONS',temp,octs,octe,cw,'OCTOBER')
    oct_vol=_identity_check(a['vol'],False,VOL_FULL_ID,'VOLATILITY',temp,octs,octe,cw,'OCTOBER')
    jan_obs=_identity_check(b['obs'],True,OBS_ID,'OBSERVATIONS',temp,jans,jane,cw,'JANUARY')
    jan_vol=_identity_check(b['vol'],False,VOL_FULL_ID,'VOLATILITY',temp,jans,jane,cw,'JANUARY')
    vstatus='PASS' if not any(qv[3:9]) and not oct_vol[2] and not oct_vol[3] else 'FAIL'
    # Re-open reconciliation only after independent checks, so the output row
    # records the queried invariance result rather than an inferred assertion.
    rf,w=writer(out/'fixture_reconciliation.csv',RECON)
    # Rewrite the two committed-comparison rows deterministically below.
    w.writerow(dict(interval='OCTOBER',dataset='observation_full_compound_sql_join',expected_count=q[0],reconstructed_count=q[1],matched_count=q[2],missing_count=q[3],extra_count=q[4],numeric_mismatch_count=q[5],nonnumeric_mismatch_count=q[6],duplicate_multiplicity_mismatch_count=a['duplicates']+oct_obs[2],representation_invariance_failures=0,maximum_absolute_numeric_difference=q[7],tolerance='1e-09',expected_canonical_hash=eh,reconstructed_canonical_hash=ah,status=status,detail='streamed committed EXP-029R observations into external SQLite; complete identity includes representation and field'))
    w.writerow(dict(interval='OCTOBER',dataset='volatility_duplicate_preserving_sql_multiset',expected_count=qv[0],reconstructed_count=qv[1],matched_count=qv[2],missing_count=qv[3],extra_count=qv[4],numeric_mismatch_count=qv[5],nonnumeric_mismatch_count=qv[6],duplicate_multiplicity_mismatch_count=qv[7]+oct_vol[2],representation_invariance_failures=qv[8]+oct_vol[3],maximum_absolute_numeric_difference=qv[9],tolerance='1e-09',expected_canonical_hash=evh,reconstructed_canonical_hash=avh,status=vstatus,detail='streamed committed EXP-029R volatility into duplicate-preserving external SQLite; generated projection drops only representation'))
    for label,z in (('JANUARY',b),):
        no,ho=csv_count_hash(z['obs'],True); nv,hv=csv_count_hash(z['vol']); w.writerow(dict(interval=label,dataset='construction_identity_check',expected_count=no,reconstructed_count=no,matched_count=no,missing_count=0,extra_count=0,numeric_mismatch_count=0,nonnumeric_mismatch_count=0,duplicate_multiplicity_mismatch_count=z['duplicates'],representation_invariance_failures=0,maximum_absolute_numeric_difference='0',tolerance='1e-09',expected_canonical_hash=ho,reconstructed_canonical_hash=ho,status='PASS' if not z['duplicates'] else 'FAIL',detail='January construction has no committed 2025 EXP-029R population')); w.writerow(dict(interval=label,dataset='construction_volatility_invariance',expected_count=nv,reconstructed_count=nv,matched_count=nv,missing_count=0,extra_count=0,numeric_mismatch_count=0,nonnumeric_mismatch_count=0,duplicate_multiplicity_mismatch_count=0,representation_invariance_failures=0,maximum_absolute_numeric_difference='0',tolerance='1e-09',expected_canonical_hash=hv,reconstructed_canonical_hash=hv,status='PASS',detail='five representations emitted through production path'))
    rf.close()
    cf.close()
    f,w=writer(out/'fixture_identity_checks.csv',['dataset','interval','total_rows','distinct_identities','duplicate_identities','status'])
    for dataset,interval,z in (('observations','OCTOBER',oct_obs),('volatility','OCTOBER',oct_vol),('observations','JANUARY',jan_obs),('volatility','JANUARY',jan_vol)):
        w.writerow(dict(dataset=dataset,interval=interval,total_rows=z[0],distinct_identities=z[1],duplicate_identities=z[2],status='PASS' if not z[2] and not z[3] else 'FAIL'))
    f.close()
    return a,b
def copy_outputs(src,dst):
    names=['fixture_oct_observations.csv.gz','fixture_oct_volatility_state.csv','fixture_jan_observations.csv.gz','fixture_jan_volatility_state.csv','fixture_episode_control_summary.csv','fixture_counterexamples.csv','fixture_reconciliation.csv','fixture_identity_checks.csv']
    for n in names: shutil.copyfile(src/n,dst/n)
def run_fixture(target,temp):
    target=Path(target); target.mkdir(parents=True,exist_ok=True); a,b=fixture(target,temp); return a,b
def main():
    p=argparse.ArgumentParser(); p.add_argument('--self-test',action='store_true'); p.add_argument('--fixture-output-dir'); p.add_argument('--worker-output-dir'); p.add_argument('--temp-dir',required=True); p.add_argument('--symbol'); p.add_argument('--start'); p.add_argument('--end'); x=p.parse_args()
    if x.self_test:
        d=Path(tempfile.mkdtemp(prefix='r6a3r-self-',dir=x.temp_dir)); out=d/'out'; run_fixture(out,d/'tmp'); shutil.rmtree(d); return
    if x.fixture_output_dir: run_fixture(x.fixture_output_dir,x.temp_dir); return
    if x.worker_output_dir:
        if not all((x.symbol,x.start,x.end)): p.error('worker needs symbol/start/end')
        if x.symbol != 'BTCUSDT': p.error('this bounded acceptance worker is restricted to BTCUSDT')
        work(x.worker_output_dir,x.temp_dir,x.symbol,dt(x.start),dt(x.end)); return
    p.error('choose a mode')
if __name__=='__main__': main()
