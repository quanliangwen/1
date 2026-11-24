from pathlib import Path
import json,hashlib,time,subprocess,os,shutil,pickle
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_momentbound_600s_20261124';assert Path.cwd()==B
F=H/'fixtures/LAB_3_2_500_';results=[]
shutil.copytree(H/'fixtures/finite',H/'fixtures/priority')
(H/'fixtures/priority/1_sample.txt').write_text('20\n20.25\n')
rare=H/'fixtures/rare';rare.mkdir();(rare/'node_to_factor.pkl').write_bytes(pickle.dumps({0:[0,1]},protocol=4));(rare/'cost.txt').write_text('1\n2\n');(rare/'0_sample.txt').write_text('0\n'*99+'100\n');(rare/'1_sample.txt').write_text('0\n'*100)
def run(name,cmd,limit):
 start=time.monotonic();env=dict(os.environ,CCMCKP_LAUNCH_MONOTONIC=str(start))
 p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=limit)
 row={'name':name,'rc':p.returncode,'wall_seconds':time.monotonic()-start,'stdout':p.stdout.decode(errors='replace')[-3000:]}
 results.append(row);(H/(name+'.log')).write_bytes(p.stdout);assert p.returncode==0,row
 return row
try:
 run('necessary_moment_exact_and_real_MIQCP',[str(H/'build/moment_bound_test'),str(H/'fixtures/priority'),str(H/'fixtures/rare'),str(H/'fixtures/near')],120)
 for flow in ['ellipsoid_momentbound']:
  out=H/'clock_integration'/flow;start=time.monotonic()
  row=run('integration_'+flow,[str(H/'build/ccmckp_s10'),'--instance',str(F),'--capacity','.5','--seed','960001',
    '--seconds','30','--rep','1','--out',str(out),'--search-flow',flow],30)
  x=json.loads((out/'RESULT.json').read_text());completion=json.loads((out/'COMPLETION.json').read_text())
  assert row['wall_seconds']<30 and completion['elapsed_before_completion_save']<29
  assert x['clock_policy']=='launch_to_exit_total_wall' and x['original_LSS_confidence']>=.99
  assert x['cost']==3 and x['lss_sample_index_max']==499 and not x['real_probability_reporting']
  row.update({'cost':x['cost'],'LSS':x['original_LSS_confidence'],'total30s_pass':True,'completion':completion})
 data={'status':'PASS','new_checks':results,'reuse_unchanged_tests':{'CDF_and_FOSD':64,'cut_coverage':32,'reused_evaluator_clock_canonical_and_FOSD_files_same_bytes':True,'parent_protocol_sha256':'a827932b590e5fe62373d30c27792f23f27983bae07dba8860d34b0467f33934'},'not_a_benchmark_conclusion':True,
   'binary_sha256':hashlib.sha256((H/'build/ccmckp_s10').read_bytes()).hexdigest(),
   'source_sha256':{p.relative_to(H/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'source').rglob('*') if p.is_file()}}
except BaseException as error:
 name='VALIDATION_FAILURE_%s.json'%len(list(H.glob('VALIDATION_FAILURE*')))
 (H/name).write_text(json.dumps({'error':repr(error),'checks':results},indent=2));raise
(H/'VALIDATION.json').write_text(json.dumps(data,indent=2));print(json.dumps(data),flush=True)
