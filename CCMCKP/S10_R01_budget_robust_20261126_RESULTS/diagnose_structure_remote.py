"""Read-only exact model-structure analysis; no solver or probability sampling."""
from pathlib import Path
from fractions import Fraction
import math,pickle,json
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/r01_budget_robust_20261126';assert Path.cwd()==B
out=[]
for case in [(19,'LAB_50_10_500_',63),(35,'APP_30_10_500_',58),(39,'APP_50_10_500_',91)]:
 index,name,cap=case;F=B/'benchmark'/name;groups=pickle.loads((F/'node_to_factor.pkl').read_bytes());groups=[groups[k] for k in sorted(groups)] if isinstance(groups,dict) else groups
 costs=[float(x) for x in (F/'cost.txt').read_text().split()];mu=[];ds=[]
 for j in range(len(costs)):
  samples=[Fraction(x) for x in (F/(str(j)+'_sample.txt')).read_text().split()];assert len(samples)==500
  mean=sum(samples,Fraction())/500;mu.append(mean);ds.append(max(samples)-mean)
 denominator=1
 for v in mu+ds:denominator=denominator*v.denominator//math.gcd(denominator,v.denominator)
 means=[int(v*denominator) for v in mu];deviations=[int(v*denominator) for v in ds]
 records=[]
 for theta in sorted(set(deviations)|{0}):
  selected=[min(group,key=lambda j:(means[j]+max(0,deviations[j]-theta),j)) for group in groups]
  inner=sum(means[j]+max(0,deviations[j]-theta) for j in selected)
  records.append((theta,inner,selected))
 rows=[]
 for ratio in ['1/10','3/20','1/20','1/5','1/40','3/10','1/2','1']:
  gamma=Fraction(ratio)*len(groups);a,b=gamma.numerator,gamma.denominator
  theta,inner,sel=min(records,key=lambda r:(a*r[0]+b*r[1],r[0]))
  lower=Fraction(a*theta+b*inner,b*denominator)
  chosen=sorted([ds[j] for j in sel],reverse=True);left=gamma;protect=Fraction()
  for d in chosen:
   if left<=0:break
   take=min(left,Fraction(1));protect+=take*d;left-=take
  assert sum((mu[j] for j in sel),Fraction())+protect==lower
  rows.append({'Gamma':str(gamma),'minimum_possible_budget_load':str(lower),'minimum_load_float':float(lower),'theta':str(Fraction(theta,denominator)),'attaining_selection':sel,'budget_model_globally_resource_infeasible':lower>Fraction(cap)-Fraction(1,10**8),'every_threshold_checked':len(records)})
 out.append({'case_index':index,'instance':name,'capacity':cap,'exact_minimum_over_all_selections_and_thresholds':True,'budgets':rows})
result={'status':'PASS','only_original_inputs':True,'no_solver_or_probability_sampling':True,'not_an_algorithm_input':True,'cases':out}
(H/'STRUCTURE_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
