import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import sys,pathlib,json,gzip,itertools,time
import numpy as np
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H/'candidate'))
from stable_solver import CachedFactor,StableSolver,binary_model
from instance import load_instance
import engine as base
cases=json.load(open(H/'frozen/original_experiment/cases.json'));checks=[]
# Independent brute-force check of binary subproblem and solution exclusion.
groups=[np.array([0,1]),np.array([2,3]),np.array([4,5])];c=np.array([5.,2.,4.,8.,3.,7.]);w=np.array([1.,6.,4.,0.,5.,1.]);ss=binary_model(groups,6,c,[w],[-np.inf],[8.],3.,4)
exact=sorted((float(c[list(s)].sum()),s) for s in itertools.product(*groups) if w[list(s)].sum()<=8.)
assert [float(c[list(s)].sum()) for s in ss]==[v[0] for v in exact[:len(ss)]]
assert len(set(ss))==len(ss) and all((float(c[list(s)].sum()),s) in exact for s in ss)
assert len(ss)==min(4,len(exact));checks.append(dict(test='HiGHS vs exhaustive enumeration',passed=True))
for i in [11,19,37,39]:
 case=next(c for c in cases if c['index']==i);inst=load_instance('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+case['instance'])
 data=json.load(gzip.open(H/'quick_v2'/f'stable_{i}_r1.json.gz','rt'));selection=tuple(data['selected']['selection'])
 sol=StableSolver(inst,case['tmax'],999123,600,H/'unused.json.gz',time.monotonic(),'B_CDF_DRO_MITM')
 regular=[CachedFactor.__mro__[1](j,float(inst.costs[j]),0,str(inst.path/f'{j}_sample.txt')) for j in selection]
 cached=[sol.factors[j] for j in selection]
 for a,b in zip(regular,cached):assert all(a.get_index_sample(k)==b.get_index_sample(k) for k in range(len(a.samples)))
 t=time.monotonic();np.random.seed(777001);p0=sol.native_func(regular,sol.T,1000000,.99,sol.param,sol.checks);state0=np.random.get_state();slow=time.monotonic()-t
 t=time.monotonic();np.random.seed(777001);p1=sol.native_func(cached,sol.T,1000000,.99,sol.param,sol.checks);state1=np.random.get_state();fast=time.monotonic()-t
 assert p0==p1 and all(np.array_equal(a,b) for a,b in zip(state0,state1))
 pguide,w=sol.gradients(selection);tilted=sol.guide_probability(selection);error=abs(pguide-tilted)
 assert error<1e-7,(pguide,tilted)
 checks.append(dict(test='native cache and RNG parity; tilted vs truncated CDF',case=i,passed=True,native=p1,guide_truncated=pguide,guide_tilted=tilted,tilt_error=error,regular_seconds=slow,cached_seconds=fast))
print(json.dumps(checks,indent=2));(H/'candidate_verification.json').write_text(json.dumps(checks,indent=2))
