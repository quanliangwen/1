import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import pathlib,sys,json,numpy as np
H=pathlib.Path(__file__).parent;sys.path.insert(0,str(H/'iterations/I001_risk_portfolio/candidate'))
from risk_models import cvar_weights,gamma_support
from scipy.optimize import linprog
rng=np.random.default_rng(711001);cvar_checks=0;gamma_checks=0
for n in [2,5,17,33]:
 for eps in [.01,.05,.1,.25,1/3,.8,1.]:
  for kind in ['continuous','ties']:
   loss=rng.normal(1,3,n) if kind=='continuous' else rng.integers(-2,5,n).astype(float)
   w=cvar_weights(loss,eps);dual=float(w@loss)
   primal=min(float(t+np.maximum(loss-t,0.).mean()/eps) for t in loss)
   lp=linprog(-loss,A_eq=np.ones((1,n)),b_eq=[1.],bounds=[(0.,1/(eps*n))]*n,method='highs')
   if not lp.success or abs(dual+lp.fun)>1e-8 or abs(dual-primal)>1e-8:raise AssertionError('CVaR dual/primal mismatch')
   cvar_checks+=1
for n in [2,5,17,33]:
 for gamma in [0.,.5,1.,1.25,2.,float(n)]:
  d=np.abs(rng.normal(size=n));ref=min(float(gamma*pi+np.maximum(d-pi,0.).sum()) for pi in np.r_[0.,d])
  if abs(gamma_support(d,gamma)-ref)>1e-10:raise AssertionError('Gamma support mismatch')
  gamma_checks+=1
result=dict(CVaR_primal_dual_LP_checks=cvar_checks,Gamma_support_checks=gamma_checks,passed=True)
(H/'RISK_MATH_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
