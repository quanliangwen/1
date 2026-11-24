from pathlib import Path
import json,hashlib,ast,base64
R=Path(__file__).resolve().parent;OLD=Path('E:/codex/S10_EGS_LSS_3large_60w_20261124')
c=(OLD/'controller.py').read_text()
c=c.replace('import time','import time\nimport threading')
c=c.replace("elapsed=time.monotonic()-item['started']","elapsed=item.get('exited_monotonic',time.monotonic())-item['started']")
c=c.replace("if rc is not None:","if rc is not None and 'exited_monotonic' in item:")
c=c.replace("'termination_reason':item.get('termination_reason'),'output_files':{}", "'termination_reason':item.get('termination_reason'),'wall_clock_source':'dedicated_wait_thread_from_before_Popen','output_files':{}")
old="""                process=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                    start_new_session=True,cwd=str(H))"""
new="""                launch_time=time.monotonic()
                env=dict(os.environ,CCMCKP_LAUNCH_MONOTONIC=str(launch_time))
                process=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                    start_new_session=True,cwd=str(H),env=env)"""
assert old in c;c=c.replace(old,new).replace("'started':time.monotonic(),'peak_rss_bytes'","'started':launch_time,'peak_rss_bytes'")
c=c.replace("                active[identity]=item", """                def watch_exit(task_item):
                    proc=task_item['process']
                    allowance=P['process_wall_watchdog_seconds']-(time.monotonic()-task_item['started'])
                    def kill_at_guard():
                        if proc.poll() is None:
                            task_item['termination_reason']='guarded_total_wall_timeout'
                            os.killpg(proc.pid,signal.SIGKILL)
                    guard=threading.Timer(max(.001,allowance),kill_at_guard)
                    guard.daemon=True;guard.start()
                    proc.wait()
                    task_item['exited_monotonic']=time.monotonic()
                    guard.cancel()
                threading.Thread(target=watch_exit,args=(item,),daemon=True).start()
                active[identity]=item""")
# The dedicated watchdog owns the wall kill; the outer loop still handles resources/user stop.
c=c.replace("            if elapsed>P['process_wall_watchdog_seconds']:\n                terminate(item,'process_wall_watchdog')\n",'')
ast.parse(c,feature_version=(3,8));(R/'controller.py').write_text(c,encoding='utf-8')
p=json.loads((OLD/'PROTOCOL.json').read_text());v=json.loads((R/'VALIDATION.json').read_text())
assert v['status']=='PASS'
p.update({'schema':'S10_EGS_costfront_LSS_total600_v1','source_commit':'new frozen source accompanying this task; parent c4ab9a3fa10b9e34a11088844280320c78ab92c0',
 'arms':[{'name':'S10_TOTAL600','flow':'frontier_mitm','gamma':None},{'name':'EGS_CF_TOTAL600','flow':'ellipsoid_costfront','gamma':2.4}],
 'total_budget_seconds':600,'search_budget_seconds':430,'search_common_reserve_seconds':170,'LSS_outside_search_budget':False,
 'primary_runtime':'dedicated child-wait thread timestamp minus pre-Popen launch monotonic; includes startup/load/search/LSS/fsync/exit',
 'secondary_runtime':'elapsed from same launch through search completion; LSS finalization separately timed',
 'LSS_phase_deadline_seconds':590,'process_wall_watchdog_seconds':595,'watchdog_means_failure_not_clipped_600':True,
 'LSS_censoring':'no partial probability; retain last complete verdict; never retry cancelled evaluation; common to both arms',
 'ellipsoid_candidate_domain':'min cost subject to R<=max(T,R(current-run initial)), one per group, strict improving cost bound; native continuous lifted SOC',
 'ellipsoid_is_final_acceptance':False,'full_CCMCKP_global_optimality_claim':False,
 'nonconvex_solver_enabled':False,'no_gamma_or_risk_cap_tuning_from_test_results':True,
 'reserve_basis':'previous peak0.6433GiB; native SOC model lifted by n continuous variables; max60 is an upper cap, fresh resource checks apply',
 'preflight_available_GiB':103.28684997558594,'no_posthoc_model_changes_or_repeat_failed_seeds':True})
p['source_and_binary_pins']={'source/'+f.relative_to(R/'source').as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in (R/'source').rglob('*') if f.is_file()}
assert v['source_sha256']=={k[7:]:h for k,h in p['source_and_binary_pins'].items()}
p['source_and_binary_pins'].update({'bin/ccmckp_s10':v['binary_sha256'],'controller.py':hashlib.sha256((R/'controller.py').read_bytes()).hexdigest(),
 'DESIGN_AND_DIAGNOSIS.txt':hashlib.sha256((R/'DESIGN_AND_DIAGNOSIS.txt').read_bytes()).hexdigest()})
(R/'PROTOCOL.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
payload={n:base64.b64encode((R/n).read_bytes()).decode() for n in ['PROTOCOL.json','controller.py','DESIGN_AND_DIAGNOSIS.txt','PREVIOUS_RUN_DIAGNOSIS.json']}
code="""from pathlib import Path
import base64,hashlib,json,shutil,os
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_costfront_600s_20261124'
assert Path.cwd()==B and not (H/'LAUNCH.json').exists()
changes=[]
for n,b in PAYLOAD.items():
 data=base64.b64decode(b);f=H/n
 if f.exists() and f.read_bytes()!=data:
  changes.append({'prelaunch_metadata':n,'old_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'new_sha256':hashlib.sha256(data).hexdigest()})
 if not f.exists() or f.read_bytes()!=data:f.write_bytes(data)
if changes:(H/'PRE_FREEZE_METADATA_REVISIONS.json').write_text(json.dumps(changes,indent=2))
for n in ['bin','logs','runs','outcomes']:(H/n).mkdir(exist_ok=True)
shutil.copy2(H/'build/ccmckp_s10',H/'bin/ccmckp_s10')
P=json.loads((H/'PROTOCOL.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in P['source_and_binary_pins'].items():assert sha(H/n)==h,n
for n,h in P['input_pins'].items():assert sha(B/n)==h,n
active=[]
for d in Path('/proc').iterdir():
 if not d.name.isdigit():continue
 try:args=(d/'cmdline').read_bytes().split(b'\\0')
 except OSError:continue
 if any(str(B).encode() in a for a in args):active.append({'pid':d.name,'cmd':[a.decode(errors='replace') for a in args if a]})
assert not active,active
mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines()}
print(json.dumps({'status':'FROZEN_READY','available_GiB':mem['MemAvailable']/2**30,'CPU_count':len(os.sched_getaffinity(0)),
 'free_disk':shutil.disk_usage(B).free,'protocol_sha256':sha(H/'PROTOCOL.json'),'input_pins':len(P['input_pins']),
 'total':P['total_runs'],'max_workers':P['max_workers'],'full_wall_budget':600,'watchdog':595}))
""".replace('PAYLOAD',repr(payload))
(R/'freeze_remote.py').write_text(code,encoding='utf-8')
for n in ['launch_remote.py','monitor_remote.py']:
 t=(OLD/n).read_text().replace('egs_lss_3large_60w_20261124','egs_costfront_600s_20261124');(R/n).write_text(t)
print('PROTOCOL_READY',hashlib.sha256((R/'PROTOCOL.json').read_bytes()).hexdigest())
