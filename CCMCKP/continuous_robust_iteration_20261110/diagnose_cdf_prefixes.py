import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,pickle,time,itertools,math
import numpy as np
from cdf_cost_bound import item_cdfs,diagnostic_bound
H=Path(__file__).parent;cases=json.load(open(H/'CASES.json'));base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};results=[];global_start=time.monotonic()
for c in cases:
 if c['index'] not in [30,32,35,37,38,39,40]:continue
 p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(p/'cost.txt');groups=pickle.load(open(p/'node_to_factor.pkl','rb'));groups=[np.asarray(groups[k],int) for k in sorted(groups,key=int)] if isinstance(groups,dict) else list(map(lambda x:np.asarray(x,int),groups));samples=[np.loadtxt(p/f'{j}_sample.txt') for j in range(len(cost))];cdf=item_cdfs(samples,c['tmax'],256)
 retained=[]
 for group in groups:
  keep=[]
  for j in group:
   dominated=False
   for k in group:
    if k==j or cost[k]>cost[j] or (cost[k]==cost[j] and k>j):continue
    if len(samples[k])!=len(samples[j]):continue
    if np.all(np.sort(samples[k])<=np.sort(samples[j])):dominated=True;break
   if not dominated:keep.append(int(j))
  retained.append(len(keep))
 impact=[np.ptp([np.mean(samples[j]) for j in g])+np.ptp([np.quantile(samples[j],.99) for j in g]) for g in groups];orders={'natural':[0,1],'resource_spread':list(map(int,np.argsort(-np.asarray(impact))[:2]))};prefixes=[];C=base[c['index']]['old_best'];start=time.monotonic()
 for label,order in orders.items():
  values=[];reject=0;unresolved=0;checked=0;total=math.prod(len(groups[g]) for g in order)
  for selection in itertools.product(*(groups[g] for g in order)):
   if time.monotonic()-global_start>45:break
   fixed=dict(zip(order,map(int,selection)));bounds=[diagnostic_bound(groups,cost,cdf,C,l,fixed) for l in [0.,.01,.03,.1,.3]];good=[b for b in bounds if b['upper'] is not None];checked+=1
   if not good:unresolved+=1;continue
   best=min(good,key=lambda b:b['log_upper']);values.append(best['upper']);reject+=int(best['upper']<.99)
  prefixes.append(dict(order=label,groups=order,prefixes_checked=checked,total_depth2_prefixes=total,complete_depth2_scan=checked==total,float_bound_below99=reject,numerically_unresolved=unresolved,min_upper=min(values) if values else None,median_upper=float(np.median(values)) if values else None,role='diagnostic of possible pruning only; no subproblem refutation certified'))
 results.append(dict(index=c['index'],T=c['tmax'],group_options=list(map(len,groups)),floating_FOSD_nondominated_counts=retained,dominance_scope='raw-only existence bound; cannot discard jointly LSS-feasible choices based solely on empirical dominance',prefixes=prefixes,seconds=time.monotonic()-start));print(json.dumps(results[-1]),flush=True)
 if time.monotonic()-global_start>45:break
(H/'CDF_PREFIX_DIAGNOSTIC.json').write_text(json.dumps(dict(rows=results,seconds=time.monotonic()-global_start,scope='budgeted floating depth2 diagnostic, no global optimality/infeasibility proof; no data or source change to F001'),indent=2))
