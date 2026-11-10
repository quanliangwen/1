from pathlib import Path
import sys,json,hashlib
H=Path(__file__).resolve().parent;S=H/'iterations/I016_cdf_pair_cover/candidate';sys.path[:0]=[str(S),str(S.parent/'vendor313')]
import numpy as np
from third_group_repair import propose
from engine import truncated_convolution
T=H/'research/third_group_repair_preflight';T.mkdir(exist_ok=True);out=T/'MATH_CHECK.json'
if out.exists():raise RuntimeError('No prototype math evidence overwrite')
rng=np.random.default_rng(9716601);checks=0;maxerr=0.;records=[]
for fixture in range(36):
 groups=[list(range(3*g,3*g+3)) for g in range(5)];center=[r[2] for r in groups];pair=list(center);pair[fixture%5]=groups[fixture%5][0];pair[(fixture+1)%5]=groups[(fixture+1)%5][0];B=24;hist=rng.integers(0,8,(15,B)).astype(float);hist/=hist.sum(axis=1)[:,None];cost=np.tile([1.,2.,3.],5)
 rows=propose(groups,cost,hist,center,pair)
 for r in rows:
  q=r['selection'];poly=np.r_[1.,np.zeros(B-1)]
  for j in q:poly=truncated_convolution(poly,hist[j],B)
  error=abs(float(poly.sum())-r['guide_probability']);maxerr=max(maxerr,error)
  assert error<1e-11 and len(set(q))==5 and sum(a!=b for a,b in zip(q,center))==3 and sum(a!=b for a,b in zip(q,pair))==1 and abs(sum(cost[j] for j in q)-r['cost'])<1e-12 and r['cost']<sum(cost[j] for j in center)-1e-7 and all(r['guide_probability']>=t for t in r['layer_targets']);checks+=1
 records.append(dict(fixture=fixture,proposals=len(rows)))
for bad in [[r[2] for r in groups],[r[0] for r in groups]]:
 try:propose(groups,cost,hist,center,bad)
 except ValueError:checks+=1
 else:raise AssertionError('Non-two-group pair accepted')
assert checks>2
v=dict(passed=True,fixtures=36,checks=checks,max_probability_error=maxerr,scope='actual proposal kernel versus direct positive truncated convolutions; no benchmark search/MC/performance or new feasibility claim',preflight_recovery='first test incorrectly required nonempty proposals for every random fixture; actual proposal layers may legitimately be empty; removed only that fixture assumption and retained all36 fixtures including empty outcomes; numerical proposal source unchanged',source_sha256=hashlib.sha256((H/'third_group_repair.py').read_bytes()).hexdigest(),records=records)
with out.open('x') as f:json.dump(v,f,indent=2)
print(json.dumps({k:x for k,x in v.items() if k!='records'}))
