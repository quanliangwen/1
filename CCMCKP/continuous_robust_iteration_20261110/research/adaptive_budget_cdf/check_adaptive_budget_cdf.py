from pathlib import Path
import itertools,json,hashlib
from fractions import Fraction
import numpy as np
from adaptive_budget_cdf import adaptive_upper
H=Path(__file__).parent;rng=np.random.default_rng(1007);checks=0;worst=0.;models=[]
for m in [2,3,4]:
 for trial in range(8):
  groups=[list(range(2*g,2*g+2)) for g in range(m)];cost=rng.integers(1,12,2*m).astype(float)
  samples=[rng.integers(0,7,4) for j in cost];T=int(rng.integers(2,5*m));cdfs=np.asarray([[np.mean(a<=t) for t in range(T+1)] for a in samples]);choices=[]
  for s in itertools.product(*groups):
   outcomes=[sum(x) for x in itertools.product(*(samples[j] for j in s))]
   choices.append(dict(cost=sum(cost[j] for j in s),p=Fraction(sum(x<=T for x in outcomes),len(outcomes))))
  c0=sum(min(cost[g]) for g in groups)
  for C in [c0,float(np.median([x['cost'] for x in choices])),max(x['cost'] for x in choices)]:
   actual=max((float(x['p']) for x in choices if x['cost']<=C),default=0.)
   for K in [8,32]:
    for reverse in [False,True]:
     upper=adaptive_upper(groups,cost,cdfs,C,K,reverse);worst=max(worst,actual-upper);assert actual<=upper+2e-12;checks+=1
  models.append(dict(groups=m,trial=trial,choices=len(choices),joint_outcomes=4**m))
d=dict(passed=True,checks=checks,input_models=len(models),largest_underestimate=worst,scope='independent exhaustive fixed choices and joint outcomes; floating numerical upper relaxation checks only, no rigorous benchmark certificate',source_sha256={n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in [Path(__file__).name,'adaptive_budget_cdf.py']},models=models)
(H/'ADAPTIVE_BUDGET_CDF_MATH_CHECK.json').write_text(json.dumps(d,indent=2));print(json.dumps({k:v for k,v in d.items() if k!='models'}))
