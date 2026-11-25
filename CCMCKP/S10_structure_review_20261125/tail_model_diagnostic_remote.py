from pathlib import Path
import json,math,pickle
import numpy as np
from decimal import Decimal as D, getcontext
from functools import reduce
getcontext().prec=100
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_corecuts_600s_20261124';assert Path.cwd()==B
P=json.loads((H/'PROTOCOL.json').read_text());out=[]
for case in P['cases']:
 d=B/'benchmark'/case['instance'];n=len(np.loadtxt(str(d/'cost.txt')))
 samples=[np.sort(np.loadtxt(str(d/(str(j)+'_sample.txt')))) for j in range(n)]
 delta=.01
 centers=[float(v[0]+v[-1])/2 for v in samples];ahat=max(float(v[-1]-v[0])/2+delta for v in samples)
 e=[]
 for i,v in enumerate(samples):
  z=(v-centers[i])/ahat;surv=(len(v)-np.searchsorted(v,v,side='right'))/len(v)
  e.append(float(np.max(surv/(1-z))))
 rows=[]
 for arm in ['S10_TOTAL600','EGS_CORE_TOTAL600']:
  saved=[json.loads(p.read_text()) for p in (H/'runs').glob(arm+'_i%s_r*/RESULT.json'%case['index'])]
  x=min(saved,key=lambda q:(q['cost'],q['rep']));s=x['selection'];m=len(s);A=D(ahat);beta=D(case['tmax'])-sum(D(centers[j]) for j in s)
  numerator=sum((-1)**k*math.comb(m,k)*max((m-2*k)*A-beta,D(0))**m for k in range(m+1))
  bound=numerator/D(math.factorial(m))*reduce(lambda a,b:a*b,(D(e[j])/A for j in s),D(1))
  assert bound>=0
  rows.append({'arm':arm,'selection_rep':x['rep'],'cost':x['cost'],'observed_saved_LSS':x['original_LSS_confidence'],'MATPD_plugin_min':min(e[j] for j in s),'MATPD_plugin_max':max(e[j] for j in s),'formal_RCP_formula_value_under_plugin_parameters':str(bound),'min_1_formula_value':float(min(1,bound)),'meets_formula_point01':bool(bound<=D('.01'))})
 out.append({'case':case['index'],'common_halfwidth':ahat,'delta_as_paper_example_not_calibrated':delta,'rows':rows})
print(json.dumps({'scope':'static diagnostic of a literature surrogate on saved vectors, no optimization or LSS/MC probability evaluation; floating plug-in statistics are illustrative, not audited certificates or population-confidence guarantees','paper':'10.1137/23M1620867 Theorem3.1 equation3.2 and empirical estimator5.2','precision_decimal_digits':100,'cases':out}))
