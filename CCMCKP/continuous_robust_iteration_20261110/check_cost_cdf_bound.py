from pathlib import Path
import itertools,json,math
import numpy as np
from cdf_cost_bound import envelope_pmfs,positive_log_convolution_mass,diagnostic_bound
H=Path(__file__).parent;rng=np.random.default_rng(105);comparisons=0;largest_violation=-math.inf;details=[]
for m in [2,3,4]:
 for trial in range(8):
  groups=[np.arange(2*g,2*g+2) for g in range(m)];cost=rng.integers(1,10,2*m).astype(float);samples=[rng.integers(0,7,3) for _ in range(2*m)];T=int(rng.integers(2,6*m));grid=T
  cdfs=np.asarray([[np.mean(a<=t) for t in range(grid+1)] for a in samples]);c0=sum(cost[g].min() for g in groups)
  actual=[]
  for selection in itertools.product(*groups):
   totals=[sum(x) for x in itertools.product(*(samples[j] for j in selection))];p=sum(x<=T for x in totals)/len(totals);actual.append((selection,p,float(cost[list(selection)].sum())))
  for lam in [0.,.01,.05,.2,.5,1.]:
   for fixed in [{},{0:int(groups[0][0])}]:
    pmfs,_=envelope_pmfs(groups,cost,cdfs,lam,fixed);lm=positive_log_convolution_mass(pmfs,T)
    if lm is None:continue
    mass=math.exp(lm)
    for selection,p,c in actual:
     if any(selection[g]!=j for g,j in fixed.items()):continue
     discounted=p*math.exp(-lam*(c-c0));violation=discounted-mass;largest_violation=max(largest_violation,violation);assert violation<2e-12;comparisons+=1
    for C in [c0,float(np.median([a[2] for a in actual])),max(a[2] for a in actual)]:
     bound=diagnostic_bound(groups,cost,cdfs,C,lam,fixed)['upper']
     for selection,p,c in actual:
      if c>C or any(selection[g]!=j for g,j in fixed.items()):continue
      assert p<=bound+2e-12;comparisons+=1
  details.append(dict(groups=m,trial=trial,capacity=T,selections=len(actual),outcomes_per_selection=3**m))
# Deterministic test has exact feasible-cost threshold20; C19 must be excluded.
groups=[np.array([0,1]),np.array([2,3])];cost=np.array([0.,10.,0.,10.]);cdfs=np.array([[0.,0.,0.,0.,0.],[1.,1.,1.,1.,1.]]*2)
bad=diagnostic_bound(groups,cost,cdfs,19.,1.)['upper'];good=diagnostic_bound(groups,cost,cdfs,20.,1.)['upper'];assert abs(bad-math.exp(-1))<1e-12 and abs(good-1)<1e-12;comparisons+=2
result=dict(passed=True,comparisons=comparisons,largest_discounted_probability_excess=largest_violation,deterministic_cost19_bound=bad,deterministic_cost20_bound=good,scope='24 independently enumerated toy models, joint sample outcomes counted directly; unconditional and fixed-prefix bounds; floating numerical checks, not rigorous benchmark proof',models=details)
(H/'COST_CDF_BOUND_MATH_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='models'}))
