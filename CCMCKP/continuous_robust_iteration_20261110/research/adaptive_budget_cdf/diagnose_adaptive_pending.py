import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,pickle,time,hashlib
import numpy as np
from cdf_cost_bound import item_cdfs
from adaptive_budget_cdf import adaptive_upper
H=Path(__file__).parent;P=H/'iterations/I005_exact_cdf_bound/case35/probe_old_512_120.json';proof=json.load(open(P));c=next(c for c in json.load(open(H/'CASES.json')) if c['index']==35)
p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(p/'cost.txt');groups=pickle.load(open(p/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
cdfs=item_cdfs([np.loadtxt(p/f'{j}_sample.txt') for j in range(len(cost))],c['tmax'],512);rows=[];start=time.monotonic()
for node in proof['pending_frontier']:
 prefix=node['prefix']
 if len(prefix)>7:continue
 restricted=[[prefix[g]] if g<len(prefix) else group for g,group in enumerate(groups)]
 curves=[dict(order=tag,upper=adaptive_upper(restricted,cost,cdfs,float(proof['cost_limit'].split('/')[0])/float(proof['cost_limit'].split('/')[1]),256,tag=='reverse')) for tag in ['natural','reverse']]
 row=dict(prefix=prefix,depth=len(prefix),best=min(x['upper'] for x in curves),curves=curves);rows.append(row);print(json.dumps(row),flush=True)
d=dict(scope='FLOAT FFT restricted-prefix adaptive-policy diagnostics only; no rigorous new pruning, no LSS calls',frontier_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),source_sha256={n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in ['adaptive_budget_cdf.py','cdf_cost_bound.py',Path(__file__).name]},rows=rows,seconds=time.monotonic()-start)
(H/'ADAPTIVE_PENDING_DIAGNOSTIC.json').write_text(json.dumps(d,indent=2))
