import sys,pathlib,itertools,types,random,json
from fractions import Fraction
import numpy as np
H=pathlib.Path(__file__).parent;sys.path.insert(0,str(H/'candidate'))
from small_counts import SmallCounts
rng=random.Random(10701);tests=0
for m in [2,3,4,5]:
 for _ in range(30):
  raw=[[str(rng.randint(0,20)/10) for k in range(4)] for j in range(m)]
  cap=str(rng.randint(0,50)/10);inst=types.SimpleNamespace(m=m,samples=[np.array(list(map(float,a))) for a in raw])
  v=SmallCounts(inst,float(cap)).count(tuple(range(m)))
  exact=sum(sum(x)<Fraction(cap) for x in itertools.product(*[[Fraction(t) for t in a] for a in raw]))
  if not int(v['lower_numerator'])<=exact<=int(v['upper_numerator']):raise AssertionError((raw,cap,v,exact))
  tests+=1
print(json.dumps(dict(boundary_tests=tests,passed=True)))
