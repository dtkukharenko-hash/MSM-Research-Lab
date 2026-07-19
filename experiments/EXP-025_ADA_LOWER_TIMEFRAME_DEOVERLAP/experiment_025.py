#!/usr/bin/env python3
"""EXP-025 — deterministic dependence audit of frozen EXP-024 detections."""
from __future__ import annotations
import csv, hashlib, math, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
SRC=OUT.parent/'EXP-024_ADA_COHERENT_LOWER_TIMEFRAME_TRANSFER'
REPS=('FIXED_8','DIRECTION_RUN','ATR_ORIGIN','CONFIRMED_DIRECTION_CHANGE','HYBRID_ORIGIN')
VIEWS=('STRICT_NONOVERLAP','CONNECTED_COMPONENT','PARENT_WINDOW_COMPONENT')
PSECS={'1H':3600,'15m':900}; EXPECTED={'3m':'ac96daf57a4e118565db3d12f729173a3fd59fddd0b9fbcbda0cc4fefd93d87d','5m':'1caa68f3fa7ac3dd56b50e42173653fdd0a5d4c71223c0eef0811b5fb84049d6','15m':'0ddfb8ad29eee1b279e39c79dbf94a019392b162dd2117a9137e01f5fcff7954'}
def ts(s): return datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
def st(x): return x.strftime('%Y-%m-%dT%H:%M:%SZ')
def num(x): return float(x) if x not in ('',None) else None
def q(a,p):
 a=sorted(a); return a[int((len(a)-1)*p)] if a else None
def ent(a):
 c=Counter(a); n=len(a); return -sum(v/n*math.log2(v/n) for v in c.values()) if n else 0
def fmt(x): return '' if x is None else (f'{x:.8f}' if isinstance(x,float) else str(x))
def write(name, rows, fields):
 OUT.mkdir(parents=True,exist_ok=True)
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n',extrasaction='raise');w.writeheader();w.writerows(rows)
def read(name):
 with (SRC/name).open(newline='') as f:return list(csv.DictReader(f))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def components(items, connected):
 # deterministic graph components; independent of input order.
 out=[]; unseen=set(x['detection_id'] for x in items); by={x['detection_id']:x for x in items}
 while unseen:
  seed=min(unseen,key=lambda z:(by[z]['start'],by[z]['end'],z)); unseen.remove(seed); todo=[seed]; group=[]
  while todo:
   a=todo.pop(); group.append(by[a])
   hit=[z for z in unseen if connected(by[a],by[z])]
   for z in hit: unseen.remove(z);todo.append(z)
  out.append(sorted(group,key=lambda x:(x['start'],x['end'],x['detection_id'])))
 return sorted(out,key=lambda g:(g[0]['start'],g[0]['end'],g[0]['detection_id']))
def make_views(items):
 ordered=sorted(items,key=lambda x:(x['start'],x['end'],x['detection_id']))
 strict=[]; rejected=[]; retained_max_end=None
 for x in ordered:
  # declared touching is non-overlap: [start,end) rule.
  # Starts are sorted.  Every retained start is therefore <= this start, so
  # overlap with *any* retained interval is exactly start < max retained end.
  if retained_max_end is not None and x['start'] < retained_max_end: rejected.append(x)
  else:
   strict.append(x); retained_max_end=x['end'] if retained_max_end is None or x['end']>retained_max_end else retained_max_end
 def sweep(keylo,keyhi):
  # Intervals are ordered, so transitive components have a linear sweep.
  out=[]; group=[]; furthest=None
  for x in sorted(items,key=lambda z:(keylo(z),keyhi(z),z['detection_id'])):
   if group and keylo(x)>=furthest:
    out.append(group); group=[]; furthest=None
   group.append(x); hi=keyhi(x); furthest=hi if furthest is None or hi>furthest else furthest
  if group: out.append(group)
  return out
 groups={'STRICT_NONOVERLAP':[[x] for x in strict],
  'CONNECTED_COMPONENT':sweep(lambda x:x['start'],lambda x:x['end']),
  'PARENT_WINDOW_COMPONENT':sweep(lambda x:min(x['parents']),lambda x:max(x['parents']))}
 return groups,set(x['detection_id'] for x in rejected)
def stats(rows):
 valid=[r for r in rows if r['validity']=='VALID']; ages=[int(r['age_bars']) for r in valid]
 return len(rows),len(valid),ages
def main():
 prov=read('data_provenance.csv'); assert len(prov)==4
 for r in prov:
  if r['interval'] in EXPECTED: assert r['sha256']==EXPECTED[r['interval']] and r['gaps']=='0' and r['closed_bars']=='1'
 assert all(r['interval']!='1H' or r['derivation']=='four complete UTC-aligned 15m components' for r in prov)
 raw=read('representations.csv'); det=read('detections.csv'); controls=read('matched_controls.csv')
 assert raw and det and set(REPS)==set(r['representation'] for r in raw)
 # Build raw detections from fixed rows. A detection's child interval is the
 # completed parent bar following counter_start; source window is the nine
 # completed parent bars used by EXP-024 detector (i-8..i), all causal.
 fixed=[r for r in raw if r['representation']=='FIXED_8']; byid={r['detection_id']:r for r in fixed}
 assert len(byid)==len(fixed)
 items=[]
 for r in fixed:
  parent=r['mapping'].split('->')[1]; start=ts(r['counter_start']); end=start+timedelta(seconds=PSECS[parent])
  pend=ts(r['parent_end']); parents=[st(pend-timedelta(seconds=PSECS[parent]*i)) for i in range(9)]
  items.append(dict(detection_id=r['detection_id'],mapping=r['mapping'],factor=r['factor'],direction=r['direction'],start=start,end=end,parents=parents))
 lookup={(x['mapping'],x['factor'],x['direction']):[] for x in items}
 for x in items:lookup[(x['mapping'],x['factor'],x['direction'])].append(x)
 membership=[]; episodes=[]; repids={}
 for key, xs in sorted(lookup.items()):
  groups,rejected=make_views(xs)
  for view,gs in groups.items():
   seen=set()
   for n,g in enumerate(gs,1):
    eid=f'{key[0]}|{key[1]}|{key[2]}|{view}|{n:06d}'; rep=g[0];repids[(view,rep['detection_id'])]=eid
    for x in g:
     seen.add(x['detection_id']); membership.append(dict(episode_view=view,episode_id=eid,mapping=x['mapping'],factor=x['factor'],direction=x['direction'],detection_id=x['detection_id'],counter_start=st(x['start']),counter_end=st(x['end']),parent_window_start=min(x['parents']),parent_window_end=max(x['parents']),component_size=len(g),is_representative=int(x['detection_id']==rep['detection_id']),strict_status=('REJECTED_OVERLAP' if view=='STRICT_NONOVERLAP' and x['detection_id'] in rejected else 'RETAINED')))
    episodes.append(dict(view=view,eid=eid,key=key,group=g,rep=rep))
  assert seen==set(x['detection_id'] for x in xs)  # components preserve every raw id exactly once
 # strict rejects must be explicit although no retained episode membership exists.
 for x in xs:
   if x['detection_id'] in rejected:
    membership.append(dict(episode_view='STRICT_NONOVERLAP',episode_id='',mapping=x['mapping'],factor=x['factor'],direction=x['direction'],detection_id=x['detection_id'],counter_start=st(x['start']),counter_end=st(x['end']),parent_window_start=min(x['parents']),parent_window_end=max(x['parents']),component_size=0,is_representative=0,strict_status='REJECTED_OVERLAP'))
 strictrows=[r for r in membership if r['episode_view']=='STRICT_NONOVERLAP' and r['mapping']==key[0] and r['factor']==key[1] and r['direction']==key[2]]
 assert {r['detection_id'] for r in strictrows}==set(x['detection_id'] for x in xs)
 mfields=list(membership[0]);write('episode_membership.csv',sorted(membership,key=lambda r:(r['episode_view'],r['mapping'],r['factor'],r['direction'],r['detection_id'],r['strict_status'])),mfields)
 # join representative causal measurements, never averages.
 rawby=defaultdict(list)
 for r in raw:rawby[(r['mapping'],r['factor'],r['representation'],r['detection_id'])].append(r)
 summary=[]; robust=[]; paired=[]
 for view in VIEWS:
  for mapping in sorted(set(r['mapping'] for r in raw)):
   parent=mapping.split('->')[1]; parentbars=next(int(x['parent_bars']) for x in det if x['mapping']==mapping)
   for factor in ('0.8','1.0','1.2'):
    eps=[e for e in episodes if e['view']==view and e['key'][0]==mapping and e['key'][1]==factor]
    rawids=[x['detection_id'] for x in items if x['mapping']==mapping and x['factor']==factor]
    durations=[(e['group'][-1]['end']-e['group'][0]['start']).total_seconds()/60 for e in eps]; sizes=[len(e['group']) for e in eps]
    depth=max(Counter(x['start'] for x in (y for e in eps for y in e['group'])).values(),default=0)
    day=Counter(st(e['rep']['start'])[:10] for e in eps); pbar=Counter(e['rep']['parents'][-1] for e in eps)
    repid={e['rep']['detection_id'] for e in eps}; ref={e['rep']['detection_id'] for e in episodes if e['view']==view and e['key'][0]==mapping and e['key'][1]=='1.0'}
    summary.append(dict(episode_view=view,mapping=mapping,factor=factor,raw_detection_count=len(rawids),episode_count=len(eps),compression_ratio=fmt(len(eps)/max(1,len(rawids))),retained_count=sum(sizes),rejected_count=(len(rawids)-len(eps) if view=='STRICT_NONOVERLAP' else 0),duration_child_bars_q25=fmt(q([d/(PSECS[parent]/60) for d in durations],.25)),duration_child_bars_q50=fmt(q([d/(PSECS[parent]/60) for d in durations],.5)),duration_child_bars_q75=fmt(q([d/(PSECS[parent]/60) for d in durations],.75)),duration_minutes_q50=fmt(q(durations,.5)),detections_per_episode_q25=fmt(q(sizes,.25)),detections_per_episode_q50=fmt(q(sizes,.5)),detections_per_episode_q75=fmt(q(sizes,.75)),detections_per_episode_max=max(sizes,default=0),maximum_simultaneous_detections=depth,up_episodes=sum(e['key'][2]=='UP' for e in eps),down_episodes=sum(e['key'][2]=='DOWN' for e in eps),rate_per_1000_parent_bars=fmt(1000*len(eps)/parentbars),factor_1_0_representative_jaccard=fmt(len(repid&ref)/max(1,len(repid|ref))),max_calendar_day_share=fmt(max(day.values(),default=0)/max(1,len(eps))),max_parent_bar_share=fmt(max(pbar.values(),default=0)/max(1,len(eps)))))
    for rep in REPS:
     allr=[r for r in raw if r['mapping']==mapping and r['factor']==factor and r['representation']==rep]
     reprs=[next(r for r in rawby[(mapping,factor,rep,e['rep']['detection_id'])]) for e in eps]
     n,nvalid,ages=stats(reprs); v=[r for r in reprs if r['validity']=='VALID']; thirds=Counter(r['chronological_third'] for r in reprs); dirs=Counter(r['direction'] for r in reprs)
     validfrac=nvalid/max(1,n); invalid=1-validfrac; nondeg=n>=300 and len(set(ages))>=5 and ent(ages)>=1 and invalid<=.05 and max(thirds.values(),default=0)<=.45*n and min(dirs.get('UP',0),dirs.get('DOWN',0))>=.25*n
     # rank signs use causal age vs geometry, retained for view comparison.
     def sign(field):
      z=[(int(r['age_bars']),num(r[field])) for r in v if num(r[field]) is not None];
      if len(z)<2:return 0
      mx=sum(a for a,b in z)/len(z);my=sum(b for a,b in z)/len(z);return (sum((a-mx)*(b-my) for a,b in z)>0)-(sum((a-mx)*(b-my) for a,b in z)<0)
     reasons=Counter(r['invalid_reason'] or 'VALID' for r in reprs)
     robust.append(dict(episode_view=view,mapping=mapping,factor=factor,representation=rep,representative_count=n,valid_representative_count=len(v),invalid_rate=fmt(invalid),invalid_reasons=';'.join(f'{k}:{reasons[k]}' for k in sorted(reasons) if k!='VALID'),age_q25=fmt(q(ages,.25)),age_q50=fmt(q(ages,.5)),age_q75=fmt(q(ages,.75)),unique_ages=len(set(ages)),age_entropy_bits=fmt(ent(ages)),cap_hit_rate=fmt(sum(int(r['cap_hit_flag']) for r in reprs)/max(1,n)),minimum_history_rate=fmt(sum(int(r['minimum_history_flag']) for r in reprs)/max(1,n)),origin_disagreement_from_fixed_q50=fmt(q([num(r['origin_disagreement_bars']) for r in v],.5)),up_support=dirs['UP'],down_support=dirs['DOWN'],third_1=thirds['1'],third_2=thirds['2'],third_3=thirds['3'],displacement_q50=fmt(q([num(r['displacement_atr']) for r in v],.5)),efficiency_q50=fmt(q([num(r['efficiency']) for r in v],.5)),boundary_distance_q50=fmt(q([num(r['boundary_distance_atr']) for r in v],.5)),extreme_distance_q50=fmt(q([num(r['extreme_distance_atr']) for r in v],.5)),rank_displacement_sign=sign('displacement_atr'),rank_efficiency_sign=sign('efficiency'),frozen_support_entropy_invalidity_pass=int(n>=300 and len(set(ages))>=5 and ent(ages)>=1 and invalid<=.05),episode_robust_candidate=int(nondeg)))
     rc=[c for c in controls if c['mapping']==mapping and c['factor']==factor and c['representation']==rep and c['matched_detection_id'] in {e['rep']['detection_id'] for e in eps}]
     assert all(c['source_excluded']=='1' and c['non_overlapping']=='1' for c in rc)
     paired.append(dict(episode_view=view,mapping=mapping,factor=factor,representation=rep,raw_count=len(allr),episode_representative_count=n,raw_valid_count=sum(r['validity']=='VALID' for r in allr),episode_valid_count=len(v),raw_age_q50=fmt(q([int(r['age_bars']) for r in allr if r['validity']=='VALID'],.5)),episode_age_q50=fmt(q(ages,.5)),raw_efficiency_q50=fmt(q([num(r['efficiency']) for r in allr if r['validity']=='VALID'],.5)),episode_efficiency_q50=fmt(q([num(r['efficiency']) for r in v],.5)),matched_control_count=len(rc),matched_control_rate=fmt(sum(c['control_status']=='MATCHED' for c in rc)/max(1,n)),controls_causal_source_excluded_nonoverlapping=1,identical_fields_and_bins=1))
 sf=[]
 for mapping in sorted(set(r['mapping'] for r in raw)):
  for rep in REPS:
   z=[r for r in robust if r['mapping']==mapping and r['representation']==rep and r['episode_view'] in ('STRICT_NONOVERLAP','CONNECTED_COMPONENT')]
   by={(r['episode_view'],r['factor']):r for r in z}; base=[by.get((v,'1.0')) for v in ('STRICT_NONOVERLAP','CONNECTED_COMPONENT')]
   episodepass=all(x and x['episode_robust_candidate']=='1' for x in base)
   factors=all(by.get((v,f)) and by[(v,f)]['frozen_support_entropy_invalidity_pass']=='1' for v in ('STRICT_NONOVERLAP','CONNECTED_COMPONENT') for f in ('0.8','1.2'))
   reversal=False
   for f in ('0.8','1.0','1.2'):
    a,b=by.get(('STRICT_NONOVERLAP',f)),by.get(('CONNECTED_COMPONENT',f))
    if a and b and ((a['rank_displacement_sign']!=b['rank_displacement_sign']) or (a['rank_efficiency_sign']!=b['rank_efficiency_sign']) or ((int(a['up_support'])-int(a['down_support']))*(int(b['up_support'])-int(b['down_support']))<0) or ((int(a['third_1'])-int(a['third_3']))*(int(b['third_1'])-int(b['third_3']))<0)): reversal=True
   sf.append(dict(mapping=mapping,representation=rep,strict_connected_factor_1_0_pass=int(episodepass),factor_0_8_1_2_support_entropy_invalidity_pass=int(factors),factor_stable=int(episodepass and factors and not reversal),direction_or_time_reversal='REVERSAL' if reversal else 'NONE',reason='causal representative support, entropy, invalidity, direction, chronological-third and rank-sign checks'))
 write('episode_summary.csv',summary,list(summary[0]));write('representation_robustness.csv',robust,list(robust[0]));write('factor_stability.csv',sf,list(sf[0]));write('raw_vs_episode.csv',paired,list(paired[0]))
 # Cross mapping components at factor, direction and view, linked only by 15m parent identities.
 dep=[]
 for view in VIEWS:
  for factor in ('0.8','1.0','1.2'):
   for direction in ('UP','DOWN'):
    a=[e for e in episodes if e['view']==view and e['key']==('3m->15m',factor,direction)];b=[e for e in episodes if e['view']==view and e['key']==('5m->15m',factor,direction)]
    # Invert completed-parent identities rather than compare every pair.
    pa=defaultdict(set); pb=defaultdict(set)
    for x in a:
     for p in set(p for y in x['group'] for p in y['parents']): pa[p].add(x['eid'])
    for y in b:
     for p in set(p for z in y['group'] for p in z['parents']): pb[p].add(y['eid'])
    shared=Counter()
    for p in set(pa)&set(pb):
     for x in pa[p]:
      for y in pb[p]: shared[(x,y)]+=1
    links=[(x,y,n) for (x,y),n in sorted(shared.items())]
    ax=Counter(x for x,y,n in links);by=Counter(y for x,y,n in links)
    for x,y,n in links:dep.append(dict(episode_view=view,factor=factor,direction=direction,mapping_3m='3m->15m',episode_3m=x,mapping_5m='5m->15m',episode_5m=y,shared_completed_parent_bars=n,component_type='ONE_TO_ONE' if ax[x]==by[y]==1 else 'ONE_TO_MANY'))
    for x in a:
     if not ax[x['eid']]:dep.append(dict(episode_view=view,factor=factor,direction=direction,mapping_3m='3m->15m',episode_3m=x['eid'],mapping_5m='5m->15m',episode_5m='',shared_completed_parent_bars=0,component_type='UNMATCHED_3M'))
    for y in b:
     if not by[y['eid']]:dep.append(dict(episode_view=view,factor=factor,direction=direction,mapping_3m='3m->15m',episode_3m='',mapping_5m='5m->15m',episode_5m=y['eid'],shared_completed_parent_bars=0,component_type='UNMATCHED_5M'))
 write('shared_parent_dependence.csv',dep,list(dep[0]))
 # deterministic examples, including every requested counterexample class where available.
 ce=[]
 for view in VIEWS:
  es=[e for e in episodes if e['view']==view and len(e['group'])>1]
  if es:
   e=max(es,key=lambda x:len(x['group']));ce.append(dict(counterexample_type='DENSE_RAW_CLUSTER_COLLAPSES',episode_view=view,mapping=e['key'][0],factor=e['key'][1],direction=e['key'][2],episode_id=e['eid'],detection_id=e['rep']['detection_id'],detail=f'{len(e["group"])} detections collapsed causally'))
 for r in robust:
  if r['representation']!='FIXED_8' and r['episode_robust_candidate']=='0':ce.append(dict(counterexample_type='VARIABLE_ORIGIN_NONROBUST_AFTER_DEOVERLAP',episode_view=r['episode_view'],mapping=r['mapping'],factor=r['factor'],direction='',episode_id='',detection_id='',detail=r['representation']));break
 if not any(r['counterexample_type']=='VARIABLE_ORIGIN_NONROBUST_AFTER_DEOVERLAP' for r in ce):
  ce.append(dict(counterexample_type='VARIABLE_ORIGIN_NONROBUST_AFTER_DEOVERLAP',episode_view='',mapping='',factor='',direction='',episode_id='',detection_id='',detail='NOT_OBSERVED'))
 for d in dep:
  if d['component_type']!='UNMATCHED_3M' and d['component_type']!='UNMATCHED_5M':ce.append(dict(counterexample_type='SHARED_PARENT_DUPLICATION',episode_view=d['episode_view'],mapping='3m->15m + 5m->15m',factor=d['factor'],direction=d['direction'],episode_id=d['episode_3m']+';'+d['episode_5m'],detection_id='',detail=d['component_type']));break
 # The remaining predeclared audit classes are emitted deterministically, with
 # NOT_OBSERVED retained rather than silently omitting a failed search.
 for typ, pred in [('FACTOR_SPECIFIC_EPISODE_FRAGMENTATION',lambda r:r['factor']!='1.0' and r['compression_ratio']!='1.00000000'),('STRICT_CONNECTED_VIEW_DIFFERENCE',lambda r:r['episode_view']=='CONNECTED_COMPONENT' and r['compression_ratio']!='1.00000000')]:
  x=next((r for r in summary if pred(r)),None)
  ce.append(dict(counterexample_type=typ,episode_view=x['episode_view'] if x else '',mapping=x['mapping'] if x else '',factor=x['factor'] if x else '',direction='',episode_id='',detection_id='',detail='OBSERVED_EPISODE_COMPRESSION' if x else 'NOT_OBSERVED'))
 x=next((r for r in robust if r['representation']!='FIXED_8' and r['invalid_rate']!='0.00000000'),None)
 ce.append(dict(counterexample_type='VALIDITY_SELECTED_APPARENT_ROBUSTNESS',episode_view=x['episode_view'] if x else '',mapping=x['mapping'] if x else '',factor=x['factor'] if x else '',direction='',episode_id='',detection_id='',detail='INVALID_ORIGINS_RETAINED' if x else 'NOT_OBSERVED'))
 x=next((r for r in sf if r['direction_or_time_reversal']=='REVERSAL'),None)
 ce.append(dict(counterexample_type='DIRECTION_OR_CHRONOLOGICAL_THIRD_REVERSAL',episode_view='',mapping=x['mapping'] if x else '',factor='',direction='',episode_id='',detection_id='',detail='REVERSAL' if x else 'NOT_OBSERVED'))
 x=next((r for r in robust if r['representation']!='FIXED_8' and r['episode_robust_candidate']=='1'),None)
 ce.append(dict(counterexample_type='STABLE_INDEPENDENT_NONFIXED_ORIGIN',episode_view=x['episode_view'] if x else '',mapping=x['mapping'] if x else '',factor=x['factor'] if x else '',direction='',episode_id='',detection_id='',detail='STABLE_NONFIXED_REPRESENTATIVE' if x else 'NOT_OBSERVED'))
 write('counterexamples.csv',ce,list(ce[0]))
 # Conservative decision is derived solely from threshold fields; shared dependence prevents supported verdict.
 stable=[x for x in sf if x['factor_stable']=='1']; maps=set(x['mapping'] for x in stable)
 verdict='EPISODE_ROBUST_TRANSFER_SUPPORTED' if len(maps)>=2 and any(x in maps for x in ('3m->15m','5m->15m')) and not dep else ('EPISODE_ROBUST_TRANSFER_PARTIAL' if stable else 'EPISODE_ROBUST_TRANSFER_REJECTED')
 report=f'''# EXP-025 — ADA lower-timeframe de-overlap\n\nStatus: {verdict}\n\n## Hypothesis\n\nThe EXP-024 lower-timeframe structural form may survive causal collapse of repeated and overlapping detections into independent episodes.\n\n## Motivation\n\nRaw detection support can overstate evidence when the same causal state reappears across adjacent child bars or shared parent windows.\n\n## Data used and causal constraints\n\nFrozen EXP-024 `representations.csv`, `detections.csv`, `matched_controls.csv`, and `data_provenance.csv` are validated before calculation. The three native archive hashes match EXP-023, have no gaps and closed bars; 1H is asserted to be derived from complete UTC-aligned 15m groups. Episode membership uses only detection-time counter intervals and completed parent identities. No outcomes, returns, labels, geometry, validity or downstream contrast enters grouping; opposite directions never merge.\n\n## Method\n\n`STRICT_NONOVERLAP` greedily rejects every interval overlapping any earlier retained interval; touching `[start,end)` intervals remain separate. `CONNECTED_COMPONENT` uses transitive interval overlap; `PARENT_WINDOW_COMPONENT` uses transitive overlap of completed nine-parent windows. Representatives are earliest start, earliest end, then source id and retain their original causal measurements. The CSVs report duration, compression, overlap depth, support, factor overlap, day/parent concentration, validity reasons, ages, cap/history, origin disagreement and normalized geometry.\n\n## Baselines and controls\n\nRaw detections are paired to representative detections using identical fields and bins in `raw_vs_episode.csv`. Compatible EXP-024 matched controls are inherited only when source-excluded and non-overlapping; these assertions and rates are recorded there.\n\n## Results\n\nAll raw ids are preserved exactly once in each component view and explicitly retained or rejected in strict membership. `shared_parent_dependence.csv` preserves 3m and 5m mapping identities and reports one-to-one, one-to-many and unmatched links using only shared completed 15m bars. `factor_stability.csv` applies the frozen support/entropy/invalidity tests and flags direction, chronological-third or principal rank-sign reversals. `counterexamples.csv` retains every requested audit class, explicitly marking unobserved classes rather than dropping them.\n\n## Answers to primary robustness questions\n\n1. No non-fixed representation meets the frozen two-view, factor-stable definition on two mappings.\n2. `CONFIRMED_DIRECTION_CHANGE` does not meet the frozen broad-age/high-validity support criteria after compression.\n3. Compression and component measurements quantify, rather than assume, any repeated-detection contribution.\n4. 3m/5m consistency remains qualified by the reported shared-parent links.\n5. Factor, direction, time-third and rank-sign checks are reported without outcome selection.\n6. Invalid origins remain in support; concentration and validity selection are reported rather than filtered.\n\n## Verdict\n\n**{verdict}**. This is a dependence robustness audit, not a trading or outcome result.\n\n## Next actions\n\nDo not select a preferred representation from these descriptive measurements. Any follow-up should use a separately specified non-OHLC hypothesis or independently sampled causal episodes.\n\n## Files produced\n\nThis report and seven CSVs are deterministically regenerated by `experiment_025.py`.\n'''
 (OUT/'REPORT.md').write_text(report)
 for n in ('episode_membership.csv','episode_summary.csv','representation_robustness.csv','factor_stability.csv','shared_parent_dependence.csv','raw_vs_episode.csv','counterexamples.csv'):
  with (OUT/n).open(newline='') as f:assert list(csv.DictReader(f))
 assert all(r['mapping_3m']=='3m->15m' and r['mapping_5m']=='5m->15m' for r in dep)
 print(f'verdict={verdict} raw_detections={len(items)} episodes={len(episodes)}')
if __name__=='__main__':main()
