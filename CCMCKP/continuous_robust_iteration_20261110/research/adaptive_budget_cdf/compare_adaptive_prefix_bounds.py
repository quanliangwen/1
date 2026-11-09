import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
from fractions import Fraction
import json,pickle,time,hashlib
import numpy as np
from cdf_cost_bound import item_cdfs,diagnostic_bound
from adaptive_budget_cdf import adaptive_upper
H=Path(__file__).parent;P=H/'iterations/I005_exact_cdf_bound/case35/probe_old_512_120.json';proof=json.load(open(P));c=next(c for c in json.load(open(H/'CASES.json')) if c['index']==35)
p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(p/'cost.txt');groups=pickle.load(open(p/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
cdfs=item_cdfs([np.loadtxt(p/f'{j}_sample.txt') for j in range(len(cost))],c['tmax'],512);C=float(Fraction(proof['cost_limit']));rows=[];start=time.monotonic()
prefixes=[[],[30]]+[n['prefix'] for n in proof['pending_frontier'] if len(n['prefix'])<=7]+[[30,271,int(j)] for j in groups[2]]
for prefix in prefixes:
 restricted=[[prefix[g]] if g<len(prefix) else group for g,group in enumerate(groups)];fixed=dict(enumerate(prefix))
 baseline=diagnostic_bound(groups,cost,cdfs,C,0.,fixed)['upper'];curves=[dict(order=tag,upper=adaptive_upper(restricted,cost,cdfs,C,256,tag=='reverse')) for tag in ['natural','reverse']];best=min(x['upper'] for x in curves)
 row=dict(prefix=prefix,plain_CDF=baseline,adaptive_CDF=best,new_numerical_refutation=baseline>=.99 and best<.99,curves=curves);rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='curves'}),flush=True)
d=dict(scope='FLOAT comparisons only; neither branch pruning nor global exclusion certified; no true model or LSS call',frontier_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),source_sha256={n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in ['adaptive_budget_cdf.py','cdf_cost_bound.py',Path(__file__).name]},new_numerical_refutations=sum(r['new_numerical_refutation'] for r in rows),rows=rows,seconds=time.monotonic()-start)
(H/'ADAPTIVE_PREFIX_COMPARISON.json').write_text(json.dumps(d,indent=2))
