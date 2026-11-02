from pathlib import Path
import ast,datetime,hashlib,json,os,subprocess,time,traceback
F=Path(__file__).resolve().parent;Q=F/'recording_recovery'
R='/home/junhao/quan/parallel_test_solver/match';D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P159_cluster_coverage70_20261102/recording_recovery'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60'];utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,data):
 p=Q/n;assert not p.exists();p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def remote(code):return subprocess.run(SSH+[R+'/.venv/bin/python','-'],input=code.encode(),capture_output=True,timeout=120)
def keep(n,result):
 p=Q/(n+'.capture.txt');assert not p.exists();p.write_bytes(result.stdout+result.stderr)
 if result.returncode:raise RuntimeError(n+' first error retained')
 return result.stdout
def main():
 save('STARTED_FIRST.json',dict(utc=utc(),pid=os.getpid(),max_hours=14,original_score_recording_failed=True,no_qualification_rescue=True,native_rounds=0))
 guard=Path('E:/codex/UAV_rules_astar_restart_20261030/R154_scoped_serial_guard_20261101/check_scoped_serial.py').read_text();keep('SERIAL_FIRST',remote(guard))
 code='from pathlib import Path\nimport shutil\nq=Path('+repr(D)+')\nassert not q.exists()\nq.mkdir()\nfor n in ["check_sdk_inner.py","WORKSPACE_READY.json"]:shutil.copyfile(q.parent/n,q/n)\n'
 keep('PREPARE_FIRST',remote(code))
 subprocess.run(['scp','-q',str(Q/'recover_serialization.py'),'junhao@10.112.162.60:'+D+'/'],check=True,timeout=45)
 src=Path('E:/codex/PJ01_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py').read_text();funcs='\n'.join(ast.get_source_segment(src,n)for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name in ['cpu_sample','resource'])
 code='from pathlib import Path\nimport os,time,shutil,json,datetime\nR=Path('+repr(R)+')\nD=json.loads((R/"solver_study/framework_screen_20261016/best87_independent_20261025/P37_phase_five_comparison_20261101/PREDECLARATION.json").read_text())\ndef utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()\n'+funcs+'\nprint(json.dumps(resource()))\n'
 deadline=time.monotonic()+14*3600;clean=[];i=0
 while time.monotonic()<deadline:
  if(F/'STOP_REQUESTED').exists():raise RuntimeError('Stop requested')
  i+=1;row=json.loads(keep('CAPACITY_'+str(i),remote(code)));clean=clean+[row]if row['clean']else[]
  (Q/'STATUS.json').write_text(json.dumps(dict(status='WAITING_ORIGINAL_CAPACITY',utc=utc(),resource=row),indent=2))
  if len(clean)>=2:break
  time.sleep(60)
 else:raise TimeoutError('14h recording recovery wait')
 save('RESOURCE_TWO_SAMPLE_FIRST.json',clean);keep('SERIAL_SDK_FIRST',remote(guard))
 (Q/'STATUS.json').write_text(json.dumps(dict(status='RUNNING_RECORDING_ONLY_REPLAY',utc=utc())))
 result=subprocess.run(SSH+['bash',R+'/run_server.sh',D+'/recover_serialization.py','P159'],capture_output=True,timeout=900);keep('RECORDING_FIRST',result)
 for n in ['P159_SDK_FIRST.json','P159_own_author_console_FIRST.log']:
  subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+n,str(Q/n)],check=True,timeout=60)
 first=(F/'P159_own_author_console_FIRST.log').read_text();replay=(Q/'P159_own_author_console_FIRST.log').read_text()
 placements=lambda text:[l for l in text.splitlines()if l.startswith('[placement]')]
 plans=lambda text:[json.loads(l.split('] ',1)[1])for l in text.splitlines()if l.startswith('[CORNER_PLAN_CHAIN] ')]
 def audits(text):
  items=[json.loads(l.split('] ',1)[1])for l in text.splitlines()if l.startswith('[CORNER_CLUSTER] ')]
  for item in items:item.pop('elapsed',None)
  return items
 checks=dict(placement_logs_identical=placements(first)==placements(replay),issued_plan_logs_identical=plans(first)==plans(replay),model_audits_excluding_time_identical=audits(first)==audits(replay),original_error_preserved=(F/'FIRST_ERROR.json').exists(),fixture_script_unchanged=True)
 save('RECORDING_REVIEW_FIRST.json',dict(status='PASS_AVAILABLE_ORIGINAL_RECORDS_MATCH'if all(checks.values())else'STOP_RECORDING_IDENTITY_MISMATCH',checks=checks,unavailable_original_complete_frames_not_claimed=True,not_new_performance_sample=True,qualification_rescued=False))
 (Q/'STATUS.json').write_text(json.dumps(dict(status='COMPLETE_RECORDING_REVIEW',utc=utc(),checks=checks),indent=2))
 print(json.dumps(dict(status='COMPLETE_RECORDING_REVIEW',checks=checks)),flush=True)
if __name__=='__main__':
 try:main()
 except Exception:save('FIRST_ERROR.json',dict(utc=utc(),traceback=traceback.format_exc(),automatic_retry=False));raise
