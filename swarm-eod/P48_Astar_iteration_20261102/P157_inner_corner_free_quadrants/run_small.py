"""Finite paired author SDK experiment; never start native or five-map jobs."""
from pathlib import Path
import ast,datetime,hashlib,json,os,subprocess,time,traceback
F=Path(__file__).resolve().parent
R='/home/junhao/quan/parallel_test_solver/match';D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P157_inner_corner_free_quadrants_20261102'
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
 assert hashlib.sha256((F/'check_sdk_inner.py').read_bytes()).hexdigest()==pre['SDK_script_sha256']
 guard=Path('E:/codex/UAV_rules_astar_restart_20261030/R154_scoped_serial_guard_20261101/check_scoped_serial.py').read_text()
 keep('SERIAL_PREPARE_FIRST',remote(guard))
 subprocess.run(['scp','-q',str(F/'BASE_WORKSPACE.json'),str(F/'prepare_sdk_workspace.py'),str(F/'check_sdk_inner.py'),'junhao@10.112.162.60:'+D+'/'],check=True,timeout=45)
 keep('WORKSPACE_FIRST',subprocess.run(SSH+[R+'/.venv/bin/python',D+'/prepare_sdk_workspace.py'],capture_output=True,timeout=120))
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
  p=subprocess.run(SSH+['bash',R+'/run_server.sh',D+'/check_sdk_inner.py',arm],capture_output=True,timeout=900)
  keep(arm+'_SDK_FIRST',p)
  for n in [arm+'_SDK_FIRST.json',arm+'_own_author_console_FIRST.log']:
   subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+n,str(F/n)],check=True,timeout=60)
 a=read(F.parent/'P156_fixed_quota_inner_corner/P48_ASTAR_SDK_FIRST.json');b=read(F/'P157_SDK_FIRST.json');sa=a['scores'];sb=b['scores']
 cluster=max((e['physical_strict']for e in b['concentration']),default=0)
 checks=dict(actual_cluster6=cluster>=6,fixed_quota_recorded=bool(b['accepted'])and all(e['audit']['fixed_target']==6 for e in b['accepted']),all10=b['placed']==10,
   official_callbacks=a['official_callbacks']and b['official_callbacks'],finite=a['numeric_finite']and b['numeric_finite'],
   no_added_total_damage=sum(b['health_min'])>=sum(a['health_min']),actual_loop_under90=a['elapsed_seconds']<90 and b['elapsed_seconds']<90,
   submitted=sb['map_raw']is not None,map_loss_at_most_half_pp=sb['map_raw']is not None and sa['map_raw']is not None and sb['map_raw']>=sa['map_raw']-.5,
   wall_retained90=sb['wall_raw']>=.9*sa['wall_raw'],time_nonregress=sb['time_raw']>=sa['time_raw'],
   controllable_loss_at_most_half_point=sb['controllable_subtotal']is not None and sa['controllable_subtotal']is not None and sb['controllable_subtotal']>=sa['controllable_subtotal']-.5)
 deltas={k:None if sa[k]is None or sb[k]is None else sb[k]-sa[k]for k in ['map_raw','wall_raw','time_raw','layout_raw','map_weighted','wall_weighted','time_weighted','layout_weighted','controllable_subtotal','full_red_score']}
 result=dict(status='PASS_AUTHOR_CONCENTRATION_AND_COVERAGE_GATE'if all(checks.values())else'STOP_FIRST_AUTHOR_MECHANISM_GATE',checks=checks,baseline=sa,candidate=sb,deltas=deltas,baseline_placed=a['placed'],candidate_placed=b['placed'],baseline_steps=a['physics_steps'],candidate_steps=b['physics_steps'],baseline_health=a['health_min'],candidate_health=b['health_min'],actual_max_cluster=cluster,concentration=b['concentration'],native_rounds=0,automatic_five=False,automatic_native=False,scope='Same authored physical arena/seed, no BLUE: only controllable subtotal, not a full red score or five-map improvement.')
 save('RESULT_FIRST.json',result);save('STATUS.json',dict(status=result['status'],utc=utc(),native_rounds=0),False)
 print(json.dumps(dict(status=result['status'],checks=checks,baseline=sa,candidate=sb),ensure_ascii=False),flush=True)
if __name__=='__main__':
 try:main()
 except Exception:
  save('FIRST_ERROR.json',dict(utc=utc(),traceback=traceback.format_exc(),automatic_retry=False));save('STATUS.json',dict(status='STOP_FIRST_SMALL_TEST_ERROR',utc=utc()),False);raise
