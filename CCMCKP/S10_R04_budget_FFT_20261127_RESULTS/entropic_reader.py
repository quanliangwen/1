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
