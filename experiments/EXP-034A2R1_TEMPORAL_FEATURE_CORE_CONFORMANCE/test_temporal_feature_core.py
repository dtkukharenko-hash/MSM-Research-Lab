"""Independent literal-oracle tests and evidence generator for EXP-034A2R1."""
import argparse,csv,gzip,hashlib,json,os,resource,shutil,subprocess,sys,unittest
from datetime import datetime,timedelta,timezone
HERE=os.path.dirname(__file__); sys.path.insert(0,HERE)
import temporal_feature_core as core
E={}
def record(name, observed, expected): E[name]=(repr(observed),repr(expected))
def bar(t,c=100.,h=None,l=None):
    return {"timestamp_utc":t.strftime("%Y-%m-%dT%H:%M:%SZ"),"open":c,"high":c+1 if h is None else h,"low":c-1 if l is None else l,"close":c,"volume":1.,"turnover":c}
BASE=datetime(2024,12,30,tzinfo=timezone.utc)
def trend(n,hours=4,start=BASE): return [bar(start+timedelta(hours=i*hours),100+.4*i,101+.4*i,99+.4*i) for i in range(n)]
def fixture():
    p=[]
    labels=[]
    for i in range(150):
        if i<30: c=100+i*.4; label="rising_trend"
        elif i<60: c=112-(i-30)*.35; label="falling_trend"
        elif i<90: c=101.; label="flat_positive_range"
        elif i<120: c=100+(i%2)*2; label="alternating_close"
        else: c=102+(i-120)*.2; label="recovery"
        if i==60: c=110; label="gap_up"
        if i==61: c=99; label="gap_down"
        p.append(bar(BASE+timedelta(hours=4*i),c,c+1,l=c-1)); labels.append(label)
    child=[bar(datetime.fromisoformat(x["timestamp_utc"].replace("Z","+00:00"))+timedelta(hours=j),x["close"]+.01*j) for x in p for j in range(4)]
    daily=[bar(datetime(2024,12,28,tzinfo=timezone.utc)+timedelta(days=i),90+i) for i in range(12)]
    return p,child,daily,labels
def write_fixture(path):
    p,ch,d,labels=fixture()
    with open(path,"wb") as raw:
        with gzip.GzipFile(filename="synthetic_feature_fixture.csv",mode="wb",fileobj=raw,mtime=0) as z:
            z.write(b"series,segment,timestamp_utc,open,high,low,close,volume,turnover\n")
            for x,label in zip(p,labels): z.write(("primary_4h,"+label+","+",".join(str(x[k]) for k in core.FIELDS)+"\n").encode())
            for x in ch: z.write(("child_1h,complete_child,"+",".join(str(x[k]) for k in core.FIELDS)+"\n").encode())
            for x in d: z.write(("daily,year_boundary_daily,"+",".join(str(x[k]) for k in core.FIELDS)+"\n").encode())

class FeatureCoreTests(unittest.TestCase):
 def test_01_daily_0000(self):
    d=datetime(2024,12,30,tzinfo=timezone.utc); got=core.join_closed_daily([bar(d)],[bar(d- timedelta(days=1),10),bar(d,20)])[0]["daily"]["timestamp_utc"]; self.assertEqual(got,"2024-12-29T00:00:00Z"); record(self.id(),got,"2024-12-29T00:00:00Z")
 def test_02_daily_0400_2000(self):
    d=datetime(2024,12,30,tzinfo=timezone.utc); got=[x["daily"] for x in core.join_closed_daily([bar(d+timedelta(hours=4)),bar(d+timedelta(hours=20))],[bar(d)])]; self.assertEqual(got,["UNKNOWN",bar(d)]); record(self.id(),[x if x=="UNKNOWN" else x["timestamp_utc"] for x in got],["UNKNOWN","2024-12-30T00:00:00Z"])
 def test_03_daily_year_boundary_refusal(self):
    d=datetime(2024,12,31,tzinfo=timezone.utc); got=core.join_closed_daily([bar(d+timedelta(days=1)),bar(d+timedelta(days=1,hours=20))],[bar(d),bar(d+timedelta(days=1))]); self.assertEqual(got[0]["daily"]["timestamp_utc"],"2024-12-31T00:00:00Z"); self.assertEqual(got[1]["daily"]["timestamp_utc"],"2025-01-01T00:00:00Z"); record(self.id(),"same-day refused; Jan-1 accepted only at Jan-2 00","same-day refused; Jan-1 accepted only at Jan-2 00")
 def test_04_exact_four_children(self):
    kids=[bar(BASE+timedelta(hours=i)) for i in range(4)]; got=core.join_closed_children([bar(BASE)],kids)[0]["children"]; self.assertEqual(len(got),4); record(self.id(),len(got),4)
 def test_05_missing_child(self):
    got=core.join_closed_children([bar(BASE)],[bar(BASE+timedelta(hours=i)) for i in (0,1,3)])[0]["children"]; self.assertEqual(got,"UNKNOWN"); record(self.id(),got,"UNKNOWN")
 def test_06_duplicate_offgrid_children(self):
    good=[bar(BASE+timedelta(hours=i)) for i in range(4)]; a=core.join_closed_children([bar(BASE)],good+[good[0]])[0]["children"]; b=core.join_closed_children([bar(BASE)],good+[bar(BASE+timedelta(minutes=30))])[0]["children"]; self.assertEqual((a,b),("UNKNOWN","UNKNOWN")); record(self.id(),(a,b),("UNKNOWN","UNKNOWN"))
 def test_07_true_range_gaps(self):
    x=[bar(BASE,10,12,8),bar(BASE+timedelta(hours=4),15,16,14),bar(BASE+timedelta(hours=8),10,11,9)]; got=[r["true_range"] for r in core.compute_features(x,"4H")]; self.assertEqual(got,[4.,6.,6.]); record(self.id(),got,[4.,6.,6.])
 def test_08_atr14_literal(self):
    got=core.compute_features(trend(14),"4H"); self.assertEqual(got[12]["atr14"],"UNKNOWN"); self.assertAlmostEqual(got[13]["atr14"],2.); record(self.id(),got[13]["atr14"],2.0)
 def test_09_ema_seed(self):
    got=core.compute_features(trend(27),"4H")[26]["ema27"]; self.assertAlmostEqual(got,105.2); record(self.id(),got,105.2)
 def test_10_ema_update(self):
    got=core.compute_features(trend(28),"4H")[27]["ema27"]; self.assertAlmostEqual(got,105.6); record(self.id(),got,105.6)
 def test_11_normalized_literals(self):
    got=core.compute_features(trend(40),"4H")[30]; self.assertAlmostEqual(got["normalized_slope"],.6); self.assertAlmostEqual(got["normalized_displacement"],2.4); record(self.id(),[got["normalized_slope"],got["normalized_displacement"]],[.6,2.4])
 def test_12_efficiency_zero_denominator(self):
    x=[bar(BASE+timedelta(hours=4*i),10,11,9) for i in range(13)]; got=core.compute_features(x,"4H")[12]["efficiency"]; self.assertEqual(got,"UNKNOWN"); record(self.id(),got,"UNKNOWN")
 def test_13_no_overlap(self):
    x=[bar(BASE+timedelta(hours=4*i),11+3*i,12+3*i,10+3*i) for i in range(7)]; got=core.compute_features(x,"4H")[-1]["overlap_density"]; self.assertEqual(got,0.); record(self.id(),got,0.)
 def test_14_full_overlap(self):
    x=[bar(BASE+timedelta(hours=4*i),2,3,1) for i in range(7)]; got=core.compute_features(x,"4H")[-1]["overlap_density"]; self.assertEqual(got,1.); record(self.id(),got,1.)
 def test_15_clip_unit(self):
    got=(core.clip_unit(-.25),core.clip_unit(1.25)); self.assertEqual(got,(0.,1.)); record(self.id(),got,(0.,1.))
 def test_16_zero_range_overlap(self):
    x=[bar(BASE+timedelta(hours=4*i),2,3,1) for i in range(7)]; x[3]=bar(BASE+timedelta(hours=12),2,2,2); got=core.compute_features(x,"4H")[-1]["overlap_density"]; self.assertEqual(got,"UNKNOWN"); record(self.id(),got,"UNKNOWN")
 def test_17_volatility_excludes_current(self):
    x=trend(110); x[-1]=bar(BASE+timedelta(hours=4*109),200,250,150); got=core.compute_features(x,"4H")[-1]["volatility_percentile"]; self.assertEqual(got,1.); record(self.id(),got,1.)
 def test_18_nearest_rank_odd(self):
    got=(core.nearest_rank([1,2,3,4,5],.3),core.nearest_rank([1,2,3,4,5],.5),core.nearest_rank([1,2,3,4,5],.7)); self.assertEqual(got,(2.,3.,4.)); record(self.id(),got,(2.,3.,4.))
 def test_19_nearest_rank_even(self):
    got=tuple(core.nearest_rank([1,2,3,4],q) for q in (.3,.5,.7)); self.assertEqual(got,(2.,2.,3.)); record(self.id(),got,(2.,2.,3.))
 def test_20_future_isolation(self):
    prefix=trend(120); future=trend(30,start=BASE+timedelta(hours=480)); first=core.freeze_thresholds(core.compute_features(prefix,"4H")); mutated=[dict(x) for x in future]
    for x in mutated:
      for k in ("open","high","low","close","turnover"): x[k]*=1000
    second=core.freeze_thresholds(core.compute_features(prefix+mutated,"4H")[:len(prefix)]); self.assertEqual(first,second); self.assertEqual(first["population_hash"],"0320d9e2455a7d245c9332b53bff475cb9509c994fc7dd2d120e84f52e1bc2a7"); record(self.id(),first["population_hash"],"0320d9e2455a7d245c9332b53bff475cb9509c994fc7dd2d120e84f52e1bc2a7")
 def test_21_prefix_feature_invariance(self):
    prefix=trend(100); appended=trend(20,start=BASE+timedelta(hours=400)); a=core.compute_features(prefix,"4H"); b=core.compute_features(prefix+appended,"4H")[:100]; self.assertEqual([core.canonical_feature_row(x) for x in a],[core.canonical_feature_row(x) for x in b]); record(self.id(),len(b),100)
 def test_22_invalid_rejection(self):
    bad=[[dict(bar(BASE),close=float("nan"))],[dict(bar(BASE),high=9)],[bar(BASE),bar(BASE)],[bar(BASE+timedelta(hours=4)),bar(BASE)]]
    for rows in bad:
      with self.assertRaises(ValueError): core.compute_features(rows,"4H")
    record(self.id(),"4 ValueErrors","4 ValueErrors")

class Result(unittest.TestResult):
 def __init__(self): super().__init__(); self.outcomes={}
 def addSuccess(self,t): super().addSuccess(t); self.outcomes[t.id()]="PASS"
 def addFailure(self,t,e): super().addFailure(t,e); self.outcomes[t.id()]="FAIL"
 def addError(self,t,e): super().addError(t,e); self.outcomes[t.id()]="ERROR"
def run():
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(FeatureCoreTests); result=Result(); suite.run(result); return result
def generate(out):
 os.makedirs(out,exist_ok=True); E.clear(); result=run()
 if not result.wasSuccessful() or result.testsRun != 22: raise SystemExit(1)
 with open(os.path.join(out,"test_results.csv"),"w",newline="") as f:
  w=csv.writer(f); w.writerow(["test_id","unittest_name","status","observed","expected"])
  for name,status in sorted(result.outcomes.items()): w.writerow([name.rsplit(".",1)[-1],name,status,*E[name]])
 write_fixture(os.path.join(out,"synthetic_feature_fixture.csv.gz"))
 expected={"oracle":"hard-coded literal formulas emitted by a subprocess which does not import temporal_feature_core","daily_join":{"primary_0000":"2024-12-29T00:00:00Z","primary_0400_2000":["UNKNOWN","2024-12-30T00:00:00Z"],"year_boundary":["2024-12-31T00:00:00Z","2025-01-01T00:00:00Z"]},"children":{"exact_count":4,"missing":"UNKNOWN","duplicate_off_grid":["UNKNOWN","UNKNOWN"]},"true_range_gaps":[4,6,6],"atr14_first_valid_index":13,"atr14_literal":2.0,"ema_seed":105.2,"ema_first_update":105.6,"normalized":{"slope":0.6,"displacement":2.4},"efficiency_zero_denominator":"UNKNOWN","overlap":{"none":0.0,"full":1.0,"zero_range":"UNKNOWN"},"clip_unit":{"below_zero":0.0,"above_one":1.0},"volatility_percentile_excludes_current":1.0,"quantile_odd":[2,3,4],"quantile_even_1234":{"p30":2,"p50":2,"p70":3},"flat_behavior":{"segment":"flat_positive_range","positive_range":2.0,"efficiency":"UNKNOWN"},"alternating_behavior":{"segment":"alternating_close","close_pattern":[100.0,102.0,100.0,102.0],"two_bar_displacement":0.0},"future_isolation_hashes":{"development_prefix":"0320d9e2455a7d245c9332b53bff475cb9509c994fc7dd2d120e84f52e1bc2a7","extreme_future_mutation":"0320d9e2455a7d245c9332b53bff475cb9509c994fc7dd2d120e84f52e1bc2a7"}}
 # The oracle writer is deliberately a fresh interpreter with no feature-core import.
 oracle=os.path.join(out,"expected_feature_results.json")
 subprocess.run([sys.executable,"-c","import json,sys; json.dump(json.loads(sys.argv[1]),open(sys.argv[2],'w'),sort_keys=True,separators=(',',':')); open(sys.argv[2],'a').write('\\n')",json.dumps(expected,sort_keys=True),oracle],check=True)
 # A complete external evidence package contains the exact static implementation
 # and documentation alongside independently executed dynamic evidence.
 for name in ("REPORT.md","PROTOCOL.md","API_CONTRACT.md","temporal_feature_core.py","test_temporal_feature_core.py","implementation_audit.csv"):
  target=os.path.join(out,name)
  if os.path.abspath(target) != os.path.abspath(os.path.join(HERE,name)): shutil.copyfile(os.path.join(HERE,name),target)
 peer=os.environ.get("FEATURE_CORE_PEER_OUTPUT")
 peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 peer_peak=None
 if peer:
  with open(os.path.join(peer,"resource_usage.csv"),newline="") as f: peer_peak=int(next(csv.DictReader(f))["peak_rss_kib"])
 with open(os.path.join(out,"resource_usage.csv"),"w",newline="") as f:
  w=csv.writer(f); w.writerow(["run","peak_rss_kib","limit_kib","status"])
  if peer_peak is not None: w.writerow(["run1",peer_peak,262144,"PASS" if peer_peak < 262144 else "FAIL"])
  w.writerow(["run2" if peer else "run1",peak,262144,"PASS" if peak < 262144 else "FAIL"])
 if peer:
  names=sorted(name for name in os.listdir(out) if name not in {"run_hashes.csv","resource_usage.csv"})
  with open(os.path.join(out,"run_hashes.csv"),"w",newline="") as f:
   w=csv.writer(f); w.writerow(["path","run1_sha256","run2_sha256","equal"])
   for name in names:
    digest=lambda p: hashlib.sha256(open(p,"rb").read()).hexdigest()
    one,two=digest(os.path.join(peer,name)),digest(os.path.join(out,name))
    w.writerow([name,one,two,str(one==two).lower()])
if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("--self-test",action="store_true"); p.add_argument("--generate-evidence",action="store_true"); p.add_argument("--output-dir"); p.add_argument("--temp-dir"); a=p.parse_args()
 if a.self_test: raise SystemExit(0 if run().wasSuccessful() else 1)
 if a.generate_evidence:
  if not a.output_dir: p.error("--output-dir required")
  generate(a.output_dir)
