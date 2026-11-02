"""Geometry reference only: certify terminal parking does not sever known task paths.

No controller integration or multi-agent trajectory/collision guarantee. Input
is an authored/own-belief free graph, not an official map or hidden state.
"""
from collections import deque
import math
import numpy as np


def certify_waiting_sites(walkable, protected, parking, exclusion_radius,
                         max_expansions=100000):
    allowed=np.asarray(walkable,dtype=bool)
    if allowed.ndim!=2 or not math.isfinite(exclusion_radius)or exclusion_radius<0:
        raise ValueError('Invalid graph/radius')
    protected=[tuple(map(int,p))for p in protected]
    parking=[tuple(map(int,p))for p in parking]
    h,w=allowed.shape
    inside=lambda p:0<=p[0]<h and 0<=p[1]<w
    if not protected:return dict(status='ABSTAIN_NO_PROTECTED_TASK_ENDPOINTS',expanded=0)
    if any(not inside(p)or not allowed[p]for p in protected):
        return dict(status='ABSTAIN_TASK_ENDPOINT_NOT_KNOWN_FREE',expanded=0)
    if any(not inside(p)or not allowed[p]for p in parking):
        return dict(status='REJECT_PARK_NOT_KNOWN_FREE',expanded=0)
    if len(set(parking))!=len(parking)or any(math.dist(a,b)<=exclusion_radius for i,a in enumerate(parking)for b in parking[i+1:]):
        return dict(status='REJECT_PARK_SEPARATION',expanded=0)
    count=0
    def flood(mask):
        nonlocal count
        reached={protected[0]}
        queue=deque(reached)
        while queue:
            if count>=max_expansions:return None
            r,c=queue.popleft()
            count+=1
            for dr,dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                nr,nc=r+dr,c+dc
                if not(0<=nr<h and 0<=nc<w)or not mask[nr,nc]:continue
                if dr and dc and(not mask[r+dr,c]or not mask[r,c+dc]):continue
                if(nr,nc)not in reached:
                    reached.add((nr,nc))
                    queue.append((nr,nc))
        return reached
    base=flood(allowed)
    if base is None:return dict(status='ABSTAIN_EXPANSION_BUDGET',expanded=count)
    if any(p not in base for p in protected):
        return dict(status='ABSTAIN_BASE_TASK_COMPONENT_DISCONNECTED',expanded=count)
    if any(p not in base for p in parking):
        return dict(status='REJECT_PARK_NOT_REACHABLE_FROM_TASK_COMPONENT',expanded=count)
    rr,cc=np.indices(allowed.shape)
    after=allowed.copy()
    for r,c in parking:after[(rr-r)**2+(cc-c)**2<=exclusion_radius**2]=False
    if any(not after[p]for p in protected):
        return dict(status='REJECT_PARK_COVERS_TASK_ENDPOINT',expanded=count)
    reachable=flood(after)
    if reachable is None:return dict(status='ABSTAIN_EXPANSION_BUDGET',expanded=count)
    if any(p not in reachable for p in protected):
        return dict(status='REJECT_PARK_SEVERS_PROTECTED_CONNECTION',expanded=count)
    return dict(status='CERTIFIED_TERMINAL_GRAPH_ONLY',expanded=count,
                removed_cells=int(np.count_nonzero(allowed&~after)),
                protected_endpoints=len(protected),parking_sites=len(parking),
                limitation='Only final parked occupancy on current known grid. No simultaneous travel, deadlock, stale-message, pose/noise or game-score guarantee.')
