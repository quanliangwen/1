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
