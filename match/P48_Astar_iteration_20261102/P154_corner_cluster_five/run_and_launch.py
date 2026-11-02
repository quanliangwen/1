from pathlib import Path
import ast,json,subprocess,time,datetime,traceback,sys,os
F=Path(__file__).resolve().parent;R='/home/junhao/quan/parallel_test_solver/match';D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P154_corner_cluster_five_20261102';ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60'];utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def remote(code):return subprocess.run(ssh+[R+'/.venv/bin/python','-'],input=code.encode(),capture_output=True)
def keep(name,p):
 path=F/(name+'.log');assert not path.exists();path.write_bytes(p.stdout+p.stderr);print(p.stdout.decode(errors='replace')[-1400:],flush=True)
 if p.returncode:raise RuntimeError('First error preserved: '+name)
def fetch(name):subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+name,str(F/name)],check=True)
def main():
 assert not(F/'QUALIFICATION_STARTED_FIRST.json').exists();assert json.loads((F/'CORNER_CONTRACT_V2_FIRST.json').read_text())['status'].startswith('PASS')
 (F/'QUALIFICATION_STARTED_FIRST.json').write_text(json.dumps(dict(utc=utc(),pid=os.getpid(),scope='Only finite explicit A* five-map request; old iteration stays paused'),indent=2)+'\n')
 guard=(F/'check_scoped_serial.py').read_text();keep('BEFORE_ENTRY_SERIAL_FIRST',remote(guard))
 for name in ['prepare_workspace.py','check_sdk_actual_zip_entry.py','run_offline.py','declare_native.py','launch_campaign.py','check_scoped_serial.py','TEST_PROTOCOL.json','CORNER_CONTRACT_V2_FIRST.json','BASELINE_REFERENCE.json']:
  p=F/name
  if p.suffix=='.py':ast.parse(p.read_text())
  subprocess.run(['scp','-q',str(p),'junhao@10.112.162.60:'+D+'/'],check=True)
 subprocess.run(['scp','-q','E:/codex/UAV_rules_astar_restart_20261030/run_sdk_captured.py','junhao@10.112.162.60:'+D+'/'],check=True)
 keep('WORKSPACE_FIRST',subprocess.run(ssh+[R+'/.venv/bin/python',D+'/prepare_workspace.py'],capture_output=True));fetch('WORKSPACE_READY.json');fetch('INTERNAL_ZIP_BINDING.json')
 src=Path('E:/codex/PJ01_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py').read_text();methods='\n'.join(ast.get_source_segment(src,n)for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name in ['cpu_sample','resource'])
 code='from pathlib import Path\nimport os,time,shutil,json,datetime\nR=Path('+repr(R)+')\nD=json.loads((R/"solver_study/framework_screen_20261016/best87_independent_20261025/P37_phase_five_comparison_20261101/PREDECLARATION.json").read_text())\ndef utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()\n'+methods+'\nprint(json.dumps(resource()))\n'
 n=0;consecutive=[];deadline=time.monotonic()+14*3600
 while time.monotonic()<deadline:
  if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop')
  n+=1;p=remote(code);keep('ENTRY_CAPACITY_'+str(n),p);r=json.loads(p.stdout);consecutive=consecutive+[r]if r['clean']else[]
  (F/'QUALIFICATION_STATUS.json').write_text(json.dumps(dict(utc=utc(),status='WAITING_ORIGINAL_CAPACITY_FOR_ENTRY',resource=r),indent=2)+'\n')
  if len(consecutive)>=2:break
  time.sleep(60)
 else:raise TimeoutError('Finite14h entry wait')
 (F/'ENTRY_RESOURCE_TWO_SAMPLE.json').write_text(json.dumps(consecutive,indent=2)+'\n');keep('ENTRY_SERIAL_FIRST',remote(guard))
 keep('ENTRY_ACTUAL_ZIP_FIRST',subprocess.run(ssh+[R+'/.venv/bin/python',D+'/run_sdk_captured.py',D+'/check_sdk_actual_zip_entry.py','ENTRY_ACTUAL_ZIP_FIRST','P154_CORNER_ASTAR'],capture_output=True));fetch('ENTRY_ACTUAL_ZIP_FIRST.json')
 keep('FROZEN_PREFLIGHT_FIRST',subprocess.run(ssh+[R+'/.venv/bin/python',D+'/declare_native.py'],capture_output=True));fetch('PREDECLARATION.json');fetch('versions/P154_CORNER_ASTAR/QUALIFICATION.json')
 if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop before test')
 keep('BEFORE_NATIVE_SERIAL_FIRST',remote(guard));subprocess.run([sys.executable,'-X','utf8',str(F/'start_local_collector.py')],check=True)
 keep('NATIVE_LAUNCH_FIRST',subprocess.run(ssh+[R+'/.venv/bin/python',D+'/launch_campaign.py'],capture_output=True));fetch('LAUNCH.json')
 (F/'QUALIFICATION_STATUS.json').write_text(json.dumps(dict(utc=utc(),status='QUALIFIED_AND_FINITE_FIVE_MAP_COORDINATOR_LAUNCHED',old_iteration_remains_paused=True,max_native_rounds=10),indent=2)+'\n')
if __name__=='__main__':
 try:main()
 except Exception:
  (F/'QUALIFICATION_FIRST_ERROR.json').write_text(json.dumps(dict(utc=utc(),traceback=traceback.format_exc(),no_automatic_retry=True),indent=2)+'\n');raise
