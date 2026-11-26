from pathlib import Path
from fractions import Fraction
from collections import Counter
import math,json,itertools,ast
R=Path(__file__).resolve().parent;s=(R/'audit_remote.py').read_text();ast.parse(s,feature_version=(3,8))
exec(s[s.index('def exact_rows'):s.index('\nrows=[]')])
values=[['0','.25'],['.5','.75'],['0','.25'],['.5','.75'],['0','0'],['.25','.5'],['0','0'],['.25','.5'],['0','0'],['.25','.5']]
d={'groups':[[2*g,2*g+1] for g in range(5)],'costs':[4,1]*5,'ordered':{j:sorted([Fraction(x) for x in row]*250) for j,row in enumerate(values)},'cache':{}}
prepare_radius(d);checks=0
for positive in [False,True]:
 for selection in itertools.product(*d['groups']):
  rows=[grid_row(d,j,128,Fraction(1),positive,True) for j in selection]
  nu,de=integer_polynomial_count(rows,128)
  unique=[sorted(set(row)) for row in rows]
  count=sum(sum(a)<128 for a in itertools.product(*unique))
  assert Fraction(nu,de)==Fraction(count,math.prod(len(u) for u in unique));checks+=1
 for block in [(0,1),(0,3),(1,3,4),(0,1,3,4)]:
  anchor=[0,2,4,6,8];record={'anchor':anchor,'block':list(block),'cost_cap':19,'bins':128}
  nu,de=proof_count(d,record,1,positive)
  for choices in itertools.product([0,1],repeat=len(block)):
   q=anchor.copy()
   for g,j in zip(block,choices):q[g]=2*g+j
   if sum(d['costs'][j] for j in q)>=19-1e-8:continue
   atoms=list(itertools.product(*(values[j] for j in q)))
   shift=sum((Fraction(d['radius_units'][j],10**12) for j in q),Fraction(0)) if positive else 0
   good=sum(sum(Fraction(x) for x in row)+shift<1 for row in atoms)
   assert Fraction(nu,de)>=Fraction(good,len(atoms));checks+=1
assert all(d['radius_units'][j]==0 for j in [4,6,8])
assert all(d['radius_units'][j]>0 for j in [0,1,2,3,5,7,9])
result={'status':'PASS','new_independent_reader_checks':checks,'no_solver_or_probability_sampling':True,'reader_sha256':__import__('hashlib').sha256(s.encode()).hexdigest()}
(R/'INDEPENDENT_READER_TEST.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
