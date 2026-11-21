"""Original versus demand delivery / early-24, with physics stepping forbidden."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import sys
import numpy as np
import pymunk
import swarm_rescue.solutions

physics_attempts=0
def no_physics(*args,**kwargs):
    global physics_attempts
    physics_attempts+=1
    raise AssertionError('Physics is forbidden in counterexample checks')
pymunk.Space.step=no_physics
parser=argparse.ArgumentParser()
parser.add_argument('archive',type=Path)
parser.add_argument('arm',choices=['original','candidate'])
args=parser.parse_args()
candidate=args.arm=='candidate'
swarm_rescue.solutions.__path__=[str(args.archive.resolve())]
from swarm_rescue.solutions.messenger_run import MessengerRun,IDLE,ACTIVE,DONE
from swarm_rescue.solutions.red_hooks import RedHooks
from swarm_rescue.solutions.lbbd_rescue import LBBDRescue
from swarm_rescue.solutions.deadline_submission import DeadlineSubmission
from swarm_rescue.solutions.pre_submit_scan import PreSubmitScan
from swarm_rescue.solutions.final_map_relay import FinalMaps

RESULTS={}
NAV=dict(forward=.2,lateral=.1,rotation=0.,grasper=0,place_bomb=0)
def noop(*args,**kwargs):pass
def drive(*args,**kwargs):return NAV.copy()
def d4():
    return NS(identifier=4,team_size=5,limit=5400,walltime_limit=180.,elapsed_walltime=75.,
              previous_inventory=0,pending_drop=None,pose=np.zeros(2),heading=0.,
              states={0:dict(point=(500.,0.),health=25,step=2200)},
              inventory_records={i:(2200,0 if i!=3 else 1) for i in range(5)},
              communicator_is_disabled=lambda:False,drive=drive,measured_velocity=lambda:np.zeros(2))
def msg(step,known=(0,1,2,4),sender=0):
    return dict(kind='two-stage',id=sender,states=(dict(id=sender,step=step),),
                red_inventory={i:(step,0 if i in known else 1) for i in range(5)})
def feed(m,d,step,known=(0,1,2,4)):
    m.receive(d,msg(step,known),step)
def tick(m,d,step):
    command=NAV.copy();controlled=m.tick(d,step,command,d.limit-step)
    return controlled,command
def starts(m):return [e for e in m.audit if e[1]=='delivery_start']

if not candidate:
    m,d=MessengerRun(),d4()
    d.inventory_records={i:(2200,0) for i in range(5)}
    tick(m,d,2200);tick(m,d,2201)
    assert m.state==ACTIVE and m.target==0
    RESULTS['source0_already_knows_all']=dict(reproduced=True,unnecessary_target=m.target)
    m,d=MessengerRun(),d4();d.states[0]['point']=(10.,0.)
    for step in range(2200,2231):tick(m,d,step)
    assert any(e[1]=='second_round' for e in m.audit)
    RESULTS['unchanged_information_restarts_tour']=dict(reproduced=True,audit=m.audit)
else:
    # Actual 0-origin knowledge is remembered before any mission can start.
    m,d=MessengerRun(),d4();d.inventory_records={i:(2200,0) for i in range(5)}
    for step in range(2200,2210):
        feed(m,d,step,range(5));tick(m,d,step)
    assert not starts(m) and m.state==IDLE
    RESULTS['source0_information_not_sent_back']=True

    m,d=MessengerRun(),d4()
    feed(m,d,2200);d.inventory_records[3]=(2201,0)
    controlled,command=tick(m,d,2204)
    assert controlled and command==NAV and len(starts(m))==1 and m.target==0
    until=m.delivery_until
    d.communicator_is_disabled=lambda:True
    for step in range(2205,until+1):
        d.inventory_records[3]=(step,0);tick(m,d,step)
    assert m.state==DONE and m.audit[-1][1]=='delivery_budget_exhausted'
    for step in range(until+1,until+30):
        d.states[0]['step']=step;d.inventory_records[3]=(step,0)
        feed(m,d,step);tick(m,d,step)
    assert len(starts(m))==1
    RESULTS['restamped_zero_and_repeated_broadcast_do_not_restart_failed_task']=True

    m,d=MessengerRun(),d4();feed(m,d,2200)
    d.inventory_records[3]=(2201,0);tick(m,d,2204)
    feed(m,d,2205,range(5));controlled,_=tick(m,d,2205)
    assert not controlled and m.state==DONE and m.audit[-1][1]=='receiver_satisfied'
    for step in range(2206,2220):
        feed(m,d,step,range(5));tick(m,d,step)
    assert len(starts(m))==1
    RESULTS['receiver_ack_or_other_route_delivery_cancels_trip']=True

    m,d=MessengerRun(),d4();feed(m,d,2200,known=(0,1,4))
    d.inventory_records[2]=(2200,1);d.inventory_records[3]=(2201,0)
    tick(m,d,2204);until=m.delivery_until
    d.inventory_records[2]=(2205,0);tick(m,d,2205)
    assert m.task_payload=={2,3} and m.delivery_until==until
    feed(m,d,2206,known=(0,1,2,4));tick(m,d,2206)
    assert m.delivery_until==until
    tick(m,d,2218)
    assert m.state==DONE
    for step in range(2219,2229):
        feed(m,d,step,known=(0,1,2,4));tick(m,d,step)
    assert len(starts(m))==1
    RESULTS['new_facts_coalesce_and_partial_ack_does_not_create_subset_retry']=True

    # A truly new missing zero fact can create one later mission.
    d.inventory_records[1]=(2230,0)
    # Existing 0 knowledge already includes 1, so this alone is not new demand.
    tick(m,d,2230);assert len(starts(m))==1
    m,d=MessengerRun(),d4();feed(m,d,2200,known=(0,4))
    d.inventory_records[1]=(2200,1);d.inventory_records[2]=(2200,1);d.inventory_records[3]=(2201,0)
    tick(m,d,2204);feed(m,d,2205,known=(0,4));tick(m,d,2205);tick(m,d,2217)
    assert m.state==DONE
    d.inventory_records[2]=(2220,0);d.states[0]['step']=2220
    tick(m,d,2220)
    assert len(starts(m))==2 and m.task_payload=={2,3}
    RESULTS['only_genuinely_new_missing_fact_allows_later_task']=True

    m,d=MessengerRun(),d4();d.states[0]['point']=(10.,0.)
    feed(m,d,2200);d.inventory_records[3]=(2201,0)
    for step in range(2204,2220):
        d.states[0]['step']=step;tick(m,d,step)
    assert not any(e[1] in ('contact','exchange_complete','receiver_satisfied') for e in m.audit)
    RESULTS['estimated_nearby_without_actual_receipt_is_not_success']=True

    m,d=MessengerRun(),d4()
    m.receive(d,msg(2100),2200)
    assert m.receiver_received_step == -1 and m.receiver_seen
    relayed=msg(2200);relayed['states']=(dict(id=1,step=2200),)
    m.receive(d,relayed,2200)
    assert m.receiver_received_step == -1
    feed(m,d,2200,range(5));feed(m,d,2201,known=(0,))
    assert m.receiver_empty==set(range(5))
    RESULTS['durable_receiver_knowledge_and_fresh_contact_are_separate']=True

    for overrides in [dict(identifier=2),dict(previous_inventory=1),dict(pending_drop=(1,(0,0),2199)),
                      dict(elapsed_walltime=172.)]:
        m,d=MessengerRun(),d4();feed(m,d,2200);d.inventory_records[3]=(2201,0)
        for k,v in overrides.items():setattr(d,k,v)
        assert not tick(m,d,2204)[0] and not starts(m)
    for step in (2159,5360):
        m,d=MessengerRun(),d4();feed(m,d,step);d.states[0]['step']=step
        d.inventory_records[3]=(step,0)
        assert not tick(m,d,step)[0] and not starts(m)
    m,d=MessengerRun(),d4();feed(m,d,2200);d.inventory_records[3]=(2201,0)
    d.states[0]['step']=2100
    assert not tick(m,d,2204)[0]
    RESULTS['activation_position_and_dual_budget_limits']=True

    # A new fact arriving exactly at expiry was not attempted by the old trip.
    m,d=MessengerRun(),d4();feed(m,d,2200,known=(0,4))
    d.inventory_records[1]=(2200,1);d.inventory_records[2]=(2200,1);d.inventory_records[3]=(2201,0)
    tick(m,d,2204);until=m.delivery_until
    d.communicator_is_disabled=lambda:True
    d.inventory_records[2]=(until,0);tick(m,d,until)
    assert m.state==DONE and 2 not in m.attempted_empty
    d.communicator_is_disabled=lambda:False;d.states[0]['step']=until+1
    tick(m,d,until+1)
    assert len(starts(m))==2 and 2 in m.task_payload
    RESULTS['new_fact_at_old_task_expiry_is_not_swallowed']=True

class Flight(RedHooks):
    def __init__(self,identifier=0):
        self.identifier,self.team_size,self.limit=identifier,5,5400
        self.walltime_limit,self.elapsed_walltime=180.,75.
        self.elapsed_timestep=2538
        self.initial_inventory,self.previous_inventory,self.pending_drop=2,0,None
        self.inventory_records={i:(2500,0) for i in range(5)}
        self.submitted=False;self.pose=np.zeros(2);self.heading=0.
        self.last_confirmed_drop_step=None
        self.deadline_submission=DeadlineSubmission();self.deadline_versions={}
        self.image=np.ones((2,2),np.uint8);self.deadline_submission.remember(2000,self.image.copy())
        self.final_maps=FinalMaps(identifier,5)
        self.map_quality,self.map_revision=8000,{4:2479}
        self.first_ready_to_submit_step=None
        self.early_submission=self.early_submission_event=None
        self.sent=[];self.base_calls=self.map_calls=self.placement_calls=0
        self.closeout=NS(state=IDLE,tick=noop)
        self.messenger=MessengerRun()
        self.states={0:dict(step=2538,point=(500.,0.),health=25)}
        self.grid=NS(pose_fixed=True);self._odometry_only=False
        self.memory=NS(observe=lambda *a:((),()),packet=lambda:(None,np.zeros((2,2)),None,None),
                       free=np.ones((2,2)),hits=np.zeros((2,2)))
        self.fine_wall_coverage=NS(observe=noop,packet=lambda:None)
        self.submission_bearings=NS(observe=noop)
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
        self.submitted_cache=None;self.final_submission_versions={}
        self.submission_elected_rank=None;self.red_submission_step=None
        self.deadline_submission_event=None
    def _sync_placement(self,step):pass
    def _update_drop_hints(self,*a):pass
    def _prepare_map_cache(self,*a):return None
    def _submission_image(self,step):
        self.map_calls+=1
        return self.image,None,{0:step}
    def submit_exploration_map(self,image):self.sent.append((self.elapsed_timestep,image.copy()))
    def lidar_values(self):return np.full(181,100.)
    def lidar_rays_angles(self):return np.linspace(-np.pi,np.pi,181)
    def semantic_values(self):return ()
    def communicator_is_disabled(self):return False
    def drive(self,*a,**kw):return NAV.copy()
    def measured_velocity(self):return np.zeros(2)
    def second_control(self,*a):
        self.placement_calls+=1
        return 'approach' if self.previous_inventory else 'none'

def base(d):
    d.base_calls+=1;return NAV.copy()
def control(d):
    with patch.object(LBBDRescue,'control',base):return RedHooks.control(d)

# Each old wait is independently capable of blocking the original version.
wait_results={}
for name in ['fixed_window','scan_wait','final_map_wait','election_wait']:
    d=Flight()
    if name!='fixed_window':d._submission_window_open=lambda step:True
    if name=='scan_wait':d.pre_submit_scan.waiting=lambda *a:True
    if name in ('final_map_wait','election_wait'):d.pre_submit_scan.waiting=lambda *a:False
    if name=='final_map_wait':d.final_maps.waiting=lambda *a:True
    if name=='election_wait':
        d.final_maps.waiting=lambda *a:False;d._prefer_own_submission=lambda step:False
    control(d)
    d.elapsed_timestep=2561;control(d);assert not d.sent
    d.elapsed_timestep=2562;control(d)
    assert bool(d.sent)==candidate
    if candidate:
        assert d.early_submission_event==dict(ready_step=2538,step=2562,collection_steps=24)
        assert d.sent[0][0]==2562
    wait_results[name]=dict(submitted=bool(d.sent),step=d.sent[0][0] if d.sent else None)
RESULTS['early_submission_bypasses_four_old_waits']=wait_results

if candidate:
    d=Flight();control(d)
    for step in range(2539,2563):
        d.inventory_records={i:(step,0) for i in range(5)}
        d.elapsed_timestep=step;control(d)
    assert len(d.sent)==1 and d.sent[0][0]==2562 and d.early_submission[0]==2538
    RESULTS['restamped_inventory_does_not_reset_24_step_clock']=True

    d=Flight();control(d);d.image[:]=0;d.elapsed_timestep=2562;control(d)
    assert np.array_equal(d.sent[0][1],np.ones((2,2),np.uint8))
    RESULTS['saved_usable_image_survives_empty_later_render']=True

    for mode in ['stock_left','pending_drop','peer_not_empty','future_report','empty_image','provisional_map','other_drone']:
        d=Flight()
        if mode=='stock_left':d.previous_inventory=1;d.inventory_records[0]=(2500,1)
        if mode=='pending_drop':d.pending_drop=(1,(0,0),2537)
        if mode=='peer_not_empty':d.inventory_records[3]=(2500,1)
        if mode=='future_report':d.inventory_records[3]=(2600,0)
        if mode=='empty_image':d.image[:]=0
        if mode=='provisional_map':d.map_quality=1000;d.map_revision={}
        if mode=='other_drone':d.identifier=1
        control(d);d.elapsed_timestep=2562;control(d)
        assert not d.sent and d.early_submission is None
    RESULTS['early_submission_requires_confirmed_clear_and_usable_map_and_drone0']=True

for step,wall,reason in [(2538,178.6,'walltime'),(5396,150.,'timestep')]:
    d=Flight();d.elapsed_timestep,d.elapsed_walltime=step,wall
    d._try_early_submission=lambda step: (_ for _ in ()).throw(AssertionError('early before hard deadline'))
    control(d)
    assert len(d.sent)==1 and d.base_calls==0 and d.deadline_submission_event['fallback']==reason
RESULTS['both_hard_deadlines_preempt_new_logic']=True

d=Flight();d.previous_inventory=1;d.inventory_records[0]=(2500,1)
control(d)
assert d.placement_calls==1 and not d.sent
RESULTS['ordinary_second_drop_review_remains_reachable']=True

if candidate:
    # Exercise source0 knowledge through the actual RedHooks receive ordering.
    d=Flight(4);d.elapsed_timestep=2544;d.inventory_records={i:(2500,1) for i in range(4)}
    d.inventory_records[4]=(2544,0);d.team_exchange_audit=[];d.drop_records={}
    d.search_reconnect=NS(record_contact=noop)
    d._receive_scan_progress=noop;d._receive_cached_map=noop
    d.placement.receive=noop;d.placement.branch_exit=NS(receive=noop)
    d.placement.local_exit=NS(receive=noop);d.placement.deep=NS(passages=NS(receive=noop))
    d.fast_closeout.receive=noop;d.team_wall.receive=noop
    d.submission_bearings.receive=noop;d.final_reconnect=NS(record=noop)
    incoming=msg(2544,range(5));incoming['red_map_bid']=None
    d.communicator=NS(received_messages=[(None,incoming)])
    with patch.object(LBBDRescue,'receive',noop):RedHooks.receive(d)
    assert d._all_inventory_empty() and d.messenger.receiver_empty==set(range(5))
    assert not tick(d.messenger,d,2544)[0] and not starts(d.messenger)
    RESULTS['actual_receive_merges_stock_before_recording_receiver_knowledge']=True

assert physics_attempts==0
print(json.dumps(dict(arm=args.arm,status='PASS',physics_steps=0,physics_step_attempts=0,full_matches=0,
    archive_sha256=sha256(args.archive.read_bytes()).hexdigest(),
    loaded_red_hooks=sys.modules[RedHooks.__module__].__file__,scenarios=RESULTS),indent=2))
