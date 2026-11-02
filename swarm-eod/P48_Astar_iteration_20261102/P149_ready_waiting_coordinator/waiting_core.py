"""Optional waiting-point proposal on a received-state/known-free graph.

Finite first-feasible rule, not global optimization or a MAPF safety proof.
Only terminal parked occupancy is certified. Flight still uses original A*.
"""
import itertools
import math
import time
import numpy as np
from swarm_rescue.solutions.wait_connectivity import certify_waiting_sites

WAIT_RADIUS=80.0
WAIT_EXCLUSION=44.0
WAIT_LEASE=72
STATE_AGE=120
BUILD_AGE=24

def point(value):
    try:
        p=np.asarray(value,dtype=float)
        return p if p.shape==(2,)and np.isfinite(p).all()else None
    except (ValueError,TypeError):return None

def states_valid(states,now,n,age=STATE_AGE):
    try:
        if type(n)is not int or n<=0 or not isinstance(states,dict)or set(states)!=set(range(n)):return False
        for owner,value in states.items():
            if not isinstance(value,(tuple,list))or len(value)!=3:return False
            if type(owner)is not int or type(value[0])is not int or not 0<=now-value[0]<=age:return False
            if point(value[1])is None or type(value[2])is not int or value[2]<0:return False
        return True
    except (ValueError,TypeError,IndexError):return False

def waiting_leader(states,eligible_idle=None):
    return min((k for k,v in states.items()if v[2]==0 and(eligible_idle is None or k in eligible_idle)),default=None)

def validate_plan(plan,now,owner,n,states,rally,sender=None,sent=None,eligible_idle=None):
    """No map query or policy mutation; invalid or uncertain plan abstains."""
    try:
        if not states_valid(states,now,n):return None
        if not isinstance(plan,dict)or type(plan.get('version'))is not int or plan['version']!=1:return None
        epoch,leader,expires=plan['epoch'],plan['leader'],plan['expires']
        if any(type(x)is not int for x in [epoch,leader,expires]):return None
        if not 0<=epoch<=now<=expires or expires-epoch!=WAIT_LEASE:return None
        if leader!=waiting_leader(states,eligible_idle)or now-states[leader][0]>BUILD_AGE:return None
        if states[leader][2]!=0:return None
        if sender is not None and(type(sender)is not int or sender!=leader):return None
        if sent is not None and(type(sent)is not int or not epoch<=sent<=now):return None
        anchor=point(plan['rally'])
        current=point(rally)
        if anchor is None or current is None or np.linalg.norm(anchor-current)>1.:return None
        signature=tuple((k,states[k][2])for k in sorted(states))
        if tuple(tuple(v)for v in plan['inventories'])!=signature:return None
        if states[owner][2]!=0 or not any(v[2]>0 for v in states.values()):return None
        goals=plan['goals']
        if not isinstance(goals,dict)or owner not in goals:return None
        parsed={}
        for k,v in goals.items():
            if type(k)is not int or k not in states or states[k][2]!=0:return None
            p=point(v)
            if p is None or np.linalg.norm(p-anchor)>100.:return None
            parsed[k]=p
        if any(np.linalg.norm(a-b)<=WAIT_EXCLUSION for i,a in enumerate(parsed.values())for b in list(parsed.values())[i+1:]):return None
        return parsed[owner].copy()
    except (KeyError,IndexError,TypeError,ValueError,OverflowError):return None

def propose_waiting_plan(memory,now,leader,n,states,rally,protected,deadline,eligible_idle=None):
    """Bounded joint proposal; no clearing/forcing of uncertain occupied cells."""
    audit=dict(status='ABSTAIN',tested_sets=0)
    if not states_valid(states,now,n,BUILD_AGE)or leader!=waiting_leader(states,eligible_idle)or states[leader][2]!=0:return None,dict(audit,reason='STATE_OR_LEADER')
    centre=point(rally)
    if centre is None:return None,dict(audit,reason='NO_RALLY')
    if any(point(p)is None or abs(float(p[0]))>=memory.width/2 or abs(float(p[1]))>=memory.height/2 for p in [centre,*protected]):
        return None,dict(audit,reason='ENDPOINT_OUTSIDE_PUBLIC_ARENA')
    idle=[k for k in sorted(states)if states[k][2]==0 and np.linalg.norm(np.asarray(states[k][1])-centre)<=120. and(eligible_idle is None or k in eligible_idle)]
    if not idle or not any(v[2]>0 for v in states.values()):return None,dict(audit,reason='NO_WAITING_SCOPE')
    if not protected:return None,dict(audit,reason='NO_KNOWN_TASK_ENDPOINTS')
    if time.perf_counter()>=deadline:return None,dict(audit,reason='BUDGET')
    allowed=np.asarray(memory.free,dtype=bool)&~np.asarray(memory.blocked(),dtype=bool)
    anchors=list(dict.fromkeys(memory.world_to_cell(p)for p in protected))
    if len(anchors)<2:return None,dict(audit,reason='NO_DISTINCT_TASK_ENDPOINTS')
    if any(not allowed[p]for p in anchors):return None,dict(audit,reason='TASK_ENDPOINT_NOT_KNOWN_FREE')
    candidates=[]
    for j in range(12):
        p=centre+WAIT_RADIUS*np.array([math.cos(2*math.pi*j/12),math.sin(2*math.pi*j/12)])
        rc=tuple(memory.world_to_cell(p))
        world=np.asarray(memory.cell_to_world(rc))
        if allowed[rc]and np.linalg.norm(world-centre)<=100 and rc not in candidates:
            candidates.append(rc)
    if len(candidates)<len(idle):return None,dict(audit,reason='NOT_ENOUGH_KNOWN_WAITING_CELLS',candidate_count=len(candidates))
    choices=[]
    for owner in idle:
        ideal=centre+WAIT_RADIUS*np.array([math.cos(2*math.pi*owner/n),math.sin(2*math.pi*owner/n)])
        here=np.asarray(states[owner][1])
        ranked=sorted(candidates,key=lambda rc:(float(np.sum((memory.cell_to_world(rc)-ideal)**2)+.25*np.sum((memory.cell_to_world(rc)-here)**2)),rc))
        choices.append(ranked[:4])
    seen=set()
    for arrangement in itertools.product(*choices):
        if time.perf_counter()>=deadline:return None,dict(audit,reason='BUDGET',candidate_count=len(candidates))
        if len(set(arrangement))!=len(arrangement):continue
        key=tuple(sorted(arrangement))
        if key in seen:continue
        seen.add(key)
        audit['tested_sets']+=1
        proof=certify_waiting_sites(allowed,anchors,arrangement,WAIT_EXCLUSION/float(memory.CELL),max_expansions=16000)
        if proof['status']=='CERTIFIED_TERMINAL_GRAPH_ONLY':
            plan=dict(version=1,epoch=int(now),leader=int(leader),expires=int(now)+WAIT_LEASE,
                      rally=centre.tolist(),inventories=[(k,states[k][2])for k in sorted(states)],
                      goals={owner:np.asarray(memory.cell_to_world(rc)).tolist()for owner,rc in zip(idle,arrangement)})
            return plan,dict(audit,status='JOINT_TERMINAL_PROPOSAL',candidate_count=len(candidates),proof=proof)
        if audit['tested_sets']>=16:break
    return None,dict(audit,reason='NO_CERTIFIED_SET_WITHIN_FINITE_RULE',candidate_count=len(candidates))
