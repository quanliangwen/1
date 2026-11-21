"""Real control/receive methods with synthetic sensors; no arena or physics."""
import argparse,json,sys,math
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace as NS
from unittest.mock import patch
import numpy as np
import pymunk
import swarm_rescue.solutions

physics_attempts=0
def no_physics(*a,**kw):
    global physics_attempts
    physics_attempts+=1
    raise AssertionError('Physics is forbidden')
pymunk.Space.step=no_physics
parser=argparse.ArgumentParser()
parser.add_argument('archive',type=Path)
parser.add_argument('arm',choices=['candidate'])
parser.add_argument('--output',type=Path)
args=parser.parse_args()
candidate=args.arm=='candidate'
swarm_rescue.solutions.__path__=[str(args.archive.resolve())]
from swarm_rescue.solutions.red_hooks import RedHooks
from swarm_rescue.solutions.lbbd_rescue import LBBDRescue
from swarm_rescue.solutions.coverage_placement import CoveragePlacementDrone
from swarm_rescue.solutions.deadline_submission import DeadlineSubmission
from swarm_rescue.solutions.pre_submit_scan import PreSubmitScan
from swarm_rescue.solutions.final_map_relay import FinalMaps
from swarm_rescue.solutions.greedy_mapping import MapMemory
from swarm_rescue.solutions.submission_renderer import SubmissionBearings
from swarm_rescue.solutions.return_exchange import ReturnExchange

RESULTS={}
NAV=dict(forward=.2,lateral=.1,rotation=0.,grasper=0,place_bomb=0)
def noop(*a,**kw):pass

class Grid:
    HULL_CLEARANCE=18.
    def __init__(self):
        self.evidence=np.full((256,256),-8,np.int8)
        self.clearance=np.full((256,256),64.)
        self.tight=np.zeros((256,256),bool)
        self.pose_fixed=True
        self.route_calls=0
        self.detour=[]
    def cell(self,p):return (int((p[1]+2048)//16),int((p[0]+2048)//16))
    def route(self,a,b):self.route_calls+=1;return tuple(self.detour)

class Flight(RedHooks):
    def __init__(self,identifier=0):
        self.identifier,self.team_size,self.limit=identifier,5,5400
        self.walltime_limit,self.elapsed_walltime=180.,75.
        self.elapsed_timestep=3240
        self.initial_inventory,self.previous_inventory,self.pending_drop=2,0,None
        self.inventory_records={i:(2500,0) for i in range(5)}
        self.submitted=False;self.pose=np.array([400.,0.]);self.heading=0.
        self.size_area=(2000,2000);self.states={};self.drives=[]
        self.last_confirmed_drop_step=None
        self.deadline_submission=DeadlineSubmission();self.deadline_versions={}
        self.deadline_submission.remember(2000,np.ones((32,32),np.uint8))
        self.final_maps=FinalMaps(identifier,5)
        self.map_quality,self.map_revision=8000,{4:2479}
        self.first_ready_to_submit_step=None
        self.sent=[];self.base_calls=self.map_calls=self.placement_calls=0
        self.rendered_memories=[];self.order=[]
        self.map_bids={};self.last_eligible_bid_comparison={}
        self.submission_priority_audit=self.submission_wait_started=None
        self.submission_wait_for=None
        self.closeout=NS(state='IDLE',tick=noop)
        self.messenger=NS(tick=lambda *a:False,state='IDLE',audit=[])
        self.grid=Grid();self._odometry_only=False
        self.memory=MapMemory(64,64);self.memory.free[:]=True;self.memory.hits[5,7]=3
        self.fine_wall_coverage=NS(observe=noop,packet=lambda:None,merge_direct=noop)
        self.submission_bearings=SubmissionBearings(64,64)
        self.red_packet=(2100,())
        self.pre_submit_scan=PreSubmitScan()
        self.drop_departure=NS(update=noop,steer=noop,controls_step=-1)
        self.second_drop=NS(observe_route=noop,control=self.second_control)
        self.team_wall=NS(reservation=None,steer=lambda *a:False)
        self.fast_closeout=NS(act=lambda *a:False)
        self.placement=NS(maneuvers=NS(exit=None,waiting_exit=None,approach=None,remember=noop),
                          _ordinary_start_step=lambda limit:0,finish_request=noop,update=noop)
        self.search_roaming=NS(departed=False)
        self.local_escape=NS(apply=noop)
        self.submitted_cache='old bitmap sentinel';self.final_submission_versions={}
        self.submission_elected_rank=None;self.red_submission_step=None
        self.deadline_submission_event=None
        self.drop_records={};self.team_exchange_audit=[]
        self.return_exchange=ReturnExchange();self.return_exchange.anchor=(100,200.,0.)
        self.return_exchange.trail=[(200.,0.),(300.,0.),(400.,0.)];self.return_exchange.rebuild()
    def _sync_placement(self,step):pass
    def _update_drop_hints(self,*a):pass
    def _prepare_map_cache(self,*a):return None
    def _submission_image(self,step):
        self.map_calls+=1
        return np.full((32,32),9,np.uint8),('old-cache',2100),{}
    def _render_submission(self,memory=None):
        self.order.append('render')
        actual=self.memory if memory is None else memory
        self.rendered_memories.append(actual)
        return (actual.hits>=3).astype(np.uint8)
    def submit_exploration_map(self,image):
        self.order.append('submit');self.sent.append((self.elapsed_timestep,image.copy()))
    def lidar_values(self):return None
    def lidar_rays_angles(self):return np.linspace(-np.pi,np.pi,181)
    def semantic_values(self):return ()
    def communicator_is_disabled(self):return False
    def drive(self,goal,velocity,**kw):
        self.drives.append(tuple(map(float,goal)))
        return dict(forward=0.,lateral=0.,rotation=0.,grasper=0,place_bomb=0)
    def measured_velocity(self):return np.zeros(2)
    def second_control(self,*a):
        self.placement_calls+=1
        return 'approach' if self.previous_inventory else 'none'

def base(d):
    d.base_calls+=1;d.order.append('base');return NAV.copy()
def control(d):
    with patch.object(LBBDRescue,'control',base):return RedHooks.control(d)
def try_submit(d):return RedHooks._try_return_submission(d,d.elapsed_timestep)

def marker_drone():
    d=Flight();d.return_exchange=ReturnExchange();d.pose=np.zeros(2);d.elapsed_timestep=3
    d.return_exchange.observe(d,3)
    d.pose=np.array([200.,0.]);d.elapsed_timestep=100
    points=[(220.,0.),(230.,30.),(80.,0.),(250.,0.)]
    d.states={i:dict(step=100,health=25,point=p) for i,p in enumerate(points,1)}
    return d

d=marker_drone();e=d.return_exchange;e.observe(d,100)
assert e.anchor==(100,200.,0.) and e.anchor[1:]!=e.launch and math.dist(e.launch,e.anchor[1:])>=140
marked=e.anchor;d.pose=np.array([250.,0.]);e.observe(d,101);assert e.anchor==marked
RESULTS['first_nonlaunch_split_marked_once_by_drone0']=dict(anchor=marked,audit=e.audit)

for mode in ['near_launch','stale_member','missing_member','no_gps','wall','not_split','too_far_to_broadcast','other_drone']:
    d=marker_drone()
    if mode=='near_launch':d.return_exchange.launch=(190.,0.)
    if mode=='stale_member':d.states[2]['step']=80
    if mode=='missing_member':del d.states[2]
    if mode=='no_gps':d.grid.pose_fixed=False
    if mode=='wall':d.grid.evidence[d.grid.cell(d.pose)]=3
    if mode=='not_split':
        for i,s in d.states.items():s['point']=(200.+i*10,0.)
    if mode=='too_far_to_broadcast':d.states[1]['point']=(400.,0.)
    if mode=='other_drone':d.identifier=2
    d.return_exchange.observe(d,100);assert d.return_exchange.anchor is None,mode
RESULTS['marker_rejects_launch_stale_unsafe_or_private_choices']=True

# All agents latch the same marker; relay/adoption never invents a private point.
leader=marker_drone();leader.return_exchange.observe(leader,100)
for i in range(1,5):
    d=Flight(i);d.return_exchange=ReturnExchange()
    d.return_exchange.trail=[(220.,0.),(300.,0.),(400.,0.)];d.return_exchange.rebuild()
    msg=dict(id=0,red_return_exchange=leader.return_exchange.message(leader,101))
    d.return_exchange.receive(d,msg,102)
    assert d.return_exchange.anchor==leader.return_exchange.anchor
    assert d.return_exchange.gate==(300.,0.)
    msg['red_return_exchange']['anchor']=(103,400.,50.)
    d.return_exchange.receive(d,msg,104);assert d.return_exchange.anchor==leader.return_exchange.anchor
RESULTS['five_agents_share_one_immutable_split_area']=True

d=Flight(1);e=d.return_exchange
assert not e.tick(d,3239,NAV.copy())
e.packet_built(d,3239);assert e.floor is None
d.red_packet=(3240,d.memory.packet());e.packet_built(d,3240);assert e.floor==3240
assert e.tick(d,3240,NAV.copy()) and e.phase=='RETURN' and d.drives[-1]==(300.,0.)
assert d.messenger.state=='DONE' and d.route==[] and d.search_task is None
d.search_roaming.allows=lambda *a:False
assert e.tick(d,3241,NAV.copy()) and d.drives[-1]==(300.,0.)
RESULTS['sixty_percent_starts_reverse_trail_not_exploration_no_return_rule']=True

for mode in ['stock','pending']:
    d=Flight()
    if mode=='stock':d.previous_inventory=1
    else:d.pending_drop=(1,np.zeros(2),3239)
    assert not d.return_exchange.owns(d,3240) and not d.return_exchange.tick(d,3240,NAV.copy())
RESULTS['unfinished_placement_is_not_interrupted']=True

d=Flight();e=ReturnExchange()
for p in [(200.,0.),(240.,0.),(240.,40.),(200.,40.),(200.,0.)]:
    d.pose=np.array(p);e.remember(d)
assert len(e.trail)==2 and all(math.dist(p,(200.,0.))<1e-6 for p in e.trail)
d=Flight();e=ReturnExchange()
for p in [(200.,0.),(240.,0.),(240.,40.),(200.,40.)]:d.pose=np.array(p);e.remember(d)
d.grid.evidence[:]=3;d.pose=np.array([200.,0.]);e.remember(d);assert len(e.trail)==5
RESULTS['loop_removal_requires_short_known_free_join']=True

d=Flight(1);e=d.return_exchange;d.grid.evidence[:]=3
assert e.tick(d,3240,NAV.copy()) and d.drives[-1]==tuple(d.pose) and d.grid.route_calls==1
assert e.tick(d,3241,NAV.copy()) and d.grid.route_calls==1
d.grid.evidence[:]=-8;assert e.tick(d,3242,NAV.copy()) and d.drives[-1]==(300.,0.)
RESULTS['blocked_or_unknown_reverse_segment_brakes_without_blind_wall_crossing']=True

d=Flight(1);e=d.return_exchange;e.anchor=None
assert e.tick(d,3240,NAV.copy()) and d.drives[-1]==tuple(d.pose)
msg=dict(id=0,red_return_exchange=dict(anchor=(100,200.,0.)))
e.receive(d,msg,3241)
assert e.anchor==(100,200.,0.) and e.route==[(400.,0.),(300.,0.)]
e.tick(d,3241,NAV.copy());assert d.drives[-1]==(300.,0.)
RESULTS['missing_marker_holds_and_late_marker_rebuilds_only_return_area_trail']=True

d=Flight();d.return_exchange.anchor=None
assert not d.return_exchange.tick(d,3240,NAV.copy()) and d.return_exchange.phase=='RELEASED'
d=Flight(1);d.return_exchange.anchor=None
assert d.return_exchange.tick(d,3240,NAV.copy())
assert not d.return_exchange.tick(d,3252,NAV.copy()) and d.return_exchange.phase=='RELEASED'
d=Flight(1);d.return_exchange.anchor=(100,-500.,0.)
assert not d.return_exchange.tick(d,3240,NAV.copy()) and d.return_exchange.phase=='RELEASED'
RESULTS['missing_marker_or_unrecorded_gate_does_not_wait_for_the_entire_return_budget']=True

for step,wall in [(5359,100.),(3500,172.1)]:
    d=Flight();d.elapsed_walltime=wall;e=d.return_exchange
    e.observe(d,step);assert e.phase=='RELEASED' and not e.tick(d,step,NAV.copy())
    e.observe(d,step+1);assert e.phase=='RELEASED'
RESULTS['return_cutoff_releases_to_original_submission_and_never_restarts']=True

def hub():
    d=Flight();d.pose=np.array([200.,0.]);e=d.return_exchange
    e.phase='HOLD';e.floor=3240;e.receipts={0:3240}
    return d
def peer_message(peer,packet,floor=3240,anchor=(100,200.,0.)):
    return dict(id=peer,red_map=packet,red_return_exchange=dict(anchor=anchor,active=True,
                        floor=floor,hub_ready=False,acks={}))

d=hub();e=d.return_exchange;sender=MapMemory(64,64);sender.hits[3,4]=4
msg=peer_message(1,(3241,sender.packet()))
e.receive(d,msg,3250);assert 1 not in e.receipts
d.memory.merge(msg['red_map'][1]);d.map_revision[1]=3241
e.receive(d,msg,3250);assert e.receipts[1]==3241
e.receive(d,msg,3251);assert len(e.receipts)==2
RESULTS['hub_receipt_requires_actual_merged_post_return_map_not_estimated_distance']=True

for mode in ['no_packet','old_version','future_version','wrong_anchor','inactive','bad_shape','not_at_hub']:
    d=hub();e=d.return_exchange;packet=(3241,d.memory.packet());msg=peer_message(1,packet)
    d.map_revision[1]=3241
    if mode=='no_packet':msg['red_map']=None
    if mode=='old_version':msg['red_map']=(3239,packet[1])
    if mode=='future_version':msg['red_map']=(4000,packet[1]);d.map_revision[1]=4000
    if mode=='wrong_anchor':msg['red_return_exchange']['anchor']=(101,200.,0.)
    if mode=='inactive':msg['red_return_exchange']['active']=False
    if mode=='bad_shape':
        ids,values,free,visits=packet[1];msg['red_map']=(3241,(ids,values,free,np.zeros((1,1))))
    if mode=='not_at_hub':d.pose=np.array([400.,0.])
    e.receive(d,msg,3250);assert 1 not in e.receipts,mode
RESULTS['stale_malformed_wrong_epoch_and_in_transit_maps_not_acknowledged_as_rendezvous']=True

d=Flight(2);e=d.return_exchange;e.floor=3242;e.phase='RETURN'
def ack(sender,version,anchor=e.anchor):
    return dict(id=sender,red_return_exchange=dict(anchor=anchor,hub_ready=True,acks={2:version}))
e.receive(d,ack(0,3241),3250);assert e.phase=='RETURN'
e.receive(d,ack(3,3242),3250);assert e.phase=='RETURN'
e.receive(d,ack(0,3242,(101,200.,0.)),3250);assert e.phase=='RETURN'
e.receive(d,ack(0,3242),3250);assert e.phase=='DELIVERED'
e.tick(d,3250,NAV.copy());assert d.drives[-1]==tuple(d.pose)
RESULTS['only_current_epoch_drone0_map_ack_releases_each_visitor']=True

# Real control owns the command at60%, but cannot submit simply because stock is clear.
d=Flight();d.pre_submit_scan.waiting=lambda *a:True;d.final_maps.waiting=lambda *a:True;d._prefer_own_submission=lambda *a:False
control(d);assert not d.sent and d.return_exchange.phase=='RETURN' and d.return_exchange.floor==3240
RESULTS['sixty_percent_returns_instead_of_reusing_failed_immediate_submission']=True

d=hub();e=d.return_exchange;d.elapsed_timestep=3300
e.receipts={i:3240+i for i in range(5)}
d.pre_submit_scan.waiting=lambda *a:True;d.final_maps.waiting=lambda *a:True;d._prefer_own_submission=lambda *a:False
control(d);assert not d.sent and e.complete_step==3300
d.elapsed_timestep=3301;control(d);assert not d.sent
d.elapsed_timestep=3302;control(d);assert d.sent[0][0]==3302 and d.map_calls==0
assert d.submitted_cache is None and d.order[-1]=='submit'
RESULTS['after_real_map_collection_two_tick_ack_flush_bypasses_all_old_waits']=dict(fixture_submit_step=3302)

for mode in ['peer_missing','pending','stock','own_stock','missing_inventory','future_inventory','empty_map','partial_map','other_drone']:
    d=hub();e=d.return_exchange;e.receipts={i:3240+i for i in range(5)};e.complete_step=3290;d.elapsed_timestep=3300
    if mode=='peer_missing':del e.receipts[4]
    if mode=='pending':d.pending_drop=(1,np.zeros(2),3299)
    if mode=='stock':d.inventory_records[4]=(3299,1)
    if mode=='own_stock':d.previous_inventory=1
    if mode=='missing_inventory':del d.inventory_records[2]
    if mode=='future_inventory':d.inventory_records[2]=(3301,0)
    if mode=='empty_map':d.memory.hits[:]=0
    if mode=='partial_map':d.map_quality=1000;d.map_revision={}
    if mode=='other_drone':d.identifier=1
    assert not try_submit(d) and not d.sent,mode
RESULTS['return_submission_keeps_inventory_pending_map_and_collector_guards']=True

# Actual receive merges current evidence before the rendezvous acknowledgment is recorded.
d=hub();d.elapsed_timestep=3300
d.search_reconnect=NS(record_contact=noop);d._receive_scan_progress=noop;d._receive_cached_map=noop
d.placement.receive=noop;d.placement.branch_exit=NS(receive=noop);d.placement.local_exit=NS(receive=noop)
d.placement.deep=NS(passages=NS(receive=noop));d.fast_closeout.receive=noop;d.team_wall.receive=noop
d.final_reconnect=NS(record=noop)
sender=MapMemory(64,64);sender.hits[2,3]=5
msg=peer_message(3,(3299,sender.packet()))
msg.update(kind='two-stage',red_inventory={},red_final_have=0)
d.communicator=NS(received_messages=[(None,msg)])
with patch.object(LBBDRescue,'receive',noop):RedHooks.receive(d)
assert d.map_revision[3]==3299 and d.memory.hits[2,3]==5 and d.return_exchange.receipts[3]==3299
RESULTS['actual_receive_merge_precedes_map_receipt_record']=True

calls=[]
with patch.object(LBBDRescue,'explore',lambda self:calls.append(self.elapsed_timestep)):
    d=Flight();d.elapsed_timestep=3239;RedHooks.explore(d)
    d.elapsed_timestep=3240;RedHooks.explore(d)
    d.previous_inventory=1;RedHooks.explore(d)
assert calls==[3239,3240]
RESULTS['new_exploration_stops_only_for_empty_returning_aircraft_after_threshold']=True

for step,wall,reason in [(3240,178.6,'walltime'),(5396,150.,'timestep')]:
    d=Flight();d.elapsed_timestep,d.elapsed_walltime=step,wall
    d.return_exchange.observe=lambda *a:(_ for _ in ()).throw(AssertionError('return before hard deadline'))
    control(d);assert d.deadline_submission_event['fallback']==reason and d.base_calls==0
RESULTS['both_original_hard_deadlines_preempt_new_policy']=True

d=Flight();d.previous_inventory=1;d.inventory_records[0]=(3240,1)
control(d);assert d.placement_calls==1 and not d.sent
RESULTS['ordinary_second_drop_review_entry_remains_reachable']=True

assert physics_attempts==0
result=dict(status='PASS',arm='candidate',physics_steps=0,physics_step_attempts=0,full_matches=0,map_objects_created=0,
    archive_sha256=sha256(args.archive.read_bytes()).hexdigest(),loaded_red_hooks=sys.modules[RedHooks.__module__].__file__,
    loaded_return_exchange=sys.modules[ReturnExchange.__module__].__file__,scenario_groups=len(RESULTS),scenarios=RESULTS)
if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

