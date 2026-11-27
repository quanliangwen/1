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
