import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,pickle,itertools,math,time
import numpy as np
from cdf_cost_bound import item_cdfs,positive_log_convolution_mass
H=Path(__file__).parent;cases=json.load(open(H/'CASES.json'));base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};results=[];start=time.monotonic()
for c in cases:
 if c['index'] not in [30,32,35,37,38,39,40]:continue
 p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(p/'cost.txt');groups=pickle.load(open(p/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;samples=[np.loadtxt(p/f'{j}_sample.txt') for j in range(len(cost))];B=512;cdf=item_cdfs(samples,c['tmax'],B);hist=np.diff(np.pad(cdf,((0,0),(1,0))),axis=1);c0=sum(cost[g].min() for g in groups);blocks=[];built=time.monotonic()
 for first in range(0,len(groups),2):
  gs=groups[first:first+2];rows=[];deviations=[]
  for q in itertools.product(*gs):
   h=np.array([1.])
   for j in q:h=np.convolve(h,hist[j])[:B+1]
   rows.append(np.cumsum(h));deviations.append(sum(cost[j]-min(cost[g]) for j,g in zip(q,gs)))
  blocks.append((np.asarray(rows),np.asarray(deviations)))
 curves={}
 for label,C in [('old',base[c['index']]['old_best']),('S10_minus_1e6',base[c['index']]['new_avg']-1e-6)]:
  curve=[]
  for lam in [0.,.0001,.0003,.001,.003,.01,.03,.1,.3,1.,3.,10.]:
   pmfs=[]
   for F,dev in blocks:
    upper=np.max(F*np.exp(-lam*dev)[:,None],axis=0);pmfs.append(np.maximum(0.,np.diff(np.r_[0.,upper])))
   lm=positive_log_convolution_mass(pmfs,B)
   if lm is None:curve.append(dict(lam=lam,status='numerically unresolved',upper=None));continue
   logupper=lam*(C-c0)+lm;curve.append(dict(lam=lam,log_upper=logupper,upper=math.exp(min(0.,logupper)),proof=False))
  resolved=[q for q in curve if q['upper'] is not None];curves[label]=dict(cost_line=C,best=min(resolved,key=lambda q:q['log_upper']) if resolved else None,curve=curve)
 row=dict(index=c['index'],T=c['tmax'],block_groups=2,bins=B,precomputed_combinations=sum(len(b[1]) for b in blocks),seconds=time.monotonic()-built,curves=curves,scope='floating paired-group optimistic CDF relaxation; no rigorous exclusion or candidate qualification claim');results.append(row);print(json.dumps(row),flush=True)
(H/'BLOCK_CDF_DIAGNOSTIC.json').write_text(json.dumps(dict(rows=results,seconds=time.monotonic()-start,claim='diagnostic only'),indent=2))
