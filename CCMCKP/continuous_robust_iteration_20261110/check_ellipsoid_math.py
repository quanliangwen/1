from pathlib import Path
import sys,json,math
import numpy as np
H=Path(__file__).parent
sys.path.insert(0,str(H/'iterations/I003_ellipsoid_frontier/candidate'))
from ellipsoid_frontier import sqrt_secant
rng=np.random.default_rng(103);checks=0;max_error=0.
for n in [3,10,50]:
 for _ in range(20):
  sd=rng.uniform(.01,8,n);mask=rng.integers(0,2,n);k=rng.uniform(.1,4)
  z=sd*mask;norm=np.linalg.norm(z)
  support=float(z@(k*z/norm)) if norm else 0.
  expected=k*math.sqrt(float((sd**2)@mask))
  assert abs(support-expected)<1e-10
  u=rng.normal(size=(100,n));u=k*u/np.maximum(np.linalg.norm(u,axis=1,keepdims=True),1e-20)
  assert np.max(u@z)<=support+1e-10;checks+=2
for lower in [0.,.001,1.,100.]:
 for scale in [1.01,2.,10.,100.]:
  upper=lower*scale+.01;a,b=sqrt_secant(lower,upper)
  grid=np.linspace(lower,upper,2001);errors=a*grid+b-np.sqrt(grid)
  assert errors.max()<1e-10
  assert abs(a*lower+b-math.sqrt(lower))<1e-10
  assert abs(a*upper+b-math.sqrt(upper))<1e-10
  max_error=max(max_error,float(errors.max()));checks+=3
record=dict(passed=True,checks=checks,max_secant_above_sqrt=max_error,role='support identity, support maximizer and random directions; sqrt secant lower bound and endpoint equality',acceptance_unchanged=True)
(H/'ELLIPSOID_MATH_CHECK.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
