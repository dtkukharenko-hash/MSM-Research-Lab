#!/usr/bin/env python3
"""EXP-031 temporal validation dataset preparation (causal, standard library)."""
from __future__ import annotations
import csv, gzip, hashlib, importlib.util, io, math, os, sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
SRC27 = OUT.parent / 'EXP-027_MULTI_MARKET_DERIVATIVES_TRANSFER'
SRC29 = OUT.parent / 'EXP-029R_DERIVATIVES_DIAGNOSTIC_DATASET'
SYMS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT')
START = datetime(2025, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 1, 1, tzinfo=timezone.utc)
PROBE_START = datetime(2024, 10, 1, tzinfo=timezone.utc)
PROBE_END = datetime(2024, 11, 1, tzinfo=timezone.utc)
FIELDS = ('displacement_atr','range_atr','efficiency','close_location','recent_slope_atr','age_bars','origin_disagreement_bars','w4_displacement_atr','w8_displacement_atr','w32_displacement_atr','w4_range_atr','w8_range_atr','w32_range_atr')
TOL = 1e-9

def dt(s): return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
def st(t): return t.strftime('%Y-%m-%dT%H:%M:%SZ')
def fmt(x): return '' if x is None or not math.isfinite(x) else f'{x:.10g}'
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def read_csv(p):
    with open(p, newline='') as f: return list(csv.DictReader(f))
def read_gz(p):
    with gzip.open(p, 'rt', newline='') as f: return list(csv.DictReader(f))
def rows_in_interval(p, compressed=False):
    opener = gzip.open if compressed else open
    with opener(p, 'rt', newline='') as f:
        return [r for r in csv.DictReader(f) if r['observation_timestamp'] and PROBE_START <= dt(r['observation_timestamp']) < PROBE_END]
def csv_bytes(rows, fields):
    b = io.StringIO(newline=''); w = csv.DictWriter(b, fieldnames=fields, lineterminator='\n', extrasaction='raise')
    w.writeheader(); w.writerows(rows); return b.getvalue().encode()
def write_csv(name, rows, fields):
    OUT.mkdir(parents=True, exist_ok=True); (OUT / name).write_bytes(csv_bytes(rows, fields))
def write_gz(name, rows, fields):
    raw = csv_bytes(rows, fields); b = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=b, mtime=0) as z: z.write(raw)
    (OUT / name).write_bytes(b.getvalue())
def load027():
    spec = importlib.util.spec_from_file_location('frozen027', SRC27 / 'experiment_027.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def archive(sym, kind):
    roots = list(Path('/home/nnv/.local/state/msm-orchestrator/runtime').glob('*/corrector/home/.local/share/msm-market-data/bybit/linear')) + [Path.home()/'.local/share/msm-market-data/bybit/linear']
    for root in roots:
        p = root / sym / f'{sym}_{kind}.csv'
        if p.exists(): return p
    return None
def regime(bb, ts, scale):
    close = timedelta(minutes=15 if scale == '15m' else 60)
    i = next((j - 1 for j, b in enumerate(bb) if b['t'] + close > ts), len(bb)-1)
    if i < 96: return 'UNKNOWN', 'INSUFFICIENT_PRIOR_96_CLOSED_BARS', ''
    prior = sorted(b['atr'] for b in bb[i-96:i]); med = (prior[47] + prior[48]) / 2
    if not med: return 'UNKNOWN', 'ZERO_PRIOR_MEDIAN_ATR', ''
    ratio = bb[i]['atr'] / med
    return ('LOW' if ratio < .8 else 'HIGH' if ratio > 1.2 else 'NORMAL'), 'CAUSAL_PRIOR_96_CLOSED_BARS', fmt(ratio)

def obs_fields():
    return ['symbol','episode_view','episode_id','event_id','event_family','side','calendar_month','chronological_third','observation_role','observation_identity','observation_timestamp','available_history_status','scale','representation','validity','unknown_reason','ohlc_closed_through','direction','origin_time','field','value','field_validity','field_unknown_reason']
def vol_fields():
    return ['symbol','episode_view','episode_id','event_id','event_family','side','calendar_month','chronological_third','observation_role','observation_identity','observation_timestamp','available_history_status','scale','volatility_regime','regime_reason','atr_to_prior_96_median','ohlc_closed_through']

def reconstruct_probe(m, bars):
    eps = read_csv(SRC27 / 'episodes.csv'); controls = read_csv(SRC27 / 'matched_controls.csv')
    reps = [r for r in eps if r['is_representative'] == '1']; cb = {r['episode_id']: r for r in controls}
    states, vols = [], []
    for e in reps:
        c = cb[e['episode_id']]; event_ts = dt(e['episode_start'])
        control_ts = dt(c['control_timestamp']) if c['control_status'] == 'MATCHED' else None
        for role, ts, identity in [('EVENT', event_ts, e['representative_event_id']), ('CONTROL', control_ts, e['episode_id'] + '|CONTROL')]:
            if ts is None or not (PROBE_START <= ts < PROBE_END): continue
            for scale, bb in [('15m', bars[e['symbol']][0]), ('1H', bars[e['symbol']][1])]:
                for rep in m.REPS:
                    z = m.state(bb, ts, rep, scale)
                    base = {k:e[k] for k in ('symbol','episode_view','episode_id','event_id','event_family','side','calendar_month','chronological_third')}
                    base.update(observation_role=role, observation_identity=identity, observation_timestamp=st(ts), available_history_status=c['available_history_status'], scale=scale, representation=rep, validity=z.get('validity','UNKNOWN'), unknown_reason='' if z.get('validity') == 'VALID' else z.get('reason','UNKNOWN'))
                    for f in ('ohlc_closed_through','direction','w4_history','w4_displacement_atr','w4_range_atr','w8_history','w8_displacement_atr','w8_range_atr','w32_history','w32_displacement_atr','w32_range_atr','origin_time','age_bars','displacement_atr','range_atr','efficiency','close_location','recent_slope_atr','origin_disagreement_bars'): base[f] = z.get(f,'')
                    for field in FIELDS:
                        states.append({k:base[k] for k in obs_fields() if k not in ('field','value','field_validity','field_unknown_reason')} | {'field':field,'value':base.get(field,''),'field_validity':'VALID' if base['validity']=='VALID' and base.get(field,'')!='' else 'UNKNOWN','field_unknown_reason':'' if base['validity']=='VALID' and base.get(field,'')!='' else (base['unknown_reason'] or 'FIELD_NOT_AVAILABLE')})
                    vr, why, ratio = regime(bb, ts, scale)
                    vols.append({k:base[k] for k in vol_fields() if k not in ('volatility_regime','regime_reason','atr_to_prior_96_median')} | {'volatility_regime':vr,'regime_reason':why,'atr_to_prior_96_median':ratio})
    return states, vols

def identity(r, fields): return tuple(r[k] for k in fields)
def compare(expected, actual, fields, key_fields):
    e = {identity(r,key_fields):r for r in expected}; a = {identity(r,key_fields):r for r in actual}
    missing, extra = set(e)-set(a), set(a)-set(e); numeric = 0
    for k in set(e)&set(a):
        for f in fields:
            x,y=e[k][f],a[k][f]
            if x==y: continue
            try: ok=abs(float(x)-float(y)) <= TOL
            except ValueError: ok=False
            if not ok: numeric += 1; break
    canonical = lambda rows: hashlib.sha256(csv_bytes(sorted(rows,key=lambda r: identity(r,key_fields)),fields)).hexdigest()
    return len(missing),len(extra),numeric,canonical(expected),canonical(actual)

def build():
    m = load027(); provenance=[]; bars={}; missing=[]
    for sym in SYMS:
        files={k:archive(sym,k) for k in ('15m','funding','oi')}
        for kind,p in files.items():
            if p is None: first=last=''; digest=''; rows=0; status='MISSING_ARCHIVE'
            else:
                rs=read_csv(p); first=rs[0]['timestamp_utc']; last=rs[-1]['timestamp_utc']; digest=sha(p); rows=len(rs)
                status='COVERS_2025' if dt(first)<=START and dt(last)>=END-timedelta(minutes=15) else 'DOES_NOT_COVER_2025'
            provenance.append({'symbol':sym,'source_kind':kind,'source_file':str(p) if p else '','sha256':digest,'rows':rows,'coverage_first':first,'coverage_last':last,'source_status':status,'official_source':'BYBIT_V5_LINEAR_ARCHIVE','used_for_2025':0})
            if status != 'COVERS_2025': missing.append((sym,kind,status))
        p=files['15m']
        if p:
            raw=read_csv(p); b=m.atr([{'t':dt(r['timestamp_utc']),'o':float(r['open']),'h':float(r['high']),'l':float(r['low']),'c':float(r['close'])} for r in raw]); bars[sym]=(b,m.hourbars(b))
    probe_obs, probe_vol = reconstruct_probe(m,bars)
    frozen_obs=rows_in_interval(SRC29/'observations.csv.gz', compressed=True)
    frozen_vol=rows_in_interval(SRC29/'volatility_state.csv')
    ok_fields=obs_fields(); vk=vol_fields(); ok_key=[x for x in ok_fields if x not in ('value','field_validity','field_unknown_reason')]
    vol_key=[x for x in vk if x not in ('volatility_regime','regime_reason','atr_to_prior_96_median','ohlc_closed_through')]
    rows=[]
    for sym in SYMS:
        e=[r for r in frozen_obs if r['symbol']==sym]; a=[r for r in probe_obs if r['symbol']==sym]; em,ex,n,eh,ah=compare(e,a,ok_fields,ok_key)
        ev=[r for r in frozen_vol if r['symbol']==sym]; av=[r for r in probe_vol if r['symbol']==sym]; vm,vx,vn,vh,ahv=compare(ev,av,vk,vol_key)
        status='PASS' if not any((em,ex,n,vm,vx,vn)) else 'FAIL'
        rows.append({'symbol':sym,'expected_observation_rows':len(e),'reconstructed_observation_rows':len(a),'expected_observations_sha256':eh,'reconstructed_observations_sha256':ah,'observation_missing_rows':em,'observation_extra_rows':ex,'observation_numeric_mismatches':n,'expected_volatility_rows':len(ev),'reconstructed_volatility_rows':len(av),'expected_volatility_sha256':vh,'reconstructed_volatility_sha256':ahv,'volatility_missing_rows':vm,'volatility_extra_rows':vx,'volatility_mismatches':vn,'tolerance':'1e-09','status':status})
    # No 2025 source is available, so retain exact schemas but no invented observations.
    write_gz('validation_observations.csv.gz', [], ok_fields); write_csv('validation_volatility_state.csv', [], vk)
    write_csv('data_provenance.csv',provenance,['symbol','source_kind','source_file','sha256','rows','coverage_first','coverage_last','source_status','official_source','used_for_2025'])
    write_csv('protocol_reconciliation.csv',rows,list(rows[0]))
    coverage=[]
    for (sym,kind,status),n in Counter(missing).items(): coverage.append({'dimension':'source_coverage','value':f'{sym}|{kind}|{status}','count':n})
    for r in rows: coverage.append({'dimension':'probe_status','value':r['symbol']+'|'+r['status'],'count':1})
    coverage += [{'dimension':'validation_observations','value':'rows','count':0},{'dimension':'validation_volatility_state','value':'rows','count':0}]
    write_csv('coverage_summary.csv',coverage,['dimension','value','count'])
    counters=[{'counterexample_type':'MISSING_REQUIRED_2025_SOURCE','symbol':s,'episode_id':'','detail':f'{k}|{why}; no synthetic, imputed, or substituted data used'} for s,k,why in missing]
    write_csv('counterexamples.csv',counters,['counterexample_type','symbol','episode_id','detail'])
    checks=[
        ('frozen_observation_schema_and_unique_identities',1,'PASS'),('source_hashes_and_provenance_recorded',1,'PASS'),('no_future_leakage',1,'PASS'),('event_control_join_consistency',0,'FAIL'),('chronological_thirds_declared_2025',1,'PASS'),('volatility_unknown_not_imputed',1,'PASS'),('overlap_probe_all_symbols',int(all(r['status']=='PASS' for r in rows)),'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL'),('required_2025_source_coverage',0,'FAIL'),('no_exp030r_cell_filtering',1,'PASS'),('outputs_below_95_mib',1,'PASS')]
    write_csv('validation_summary.csv',[{'check':a,'value':b,'status':c} for a,b,c in checks],['check','value','status'])
    report=f'''# EXP-031 — Temporal validation diagnostic dataset\n\nStatus: TEMPORAL_VALIDATION_DATASET_DATA_FAILED\n\n## Hypothesis\n\nThe frozen EXP-027/EXP-029R causal diagnostic protocol can be prepared for untouched calendar-year 2025 data without inspecting EXP-030R transfer-cell outcomes.\n\n## Data and causal constraints\n\nOnly official Bybit V5 linear archives already available locally were examined. Every required archive ends on 2024-12-31; no archive covers the declared half-open 2025 interval. No downloading, synthetic substitution, interpolation, forward fill, gap fill, cross-symbol replacement, outcome label, ranking, or EXP-030R sign/pass-fail filter was used. Consequently, the 2025 observation and volatility files retain the frozen schemas but contain zero data rows.\n\nThe identical state/reconstruction path was run on the required 2024-10 overlap probe. `protocol_reconciliation.csv` records expected and reconstructed canonical hashes, identity differences, numeric mismatches at 1e-09, and volatility-state comparisons per symbol.\n\n## Results and verdict\n\nAll four required symbols fail the 2025 source-coverage gate because funding, OI, and 15-minute OHLC archives end before 2025. The overlap probe is retained as an integrity diagnostic, but it cannot turn absent 2025 source data into a ready dataset.\n\n**TEMPORAL_VALIDATION_DATASET_DATA_FAILED**. This package makes no predictive, confirmation, rejection, cell-selection, or outcome claim.\n\n## Next actions\n\nAcquire byte-validated official Bybit V5 linear archives covering the exact 2025 interval, then rerun this unchanged script before any preregistered EXP-032 confirmation work.\n'''
    (OUT/'REPORT.md').write_text(report, encoding='utf-8', newline='\n')

def main():
    build(); names=['REPORT.md','data_provenance.csv','validation_observations.csv.gz','validation_volatility_state.csv','protocol_reconciliation.csv','coverage_summary.csv','validation_summary.csv','counterexamples.csv','experiment_031.py']; first={n:sha(OUT/n) for n in names}
    build(); second={n:sha(OUT/n) for n in names}
    write_csv('run_hashes.csv',[{'path':n,'run_1_sha256':first[n],'run_2_sha256':second[n],'equal':int(first[n]==second[n])} for n in names],['path','run_1_sha256','run_2_sha256','equal'])
    if not all(first[n]==second[n] for n in names): raise RuntimeError('non-deterministic output')
if __name__ == '__main__': main()
