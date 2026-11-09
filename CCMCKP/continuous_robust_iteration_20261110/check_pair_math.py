from pathlib import Path
import sys,json,itertools
import numpy as np
H=Path(__file__).parent;sys.path.insert(0,str(H/'iterations/I004_robust_pair_exchange/candidate'))
from pair_exchange import tilted_fourier,pair_scores
rng=np.random.default_rng(104);checks=0;maxerr=0.
for B in [16,31,64]:
 for m in [3,5,8]:
  hist=rng.random((m*3,B));hist/=hist.sum(axis=1,keepdims=True);F,W=tilted_fourier(hist);s=np.arange(m)*3
  for ga,gb in itertools.combinations(range(m),2):
   others=[s[g] for g in range(m) if g not in [ga,gb]];rest=np.prod(F[others],axis=0);left=np.arange(ga*3,ga*3+3);right=np.arange(gb*3,gb*3+3);p=pair_scores(F,W,rest,left,right)
   for a,b in itertools.product(range(3),repeat=2):
    ids=others+[left[a],right[b]];c=np.array([1.])
    for j in ids:c=np.convolve(c,hist[j])
    exact=c[:B].sum();error=abs(p[a,b]-exact);maxerr=max(maxerr,float(error));assert error<3e-8;checks+=1
record=dict(passed=True,checks=checks,max_abs_error=maxerr,reference='independent full np.convolve; every pair alternative, no truncation FFT reused',score_only=True,final_integer_certificates_unchanged=True)
(H/'PAIR_MATH_CHECK.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
