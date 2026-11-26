from pathlib import Path
import json,hashlib,subprocess,os,time,pickle,itertools
from fractions import Fraction
from collections import Counter
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/r01_budget_robust_20261126';assert Path.cwd()==B and not (H/'formal').exists() and not (H/'VALIDATION.json').exists()
old=json.loads((H/'VALIDATION_FAILURE_0.json').read_text());checks=old['checks'];assert checks[0]['rc']==checks[1]['rc']==0
# The initial fixture assertion incorrectly assumed RO and nominal-CDF sets had
# the same optimum. Retain successful runs and derive the expected RO result.
def expected(F,cap):
 groups=pickle.loads((F/'node_to_factor.pkl').read_bytes());groups=[groups[k] for k in sorted(groups)] if isinstance(groups,dict) else groups
 costs=[float(x) for x in (F/'cost.txt').read_text().split()];samples=[[Fraction(x) for x in (F/(str(j)+'_sample.txt')).read_text().split()] for j in range(len(costs))]
 gamma=Fraction(len(groups),40);best=None
 for sel in itertools.product(*groups):
  means=[sum(samples[j],Fraction())/len(samples[j]) for j in sel];ds=sorted([max(samples[j])-means[k] for k,j in enumerate(sel)],reverse=True)
  left=gamma;extra=Fraction()
  for delta in ds:take=min(left,Fraction(1));extra+=take*delta;left-=take
  robust=sum(means,Fraction())+extra
  if robust>Fraction(cap)-Fraction(1,10**8):continue
  frequencies=[Counter(samples[j]) for j in sel];safe=0;total=1
  for j in sel:total*=len(samples[j])
  for points in itertools.product(*[list(f.items()) for f in frequencies]):
   if sum((p[0] for p in points),Fraction())<Fraction(cap):
    mass=1
    for p in points:mass*=p[1]
    safe+=mass
  if safe*100<99*total:continue
  value=sum(costs[j] for j in sel);best=value if best is None else min(best,value)
 return best
try:
 for ordinal,(fixture,cap) in enumerate([('LAB_3_2_500_','.5'),('LAB_2_2_500_','1.25')]):
  out=H/'integration60'/fixture
  if ordinal==0:row=checks[1];assert out.exists()
  else:
   assert not out.exists();begin=time.monotonic();env=dict(os.environ,CCMCKP_LAUNCH_MONOTONIC=str(begin),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',BLIS_NUM_THREADS='1')
   p=subprocess.run([str(H/'build/ccmckp_s10'),'--instance',str(H/'fixtures'/fixture),'--capacity',cap,'--seed','1010001','--seconds','60','--out',str(out),'--search-flow','budget_robust'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60,env=env);(H/('integration_'+fixture+'.log')).write_bytes(p.stdout)
   row={'name':'integration_'+fixture,'rc':p.returncode,'whole_seconds':time.monotonic()-begin,'tail':p.stdout.decode(errors='replace')[-1800:]};checks.append(row);assert p.returncode==0
  raw=json.loads((out/'S10_search.json').read_text());x=json.loads((out/'RESULT.json').read_text());cost=expected(H/'fixtures'/fixture,cap)
  assert abs(x['cost']-cost)<1e-10 and x['original_LSS_confidence']>=.99 and x['lss_sample_index_max']==499 and not x['real_probability_reporting']
  assert row['whole_seconds']<60 and raw['budget_RO_subproblems'] and not raw['DRO_model'] and not raw['DRO_transport_statistics']
  assert all(q['source'].startswith('R01_') for q in raw['candidate_shortlist'])
  row.update(cost=x['cost'],expected_RO_cost_by_independent_enumeration=cost,LSS=x['original_LSS_confidence'],budget_proposals=len(raw['budget_RO_proposals']),budget_subproblems=len(raw['budget_RO_subproblems']),native_infeasible=len(raw['native_infeasible_proofs']))
  if ordinal==1:assert row['native_infeasible']>0
 unchanged=['evaluation.cpp','evaluation.hpp','rng.cpp','rng.hpp','report.cpp','report.hpp','model.cpp','model.hpp','mip.cpp','mip.hpp','fft.hpp','partition.hpp','block_mitm.hpp','block_bounds.hpp','block_schedule.hpp','convolution_tree.hpp','winf_product.hpp','transport_cuts.hpp']
 for name in unchanged:assert (H/'source'/name).read_bytes()==(B/'work/d02_transport_cert_20261126/source'/name).read_bytes(),name
 v={'status':'PASS','checks':checks,'unchanged_bytes':unchanged,'reused_original_math_by_source_SHA':{'D01':632,'D02':173},'preparation_fixture_assumption_failure_retained':True,'successful_math_or_pipeline_not_repeated':True,'no_extra_native_probability_diagnostic':True,'binary_sha256':hashlib.sha256((H/'build/ccmckp_s10').read_bytes()).hexdigest(),'source_sha256':{p.relative_to(H/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'source').rglob('*') if p.is_file()}}
 (H/'VALIDATION.json').write_text(json.dumps(v,indent=2));print(json.dumps(v if False else {'status':'PASS','checks':checks,'binary_sha256':v['binary_sha256']}))
except BaseException as e:
 (H/('VALIDATION_FAILURE_%d.json'%len(list(H.glob('VALIDATION_FAILURE_*'))))).write_text(json.dumps({'error':repr(e),'checks':checks},indent=2));raise
