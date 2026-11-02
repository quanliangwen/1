from pathlib import Path
import json,subprocess,hashlib,ast,time,datetime,os,traceback,concurrent.futures
F=Path(__file__).resolve().parent;A=F/'audit';R='/home/junhao/quan/parallel_test_solver/match';H=R+'/solver_study/framework_screen_20261016/best87_independent_20261025';D=H+'/P48_v09_release_validation_20261102';ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60'];utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def remote(code):return subprocess.run(ssh+[R+'/.venv/bin/python','-'],input=code.encode(),capture_output=True)
def keep(label,p):
 path=A/(label+'.log');assert not path.exists();path.write_bytes(p.stdout+p.stderr);print(p.stdout.decode(errors='replace')[-1000:],flush=True)
 if p.returncode:raise RuntimeError('Keep first validation error '+label)
def main():
 assert not(A/'STARTED_FIRST.json').exists();(A/'STARTED_FIRST.json').write_text(json.dumps(dict(utc=utc(),pid=os.getpid(),purpose='P48_V09_PACKAGING_VALIDATION_ONLY',algorithm_iteration_remains_paused=True,new_game_rounds=0),indent=2)+'\n')
 guard=Path('E:/codex/UAV_rules_astar_restart_20261030/R154_scoped_serial_guard_20261101/check_scoped_serial.py').read_text();keep('SERIAL_FIRST',remote(guard))
 keep('MKDIR_FIRST',remote('from pathlib import Path\np=Path('+repr(D)+')\nassert not p.exists()\np.mkdir()\n'))
 for p in [F/'team615_red_v09.zip',F/'BUILD.json',F/'prepare_server.py',F/'probe_actual_v09.py',F/'invoke_probe.py']:subprocess.run(['scp','-q',str(p),'junhao@10.112.162.60:'+D+'/'],check=True)
 keep('WORKSPACE_FIRST',subprocess.run(ssh+[R+'/.venv/bin/python',D+'/prepare_server.py'],capture_output=True))
 for label in ['numpy1','numpy2']:
  code='import subprocess\nsubprocess.run('+repr([R+'/.venv/bin/python','-m','venv',D+'/env_'+label])+',check=True)\n'
  keep('CREATE_'+label,remote(code))
 def install(label):
  version='1.26.4'if label=='numpy1'else'2.2.6'
  command=[D+'/env_'+label+'/bin/python','-m','pip','--isolated','install','--index-url','https://pypi.org/simple','--only-binary=:all:','numpy=='+version,'pandas==2.2.3','opencv-contrib-python==4.11.0.86']
  return label,subprocess.run(ssh+command,capture_output=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  results=list(pool.map(install,['numpy1','numpy2']))
 for label,p in results:keep('INSTALL_'+label,p)
 # Same original resource conditions before even isolated SDK constructors.
 src=Path('E:/codex/PJ01_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py').read_text();methods='\n'.join(ast.get_source_segment(src,n)for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name in ['cpu_sample','resource'])
 code='from pathlib import Path\nimport os,time,shutil,json,datetime\nR=Path('+repr(R)+')\nD=json.loads((R/"solver_study/framework_screen_20261016/best87_independent_20261025/P37_phase_five_comparison_20261101/PREDECLARATION.json").read_text())\ndef utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()\n'+methods+'\nprint(json.dumps(resource()))\n'
 consecutive=[];deadline=time.monotonic()+3600;n=0
 while time.monotonic()<deadline:
  n+=1;p=remote(code);keep('CAPACITY_'+str(n),p);r=json.loads(p.stdout);consecutive=consecutive+[r]if r['clean']else[]
  (A/'STATUS.json').write_text(json.dumps(dict(utc=utc(),status='WAITING_RELEASE_STARTUP_CAPACITY',resource=r),indent=2)+'\n')
  if len(consecutive)>=2:break
  time.sleep(60)
 else:raise TimeoutError('One-hour startup validation resource wait')
 (A/'RESOURCE_TWO_SAMPLE.json').write_text(json.dumps(consecutive,indent=2)+'\n');keep('BEFORE_STARTUP_SERIAL',remote(guard))
 for label in ['numpy1','numpy2','native_main']:
  python=R+'/.venv/bin/python'if label=='native_main'else D+'/env_'+label+'/bin/python'
  keep('PROBE_'+label,subprocess.run(ssh+['bash',R+'/run_server.sh',D+'/invoke_probe.py',label,python],capture_output=True))
  subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/ABI_'+label+'.json',str(A/('ABI_'+label+'.json'))],check=True)
  subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/INSTALL_DRY_RUN_'+label+'.log',str(A/('INSTALL_DRY_RUN_'+label+'.log'))],check=True)
 keep('OFFICIAL_STATIC',remote('from pathlib import Path\nimport sys,json,hashlib,shutil\nF=Path('+repr(D)+')\nW=Path(json.loads((F/"WORKSPACE_READY.json").read_text())["workspace"])\nsys.path.insert(0,str(W/"src"))\nfrom swarm_rescue.submission_check import validate_submission\nz=F/"team615_red_v09.zip"\na=F/"team615_preliminary.zip"\nassert not a.exists()\nshutil.copyfile(z,a)\nr=validate_submission(a)\nprint(r)\nassert not r.errors,r.errors\nsha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()\nout=dict(status="PASS",submission_zip_sha256=sha(z),alias_sha256=sha(a),alias_name=a.name,errors=r.errors,warnings=r.warnings,official_checker_path=str(W/"src/swarm_rescue/submission_check.py"))\n(F/"OFFICIAL_STATIC_CHECK.json").write_text(json.dumps(out,indent=2)+"\\n")\n'))
 subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/OFFICIAL_STATIC_CHECK.json',str(A/'OFFICIAL_STATIC_CHECK.json')],check=True)
 (A/'STATUS.json').write_text(json.dumps(dict(utc=utc(),status='ABI_AND_OFFICIAL_STATIC_PASSED_FINAL_GUARD_PENDING',new_game_rounds=0,algorithm_iteration_remains_paused=True),indent=2)+'\n')
if __name__=='__main__':
 try:main()
 except Exception:
  (A/'FIRST_VALIDATION_ERROR.json').write_text(json.dumps(dict(utc=utc(),traceback=traceback.format_exc()),indent=2)+'\n');raise
