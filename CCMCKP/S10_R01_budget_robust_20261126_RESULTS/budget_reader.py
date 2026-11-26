"""Independent Fraction reader; never imports the optimization writer or sampler."""
from fractions import Fraction

def verify_budget(raw,groups,costs,original_samples,capacity):
 model=raw['budget_RO_model'];proofs=raw['budget_RO_proposals'];tasks=raw['budget_RO_subproblems'];stats=raw['budget_RO_statistics']
 if raw['search_flow']!='budget_robust':
  assert model is None and stats is None and proofs==[] and tasks==[], 'budget_disabled_control'
  return {'proofs':0,'qualified':0,'rejected':0,'subproblems':0}
 assert model['model']=='Bertsimas_Sim_upper_deviation_budget_RO' and model['all_original_samples']
 assert model['positive_budget_only'] and not model['nominal_zero_budget_fallback']
 assert not model['probability_coverage_claim'] and not model['Gamma_is_probability_level']
 assert not model['historical_solution_inputs'] and not model['external_MIPstarts']
 assert model['original_CDF_gate_preserved'] and model['final_acceptance']=='unchanged original LSS'
 assert not model['global_optimality_claim'] and model['partial_threshold_enumeration_possible']
 assert model['fixed_gamma_candidate_quota']==16 and model['MIP_slice_seconds']==1 and model['MIP_solutions_per_subproblem']==2
 n=len(costs);m=len(groups);margin=Fraction(1,10**8);cap=Fraction(str(capacity));assert Fraction(model['robust_guard'])==margin
 mean=[];upper=[];delta=[]
 for j,row in enumerate(original_samples):
  row=[Fraction(x) for x in row];assert len(row)==model['samples_per_item']
  mu=sum(row,Fraction())/len(row);top=max(row);mean.append(mu);upper.append(top);delta.append(top-mu)
  rec=model['items'][j];assert rec['item']==j and Fraction(rec['mean'])==mu and Fraction(rec['upper'])==top and Fraction(rec['deviation'])==top-mu,'budget_raw_item'
 assert len(model['items'])==n
 thresholds=set(delta)|{Fraction()};assert model['threshold_count']==len(thresholds)
 ratios=['1/10','3/20','1/20','1/5','1/40','3/10','1/2','1']
 gammas=[Fraction(x)*m for x in ratios];assert [Fraction(x) for x in model['budget_order']]==gammas,'budget_frozen_order'
 def selection(s):return len(s)==m and all(j in group for j,group in zip(s,groups))
 qualified={};rejected=0
 for p in proofs:
  s=p['selection'];assert selection(s),'budget_selection'
  gamma=Fraction(p['gamma']);theta=Fraction(p['theta']);assert gamma in gammas and gamma>0 and theta in thresholds,'budget_parameters'
  values=sorted([delta[j] for j in s],reverse=True);whole=gamma.numerator//gamma.denominator
  protect=sum(values[:whole],Fraction())+(gamma-whole)*values[whole] if whole<m else sum(values,Fraction())
  nominal=sum((mean[j] for j in s),Fraction());worst=nominal+protect
  fixed=nominal+gamma*theta+sum((max(Fraction(),delta[j]-theta) for j in s),Fraction())
  assert fixed>=worst,'budget_dual_bound'
  assert Fraction(p['nominal_sum'])==nominal and Fraction(p['budget_worst_sum'])==worst and Fraction(p['fixed_theta_sum'])==fixed,'budget_exact_sums'
  assert Fraction(p['robust_slack'])==cap-margin-worst and p['robust_feasible']==(worst<=cap-margin) and p['fixed_theta_feasible']==(fixed<=cap-margin),'budget_exact_guard'
  assert p['own_run_raw_samples'] and p['not_a_probability_estimate'] and p['source'] in ['R01_self_generated_full_budget_anchor','R01_budget_threshold_MCKP'],'budget_provenance'
  if p['source']=='R01_self_generated_full_budget_anchor':
   own=[min(group,key=lambda j:(upper[j],costs[j],j)) for group in groups]
   assert s==own and gamma==m and theta==0,'budget_own_initialization'
  if p['robust_feasible'] and p['fixed_theta_feasible']:
   assert tuple(s) not in qualified,'budget_duplicate_native_gate';qualified[tuple(s)]=p
  else:
   rejected+=1;assert p['decision']=='rejected_exact_robust_row' and not p['native_evaluation_completed'],'budget_false_witness_not_admitted'
 for q in raw['candidate_shortlist']:
  p=qualified[tuple(q['selection'])];assert p['decision']=='nominal_CDF_accepted' and p['native_evaluation_completed'],'budget_admitted_own_witness'
  assert q['source']==p['source'],'budget_candidate_origin'
 for task in tasks:
  gamma=Fraction(task['gamma']);theta=Fraction(task['theta']);assert gamma in gammas and theta in thresholds
  assert Fraction.from_float(task['rhs_double'])<=cap-margin-gamma*theta,'budget_outward_rhs'
  assert task['solutions_returned']<=2 and task['MIP_seconds']>=0 and task['completed_before_native_gate']
 assert stats['unique_proposals']==len(qualified) and stats['subproblem_count']==len(tasks) and stats['no_LSS_calls_in_generator']
 return {'proofs':len(proofs),'qualified':len(qualified),'rejected':rejected,'subproblems':len(tasks)}
