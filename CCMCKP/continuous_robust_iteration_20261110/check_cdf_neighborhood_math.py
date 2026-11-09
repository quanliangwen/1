import pathlib,sys,json,numpy as np
H=pathlib.Path(__file__).parent;sys.path.insert(0,str(H/'iterations/I002_cdf_neighborhood/candidate'))
from portfolio_lns import cdf_gradients
from engine import worst_cdf_hist
rng=np.random.default_rng(711002);tests=0
groups=[np.array([0,1]),np.array([2,3]),np.array([4,5])];samples=[rng.uniform(.01,6,7) for _ in range(6)];center=[0,2,4]
for B in [16,32,64]:
 for delta in [0.,.01,.1]:
  hist=np.asarray([worst_cdf_hist(a,10.,B,delta) for a in samples]);p,w=cdf_gradients(groups,hist,center)
  def direct(q):
   v=np.array([1.])
   for j in q:v=np.convolve(v,hist[j])
   return float(v[:B].sum())
  if abs(p-direct(center))>1e-12:raise AssertionError('CDF center mismatch')
  for g,items in enumerate(groups):
   for j in items:
    q=center.copy();q[g]=int(j)
    if abs(p+w[j]-direct(q))>1e-12:raise AssertionError('One-group CDF derivative mismatch')
    tests+=1
result=dict(finite_support_CDF_single_group_checks=tests,passed=True,scope='proposal model only, original exact acceptance unchanged');(H/'CDF_NEIGHBORHOOD_MATH_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
