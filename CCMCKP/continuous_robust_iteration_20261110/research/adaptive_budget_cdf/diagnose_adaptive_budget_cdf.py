import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,pickle,time,hashlib
import numpy as np
from cdf_cost_bound import item_cdfs
from adaptive_budget_cdf import adaptive_upper
H=Path(__file__).parent;rows=[];start=time.monotonic()
mathcheck=json.load(open(H/'ADAPTIVE_BUDGET_CDF_MATH_CHECK.json'))
if not mathcheck['passed'] or mathcheck['source_sha256']['adaptive_budget_cdf.py']!=hashlib.sha256((H/'adaptive_budget_cdf.py').read_bytes()).hexdigest():raise RuntimeError('Small exhaustive check first')
for index in [35,37,38,39,40]:
 c=next(c for c in json.load(open(H/'CASES.json')) if c['index']==index);base=next(r for r in json.load(open(H/'BASELINE_S10.json'))['rows'] if r['index']==index)
 p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(p/'cost.txt');groups=pickle.load(open(p/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
 samples=[np.loadtxt(p/f'{j}_sample.txt') for j in range(len(cost))]
 for B,K in [(256,128),(512,256)]:
  cdfs=item_cdfs(samples,c['tmax'],B);curves=[dict(order=tag,upper=adaptive_upper(groups,cost,cdfs,base['old_best'],K,tag=='reverse')) for tag in ['natural','reverse']]
  row=dict(index=index,instance=c['instance'],cost_line=base['old_best'],time_bins=B,cost_bins=K,best=min(x['upper'] for x in curves),curves=curves);rows.append(row);print(json.dumps(row),flush=True)
d=dict(scope='FLOAT FFT adaptive-policy budget-CDF diagnostic only; no rigorous exclusion, no native LSS calls, no acceptance changes',seconds=time.monotonic()-start,math_checks=mathcheck['checks'],source_sha256={n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in ['adaptive_budget_cdf.py','cdf_cost_bound.py',Path(__file__).name]},rows=rows)
(H/'ADAPTIVE_BUDGET_CDF_DIAGNOSTIC.json').write_text(json.dumps(d,indent=2))
