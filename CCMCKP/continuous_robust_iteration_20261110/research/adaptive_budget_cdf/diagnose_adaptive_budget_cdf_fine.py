import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,pickle,time,hashlib
import numpy as np
from cdf_cost_bound import item_cdfs
from adaptive_budget_cdf import adaptive_upper
H=Path(__file__).parent;c=next(c for c in json.load(open(H/'CASES.json')) if c['index']==35);base=next(r for r in json.load(open(H/'BASELINE_S10.json'))['rows'] if r['index']==35)
p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(p/'cost.txt');groups=pickle.load(open(p/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
samples=[np.loadtxt(p/f'{j}_sample.txt') for j in range(len(cost))];rows=[];start=time.monotonic()
for B,K in [(1024,512),(2048,1024)]:
 cdfs=item_cdfs(samples,c['tmax'],B)
 for reverse in [False,True]:
  t=time.monotonic();upper=adaptive_upper(groups,cost,cdfs,base['old_best'],K,reverse)
  r=dict(index=35,cost_line=base['old_best'],time_bins=B,cost_bins=K,order='reverse' if reverse else 'natural',upper=upper,seconds=time.monotonic()-t);rows.append(r);print(json.dumps(r),flush=True)
d=dict(scope='fine FLOAT FFT adaptive-policy budget-CDF exploration only, no rigorous exclusion; original criteria unchanged, no LSS call',source_sha256={n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in ['adaptive_budget_cdf.py','cdf_cost_bound.py',Path(__file__).name]},rows=rows,seconds=time.monotonic()-start)
(H/'ADAPTIVE_BUDGET_CDF_FINE_DIAGNOSTIC.json').write_text(json.dumps(d,indent=2))
