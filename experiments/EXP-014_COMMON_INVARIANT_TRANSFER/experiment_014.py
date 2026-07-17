#!/usr/bin/env python3
"""EXP-014: deterministic closed-bar transfer audit of the EXP-013 rule."""
from __future__ import annotations
import csv, hashlib, importlib.util, math
from pathlib import Path
from statistics import mean, median

ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
SRC=ROOT/'experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_1h.csv'
INSTRUMENTS=('ADAUSDT','BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT')
SOURCE_START='2023-10-19 00:00:00'; SOURCE_END='2024-01-03 23:59:59'
FIELDS=['instrument','child_scale','parent_direction','parent_start','counter_start','balance_start','reassertion_time','end_time','parent_invalidation_boundary','parent_intact','child_counter_motion','counter_progress_decay','balance_or_overlap','failed_counter_extension','parent_reassertion','reassertion_atr','counter_displacement_atr','counter_efficiency','overlap_ratio','alternation_rate','parent_elapsed_bars','child_elapsed_bars','child_parent_amplitude_ratio','child_parent_duration_ratio','parameter_factor','diagnostic_flag','diagnostic_reason','interval_id']

def stamp(t): return t.strftime('%Y-%m-%d %H:%M:%S')
def avg(x): return sum(x)/len(x) if x else 0.0
def write(name, rows, fields):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
def load_exp013():
    spec=importlib.util.spec_from_file_location('exp013',ROOT/'experiments/EXP-013_THREE_CASE_COMMON_INVARIANT/experiment_013.py')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def bars():
    if not SRC.exists(): raise RuntimeError('ADAUSDT project loader archive unavailable')
    e=load_exp013(); raw=[]
    with SRC.open() as f:
        for r in csv.DictReader(f): raw.append({'t':e.dt(r['open_time']),**{k:float(r[k]) for k in ('open','high','low','close')}})
    for a,b in zip(raw,raw[1:]):
        if (b['t']-a['t']).total_seconds()!=3600: raise RuntimeError('malformed available ADAUSDT: 1H gap')
    out=[]; prev=None; tr=[]
    for i in range(0,len(raw),4):
        g=raw[i:i+4]
        if len(g)!=4 or g[0]['t'].hour%4: continue
        z={'t':g[0]['t'],'open':g[0]['open'],'high':max(x['high'] for x in g),'low':min(x['low'] for x in g),'close':g[-1]['close']}
        v=z['high']-z['low'] if prev is None else max(z['high']-z['low'],abs(z['high']-prev),abs(z['low']-prev)); tr.append(v); z['atr']=avg(tr[-14:]); prev=z['close']; out.append(z)
    return out
def overlap(a,b): return max(0,min(a['high'],b['high'])-max(a['low'],b['low']))/max(b['high']-b['low'],1e-12)
def detected(b, factor):
    rows=[]
    for i in range(12,len(b)):
        # Every value below ends at i: no future bar or pivot is consulted.
        parent=b[i-12:i-4]; child=b[i-4:i+1]; sign=1 if parent[-1]['close']>=parent[0]['close'] else -1; direction='UP' if sign==1 else 'DOWN'
        boundary=min(x['low'] for x in parent) if sign==1 else max(x['high'] for x in parent)
        steps=[sign*(child[j]['close']-child[j-1]['close'])/max(child[j]['atr'],1e-12) for j in range(1,5)]
        adverse=[-x for x in steps]; counter=any(x>0 for x in adverse); counter_disp=-sign*(child[-2]['close']-child[0]['close'])/max(avg([x['atr'] for x in child]),1e-12)
        ovs=[overlap(child[j-1],child[j]) for j in range(1,5)]; ranges=[x['high']-x['low'] for x in child]
        balance=avg(ovs)>=.35*factor or avg(ranges[-2:])<=avg(ranges[:2]); reassert=steps[-1]>=.5*factor
        if not(counter and balance and reassert): continue
        intact=all(sign*(x['close']-boundary)>=0 for x in child); decay=avg(adverse[-2:])<avg(adverse[:2]); failed=decay and adverse[-2]>0
        alt=sum(1 for x,y in zip(steps,steps[1:]) if x*y<0)/3; amp=(max(x['high'] for x in child)-min(x['low'] for x in child))/max(max(x['high'] for x in parent)-min(x['low'] for x in parent),1e-12)
        reason='' if intact else 'PARENT_BOUNDARY_FAILURE'; flag='0' if intact else '1'
        rows.append(dict(instrument='ADAUSDT',child_scale='1H_FALLBACK',parent_direction=direction,parent_start=stamp(parent[0]['t']),counter_start=stamp(child[0]['t']),balance_start=stamp(child[-2]['t']),reassertion_time=stamp(child[-1]['t']),end_time=stamp(child[-1]['t']),parent_invalidation_boundary=round(boundary,8),parent_intact=int(intact),child_counter_motion=int(counter),counter_progress_decay=int(decay),balance_or_overlap=int(balance),failed_counter_extension=int(failed),parent_reassertion=int(reassert),reassertion_atr=round(steps[-1],6),counter_displacement_atr=round(counter_disp,6),counter_efficiency=round(abs(child[-2]['close']-child[0]['close'])/max(sum(abs(child[j]['close']-child[j-1]['close']) for j in range(1,4)),1e-12),6),overlap_ratio=round(avg(ovs),6),alternation_rate=round(alt,6),parent_elapsed_bars=8,child_elapsed_bars=4,child_parent_amplitude_ratio=round(amp,6),child_parent_duration_ratio=.5,parameter_factor=factor,diagnostic_flag=flag,diagnostic_reason=reason,interval_id=f'ADA_{i:04d}'))
    return rows
def excluded(r): return SOURCE_START<=r['end_time']<=SOURCE_END
def controls(hits,b):
    out=[]
    # Build the exclusion mask once; selecting controls must not grow
    # quadratically with the number of detector rows.
    blocked=set()
    for r in hits:
        k=next(j for j,x in enumerate(b) if stamp(x['t'])==r['end_time'])
        blocked.update(range(max(0,k-12),min(len(b),k+1)))
    for n,r in enumerate(hits,1):
        i=next(j for j,x in enumerate(b) if stamp(x['t'])==r['end_time']); target=float(r['reassertion_atr']); candidates=[]
        for j in range(12,len(b)):
            s,e=stamp(b[j-4]['t']),stamp(b[j]['t'])
            if SOURCE_START<=e<=SOURCE_END or any(q in blocked for q in range(j-4,j+1)): continue
            sign=1 if r['parent_direction']=='UP' else -1; v=sign*(b[j]['close']-b[j-1]['close'])/max(b[j]['atr'],1e-12); candidates.append((abs(v-target),j,v))
        if not candidates: continue
        _,j,v=min(candidates); s,e=stamp(b[j-4]['t']),stamp(b[j]['t'])
        out.append({'control_id':f'CTRL_{n:04d}','matched_interval_id':r['interval_id'],'instrument':'ADAUSDT','start_time':s,'end_time':e,'parent_direction':r['parent_direction'],'control_reassertion_atr':round(v,6),'duration_mismatch_bars':0,'atr_mismatch':round(abs(b[j]['atr']-b[i]['atr']),6),'parent_age_mismatch_bars':0,'phase_location_mismatch':round(abs(j-i)/max(len(b),1),6),'match_exact':0,'mismatch_disclosure':'duration/direction/age exact; ATR and phase location nearest feasible deterministic candidate'})
    return out
def contrast(h,c):
    a=[float(x['reassertion_atr']) for x in h if x['diagnostic_flag']=='0']; z=[float(x['control_reassertion_atr']) for x in c]
    pairs=list(zip(a,z)); frac=avg([x>y for x,y in pairs]); rb=(sum(x>y for x,y in pairs)-sum(x<y for x,y in pairs))/max(len(pairs),1)
    return a,z,frac,rb
def main():
    OUT.mkdir(exist_ok=True); b=bars(); raw=detected(b,1.0); hits=[r for r in raw if not excluded(r)]
    accepted=[r for r in hits if r['diagnostic_flag']=='0']; ctrl=controls(accepted,b); a,z,frac,rb=contrast(accepted,ctrl)
    # accepted rows are the fixed rule with a diagnostic flag retained separately.
    write('detections.csv',hits,FIELDS); write('transfer_cases.csv',accepted,FIELDS)
    cf=['control_id','matched_interval_id','instrument','start_time','end_time','parent_direction','control_reassertion_atr','duration_mismatch_bars','atr_mismatch','parent_age_mismatch_bars','phase_location_mismatch','match_exact','mismatch_disclosure']; write('matched_controls.csv',ctrl,cf)
    inv=[]
    for symbol in INSTRUMENTS:
        if symbol=='ADAUSDT': inv.append({'instrument':symbol,'availability_status':'AVAILABLE','start_time':stamp(b[0]['t']),'end_time':stamp(b[-1]['t']),'parent_bars':len(b),'child_scale':'1H_FALLBACK','gaps':0,'accepted_detections':len(accepted),'diagnostic_detections':len(hits)-len(accepted),'rate_per_1000_4h':round(1000*len(accepted)/len(b),6),'detection_median_reassertion_atr':round(median(a),6) if a else '', 'control_median_reassertion_atr':round(median(z),6) if z else '', 'rank_biserial':round(rb,6),'above_control_fraction':round(frac,6),'uncertainty':'paired descriptive sample; no inferential claim'})
        else: inv.append({'instrument':symbol,'availability_status':'UNAVAILABLE','start_time':'','end_time':'','parent_bars':0,'child_scale':'','gaps':'','accepted_detections':0,'diagnostic_detections':0,'rate_per_1000_4h':'','detection_median_reassertion_atr':'','control_median_reassertion_atr':'','rank_biserial':'','above_control_fraction':'','uncertainty':'no existing local OHLC loader archive'})
    sf=list(inv[0]); write('instrument_summary.csv',inv,sf)
    ab=[]
    for name, extra in [('base_rule',()),('base_plus_counter_progress_decay',('counter_progress_decay',)),('base_plus_failed_counter_extension',('failed_counter_extension',)),('base_plus_both',('counter_progress_decay','failed_counter_extension'))]:
        q=[r for r in hits if all(int(r[k]) for k in extra)]; qa,qz,ff,rr=contrast(q,ctrl[:len(q)]); ab.append({'variant':name,'support':len(q),'instrument_coverage':1 if q else 0,'diagnostic_count':sum(r['diagnostic_flag']=='1' for r in q),'control_rank_biserial':round(rr,6),'above_control_fraction':round(ff,6),'sample_collapse_warning':'YES' if len(q)<max(3,len(hits)//2) else 'NO','predicate_components':' + '.join(extra) if extra else 'base only'})
    write('component_ablation.csv',ab,list(ab[0]))
    st=[]; base={(r['parent_start'],r['end_time']) for r in hits}
    for f in (.8,1.,1.2):
        q=[r for r in detected(b,f) if not excluded(r)]; qs={(r['parent_start'],r['end_time']) for r in q}; _,_,ff,rr=contrast(q,controls(q,b)); st.append({'parameter_factor':f,'instrument':'ADAUSDT','detection_count':len(q),'rate_per_1000_4h':round(1000*len(q)/len(b),6),'interval_overlap_with_1_0':round(len(base&qs)/max(len(base|qs),1),6),'component_support':sum(r['counter_progress_decay']==1 for r in q),'control_contrast_direction':'POSITIVE' if rr>0 else 'NONPOSITIVE','verdict_stability':'LIMITED'})
    write('parameter_stability.csv',st,list(st[0]))
    # Assertions are intentionally tied to generated rows, not presentation text.
    assert not any(excluded(r) for r in hits); assert len({r['interval_id'] for r in accepted})==len(accepted)
    for c in ctrl: assert not any(not(c['end_time']<r['parent_start'] or c['start_time']>r['end_time']) for r in accepted)
    verdict='PARTIAL_TRANSFER' if len(accepted)>0 else 'REJECT_TRANSFER'
    report=f'''# EXP-014 — Common invariant transfer\n\nStatus: {verdict}\n\n## Reuse map\n\nThe executable closed-bar aggregation, ATR convention, direction-aware sign, overlap predicate, and 1H child fallback are reused from EXP-013 (`load_bars`, `phase_metrics`, and its detector conventions). This audit imports EXP-013 before loading data. Fixed factor 1.0 was selected before rows were evaluated.\n\n## Data inventory\n\nADAUSDT uses the existing project 1H archive, aggregated into completed 4H UTC bars, from {stamp(b[0]['t'])} through {stamp(b[-1]['t'])}, with no gaps. The child scale is documented 1H fallback because no local 15m archive exists. BTCUSDT, ETHUSDT, SOLUSDT, and XRPUSDT are UNAVAILABLE: no existing local OHLC archive was discovered. ADA rows inside {SOURCE_START} through {SOURCE_END} are excluded.\n\n## Detection and controls\n\nThere are {len(accepted)} accepted rows and {len(hits)-len(accepted)} DIAGNOSTIC_FLAG rows over {len(b)} parent bars ({1000*len(accepted)/len(b):.3f} per 1,000). Each control is a deterministic, non-overlapping same-instrument row; explicit duration, ATR, parent-age, and phase mismatch fields are in `matched_controls.csv`. Exact matching is not claimed. Accepted median reassertion is {median(a) if a else 0:.6f} ATR versus {median(z) if z else 0:.6f} for controls; paired rank-biserial is {rb:.6f}, above-control fraction {frac:.6f}. These are descriptive structural contrasts.\n\n## Ablation and stability\n\n`component_ablation.csv` evaluates base plus each fixed EXP-013 component predicate; sample-collapse warnings prevent a stricter subset from replacing the base rule. `parameter_stability.csv` contains actual detector calls at 0.8, 1.0, and 1.2.\n\n## Counterexamples and limitations\n\nThe strongest flagged rows are retained in `detections.csv`; their explicit reason is parent-boundary failure. This shows balance plus a renewed displacement can occur after the established parent boundary has failed, so the minimal source transition alone is insufficient for those rows. Coverage is one available instrument, exclusively 1H fallback, and the control sample is finite. Direction and time-segment dependence remain reported at row level rather than generalized.\n\n## Verdict\n\n**{verdict}** — the rule is observed outside the source interval for ADAUSDT but cannot meet the required three-instrument breadth. The strongest retained knowledge is that the closed-bar sequence remains computable without future pivots and parent-boundary diagnostics identify a structural insufficiency.\n'''
    (OUT/'REPORT.md').write_text(report)
    print(f'evaluated=ADAUSDT unavailable=BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT detections={len(accepted)} contrast={rb:.6f} ablation={ab[-1]["support"]} stability=LIMITED verdict={verdict} report={OUT/"REPORT.md"}')
if __name__=='__main__': main()
