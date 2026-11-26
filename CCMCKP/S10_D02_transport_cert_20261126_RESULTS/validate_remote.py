from pathlib import Path
import json,hashlib,subprocess,os,time
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/d02_transport_cert_20261126';assert Path.cwd()==B and not (H/'formal').exists()
checks=[]
def run(name,cmd,seconds):
 begin=time.monotonic();env=dict(os.environ,CCMCKP_LAUNCH_MONOTONIC=str(begin),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',BLIS_NUM_THREADS='1')
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds,env=env);(H/(name+'.log')).write_bytes(p.stdout)
 row={'name':name,'rc':p.returncode,'whole_seconds':time.monotonic()-begin,'tail':p.stdout.decode(errors='replace')[-1500:]};checks.append(row);print(json.dumps(row),flush=True);assert p.returncode==0,row
 return row
try:
 mathrow=run('transport_math',[str(H/'build/transport_cuts_test'),str(H/'fixtures/winf'),str(H/'fixtures/compensating'),str(H/'fixtures/crossing'),str(H/'fixtures/overflow')],60)
 for flow in ['block_mitm','block_winf_dro','block_winf_transport']:
  out=H/'integration60'/flow;assert not out.exists()
  row=run('integration_'+flow,[str(H/'build/ccmckp_s10'),'--instance',str(H/'fixtures/LAB_3_2_500_'),'--capacity','.5','--seed','1000001','--seconds','60','--out',str(out),'--search-flow',flow],60)
  raw=json.loads((out/'S10_search.json').read_text());x=json.loads((out/'RESULT.json').read_text())
  assert x['cost']==3 and x['original_LSS_confidence']>=.99 and x['lss_sample_index_max']==499 and not x['real_probability_reporting']
  assert row['whole_seconds']<60 and raw['block_history'] and any('pairs' in q for q in raw['block_history'])
  assert bool(raw['DRO_model'])==(flow!='block_mitm')
  if flow=='block_winf_transport':
   st=raw['DRO_transport_statistics'];assert st['queries']>0 and st['native_witnesses_added']>0
   assert st['excluded']==len(raw['DRO_transport_prunes']) and st['maximum_bank_size']<=128
   assert st['feasible_certificate_reuse'] is False and st['model_unchanged_from_D01'] and st['current_run_native_witnesses_only']
   row['transport']=st
  else:assert raw['DRO_transport_statistics'] is None and raw['DRO_transport_prunes']==[]
  row.update(cost=x['cost'],LSS=x['original_LSS_confidence'],block_records=len(raw['block_history']))
 unchanged=['evaluation.cpp','evaluation.hpp','rng.cpp','rng.hpp','report.cpp','report.hpp','model.cpp','model.hpp','mip.cpp','mip.hpp','fft.hpp','partition.hpp','block_mitm.hpp','block_bounds.hpp','block_schedule.hpp','convolution_tree.hpp','winf_product.hpp']
 for name in unchanged:assert (H/'source'/name).read_bytes()==(B/'work/d01_winf_product_20261126/source'/name).read_bytes(),name
 v={'status':'PASS','checks':checks,'unchanged_bytes':unchanged,'reused_D01_math_checks_by_identical_source':632,'no_extra_native_probability_diagnostic':True,'binary_sha256':hashlib.sha256((H/'build/ccmckp_s10').read_bytes()).hexdigest(),'source_sha256':{p.relative_to(H/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'source').rglob('*') if p.is_file()}}
 (H/'VALIDATION.json').write_text(json.dumps(v,indent=2));print(json.dumps({'status':'PASS','checks':checks,'binary_sha256':v['binary_sha256']}))
except BaseException as e:
 (H/('VALIDATION_FAILURE_%d.json'%len(list(H.glob('VALIDATION_FAILURE_*'))))).write_text(json.dumps({'error':repr(e),'checks':checks},indent=2));raise
