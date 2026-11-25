from pathlib import Path
import json,math,pickle
import numpy as np
from fractions import Fraction
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_corecuts_600s_20261124';assert Path.cwd()==B
P=json.loads((H/'PROTOCOL.json').read_text());output=[]
for case in P['cases']:
 d=B/'benchmark'/case['instance'];groups=pickle.loads((d/'node_to_factor.pkl').read_bytes());groups=[groups[k] for k in sorted(groups)] if isinstance(groups,dict) else groups
 costs=np.loadtxt(str(d/'cost.txt'));samples=[np.loadtxt(str(d/(str(j)+'_sample.txt'))) for j in range(len(costs))]
 mu=np.array([np.mean(v) for v in samples]);var=np.array([np.var(v) for v in samples]);center=(np.array([max(v) for v in samples])+np.array([min(v) for v in samples]))/2
 half=(np.array([max(v) for v in samples])-np.array([min(v) for v in samples]))/2+.01;ahat=max(half)
 cc=np.empty(len(costs));mm=cc.copy()
 for group in groups:cc[group]=costs[group]-np.mean(costs[group]);mm[group]=mu[group]-np.mean(mu[group])
 rows=[]
 for arm in ['S10_TOTAL600','EGS_CORE_TOTAL600']:
  records=[json.loads(p.read_text()) for p in (H/'runs').glob(arm+'_i%s_r*/RESULT.json'%case['index'])]
  x=min(records,key=lambda x:(x['cost'],x['rep']));s=x['selection'];m=len(s);V=float(var[s].sum());M=float(mu[s].sum());risk=M+2.4*math.sqrt(V)
  rows.append({'arm':arm,'rep_for_lowest_observed_cost':x['rep'],'cost':x['cost'],'sum_empirical_means':M,'sqrt_sum_empirical_population_variances':math.sqrt(V),'ellipsoid_score_gamma2_4':risk,'recorded_last_LSS':x['original_LSS_confidence'],
   'sum_sample_support_midpoints':float(center[s].sum()),'sample_support_common_halfwidth':float(ahat),
   'selected_halfwidth_max':float(max(half[s])),'selected_halfwidth_min':float(min(half[s]))})
 output.append({'case_index':case['index'],'instance':case['instance'],'capacity':case['tmax'],'groups':len(groups),'alternatives_per_group':[len(g) for g in groups],
  'within_group_cost_vs_mean_correlation':float(np.corrcoef(cc,mm)[0,1]),'empirical_product_log10_outcomes_per_selection':len(groups)*math.log10(500),'comparison':rows})
print(json.dumps({'scope':'read-only moments/support summaries of saved outputs and raw input; no new probability evaluation, optimization, or parameter scan','cases':output}))
