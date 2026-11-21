"""Real control/receive methods with synthetic sensors; no arena or physics."""
import argparse,json,sys
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
parser.add_argument('arm',choices=['original','candidate'])
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

RESULTS={}
NAV=dict(forward=.2,lateral=.1,rotation=0.,grasper=0,place_bomb=0)
def noop(*a,**kw):pass

class Flight(RedHooks):
    def __init__(self,identifier=0):
        self.identifier,self.team_size,self.limit=identifier,5,5400
        self.walltime_limit,self.elapsed_walltime=180.,75.
        self.elapsed_timestep=3240
        self.initial_inventory,self.previous_inventory,self.pending_drop=2,0,None
        self.inventory_records={i:(2500,0) for i in range(5)}
        self.submitted=False;self.pose=np.zeros(2);self.heading=0.
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
        self.messenger=NS(tick=lambda *a:False)
        self.grid=NS(pose_fixed=True);self._odometry_only=False
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
    def second_control(self,*a):
        self.placement_calls+=1
        return 'approach' if self.previous_inventory else 'none'

def base(d):
    d.base_calls+=1;d.order.append('base');return NAV.copy()
def control(d):
    with patch.object(LBBDRescue,'control',base):return RedHooks.control(d)
def target(d):return RedHooks._try_target_submission(d,d.elapsed_timestep)

# Independently reproduce each blocking wait, then all of them together.
waits={}
for name in ['scan_wait','final_map_wait','election_wait','all_three']:
    d=Flight();called=[]
    def scan(*a):called.append('scan');return name in ['scan_wait','all_three']
    def final(*a):called.append('final');return name in ['final_map_wait','all_three']
    def election(*a):called.append('election');return False
    d.pre_submit_scan.waiting=scan;d.final_maps.waiting=final;d._prefer_own_submission=election
    control(d)
    assert bool(d.sent)==candidate
    if candidate:
        # refresh_due normally queries scan.waiting before the submission gate.
        # That query must stay; the later blocking query and both old waits must not run.
        assert d.sent[0][0]==3240 and called==['scan'] and d.map_calls==0
    waits[name]=dict(submitted=bool(d.sent),step=d.sent[0][0] if d.sent else None,
                    calls_including_normal_packet_refresh=called)
RESULTS['three_waits_individually_and_combined']=waits

# Check the fixed floor rather than the former stock-clear+24 policy.
d=Flight()
for t in [2538,2562,2753,3239]:
    d.elapsed_timestep=t;assert control(d)==NAV and not d.sent
d.elapsed_timestep=3240;control(d)
assert bool(d.sent)==candidate
RESULTS['no_early_exit_before_target']=dict(submitted_at3240=bool(d.sent),checked_steps=[2538,2562,2753,3239,3240])

# Original reaches its natural tail; this fixture is not a Map08 rollout.
if not candidate:
    d=Flight()
    for t in [3239,3240,3420,3443]:
        d.elapsed_timestep=t;control(d);assert not d.sent
    d.elapsed_timestep=3444;control(d);assert d.sent[0][0]==3444
    RESULTS['original_natural_wait_chain']=dict(fixture_submission_step=3444,not_a_match=True)

if candidate:
    # Calling twice does not submit twice; there is no 24-step timer or saved bitmap.
    d=Flight();control(d);control(d)
    assert len(d.sent)==1 and d.red_submission_step==3240 and d.base_calls==1
    assert d.submitted_cache is None and d.final_submission_versions=={}
    # The unchanged periodic deadline-backup branch may render before this exit.
    assert d.rendered_memories and all(m is d.memory for m in d.rendered_memories) and d.map_calls==0
    assert np.array_equal(d.sent[0][1],(d.memory.hits>=3).astype(np.uint8))
    RESULTS['current_render_and_single_submission_no_cached_bitmap']=dict(render_calls=len(d.rendered_memories),
        note='Includes unchanged periodic backup render; only one submission.')

    # Reject unconfirmed stock, missing/future inventory records, or a pending drop.
    rejected=[]
    for mode in ['own_stock','peer_stock','missing_peer','future_peer','negative_stamp','pending_drop','empty_map','provisional_map']:
        d=Flight()
        if mode=='own_stock':d.previous_inventory=1;d.inventory_records[0]=(2500,1)
        if mode=='peer_stock':d.inventory_records[3]=(2500,1)
        if mode=='missing_peer':del d.inventory_records[2]
        if mode=='future_peer':d.inventory_records[3]=(3241,0)
        if mode=='negative_stamp':d.inventory_records[3]=(-1,0)
        if mode=='pending_drop':d.pending_drop=(1,np.zeros(2),3240)
        if mode=='empty_map':d.memory.hits[:]=0
        if mode=='provisional_map':d.memory.free[:]=False;d.map_quality=1000;d.map_revision={}
        control(d);assert not d.sent,mode
        assert not target(d),mode
        rejected.append(mode)
    RESULTS['guard_rejections']=rejected

    # If the map becomes available later, retry with that current map, not an old saved one.
    d=Flight();d.memory.hits[:]=0;control(d);assert not d.sent
    d.memory.hits[8,11]=4;d.elapsed_timestep=3241;control(d)
    assert d.sent[0][0]==3241 and d.sent[0][1][8,11]==1 and d.map_calls==0
    RESULTS['empty_target_map_can_retry_next_step_without_timer']=True

    # Preserve the existing partial-map rule, including its fresh-peer exception.
    d=Flight();d.memory.free[:]=False;d.map_quality=1000;d.map_revision={3:3239}
    d.elapsed_timestep=3241;assert target(d) and d.sent[0][0]==3241
    RESULTS['existing_partial_map_guard_fresh_peer_exception_preserved']=True

    # Other drones retain all original waits; direct calls cannot use the new exit.
    for i in [1,2,3,4]:
        d=Flight(i);assert not target(d);control(d);assert not d.sent
    RESULTS['only_drone0_uses_new_exit']=True

    # Actual FinalMaps fusion still contributes, but no cached rendered image is selected.
    d=Flight();other=MapMemory(64,64);other.hits[12,15]=4
    d.final_maps.snapshots[1]=(1,3200,True,other.packet())
    control(d)
    assert d.sent[0][1][12,15]==1 and d.sent[0][1][5,7]==1
    assert d.memory.hits[12,15]==0 and d.final_submission_versions=={1:3200} and d.map_calls==0
    RESULTS['current_memory_plus_received_final_evidence_fused_without_cache_selection']=True

    # Exercise actual receive -> merge -> normal same-step observe -> early render ordering.
    d=Flight();d.memory.hits[:]=0
    sender=MapMemory(64,64);sender.hits[2,3]=5
    d.search_reconnect=NS(record_contact=noop);d._receive_scan_progress=noop;d._receive_cached_map=noop
    d.placement.receive=noop;d.placement.branch_exit=NS(receive=noop)
    d.placement.local_exit=NS(receive=noop);d.placement.deep=NS(passages=NS(receive=noop))
    d.fast_closeout.receive=noop;d.team_wall.receive=noop;d.final_reconnect=NS(record=noop)
    message=dict(kind='two-stage',id=3,red_map=(3239,sender.packet()),red_inventory={},
                 red_submission_bearings=(3239,np.array([1],np.int32),np.array([5],np.uint8)),red_final_have=0)
    d.communicator=NS(received_messages=[(None,message)])
    with patch.object(LBBDRescue,'receive',noop):RedHooks.receive(d)
    assert d.memory.hits[2,3]==5 and d.map_revision[3]==3239 and d.submission_bearings.bits.ravel()[1]==5
    old_observe=d.memory.observe
    def observe(*a,**kw):d.order.append('observe');return old_observe(*a,**kw)
    d.memory.observe=observe;d.lidar_values=lambda:np.full(181,20.)
    control(d)
    assert d.sent[0][1][2,3]==1 and np.count_nonzero(d.sent[0][1])>1
    assert d.order.index('observe')<d.order.index('render')<d.order.index('submit')
    RESULTS['actual_receive_and_same_frame_observation_precede_fresh_render']=True

    # Real stock-confirmation code gates the target exit; a denied placement stays unsubmitted.
    synced=[]
    for stock in [0,1]:
        d=Flight();d.previous_inventory=1;d.inventory_records[0]=(3239,1)
        d.pending_drop=(1,np.array([0.,0.]),3239);d.carried_bombs_count=lambda:stock
        d._sync_placement=lambda step:CoveragePlacementDrone._sync_placement(d,step)
        control(d)
        assert bool(d.sent)==(stock==0)
        if stock==0:assert (0,2) in d.drop_records and d.last_confirmed_drop_step==3240
        synced.append(dict(reported_stock=stock,submitted=bool(d.sent)))
    RESULTS['actual_inventory_confirmation_before_target_exit']=synced

    # Target is the existing fraction of this round's limit, not an absolute Map08 magic number.
    d=Flight();d.limit=3000;d.inventory_records={i:(1700,0) for i in range(5)}
    d.elapsed_timestep=1799;assert not target(d)
    d.elapsed_timestep=1800;assert target(d)
    RESULTS['target_scales_with_round_limit']=True

# Both real hard-budget decisions preempt base navigation and the new exit.
hard=[]
for step,wall,reason in [(3240,178.6,'walltime'),(5396,150.,'timestep')]:
    d=Flight();d.elapsed_timestep,d.elapsed_walltime=step,wall
    d._try_target_submission=lambda step:(_ for _ in ()).throw(AssertionError('target before deadline'))
    control(d)
    assert len(d.sent)==1 and d.base_calls==0 and d.deadline_submission_event['fallback']==reason
    hard.append(reason)
RESULTS['both_hard_deadlines_preempt_target_and_navigation']=hard

d=Flight();d.previous_inventory=1;d.inventory_records[0]=(3240,1)
control(d);assert d.placement_calls==1 and not d.sent
RESULTS['ordinary_second_drop_review_entry_remains_reachable']=True

assert physics_attempts==0
result=dict(status='PASS',arm=args.arm,physics_steps=0,physics_step_attempts=0,full_matches=0,
    map_objects_created=0,archive_sha256=sha256(args.archive.read_bytes()).hexdigest(),
    loaded_red_hooks=sys.modules[RedHooks.__module__].__file__,scenario_groups=len(RESULTS),scenarios=RESULTS)
if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
