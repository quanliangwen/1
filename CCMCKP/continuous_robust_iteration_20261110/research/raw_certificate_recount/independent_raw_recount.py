"""Final-report verifier, independent of all optimizer/oracle modules.

Small models: exact rational meet-in-the-middle, with no IEEE intervals.
Large models: exact ceil-grid histograms, shifted balanced integer products.
"""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
from bisect import bisect_left
import sys,math
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H/'iterations/I002_cdf_neighborhood/vendor313'))
from flint import fmpz_poly

def rational_joint_count(arrays,T):
 T=F(T);cut=len(arrays)//2
 def sums(items):
  values=[F(0)]
  for a in items:values=[x+y for x in values for y in a]
  return values
 left=sums(arrays[:cut]);right=sorted(sums(arrays[cut:]));num=sum(bisect_left(right,T-x) for x in left)
 return num,math.prod(map(len,arrays))

def upward_grid_count(arrays,T,bins):
 T=F(T);offset=0;histograms=[];den=math.prod(map(len,arrays))
 for a in arrays:
  q=[]
  for x in a:
   ratio=F(x)*bins/T;q.append(-(-ratio.numerator//ratio.denominator))
  minimum=min(q);offset+=minimum;histograms.append(Counter(v-minimum for v in q))
 cut=bins-offset
 if cut<=0:return 0,den
 polys=[]
 for counts in histograms:
  h=[0]*min(cut,max(counts)+1)
  for k,n in counts.items():
   if k<cut:h[k]=n
  polys.append(fmpz_poly(h))
 while len(polys)>1:polys=[(polys[k]*polys[k+1]).truncate(cut) if k+1<len(polys) else polys[k] for k in range(0,len(polys),2)]
 num=int(polys[0].truncate(cut)(1))
 if not 0<=num<=den:raise ArithmeticError('Invalid recount')
 return num,den

def verify(bench,selection,capacity,certificate):
 bench=Path(bench);selection=tuple(map(int,selection));T=F(str(capacity));arrays=[[F(x) for x in (bench/f'{j}_sample.txt').read_text().split()] for j in selection]
 if not arrays or any(not a or min(a)<0 for a in arrays):raise ValueError('Nonnegative nonempty observations required')
 if not certificate['all_original_samples'] or certificate['strict_event']!='sum<T':raise RuntimeError('Original raw predicate changed')
 old_n=int(certificate['lower_numerator']);old_d=int(certificate['denominator'])
 if 100*old_n<99*old_d or old_d!=math.prod(map(len,arrays)):raise RuntimeError('Invalid declared raw99 certificate')
 if certificate['method']=='outward_interval_integer_pair_count':
  if len(arrays)>5 or max(math.prod(map(len,arrays[:len(arrays)//2])),math.prod(map(len,arrays[len(arrays)//2:])))>2000000:raise RuntimeError('Unexpected small-model scope')
  num,den=rational_joint_count(arrays,T)
  if not old_n<=num<=int(certificate['upper_numerator']):raise RuntimeError('Interval certificate does not enclose exact rational count')
  method='exact_decimal_rational_joint_MITM'
 elif certificate['method']=='exact_integer_upward_grid_count':
  num,den=upward_grid_count(arrays,T,certificate['bins'])
  if num!=old_n or den!=old_d:raise RuntimeError('Original grid certificate failed independent recount')
  method='independent_ceil_grid_shifted_balanced_integer_count'
 else:raise RuntimeError('Unrecognized raw certificate method')
 if 100*num<99*den:raise RuntimeError('Selected vector fails original empirical99')
 return dict(passed=True,method=method,numerator=str(num),denominator=str(den),lower=float(F(num,den)),original_method=certificate['method'],original_lower_numerator=str(old_n),original_denominator=str(old_d),original_bins=certificate.get('bins'),sample_counts=list(map(len,arrays)))
