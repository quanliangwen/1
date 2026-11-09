"""Explore cost-coupled optimistic CDF bounds on the preserved I005 frontier.

This is a numerical diagnostic, never a probability certificate. It reads
original empirical samples and the scalar cost line/prefixes, no true model,
historical solution vectors or validation cache.
"""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']: os.environ[k]='1'
from pathlib import Path
from fractions import Fraction
import json,pickle,time,hashlib,math
import numpy as np
from cdf_cost_bound import item_cdfs,diagnostic_bound
H=Path(__file__).parent;P=H/'iterations/I005_exact_cdf_bound/case35/probe_old_30.json'
proof=json.loads(P.read_text());case=next(c for c in json.load(open(H/'CASES.json')) if c['index']==35)
p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/case['instance']
costq=[Fraction(s) for s in (p/'cost.txt').read_text().split()];cost=np.array(list(map(float,costq)))
groups=pickle.load(open(p/'node_to_factor.pkl','rb'))
groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
groups=[list(map(int,g)) for g in groups];C=Fraction(proof['cost_limit']);mins=[min(costq[j] for j in g) for g in groups]
samples=[np.loadtxt(p/f'{j}_sample.txt') for j in range(len(cost))]
start=time.monotonic();cdf=item_cdfs(samples,case['tmax'],512);rows=[]
for node in proof['pending_frontier']:
 prefix=node['prefix'];fixed=dict(enumerate(prefix));d=len(prefix)
 excess=C-sum((costq[j] for j in prefix),Fraction(0))-sum(mins[d:],Fraction(0))
 allowed=[([prefix[g]] if g<d else [j for j in group if costq[j]-mins[g]<=excess]) for g,group in enumerate(groups)]
 curves={}
 for tag,gs in [('unconditional',groups),('individually_affordable',allowed)]:
  if any(not g for g in gs):curves[tag]=dict(empty_cost_range=True);continue
  curve=[diagnostic_bound(gs,cost,cdf,float(C),lam,fixed) for lam in [0.,.001,.003,.01,.03,.1,.3,1.,3.,10.]]
  best=min((r for r in curve if r['upper'] is not None),key=lambda r:r['log_upper'])
  curves[tag]=dict(best=best,curve=curve)
 row=dict(prefix=prefix,depth=d,remaining_excess=str(excess),remaining_options_before=sum(map(len,groups[d:])),remaining_options_after=sum(map(len,allowed[d:])),curves=curves)
 rows.append(row);print(json.dumps(dict(depth=d,baseline=curves['unconditional']['best']['upper'],cost_coupled=curves['individually_affordable'].get('best',{}).get('upper'),lambda_best=curves['individually_affordable'].get('best',{}).get('dual_multiplier'))),flush=True)
result=dict(scope='floating exploratory diagnostics only; no global exclusion and no new LSS calls',case=35,grid=512,frontier_nodes=len(rows),elapsed=time.monotonic()-start,source_sha256={n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in ['cdf_cost_bound.py',Path(__file__).name]},frontier_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),rows=rows)
(H/'PENDING_COST_CDF_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2))
