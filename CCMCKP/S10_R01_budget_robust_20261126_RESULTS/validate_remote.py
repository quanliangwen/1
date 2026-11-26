from pathlib import Path
import json,hashlib,subprocess,os,time
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/r01_budget_robust_20261126';assert Path.cwd()==B and not (H/'formal').exists()
checks=[]
def run(name,cmd,limit):
 begin=time.monotonic();env=dict(os.environ,CCMCKP_LAUNCH_MONOTONIC=str(begin),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',BLIS_NUM_THREADS='1')
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=limit,env=env);(H/(name+'.log')).write_bytes(p.stdout)
 row={'name':name,'rc':p.returncode,'whole_seconds':time.monotonic()-begin,'tail':p.stdout.decode(errors='replace')[-1800:]};checks.append(row);print(json.dumps(row),flush=True);assert p.returncode==0,row
 return row
try:
 run('budget_math',[str(H/'build/budget_ro_test'),str(H/'fixtures/budget_tiny')],90)
 for fixture,cap,cost in [('LAB_3_2_500_','.5',3),('LAB_2_2_500_','1.25',4)]:
  out=H/'integration60'/fixture;assert not out.exists()
  row=run('integration_'+fixture,[str(H/'build/ccmckp_s10'),'--instance',str(H/'fixtures'/fixture),'--capacity',cap,'--seed','1010001','--seconds','60','--out',str(out),'--search-flow','budget_robust'],60)
  raw=json.loads((out/'S10_search.json').read_text());x=json.loads((out/'RESULT.json').read_text())
  assert abs(x['cost']-cost)<1e-10 and x['original_LSS_confidence']>=.99 and x['lss_sample_index_max']==499 and not x['real_probability_reporting']
  assert row['whole_seconds']<60 and raw['budget_RO_model'] and not raw['DRO_model'] and not raw['DRO_transport_statistics']
  assert raw['budget_RO_subproblems'] and raw['budget_RO_statistics']['no_LSS_calls_in_generator']
  assert all(q['source'].startswith('R01_') for q in raw['candidate_shortlist'])
  row.update(cost=x['cost'],LSS=x['original_LSS_confidence'],budget_proposals=len(raw['budget_RO_proposals']),budget_subproblems=len(raw['budget_RO_subproblems']),native_infeasible=len(raw['native_infeasible_proofs']))
  if fixture=='LAB_2_2_500_':assert row['native_infeasible']>0
 unchanged=['evaluation.cpp','evaluation.hpp','rng.cpp','rng.hpp','report.cpp','report.hpp','model.cpp','model.hpp','mip.cpp','mip.hpp','fft.hpp','partition.hpp','block_mitm.hpp','block_bounds.hpp','block_schedule.hpp','convolution_tree.hpp','winf_product.hpp','transport_cuts.hpp']
 for name in unchanged:assert (H/'source'/name).read_bytes()==(B/'work/d02_transport_cert_20261126/source'/name).read_bytes(),name
 v={'status':'PASS','checks':checks,'unchanged_bytes':unchanged,'reused_original_math_by_source_SHA':{'D01':632,'D02':173},'no_extra_native_probability_diagnostic':True,'binary_sha256':hashlib.sha256((H/'build/ccmckp_s10').read_bytes()).hexdigest(),'source_sha256':{p.relative_to(H/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'source').rglob('*') if p.is_file()}}
 (H/'VALIDATION.json').write_text(json.dumps(v,indent=2));print(json.dumps({'status':'PASS','checks':checks,'binary_sha256':v['binary_sha256']}))
except BaseException as e:
 (H/('VALIDATION_FAILURE_%d.json'%len(list(H.glob('VALIDATION_FAILURE_*'))))).write_text(json.dumps({'error':repr(e),'checks':checks},indent=2));raise
