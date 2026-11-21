"""Static path and time estimates from sealed tracks; no simulator imports."""
from hashlib import sha256
from pathlib import Path
import json
import math
import heapq
import numpy as np
import cv2
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

out=Path.cwd()
source=Path('/home/quanliangwen/isolated_test/team615_messenger_batch1_32QMQI/Map08_baseline')
finish=json.loads((source/'FINISH.json').read_bytes())
official=Path(finish['result_dir'])
track_file=next((official/'recordings').glob('*.npz'))
assert sha256(track_file.read_bytes()).hexdigest()==finish['files'][track_file.relative_to(official).as_posix()]
tracks=np.load(track_file)['drone_states']
walls=np.load(source/'wall_geometry.npz')['walls'].astype(np.uint8)
score=json.loads((source/'OFFICIAL_SCORE.json').read_bytes())
assert score['steps']==3444 and tracks.shape==(3443,5)
assert walls.shape==(1122,1660)
WIDTH,HEIGHT=1660,1122
CELL=2
RADIO=160.
WINDOW_START,WINDOW_END=3240,3420
SPEEDS=(1.5,2.,2.8)
last={d['drone']:d['last_confirmation'] for d in score['drone_details']}
obstacles=walls.copy()
# Non-wall disposal-center body from the existing Map08 source. Far from these goals.
obstacles[6:260,1497:1656]=1
distance=cv2.distanceTransform(1-obstacles,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
padding=np.pad(obstacles,1,constant_values=1)
distance=cv2.distanceTransform(1-padding,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)[1:-1,1:-1]
events=[json.loads(line) for line in (source/'placement_events.jsonl').read_text().splitlines()]
aligned=0
for e in events:
    if e['event']=='trace':
        i=e['step']-3
        p=np.array([tracks[i,e['drone']]['x'],tracks[i,e['drone']]['y']])
        assert np.linalg.norm(p-np.asarray(e['physical_xy']))<.0002
        aligned+=1
assert aligned>100

def pos(drone,step):
    s=tracks[step-3,drone]
    return np.array([s['x'],s['y']],float)

def clearance(points):
    p=np.asarray(points)
    cols=np.clip(np.rint(p[...,0]+WIDTH/2).astype(int),0,WIDTH-1)
    rows=np.clip(np.rint(HEIGHT/2-p[...,1]).astype(int),0,HEIGHT-1)
    return distance[rows,cols]

def segment_samples(a,b,spacing=.75):
    return np.linspace(a,b,max(2,1+math.ceil(float(np.linalg.norm(np.subtract(b,a)))/spacing)))

def build(margin):
    hh,ww=HEIGHT//CELL,WIDTH//CELL
    free=(distance.reshape(hh,CELL,ww,CELL).min(axis=(1,3))>=margin)
    ids=np.full(free.shape,-1,np.int32)
    ids[free]=np.arange(int(free.sum()),dtype=np.int32)
    rr,cc=np.nonzero(free)
    xy=np.column_stack((cc*CELL+.5-WIDTH/2,HEIGHT/2-(rr*CELL+.5)))
    from_ids=[];to_ids=[];costs=[]
    for dr,dc in [(0,1),(1,0),(1,1),(1,-1)]:
        r0,r1=max(0,-dr),min(hh,hh-dr)
        c0,c1=max(0,-dc),min(ww,ww-dc)
        a=ids[r0:r1,c0:c1];b=ids[r0+dr:r1+dr,c0+dc:c1+dc]
        ok=(a>=0)&(b>=0)
        if dr and dc:
            ok &= free[r0+dr:r1+dr,c0:c1]&free[r0:r1,c0+dc:c1+dc]
        aa,bb=a[ok],b[ok]
        from_ids.extend([aa,bb]);to_ids.extend([bb,aa])
        length=CELL*math.hypot(dr,dc)
        costs.extend([np.full(len(aa),length),np.full(len(aa),length)])
    graph=coo_matrix((np.concatenate(costs),(np.concatenate(from_ids),np.concatenate(to_ids))),shape=(len(xy),len(xy))).tocsr()
    tree=cKDTree(xy)
    hub=int(tree.query([0.,0.])[1])
    goals=np.flatnonzero(np.hypot(xy[:,0],xy[:,1])<=RADIO)
    hubdist,hubpred=dijkstra(graph,directed=True,indices=hub,return_predecessors=True)
    radiodist,radiopred,_=dijkstra(graph,directed=True,indices=goals,min_only=True,return_predecessors=True)
    return dict(margin=margin,free=free,ids=ids,xy=xy,tree=tree,hub=hub,
                hubdist=hubdist,hubpred=hubpred,radiodist=radiodist,radiopred=radiopred)

def attach(model,p,kind):
    dists,choices=model['tree'].query(p,k=24)
    field=model[kind+'dist']
    best=None
    start_clear=float(clearance([p])[0])
    floor=min(18.,start_clear-.05)
    for gap,node in zip(dists,choices):
        if gap>24 or not np.isfinite(field[node]):continue
        q=model['xy'][node]
        if float(clearance(segment_samples(p,q)).min())<floor:continue
        cost=float(gap+field[node])
        if best is None or cost<best[0]:best=(cost,int(node),float(gap),start_clear)
    return best

def route(model,p,kind):
    result=attach(model,p,kind)
    if result is None:return None
    length,node,entry_gap,start_clear=result
    ids=[];current=node
    while current>=0:
        ids.append(current);current=int(model[kind+'pred'][current])
    path=np.vstack([p,model['xy'][ids]])
    if kind=='hub':path=np.vstack([path,[0.,0.]]);length+=float(np.linalg.norm(path[-1]-path[-2]))
    # Every grid edge has margin; the connector may start inside that margin.
    checked_min=math.inf
    for a,b in zip(path[1:],path[2:]):checked_min=min(checked_min,float(clearance(segment_samples(a,b,.5)).min()))
    assert checked_min>=model['margin']-.01
    simple=[path[0]];index=0
    while index<len(path)-1:
        selected=index+1
        for j in range(len(path)-1,index+1,-1):
            if float(clearance(segment_samples(path[index],path[j],.5)).min())>=model['margin']:
                selected=j;break
        simple.append(path[selected]);index=selected
    simple=np.array(simple)
    smooth_length=float(np.linalg.norm(np.diff(simple,axis=0),axis=1).sum())
    samples=np.vstack([segment_samples(a,b,2.) for a,b in zip(simple[:-1],simple[1:])])
    nogps=((samples[:,0]>=-637)&(samples[:,0]<=-129)&(samples[:,1]>=-99)&(samples[:,1]<=557))|((samples[:,0]>=127)&(samples[:,0]<=751)&(samples[:,1]>=-435.5)&(samples[:,1]<=45.5))
    return dict(grid_length_pixels=length,route_length_pixels=smooth_length,
                start_clearance_pixels=start_clear,connector_pixels=entry_gap,
                checked_grid_min_clearance_pixels=checked_min,
                waypoints=[[round(float(x),2),round(float(y),2)] for x,y in simple],
                end_distance_from_origin=float(np.linalg.norm(simple[-1])),
                route_sample_fraction_in_no_gps=float(nogps.mean()))

def flight_times(length,drone):
    reserve=12 if drone==0 else 24
    return {str(v):int(math.ceil(length/v)+reserve) for v in SPEEDS}

model=build(23.)
snapshots={}
for step in [2489,2700,2800,2900,3000,3100,3200,3240,3300,3360]:
    rows=[]
    for i in range(5):
        p=pos(i,step);kind='hub' if i==0 else 'radio';r=route(model,p,kind)
        rows.append(dict(drone=i,step=step,position=p.tolist(),route=r,
                         required_steps=None if r is None else flight_times(r['route_length_pixels'],i)))
    snapshots[str(step)]=rows

# Cheap all-step distance lookups are used to find departure brackets, then
# the bracket is refined with the verified, smoothed route, not a rollout.
latest={}
for i in range(5):
    kind='hub' if i==0 else 'radio'
    deadline=WINDOW_START if i==0 else WINDOW_END
    candidates=[]
    for t in range(last[i],deadline+1,5):
        a=attach(model,pos(i,t),kind)
        if a is not None:candidates.append((t,a[0]))
    per_speed={}
    for speed in SPEEDS:
        reserve=12 if i==0 else 24
        # Grid distance is a conservative approximation. Refine near its latest feasible time.
        feasible=[t for t,length in candidates if t+math.ceil(length/speed)+reserve<=deadline]
        base=max(feasible) if feasible else last[i]
        best=None
        for t in range(max(last[i],base-5),min(deadline,base+100)+1,5):
            rr=route(model,pos(i,t),kind)
            if rr is None:continue
            need=math.ceil(rr['route_length_pixels']/speed)+reserve
            if t+need<=deadline:best=dict(depart_step=t,estimated_arrival_step=t+need,
                required_steps=need,route=rr,position=pos(i,t).tolist(),
                pre_window_exploration_steps_given_up=max(0,WINDOW_START-t),
                total_original_task_steps_given_up=(WINDOW_END-t if i==0 else need))
        per_speed[str(speed)]=best
    latest[str(i)]=per_speed

# Sensitivity at 18px clearance, using the same physical map and clock assumptions.
narrow=build(18.)
sensitivity=[]
for i in range(5):
    rr=route(narrow,pos(i,3240),'hub' if i==0 else 'radio')
    sensitivity.append(dict(drone=i,route=rr,required_steps=None if rr is None else flight_times(rr['route_length_pixels'],i)))

motion={}
for i in range(5):
    xy=np.column_stack((tracks['x'][:,i],tracks['y'][:,i])).astype(float)
    speeds=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    moving=speeds[(np.arange(len(speeds))<3240-3)&(speeds>=1)&(speeds<=4.5)]
    late=speeds[2489-3:3240-3]
    motion[str(i)]=dict(moving_samples=len(moving),moving_p25=float(np.percentile(moving,25)),
                        moving_median=float(np.median(moving)),moving_p75=float(np.percentile(moving,75)),
                        late_fraction_below_point2=float(np.mean(late<.2)),late_distance_pixels=float(late.sum()))
result=dict(status='COMPLETE',new_matches=0,simulation_steps=0,seed=615,map_name='Map08',
    baseline_zip_sha256='c3021a3eb48031e82bfac9306654b48ca09f168d6f65b13349cf12f783104c7c',
    input_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in [track_file,source/'wall_geometry.npz',source/'OFFICIAL_SCORE.json',source/'placement_events.jsonl']},
    alignment_checks=aligned,recording_frame_to_control_step_offset=3,
    assumptions=dict(grid_pixels=CELL,nominal_wall_clearance=23,radio_radius=RADIO,
        collector_drone=0,collector_goal=[0,0],collector_deadline=3240,visitors_deadline=3420,
        collector_settle_steps=12,exchange_steps=24,speeds_pixels_per_step=list(SPEEDS),
        collisions_with_other_drones_not_modelled=True,known_online_maps_not_recorded=True,
        full_truth_geometry_used_only_for_offline_static_path_analysis=True),
    own_last_drop_confirmations=last,origin_clearance_pixels=float(clearance([[0.,0.]])[0]),
    motion=motion,snapshots=snapshots,latest_departures=latest,clearance18_at3240=sensitivity)
(out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
np.savez_compressed(out/'PATH_GEOMETRY.npz',walls=walls,clearance=distance)
print('AT3240',json.dumps(snapshots['3240'],indent=2))
print('LATEST',json.dumps({i:{v:None if q is None else {k:x for k,x in q.items() if k!='route'} for v,q in values.items()} for i,values in latest.items()},indent=2))
print('MOTION',json.dumps(motion,indent=2))
