"""Exact original-decimal empirical MITM with reusable half sums.

This is an audit/research primitive, not a change to the frozen optimizer.
No data, native distributions, search history, or probability thresholds loaded.
"""
from decimal import Decimal
from fractions import Fraction
from itertools import product
from bisect import bisect_left
from math import prod

def decimal_integers(strings):
 parts=[]
 for s in strings:
  d=Decimal(str(s))
  if not d.is_finite():raise ValueError('Finite decimal required')
  t=d.as_tuple();parts.append(((-1 if t.sign else 1)*int(''.join(map(str,t.digits))),t.exponent))
 if not parts:raise ValueError('Nonempty decimal list required')
 exponent=min(e for _,e in parts)
 return [a*10**(e-exponent) for a,e in parts],exponent

class ExactHalfSums:
 def __init__(self,samples):
  if not samples or any(not a for a in samples):raise ValueError('Nonempty original marginals required')
  values,self.exponent=decimal_integers([x for a in samples for x in a]);self.samples=[];offset=0
  for a in samples:self.samples.append(tuple(values[offset:offset+len(a)]));offset+=len(a)
  self.left={};self.right={};self.calls=0
 def count(self,selection,capacity):
  selection=tuple(selection);cut=len(selection)//2;left=selection[:cut];right=selection[cut:]
  if left not in self.left:self.left[left]=tuple(sum(x) for x in product(*(self.samples[j] for j in left)))
  if right not in self.right:self.right[right]=tuple(sorted(sum(x) for x in product(*(self.samples[j] for j in right))))
  scaled=Fraction(str(capacity))*Fraction(10)**(-self.exponent);threshold=-(-scaled.numerator//scaled.denominator)
  n=sum(bisect_left(self.right[right],threshold-x) for x in self.left[left]);den=prod(len(self.samples[j]) for j in selection);self.calls+=1
  if not 0<=n<=den:raise ArithmeticError('Invalid exact count')
  return n,den
 def cache_stats(self):return dict(left_vectors=len(self.left),right_vectors=len(self.right),left_sums=sum(map(len,self.left.values())),right_sums=sum(map(len,self.right.values())),exact_counts=self.calls)
