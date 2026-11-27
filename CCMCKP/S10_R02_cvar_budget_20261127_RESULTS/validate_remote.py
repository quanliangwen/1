from pathlib import Path
import json,hashlib,subprocess,os,time
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/r02_cvar_budget_20261127';assert Path.cwd()==B and not (H/'formal').exists()
checks=[]
def run(name,cmd,limit):
 begin=time.monotonic();env=dict(os.environ,CCMCKP_LAUNCH_MONOTONIC=str(begin),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',BLIS_NUM_THREADS='1')
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=limit,env=env);(H/(name+'.log')).write_bytes(p.stdout)
 row={'name':name,'rc':p.returncode,'whole_seconds':time.monotonic()-begin,'tail':p.stdout.decode(errors='replace')[-2000:]};checks.append(row);print(json.dumps(row),flush=True);assert p.returncode==0,row
 return row
try:
 previous=(H/'calibrated_math_debug.log').read_text().splitlines()
 result=next((json.loads(x) for x in previous if x.startswith('{') and '"status":"PASS"' in x),None)
 assert result and result['checks']>0
 checks.append({'name':'calibrated_math','rc':0,'source':'same frozen bytes successful debug run; not repeated','result':result})
 for fixture,cap,cost in [('LAB_3_2_500_','.5',3),('LAB_2_2_500_','1.25',4)]:
  out=H/'integration60'/fixture;assert not out.exists()
  row=run('integration_'+fixture,[str(H/'build/ccmckp_s10'),'--instance',str(H/'fixtures'/fixture),'--capacity',cap,'--seed','1020001','--seconds','60','--out',str(out),'--search-flow','cvar_budget_calibrated'],60)
  raw=json.loads((out/'S10_search.json').read_text());x=json.loads((out/'RESULT.json').read_text())
  assert abs(x['cost']-cost)<1e-10 and x['original_LSS_confidence']>=.99 and x['lss_sample_index_max']==499 and not x['real_probability_reporting']
  assert row['whole_seconds']<60 and raw['adaptive_RO_model'] and not raw['DRO_model'] and not raw['budget_RO_model']
  assert raw['adaptive_RO_queries'] and raw['adaptive_RO_statistics']['no_LSS_calls_in_generator']
  assert all(q['source'].startswith('R02_') for q in raw['candidate_shortlist'])
  assert not x['stage4_lss_final']['generator_observed_LSS']
  row.update(cost=x['cost'],LSS=x['original_LSS_confidence'],proposals=len(raw['adaptive_RO_proposals']),queries=len(raw['adaptive_RO_queries']))
 unchanged=['evaluation.cpp','evaluation.hpp','rng.cpp','rng.hpp','report.cpp','report.hpp','model.cpp','model.hpp','mip.cpp','mip.hpp','fft.hpp','partition.hpp','block_mitm.hpp','block_bounds.hpp','block_schedule.hpp','convolution_tree.hpp','winf_product.hpp','transport_cuts.hpp','budget_ro.hpp']
 for name in unchanged:assert (H/'source'/name).read_bytes()==(B/'work/r01_budget_robust_20261126/source'/name).read_bytes(),name
 old=(B/'work/r01_budget_robust_20261126/source/search.cpp').read_text();new=(H/'source/search.cpp').read_text()
 for begin,end in [('double Search::native_check','\n}',),('Json Search::shortlist','\n}',)]:
  def span(s):i=s.index(begin);return s[i:s.index(end,i)+len(end)]
  assert span(old)==span(new),begin
 v={'status':'PASS','checks':checks,'unchanged_bytes':unchanged,'reused_math_by_source_SHA':{'R01':421,'D01':632,'D02':173},'no_extra_native_probability_diagnostic':True,'binary_sha256':hashlib.sha256((H/'build/ccmckp_s10').read_bytes()).hexdigest(),'source_sha256':{p.relative_to(H/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'source').rglob('*') if p.is_file()}}
 (H/'VALIDATION.json').write_text(json.dumps(v,indent=2));print(json.dumps(v))
except BaseException as e:
 (H/('VALIDATION_FAILURE_%d.json'%len(list(H.glob('VALIDATION_FAILURE_*'))))).write_text(json.dumps({'error':repr(e),'checks':checks},indent=2));raise
