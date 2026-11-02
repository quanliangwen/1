"""Finite paired author SDK experiment; never start native or five-map jobs."""
from pathlib import Path
import ast,datetime,hashlib,json,os,subprocess,time,traceback
F=Path(__file__).resolve().parent
R='/home/junhao/quan/parallel_test_solver/match';D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P158_cluster_coverage_bound_20261102'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60']
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def save(n,d,first=True):
 p=F/n
 if first:assert not p.exists(),p
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def remote(code):return subprocess.run(SSH+[R+'/.venv/bin/python','-'],input=code.encode(),capture_output=True,timeout=120)
def keep(n,p):
 dest=F/(n+'.capture.txt');assert not dest.exists();dest.write_bytes(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError('First error retained '+n)
 return p.stdout
def main():
 assert not(F/'STARTED_FIRST.json').exists()
 save('STARTED_FIRST.json',dict(utc=utc(),pid=os.getpid(),max_hours=14,SDK_max_arms=2,native_rounds=0))
 pre=read(F/'PREDECLARATION_FIRST.json')
 assert hashlib.sha256((F/'check_sdk_observer.py').read_bytes()).hexdigest()==pre['SDK_script_sha256']
 guard=Path('E:/codex/UAV_rules_astar_restart_20261030/R154_scoped_serial_guard_20261101/check_scoped_serial.py').read_text()
 keep('SERIAL_PREPARE_FIRST',remote(guard))
 subprocess.run(['scp','-q',str(F/'check_sdk_observer.py'),'junhao@10.112.162.60:'+D+'/'],check=True,timeout=45)
 keep('WORKSPACE_BINDING_FIRST',remote("from pathlib import Path\nimport shutil\ns=Path("+repr(R+"/solver_study/framework_screen_20261016/best87_independent_20261025/P157_inner_corner_free_quadrants_20261102/WORKSPACE_READY.json")+")\nd=Path("+repr(D+"/WORKSPACE_READY.json")+")\nassert not d.exists()\nshutil.copyfile(s,d)\n"))
 src=Path('E:/codex/PJ01_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py').read_text()
 funcs='\n'.join(ast.get_source_segment(src,n)for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name in ['cpu_sample','resource'])
 code='from pathlib import Path\nimport os,time,shutil,json,datetime\nR=Path('+repr(R)+')\nD=json.loads((R/"solver_study/framework_screen_20261016/best87_independent_20261025/P37_phase_five_comparison_20261101/PREDECLARATION.json").read_text())\ndef utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()\n'+funcs+'\nprint(json.dumps(resource()))\n'
 deadline=time.monotonic()+14*3600
 for arm in ['P157']:
  clean=[];i=0
  while time.monotonic()<deadline:
   if(F/'STOP_REQUESTED').exists():raise RuntimeError('Stop requested')
   i+=1;row=json.loads(keep(arm+'_CAPACITY_'+str(i),remote(code)))
   clean=clean+[row]if row['clean']else[]
   save('STATUS.json',dict(status='WAITING_ORIGINAL_CAPACITY',arm=arm,utc=utc(),resource=row),False)
   if len(clean)>=2:break
   time.sleep(60)
  else:raise TimeoutError('Finite 14h wait')
  keep(arm+'_SERIAL_FIRST',remote(guard))
  save(arm+'_RESOURCE_TWO_SAMPLE.json',clean)
  save('STATUS.json',dict(status='RUNNING_AUTHOR_SDK',arm=arm,utc=utc(),native_rounds=0),False)
  p=subprocess.run(SSH+['bash',R+'/run_server.sh',D+'/check_sdk_observer.py',arm],capture_output=True,timeout=900)
  keep(arm+'_SDK_FIRST',p)
  for n in [arm+'_SDK_FIRST.json',arm+'_own_author_console_FIRST.log']:
   subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+n,str(F/n)],check=True,timeout=60)
 expected=read(Path(pre['expected_result']));observed=read(F/'P157_SDK_FIRST.json')
 checks=dict(rows_identical=expected['rows']==observed['rows'],scores_identical=expected['scores']==observed['scores'],actual_bombs_identical=expected['actual_bombs']==observed['actual_bombs'],source_identical=expected['source_sha256']==observed['source_sha256'],SDK_identical=expected['SDK_sha256']==observed['SDK_sha256'],submission_identical=expected['submitted']==observed['submitted'],first_actual_model_captured=len(observed.get('model_snapshots',[]))==1)
 result=dict(status='PASS_READONLY_OBSERVATION_IDENTITY'if all(checks.values())else'STOP_READONLY_IDENTITY_MISMATCH',checks=checks,physics_steps=observed['physics_steps'],new_native_rounds=0,new_performance_score=False,snapshots=observed.get('model_snapshots',[]))
 save('RESULT_FIRST.json',result);save('STATUS.json',dict(status=result['status'],utc=utc()),False)
 print(json.dumps(dict(status=result['status'],checks=checks)))
if __name__=='__main__':
 try:main()
 except Exception:
  save('FIRST_ERROR.json',dict(utc=utc(),traceback=traceback.format_exc(),automatic_retry=False));save('STATUS.json',dict(status='STOP_FIRST_SMALL_TEST_ERROR',utc=utc()),False);raise
