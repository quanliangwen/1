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
