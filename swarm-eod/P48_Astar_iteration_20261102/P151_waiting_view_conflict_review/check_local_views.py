"""Two actual P149 helper instances, different received readiness views; no SDK."""
from pathlib import Path
import hashlib,importlib.util,json,sys,time,types
import numpy as np
F=Path(__file__).resolve().parent
P=F.parent/'P149_ready_waiting_coordinator'
out=F/'COUNTEREXAMPLE_FIRST.json';assert not out.exists()
for n in['swarm_rescue','swarm_rescue.solutions']:
    m=types.ModuleType(n);m.__path__=[];sys.modules[n]=m
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
module('swarm_rescue.solutions.wait_connectivity',P/'wait_connectivity.py')
core=module('swarm_rescue.solutions.waiting_core',P/'waiting_core.py')
mix=module('swarm_rescue.solutions.joint_waiting',P/'joint_waiting.py')
class Memory:
    CELL=16; width=800;height=800;shape=(50,50)
    def __init__(self):self.free=np.ones(self.shape,bool);self.obstacle=np.zeros(self.shape,bool)
    def blocked(self):return self.obstacle.copy()
    def world_to_cell(self,p):return(int(np.clip((self.height/2-p[1])//self.CELL,0,49)),int(np.clip((p[0]+self.width/2)//self.CELL,0,49)))
    def cell_to_world(self,rc):return np.array([(rc[1]+.5)*self.CELL-self.width/2,self.height/2-(rc[0]+.5)*self.CELL])
m=Memory();rally=np.zeros(2)
ring=[m.world_to_cell(rally+80*np.array([np.cos(2*np.pi*j/12),np.sin(2*np.pi*j/12)]))for j in range(12)]
only=ring[0]
for rc in ring[1:]:m.obstacle[rc]=True
states={0:(100,np.array([-16.,0.]),0),1:(100,np.array([16.,0.]),0),2:(100,np.array([180.,180.]),1)}
protected=[np.array([-180.,180.]),np.array([180.,180.])]
class Parent:
    def __init__(self,owner):
        self.identifier=owner;self._sortie_state='DOCK';self.survey_plan=None;self._sortie_docked_step=50;self.last_peer_step={1-owner:90}
    def carried_bombs_count(self):return 0
class D(mix.JointWaitingMixin,Parent):pass
reviews=[]
for owner in[0,1]:
    d=D(owner);d._waiting_ready_reports={1-owner:(99,False),2:(99,False)}
    eligible=d._waiting_eligible(100,states)
    assert eligible=={owner}
    leader=core.waiting_leader(states,eligible)
    plan,audit=core.propose_waiting_plan(m,100,leader,3,states,rally,protected,time.perf_counter()+2.,eligible_idle=eligible)
    assert plan is not None,audit
    target=core.validate_plan(plan,100,owner,3,states,rally,owner,100,eligible_idle=eligible)
    assert target is not None
    reviews.append(dict(owner=owner,local_eligible=sorted(eligible),leader=leader,plan=plan,audit=audit,target=target.tolist()))
distance=float(np.linalg.norm(np.asarray(reviews[0]['target'])-reviews[1]['target']))
assert distance==0 and all(x['audit']['proof']['status']=='CERTIFIED_TERMINAL_GRAPH_ONLY'for x in reviews)
result=dict(status='CONFIRMED_LOCAL_READY_VIEWS_CAN_ACCEPT_OVERLAPPING_PARKS',
            actual_rule_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest()for n in['waiting_core.py','joint_waiting.py','wait_connectivity.py']},
            reviews=reviews,accepted_target_distance=distance,nominal_exclusion=core.WAIT_EXCLUSION,
            evidence='Both actual eligibility/election/proposal/validation chains accept their own plan under fresh but different readiness views; the two actual accepted target coordinates coincide.',
            scope='Authored known-free topology/protocol counterexample, not flight or official score evidence.',
            limitations=['Does not establish that this pattern occurs in the retained CROSS episode or any official map.',
                         'P149 already disclaimed distributed consensus; this proves why terminal joint graph certificates alone cannot support the desired non-overlapping waiting rule.',
                         'No SDK frames executed; no gate/seed/candidate/parent data changed.'],
            decision='Cancel pending P149 before any SDK frame if authoritative run state is still WAITING. Stop this parking branch instead of layering more protocol into the map-first baseline.',sdk_frames=0,native_rounds=0)
out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=result['status'],accepted_distance=distance,individually_certified=len(reviews))))
