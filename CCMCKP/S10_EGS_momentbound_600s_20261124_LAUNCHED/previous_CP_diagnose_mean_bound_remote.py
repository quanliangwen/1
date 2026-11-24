from pathlib import Path
import json,pickle,math
import numpy as np
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_costpriority_600s_20261124';assert Path.cwd()==B
P=json.loads((H/'PROTOCOL.json').read_text());out=[]
for c in P['cases']:
 d=B/'benchmark'/c['instance'];g=pickle.loads((d/'node_to_factor.pkl').read_bytes());g=[g[k] for k in sorted(g)] if isinstance(g,dict) else g
 means=[];variances=[]
 for j in range(sum(len(x) for x in g)):
  a=np.loadtxt(d/(str(j)+'_sample.txt'));means.append(float(a.mean()));variances.append(float(a.var()))
 vmax=sum(max(variances[j] for j in group) for group in g);upper=c['tmax']+math.sqrt(vmax/99)
 raw=json.loads((H/'runs'/('EGS_CP_TOTAL600_i%s_r01'%c['index'])/'S10_search.json').read_text());q=[x for x in raw['ellipsoid_history'] if x.get('has_candidate')]
 init=next(x for x in raw['ellipsoid_history'] if x['event']=='dominance_master_initialized')['self_generated_start']
 row={'case_index':c['index'],'capacity':c['tmax'],'diagnostic_global_variance_upper':vmax,'diagnostic_necessary_mean_upper':upper,'init_mean':sum(means[j] for j in init),'queried_mean_min':min(sum(means[j] for j in x['selection']) for x in q),'queried_mean_max':max(sum(means[j] for j in x['selection']) for x in q),'queries':len(q),'excluded_by_necessary_mean_bound':sum(sum(means[j] for j in x['selection'])>upper+1e-8 for x in q),'new_probability_evaluations':0,'not_a_parameter_scan':True};out.append(row)
(H/'MEAN_BOUND_DIAGNOSIS.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
