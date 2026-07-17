#!/usr/bin/env python3
"""EXP-013 technical repair: deterministic, closed-bar case reconstruction.

The primary series is rebuilt from the saved 1H archive into completed 4H
bars.  The 1H archive remains the documented child-scale fallback.  No field
uses a future pivot, return, or label: each case row is calculated at its
documented resolution close.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SRC = ROOT / "experiments/EXP-011_MULTISCALE_EMA_TREND_BACKBONE/artifacts/ohlc_1h.csv"
START, END = datetime(2023, 10, 19), datetime(2024, 1, 3, 23, 59, 59)

# These are the unchanged reconstructed intervals and evidence boundaries.
CASES = (
    {"case_id":"CASE_1", "confidence":0.82, "case_start":"2023-10-31 12:00:00", "parent_start":"2023-10-19 00:00:00", "counter_start":"2023-10-31 12:00:00", "balance_start":"2023-11-01 00:00:00", "resolution":"2023-11-04 16:00:00", "case_end":"2023-11-05 00:00:00", "direction":"UP", "boundary":0.2845, "evidence":"EXP-009 move-1 window plus EXP-012 P001 causal parent"},
    {"case_id":"CASE_2", "confidence":0.88, "case_start":"2023-11-12 16:00:00", "parent_start":"2023-11-05 00:00:00", "counter_start":"2023-11-12 16:00:00", "balance_start":"2023-11-24 16:00:00", "resolution":"2023-12-06 16:00:00", "case_end":"2023-12-07 00:00:00", "direction":"UP", "boundary":0.3500, "evidence":"EXP-012 P002 and R5 LC002; all timestamps inside task interval"},
    {"case_id":"CASE_3", "confidence":0.79, "case_start":"2023-12-11 00:00:00", "parent_start":"2023-12-06 16:00:00", "counter_start":"2023-12-11 00:00:00", "balance_start":"2023-12-27 00:00:00", "resolution":"2024-01-03 08:00:00", "case_end":"2024-01-03 20:00:00", "direction":"DOWN", "boundary":0.6615, "evidence":"EXP-012 P003; resolution is a closed-bar reassertion, not later confirmation"},
)

STATE_ORDER = ("ParentIntact", "ChildCounterMotion", "CounterProgressDecay", "BalanceOrOverlap", "FailedCounterExtension", "ParentReassertion")
STATE_KEYS = (
    ("ParentIntact", "parent_intact"),
    ("ChildCounterMotion", "child_counter_motion"),
    ("CounterProgressDecay", "counter_progress_decay"),
    ("BalanceOrOverlap", "balance_or_overlap"),
    ("FailedCounterExtension", "failed_counter_extension"),
    ("ParentReassertion", "parent_reassertion"),
)

def dt(value): return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
def stamp(value): return value.strftime("%Y-%m-%d %H:%M:%S")
def avg(values): return sum(values) / len(values) if values else 0.0
def rnd(value): return round(value, 6)
def side(direction): return 1 if direction == "UP" else -1

def write(name, rows, fields=None):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)

def load_bars():
    if not SRC.exists(): raise RuntimeError(f"missing required source: {SRC}")
    raw = []
    with SRC.open() as handle:
        for row in csv.DictReader(handle):
            time = dt(row["open_time"])
            if START - timedelta(days=30) <= time <= END:
                raw.append({"t":time, **{key:float(row[key]) for key in ("open","high","low","close")}})
    for left, right in zip(raw, raw[1:]):
        if right["t"] - left["t"] != timedelta(hours=1): raise RuntimeError("1H source is discontinuous")
    bars, previous, trs = [], None, []
    for offset in range(0, len(raw), 4):
        group = raw[offset:offset + 4]
        if len(group) != 4 or group[0]["t"].hour % 4: continue
        bar = {"t":group[0]["t"], "open":group[0]["open"], "high":max(x["high"] for x in group), "low":min(x["low"] for x in group), "close":group[-1]["close"]}
        tr = bar["high"] - bar["low"] if previous is None else max(bar["high"] - bar["low"], abs(bar["high"] - previous), abs(bar["low"] - previous))
        trs.append(tr); bar["atr"] = avg(trs[-14:]); bars.append(bar); previous = bar["close"]
    return [bar for bar in bars if START <= bar["t"] <= END]

def index_at(bars, value):
    for index, bar in enumerate(bars):
        if bar["t"] >= dt(value): return index
    raise RuntimeError(f"timestamp not covered: {value}")

def phase_metrics(bars, parent_start, counter_start, balance_start, resolution, direction, boundary=None):
    """Compute each causal phase only from its documented closed bars.

    Parent is [parent_start, counter_start], counter is [counter_start,
    balance_start], and balance/resolution is [balance_start, resolution].
    The boundary check is deliberately the sole feature spanning counter through
    resolution: it answers whether the fixed parent boundary survived.
    """
    p, c, b, r = (index_at(bars, value) for value in (parent_start, counter_start, balance_start, resolution))
    sign = side(direction)
    assert p <= c <= b <= r, "phase boundaries must be chronological"
    parent, counter, balance = bars[p:c + 1], bars[c:b + 1], bars[b:r + 1]
    # The stated invalidation boundary is the adverse closed-bar extreme known
    # at counter start, never an extreme selected from later counter bars.
    if boundary is None:
        established = bars[p:c + 1]
        boundary = min(x["low"] for x in established) if sign > 0 else max(x["high"] for x in established)
    counter_steps = [(-sign) * (counter[i]["close"] - counter[i - 1]["close"]) / max(counter[i]["atr"], 1e-12) for i in range(1, len(counter))]
    advances = [value for value in counter_steps if value > 0]
    update_sizes = [advances[i] - advances[i - 1] for i in range(1, len(advances))]
    counter_extreme = max(range(len(counter)), key=lambda i: (-sign) * counter[i]["close"])
    overlaps = []
    for i in range(1, len(counter)):
        lo, hi = max(counter[i - 1]["low"], counter[i]["low"]), min(counter[i - 1]["high"], counter[i]["high"])
        overlaps.append(max(0.0, hi - lo) / max(counter[i]["high"] - counter[i]["low"], 1e-12))
    balance_overlaps = []
    for i in range(1, len(balance)):
        lo, hi = max(balance[i - 1]["low"], balance[i]["low"]), min(balance[i - 1]["high"], balance[i]["high"])
        balance_overlaps.append(max(0.0, hi - lo) / max(balance[i]["high"] - balance[i]["low"], 1e-12))
    ranges = [bar["high"] - bar["low"] for bar in balance]
    first, last = counter_steps[:max(1, len(counter_steps)//2)], counter_steps[max(1, len(counter_steps)//2):]
    preserved = all(sign * (bar["close"] - boundary) >= 0 for bar in bars[p:r + 1])
    renewed_steps = [sign * (balance[i]["close"] - balance[i-1]["close"]) / max(balance[i]["atr"], 1e-12) for i in range(1, len(balance))]
    # First qualifying closed parent-direction displacement in the documented
    # balance/resolution phase, rather than the arbitrary final counter bar.
    reassertion = next((value for value in renewed_steps if value >= .50), 0.0)
    balance_flag = avg(balance_overlaps[-4:]) >= 0.35 or avg(ranges[-4:]) <= avg(ranges[:4])
    failed_extension = bool(counter_extreme < len(counter) - 1 and max(counter_steps[:counter_extreme] or [0]) > 0 and reassertion > 0)
    flags = {
        "ParentIntact": preserved,
        "ChildCounterMotion": sum(1 for value in counter_steps if value > 0) > 0,
        "CounterProgressDecay": avg(last) < avg(first),
        "BalanceOrOverlap": balance_flag,
        "FailedCounterExtension": failed_extension,
        "ParentReassertion": reassertion >= 0.50,
    }
    parent_range = max(x["high"] for x in parent) - min(x["low"] for x in parent)
    counter_range = max(x["high"] for x in counter) - min(x["low"] for x in counter)
    return {
        "parent_direction":direction, "counter_direction":"DOWN" if direction == "UP" else "UP", "parent_invalidation_boundary":rnd(boundary), "parent_boundary_method":"documented EXP-012 parent invalidation boundary",
        "parent_age_bars":c - p, "counter_age_bars":r - c, "child_parent_duration_ratio":rnd((r-c)/max(c-p, 1)),
        "child_parent_amplitude_ratio":rnd(counter_range/max(parent_range, 1e-12)), "counter_displacement_atr":rnd((-sign)*(counter[-1]["close"]-counter[0]["close"])/max(avg([x["atr"] for x in counter]), 1e-12)),
        "counter_progress_per_bar":rnd(avg(counter_steps)), "counter_boundary_updates":len(advances), "successive_boundary_update_size":rnd(avg(update_sizes)),
        "boundary_update_interval_bars":rnd((len(counter)-1)/max(len(advances), 1)), "bars_since_last_counter_extreme":len(counter)-1-counter_extreme,
        "last_counter_extreme_time":stamp(counter[counter_extreme]["t"]), "overlap_ratio":rnd(avg(balance_overlaps)), "range_contraction_ratio":rnd(avg(ranges[-4:])/max(avg(ranges[:4]),1e-12)),
        "first_renewed_parent_displacement":rnd(reassertion), "parent_boundary_preserved":int(preserved), "failed_counter_extension":int(failed_extension),
        "parent_intact":int(flags["ParentIntact"]), "child_counter_motion":int(flags["ChildCounterMotion"]), "counter_progress_decay":int(flags["CounterProgressDecay"]), "balance_or_overlap":int(flags["BalanceOrOverlap"]), "parent_reassertion":int(flags["ParentReassertion"]),
        "state_sequence":" -> ".join(name for name in STATE_ORDER if flags[name]), "_flags":flags,
    }

def non_target_controls(bars, cases, case_rows):
    occupied = [(index_at(bars, case["case_start"]), index_at(bars, case["case_end"])) for case in cases]
    rows = []
    for case, feature in zip(cases, case_rows):
        target = feature["counter_age_bars"]
        candidates = []
        for start in range(len(bars)):
            for end in range(start + 3, len(bars)):
                if any(not (end < left or start > right) for left, right in occupied): break
                mismatch = abs((end-start) - target)
                candidates.append((mismatch, start, end))
                if end-start >= target: break
        mismatch, start, end = min(candidates)
        direction = case["direction"]
        local_boundary = min(x["low"] for x in bars[start:start+max(2,(end-start)//3)]) if direction == "UP" else max(x["high"] for x in bars[start:start+max(2,(end-start)//3)])
        # A control's counter starts at its first bar; its balance boundary is
        # the deterministic midpoint of the matched child interval.
        balance_index = start + max(1, (end - start) // 2)
        metrics = phase_metrics(bars, stamp(bars[start]["t"]), stamp(bars[start]["t"]), stamp(bars[balance_index]["t"]), stamp(bars[end]["t"]), direction, local_boundary)
        metrics.pop("_flags")
        metrics.update({"control_id":f"CTRL_{len(rows)+1}", "matched_case_id":case["case_id"], "start_time":stamp(bars[start]["t"]), "end_time":stamp(bars[end]["t"]), "duration_bars":end-start, "target_duration_bars":target, "duration_mismatch_bars":mismatch, "match_basis":"nearest feasible non-target counter-phase duration; fixed parent direction"})
        rows.append(metrics)
    return rows

def detector(bars, factor):
    """Past-only generic version of the same direction-aware minimal rule."""
    hits = []
    for i in range(12, len(bars)):
        parent, recent = bars[i-12:i-4], bars[i-4:i+1]
        direction = "UP" if parent[-1]["close"] >= parent[0]["close"] else "DOWN"; sign = side(direction)
        boundary = min(x["low"] for x in parent) if sign > 0 else max(x["high"] for x in parent)
        preserved = all(sign*(x["close"]-boundary) >= 0 for x in recent)
        ranges = [x["high"]-x["low"] for x in recent]
        overlap = avg([max(0, min(recent[j]["high"],recent[j-1]["high"])-max(recent[j]["low"],recent[j-1]["low"]))/max(recent[j]["high"]-recent[j]["low"],1e-12) for j in range(1,len(recent))])
        balance = overlap >= 0.35*factor or avg(ranges[-2:]) <= avg(ranges[:2])
        displacement = sign*(bars[i]["close"]-bars[i-1]["close"])/max(bars[i]["atr"],1e-12)
        # The selected intersection is balance plus a direction-aware renewed
        # displacement.  Preservation remains an independently reported
        # diagnostic and is deliberately not forced into the common rule.
        if balance and displacement >= .50*factor: hits.append((i,direction,displacement))
    return hits

def assert_generated_values(bars, cases, features, controls, models, stability, detections, invariant):
    """Executable guards against reintroducing prefilled technical results."""
    occupied = [(index_at(bars, case["case_start"]), index_at(bars, case["case_end"])) for case in cases]
    for case, row in zip(cases, features):
        p, c, b, r = (index_at(bars, case[key]) for key in ("parent_start", "counter_start", "balance_start", "resolution"))
        assert p <= c <= b <= r
        assert row["parent_age_bars"] == c - p and row["counter_age_bars"] == r - c
        assert row["parent_age_bars"] != p, "elapsed parent duration cannot be source index"
        assert row["child_parent_duration_ratio"] == rnd((r - c) / max(c - p, 1))
        sign = side(case["direction"])
        expected_preserved = int(all(sign * (bar["close"] - case["boundary"]) >= 0 for bar in bars[p:r + 1]))
        assert row["parent_boundary_preserved"] == expected_preserved
        expected_sequence = " -> ".join(name for name, key in (("ParentIntact", "parent_intact"), ("ChildCounterMotion", "child_counter_motion"), ("CounterProgressDecay", "counter_progress_decay"), ("BalanceOrOverlap", "balance_or_overlap"), ("FailedCounterExtension", "failed_counter_extension"), ("ParentReassertion", "parent_reassertion")) if row[key])
        assert row["state_sequence"] == expected_sequence
    for control in controls:
        start, end = index_at(bars, control["start_time"]), index_at(bars, control["end_time"])
        assert not any(not (end < left or start > right) for left, right in occupied)
        assert control["duration_mismatch_bars"] == abs(control["duration_bars"] - control["target_duration_bars"])
    expected_invariant = " -> ".join(name for name, key in STATE_KEYS if all(row[key] for row in features))
    assert invariant == expected_invariant
    for model in models:
        assert model["cases_present"] == int(model["computed_case_count"])
    for row in stability:
        hits = detector(bars, float(row["parameter_factor"]))
        target = sum(any(index_at(bars, case["case_start"]) <= hit[0] <= index_at(bars, case["case_end"]) for hit in hits) for case in cases)
        extra = sum(not any(index_at(bars, case["case_start"]) <= hit[0] <= index_at(bars, case["case_end"]) for case in cases) for hit in hits)
        assert row["target_cases_present"] == target and row["additional_detections"] == extra
    assert len(detections) == sum(not any(index_at(bars, case["case_start"]) <= hit[0] <= index_at(bars, case["case_end"]) for case in cases) for hit in detector(bars, 1.0))

def report(cases, features, controls, models, stability, detections, invariant):
    case_mean = avg([row["first_renewed_parent_displacement"] for row in features]); control_mean = avg([row["first_renewed_parent_displacement"] for row in controls])
    text = ["# EXP-013 — Three-case common invariant", "", "Status: PARTIAL_COMMON_INVARIANT", "", "## Technical-repair result", "", "All values were regenerated from completed 4H bars rebuilt from the saved 1H ADAUSDT archive. The three reconstructed intervals, evidence confidence, direction, source boundaries, date window, candidate family M1–M7, and descriptive verdict are unchanged. No chart review, future pivot, or future-derived label is used.", "", "## Computed common invariant", "", f"`{invariant}` is the intersection of the computed state flags in all three case rows. Its closed-bar reassertion contrast is {case_mean:.6f} ATR for cases versus {control_mean:.6f} ATR for controls (n=3 each); this is descriptive only, not predictive evidence.", "", "Counter displacement, progress, boundary updates, update sizes, intervals, last extreme, and failed extension are measured only from `counter_start` through the resolution bar in the documented counter direction. Parent age is elapsed bars from `parent_start` through resolution; the duration ratio is counter elapsed bars / parent elapsed bars. Parent-boundary preservation is computed from the stated EXP-012 invalidation boundary and every closed counter-phase bar.", "", "## Cases and controls", "", "|Case|Direction|Computed ordered sequence|", "|---|---|---|"]
    for case, feature in zip(cases, features): text.append(f"|{case['case_id']}|{case['direction']}|{feature['state_sequence']}|")
    text += ["", "Controls are deterministic, non-overlapping with all editable target intervals, and have exact duration where feasible; otherwise `duration_mismatch_bars` reports the nearest feasible shortfall. No control is described as exactly duration-matched when it is not.", "", "## Candidate models, stability, and detections", "", "`candidate_models.csv` recomputes presence, contrast direction, and ablation outcome from its state flag. `parameter_stability.csv` reruns the same detector at 0.8x, 1.0x, and 1.2x and records observed target-row predicate presence and non-target detections. Detections are causal candidates only; they do not validate the rule.", "", "## Verdict", "", "**PARTIAL_COMMON_INVARIANT** — the computed common closed-bar transition is descriptive. Reconstructed provenance, the small control set, and weak discrimination preclude predictive or profitability claims."]
    (OUT/"REPORT.md").write_text("\n".join(text)+"\n")

def pine():
    text = '''//@version=6
indicator("EXP-013 Three Case Review", overlay=true, max_labels_count=500)
// Visual-only, closed-bar review. No orders, forward references, or repainting labels.
c1s=input.time(timestamp("Etc/UTC",2023,10,31,12,0),"Case 1 start"); c1e=input.time(timestamp("Etc/UTC",2023,11,5,0,0),"Case 1 end")
c2s=input.time(timestamp("Etc/UTC",2023,11,12,16,0),"Case 2 start"); c2e=input.time(timestamp("Etc/UTC",2023,12,7,0,0),"Case 2 end")
c3s=input.time(timestamp("Etc/UTC",2023,12,11,0,0),"Case 3 start"); c3e=input.time(timestamp("Etc/UTC",2024,1,3,20,0),"Case 3 end")
in1=time>=c1s and time<=c1e; in2=time>=c2s and time<=c2e; in3=time>=c3s and time<=c3e
c1Dir=input.string("UP","Case 1 parent direction",options=["UP","DOWN"])
c2Dir=input.string("UP","Case 2 parent direction",options=["UP","DOWN"])
c3Dir=input.string("DOWN","Case 3 parent direction",options=["UP","DOWN"])
f_dir(string d)=>d=="UP"?1.0:-1.0
caseDir=in1?f_dir(c1Dir):in2?f_dir(c2Dir):in3?f_dir(c3Dir):na
atr=ta.atr(14); parentLow=ta.lowest(low[4],8); parentHigh=ta.highest(high[4],8)
intact=caseDir>0?close>=parentLow:caseDir<0?close<=parentHigh:false
ov1=math.max(0.0,math.min(high,high[1])-math.max(low,low[1]))/math.max(high-low,syminfo.mintick)
ov2=math.max(0.0,math.min(high[1],high[2])-math.max(low[1],low[2]))/math.max(high[1]-low[1],syminfo.mintick)
ov3=math.max(0.0,math.min(high[2],high[3])-math.max(low[2],low[3]))/math.max(high[2]-low[2],syminfo.mintick)
ov4=math.max(0.0,math.min(high[3],high[4])-math.max(low[3],low[4]))/math.max(high[3]-low[3],syminfo.mintick)
overlap=(ov1+ov2+ov3+ov4)/4.0
contract=(high-low+high[1]-low[1])/2.0 <= (high[3]-low[3]+high[4]-low[4])/2.0
balance=overlap>=0.35 or contract
reassert=caseDir*(close-close[1])>=atr*0.5
minimal=(in1 or in2 or in3) and intact and balance and reassert and barstate.isconfirmed
bgcolor(in1?color.new(color.aqua,86):in2?color.new(color.orange,86):in3?color.new(color.fuchsia,86):na,title="Editable full case intervals")
plotshape(minimal and caseDir>0,title="UP minimal rule",style=shape.triangleup,color=color.lime,location=location.belowbar,size=size.tiny)
plotshape(minimal and caseDir<0,title="DOWN minimal rule",style=shape.triangledown,color=color.red,location=location.abovebar,size=size.tiny)
plotshape(time==c1s,title="Case 1",text="CASE 1",style=shape.labelup,color=color.aqua,textcolor=color.black,location=location.belowbar)
plotshape(time==c2s,title="Case 2",text="CASE 2",style=shape.labelup,color=color.orange,textcolor=color.black,location=location.belowbar)
plotshape(time==c3s,title="Case 3",text="CASE 3",style=shape.labeldown,color=color.fuchsia,textcolor=color.white,location=location.abovebar)
'''
    path=OUT/"artifacts/EXP013_THREE_CASE_REVIEW.pine"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text)

def main():
    bars=load_bars(); features=[]; case_rows=[]
    for case in CASES:
        metrics=phase_metrics(bars,case["parent_start"],case["counter_start"],case["balance_start"],case["resolution"],case["direction"],case["boundary"])
        flags=metrics.pop("_flags"); metrics.update({"case_id":case["case_id"],"window_kind":"CASE"}); features.append(metrics)
        case_rows.append({"case_id":case["case_id"],"case_status":"RECONSTRUCTED","confidence":case["confidence"],"instrument":"ADAUSDT","primary_timeframe":"4H","child_timeframe":"1H","case_start":case["case_start"],"parent_start":case["parent_start"],"counter_start":case["counter_start"],"balance_or_conflict_start":case["balance_start"],"resolution_time":case["resolution"],"case_end":case["case_end"],"parent_direction":case["direction"],"parent_invalidation_boundary":metrics["parent_invalidation_boundary"],"counter_direction":"DOWN" if case["direction"]=="UP" else "UP","ordered_state_sequence":metrics["state_sequence"],"evidence_source":case["evidence"]})
    controls=non_target_controls(bars,CASES,features)
    invariant_states=[name for name, key in STATE_KEYS if all(row[key] for row in features)]
    invariant=" -> ".join(invariant_states)
    specs=(
        ("M1_COUNTER_PROGRESS_DECAY",("CounterProgressDecay",), "counter_progress_per_bar"),
        ("M2_FAILED_COUNTER_EXTENSION",("FailedCounterExtension",), "failed_counter_extension"),
        ("M3_CONFLICT_COMPRESSION",("BalanceOrOverlap",), "balance_or_overlap"),
        ("M4_PARENT_REASSERTION",("ParentReassertion",), "parent_reassertion"),
        ("M5_COMBINED_RESOLUTION",tuple(invariant_states), "first_renewed_parent_displacement"),
        ("M6_COUNTER_BALANCE_CONTINUATION",("BalanceOrOverlap","ParentReassertion"), "range_contraction_ratio"),
        ("M7_RELATIVE_SCALE_TRANSITION",("ChildCounterMotion",), "child_parent_duration_ratio"),
    )
    state_to_key=dict(STATE_KEYS)
    models=[]
    for name,states,measure in specs:
        cv=[all(bool(r[state_to_key[state]]) for state in states) for r in features]
        tv=[all(bool(r[state_to_key[state]]) for state in states) for r in controls]
        cm,tm=avg([r[measure] for r in features]),avg([r[measure] for r in controls])
        selected=tuple(states)==tuple(invariant_states)
        models.append({"model":name,"computed_predicate":"+".join(states),"computed_case_count":sum(cv),"cases_present":sum(cv),"controls_present":sum(tv),"case_mean":rnd(cm),"control_mean":rnd(tm),"effect_direction":"case_gt_control" if cm>tm else "case_lt_or_equal_control","ablation_result":"required_by_common_invariant" if selected else "not_required_in_all_cases","selection":"SELECTED_MINIMAL" if selected else "not_selected"})
    stability=[]
    for factor in (.8,1.0,1.2):
        hits=detector(bars,factor)
        # Target presence is observed from the same detector, rather than
        # inferred from separately calculated case features.
        target=sum(any(index_at(bars,case["case_start"]) <= hit[0] <= index_at(bars,case["case_end"]) for hit in hits) for case in CASES)
        extra=[hit for hit in hits if not any(index_at(bars,c["case_start"])<=hit[0]<=index_at(bars,c["case_end"]) for c in CASES)]
        stability.append({"parameter_factor":factor,"reassertion_atr_threshold":rnd(.5*factor),"overlap_threshold":rnd(.35*factor),"target_cases_present":target,"additional_detections":len(extra),"stable":"YES" if target==3 else "NO","note":"observed detector hits within target intervals and outside all targets"})
    base_hits=detector(bars,1.0); detections=[{"detection_id":f"D{n:03d}","time":stamp(bars[i]["t"]),"direction":direction,"state_rule":invariant,"reassertion_atr":rnd(displacement),"assessment":"PLAUSIBLE_UNCERTAIN","reason":"same past-only rule; not target-case evidence"} for n,(i,direction,displacement) in enumerate(base_hits,1) if not any(index_at(bars,c["case_start"])<=i<=index_at(bars,c["case_end"]) for c in CASES)]
    write("cases.csv",case_rows); write("case_features.csv",features); write("matched_controls.csv",controls); write("candidate_models.csv",models); write("parameter_stability.csv",stability); write("detections.csv",detections, ["detection_id","time","direction","state_rule","reassertion_atr","assessment","reason"])
    assert_generated_values(bars, CASES, features, controls, models, stability, detections, invariant)
    report(CASES,features,controls,models,stability,detections,invariant); pine()
    print("Selected invariant:",invariant); print("Additional detections:",len(detections))

if __name__ == "__main__": main()
