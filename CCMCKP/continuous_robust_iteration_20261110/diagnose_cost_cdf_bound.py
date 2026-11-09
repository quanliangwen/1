import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,json,time,pickle,hashlib
import numpy as np
from cdf_cost_bound import item_cdfs,diagnostic_bound
H=Path(__file__).parent;cases=json.load(open(H/'CASES.json'));base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};rows=[]
for c in cases:
 if c['index'] not in [30,32,35,37,38,39,40]:continue
 p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(p/'cost.txt');groups=pickle.load(open(p/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
 samples=[np.loadtxt(p/f'{j}_sample.txt') for j in range(len(cost))];start=time.monotonic();cdf=item_cdfs(samples,c['tmax'],512);curves={}
 for tag,C in [('historical_cost_line',base[c['index']]['old_best']),('S10_cost_line',base[c['index']]['new_avg']-1e-6)]:
  curve=[diagnostic_bound(groups,cost,cdf,C,l) for l in [0.,.0001,.0003,.001,.003,.01,.03,.1,.3,1.,3.,10.]]
  resolved=[r for r in curve if r['upper'] is not None];best=min(resolved,key=lambda r:r['log_upper']) if resolved else None
  curves[tag]=dict(cost_line=C,best=best,curve=curve)
 row=dict(index=c['index'],instance=c['instance'],T=c['tmax'],grid=512,groups=len(groups),curves=curves,seconds=time.monotonic()-start,scope='floating positive-convolution upper-envelope diagnostic; no rigorous global exclusion claimed',historical_data_use='scalar cost line only for external diagnostic; never reads solution vectors or native probabilities');rows.append(row);print(json.dumps(row),flush=True)
(H/'COST_CDF_BOUND_DIAGNOSTIC.json').write_text(json.dumps(dict(rows=rows,source_sha256={n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in ['cdf_cost_bound.py','diagnose_cost_cdf_bound.py']},claim='numerical diagnostic only, no benchmark optimality certificate'),indent=2))
