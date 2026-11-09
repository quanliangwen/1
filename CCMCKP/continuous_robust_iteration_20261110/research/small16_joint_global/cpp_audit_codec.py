"""Original decimal text -> exact bounded-integer C++ audit stream.

Independent of small_exact_integer_core; includes capacities in the scale.
"""
from decimal import Decimal
def scale(strings):
 parts=[]
 for value in strings:
  d=Decimal(str(value))
  if not d.is_finite():raise ValueError('Finite decimal required')
  t=d.as_tuple();coefficient=0
  for digit in t.digits:coefficient=coefficient*10+digit
  parts.append((-coefficient if t.sign else coefficient,t.exponent))
 if not parts:raise ValueError('Empty decimal input')
 exponent=min(t[1] for t in parts);values=[coefficient*10**(power-exponent) for coefficient,power in parts]
 if any(abs(v)>=(1<<126) for v in values):raise ValueError('C++ exact audit domain exceeded')
 return values,exponent
def write_model(stream,samples,m,queries):
 thresholds=[str(q[0]) for q in queries];values,exponent=scale([s for a in samples for s in a]+thresholds);offset=0
 stream.write(f'{len(samples)} {m} {len(queries)}\n')
 for a in samples:
  stream.write(str(len(a))+' '+' '.join(map(str,values[offset:offset+len(a)]))+'\n');offset+=len(a)
 for k,(_,n,den,selection) in enumerate(queries):
  if len(selection)!=m:raise ValueError('Wrong query dimension')
  stream.write(f'{values[offset+k]} {n} {den} '+' '.join(map(str,selection))+'\n')
 return exponent
