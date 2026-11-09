"""Independent replay: sorted threshold CDFs + shifted balanced integer products.
Does not import the branch implementation. Verifies a prefix-free partition of
the entire finite choice space, exact costs and every integer pruning bound.
"""
from pathlib import Path
from fractions import Fraction
from collections import Counter
from bisect import bisect_left
import sys,json,pickle,gzip,hashlib,math,time,argparse
H=Path(__file__).parent;I=H/'iterations/I005_exact_cdf_bound';sys.path.insert(0,str(I/'vendor313'))
from flint import fmpz_poly
ap=argparse.ArgumentParser();ap.add_argument('--result',required=True);ap.add_argument('--registry',required=True);a=ap.parse_args();start=time.monotonic();path=I/a.result;d=json.load(open(path));reg=json.load(open(I/a.registry));meta=json.load(open(str(path)+'.run.json'))
source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (I/'candidate').glob('*.py')}
if source!=meta['source_sha256'] or source!=reg['source_sha256']:raise RuntimeError('Proof source differs from registered execution')
if Fraction(d['capacity'])!=Fraction(str(reg['capacity'])) or Fraction(d['cost_limit'])!=Fraction(reg['cost_limit']):raise RuntimeError('Proof target changed')
bench=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/d['instance'];raw=json.load(open(H/'RAW_REFERENCE.json'))
for name,sha in meta['input_sha256'].items():
 if hashlib.sha256((bench/name).read_bytes()).hexdigest()!=sha or raw[str(bench/name)]!=sha:raise RuntimeError('Original input changed')
if any(p.endswith('_dist.txt') or '/lss_cache/' in p for p in meta['opened_task_paths']):raise RuntimeError('Proof searched true distribution')
groups=pickle.load(open(bench/'node_to_factor.pkl','rb'));groups=[list(map(int,groups[k])) for k in sorted(groups,key=int)] if isinstance(groups,dict) else [list(map(int,g)) for g in groups]
if groups!=d['groups'] or d['group_order']!=list(range(len(groups))):raise RuntimeError('Wrong partition order')
cost=[Fraction(s) for s in (bench/'cost.txt').read_text().split()];samples={j:sorted(Fraction(s) for s in (bench/f'{j}_sample.txt').read_text().split()) for g in groups for j in g};B=d['bins'];T=Fraction(d['capacity']);C=Fraction(d['cost_limit']);m=len(groups)
all_den=[];items={};env=[]
for group in groups:
 D=math.lcm(*(len(samples[j]) for j in group));all_den.append(D);cdfs=[]
 for j in group:
  # floor(B*x/T)<=k iff x<(k+1)*T/B; independent sorted-threshold construction.
  cdf=[bisect_left(samples[j],Fraction(k+1)*T/B)*(D//len(samples[j])) for k in range(B+1)];cdfs.append(cdf);items[j]=[cdf[0]]+[cdf[k]-cdf[k-1] for k in range(1,B+1)]
 upper=[max(cdf[k] for cdf in cdfs) for k in range(B+1)];env.append([upper[0]]+[upper[k]-upper[k-1] for k in range(1,B+1)])
den=math.prod(all_den)
if den!=int(d['denominator']):raise RuntimeError('Wrong common denominator')
def product_count(histograms,limit):
 shifted=[];offset=0
 for h in histograms:
  nonzero=[k for k,v in enumerate(h) if v]
  if not nonzero:return 0
  first=nonzero[0];offset+=first;shifted.append(fmpz_poly(h[first:]))
 cut=limit-offset+1
 if cut<=0:return 0
 while len(shifted)>1:
  shifted=[(shifted[k]*shifted[k+1]).truncate(cut) if k+1<len(shifted) else shifted[k] for k in range(0,len(shifted),2)]
 return int(shifted[0].truncate(cut)(1))
def strict_recount(selection,bins,up):
 hist=[];offset=0;den=1
 for j in selection:
  q=[]
  for x in samples[j]:
   y=x*bins/T;q.append((y.numerator+y.denominator-1)//y.denominator if up else y.numerator//y.denominator)
  first=min(q);offset+=first;den*=len(q);counts=Counter(v-first for v in q);h=[0]*(min(bins,max(counts))+1)
  for k,v in counts.items():
   if k<len(h):h[k]=v
  hist.append(h)
 limit=bins-offset-1
 return (product_count(hist,limit) if limit>=0 else 0),den
trie={};trie_nodes=1;covered=0;counts=dict(cost=0,cdf=0,raw_refuted=0,raw_accepted=0,unresolved=0);replayed=0
def add(prefix):
 global trie_nodes
 if len(prefix)>m or any(j not in groups[g] for g,j in enumerate(prefix)):raise RuntimeError('Invalid prefix item')
 node=trie
 for j in prefix:
  if '_end' in node:raise RuntimeError('Overlapping prefix ancestor')
  if j not in node:node[j]={};trie_nodes+=1
  node=node[j]
 if node:raise RuntimeError('Duplicate prefix or overlapping descendant')
 node['_end']=True
def verify_leaf(prefix,certificate,accepted):
 n,dd=strict_recount(prefix,certificate['bins'],accepted)
 key='lower_numerator' if accepted else 'upper_numerator'
 if n!=int(certificate[key]) or dd!=int(certificate['denominator']):raise RuntimeError('Leaf integer count mismatch')
 if accepted and 100*n<99*dd:raise RuntimeError('False raw acceptance')
 if not accepted and 100*n>=99*dd:raise RuntimeError('False raw rejection')
with gzip.open(path.with_name(d['proof_log']),'rt') as f:
 for line in f:
  r=json.loads(line);prefix=r['prefix'];add(prefix);kind=r['kind'];counts[kind]+=1;cover=math.prod(len(g) for g in groups[len(prefix):])
  if r['cover']!=cover:raise RuntimeError('Wrong subtree cardinality')
  covered+=cover
  if kind=='cost':
   least=sum((cost[j] for j in prefix),Fraction(0))+sum((min(cost[j] for j in g) for g in groups[len(prefix):]),Fraction(0))
   if least<=C or least!=Fraction(r['minimum_completion_cost']):raise RuntimeError('False exact cost exclusion')
  elif kind=='cdf':
   h=[items[prefix[g]] if g<len(prefix) else env[g] for g in range(m)];num=product_count(h,B)
   if num!=int(r['upper_numerator']) or den!=int(r['denominator']) or 100*num>=99*den:raise RuntimeError('False CDF subtree exclusion')
   replayed+=1
  elif kind=='raw_refuted':verify_leaf(prefix,r['certificate'],False);replayed+=1
  elif kind=='raw_accepted':
   if len(prefix)!=m or sum(cost[j] for j in prefix)>C:raise RuntimeError('Candidate outside cost line')
   verify_leaf(prefix,r['candidate']['certificate'],True);replayed+=1
  elif kind!='unresolved':raise RuntimeError('Unknown proof event')
remaining=0
for q in d['pending_frontier']:
 prefix=q['prefix'];add(prefix)
 if sum((cost[j] for j in prefix),Fraction(0))!=Fraction(q['cost']):raise RuntimeError('Wrong pending prefix cost')
 remaining+=math.prod(len(g) for g in groups[len(prefix):])
total=math.prod(map(len,groups));visited=trie_nodes-len(d['pending_frontier'])
if covered+remaining!=total or covered!=int(d['covered_combinations']) or remaining!=int(d['remaining_combinations']) or counts!=d['terminal_counts'] or visited!=d['visited_nodes']:raise RuntimeError('Incomplete or overlapping proof coverage')
excluded=d['status']=='exhausted' and remaining==0 and counts['raw_accepted']==0 and counts['unresolved']==0
if excluded!=d['raw_cost_line_excluded']:raise RuntimeError('False global exclusion flag')
result=dict(passed=True,instance=d['instance'],capacity=d['capacity'],cost_limit=d['cost_limit'],total_combinations=str(total),independent_integer_certificates_recomputed=replayed,verified_visited_nodes=visited,covered_combinations=str(covered),pending_combinations=str(remaining),raw_cost_line_excluded=excluded,scope='raw empirical predicate at declared exact-decimal cost line only; any joint raw/LSS feasible choice must also satisfy raw, no positive LSS-feasibility claim',method='different sorted-threshold CDF construction, shifted balanced integer convolution, exact decimal costs and prefix-free complete-space partition',result_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),proof_sha256=hashlib.sha256(path.with_name(d['proof_log']).read_bytes()).hexdigest(),seconds=time.monotonic()-start)
with Path(str(path)+'.audit.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
