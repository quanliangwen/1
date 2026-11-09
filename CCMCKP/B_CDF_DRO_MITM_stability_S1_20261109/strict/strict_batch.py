import pathlib,json,gzip,time,concurrent.futures
from strict_select import EmpiricalOracle,select
H=pathlib.Path(__file__).parent;S=json.load(open(H/'validation/SUMMARY.json'));out=H/'strict_validation';out.mkdir(exist_ok=True)
def run(row):
 m=len(row['runs'][0]['selection']);oracle=EmpiricalOracle('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+row['instance'],row['capacity'],m);runs=[]
 for r in row['runs']:
  name=f"S1_{row['index']:02d}_r{r['rep']:02d}";d=json.load(gzip.open(H/'validation'/(name+'.json.gz'),'rt'));result=select(d,oracle);result.update(index=row['index'],rep=r['rep'])
  (out/(name+'.strict.json')).write_text(json.dumps(result,indent=2));runs.append(result)
 return dict(index=row['index'],runs=runs)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:
 rows=[]
 for result in p.map(run,S['rows']):rows.append(result);print(result['index'],flush=True)
(out/'STRICT_RESULTS.json').write_text(json.dumps(rows,indent=2))
