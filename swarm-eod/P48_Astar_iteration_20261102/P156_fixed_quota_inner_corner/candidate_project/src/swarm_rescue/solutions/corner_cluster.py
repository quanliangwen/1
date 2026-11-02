"""Coverage-guarded majority-corner proposals, public own/received geometry only.

Finite engineering rule, not global optimization or guaranteed BLUE difficulty.
The baseline remains the fallback. No new map/physics/solver dependency.
"""
import math
import time
import cv2
import numpy as np
from swarm_rescue.solutions.geometry_route_view import GeometryPlanningMemory
from swarm_rescue.solutions.team_coverage import observed_wall_values,path_costs
from swarm_rescue.solutions.farthest_wall_cover import owner_travel_budget

COVERAGE_RATIO=.90
CORNER_RADIUS_RATIO=2.0
MAJORITY_RATIO=.60
OPTIONAL_SECONDS=.40
MAX_CALLS=12

def _mask(xx,yy,points,radius):
    out=np.zeros(xx.shape,bool)
    for p in points:out|=(xx-p[0])**2+(yy-p[1])**2<=radius**2+1e-8
    return out

def _corners(memory,allowed,xx,yy,radius):
    """Harris proposes pivots; two actual perpendicular hit arms certify them.

    No true map, map-name coordinates, or synthetic frame evidence is used.
    This axis-aligned rule deliberately abstains on unsupported/diagonal walls.
    """
    measured=cv2.resize((np.asarray(memory.hits)>=2).astype(np.float32),
                        (allowed.shape[1],allowed.shape[0]),interpolation=cv2.INTER_AREA)>0
    response=cv2.cornerHarris(measured.astype(np.float32),3,3,.04)
    if not response.size or float(response.max())<=0:return []
    peaks=(response==cv2.dilate(response,np.ones((5,5),np.uint8)))&(response>.05*response.max())
    rows,cols=np.nonzero(peaks);out=[]
    lock=getattr(memory,'corner_cluster_anchor',None)
    for peak_row,peak_col in zip(rows,cols):
        certified=[]
        # A 3x3 Harris response peak may be offset from the measured junction.
        # Snap only to a measured cell in its two-cell filter support, then
        # require both long arms; a lone segment endpoint still cannot pass.
        for row in range(max(0,peak_row-2),min(measured.shape[0],peak_row+3)):
            for col in range(max(0,peak_col-2),min(measured.shape[1],peak_col+3)):
                if not measured[row,col]:continue
                arms=[]
                for dr,dc in[(0,1),(0,-1),(1,0),(-1,0)]:
                    support=[]
                    for distance in range(2,7):
                        rr,cc=row+dr*distance,col+dc*distance
                        r0,r1=max(0,rr-1),min(measured.shape[0],rr+2)
                        c0,c1=max(0,cc-1),min(measured.shape[1],cc+2)
                        support.append(r0<r1 and c0<c1 and measured[r0:r1,c0:c1].any())
                    arms.append(sum(support)>=4)
                if any(arms[:2])and any(arms[2:]):certified.append(((row-peak_row)**2+(col-peak_col)**2,row,col))
        if not certified:continue
        _,row,col=min(certified)
        pivot=np.array([xx[row,col],yy[row,col]])
        # Internal pivots only; outer corners already failed the majority test.
        if min(memory.width/2-abs(pivot[0]),memory.height/2-abs(pivot[1]))<3*memory.CELL:continue
        if lock is not None and np.linalg.norm(pivot-np.asarray(lock[:2]))>3*memory.CELL:continue
        arms=[]
        for dr,dc in[(0,1),(0,-1),(1,0),(-1,0)]:
            support=[]
            for distance in range(2,7):
                rr,cc=row+dr*distance,col+dc*distance
                r0,r1=max(0,rr-1),min(measured.shape[0],rr+2)
                c0,c1=max(0,cc-1),min(measured.shape[1],cc+2)
                support.append(r0<r1 and c0<c1 and measured[r0:r1,c0:c1].any())
            arms.append(sum(support)>=4)
        if not(any(arms[:2])and any(arms[2:])):continue
        ids=np.flatnonzero(allowed & ((xx-pivot[0])**2+(yy-pivot[1])**2<=(4*memory.CELL)**2))
        if not len(ids):continue
        if lock is None:
            flat=min(ids,key=lambda n:(float((xx.ravel()[n]-pivot[0])**2+(yy.ravel()[n]-pivot[1])**2),int(n)))
            anchor=np.array([xx.ravel()[flat],yy.ravel()[flat]])
        else:anchor=np.asarray(lock[2:4],float)
        region=allowed & ((xx-anchor[0])**2+(yy-anchor[1])**2<=(CORNER_RADIUS_RATIO*radius)**2)
        # One connected free pocket; no gathering through a dividing wall.
        count,labels=cv2.connectedComponents(region.astype(np.uint8),connectivity=8)
        cell=memory.world_to_cell(anchor);component=int(labels[cell])
        if component==0:continue
        region &= labels==component
        if any(np.linalg.norm(anchor-old[2])<3*memory.CELL for old in out):continue
        out.append((float(pivot[0]),float(pivot[1]),anchor,region))
    return out

def corner_cluster_layout(memory,agents,drops,radius,base,travel_budget=None,
                          forbidden_points=(),forbidden_mask=None,_prepared=None):
    started=time.perf_counter();deadline=started+OPTIONAL_SECONDS
    original={int(k):[np.asarray(p,float).copy()for p in ps]for k,ps in base.items()}
    calls=int(getattr(memory,'corner_cluster_calls',0))+1;memory.corner_cluster_calls=calls
    audit=dict(status='KEEP_BASE',call=calls,reason='not_started',coverage_floor=COVERAGE_RATIO,
               radius_ratio=CORNER_RADIUS_RATIO,fields=0,attempts=0,accepted=False)
    memory.corner_cluster_diagnostics=audit
    def finish(reason,result=None):
        audit.update(reason=reason,elapsed=time.perf_counter()-started)
        if calls<=MAX_CALLS:
            print('[CORNER_CLUSTER] '+__import__('json').dumps(audit,separators=(',',':')),flush=True)
        return original if result is None else result
    if calls>MAX_CALLS:return finish('optional_call_limit')
    counts={k:len(ps)for k,ps in original.items()if ps}
    total=sum(counts.values())
    if total<2:return finish('too_few_unreserved_slots')
    clean={int(k):(np.asarray(p,float),int(n))for k,(p,n)in agents.items()if p is not None and int(n)>0}
    if any(k not in clean or counts[k]>clean[k][1]for k in counts):return finish('incumbent_owner_count')
    pm=GeometryPlanningMemory(memory)if _prepared is None else _prepared
    values,solids=observed_wall_values(pm,radius,return_solids=True)
    walkable=pm.free & ~pm.blocked() & ~solids
    allowed=walkable.copy();rr,cc=np.indices(pm.shape)
    xx=(cc+.5)*pm.CELL-pm.width/2;yy=pm.height/2-(rr+.5)*pm.CELL
    if forbidden_mask is not None:
        if np.asarray(forbidden_mask).shape!=pm.shape:return finish('forbidden_shape')
        allowed &= ~np.asarray(forbidden_mask,bool)
    separation=40.+.71*pm.CELL
    for p,exclusion in forbidden_points:allowed &= (xx-p[0])**2+(yy-p[1])**2>=float(exclusion)**2
    residual=np.asarray(values,np.float32).copy()
    for p in drops:
        squared=(xx-p[0])**2+(yy-p[1])**2
        residual[squared<=radius**2]=0
        allowed &= squared>=separation**2
    baseline_points=[p for ps in original.values()for p in ps]
    baseline=float(residual[_mask(xx,yy,baseline_points,radius)].sum())
    audit.update(baseline_value=baseline,planned=total)
    if baseline<=0 or not np.isfinite(residual).all():return finish('no_positive_incumbent')
    state=getattr(memory,'corner_policy_state',{})
    initial_total=state.get('initial_total')
    if not isinstance(initial_total,int)or initial_total<=0:return finish('no_initial_inventory_certificate')
    target_total=int(math.ceil(MAJORITY_RATIO*initial_total))
    confirmed=[np.asarray(p,float)for p in state.get('confirmed',[])]
    reserved=[np.asarray(p,float)for p in state.get('reserved',{}).values()]
    committed=confirmed+reserved
    audit.update(initial_total=initial_total,target_total=target_total,confirmed_count=len(confirmed),reserved_count=len(reserved))
    corners=_corners(memory,allowed,xx,yy,radius)
    if not corners:return finish('no_two_measured_corner_surfaces')
    fields={}
    class Budget(Exception):pass
    def field(p):
        rc=tuple(pm.world_to_cell(p))
        if rc not in fields:
            if time.perf_counter()>=deadline:raise Budget
            fields[rc]=path_costs(pm,walkable,rc);audit['fields']+=1
        return fields[rc]
    def route_length(owner,points):
        here=clean[owner][0];length=0.
        for p in points:
            length+=float(field(here)[pm.world_to_cell(p)]);here=p
        return length
    rc=int(math.ceil(radius/pm.CELL));ky,kx=np.mgrid[-rc:rc+1,-rc:rc+1]
    disk=((kx*pm.CELL)**2+(ky*pm.CELL)**2<=radius**2+1e-8).astype(np.float32)
    wanted=target_total # fixed initial-total quota; candidate-specific confirmed credit below
    best=None;best_rank=None
    try:
        # Initial exact path fields are reused across the at most two proposals.
        starts={k:field(clean[k][0])for k in counts}
        ranked=[]
        for sx,sy,anchor,region in corners:
            reachable=[float(np.min(starts[k][region]))for k in counts if np.any(region&np.isfinite(starts[k]))]
            if not reachable:continue
            mass=float(residual[_mask(xx,yy,[anchor],(CORNER_RADIUS_RATIO+1)*radius)].sum())
            ranked.append((mass/(1+sum(sorted(reachable)[:3])/max(1.,3*radius)),sx,sy,anchor,region))
        ranked.sort(key=lambda x:(-x[0],x[1],x[2]))
        for _,sx,sy,anchor,region in ranked[:2]:
            if time.perf_counter()>=deadline:break
            audit['attempts']+=1
            committed_cluster=sum(np.linalg.norm(p-anchor)<=CORNER_RADIUS_RATIO*radius+1e-8 for p in committed)
            wanted=max(0,target_total-int(committed_cluster))
            audit['required_suffix']=wanted
            if wanted>total:continue
            base_cluster=sum(float(np.linalg.norm(p-anchor))<=CORNER_RADIUS_RATIO*radius+1e-8 for p in baseline_points)
            # Even a previously accepted layout must survive the same current coverage/route checks.
            # Zero suffix deficit still retains the reserved clustered objective.
            old=state.get('previous_suffix',{})
            if old and all(k in old and len(old[k])==len(original[k])for k in original):
                carried={k:[np.asarray(p,float).copy()for p in old[k]]for k in original}
                carried_points=[p for ps in carried.values()for p in ps]
                carried_cluster=sum(np.linalg.norm(p-anchor)<=CORNER_RADIUS_RATIO*radius+1e-8 for p in carried_points)
                full_reference=float(np.asarray(values)[_mask(xx,yy,committed+baseline_points,radius)].sum())
                full_value=float(np.asarray(values)[_mask(xx,yy,committed+carried_points,radius)].sum())
                carried_ratio=full_value/max(1e-12,full_reference)
                good=carried_cluster>=wanted and carried_ratio+1e-8>=COVERAGE_RATIO
                good=good and all(allowed[pm.world_to_cell(p)]for p in carried_points)
                good=good and all(np.linalg.norm(p-q)>=separation-1e-8 for i,p in enumerate(carried_points)for q in carried_points[i+1:])
                if good:
                    lengths={k:route_length(k,carried[k])for k in counts}
                    good=all(math.isfinite(lengths[k])and lengths[k]<=owner_travel_budget(travel_budget,k)+1e-6 for k in counts)
                if good:
                    best=(carried,sx,sy,anchor,carried_ratio,int(carried_cluster),base_cluster)
                    best_rank=(int(carried_cluster),full_value,-sum(lengths.values()),sx,sy)
                    audit['carry_previous_suffix']=True
                    break
            order=sorted(counts,key=lambda k:(float(np.min(starts[k][region]))if np.any(region&np.isfinite(starts[k]))else math.inf,k))
            quota={k:0 for k in counts};left=wanted
            for k in order:
                quota[k]=min(counts[k],left);left-=quota[k]
            result={k:[]for k in original};spent={k:0. for k in counts};current={k:starts[k]for k in counts}
            valid=allowed.copy();remaining=residual.copy();failed=False
            for stage in[0,1]:
                demand=quota if stage==0 else counts
                for _slot in range(wanted if stage==0 else total-wanted):
                    if time.perf_counter()>=deadline:raise Budget
                    gains=cv2.filter2D(remaining,-1,disk,borderType=cv2.BORDER_CONSTANT)
                    winner=None
                    for k in sorted(counts):
                        if len(result[k])>=demand[k]:continue
                        feasible=valid & np.isfinite(current[k]) &(current[k]+spent[k]<=owner_travel_budget(travel_budget,k)+1e-8)
                        if stage==0:feasible &= region
                        if not feasible.any():continue
                        bid=gains/(1+.10*(current[k]+spent[k])/max(1.,radius))
                        bid[~feasible]=-np.inf;flat=int(np.argmax(bid));cell=np.unravel_index(flat,pm.shape)
                        key=(float(bid[cell]),-float(current[k][cell]),-float((xx[cell]-anchor[0])**2+(yy[cell]-anchor[1])**2),-k,-flat)
                        if winner is None or key>winner[0]:winner=(key,k,cell)
                    if winner is None:failed=True;break
                    _,k,cell=winner;p=pm.cell_to_world(cell)
                    spent[k]+=float(current[k][cell]);result[k].append(p.copy())
                    squared=(xx-p[0])**2+(yy-p[1])**2
                    remaining[squared<=radius**2]=0;valid &= squared>=separation**2
                    if len(result[k])<counts[k]:current[k]=field(p)
                if failed:break
            if failed or any(len(result[k])!=len(original[k])for k in original):continue
            points=[p for ps in result.values()for p in ps]
            score=float(residual[_mask(xx,yy,points,radius)].sum())
            clustered=sum(np.linalg.norm(p-anchor)<=CORNER_RADIUS_RATIO*radius+1e-8 for p in points)
            full_reference=float(np.asarray(values)[_mask(xx,yy,committed+baseline_points,radius)].sum())
            full_value=float(np.asarray(values)[_mask(xx,yy,committed+points,radius)].sum())
            ratio=full_value/max(1e-12,full_reference)
            audit['last_proposal']=dict(corner=[sx,sy],anchor=anchor.tolist(),clustered=int(clustered),wanted=wanted,coverage_ratio=ratio)
            if ratio+1e-8<COVERAGE_RATIO or clustered<wanted:continue
            if any(not allowed[pm.world_to_cell(p)]for p in points):continue
            if any(np.linalg.norm(p-q)<separation-1e-8 for i,p in enumerate(points)for q in points[i+1:]):continue
            lengths={k:route_length(k,result[k])for k in counts}
            if any(not math.isfinite(lengths[k])or lengths[k]>owner_travel_budget(travel_budget,k)+1e-6 for k in counts):continue
            rank=(int(clustered),score,-sum(lengths.values()),sx,sy)
            if best_rank is None or rank>best_rank:best=(result,sx,sy,anchor,ratio,int(clustered),base_cluster);best_rank=rank
    except Budget:audit['budget_exhausted']=True
    if best is None:return finish('no_majority_proposal_within_coverage_and_budget')
    result,sx,sy,anchor,ratio,clustered,before=best
    memory.corner_cluster_anchor=(sx,sy,float(anchor[0]),float(anchor[1]))
    audit.update(status='ACCEPTED',accepted=True,anchor=anchor.tolist(),corner=[sx,sy],radius=CORNER_RADIUS_RATIO*radius,
                 coverage_ratio=ratio,clustered=clustered,fixed_target=target_total,baseline_clustered=int(before),step=int(getattr(memory,'step',-1)))
    return finish('majority_corner_with_predicted_coverage_floor',result)
