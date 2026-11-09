from pathlib import Path
import sys,json,pickle,itertools,gzip,math,hashlib
from fractions import Fraction
import numpy as np
H=Path(__file__).parent;I=H/'iterations/I005_exact_cdf_bound';sys.path[:0]=[str(I/'candidate'),str(I/'vendor313')]
from instance import load_instance
from prefix_bound import PrefixBound
root=I/(sys.argv[1] if len(sys.argv)>1 else 'math01');root.mkdir(exist_ok=False);rng=np.random.default_rng(1005);checks=0;records=[]
for m in [2,3,4]:
 for trial in range(4):
  folder=root/f'm{m}_t{trial}';folder.mkdir();groups=[list(range(g*3,g*3+3)) for g in range(m)];samples=[];cost=[]
  for g in range(m):
   samples.extend([rng.integers(0,9,5),rng.integers(0,6,5),rng.integers(0,2,5)]);cost.extend([int(rng.integers(1,4)),int(rng.integers(4,7)),int(rng.integers(7,10))])
  (folder/'cost.txt').write_text('\n'.join(map(str,cost)));(folder/'node_to_factor.pkl').write_bytes(pickle.dumps(groups))
  for j,a in enumerate(samples):(folder/f'{j}_sample.txt').write_text('\n'.join(map(str,a.tolist())))
  T=8 if trial%2==0 else 16;truth={}
  for selection in itertools.product(*groups):
   outcomes=[sum(v) for v in itertools.product(*(samples[j] for j in selection))];truth[selection]=dict(cost=sum(cost[j] for j in selection),strict=Fraction(sum(v<T for v in outcomes),len(outcomes)),inclusive=Fraction(sum(v<=T for v in outcomes),len(outcomes)))
  minimum=min(v['cost'] for v in truth.values() if v['strict']>=Fraction(99,100))
  inst=load_instance(folder)
  for label,C in [('below',minimum-1),('at',minimum)]:
   out=folder/(label+'.json');b=PrefixBound(inst,T,str(C),64,15,out);result=b.run();assert result['raw_cost_line_excluded']==(label=='below');checks+=1
   prefixes=[];covered=0
   with gzip.open(str(out)+'.proof.jsonl.gz','rt') as f:
    for line in f:
     r=json.loads(line);prefix=tuple(r['prefix']);prefixes.append(prefix);covered+=r['cover'];matching=[v for s,v in truth.items() if s[:len(prefix)]==prefix]
     if r['kind']=='cost':assert all(v['cost']>C for v in matching);checks+=1
     elif r['kind']=='cdf':
      bound=Fraction(int(r['upper_numerator']),int(r['denominator']));assert bound<Fraction(99,100);assert all(v['inclusive']<=bound for v in matching);checks+=len(matching)
     elif r['kind']=='raw_refuted':assert truth[prefix]['strict']<Fraction(99,100);checks+=1
     elif r['kind']=='raw_accepted':assert truth[prefix]['strict']>=Fraction(99,100) and truth[prefix]['cost']<=C;checks+=1
     else:raise AssertionError('Unresolved toy model')
   for p in result['pending_frontier']:prefixes.append(tuple(p['prefix']));covered+=math.prod(len(g) for g in groups[len(p['prefix']):])
   for i,a in enumerate(prefixes):
    for other in prefixes[:i]:assert a[:len(other)]!=other and other[:len(a)]!=a
   assert covered==len(truth);checks+=1
   records.append(dict(groups=m,trial=trial,label=label,true_minimum=minimum,cost_limit=C,status=result['status'],visited=result['visited_nodes'],terminal=result['terminal_counts']))
result=dict(passed=True,checks=checks,input_models=12,cost_line_proof_runs=24,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (I/'candidate').glob('*.py')},scope='independent exhaustive all item choices and joint sample outcomes; verifies every pruned subtree inclusive probability, exact cost, raw leaf decision and prefix-free total coverage',records=records)
(H/'I005_EXACT_BOUND_MATH_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='records'}))
