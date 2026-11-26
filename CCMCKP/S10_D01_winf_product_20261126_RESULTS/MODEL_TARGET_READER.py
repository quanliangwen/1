"""Independent terminal record reader: no solver, sampler or C++ module import."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,hashlib,pickle,csv,statistics,math
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');assert Path.cwd()==B
H=B/'work/d01_winf_product_20261126/formal'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=read(H/'PROTOCOL.json');end=read(H/'COMPLETED.json');assert end['phase']=='completed' and end['terminal']==P['total_runs'] and end['pending']==0
errors=[]
if sha(H/'PROTOCOL.json')!=read(H/'LAUNCH.json')['protocol_sha256']:errors.append('protocol_changed')
for n,h in P['source_and_binary_pins'].items():
 if sha(H/n)!=h:errors.append('source:'+n)
for n,h in P['input_pins'].items():
 if sha(B/n)!=h:errors.append('input:'+n)
outcomes=[read(p) for p in (H/'outcomes').glob('*.json')]
expected={(a['name'],c['index'],r) for a in P['arms'] for c in P['cases'] for r in range(1,P['repetitions']+1)}
if len(outcomes)!=len(expected) or {(x['arm'],x['case_index'],x['rep']) for x in outcomes}!=expected:errors.append('coverage_duplicates')
flow={a['name']:a['flow'] for a in P['arms']};data={};verified_files=0;bound_checks=0
for c in P['cases']:
 path=B/'benchmark'/c['instance'];groups=pickle.loads((path/'node_to_factor.pkl').read_bytes())
 if isinstance(groups,dict):groups=[groups[k] for k in sorted(groups)]
 costs=[float(x) for line in (path/'cost.txt').read_text().splitlines() for x in line.split('#')[0].split()]
 data[c['index']]={'path':path,'groups':groups,'costs':costs,'ordered':{},'cache':{}}
 # Conservative scale/operation allowance for the widened cost domains used
 # by BlockBounds. This is an arithmetic verification, not a new performance gate.
 eps=Fraction(1,2**53);gamma=256*eps/(1-256*eps)
 bound=float(gamma*64*(1+sum(max(abs(Fraction.from_float(costs[j])) for j in group) for group in groups)))
 assert bound<1e-8,'Cost safety-margin premise not verified'
 data[c['index']]['cost_arithmetic_error_bound']=bound
def valid_selection(d,s):return len(s)==len(d['groups']) and all(j in g for j,g in zip(s,d['groups']))
def exact_rows(d,j):
 if j not in d['ordered']:
  text=(d['path']/(str(j)+'_sample.txt')).read_text();d['ordered'][j]=sorted(Fraction(x) for line in text.splitlines() for x in line.split('#')[0].split())
 return d['ordered'][j]

def prepare_radius(d):
 if 'radius_units' in d:return
 units=[];variances=[];scale=10**12
 for j in range(len(d['costs'])):
  values=exact_rows(d,j);n=len(values);assert n==500
  mean=sum(values,Fraction(0))/n;v=sum((x*x for x in values),Fraction(0))/n-mean*mean
  square=v*scale*scale/(10000*n);ceiling=-((-square.numerator)//square.denominator)
  u=math.isqrt(ceiling)
  if u*u<ceiling:u+=1
  assert Fraction(u*u)>=square and (u==0 or Fraction((u-1)**2)<square)
  units.append(u);variances.append(v)
 d['radius_units']=units;d['exact_variances']=variances
def grid_row(d,j,bins,cap,positive=False,up=False):
 key=(bins,str(cap),j,positive,up);cache=d.setdefault('model_grid_cache',{})
 if key not in cache:
  shift=Fraction(d['radius_units'][j],10**12) if positive else Fraction(0)
  row=[]
  for value in exact_rows(d,j):
   scaled=(value+shift)*bins/cap
   k=-((-scaled.numerator)//scaled.denominator) if up else scaled.numerator//scaled.denominator
   assert k>=0
   row.append(min(bins,k))
  cache[key]=row
 return cache[key]
"""Independent Python coefficient construction; system GMP is arithmetic only."""
import ctypes,ctypes.util
from collections import Counter
class _MPZ(ctypes.Structure):
 _fields_=[('alloc',ctypes.c_int),('size',ctypes.c_int),('limbs',ctypes.POINTER(ctypes.c_ulong))]
_lib=ctypes.CDLL(ctypes.util.find_library('gmp'))
_ptr=ctypes.POINTER(_MPZ);_g={}
for _name,_args in [('init',[_ptr]),('clear',[_ptr]),('set_str',[_ptr,ctypes.c_char_p,ctypes.c_int]),('setbit',[_ptr,ctypes.c_ulong]),('mul',[_ptr,_ptr,_ptr]),('fdiv_r_2exp',[_ptr,_ptr,ctypes.c_ulong]),('fdiv_r',[_ptr,_ptr,_ptr]),('sub_ui',[_ptr,_ptr,ctypes.c_ulong]),('get_str',[ctypes.c_void_p,ctypes.c_int,_ptr])]:
 _fn=getattr(_lib,'__gmpz_'+_name);_fn.argtypes=_args;_fn.restype=ctypes.c_int if _name=='set_str' else None;_g[_name]=_fn
class _Z:
 def __init__(self,n=0):
  self.value=_MPZ();_g['init'](ctypes.byref(self.value));assert _g['set_str'](ctypes.byref(self.value),str(n).encode(),10)==0
 def __del__(self):_g['clear'](ctypes.byref(self.value))
 def bit(self,k):_g['setbit'](ctypes.byref(self.value),k)
 def ref(self):return ctypes.byref(self.value)
def integer_polynomial_count(rows,bins):
 den=500**len(rows);mins=[min(row) for row in rows];cut=bins-sum(mins)
 if cut<=0:return 0,den
 if sum(max(row) for row in rows)<bins:return den,den
 stride=den.bit_length()+1;polynomials=[]
 for row,lo in zip(rows,mins):
  p=_Z()
  for k,n in Counter(x-lo for x in row if x-lo<cut).items():
   for b in range(n.bit_length()):
    if n>>b&1:p.bit(k*stride+b)
  polynomials.append(p)
 while len(polynomials)>1:
  nxt=[]
  for k in range(0,len(polynomials),2):
   if k+1==len(polynomials):nxt.append(polynomials[k]);continue
   p=_Z();_g['mul'](p.ref(),polynomials[k].ref(),polynomials[k+1].ref());_g['fdiv_r_2exp'](p.ref(),p.ref(),cut*stride);nxt.append(p)
  polynomials=nxt
 modulus=_Z();modulus.bit(stride);_g['sub_ui'](modulus.ref(),modulus.ref(),1);p=_Z();_g['fdiv_r'](p.ref(),polynomials[0].ref(),modulus.ref())
 buffer=ctypes.create_string_buffer(len(str(den))+2);_g['get_str'](buffer,10,p.ref());numerator=int(buffer.value);assert 0<=numerator<=den
 return numerator,den


def selected_model_count(d,s,bins,capacity):
 key=(tuple(s),bins,str(capacity));cache=d.setdefault('selected_DRO_count_cache',{})
 if key not in cache:cache[key]=integer_polynomial_count([grid_row(d,j,bins,Fraction(str(capacity)),True,True) for j in s],bins)
 return cache[key]

def proof_count(d,record,capacity,positive=False):
 anchor=record['anchor'];block=record['block'];costcap=record['cost_cap'];key=(positive,tuple(anchor),tuple(block),costcap)
 if key in d['cache']:return d['cache'][key]
 # Independent exact rational relaxation uses a wider cost safety margin than
 # double summation error for these pinned cases; no exact equality excluded.
 outside=math.fsum(d['costs'][anchor[g]] for g in range(len(anchor)) if g not in block)
 minima=[min(d['costs'][j] for j in d['groups'][g]) for g in block];slack=costcap-outside-math.fsum(minima)
 bins=record['bins'];cap=Fraction(str(capacity))
 def grid(j):return grid_row(d,j,bins,cap,positive,False)
 rows=[grid(j) for j in anchor]
 for h,g in enumerate(block):
  eligible=[j for j in d['groups'][g] if d['costs'][j]-minima[h]<=slack+1e-7]
  assert eligible,'empty_relaxation';rows[g]=[min(grid(j)[k] for j in eligible) for k in range(500)]
 # Monotone floor quantization commutes with coordinatewise quantile minima.
 indices=rows
 den=500**len(anchor);mins=[min(row) for row in indices];cut=bins-sum(mins)
 if cut<=0:result=(0,den)
 else:
  stride=den.bit_length()+1;base=1<<stride;mask=(1<<(cut*stride))-1
  polynomials=[]
  for row,lo in zip(indices,mins):
   hist=Counter(k-lo for k in row if k-lo<cut);polynomials.append(sum(n<<(k*stride) for k,n in hist.items()))
  while len(polynomials)>1:polynomials=[(polynomials[k]*polynomials[k+1])&mask if k+1<len(polynomials) else polynomials[k] for k in range(0,len(polynomials),2)]
  result=(polynomials[0]%(base-1),den)
 d['cache'][key]=result;return result
def validate_model_metadata(d,raw):
 prepare_radius(d);model=raw['DRO_model']
 assert raw['certificate_scope']=='exact_worst_case_shifted_product_probability'
 assert model['transport_order']=='infinity' and model['transport_radius']==1 and model['kappa']=='1/100'
 assert model['center']=='full_independent_empirical_product_all_original_samples' and model['not_500_pseudo_joint_scenarios']
 assert model['original_sample_count_per_item']==500 and model['item_count']==len(d['costs']) and model['group_count']==len(d['groups'])
 assert not model['statistical_population_coverage_claim'] and not model['nominal_fallback_in_DRO_pool']
 assert len(model['radii'])==len(d['costs']) and raw['search_certificate_calls']>0
 for j,item in enumerate(model['radii']):
  assert item['item']==j and int(item['units_1e12'])==d['radius_units'][j],'independent_radius'
  assert Fraction(item['exact_variance'])==d['exact_variances'][j],'exact_variance'
  assert Fraction(item['radius_rational'])==Fraction(d['radius_units'][j],10**12),'radius_rational'
 selected=raw['selected']['selection'];shift=sum((Fraction(d['radius_units'][j],10**12) for j in selected),Fraction(0))
 assert shift>0 and shift==Fraction(raw['selected_transport_shift_rational']),'nonzero_selected_adversarial_shift'

assert not (H/'MODEL_TARGET_DIAGNOSTIC.json').exists()
rows=[]
for c in P['cases']:
 d=data[c['index']];prepare_radius(d)
 raw=read(H/'runs'/('A_B01_ORIGINAL_i%02d_r01'%c['index'])/'S10_search.json');selection=raw['selected']['selection'];bins=1048576
 lower,den=integer_polynomial_count([grid_row(d,j,bins,Fraction(str(c['tmax'])),True,True) for j in selection],bins)
 upper,de=integer_polynomial_count([grid_row(d,j,bins,Fraction(str(c['tmax'])),True,False) for j in selection],bins)
 assert de==den and lower<=upper
 status='DRO_feasible' if lower*100>=99*den else 'DRO_infeasible' if upper*100<99*den else 'unknown'
 rows.append({'case_index':c['index'],'nominal_target_selection':selection,'nominal_target_model_cost':raw['selected']['cost'],'bins':bins,'positive_DRO_lower_numerator':str(lower),'positive_DRO_upper_numerator':str(upper),'denominator':str(den),'lower_diagnostic':lower/den,'upper_diagnostic':upper/den,'status':status})
result={'scope':'deterministic post-run diagnostic of previous nominal model best under positive DRO; not an LSS evaluation or acceptance gate','no_solver_or_probability_sampling':True,'reader_sha256':sha(Path(__file__)),'rows':rows}
(H/'MODEL_TARGET_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
