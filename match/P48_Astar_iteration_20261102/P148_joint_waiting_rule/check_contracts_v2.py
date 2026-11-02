"""Pure helper/protocol fixtures only. Aliases below are not a real SDK import."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import sys
import time
import types
import numpy as np

F=Path(__file__).resolve().parent
assert not(F/'CONTRACT_V2_FIRST.json').exists()
for name in ['swarm_rescue','swarm_rescue.solutions']:
    module=types.ModuleType(name)
    module.__path__=[]
    sys.modules[name]=module
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value
    spec.loader.exec_module(value)
    return value
module('swarm_rescue.solutions.wait_connectivity',F.parent/'P147_nonblocking_wait_reference/wait_connectivity.py')
core=module('swarm_rescue.solutions.waiting_core',F/'waiting_core_v2.py')
checks=[]
def check(name,passed,**extra):
    checks.append(dict(name=name,passed=bool(passed),**extra))
    assert passed,(name,extra)
class Memory:
    CELL=16
    width=800
    height=800
    shape=(50,50)
    def __init__(self):self.free=np.ones(self.shape,bool);self.obstacle=np.zeros(self.shape,bool)
    def blocked(self):return self.obstacle.copy()
    def world_to_cell(self,p):return(int(np.clip((self.height/2-p[1])//self.CELL,0,49)),int(np.clip((p[0]+self.width/2)//self.CELL,0,49)))
    def cell_to_world(self,rc):return np.array([(rc[1]+.5)*self.CELL-self.width/2,self.height/2-(rc[0]+.5)*self.CELL])
m=Memory()
states={0:(100,np.array([0.,-16.]),0),1:(100,np.array([16.,-16.]),0),2:(100,np.array([-180.,180.]),1)}
anchor=np.zeros(2)
protected=[np.array([-180.,180.]),np.array([180.,180.])]
digest=hashlib.sha256(m.free.tobytes()+m.obstacle.tobytes()).hexdigest()
plan,audit=core.propose_waiting_plan(m,100,0,3,states,anchor,protected,time.perf_counter()+2.)
check('joint_proposal_uses_known_cells',plan is not None and audit['proof']['status']=='CERTIFIED_TERMINAL_GRAPH_ONLY',audit=audit)
check('input_arrays_unchanged',digest==hashlib.sha256(m.free.tobytes()+m.obstacle.tobytes()).hexdigest())
def valid(p=plan,now=100,owner=1,s=states,sender=0,sent=100,rally=anchor):return core.validate_plan(p,now,owner,3,s,rally,sender,sent)
check('fresh_coordinator_plan_accepted',valid()is not None)
for name,change in [
    ('future_epoch',lambda p:p.update(epoch=101,expires=173)),
    ('bad_duration',lambda p:p.update(expires=1000)),
    ('wrong_leader',lambda p:p.update(leader=1)),
    ('bool_epoch',lambda p:p.update(epoch=True)),
    ('bool_version',lambda p:p.update(version=True)),
    ('nonfinite_goal',lambda p:p['goals'].update({1:[float('nan'),0]})),
    ('duplicate_goals',lambda p:p['goals'].update({1:p['goals'][0]})),
    ('unknown_owner',lambda p:p['goals'].update({8:[0,80]})),
    ('goal_beyond_communication_area',lambda p:p['goals'].update({1:[180,0]})),
]:
    bad=copy.deepcopy(plan);change(bad)
    check(name,valid(p=bad)is None)
check('forged_sender_rejected',valid(sender=1)is None)
check('future_envelope_rejected',valid(sent=101)is None)
check('relayed_proposal_not_mistaken_for_direct_leader',valid(sender=2)is None)
missing=dict(states);missing.pop(2)
check('missing_received_state_abstains',valid(s=missing)is None)
changed=dict(states);changed[1]=(100,np.array([16.,-16.]),1)
check('owner_inventory_change_rejects',valid(s=changed)is None)
empty={k:(100,v[1],0)for k,v in states.items()}
check('all_completed_does_not_create_waiting_delay',valid(s=empty)is None)
refreshed={k:(172,v[1],v[2])for k,v in states.items()}
check('lease_last_frame_valid',valid(now=172,s=refreshed,sent=172)is not None)
fresh173={k:(173,v[1],v[2])for k,v in states.items()}
check('lease_expiry_rejects',valid(now=173,s=fresh173,sent=173)is None)
check('anchor_drift_rejects',valid(rally=np.array([2.,0.]))is None)
check('carrying_robot_has_no_waiting_goal',valid(owner=2)is None)
check('malformed_state_abstains',core.states_valid({0:(),1:(),2:()},100,3)is False)
bad=m.obstacle.copy();m.obstacle[m.world_to_cell(protected[0])]=True
none,why=core.propose_waiting_plan(m,100,0,3,states,anchor,protected,time.perf_counter()+2.)
check('uncertain_task_endpoint_does_not_get_cleared',none is None and why['reason']=='TASK_ENDPOINT_NOT_KNOWN_FREE')
m.obstacle=bad
none,why=core.propose_waiting_plan(m,100,0,3,states,anchor,protected,time.perf_counter()-1)
check('expired_compute_budget_does_not_emit_plan',none is None and why['reason']=='BUDGET')

# Forwarding contract: a small parent is explicit, not simulator or truth.
mix=module('swarm_rescue.solutions.joint_waiting',F/'joint_waiting_v2.py')
class Parent:
    def __init__(self):
        self.identifier=1;self.pose=np.array([16.,-16.]);self.rally=anchor.copy();self.team_size=3
        self.fleet_states=dict(states);self._sortie_state='RETURN';self.submitted=False;self.qty=1;self.elapsed_timestep=100
        self.assignment_reports={};self.GOAL_LEASE_STEPS=600;self.calls=0;self.memory=m
    def carried_bombs_count(self):return self.qty
    def _plan_route(self,*args):self.calls+=1;return ['parent_path'],['parent_goal']
    def define_message_for_all(self):return {'original':True}
    def _drive(self,*args,**kwargs):return dict(forward=.1,lateral=.2,rotation=0,grasper=0,place_bomb=0)
class D(mix.JointWaitingMixin,Parent):pass
d=D();answer=d._plan_route(100,False,[])
check('carrying_route_forwarded_exactly_once',answer==(['parent_path'],['parent_goal'])and d.calls==1)
d.qty=0;d._sortie_state='SORTIE';answer=d._plan_route(101,False,[])
check('existing_mapping_sortie_kept',answer==(['parent_path'],['parent_goal'])and d.calls==2)
d._sortie_state='RETURN';d.fleet_states={}
answer=d._plan_route(102,False,[])
check('no_complete_state_keeps_parent_route',answer==(['parent_path'],['parent_goal'])and d.calls==3)
message=d.define_message_for_all()
check('original_message_fields_preserved',message['original']is True and message['waiting_plan_v1']is None)

class RouteMemory(Memory):
    def __init__(self):super().__init__();self.route_calls=0
    def route(self,pose,destination):self.route_calls+=1;return[point.copy()for point in[destination]],np.asarray(destination).copy()
rm=RouteMemory()
def ready_fixture():
    x=D();x.qty=0;x.memory=rm;x.fleet_states=dict(states);x.survey_plan=None
    x.last_peer_step={0:90};x._sortie_docked_step=50;x._waiting_plan=copy.deepcopy(plan)
    return x
x=ready_fixture();x._sortie_docked_step=None
kept=x._plan_route(100,False,[])
check('no_docking_keeps_original_mapping_route',kept==(['parent_path'],['parent_goal'])and rm.route_calls==0)
x=ready_fixture();x.last_peer_step={}
check('no_actual_map_message_keeps_original',x._plan_route(100,False,[])==(['parent_path'],['parent_goal'])and rm.route_calls==0)
x=ready_fixture();x._sortie_docked_step=90;x.last_peer_step={0:99}
check('dock_exchange_window_not_shortened',x._plan_route(100,False,[])==(['parent_path'],['parent_goal'])and rm.route_calls==0)
x=ready_fixture();x.survey_plan=(100,0,1,np.array([80.,0.]),180)
check('active_five_field_wall_survey_is_preserved',x._plan_route(100,False,[])==(['parent_path'],['parent_goal'])and rm.route_calls==0)
x=ready_fixture();answer=x._plan_route(100,False,[])
check('post_exchange_optional_wait_route_can_apply',rm.route_calls==1 and np.array_equal(answer[1],plan['goals'][1])and x._waiting_exchange_ready)
x._sortie_docked_step=None
check('completed_exchange_evidence_survives_leaving_dock',x._waiting_can_wait(101))
report=x.define_message_for_all()
check('readiness_report_carries_actual_step_and_flag',report['waiting_ready_v1']==(100,True))
alt={0:(100,np.array([-180.,180.]),1),1:(100,np.array([0.,-16.]),0),2:(100,np.array([16.,-16.]),0)}
alt_plan,alt_audit=core.propose_waiting_plan(m,100,1,3,alt,anchor,protected,time.perf_counter()+2.)
check('empty_coordinator_available_while_main_leader_carries',alt_plan is not None and alt_plan['leader']==1 and core.validate_plan(alt_plan,100,2,3,alt,anchor,1,100)is not None)
one,why=core.propose_waiting_plan(m,100,0,3,states,anchor,protected,time.perf_counter()+2.,eligible_idle={0})
check('unready_idle_peer_not_assigned',one is not None and set(one['goals'])=={0})
all_loaded={k:(100,v[1],1)for k,v in states.items()}
check('no_empty_peer_no_waiting_coordinator',core.waiting_leader(all_loaded)is None)

# Counterexample is explicitly pre-SDK and uses the unrun V1 source.
module('swarm_rescue.solutions.waiting_core',F/'waiting_core.py')
v1=module('fixture_v1_joint_waiting',F/'joint_waiting.py')
class V1D(v1.JointWaitingMixin,Parent):pass
old=V1D();old.qty=0;old.memory=rm;old.fleet_states=dict(states);old.survey_plan=(100,0,1,np.array([80.,0.]),180);old._waiting_plan=copy.deepcopy(plan)
old_answer=old._plan_route(100,False,[])
counter=dict(status='V1_PRE_SDK_SCOPE_COUNTEREXAMPLE_CONFIRMED',active_survey_was_overridden=not isinstance(old_answer[1],list)or old_answer[1]!=['parent_goal'],sdk_frames=0)
assert counter['active_survey_was_overridden']
(F/'V1_SCOPE_COUNTEREXAMPLE_FIRST.json').write_bytes((json.dumps(counter,indent=2)+'\n').encode())

out=dict(status='PASS_V2_WAITING_SCOPE_PROTOCOL_AND_FORWARDING',checks=checks,plan=plan,
         source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [F/'waiting_core_v2.py',F/'joint_waiting_v2.py']},
         scope='Authored helper arrays and explicit parent fixture; no real SDK or flight qualification.',sdk_frames=0,native_rounds=0)
(F/'CONTRACT_V2_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=out['status'],checks=len(checks),goals=plan['goals'])))
