"""Collect an already completed authorized match; never start a match."""
from pathlib import Path,PurePosixPath
from hashlib import sha256
import json,math,statistics,subprocess,sys
import numpy as np

ROOT=Path(__file__).resolve().parent
MAP=sys.argv[1];assert MAP == 'Map07'
HOST='quanliangwen@10.112.162.60';REMOTE='/home/quanliangwen/isolated_test/'+ROOT.name
LOCAL_ONLY='--local' in sys.argv[2:]
out=ROOT/MAP/'received';out.mkdir(exist_ok=True)
H=lambda p:sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf8'))
save=lambda p,d:p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def get(paths,dest):
    dest.mkdir(parents=True,exist_ok=True)
    if LOCAL_ONLY:
        assert all((dest/PurePosixPath(p).name).is_file() for p in paths)
        return
    subprocess.run(['scp','-q',*[HOST+':'+p for p in paths],str(dest)],check=True)
names=['STATUS.json','START.json','FINISH.json','SOURCE_MATCH.json','OFFICIAL_SCORE.json','placement_events.jsonl',
       'POST_RUN_SOURCE_CHECK.json','EXTRA_ARTIFACTS.json','resources.jsonl','ADMISSION.json','MONITOR_FINISH.json',
       'MONITOR_CONFIG.json','AFFINITY_SELECTION.json','SDK_PID','TIMING_ANCHORS.jsonl','dispatch.log','run.log',
       'GROUP_DATASET.json','group_dataset.npz','wall_geometry.npz']
get([REMOTE+'/'+MAP+'/'+n for n in names],out)
assert read(out/'STATUS.json')['state']=='COMPLETE'
f=read(out/'FINISH.json');assert (f['status'],f['completed_red_rounds'],f['blue_rounds'],f['layout_evaluations'])==('COMPLETE',1,0,0)
base=PurePosixPath(f['result_dir']);assert base.is_relative_to(PurePosixPath(REMOTE)/MAP/'official_sdk/results_swarm_rescue')
for name,digest in f['files'].items():
    rel=PurePosixPath(name);assert not rel.is_absolute() and '..' not in rel.parts
    get([str(base/rel)],out/'official'/rel.parent)
    assert H(out/'official'/name)==digest
assert read(out/'POST_RUN_SOURCE_CHECK.json')['status']=='PASS'
assert read(out/'SOURCE_MATCH.json')['candidate_zip_sha256']=='6207ff8df49e435dc988119f98c130673da3dc123620ef4d20f39afc170c2a23'
declared=read(ROOT/MAP/'DECLARED_SOURCE.json')
assert read(out/'START.json')['solutions_sha256']==read(out/'SOURCE_MATCH.json')['candidate']==declared
for name,digest in read(out/'EXTRA_ARTIFACTS.json').items():assert H(out/name)==digest
s=read(out/'OFFICIAL_SCORE.json');start=read(out/'START.json')
assert s['placement_events_sha256']==H(out/'placement_events.jsonl')
assert s['wall_geometry_sha256']==H(out/'wall_geometry.npz')
assert math.isclose(s['partial'],.5*s['map_score']+.2*s['coverage']+.1*s['time_score'],abs_tol=1.e-9)

def distribution(v):
    v=sorted(float(x) for x in v if x is not None)
    return None if not v else dict(count=len(v),mean=statistics.mean(v),median=statistics.median(v),
        p95=v[math.ceil(.95*len(v))-1],maximum=max(v))
def summarize_resources(p):
    rows=[json.loads(l) for l in (p/'resources.jsonl').read_text().splitlines()]
    admitted=read(p/'ADMISSION.json');pool=admitted['logical_cpus'];other=[]
    for a,z in zip(rows,rows[1:]):
        if a.get('test_process') and z.get('test_process'):
            dt=z['monotonic']-a['monotonic']
            own=sum(z['test_process'][k]-a['test_process'][k] for k in ['user_seconds','system_seconds'])/dt
            other.append(max(0.,sum(z['selected_cpu_busy_percent'].values())/100-own))
    return dict(assigned_logical_cpus=pool,assigned_count=len(pool),server_busy_percent=distribution([r['cpu_busy_percent'] for r in rows]),
                load1=distribution([r['load1'] for r in rows]),other_work_cpu_equivalents_in_monitored_pool=distribution(other),
                note='Affinity does not reserve CPUs; monitored pool can include SMT siblings. Different historical CPU pools are not a controlled speed benchmark.')
def result(score,p):
    ev=[json.loads(l) for l in (p/'placement_events.jsonl').read_text().splitlines()]
    stockgates=[r for r in ev if r['event']=='ordinary_inventory_gate']
    actual={str(d['drone']):d['inventory'] for d in score['drone_details']}
    confirmations={};stockblocks={};details=score['drone_details']
    for d in details:
        owner=d['drone'];key=str(owner)
        placements=[r for r in ev if r['drone']==owner and r['event']=='sdk_placement' and r.get('accepted')]
        placed=[r['step'] for r in placements]
        requests={r['step']:r for r in ev if r['drone']==owner and r['event']=='request' and 'branch' in r}
        confirmations[key]=dict(accepted_steps=placed,second_accepted_step=placed[1] if len(placed)>1 else None,
            accepted_physical_xy=[r['physical_xy'] for r in placements],
            accepted_request_branches=[requests.get(step,{}).get('branch') for step in placed],
            accepted_request_wall_seconds=[requests.get(step,{}).get('walltime_seconds') for step in placed],
            final_bomb_confirmation_step=d['last_confirmation'] if d['inventory']==0 else None,
            last_any_confirmation_step=d['last_confirmation'],remaining=d['inventory'])
        stockblocks[key]={peer:dict(origin_step=stamp,count=count,actual_remaining=actual[peer],
                                  stale_positive=actual[peer]==0)
                         for peer,(stamp,count) in d['final_inventory_records'].items() if count>0}
    assert sum(len(v['accepted_steps']) for v in confirmations.values())==score['placed']
    selected=score['selected_submission'];chosen=next((d for d in details if selected and d['drone']==selected['drone']),None)
    path=('no_submission' if not chosen else 'budget93' if chosen['budget_submission'] is not None else
          'hard_fallback' if chosen['walltime_submission'] is not None else
          'group_submit' if any(row[1] in ('submitted','soft_cutoff_submit') for row in chosen['group_audit']) else
          'ordinary_direct_after_exchange' if chosen.get('group_early_finish_started') is not None else 'ordinary_direct')
    choice=None if chosen is None else chosen['group_choice']
    wait=None if not choice or selected is None else selected['step']-choice['created']
    mb=score.get('map_breakdown') or {}
    return dict(score_out_of_80=score['partial'],map_score=score['map_score'],wall_score=score['coverage'],
        time_score=score['time_score'],exploration_percent=score['trajectory'],placed=score['placed'],expected=score['expected'],
        health_lost=sum(25-d['health'] for d in details),final_walltime_seconds=score['elapsed_walltime'],
        submission_drone=None if selected is None else selected['drone'],submission_step=None if selected is None else selected['step'],
        submission_walltime_seconds=None if selected is None else selected['walltime_seconds'],ending_path=path,
        submission_calls=score['submissions'],simultaneous_submission=len(score['submissions'])>1 and len({r['step'] for r in score['submissions']})==1,
        selected_choice_wait_steps=wait,choice_two_step_wait_observed=None if wait is None else wait>=2,
        confirmations=confirmations,actual_final_inventory=actual,ordinary_stock_blocks_at_end=stockblocks,
        first_actual_return_step={str(d['drone']):next((row[0] for row in d['group_audit'] if row[1]=='return_owned'),None) for d in details},
        return_tasks={str(d['drone']):[dict(step=row[0],group=row[2],target=row[3],estimated_steps=row[4]) for row in d['group_audit'] if row[1]=='return_owned'] for d in details},
        return_preflight_events={str(d['drone']):[row for row in d['group_audit'] if row[1]=='return_preflight'] for d in details},
        return_abort_events={str(d['drone']):[row for row in d['group_audit'] if row[1]=='route_abort'] for d in details},
        return_arrival_events={str(d['drone']):[row for row in d['group_audit'] if row[1]=='region_arrival'] for d in details},
        group_end_phase={str(d['drone']):d['group_phase'] for d in details},
        ordinary_first_ready={str(d['drone']):d['original_first_ready'] for d in details},
        first_team_confirmed_step={str(d['drone']):next((r['step'] for r in stockgates if r['drone']==d['drone'] and r['team_confirmed']),None) for d in details},
        group_early_finish_started={str(d['drone']):d.get('group_early_finish_started') for d in details},
        confirmation_retry_used={str(d['drone']):d.get('group_confirmation_retry_used') for d in details},
        group_finish_refresh_step={str(d['drone']):d['group_finish_refresh_step'] for d in details},
        missed_wall_pixels=mb.get('wall_pixels',0)-mb.get('wall_hits',0),charged_misdraw_pixels=mb.get('charged_pixels'),
        resources=summarize_resources(p))

refs={
    'return50':ROOT.parent/'team615_return50_maps05_06_07_seed615_20261122'/'Map07'/'received',
    'return60':ROOT.parent/'team615_finish_minimal_maps05_06_07_seed615_20261122'/'Map07'/'received',
}
new=result(s,out)
historical={}
trajectory={}
events=[json.loads(line) for line in (out/'placement_events.jsonl').read_text(encoding='utf8').splitlines()]
def position_analysis(path,score,metrics):
    with np.load(next((path/'official/recordings').glob('*.npz')),allow_pickle=False) as z:
        times=z['timestamps'].copy();states=z['drone_states'].copy()
    assert len(states)==score['steps']-1
    first=metrics['confirmations']['4']['accepted_steps'][0]
    centre=metrics['confirmations']['4']['accepted_physical_xy'][0]
    r=np.hypot(states[:,4]['x'].astype(float)-centre[0],states[:,4]['y'].astype(float)-centre[1])
    crosses={str(th):(None if not len(ix:=np.flatnonzero(r[first-1:]>=th)) else int(ix[0]+first+1)) for th in (24,32,36)}
    return dict(first_drop_step=first,first_drop_physical_xy=centre,
        first_recorded_separation_step=crosses,
        minimum_distance_after_first=float(r[first-1:].min()),maximum_distance_after_first=float(r[first-1:].max()),
        end_distance=float(r[-1]),recorded_last_step=len(states)+1),times,states,r
current_motion,times,states,radius=position_analysis(out,s,new)
timings={};state_diffs={}
for name,path in refs.items():
    score=read(path/'OFFICIAL_SCORE.json');origin=read(path/'START.json')
    for key in ['seed','sdk','sdk_archive_sha256','spawn','zones','drones','bombs_per_drone','timestep_limit','walltime_limit']:
        assert start[key]==origin[key],(name,key)
    with np.load(path/'wall_geometry.npz') as z,np.load(out/'wall_geometry.npz') as q:
        assert np.array_equal(z['walls'],q['walls']) and np.array_equal(z['boundary'],q['boundary'])
    old=result(score,path);historical[name]=old
    motion,oldtimes,oldstates,oldradius=position_analysis(path,score,old);trajectory[name]=motion
    points=[step for step in [1001,1356,1418,1501,2001,2700,3001,3240,4001,4501,5001] if step<=min(s['steps']-1,score['steps']-1)]
    timings[name]={str(step):dict(historical_seconds=float(oldtimes[step-2]),candidate_seconds=float(times[step-2]),difference=float(times[step-2]-oldtimes[step-2])) for step in points}
    count=min(len(states),len(oldstates));diff=np.any(states[:count]!=oldstates[:count],axis=1)
    state_diffs[name]=None if not diff.any() else int(np.flatnonzero(diff)[0]+2)
trajectory['recovery_once']=current_motion
detail4=next(d for d in s['drone_details'] if d['drone']==4)
recovery_events=[row for row in events if row['drone']==4 and row.get('source')=='drop_departure' and row['event'].startswith('recovery_')]
audits=detail4['drop_departure_audit']
recovery=dict(events=recovery_events,audit=audits,final_state=detail4['first_drop_recovery'],
    first_trigger_step=next((x[0] for x in audits if x[1]=='recovery_started'),None),
    success_reported_step=next((x[0] for x in audits if x[1]=='recovery_clear'),None),
    exit_events=[x for x in audits if x[1].startswith('recovery_') and x[1] not in ('recovery_started','recovery_path')],
    drone4_confirmation=new['confirmations']['4'])
compact_events=[]
for row in recovery_events:
    compact_events.append({k:v for k,v in row.items() if k not in ['lidar','angles','semantic','prior_scan']})
recovery['compact_events']=compact_events
keys=['score_out_of_80','map_score','exploration_percent','placed','health_lost','submission_step','final_walltime_seconds']
summary=dict(status='COMPLETE',map='Map07',seed=615,new_red_rounds=1,baseline_reruns=0,other_maps_run=False,
    candidate_zip_sha256=read(out/'SOURCE_MATCH.json')['candidate_zip_sha256'],algorithm_changes=False,
    V16_remains_competition_baseline=True,candidate=new,historical=historical,recovery_drone4=recovery,
    physical_trajectory=trajectory,same_step_timing=timings,first_recorded_state_difference=state_diffs,
    delta={name:{key:new[key]-old[key] for key in keys if new[key] is not None and old[key] is not None} for name,old in historical.items()},
    native_limits=[5400,180],source_bytes_verified=True,matched_seed_spawn_geometry_limits=True)
save(ROOT/'RESULTS.json',summary)
print(json.dumps(dict(status='COMPLETE',candidate={k:new[k] for k in keys+['submission_drone','ending_path']},
    recovery={k:recovery[k] for k in ['first_trigger_step','success_reported_step','exit_events','drone4_confirmation']},
    candidate_motion=current_motion),indent=2,ensure_ascii=False))
