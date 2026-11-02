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
    rows,cols=np.nonzero(np.asarray(memory.hits)>=2)
    hx=(cols+.5)*memory.FINE-memory.width/2
    hy=memory.height/2-(rows+.5)*memory.FINE
    out=[]
    lock=getattr(memory,'corner_cluster_anchor',None)
    for sx,sy in[(-1,-1),(-1,1),(1,-1),(1,1)]:
        if lock is not None and(sx,sy)!=tuple(lock[:2]):continue
        # Two real measured surface spans, not an assumed whole arena frame.
        vx=(np.abs(hx-sx*memory.width/2)<=2*memory.CELL)&(sy*hy>=memory.height/2-3*radius)
        hz=(np.abs(hy-sy*memory.height/2)<=2*memory.CELL)&(sx*hx>=memory.width/2-3*radius)
        if np.count_nonzero(vx)<3 or np.count_nonzero(hz)<3:continue
        if np.ptp(hy[vx])<2*memory.CELL or np.ptp(hx[hz])<2*memory.CELL:continue
        near=allowed &((xx-sx*memory.width/2)**2+(yy-sy*memory.height/2)**2<=(2*radius)**2)
        ids=np.flatnonzero(near)
        if not len(ids):continue
        if lock is None:
            distances=(xx-sx*memory.width/2)**2+(yy-sy*memory.height/2)**2
            flat=min(ids,key=lambda n:(float(distances.ravel()[n]),int(n)))
            anchor=np.array([xx.ravel()[flat],yy.ravel()[flat]])
        else:anchor=np.asarray(lock[2:4],float)
        region=allowed &((xx-anchor[0])**2+(yy-anchor[1])**2<=(CORNER_RADIUS_RATIO*radius)**2)
        out.append((sx,sy,anchor,region))
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
    wanted=max(2,int(math.ceil(MAJORITY_RATIO*total)))
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
            base_cluster=sum(float(np.linalg.norm(p-anchor))<=CORNER_RADIUS_RATIO*radius+1e-8 for p in baseline_points)
            if base_cluster>=wanted:continue
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
            ratio=score/baseline
            audit['last_proposal']=dict(corner=[sx,sy],anchor=anchor.tolist(),clustered=int(clustered),wanted=wanted,coverage_ratio=ratio)
            if score+1e-5<COVERAGE_RATIO*baseline or clustered<wanted or clustered<=base_cluster:continue
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
                 coverage_ratio=ratio,clustered=clustered,baseline_clustered=int(before),step=int(getattr(memory,'step',-1)))
    return finish('majority_corner_with_predicted_coverage_floor',result)
