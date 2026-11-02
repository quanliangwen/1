from pathlib import Path
import subprocess,json,ast,time,datetime,traceback
F=Path(__file__).resolve().parent;A=F/'audit';R='/home/junhao/quan/parallel_test_solver/match';D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P48_v09_release_validation_20261102';ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60'];utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def remote(code):return subprocess.run(ssh+[R+'/.venv/bin/python','-'],input=code.encode(),capture_output=True)
def keep(label,p):
 f=A/(label+'.log');assert not f.exists();f.write_bytes(p.stdout+p.stderr);print(p.stdout.decode(errors='replace')[-1000:],flush=True)
 if p.returncode:raise RuntimeError('Preserve validation V2 first error '+label)
def main():
 assert not(A/'V2_STARTED_FIRST.json').exists();assert(A/'PROBE_FIRST_COMPILE_ERROR.json').exists()
 for n in ['probe_actual_v09_v2.py','invoke_probe_v2.py','check_official_static.py']:ast.parse((F/n).read_text());subprocess.run(['scp','-q',str(F/n),'junhao@10.112.162.60:'+D+'/'],check=True)
 (A/'V2_STARTED_FIRST.json').write_text(json.dumps(dict(utc=utc(),reason='Fix probe lexical compile error only, reuse untouched new isolated environments; package/core frozen',new_game_rounds=0),indent=2)+'\n')
 guard=Path('E:/codex/UAV_rules_astar_restart_20261030/R154_scoped_serial_guard_20261101/check_scoped_serial.py').read_text();keep('V2_SERIAL',remote(guard))
 src=Path('E:/codex/PJ01_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py').read_text();methods='\n'.join(ast.get_source_segment(src,n)for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name in ['cpu_sample','resource'])
 code='from pathlib import Path\nimport os,time,shutil,json,datetime\nR=Path('+repr(R)+')\nD=json.loads((R/"solver_study/framework_screen_20261016/best87_independent_20261025/P37_phase_five_comparison_20261101/PREDECLARATION.json").read_text())\ndef utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()\n'+methods+'\nprint(json.dumps(resource()))\n'
 n=0;consecutive=[];deadline=time.monotonic()+3600
 while time.monotonic()<deadline:
  n+=1;p=remote(code);keep('V2_CAPACITY_'+str(n),p);r=json.loads(p.stdout);consecutive=consecutive+[r]if r['clean']else[]
  (A/'STATUS.json').write_text(json.dumps(dict(utc=utc(),status='WAITING_V2_RELEASE_STARTUP_CAPACITY',resource=r),indent=2)+'\n')
  if len(consecutive)>=2:break
  time.sleep(60)
 else:raise TimeoutError('One-hour validation resource wait')
 (A/'V2_RESOURCE_TWO_SAMPLE.json').write_text(json.dumps(consecutive,indent=2)+'\n');keep('V2_BEFORE_STARTUP_SERIAL',remote(guard))
 for label in ['numpy1','numpy2','native_main']:
  python=R+'/.venv/bin/python'if label=='native_main'else D+'/env_'+label+'/bin/python'
  keep('V2_PROBE_'+label,subprocess.run(ssh+['bash',R+'/run_server.sh',D+'/invoke_probe_v2.py',label,python],capture_output=True))
  for file in ['ABI_'+label+'.json','INSTALL_DRY_RUN_'+label+'.log']:
   subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+file,str(A/file)],check=True)
 keep('V2_OFFICIAL_STATIC',subprocess.run(ssh+[R+'/.venv/bin/python',D+'/check_official_static.py'],capture_output=True));subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/OFFICIAL_STATIC_CHECK.json',str(A/'OFFICIAL_STATIC_CHECK.json')],check=True)
 (A/'STATUS.json').write_text(json.dumps(dict(utc=utc(),status='ABI_AND_OFFICIAL_STATIC_PASSED_FINAL_GUARD_PENDING',new_game_rounds=0,algorithm_iteration_remains_paused=True),indent=2)+'\n')
if __name__=='__main__':
 try:main()
 except Exception:
  (A/'V2_FIRST_VALIDATION_ERROR.json').write_text(json.dumps(dict(utc=utc(),traceback=traceback.format_exc()),indent=2)+'\n');raise
