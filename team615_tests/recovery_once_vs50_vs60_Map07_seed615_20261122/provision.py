from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import ast,json,shutil,subprocess

ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/'team615_first_drop_recovery_once_20261122'
OLD=ROOT.parent/'team615_return50_maps05_06_07_seed615_20261122'
HOST='quanliangwen@10.112.162.60';REMOTE='/home/quanliangwen/isolated_test/'+ROOT.name
H=lambda p:sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf8'))
save=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
b=read(SRC/'BUILD.json')
assert H(SRC/'candidate_snapshot.zip')==b['candidate_zip_sha256']=='6207ff8df49e435dc988119f98c130673da3dc123620ef4d20f39afc170c2a23'
assert b['baseline_zip_sha256']=='e69ea77adb25b9ecbb8bd3a38f34f2241c35ad788c147aff67bc6d83e7c227e8'
checks=[read(SRC/'received'/n) for n in ['RECOVERY_COUNTEREXAMPLES.json','COUNTEREXAMPLES.json','BUDGET_REGRESSION.json','RETURN50_TESTS.json']]
assert all(x['status']=='PASS' and x['candidate_zip_sha256']==b['candidate_zip_sha256'] for x in checks)
assert sum(x['total_checks'] for x in checks)==269
with ZipFile(SRC/'candidate_snapshot.zip') as z:
    assert {n:sha256(z.read(n)).hexdigest() for n in z.namelist()}==b['candidate_files']
assert all(H(SRC/'candidate'/n)==h for n,h in b['candidate_files'].items())
stage=ROOT/'Map07';stage.mkdir()
for n in ['candidate_snapshot.zip','baseline_snapshot.zip']:shutil.copy2(SRC/n,stage/n)
save(stage/'DECLARED_SOURCE.json',b['candidate_files'])
save(stage/'PATCH_BINDING.json',dict(baseline_commit='5024a33bb07be4172b96536e6b82744f5ec6fa3c',baseline_zip_sha256=b['baseline_zip_sha256'],candidate_zip_sha256=b['candidate_zip_sha256'],baseline=b['baseline_files'],candidate=b['candidate_files'],changed=b['changed_files']))
save(stage/'OFFLINE_CHECK.json',dict(simulation_steps=0,unit_checks=269,checks=[dict(sha256=H(SRC/'received'/n),file=n) for n in ['RECOVERY_COUNTEREXAMPLES.json','COUNTEREXAMPLES.json','BUDGET_REGRESSION.json','RETURN50_TESTS.json']]))
previous=read(OLD/'Map07/received/START.json')
assert previous['seed']==615 and previous['zones']==dict(NoGpsZone=0,NoComZone=0)
save(stage/'matched_spawns.json',{'Map07':previous['spawn']})
save(stage/'EXPECTED_ZONES.json',{'Map07':previous['zones']})
save(stage/'EXPECTED_LIMITS.json',{'Map07':[5400,180]})
observer=(OLD/'Map07/stage_run.py').read_text(encoding='utf8')
observer=observer.replace('assert map_name in ("Map05", "Map06", "Map07")','assert map_name == "Map07"')
needle='        if self.source == "messenger":'
assert observer.count(needle)==1
observer=observer.replace(needle,'''        if self.source == "drop_departure" and (event.startswith("recovery_") or event == "departure_ended"):
            r=self.drone.drop_departure
            extra={}
            if self.drone.identifier==4 and event.startswith("recovery_"):
                extra=dict(pose=self.drone.pose,first_point=r.first_point,goal=r.recovery_goal,
                    walltime=float(self.drone.elapsed_walltime),prior_scan=r.before_drop_scan,
                    lidar=self.drone.lidar_values(),angles=self.drone.lidar_rays_angles(),
                    semantic=[dict(distance=h.distance,angle=h.angle,kind=getattr(h.entity_type,"name",""),grasped=h.grasped) for h in self.drone.semantic_values() or ()])
            emit(dict(drone=int(self.drone.identifier),step=step,event=event,source=self.source,values=values,**extra))
'''+needle)
needle='        return result\n    return execute'
assert observer.count(needle)==1
observer=observer.replace(needle,'''        if drone.identifier==4:
            r=drone.drop_departure
            state=(r.recovery_failed,r.recovery_used,r.started,r.recovery_started,
                   r.before_drop_scan is not None,r.first_point is not None,len(r.recovery_trace)==30)
            if state!=recovery_states.get(4) or step in (1356,1418,1450,1500,1620,2700,3240,4000,5022):
                recovery_states[4]=state
                emit(dict(drone=4,step=step,event="recovery_state_observed",state=state,
                    pose=drone.pose,first_point=r.first_point,
                    distance=None if r.first_point is None else float(np.linalg.norm(drone.pose-r.first_point)),
                    trace_span=None if not r.recovery_trace else step-r.recovery_trace[0][0],
                    trace_movement=None if not r.recovery_trace else float(max(np.linalg.norm(p-r.recovery_trace[0][1]) for _,p in r.recovery_trace)),
                    prior_scan_step=None if r.before_drop_scan is None else r.before_drop_scan[0],
                    fixed=bool(drone.grid.pose_fixed and not drone._odometry_only),
                    inventory=int(drone.carried_bombs_count()),pending=drone.pending_drop is not None,
                    walltime=float(drone.elapsed_walltime)))
        return result
    return execute''')
observer=observer.replace('stock_states = {}','stock_states = {}\nrecovery_states = {}')
needle='             second_drop_audit=d.second_drop.audit,'
assert observer.count(needle)==1
observer=observer.replace(needle,'''             drop_departure_audit=d.drop_departure.audit,
             first_drop_recovery=dict(failed=d.drop_departure.recovery_failed,used=d.drop_departure.recovery_used,
                 started=d.drop_departure.recovery_started,first_point=d.drop_departure.first_point,
                 prior_scan=d.drop_departure.before_drop_scan),
'''+needle)
(stage/'stage_run.py').write_text(observer,encoding='utf8',newline='\n')
shutil.copy2(OLD/'Map07/place_map09.yml',stage/'place_map09.yml')
(stage/'run_monitored.sh').write_text((OLD/'Map07/run_monitored.sh').read_text(encoding='utf8').replace('return50','recovery_once'),encoding='utf8',newline='\n')
monitor=(OLD/'monitor.py').read_text(encoding='utf8')
monitor=monitor.replace("maps=['Map05','Map06','Map07'];COUNT=8","maps=['Map07'];COUNT=8")
monitor=monitor.replace("maps=['Map05','Map06','Map07']","maps=['Map07']").replace('new_red_rounds=3','new_red_rounds=1')
(ROOT/'monitor.py').write_text(monitor,encoding='utf8',newline='\n')
shutil.copy2(OLD/'environment.py',ROOT/'environment.py')
save(ROOT/'AUTHORIZED_RUN.json',dict(maps=['Map07'],seed=615,rounds_per_map=1,total_red_rounds=1,other_maps=False,baseline_reruns=0,algorithm_changes=False,V16_remains_competition_baseline=True,candidate_zip_sha256=b['candidate_zip_sha256'],assigned_logical_cpus=8,distinct_physical_cores=8,sibling_idle_required=False,global_load_is_admission_gate=False,retries=False))
save(ROOT/'OBSERVER_BINDING.json',dict(source_observer_sha256=H(OLD/'Map07/stage_run.py'),observer_sha256=H(stage/'stage_run.py'),change='Passive recovery audit forwarding, public sensor snapshots at recovery events, state transitions for drone4, final audit export; no command or score changes',candidate_bytes_unmodified=True))
for p in [ROOT/'monitor.py',stage/'stage_run.py']:ast.parse(p.read_text(encoding='utf8'))
subprocess.run(['ssh','-o','BatchMode=yes',HOST,'mkdir '+REMOTE],check=True)
subprocess.run(['ssh',HOST,'mkdir '+REMOTE+'/Map07'],check=True)
subprocess.run(['scp','-q',*[str(ROOT/n) for n in ['monitor.py','environment.py','AUTHORIZED_RUN.json','OBSERVER_BINDING.json']],HOST+':'+REMOTE+'/'],check=True)
subprocess.run(['scp','-q',*[str(p) for p in stage.iterdir() if p.is_file()],HOST+':'+REMOTE+'/Map07/'],check=True)
subprocess.run(['ssh',HOST,'/home/junhao/quan/parallel_test_solver/match/.venv/bin/python '+REMOTE+'/environment.py'],check=True)
print(subprocess.run(['ssh',HOST,'nohup python3 '+REMOTE+'/monitor.py > '+REMOTE+'/queue.log 2>&1 < /dev/null & echo MAP07_SEED615_EXACTLY_ONCE_QUEUED'],capture_output=True,text=True,check=True).stdout)
