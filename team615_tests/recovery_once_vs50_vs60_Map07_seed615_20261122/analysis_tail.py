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
