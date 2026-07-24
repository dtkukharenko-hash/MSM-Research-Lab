"""Causal, deterministic temporal feature primitives (standard library only)."""
from __future__ import annotations
import datetime as dt, hashlib, math

UNKNOWN = "UNKNOWN"
FIELDS = ("timestamp_utc", "open", "high", "low", "close", "volume", "turnover")

def _time(s):
    if not isinstance(s, str): raise ValueError("timestamp_utc must be UTC ISO-8601")
    try: value = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as e: raise ValueError("invalid timestamp_utc") from e
    if value.tzinfo is None or value.utcoffset() != dt.timedelta(0): raise ValueError("timestamp_utc must be UTC")
    return value.astimezone(dt.timezone.utc)
def _stamp(v): return v.strftime("%Y-%m-%dT%H:%M:%SZ")
def _number(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError(name + " must be finite")
    return float(v)
def _rows(rows):
    output=[]; prior=None
    for raw in rows:
        if not isinstance(raw, dict) or any(k not in raw for k in FIELDS): raise ValueError("invalid row schema")
        t=_time(raw["timestamp_utc"])
        if prior is not None and t <= prior: raise ValueError("timestamps must be strictly increasing")
        r={"timestamp_utc": _stamp(t)}
        for k in FIELDS[1:]: r[k]=_number(raw[k], k)
        if min(r["open"],r["high"],r["low"],r["close"]) <= 0 or r["low"] > min(r["open"],r["close"]) or r["high"] < max(r["open"],r["close"]) or r["volume"] < 0 or r["turnover"] < 0: raise ValueError("invalid OHLC")
        output.append(r); prior=t
    return output

def clip_unit(value):
    value=_number(value,"value")
    return 0.0 if value < 0 else 1.0 if value > 1 else value
def nearest_rank(values, probability):
    if not isinstance(probability,(int,float)) or isinstance(probability,bool) or not math.isfinite(probability) or not 0 < probability <= 1: raise ValueError("invalid probability")
    values=sorted(_number(v,"quantile value") for v in values)
    if not values: raise ValueError("empty values")
    return values[math.ceil(probability*len(values))-1]

def join_closed_daily(primary_rows, daily_rows):
    primary,daily=_rows(primary_rows),_rows(daily_rows); answer=[]; j=0; current=UNKNOWN
    for p in primary:
        emission=_time(p["timestamp_utc"])+dt.timedelta(hours=4)
        while j < len(daily) and _time(daily[j]["timestamp_utc"])+dt.timedelta(days=1) <= emission:
            current=daily[j]; j+=1
        answer.append({"timestamp_utc":p["timestamp_utc"],"daily":current})
    return answer

def join_closed_children(primary_rows, child_rows):
    primary=_rows(primary_rows); parsed=[]
    # Child defects are localized to their parent and deliberately yield UNKNOWN.
    for raw in child_rows:
        try: parsed.append(_rows([raw])[0])
        except ValueError: parsed.append(None)
    answer=[]
    for p in primary:
        start=_time(p["timestamp_utc"]); end=start+dt.timedelta(hours=4)
        in_window=[x for x in parsed if x is not None and start <= _time(x["timestamp_utc"]) < end]
        invalid_window=any(x is None for x in parsed) # invalid timestamps cannot safely be borrowed
        expected=[_stamp(start+dt.timedelta(hours=i)) for i in range(4)]
        times=[x["timestamp_utc"] for x in in_window]
        valid=(not invalid_window and len(in_window)==4 and sorted(times)==expected and len(set(times))==4)
        answer.append({"timestamp_utc":p["timestamp_utc"],"children":sorted(in_window,key=lambda x:x["timestamp_utc"]) if valid else UNKNOWN})
    return answer

def compute_features(rows, scale):
    if scale not in ("4H","1H"): raise ValueError("scale must be 4H or 1H")
    rows=_rows(rows); k,w,pairs=(3,12,6) if scale=="4H" else (6,24,12)
    tr=[]; atr=[]; ema=[]
    for i,r in enumerate(rows):
        previous=rows[i-1]["close"] if i else None
        tr.append(r["high"]-r["low"] if previous is None else max(r["high"]-r["low"],abs(r["high"]-previous),abs(r["low"]-previous)))
        atr.append(sum(tr[i-13:i+1])/14 if i >= 13 else None)
        if i < 26: ema.append(None)
        elif i == 26: ema.append(sum(x["close"] for x in rows[:27])/27)
        else: ema.append((2/28)*r["close"]+(26/28)*ema[-1])
    result=[]
    for i,r in enumerate(rows):
        a=atr[i]
        slope=(ema[i]-ema[i-k])/a if a is not None and i>=k and ema[i] is not None and ema[i-k] is not None else UNKNOWN
        displacement=(r["close"]-rows[i-w]["close"])/a if a is not None and i>=w else UNKNOWN
        if i>=w:
            denominator=sum(abs(rows[z]["close"]-rows[z-1]["close"]) for z in range(i-w+1,i+1))
            efficiency=abs(r["close"]-rows[i-w]["close"])/denominator if denominator else UNKNOWN
        else: efficiency=UNKNOWN
        if i>=pairs:
            ratios=[]
            for z in range(i-pairs+1,i+1):
                left,right=rows[z-1],rows[z]; denom=min(left["high"]-left["low"],right["high"]-right["low"])
                if denom <= 0: ratios=None; break
                ratios.append(clip_unit((min(left["high"],right["high"])-max(left["low"],right["low"]))/denom))
            overlap=sum(ratios)/len(ratios) if ratios is not None else UNKNOWN
        else: overlap=UNKNOWN
        previous_atr=[x for x in atr[:i] if x is not None]
        volatility=((sum(x<a for x in previous_atr[-96:]) + .5*sum(x==a for x in previous_atr[-96:]))/96 if a is not None and len(previous_atr)>=96 else UNKNOWN)
        result.append({"timestamp_utc":r["timestamp_utc"],"true_range":tr[i],"atr14":a if a is not None else UNKNOWN,"ema27":ema[i] if ema[i] is not None else UNKNOWN,"normalized_slope":slope,"normalized_displacement":displacement,"efficiency":efficiency,"overlap_density":overlap,"volatility_percentile":volatility})
    return result

FEATURE_KEYS=("timestamp_utc","true_range","atr14","ema27","normalized_slope","normalized_displacement","efficiency","overlap_density","volatility_percentile")
def canonical_feature_row(row): return ",".join(format(row[k],".17g") if isinstance(row[k],float) else str(row[k]) for k in FEATURE_KEYS)
def freeze_thresholds(development_features):
    rows=list(development_features); population="\n".join(canonical_feature_row(r) for r in rows)
    spec=(("S70","normalized_slope",.7,True),("S50","normalized_slope",.5,True),("D70","normalized_displacement",.7,True),("D50","normalized_displacement",.5,True),("E30","efficiency",.3,False),("O70","overlap_density",.7,False))
    result={"population_rows":len(rows),"population_hash":hashlib.sha256(population.encode()).hexdigest(),"counts":{}}
    for label,field,q,absolute in spec:
        values=[abs(r[field]) if absolute else r[field] for r in rows if isinstance(r.get(field),(int,float)) and not isinstance(r.get(field),bool) and math.isfinite(r[field])]
        result["counts"][field]=len(values); result[label]=nearest_rank(values,q) if values else UNKNOWN
    return result
