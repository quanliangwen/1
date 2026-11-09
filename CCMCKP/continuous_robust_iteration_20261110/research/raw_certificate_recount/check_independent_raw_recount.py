from pathlib import Path
from fractions import Fraction as F
import itertools,random,math,json,hashlib
from independent_raw_recount import rational_joint_count,upward_grid_count
H=Path(__file__).parent;rng=random.Random(1200);checks=0;models=[]
for m in range(1,6):
 for trial in range(10):
  arrays=[[F(rng.randrange(0,21),4) for _ in range(rng.randrange(2,6))] for _ in range(m)];T=F(rng.randrange(1,22),2);outcomes=list(itertools.product(*arrays));den=math.prod(map(len,arrays));truth=sum(sum(x,F(0))<T for x in outcomes)
  assert rational_joint_count(arrays,T)==(truth,den);checks+=1
  for bins in [4,9,16,31]:
   truth_grid=0
   for outcome in outcomes:
    rounded=[min(bins,math.ceil(x*bins/T)) for x in outcome]
    truth_grid+=sum(rounded)<bins
   num,d=upward_grid_count(arrays,T,bins);assert (num,d)==(truth_grid,den) and num<=truth;checks+=1
  models.append(dict(groups=m,trial=trial,observations=list(map(len,arrays)),outcomes=den))
result=dict(passed=True,checks=checks,models=len(models),source_sha256=hashlib.sha256((H/'independent_raw_recount.py').read_bytes()).hexdigest(),scope='independent exhaustive rational joint outcomes including zero/above-capacity values, varying sample counts, strict ties and4ceil grids; unclipped shifted histograms equal clipped original-grid event',records=models)
with (H/'INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
