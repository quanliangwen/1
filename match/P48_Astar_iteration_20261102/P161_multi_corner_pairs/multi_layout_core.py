"""Several measured corners, 2--3 bombs per corner, coverage-guarded routes.
Engineering construction on public sensor memory; not a global optimizer.
"""
import math,time,json
import cv2
import numpy as np
from swarm_rescue.solutions.geometry_route_view import GeometryPlanningMemory
from swarm_rescue.solutions.team_coverage import observed_wall_values,path_costs
from swarm_rescue.solutions.farthest_wall_cover import owner_travel_budget
COVERAGE_RATIO=.70
CORNER_RADIUS_RATIO=1.0
OPTIONAL_SECONDS=.40
MAX_CALLS=12
MIN_GROUP=2
MAX_GROUP=3

def _mask(xx,yy,points,radius):
    out=np.zeros(xx.shape,bool)
    for p in points:out|=(xx-p[0])**2+(yy-p[1])**2<=radius**2+1e-8
    return out

# INSERT_INNER_DETECTOR

def _regions(memory,walkable,xx,yy,radius,retained):
    """Geometric components precede point exclusions; an anchor is a label,
    not a mandatory new bomb position. Current measured walls still certify it.
    """
    candidates=[]
    for sx,sy,anchor,region in _inner_corners(memory,walkable,xx,yy,radius):
        candidates.append(dict(pivot=[sx,sy],anchor=anchor.tolist(),radius=float(radius),kind='inner',mask=region))
    rows,cols=np.nonzero(np.asarray(memory.hits)>=2)
    hx=(cols+.5)*memory.FINE-memory.width/2;hy=memory.height/2-(rows+.5)*memory.FINE
    for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        vx=(np.abs(hx-sx*memory.width/2)<=2*memory.CELL)&(sy*hy>=memory.height/2-3*radius)
        hz=(np.abs(hy-sy*memory.height/2)<=2*memory.CELL)&(sx*hx>=memory.width/2-3*radius)
        if np.count_nonzero(vx)<3 or np.count_nonzero(hz)<3:continue
        if np.ptp(hy[vx])<2*memory.CELL or np.ptp(hx[hz])<2*memory.CELL:continue
        distance=(xx-sx*memory.width/2)**2+(yy-sy*memory.height/2)**2
        ids=np.flatnonzero(walkable & (distance<=(2*radius)**2))
        if not len(ids):continue
        flat=min(ids,key=lambda n:(float(distance.ravel()[n]),int(n)))
        anchor=np.array([xx.ravel()[flat],yy.ravel()[flat]])
        physical=walkable & ((xx-anchor[0])**2+(yy-anchor[1])**2<=radius**2+1e-8)
        _,labels=cv2.connectedComponents(physical.astype(np.uint8),connectivity=8)
        component=int(labels[memory.world_to_cell(anchor)])
        if component:candidates.append(dict(pivot=[sx*memory.width/2,sy*memory.height/2],anchor=anchor.tolist(),radius=float(radius),kind='outer',mask=physical&(labels==component)))
    stable=[]
    for old in retained:
        try:
            anchor=np.asarray(old['anchor'],float);pivot=np.asarray(old['pivot'],float)
            if anchor.shape!=(2,)or pivot.shape!=(2,)or not np.isfinite(anchor).all():continue
            if not any(c['kind']==old['kind']and np.linalg.norm(np.asarray(c['pivot'])-pivot)<=3*memory.CELL for c in candidates):continue
            physical=walkable & ((xx-anchor[0])**2+(yy-anchor[1])**2<=radius**2+1e-8)
            _,labels=cv2.connectedComponents(physical.astype(np.uint8),connectivity=8)
            component=int(labels[memory.world_to_cell(anchor)])
            if component:stable.append(dict(pivot=pivot.tolist(),anchor=anchor.tolist(),radius=float(radius),kind=old['kind'],mask=physical&(labels==component)))
        except (KeyError,ValueError,TypeError):continue
    result=[]
    for c in stable+candidates:
        if not any(np.linalg.norm(np.asarray(c['anchor'])-np.asarray(d['anchor']))<memory.CELL for d in result):result.append(c)
    return result

def corner_cluster_layout(memory,agents,drops,radius,base,travel_budget=None,
                          forbidden_points=(),forbidden_mask=None,_prepared=None):
    start=time.perf_counter();deadline=start+OPTIONAL_SECONDS
    original={int(k):[np.asarray(p,float).copy()for p in ps]for k,ps in base.items()}
    calls=int(getattr(memory,'multi_corner_calls',0))+1;memory.multi_corner_calls=calls
    audit=dict(status='KEEP_BASE',accepted=False,call=calls,coverage_floor=COVERAGE_RATIO,radius_ratio=CORNER_RADIUS_RATIO,regions=[],attempts=0,fields=0,step=int(getattr(memory,'step',-1)))
    memory.multi_corner_diagnostics=audit
    def finish(reason,result=None):
        audit.update(reason=reason,elapsed=time.perf_counter()-start)
        if calls<=MAX_CALLS:print('[MULTI_CORNER] '+json.dumps(audit,separators=(',',':')),flush=True)
        return original if result is None else result
    if calls>MAX_CALLS:return finish('optional_call_limit')
    state=getattr(memory,'corner_policy_state',{})
    if int(state.get('initial_total',0))<=0:return finish('no_initial_capacity')
    counts={k:len(ps)for k,ps in original.items()if ps};total=sum(counts.values())
    if not total:return finish('no_unreserved_slots')
    clean={int(k):(np.asarray(p,float),int(n))for k,(p,n)in agents.items()if p is not None and int(n)>0}
    if any(k not in clean or counts[k]>clean[k][1]for k in counts):return finish('inventory_mismatch')
    pm=GeometryPlanningMemory(memory)if _prepared is None else _prepared
    values,solids=observed_wall_values(pm,radius,return_solids=True)
    walkable=pm.free & ~pm.blocked() & ~solids;allowed=walkable.copy()
    rr,cc=np.indices(pm.shape);xx=(cc+.5)*pm.CELL-pm.width/2;yy=pm.height/2-(rr+.5)*pm.CELL
    if forbidden_mask is not None:
        if np.asarray(forbidden_mask).shape!=pm.shape:return finish('forbidden_shape')
        allowed &= ~np.asarray(forbidden_mask,bool)
    separation=40.+.71*pm.CELL
    for p,exclusion in forbidden_points:allowed &= (xx-p[0])**2+(yy-p[1])**2>=float(exclusion)**2
    residual=np.asarray(values,np.float32).copy()
    for p in drops:
        squared=(xx-p[0])**2+(yy-p[1])**2;residual[squared<=radius**2]=0;allowed &= squared>=separation**2
    committed=[np.asarray(p,float)for p in state.get('confirmed',[])]+[np.asarray(p,float)for p in state.get('reserved',{}).values()]
    base_points=[p for ps in original.values()for p in ps]
    reference=float(values[_mask(xx,yy,committed+base_points,radius)].sum())
    if reference<=0 or not np.isfinite(values).all():return finish('no_positive_reference')
    corners=_regions(memory,walkable,xx,yy,radius,state.get('regions',[]))
    if len(corners)<2:return finish('fewer_than_two_measured_regions')
    audit.update(initial_total=int(state['initial_total']),planned=total,candidates=len(corners),reference=reference)
    rc=int(math.ceil(radius/pm.CELL));ky,kx=np.mgrid[-rc:rc+1,-rc:rc+1]
    disk=((kx*pm.CELL)**2+(ky*pm.CELL)**2<=radius**2+1e-8).astype(np.float32)
    fields={}
    class Budget(Exception):pass
    def field(p):
        key=tuple(pm.world_to_cell(p))
        if key not in fields:
            if time.perf_counter()>=deadline:raise Budget
            fields[key]=path_costs(pm,walkable,key);audit['fields']+=1
        return fields[key]
    def count_in(c,points):return sum(float(np.linalg.norm(p-np.asarray(c['anchor'])))<=radius+1e-8 for p in points)
    def separated(c,groups):return all(np.linalg.norm(np.asarray(c['anchor'])-np.asarray(d['anchor']))>=2*radius+separation-1e-8 for d in groups)
    def descriptor(c,number):return dict(pivot=c['pivot'],anchor=c['anchor'],radius=float(radius),kind=c['kind'],planned_count=int(number))
    def validate(result,groups):
        if any(len(result[k])!=len(original[k])for k in original):return None
        points=[p for ps in result.values()for p in ps]
        if any(not allowed[pm.world_to_cell(p)]for p in points):return None
        if any(np.linalg.norm(p-q)<separation-1e-8 for i,p in enumerate(points)for q in points[i+1:]):return None
        allpoints=committed+points;selected=[]
        for c in groups:
            number=count_in(c,allpoints)
            if not 2<=number<=3 or not separated(c,selected):return None
            selected.append(c)
        if len(selected)<2:return None
        value=float(values[_mask(xx,yy,allpoints,radius)].sum());ratio=value/reference
        if ratio+1e-8<COVERAGE_RATIO:return None
        length=0.
        for k in counts:
            here=clean[k][0];distance=0.
            for p in result[k]:distance+=float(field(here)[pm.world_to_cell(p)]);here=p
            if not math.isfinite(distance)or distance>owner_travel_budget(travel_budget,k)+1e-6:return None
            length+=distance
        ds=[descriptor(c,count_in(c,allpoints))for c in selected]
        return (value,sum(d['planned_count']for d in ds),len(ds),-length),ratio,ds
    best=None
    try:
        starts={k:field(clean[k][0])for k in counts}
        # Preserve a complete valid suffix with all its distinct corner groups.
        old=state.get('previous_suffix',{})
        retained=[c for c in corners if any(np.linalg.norm(np.asarray(c['anchor'])-np.asarray(d['anchor']))<1e-8 for d in state.get('regions',[]))]
        if retained and old and all(k in old and len(old[k])==len(original[k])for k in original):
            carried={k:[np.asarray(p,float).copy()for p in old[k]]for k in original};check=validate(carried,retained)
            if check is not None:best=(carried,check);audit['carried_suffix']=True
        for target_groups in range(2,min(5,(total+len(committed))//2)+1):
            if best is not None and audit.get('carried_suffix'):break
            if time.perf_counter()>=deadline:raise Budget
            audit['attempts']+=1
            result={k:[]for k in original};spent={k:0. for k in counts};current=dict(starts)
            valid=allowed.copy();remaining=residual.copy();groups=[];rejected=set()
            # Completed/reserved small clusters remain valid without spending again.
            for c in retained:
                if 2<=count_in(c,committed)<=3 and separated(c,groups):groups.append(c)
                if len(groups)>=target_groups:break
            def commit(assignments):
                nonlocal valid,remaining
                # Atomic bundle feasibility using the actual original distance fields.
                local_spent=dict(spent);local_current=dict(current);local_points={k:list(ps)for k,ps in result.items()}
                for k,p in assignments:
                    distance=float(local_current[k][pm.world_to_cell(p)])
                    if not math.isfinite(distance)or distance+local_spent[k]>owner_travel_budget(travel_budget,k)+1e-8:return False
                    local_spent[k]+=distance;local_points[k].append(p.copy())
                    if len(local_points[k])<counts[k]:local_current[k]=field(p)
                for k,p in assignments:
                    squared=(xx-p[0])**2+(yy-p[1])**2;remaining[squared<=radius**2]=0;valid &= squared>=separation**2
                spent.update(local_spent);current.update(local_current);result.update(local_points)
                return True
            while len(groups)<target_groups:
                if time.perf_counter()>=deadline:raise Budget
                gains=cv2.filter2D(remaining,-1,disk,borderType=cv2.BORDER_CONSTANT);winner=None
                for index,c in enumerate(corners):
                    if time.perf_counter()>=deadline:raise Budget
                    if index in rejected or not separated(c,groups):continue
                    credit=count_in(c,committed);need=max(0,2-credit)
                    if credit>3:continue
                    if need==0:
                        winner=((math.inf,0.,-index),index,c,[]);break
                    region=valid&c['mask']
                    if np.count_nonzero(region)<need:continue
                    candidates=gains.copy();candidates[~region]=-np.inf
                    for _ in range(3):
                        if time.perf_counter()>=deadline:raise Budget
                        flat=int(np.argmax(candidates));loc=np.unravel_index(flat,pm.shape)
                        if not np.isfinite(candidates[loc]):break
                        p=pm.cell_to_world(loc);assignments=[]
                        if need==1:
                            for k in counts:
                                if len(result[k])>=counts[k]:continue
                                distance=float(current[k][loc])
                                if math.isfinite(distance)and distance+spent[k]<=owner_travel_budget(travel_budget,k):assignments.append((float(gains[loc])/(1+.10*distance/max(1.,radius)),-distance,-k,[(k,p)]))
                        else:
                            second=remaining.copy();second[(xx-p[0])**2+(yy-p[1])**2<=radius**2]=0
                            gains2=cv2.filter2D(second,-1,disk,borderType=cv2.BORDER_CONSTANT)
                            legal2=region & ((xx-p[0])**2+(yy-p[1])**2>=separation**2)
                            if legal2.any():
                                gains2[~legal2]=-np.inf;loc2=np.unravel_index(int(np.argmax(gains2)),pm.shape);q=pm.cell_to_world(loc2)
                                gain=float(gains[loc]+gains2[loc2]);between=float(np.linalg.norm(p-q))
                                for k in counts:
                                    room=counts[k]-len(result[k]);distance=float(current[k][loc])
                                    if room>=2 and math.isfinite(distance)and distance+between+spent[k]<=owner_travel_budget(travel_budget,k):assignments.append((gain/(1+.10*(distance+between)/max(1.,radius)),-distance-between,-k,[(k,p),(k,q)]))
                                    if room<1 or not math.isfinite(distance):continue
                                    for j in counts:
                                        if j==k or counts[j]-len(result[j])<1:continue
                                        other=float(current[j][loc2])
                                        if math.isfinite(other)and distance+spent[k]<=owner_travel_budget(travel_budget,k)and other+spent[j]<=owner_travel_budget(travel_budget,j):assignments.append((gain/(1+.10*(distance+other)/max(1.,radius)),-distance-other,-k,[(k,p),(j,q)]))
                        if assignments:
                            chosen=max(assignments,key=lambda x:x[:3]);key=(chosen[0],chosen[1],-index)
                            if winner is None or key>winner[0]:winner=(key,index,c,chosen[3])
                        candidates[(xx-p[0])**2+(yy-p[1])**2<(2*pm.CELL)**2]=-np.inf
                if winner is None:break
                _,index,c,assignments=winner
                if commit(assignments):groups.append(c)
                else:rejected.add(index)
            if len(groups)<target_groups:continue
            # Remaining inventory fills coverage; a third point is allowed,
            # but no already selected corner may accumulate a fourth.
            while sum(len(ps)for ps in result.values())<total:
                if time.perf_counter()>=deadline:raise Budget
                gains=cv2.filter2D(remaining,-1,disk,borderType=cv2.BORDER_CONSTANT);winner=None
                cap=valid.copy();allpoints=committed+[p for ps in result.values()for p in ps]
                for c in groups:
                    if count_in(c,allpoints)>=3:cap &= ~_mask(xx,yy,[c['anchor']],radius)
                for k in counts:
                    if len(result[k])>=counts[k]:continue
                    feasible=cap & np.isfinite(current[k]) &(current[k]+spent[k]<=owner_travel_budget(travel_budget,k)+1e-8)
                    if not feasible.any():continue
                    bid=gains/(1+.10*(current[k]+spent[k])/max(1.,radius));bid[~feasible]=-np.inf;loc=np.unravel_index(int(np.argmax(bid)),pm.shape)
                    key=(float(bid[loc]),-float(current[k][loc]),-k)
                    if winner is None or key>winner[0]:winner=(key,k,pm.cell_to_world(loc))
                if winner is None:break
                if not commit([(winner[1],winner[2])]):break
            check=validate(result,groups)
            if check is not None and(best is None or check[0]>best[1][0]):best=(result,check)
    except Budget:audit['budget_exhausted']=True
    if best is None:return finish('no_two_small_clusters_with_coverage_and_routes')
    result,(rank,ratio,descriptors)=best
    memory.multi_corner_regions=descriptors
    audit.update(status='ACCEPTED',accepted=True,coverage_ratio=float(ratio),regions=descriptors,grouped=int(rank[1]),group_count=int(rank[2]))
    return finish('multiple_small_corners_coverage_guarded',result)
