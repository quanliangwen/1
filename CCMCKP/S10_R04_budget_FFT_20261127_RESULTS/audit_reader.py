"""Independent terminal record reader: no solver, sampler or C++ module import."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,hashlib,pickle,csv,statistics,math
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');assert Path.cwd()==B
H=B/'work/r04_budget_fft_polish_20261127/formal'
import os
REPS=int(os.environ.get('R04_AUDIT_REPS','30'));PILOT=REPS==5
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=read(H/'PROTOCOL.json')
if not PILOT:
 end=read(H/'COMPLETED.json');assert end['phase']=='completed' and end['terminal']==P['total_runs'] and end['pending']==0
errors=[]
if sha(H/'PROTOCOL.json')!=read(H/'LAUNCH.json')['protocol_sha256']:errors.append('protocol_changed')
for n,h in P['source_and_binary_pins'].items():
 if sha(H/n)!=h:errors.append('source:'+n)
for n,h in P['input_pins'].items():
 if sha(B/n)!=h:errors.append('input:'+n)
outcomes=[read(p) for p in (H/'outcomes').glob('*.json') if read(p)['rep']<=REPS]
expected={(a['name'],c['index'],r) for a in P['arms'] for c in P['cases'] for r in range(1,REPS+1)}
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


def selected_model_count(d,s,bins,capacity,positive=True):
 key=(tuple(s),bins,str(capacity),positive);cache=d.setdefault('selected_DRO_count_cache',{})
 if key not in cache:cache[key]=integer_polynomial_count([grid_row(d,j,bins,Fraction(str(capacity)),positive,True) for j in s],bins)
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

def check_transport_proofs(d,raw,flow_name):
 stats=raw['DRO_transport_statistics'];cuts=raw['DRO_transport_prunes']
 if flow_name!='block_winf_transport':
  assert stats is None and cuts==[],'transport_disabled_control'
  return 0
 assert stats['enabled'] and stats['model_unchanged_from_D01'] and stats['current_run_native_witnesses_only']
 assert stats['max_witnesses']==128 and stats['maximum_bank_size']<=128 and not stats['feasible_certificate_reuse'] and not stats['probability_sampling']
 assert stats['excluded']==len(cuts) and stats['queries']>=len(cuts)
 native={tuple(c['selection']):c for c in raw['native_infeasible_proofs']};cache=d.setdefault('transport_pair_floor_cache',{})
 targets=set()
 for cut in cuts:
  target=cut['target_selection'];witness=cut['witness_selection'];assert valid_selection(d,target) and valid_selection(d,witness),'transport_identity'
  assert tuple(target) not in targets,'duplicate_transport_target';targets.add(tuple(target))
  c=native[tuple(witness)];den=int(c['denominator']);upper=int(c['upper_numerator'])
  assert upper*100<99*den and den==500**len(d['groups']),'native_witness_upper'
  assert str(upper)==cut['witness_upper_numerator'] and str(den)==cut['denominator'] and c['bins']==cut['witness_bins'],'witness_provenance'
  assert cut['witness_source']=='current_run_native_integer_infeasible_certificate' and cut['not_a_probability_estimate'] and cut['strict_event']=='sum<T'
  assert cut['lower_units_denominator']=='1000000000000'
  changed={g:(x,y) for g,(x,y) in enumerate(zip(target,witness)) if x!=y};pairs=cut['changed_pairs']
  assert len(pairs)==len(changed) and {p['group'] for p in pairs}==set(changed),'transport_changed_groups'
  total=0
  for pair in pairs:
   x,y=changed[pair['group']];assert pair['target_item']==x and pair['witness_item']==y
   key=(x,y)
   if key not in cache:
    shift=Fraction(d['radius_units'][x]-d['radius_units'][y],10**12)
    gap=min(a-b for a,b in zip(exact_rows(d,x),exact_rows(d,y)))+shift
    scaled=gap*10**12;cache[key]=scaled.numerator//scaled.denominator
   assert int(pair['floor_lower_units'])==cache[key],'independent_quantile_floor'
   total+=cache[key]
  assert total==int(cut['sum_floor_lower_units']) and total>=0,'transport_monotonicity'
 return len(cuts)

"""Independent exact Fraction audit; no optimization model or sampler imports."""
from fractions import Fraction as F
_prepared={}

def verify_adaptive(raw,groups,costs,samples,capacity):
 model=raw['adaptive_RO_model'];proofs=raw['adaptive_RO_proposals'];queries=raw['adaptive_RO_queries'];cuts=raw['adaptive_RO_cost_cuts'];stats=raw['adaptive_RO_statistics']
 if raw['search_flow']!='cvar_budget_calibrated':
  assert model is None and stats is None and proofs==[] and queries==[] and cuts==[]
  return {'proofs':0,'qualified':0,'rejected':0,'subproblems':0,'exact_cost_cuts':0}
 assert model['model']=='R02_empirical_ES95_calibrated_budget_RO'
 assert not model['CDF_solution_probability_monotonicity_claim'] and not model['probability_coverage_claim'] and not model['global_optimality_claim']
 assert model['localization_is_heuristic'] and model['original_CDF_gate_preserved']
 assert model['final_acceptance']=='unchanged original LSS' and not model['historical_solution_inputs'] and not model['external_MIPstarts']
 n=len(costs);m=len(groups);cap=F(str(capacity));margin=F(1,10**8)
 key=(id(groups),str(capacity));cache=_prepared.get(key)
 if cache is None:
  mean=[];es=[];delta=[]
  for row in samples:
   a=sorted((F(v) for v in row),reverse=True);mu=sum(a,F())/len(a);mass=F(len(a),20);whole=mass.numerator//mass.denominator
   total=sum(a[:whole],F())+(mass-whole)*a[whole] if whole<len(a) else sum(a,F())
   e=total/mass;mean.append(mu);es.append(e);delta.append(e-mu)
  thresholds=sorted(set(delta)|{F()});mins=[];choices=[]
  for t in thresholds:
   sel=[min(g,key=lambda j:(mean[j]+max(F(),delta[j]-t),j)) for g in groups]
   choices.append(sel);mins.append(sum((mean[j]+max(F(),delta[j]-t) for j in sel),F()))
  nominal=sum((min(mean[j] for j in g) for g in groups),F());gmax=F()
  if nominal<=cap-margin:
   for t,v in zip(thresholds,mins):
    if t:gmax=max(gmax,(cap-margin-v)/t)
    elif v<=cap-margin:gmax=F(m)
   gmax=min(gmax,F(m))
  cache={'mean':mean,'es':es,'delta':delta,'thresholds':thresholds,'mins':mins,'choices':choices,'nominal':nominal,'gmax':gmax,'dual':{}}
  _prepared[key]=cache
 mean,es,delta,thresholds,mins,choices,gmax=[cache[k] for k in ['mean','es','delta','thresholds','mins','choices','gmax']]
 assert F(model['gamma_max_exact'])==gmax and model['mean_infeasible']==(cache['nominal']>cap-margin)
 assert F(model['positive_gamma_floor'])==(gmax/2 if 0<gmax<F(1,20) else F(1,20))
 assert len(model['items'])==n and model['threshold_count']==len(thresholds)
 for j,r in enumerate(model['items']):
  assert r['item']==j and F(r['mean'])==mean[j] and F(r['ES95'])==es[j] and F(r['deviation'])==delta[j]
  assert F(r['tail_mass'])==F(len(samples[j]),20)
 for k,r in enumerate(model['resource_table']):assert F(r['theta'])==thresholds[k] and F(r['group_min_sum'])==mins[k]
 assert len(model['resource_table'])==len(thresholds)
 def selection(s):assert len(s)==m and all(j in g for j,g in zip(s,groups))
 def cost(s):return sum((F.from_float(costs[j]) for j in s),F())
 qualified={};rejected=0
 for p in proofs:
  s=p['selection'];selection(s);gamma,t=F(p['gamma']),F(p['theta']);assert 0<gamma<=gmax and t in thresholds
  ds=sorted((delta[j] for j in s),reverse=True);left=gamma;protection=F()
  for v in ds:take=min(F(1),max(F(),left));protection+=take*v;left-=take
  mu=sum((mean[j] for j in s),F());worst=mu+protection;fixed=mu+gamma*t+sum((max(F(),delta[j]-t) for j in s),F())
  assert F(p['nominal_sum'])==mu and F(p['budget_worst_sum'])==worst and F(p['fixed_theta_sum'])==fixed and fixed>=worst
  assert F(p['robust_slack'])==cap-margin-worst and p['robust_feasible']==(worst<=cap-margin) and p['fixed_theta_feasible']==(fixed<=cap-margin)
  assert p['own_run_raw_samples'] and p['not_a_probability_estimate'] and p['source'].startswith('R02_')
  if p['source']=='R02_self_generated_gamma_max_anchor':
   k=min(range(len(thresholds)),key=lambda k:gmax*thresholds[k]+mins[k]);assert s==choices[k] and gamma==gmax and t==thresholds[k]
  if p['robust_feasible'] and p['fixed_theta_feasible']:
   assert tuple(s) not in qualified;qualified[tuple(s)]=p
  else:rejected+=1;assert not p['native_evaluation_completed']
 for q in raw['candidate_shortlist']:
  p=qualified[tuple(q['selection'])];assert p['native_state']=='accepted' and p['native_evaluation_completed'] and q['source'].startswith('R02_')
 certs={tuple(q['selection']):q for q in raw['candidate_shortlist']+raw['adaptive_RO_incumbents']}
 for cut in cuts:
  gamma,t,lam,lb=[F(cut[k]) for k in ['gamma','theta','lambda','dual_lower']];s=cut['incumbent_selection'];selection(s)
  assert 0<gamma<=gmax and t in thresholds and lam>=0
  ck=(t,lam)
  if ck not in cache['dual']:
   cache['dual'][ck]=sum((min(F.from_float(costs[j])+lam*(mean[j]+max(F(),delta[j]-t)) for j in g) for g in groups),F())
  assert lb==cache['dual'][ck]-lam*(cap-margin-gamma*t)
  assert lb>=cost(s)==F(cut['incumbent_exact_cost'])
  assert cut['current_run_integer_CDF_incumbent'] and cut['strict_cheaper_exact_solution_preserved']
  cert=certs[tuple(s)]['certificate'];assert int(cert['lower_numerator'])*100>=99*int(cert['denominator'])
  assert tuple(s) in qualified and qualified[tuple(s)]['native_state']=='accepted'
 tasks=0
 for query in queries:
  gamma=F(query['gamma']);assert 0<gamma<=gmax and not query['CDF_monotonicity_claim']
  for task in query['solver_tasks']:
   tasks+=1;assert F(task['theta']) in thresholds and task['whole_subproblem_seconds']>=0
   if not task.get('model_setup_exhausted_slice'):
    assert task['external_MIPstarts']==False and task['PoolSolutions']==(25 if query['stage']=='fine' else 1)
    assert task['PoolSearchMode']==(2 if query['stage']=='fine' else 0)
   for index in task['excluded_proposal_indices']:
    assert query['stage']=='fine' and proofs[index]['native_state'] in ['accepted','infeasible']
   if task['current_run_cost_cap']:
    r=task['current_run_cost_cap'];assert cost(r['selection'])==F(r['cost']) and tuple(r['selection']) in qualified
  for i in query['candidate_refs']:assert proofs[i]['robust_feasible'] and proofs[i]['fixed_theta_feasible']
 assert stats['mip_subproblems_solved']==tasks and stats['mip_pruned_by_safe_lb']==len(cuts)
 assert stats['rational_verified_unique']==len(qualified) and stats['no_LSS_calls_in_generator']
 return {'proofs':len(proofs),'qualified':len(qualified),'rejected':rejected,'subproblems':tasks,'exact_cost_cuts':len(cuts)}

"""Independent integer/Fraction enclosures; no C++ writer, solver or sampler import."""
from fractions import Fraction as F
class IntervalMath:
 def __init__(self,bits=208,exp_terms=50,log_terms=90):
  self.q=1<<bits;self.ne=exp_terms;self.nl=log_terms;self.ln2=self.log_unit(F(2))
 @staticmethod
 def ceil(a,b):return -((-a)//b)
 def exp_negative(self,y):
  assert y>=0
  if y==0:return self.q,self.q
  k=0
  while y>F(1,2):y/=2;k+=1
  a,b=y.numerator,y.denominator;tl=th=lo=hi=self.q
  for n in range(1,self.ne+1):
   tl=tl*a//(b*n);th=self.ceil(th*a,b*n);lo+=tl;hi+=th
  tail=F(th)*y/(self.ne+1)/(1-y/(self.ne+2));hi+=self.ceil(tail.numerator,tail.denominator)
  for _ in range(k):lo=lo*lo//self.q;hi=self.ceil(hi*hi,self.q)
  return self.q*self.q//hi,self.ceil(self.q*self.q,lo)
 def log_unit(self,x):
  assert 1<=x<=2
  z=(x-1)/(x+1);z2=z*z;pl=self.q*z.numerator//z.denominator;ph=self.ceil(self.q*z.numerator,z.denominator);sl=sh=0
  for n in range(self.nl):
   sl+=pl//(2*n+1);sh+=self.ceil(ph,2*n+1);pl=pl*z2.numerator//z2.denominator;ph=self.ceil(ph*z2.numerator,z2.denominator)
  rem=F(2*ph,2*self.nl+1)/(1-z2)
  return 2*sl,2*sh+self.ceil(rem.numerator,rem.denominator)
 def log(self,x):
  assert x>0
  k=0
  while x<1:x*=2;k-=1
  while x>=2:x/=2;k+=1
  lo,hi=self.log_unit(x);a,b=self.ln2
  return (lo+k*a,hi+k*b) if k>=0 else (lo+k*b,hi+k*a)
 def weight(self,values,t):
  top=max(values)
  if min(values)==top:return top,top
  low=high=0
  for a in values:
   l,h=self.exp_negative(t*(top-a));low+=l;high+=h
  low//=len(values);high=self.ceil(high,len(values));assert low>0
  a,_=self.log(F(low,self.q));_,b=self.log(F(high,self.q))
  return top+F(a,self.q)/t,top+F(b,self.q)/t

_cache={}
_ref=IntervalMath()
def verify_entropy(raw,groups,costs,samples,capacity):
 model=raw['entropic_model'];proofs=raw['entropic_proposals'];queries=raw['entropic_queries'];cuts=raw['entropic_cost_cuts'];stats=raw['entropic_statistics']
 if raw['search_flow']!='entropy_cdf_calibrated':
  assert model is None and stats is None and proofs==[] and queries==[] and cuts==[]
  return {'proofs':0,'qualified':0,'rejected':0,'subproblems':0,'exact_cost_cuts':0,'coefficient_items':0}
 assert model['model']=='R03b_empirical_entropic_risk_CDF_proxy'
 assert model['center']=='full_independent_empirical_product_all_original_samples' and model['all_original_samples']
 assert not model['fixed_radius_KL_ball_claim'] and not model['population_probability_coverage_claim'] and not model['global_optimality_claim']
 assert model['precision_bits']==192 and model['exp_terms']==40 and model['log_terms']==70
 assert model['CDF_localization_is_heuristic'] and not model['CDF_solution_probability_monotonicity_claim']
 assert not model['historical_solution_inputs'] and not model['external_MIPstarts'] and model['final_acceptance']=='unchanged original LSS'
 cap=F(str(capacity));guard=cap-F(1,10**8);floor=F(4,5);eta_cap=F(model['eta_cap_upper_log100'])
 ln100=_ref.log(F(100));assert F(ln100[1],_ref.q)<=eta_cap and eta_cap-F(ln100[0],_ref.q)<F(1,10**40)
 assert F(model['eta_floor'])==floor and F(model['robust_guard'])==F(1,10**8)
 tilts=[F(1,10),F(4,25),F(1,4),F(2,5),F(3,5),F(17,20)];tabs={};n=len(costs);m=len(groups)
 cache=_cache.setdefault((id(groups),str(capacity)),{'coefficients':{},'dual':{}})
 for k,tab in enumerate(model['tables']):
  assert tab['index']==k and F(tab['t'])==tilts[k] and len(tab['items'])==n
  if k not in cache['coefficients']:
   values=[]
   for j,row in enumerate(samples):
    assert len(row)==model['samples_per_item'];values.append(_ref.weight([F(x) for x in row],tilts[k]))
   cache['coefficients'][k]=values
  lo=[];hi=[]
  for j,w in enumerate(tab['items']):
   l,h=F(w['lower']),F(w['upper']);rl,rh=cache['coefficients'][k][j]
   assert w['item']==j and l<=rl<=rh<=h and h-l<F(1,10**40),'independent_entropic_coefficient'
   lo.append(l);hi.append(h)
  own=[min(g,key=lambda j:(hi[j],j)) for g in groups];minimum=sum((hi[j] for j in own),F());maximum=min(tilts[k]*(guard-minimum),eta_cap)
  assert own==tab['initial_selection'] and minimum==F(tab['minimum_upper_weight_sum']) and maximum==F(tab['eta_max'])
  assert tab['resource_feasible_at_eta_floor']==(maximum>=floor)
  tabs[k]=(lo,hi,maximum)
 def selection(s):assert len(s)==m and all(j in g for j,g in zip(s,groups))
 def cost(s):return sum((F.from_float(costs[j]) for j in s),F())
 qualified={}
 for p in proofs:
  s=p['selection'];selection(s);k=p['table_index'];eta=F(p['eta']);t=tilts[k];lo,hi,maximum=tabs[k]
  assert F(p['t'])==t and floor<=eta<=maximum
  low=sum((lo[j] for j in s),F());high=sum((hi[j] for j in s),F());rhs=guard-eta/t
  assert low==F(p['weight_sum_lower']) and high==F(p['weight_sum_upper']) and rhs==F(p['rhs_exact'])
  assert high<=rhs and p['entropic_upper_feasible'] and p['empirical_0.99_sufficient_eta']==(eta>=eta_cap)
  assert p['own_run_raw_samples'] and p['not_a_probability_estimate'] and p['source'].startswith('R03b_')
  if p['source']=='R03b_self_generated_upper_weight_anchor':assert s==model['tables'][k]['initial_selection'] and eta==maximum
  assert tuple(s) not in qualified;qualified[tuple(s)]=p
 certs={tuple(c['selection']):c for c in raw['candidate_shortlist']+raw['entropic_incumbents']}
 for p in raw['candidate_shortlist']:
  q=qualified[tuple(p['selection'])];assert q['native_state']=='accepted' and q['native_evaluation_completed'] and p['source'].startswith('R03b_')
 for cut in cuts:
  k=cut['table_index'];eta,lam,lb=F(cut['eta']),F(cut['lambda']),F(cut['dual_lower']);hi=tabs[k][1];s=cut['incumbent_selection'];selection(s)
  assert floor<=eta<=tabs[k][2] and lam>=0 and cut['safe_for_implemented_upper_weight_model']
  ck=(k,tuple(hi),lam)
  if ck not in cache['dual']:cache['dual'][ck]=sum((min(F.from_float(costs[j])+lam*hi[j] for j in g) for g in groups),F())
  assert lb==cache['dual'][ck]-lam*(guard-eta/tilts[k]) and lb>=cost(s)==F(cut['incumbent_exact_cost'])
  cert=certs[tuple(s)]['certificate'];assert int(cert['lower_numerator'])*100>=99*int(cert['denominator'])
  assert tuple(s) in qualified and qualified[tuple(s)]['native_state']=='accepted'
 tasks=0;references=0
 for q in queries:
  k=q['table_index'];eta=F(q['eta']);assert F(q['t'])==tilts[k] and floor<=eta<=tabs[k][2] and not q['CDF_monotonicity_claim']
  for i in q['candidate_refs']:
   p=proofs[i];assert sum((tabs[k][1][j] for j in p['selection']),F())<=guard-eta/tilts[k];references+=1
  for task in q['solver_tasks']:
   tasks+=1
   if not task.get('model_setup_exhausted_slice'):
    assert task['external_MIPstarts']==False and task['PoolSolutions']==(25 if q['stage']=='fine' else 1) and task['PoolSearchMode']==(2 if q['stage']=='fine' else 0)
   for i in task['excluded_proposal_indices']:assert q['stage']=='fine' and proofs[i]['native_state'] in ['accepted','infeasible']
 assert stats['mip_subproblems_solved']==tasks and stats['mip_pruned_by_safe_lb']==len(cuts) and stats['rational_verified_unique']==len(qualified) and stats['no_LSS_calls_in_generator']
 return {'proofs':len(proofs),'qualified':len(qualified),'rejected':0,'subproblems':tasks,'exact_cost_cuts':len(cuts),'coefficient_items':n*len(tabs),'query_reference_checks':references}

"""Independent raw-sample reconstruction; no solver or C++ writer imports."""
from fractions import Fraction as F
import math
_private_fft_cache={}

def verify_polish(raw,groups,costs,samples,capacity):
 if raw['search_flow']!='cvar_budget_polish':
  assert raw.get('R04_model') is None and not raw.get('polish_history') and not raw.get('polish_proposals') and not raw.get('polish_MIP_queries')
  return {'polish_proposals':0,'polish_history':0,'polish_mips':0}
 import numpy as np
 from scipy.fft import rfft,irfft
 model=raw['R04_model'];history=raw['polish_history'];proposals=raw['polish_proposals'];tasks=raw['polish_MIP_queries']
 assert model['model']=='R04_budget_RO_guided_empirical_chance_polish' and model['parent']=='R02_empirical_ES95_calibrated_budget_RO'
 assert not model['historical_solution_inputs'] and not model['external_MIPstarts'] and model['generator_LSS_calls']==0
 assert not model['polish_preserves_parent_RO_guarantee'] and not model['FFT_is_probability_certificate']
 assert model['private_score_cache_not_original_guide_cache'] and model['private_bins']==8192 and model['damping']==12
 assert model['repair_buffer']==.0002 and model['borderline_native_gate']==.9895 and model['max_seeds']==6 and model['rounds']==3
 assert model['trust_group_radius']==5 and model['trust_binary_Hamming_radius']==10 and model['trust_PoolSolutions']==10 and model['trust_MIP_seconds']==2
 assert model['parent_absolute_allowance_seconds']<=120 and model['proposal_slice_cap_seconds']==60 and model['max_new_native_checks']==24
 b=8192;key=(id(groups),float(capacity));cache=_private_fft_cache.get(key)
 if cache is None:
  hist=np.zeros((len(costs),b),dtype=np.longdouble)
  for j,row in enumerate(samples):
   values=np.array([float(v) for v in row],dtype=np.longdouble);assert np.isfinite(values).all() and (values>=0).all()
   # Same binary64 input interpretation, independently grouped and transformed.
   ids=np.floor(values*np.longdouble(b)/np.longdouble(float(capacity))+np.longdouble('.5')).astype(np.int64);valid=ids<b
   for k in ids[valid]:hist[j,int(k)]+=np.longdouble(1)/len(row)
  undo=np.exp(np.longdouble(12)*np.arange(b,dtype=np.longdouble)/b)
  freq=rfft(hist/undo,n=2*b,axis=1,workers=1)
  cache={'hist':hist,'freq':freq,'undo':undo,'prob':{},'marginals':{}};_private_fft_cache[key]=cache
 def selection(s):assert len(s)==len(groups) and all(j in g for j,g in zip(s,groups))
 def cost(s):return sum((F.from_float(costs[j]) for j in s),F())
 def probability(s):
  k=tuple(s)
  if k not in cache['prob']:
   product=np.prod(cache['freq'][list(s)],axis=0);pdf=irfft(product,n=2*b,workers=1)[:b]
   cache['prob'][k]=float(np.clip(np.sum(np.maximum(pdf,0)*cache['undo']),0,1))
  return cache['prob'][k]
 def marginals(s):
  k=tuple(s)
  if k not in cache['marginals']:
   p=probability(s);result=np.zeros(len(costs));m=len(s)
   left=np.ones((m+1,b+1),dtype=cache['freq'].dtype);right=left.copy()
   for g,j in enumerate(s):left[g+1]=left[g]*cache['freq'][j]
   for g in range(m-1,-1,-1):right[g]=right[g+1]*cache['freq'][s[g]]
   for g in range(m):
    pdf=irfft(left[g]*right[g+1],n=2*b,workers=1)[:b];cdf=np.cumsum(np.maximum(pdf,0)*cache['undo'])
    for j in groups[g]:result[j]=float(np.clip(np.dot(cache['hist'][j],cdf[::-1]),0,1))
    result[s[g]]=p
   cache['marginals'][k]=(p,result)
  return cache['marginals'][k]
 def near(a,b):assert math.isfinite(float(a)) and abs(float(a)-float(b))<1e-6,'independent_private_FFT_score'
 seeds=model['seeds'];assert len(seeds)<=6 and len({tuple(s['selection']) for s in seeds})==len(seeds)
 reachable=[set() for _ in seeds]
 for si,seed in enumerate(seeds):
  s=seed['selection'];selection(s);proof=raw['adaptive_RO_proposals'][seed['parent_proposal_index']]
  assert s==proof['selection'] and proof['robust_feasible'] and proof['fixed_theta_feasible']
  assert seed['source']=='current_run_R02_model';reachable[si].add(tuple(s))
 for i,row in enumerate(history):
  s=row['selection'];anchor=row['anchor'];selection(s);selection(anchor)
  assert 0<=row['seed_index']<len(seeds) and tuple(anchor) in reachable[row['seed_index']] and not row['FFT_is_certificate']
  distance=sum(a!=b for a,b in zip(s,anchor));assert row['group_distance']==distance
  near(row['cost'],float(cost(s)));near(row['approx_probability'],probability(s));assert 0<=row['elapsed']<=raw['runtime_before_save']+1
  action=row['action'];p,weights=marginals(anchor)
  if action.startswith('one_'):
   assert distance==1
   g=next(g for g in range(len(groups)) if anchor[g]!=s[g]);near(row['approx_probability'],weights[s[g]])
   if action=='one_descent':assert cost(s)<cost(anchor) and weights[s[g]]>=.9902-1e-6
   elif action=='one_borderline':assert cost(s)<cost(anchor) and weights[s[g]]>=.9895-1e-6
   else:assert action=='one_repair' and weights[s[g]]>p-1e-6
  elif action=='two_proposal':assert distance==2 and cost(s)<cost(anchor)
  else:
   assert action=='trust_MCKP';task=tasks[row['extra']['MIP_index']];assert task['anchor']==anchor and i in task['returned']
   assert distance<=task['group_radius']<=5 and cost(s)<cost(anchor)
  reachable[row['seed_index']].add(tuple(s))
 rejected={tuple(p['selection']):p for p in raw['native_infeasible_proofs']}
 for ti,task in enumerate(tasks):
  anchor=task['anchor'];selection(anchor);p,weights=marginals(anchor);near(task['anchor_approx_probability'],p)
  assert task['heuristic_linearization_not_valid_chance_cut'] and task['group_radius']==min(5,len(groups)) and F(task['exact_anchor_cost'])==cost(anchor)
  assert not task['external_MIPstarts'] and task['PoolSolutions']==10 and task['PoolSearchMode']==2
  near(task['risk_rhs'],p-.99+.0002);assert len(task['risk'])==len(costs)
  for j,v in enumerate(task['risk']):near(v,p-weights[j])
  for s in task['excluded_complete_native_rejections']:assert tuple(s) in rejected
  for hi in task['returned']:
   row=history[hi];assert row['action']=='trust_MCKP' and row['extra']['MIP_index']==ti
   assert sum(task['risk'][j] for j in row['selection'])<=task['risk_rhs']+1e-7+1e-12
 parent={tuple(q['selection']):q for q in model.get('parent_pool',[])}
 assert len(parent)==len(model.get('parent_pool',[]))
 for p in parent.values():
  assert p['source'].startswith('R02_') and p['found_seconds']<=model['parent_snapshot_seconds']+1e-6
  cert=p['certificate'];assert int(cert['lower_numerator'])*100>=99*int(cert['denominator'])
 seen={};accepted_novel=0
 for p in proposals:
  s=p['selection'];selection(s);assert tuple(s) not in seen;seen[tuple(s)]=p
  row=history[p['history_index']];assert row['selection']==s and row['seed_index']==p['seed_index'] and p['source']=='R04_'+row['action']
  assert p['own_run_RO_seed'] and p['not_a_budget_RO_certificate'];near(p['approx_probability'],row['approx_probability']);assert p['approx_probability']>=.9895
  if p['native_state'] in ['accepted','infeasible']:
   cert=p['native_certificate'];assert p['native_evaluation_completed'] and cert['selection']==s
   lo,hi,de=[int(cert[k]) for k in ['lower_numerator','upper_numerator','denominator']];assert 0<=lo<=hi<=de and de==len(samples[0])**len(groups)
   if p['native_state']=='accepted':assert lo*100>=99*de;accepted_novel+=tuple(s) not in parent
   else:assert hi*100<99*de and tuple(s) in rejected and cert==rejected[tuple(s)]
 for p in raw['candidate_shortlist']:
  if p['source'].startswith('R02_'):assert tuple(p['selection']) in parent
  else:
   q=seen[tuple(p['selection'])];assert q['native_state']=='accepted' and p['certificate']==q['native_certificate'] and p['source']==q['source']
 stage=raw['stage3_internal_cdf_and_polish'];assert stage['ro_passed_native_cdf_count']==len(parent)
 assert stage['polish_seeds_used']==len(seeds) and stage['post_polish_passed_native_cdf_count']==accepted_novel
 if 'new_native_queries' in model:assert model['new_native_queries']<=24
 assert len(model.get('native_queue',[]))==len(set(model.get('native_queue',[]))) and all(0<=i<len(proposals) for i in model.get('native_queue',[]))
 return {'polish_proposals':len(proposals),'polish_history':len(history),'polish_mips':len(tasks),'polish_accepted_novel':accepted_novel,'private_numeric_tolerance':1e-6}

def verify_models(raw,groups,costs,samples,capacity):
 if raw['search_flow']=='cvar_budget_polish':
  parent=dict(raw);parent['search_flow']='cvar_budget_calibrated'
  parent['candidate_shortlist']=raw['R04_model'].get('parent_pool',[])
  result=verify_adaptive(parent,groups,costs,samples,capacity)
  return dict(result,**verify_polish(raw,groups,costs,samples,capacity))
 a=verify_adaptive(raw,groups,costs,samples,capacity)
 b=verify_entropy(raw,groups,costs,samples,capacity)
 c=verify_polish(raw,groups,costs,samples,capacity)
 return dict(b if raw['search_flow']=='entropy_cdf_calibrated' else a,**c)

def model_statistics(raw):return raw.get('entropic_statistics') or raw.get('adaptive_RO_statistics')

rows=[]
for ordinal,o in enumerate(sorted(outcomes,key=lambda x:(x['case_index'],x['arm'],x['rep']))):
 if ordinal%15==0:print(json.dumps({'audit_progress':ordinal,'total':len(outcomes)}),flush=True)
 r={k:o.get(k) for k in ['identity','case_index','instance','arm','rep','seed','rc','termination_reason','process_wall_seconds','peak_rss_bytes']};r.update(valid=False,errors=[],cost=None)
 root=H/'runs'/o['identity'];d=data[o['case_index']]
 try:
  assert o['seed']==P['seed_base']+o['rep'],'identity_seed'
  for n,h in o['output_files'].items():assert sha(root/n)==h['sha256'] and (root/n).stat().st_size==h['bytes'],n;verified_files+=1
  if o['rc']!=0 or o['termination_reason'] is not None:
   assert 0<o['process_wall_seconds']<=600,'failed_run_clock'
   if (root/'S10_search.json').exists():
    failed_raw=read(root/'S10_search.json')
    if flow[o['arm']] in ['cvar_budget_calibrated','entropy_cdf_calibrated','cvar_budget_polish']:
     bv=verify_models(failed_raw,d['groups'],d['costs'],[exact_rows(d,j) for j in range(len(d['costs']))],o['capacity'])
     recounted=0
     for cert in failed_raw['native_infeasible_proofs']:
      s=cert['selection'];bins=cert['bins'];key=(tuple(s),bins,str(o['capacity']))
      cache=d.setdefault('failed_nominal_upper_count_cache',{})
      if key not in cache:cache[key]=integer_polynomial_count([grid_row(d,j,bins,Fraction(str(o['capacity'])),False,False) for j in s],bins)
      nu,de=cache[key];assert nu==int(cert['upper_numerator']) and de==int(cert['denominator']) and nu*100<99*de,'independent_failed_upper'
      recounted+=1
     reason='no_LSS_accepted_output'
     if failed_raw['raw_certified_pool_count']==0:reason='no_internal_CDF_accepted_model_candidate'
     r.update(budget_proofs_verified=bv,budget_statistics=model_statistics(failed_raw),active_certificate_calls=failed_raw['search_certificate_calls'],active_certificate_seconds=failed_raw['search_certificate_seconds'],raw_pool_count=failed_raw['raw_certified_pool_count'],failure_class=reason,independent_failed_upper_certificates=recounted)
   if o['termination_reason'] is None:
    failure=read(root/'FAILED.json').get('error','') if (root/'FAILED.json').exists() else ''
    allowed=('No completed LSS-accepted candidate before the wall deadline','No candidate passes final LSS acceptance (P >= 0.99)','phase wall deadline reached')
    assert failure in allowed,'unexpected_worker_failure:'+failure
   raise AssertionError('process_failure:'+str(r.get('failure_class',o['termination_reason'])))
  assert 0<o['process_wall_seconds']<=600 and o['wall_clock_source']=='dedicated_wait_thread_from_before_Popen','whole600'
  x=read(root/'RESULT.json');raw=read(root/'S10_search.json');meta=read(root/'S10_search.run.json');complete=read(root/'COMPLETION.json');trace=read(root/'ORIGINAL_LSS_DECISION_TRACE.json')
  assert x['status']==raw['status']=='completed' and x['schema']=='S10_LSS_full_sample_total600_v3','completion_status'
  assert x['acceptance_evaluator']=='LSS' and x['acceptance_threshold']==.99 and x['final_lss_enforced'],'final_acceptance_method'
  assert x['search_flow']==raw['search_flow']==meta['search_flow']==flow[o['arm']],'flow'
  positive=flow[o['arm']] in ['block_winf_dro','block_winf_transport']
  if positive:validate_model_metadata(d,raw)
  else:assert raw['DRO_model'] is None and raw['certificate_scope']=='nominal_empirical_product_probability','nominal_control'

  assert x['search_seed']==raw['seed']==meta['seed']==o['seed'] and x['rep']==o['rep'],'seed'
  assert x['instance']==raw['instance']==o['instance'] and x['capacity']==raw['capacity']==o['capacity'],'problem'
  assert complete['start_includes_process_launch'] and complete['all_output_files_fsynced'],'save_clock'
  assert x['clock_policy']==complete['clock_policy']=='launch_to_exit_total_wall' and complete['budget']==x['total_budget_seconds']==600,'clock_contract'
  assert 0<meta['elapsed']<=x['wall_seconds_including_LSS']<=complete['elapsed_before_completion_save']<=o['process_wall_seconds'],'clock_order'
  assert meta['within_budget'] and not raw['config']['validation_outside_search_clock'],'phase_clock'
  assert x['lss_sample_index_min']==0 and x['lss_sample_index_max']==499 and not x['real_probability_reporting'],'LSS_indices'
  assert raw['config']['no_cross_run_solutions'] and raw['config']['sampling_population']=='all_L_samples','isolation'
  for n,h in meta['input_sha256'].items():assert h==P['input_pins']['benchmark/'+o['instance']+'/'+n],'input_hash'
  latest={};final={};evaluations=[]
  for e in trace:
   if 'evaluation' in e:
    assert 0<=e['probability']<=1 and 0<=e['elapsed_start']<=e['elapsed_end']<=590.1,'evaluation_clock'
    latest[tuple(e['selection'])]=e;evaluations.append(e['evaluation'])
   if e['stage']=='LSS_final_acceptance':final[tuple(e['selection'])]=e
   if e['stage']=='LSS_incomplete_evaluation':assert e['no_probability_returned'] and 'probability' not in e,'partial_probability'
  assert evaluations==list(range(1,x['evaluation_times']+1)),'evaluation_sequence'
  for key,e in final.items():assert e['source_evaluation']==latest[key]['evaluation'] and e['probability']==latest[key]['probability'] and e['accepted']==(e['probability']>=.99),'last_complete_LSS'
  variants=x['original_output_variants'];assert len(variants)==3,'variants'
  for v in variants:
   key=tuple(v['selection']);assert valid_selection(d,v['selection']) and abs(math.fsum(d['costs'][j] for j in key)-v['cost'])<1e-8,'selection_cost'
   assert v['probability']>=.99 and v['probability']==latest[key]['probability'] and final[key]['accepted'] and 'real_probability' not in v,'LSS_acceptance'
  assert variants[0]['selection']==x['selection'] and variants[0]['cost']==x['cost'] and variants[0]['probability']==x['original_LSS_confidence'],'main_output'
  csvs=list((root/'result/Localsearch').glob('*_[012].csv'));assert len(csvs)==3,'CSVs'
  for p in csvs:
   v=variants[int(p.stem.rsplit('_',1)[1])]
   with p.open() as f:rr=csv.DictReader(f);names=rr.fieldnames;values=list(rr)
   assert len(names)==6 and all('Real' not in name for name in names) and len(values)==1,'CSV_format'
   y=values[0];assert float(y['Cost'])==v['cost'] and float(y['Confidence Level'])==v['probability'] and json.loads(y['Solution'])==v['selection'],'CSV_record'
  for q in raw['candidate_shortlist']:
   cert=q['certificate'];lo=int(cert['lower_numerator']);hi=int(cert['upper_numerator']);den=int(cert['denominator'])
   assert valid_selection(d,q['selection']) and den==500**len(d['groups']) and 0<=lo<=hi<=den and lo*100>=den*99,'raw_CDF_certificate'
  for cert in raw['native_infeasible_proofs']:
   lo=int(cert['lower_numerator']);hi=int(cert['upper_numerator']);den=int(cert['denominator'])
   assert valid_selection(d,cert['selection']) and den==500**len(d['groups']) and 0<=lo<=hi<=den and hi*100<99*den,'native_infeasible_certificate'
  candidates=[q for q in raw['candidate_shortlist'] if q['selection']==x['selection']];assert candidates,'own_pool'
  init=next(q for q in meta['phase_records'] if q['phase']=='initialization')
  for entry in raw.get('block_history',[]):
   bound=entry.get('bound')
   if bound:
    assert valid_selection(d,bound['anchor']) and bound['anchor']==entry['anchor'] and bound['block']==entry['block'] and bound['cost_cap']==entry.get('collection_cap',entry['best_before']),'bound_identity'
    block=bound['block'];assert block==sorted(set(block)) and 2<=len(block)<=4,'bound_block'
    if bound['status']=='cost_infeasible':
     minimum=sum((Fraction.from_float(d['costs'][bound['anchor'][g]]) for g in range(len(d['groups'])) if g not in block),Fraction(0))
     minimum+=sum((min(Fraction.from_float(d['costs'][j]) for j in d['groups'][g]) for g in block),Fraction(0))
     assert minimum>Fraction.from_float(bound['cost_cap'])+Fraction(1,10**8),'cost_lower_bound'
   if bound and 'upper' in bound:
    numerator,denominator=proof_count(d,bound,o['capacity'],positive);assert numerator==int(bound['upper']) and denominator==int(bound['denominator']),'independent_envelope_count';bound_checks+=1
    assert (numerator*100<denominator*99)==(bound['status']=='integer_probability_infeasible'),'prune_proof'
   if entry.get('pruned'):assert bound and bound['status'] in ['integer_probability_infeasible','cost_infeasible'],'floating_prune'
  if flow[o['arm']]=='frontier_mitm_zero':assert all(e['delta']==0 for e in raw['match_history']),'zero_radius_control'
  if flow[o['arm']]=='block_mitm':assert all(e['delta']==0 for e in raw['match_history']) and not raw['ellipsoid_history'],'B01_flow'

  model_output_checks=0
  if True:
   for variant in variants:
    record=next(q for q in raw['candidate_shortlist'] if q['selection']==variant['selection'])
    certificate=record['certificate'];nu,de=selected_model_count(d,variant['selection'],certificate['bins'],o['capacity'],positive)
    assert nu==int(certificate['lower_numerator']) and de==int(certificate['denominator']),'independent_worst_case_output_count'
    assert nu*100>=99*de,'DRO_output_not_model_feasible'
    model_output_checks+=1
  if flow[o['arm']] in ['block_insurance','block_winf_dro','block_winf_transport']:
   assert all(q['delta']==0 for q in raw['match_history']) and not raw['ellipsoid_history'],'coverage_flow'
   expected_model='positive_Winf' if positive else 'nominal'
   assert all(q.get('model',expected_model)==expected_model for q in raw['block_history']),'block_model'

  budget_verified=verify_models(raw,d['groups'],d['costs'],[exact_rows(d,j) for j in range(len(d['costs']))] if flow[o['arm']] in ['cvar_budget_calibrated','entropy_cdf_calibrated','cvar_budget_polish'] else [],o['capacity'])
  transport_verified=check_transport_proofs(d,raw,flow[o['arm']])
  assert 0<=raw['search_certificate_seconds']<=meta['elapsed'],'active_certificate_clock'
  rawbest=tuple(raw['selected']['selection']);last=latest.get(rawbest)
  r.update(budget_proofs_verified=budget_verified, budget_statistics=model_statistics(raw), independent_output_CDF_checks=model_output_checks, valid=not errors,cost=x['cost'],LSS=x['original_LSS_confidence'],selection=x['selection'],initialization_cost=init['best_after'],raw_final_cost=raw['selected']['cost'],post_init_improved=(init['best_after'] is None or raw['selected']['cost']<init['best_after']-1e-8),block_incumbent_improvements=sum(e.get('source','').startswith(('B01_','C01_insurance_block','D01_DRO_block')) for e in raw['events']),first_found_seconds=min(q['found_seconds'] for q in candidates),search_seconds=meta['elapsed'],LSS_seconds=x['LSS_finalization_seconds'],block_records=len(raw.get('block_history',[])),independent_DRO_output_checks=model_output_checks if positive else 0,positive_DRO=positive,selected_transport_shift=raw.get('selected_transport_shift_rational'),transport_exclusions_verified=transport_verified,active_certificate_calls=raw['search_certificate_calls'],active_certificate_seconds=raw['search_certificate_seconds'],transport_statistics=raw['DRO_transport_statistics'],raw_pool_count=raw['raw_certified_pool_count'],shortlist_count=len(raw['candidate_shortlist']),raw_best_last_LSS=last['probability'] if last else None,raw_best_final_filter=final.get(rawbest,{}).get('accepted'),final_cost_above_raw_best=x['cost']>raw['selected']['cost']+1e-8,final_cost_minus_raw_best=x['cost']-raw['selected']['cost'])
 except Exception as e:r['errors'].append(type(e).__name__+':'+str(e))
 rows.append(r)
allvalid=not errors and all(r['valid'] for r in rows)
improved={c['index']:sum(r.get('post_init_improved',False) for r in rows if r['arm']==P['arms'][-1]['name'] and r['case_index']==c['index']) for c in P['cases']}
gate=allvalid and all(v>=1 for v in improved.values())
groups=[]
for c in P['cases']:
 for a in P['arms']:
  rr=[r for r in rows if r['case_index']==c['index'] and r['arm']==a['name']];vv=[r for r in rr if r['valid']]
  groups.append({'case_index':c['index'],'arm':a['name'],'terminal':len(rr),'valid':len(vv),'best_diagnostic':min([r['cost'] for r in vv],default=None),'official_avg':statistics.mean(r['cost'] for r in vv) if len(vv)==30 else None,'official_std':statistics.stdev(r['cost'] for r in vv) if len(vv)==30 else None,'valid_only_diagnostic_avg':statistics.mean(r['cost'] for r in vv) if vv else None,'whole_mean':statistics.mean(r['process_wall_seconds'] for r in rr),'post_init_improvements':sum(r.get('post_init_improved',False) for r in vv),'block_improvements':sum(r.get('block_incumbent_improvements',0) for r in vv)})
report={'schema':'R02_formal_record_audit','reader_version':'R02_independent_v1_GMP_budget_RO','reader_sha256':sha(Path(__file__)) if Path(__file__).is_file() else None,'global_errors':errors,'terminal':len(rows),'independent_valid':sum(r['valid'] for r in rows),'verified_output_files':verified_files,'independent_integer_envelope_checks':bound_checks,'gate_pass':gate,'post_init_by_case':improved,'formal360_started':True,'groups':groups,'rows':rows,'no_probability_resampling':True,'not_30_repeat_conclusion':PILOT,'cost_arithmetic_error_bounds':{k:d['cost_arithmetic_error_bound'] for k,d in data.items()}}
for g in groups:
 rr=[r for r in rows if r['valid'] and r['case_index']==g['case_index'] and r['arm']==g['arm']]
 g['final_cost_above_raw_best_runs']=sum(r['final_cost_above_raw_best'] for r in rr)
 g['raw_best_last_LSS_below_threshold_runs']=sum(r['raw_best_last_LSS'] is not None and r['raw_best_last_LSS']<.99 for r in rr)
 g['mean_final_cost_minus_raw_best']=statistics.mean(r['final_cost_minus_raw_best'] for r in rr) if rr else None
 g['mean_raw_pool_count']=statistics.mean(r['raw_pool_count'] for r in rr) if rr else None
 g['mean_LSS_seconds']=statistics.mean(r['LSS_seconds'] for r in rr) if rr else None

import numpy as np
def flip(a,b,seed):
 delta=np.array(a,dtype=float)-np.array(b,dtype=float);delta=delta[delta!=0]
 if not len(delta):return 1.
 observed=abs(float(np.mean(delta)));rng=np.random.RandomState(seed)
 # Enumerate a small active difference family exactly, otherwise use a
 # predeclared common Monte Carlo sign-flip family (not probability sampling).
 if len(delta)<=18:
  masks=np.arange(1<<len(delta),dtype=np.uint64)[:,None]
  signs=2*((masks>>np.arange(len(delta),dtype=np.uint64))&1).astype(np.int8)-1
  return float(np.mean(np.abs(np.mean(signs*delta,axis=1))>=observed-1e-12))
 extreme=0
 for first in range(0,99999,5000):
  size=min(5000,99999-first);signs=rng.randint(0,2,size=(size,len(delta)))*2-1
  extreme+=int(np.sum(np.abs(np.mean(signs*delta,axis=1))>=observed-1e-12))
 return (extreme+1)/100000
def holm(values):
 order=sorted(range(len(values)),key=lambda k:values[k]);out=[1.]*len(values);prior=0
 for rank,k in enumerate(order):prior=max(prior,min(1.,(len(values)-rank)*values[k]));out[k]=prior
 return out
comparisons=[]
for c in P['cases']:
 for idx,(a,b) in enumerate([(P['arms'][i]['name'],P['arms'][j]['name']) for i in range(1,len(P['arms'])) for j in range(i)]):
  rr={arm:sorted([r for r in rows if r['case_index']==c['index'] and r['arm']==arm],key=lambda r:r['rep']) for arm in [a,b]}
  complete=all(len(v)==30 and all(r['valid'] for r in v) for v in rr.values())
  p=flip([r['cost'] for r in rr[a]],[r['cost'] for r in rr[b]],20261201+c['index']*10+idx) if complete else 1.
  disc_a=sum(x['valid'] and not y['valid'] for x,y in zip(rr[a],rr[b]));disc_b=sum(not x['valid'] and y['valid'] for x,y in zip(rr[a],rr[b]));n=disc_a+disc_b
  vp=min(1.,2*sum(math.comb(n,k) for k in range(min(disc_a,disc_b)+1))/2**n) if n else 1.
  diff=statistics.mean(r['cost'] for r in rr[a])-statistics.mean(r['cost'] for r in rr[b]) if complete else None
  comparisons.append({'case_index':c['index'],'candidate':a,'reference':b,'complete30':complete,'avg_diff':diff,'cost_p_raw':p if complete else None,'cost_family_reserved_p':p,'validity_p_raw':vp})
for key,outkey in [('cost_family_reserved_p','cost_p_holm18'),('validity_p_raw','validity_p_holm18')]:
 adjusted=holm([x[key] for x in comparisons])
 for item,p in zip(comparisons,adjusted):item[outkey]=p
report['comparisons']=comparisons
report['schema']='R04_pilot60_independent_record_audit' if PILOT else 'R04_formal360_independent_record_audit'
report['official30_conclusion']=not PILOT
report['pilot_first5_counted_in_formal30']=PILOT
report['mechanism_progress_check']=report.pop('gate_pass')
report['automatic40_expansion']=False
report['independent_DRO_output_certificates']=sum(r.get('independent_DRO_output_checks',0) for r in rows)
report['independent_output_CDF_certificates']=sum(r.get('independent_output_CDF_checks',0) for r in rows)
report['independent_budget_proofs']=sum(r.get('budget_proofs_verified',{}).get('proofs',0) for r in rows)
report['integer_arithmetic_backend']='independent Python coefficients; system GMP via ctypes (no solver or writer imports)'
report['all_positive_radius_items_verified']=all('radius_units' in d for d in data.values())

(H/('PILOT_INDEPENDENT_AUDIT.json' if PILOT else 'FINAL_INDEPENDENT_AUDIT.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False),flush=True)

report['independent_transport_exclusions_verified']=sum(r.get('transport_exclusions_verified',0) for r in rows)
(H/('PILOT_INDEPENDENT_AUDIT.json' if PILOT else 'FINAL_INDEPENDENT_AUDIT.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'R04_transport_verified':report['independent_transport_exclusions_verified'],'valid':report['independent_valid'],'terminal':report['terminal']}),flush=True)

# Runtime comparisons have their own prospectively registered Holm18 family.
for idx,item in enumerate(comparisons):
 aa=sorted([r for r in rows if r['case_index']==item['case_index'] and r['arm']==item['candidate']],key=lambda r:r['rep'])
 bb=sorted([r for r in rows if r['case_index']==item['case_index'] and r['arm']==item['reference']],key=lambda r:r['rep'])
 complete=item['complete30']
 tp=flip([r['process_wall_seconds'] for r in aa],[r['process_wall_seconds'] for r in bb],20261202+item['case_index']*10+idx) if complete else 1.
 item['whole_time_diff']=statistics.mean(r['process_wall_seconds'] for r in aa)-statistics.mean(r['process_wall_seconds'] for r in bb) if complete else None
 item['time_p_raw']=tp if complete else None;item['time_family_reserved_p']=tp
for item,p in zip(comparisons,holm([c['time_family_reserved_p'] for c in comparisons])):item['time_p_holm18']=p
report['comparisons']=comparisons
report['reader_version']='R04_independent_RO_Fraction_private_FFT_reconstruction_GMP_CDF'
report['independent_polish_history']=sum(r.get('budget_proofs_verified',{}).get('polish_history',0) for r in rows)
report['independent_polish_proposals']=sum(r.get('budget_proofs_verified',{}).get('polish_proposals',0) for r in rows)
report['independent_polish_MIPs']=sum(r.get('budget_proofs_verified',{}).get('polish_mips',0) for r in rows)
(H/('PILOT_INDEPENDENT_AUDIT.json' if PILOT else 'FINAL_INDEPENDENT_AUDIT.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
if not PILOT:
 contrasts=[c for c in comparisons if c['candidate']=='D_R04_BUDGET_FFT' and c['reference']=='B_D02_TRANSPORT']
 clean=not errors and len(contrasts)==3 and all(c['complete30'] for c in contrasts)
 tests={'all_R04_D02_30_valid_source_clock_clean':clean,'all_three_unrounded_avg_not_higher':clean and all(c['avg_diff']<=0 for c in contrasts),
 'at_least_one_cost_significantly_lower':clean and any(c['avg_diff']<0 and c['cost_p_holm18']<.05 for c in contrasts),
 'all_three_complete_mean_time_lower_and_significant':clean and all(c['whole_time_diff']<0 and c['time_p_holm18']<.05 for c in contrasts)}
 decision={'stage':'completed_three_case_L3','L4_eligible':all(tests.values()),'tests':tests,'contrasts':contrasts,'requires_fresh_capacity_and_new_full40_protocol':True,'no_retries':True,'failed_cost_not_imputed':True}
 (H/'FULL40_ELIGIBILITY_DECISION.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2))
 print(json.dumps({'R04_complete':True,'terminal':len(rows),'valid':report['independent_valid'],'global_errors':errors,'L4_eligible':decision['L4_eligible']}),flush=True)
