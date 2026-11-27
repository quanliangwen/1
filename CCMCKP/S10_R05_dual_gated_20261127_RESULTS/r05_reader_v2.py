"""Independent Fraction/interval/private-score reader. No writer or solver imports."""
from fractions import Fraction as F
import math
from adaptive_reader import verify_adaptive
from interval_reader import IntervalMath
from r05_fft_reader import r05_private_tools
_r05_coeff={}
def verify_r05(raw,groups,costs,samples,capacity):
 assert raw['search_flow']=='dual_budget_gated'
 model=raw['R05_model'];calls=raw['r05_native_calls'];history=raw['r05_private_history']
 assert model['model']=='R05_dual_surrogate_certification_gated_empirical_chance_hybrid'
 assert not model['historical_solution_inputs'] and model['generator_LSS_calls']==0 and model['private_cache_isolated']
 assert not model['private_FFT_is_certificate'] and not model['nearest_rounding_is_unbiased_claim'] and model['precision_damping']==12
 assert model['safe_probability']==.99005 and model['safe_fft_gate']==.98985 and model['fallback_ratio']==.005
 assert model['ES95_finished_seconds']<=66 and model['mother_finished_seconds']<=91
 parent=dict(raw,search_flow='cvar_budget_calibrated',candidate_shortlist=model['ES95_pool'])
 budget=verify_adaptive(parent,groups,costs,samples,capacity)
 select,cost,prob,marginal,near=r05_private_tools(groups,costs,samples,capacity)
 em=raw['entropic_model'];tabs={};ref=IntervalMath();tilts=[F(3,5),F(1,4)];key=(id(groups),str(capacity));cache=_r05_coeff.setdefault(key,{})
 assert not em['historical_solution_inputs'] and not em['external_MIPstarts'] and em['precision_bits']==192
 for k,tab in enumerate(em['tables']):
  assert tab['index']==k and k<2 and F(tab['t'])==tilts[k]
  if k not in cache:cache[k]=[ref.weight([F(x) for x in row],tilts[k]) for row in samples]
  lower=[];upper=[]
  for j,w in enumerate(tab['items']):
   lo,hi=F(w['lower']),F(w['upper']);a,b=cache[k][j];assert lo<=a<=b<=hi and hi-lo<F(1,10**40)
   lower.append(lo);upper.append(hi)
  own=[min(g,key=lambda j:(upper[j],j)) for g in groups]
  assert own==tab['initial_selection'] and F(tab['minimum_upper_weight_sum'])==sum((upper[j] for j in own),F())
  tabs[k]=(lower,upper)
 ent={}
 for w in raw['entropic_proposals']:
  s=w['selection'];select(s);k=w['table_index'];lo,hi=tabs[k];eta=F(w['eta']);assert F(4,5)<=eta<=F(921,200) and F(w['t'])==tilts[k]
  low=sum((lo[j] for j in s),F());high=sum((hi[j] for j in s),F());rhs=F(str(capacity))-F(1,10**8)-eta/tilts[k]
  assert low==F(w['weight_sum_lower']) and high==F(w['weight_sum_upper']) and rhs==F(w['rhs_exact']) and high<=rhs
  assert w['source']=='R05_entropic_model' and w['own_run_raw_samples'] and not w['empirical_0.99_sufficient_eta']
  ent[tuple(s)]=w
 for q in raw['entropic_queries']:
  assert 0<=q['table_index']<2 and F(4,5)<=F(q['eta'])<=F(921,200)
  for x in q['returned']:
   s=raw['entropic_proposals'][x['record_index']]['selection'];near(x['private_probability'],prob(s))
   if q['cost_cap'] is not None and float(cost(s))>q['cost_cap']+1e-7:
    # A raw solver pool item may violate a float cost row by feasibility tolerance.
    # It must not be admitted to native CDF; the exact post-solver gate owns admission.
    assert not any(x['stage']=='mother_entropic_native_cdf' and x['selection']==s for x in calls),'out_of_cost_cap_solver_item_admitted'

 roots={tuple(w['selection']) for w in raw['adaptive_RO_proposals'] if w['robust_feasible'] and w['fixed_theta_feasible']}|set(ent)
 certified={tuple(x['selection']):x for x in model['certified_pool']}
 assert len(certified)==len(model['certified_pool'])
 for x in certified.values():
  select(x['selection']);near(x['cost'],float(cost(x['selection'])));c=x['certificate'];assert c['selection']==x['selection']
  assert int(c['lower_numerator'])*100>=int(c['denominator'])*99 and c['accepted']
 assert len(model['seeds'])<=4 and len({tuple(s) for s in model['seeds']})==len(model['seeds'])
 assert all(tuple(s) in roots|set(certified) for s in model['seeds'])
 reachable=set(roots)|set(certified)
 for x in history:
  s=x['selection'];select(s);near(x['probability'],prob(s))
  if x['stage']=='entropic':assert tuple(s) in ent
  else:
   anchor=x['anchor'];assert tuple(anchor) in reachable;dist=sum(a!=b for a,b in zip(s,anchor));assert x['distance']==dist
   assert dist==(1 if x['stage'].endswith('_one') else 2) if x['stage']!='A_local_MCKP' else dist<=5
   reachable.add(tuple(s))
 for q in raw['r05_local_MIP']:
  select(q['anchor']);p,values=marginal(q['anchor']);near(q['anchor_probability'],p)
  for j,r in enumerate(q['risk']):near(r,p-values[j])
  assert not q['solver'].get('external_MIPstarts',False)
  for s in q['returned']:
   assert sum(a!=b for a,b in zip(s,q['anchor']))<=5 and float(cost(s))<=q['cost_cap']+1e-7
   assert sum(q['risk'][j] for j in s)<=p-.9895+1e-7
 countA=countB=0;before=None;elapsedA=elapsedB=0
 for q in calls:
  s=q['selection'];select(s);near(q['cost'],float(cost(s)));assert q['elapsed']>=0 and q['finish']>=q['start']
  stage=q['stage'];assert q['state'] in ['accepted','infeasible','unknown']
  if q['state']!='unknown':
   c=q['certificate'];assert c['selection']==s and int(c['denominator'])==len(samples[0])**len(groups)
   assert int(c['lower_numerator'])*100>=99*int(c['denominator']) if q['state']=='accepted' else int(c['upper_numerator'])*100<99*int(c['denominator'])
  if stage.startswith('polish_channel'):
   assert q['fresh'] and tuple(s) in reachable
   bc=q['best_cost_before'];py=q['gate']['private_probability'];near(py,prob(s))
   if stage=='polish_channelA_native_cdf':
    countA+=1;elapsedA+=q['elapsed'];assert q['cost']<=bc-1e-6+1e-8 and py>=.9885
   else:
    countB+=1;elapsedB+=q['elapsed'];assert q['gate']['B_active_before'] and q['gate']['N_safe_before']<3
    assert q['best_probability_before']<.99005 and bc-1e-8<=q['cost']<=bc*1.005+1e-8 and py>=.98985
  elif stage=='mother_entropic_native_cdf':
   assert tuple(s) in ent
   if q['best_cost_before'] is not None:assert q['cost']<=q['best_cost_before']-1e-6+1e-8
 assert countB<=8 and countA+countB<=35 and elapsedA+elapsedB<=60.5
 if 'channelA_cdf_calls' in model:assert countA==model['channelA_cdf_calls'] and countB==model['channelB_cdf_calls']
 for s in raw['candidate_shortlist']:assert tuple(s['selection']) in certified and s['certificate']==certified[tuple(s['selection'])]['certificate']
 return dict(budget,entropic_proofs=len(ent),coefficient_items=sum(len(t[1]) for t in tabs.values()),polish_history=len(history),polish_mips=len(raw['r05_local_MIP']),polish_proposals=countA+countB)

def verify_r05_timing(timing,wall):
 t=timing['timing'];assert all(math.isfinite(x) and x>=-.001 for x in t.values())
 assert abs(sum(t.values())-timing['elapsed_before_timing_save'])<.001
 assert abs(wall-sum(t.values()))<1
 assert t['polish_channelA_native_cdf']+t['polish_channelB_native_cdf']<=60.5
