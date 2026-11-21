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
pymunk.Space.__init__=no_physics
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
from swarm_rescue.solutions.group_exchange import GroupExchange
from swarm_rescue.solutions.exchange_plan import known_segment
from swarm_rescue.solutions.map_candidates import digest, frozen
from swarm_rescue.solutions.red_hooks import local_score

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
        self.group_best_image=None
        self.group_exchange=GroupExchange(identifier,5,5400,(64,64))
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
        return np.repeat(np.repeat((actual.hits>=3).astype(np.uint8),2,axis=0),2,axis=1)[:actual.height,:actual.width]
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


def ready(owner=0):
    d=Flight(owner);g=d.group_exchange;p=g.plan
    p.root=(100,200.,0.);p.acks=set(range(5))
    p.trail=[(200.,0.),(300.,0.),(400.,0.)]
    return d,g


def committed(owner=0):
    d,g=ready(owner);intent=g.prepare_return(d,3240);assert intent is not None
    g.commit_return(d,intent,3240)
    # Earlier protocol cases use a shortened existing-window fixture.
    # New finish-gate cases below restore the real 3420+24 window.
    d.pre_submit_scan.finish=lambda drone:3276
    return d,g


def check(name, method):
    method();RESULTS[name]='PASS'


def no_marker():
    d=Flight();g=d.group_exchange
    d.route=[(9,8)];d.search_task=NS(started=11);d.messenger.state='ACTIVE'
    before=(list(d.route),d.search_task,d.messenger.state,list(d.messenger.audit))
    assert g.prepare_return(d,3240) is None
    assert (d.route,d.search_task,d.messenger.state,d.messenger.audit)==before
check('P03_no_root_does_not_cancel_original_mission',no_marker)


def end_drone():
    d=Flight();p=d.group_exchange.plan;p.observe(d,3)
    d.pose=np.array([600.,0.]);p.observe(d,100)
    assert p.root==(100,600.,0.) # No all-team span or radius-about-zero rule.
check('P01_endpoint_leader_records_without_team_radius',end_drone)


def async_root():
    d,g=ready(3);g.plan.acks=set()
    body=dict(epoch=g.plan.epoch,root=g.plan.root,acks=(0,1),step=100,point=(300.,0.),edges={},fixed=True)
    g.plan.receive(d,dict(id=0),body,100)
    body.update(acks=(2,4),step=140)
    g.plan.receive(d,dict(id=2),body,140)
    g.plan.observe(d,141)
    assert g.plan.committed()
check('P09_asynchronous_multihop_root_ack',async_root)


def unknown_ack():
    d,g=ready();g.plan.acks={0,1,2,3}
    assert not g.plan.committed() and g.prepare_return(d,3240) is None
check('P10_missing_acceptance_not_global_commit',unknown_ack)


def direct_only():
    d,g=ready();body=dict(epoch=g.plan.epoch,step=100,point=(400.,0.),fixed=True)
    g.receive(d,dict(id=1,states=({'id':4,'step':100,'point':(400.,0.)},),red_group_exchange=body),100)
    assert 1 in g.plan.direct and 4 not in g.plan.direct
check('P04_relayed_third_party_is_not_direct_contact',direct_only)


def near_no_packet():
    d,g=ready();d.states={1:dict(point=(401,0),step=100)}
    g.observe(d,100);assert not g.plan.direct and not g.candidates.receipts
check('P05_no_communication_without_received_message',near_no_packet)


def root_no_local():
    d,g=ready();g.plan.branch_group=(0,1);g.plan.local_region=(900.,900.)
    intent=g.prepare_return(d,3240);assert intent.target==(200.,0.) and intent.group==(0,)
check('P02_local_missing_falls_back_shared_root',root_no_local)


def conflict():
    d,g=ready();root=g.plan.root
    g.receive(d,dict(id=1,red_group_exchange=dict(epoch=g.plan.epoch,step=100,point=(300,0),
              root=(90,-500.,0.),acks=(0,1,2,3,4))),100)
    assert g.plan.root==root
check('P08_conflicting_middle_point_cannot_replace_root',conflict)


def branches():
    for group in [(0,1,2,3),(0,3),(1,2)]:
        owner=group[0];d,g=ready(owner);p=g.plan
        for a,b in zip(group,group[1:]):p.edges[(a,b)]=(100,(250.,0.))
        p.observe(d,100);p.observe(d,140)
        assert p.branch_group==group,(group,p.branch_group)
check('P06_actual_4plus1_2plus2plus1_branch_members',branches)


def single_loss():
    d,g=ready();g.plan.edges={(0,1):(100,(200.,0.))}
    g.plan.observe(d,100);g.plan.observe(d,101)
    assert g.plan.branch_group==(0,)
check('P07_one_frame_not_stable_split',single_loss)


def drop_gates():
    for stock,pending in [(1,None),(0,(1,np.zeros(2),3239))]:
        d,g=ready();d.previous_inventory=stock;d.pending_drop=pending
        assert g.prepare_return(d,3240) is None
    d,g=ready();assert g.prepare_return(d,3239) is None
check('T01_actual_stock_pending_and_60percent_gate',drop_gates)


def escape():
    d,g=ready();d.placement.maneuvers.exit=NS()
    assert g.prepare_return(d,3240) is None
check('T02_post_drop_escape_priority',escape)


def duplicate():
    d,g=committed();before=(g.started_step,list(g.route),list(d.messenger.audit))
    for step in range(3241,3341):assert g.prepare_return(d,step) is None
    assert before==(g.started_step,g.route,d.messenger.audit)
check('T03_repeats_never_restart_mission_or_timer',duplicate)


def late_root():
    d,g=committed();d.pose=np.array([300.,0.]);g.go_root(d,3300)
    assert g.phase=='COURIER_TO_C' and g.target==(200.,0.)
check('T04_late_member_uses_shared_C_not_old_peer_position',late_root)


def passive_late_delivery():
    d,g=ready(1);g.plan.trail=[(200.,0.),(300.,0.),(400.,0.)]
    d.elapsed_timestep=4501
    d.route=[(123,456)];d.search_task=NS(started=99);d.messenger.state='ACTIVE'
    old=(list(d.route),d.search_task,d.messenger.state)
    g.observe(d,4501)
    assert g.prepare_return(d,4501) is None
    assert not g.owns_navigation and (d.route,d.search_task,d.messenger.state)==old
    assert 1 in g.candidates.snapshots and 1 in g.candidates.images
    g.peer_status[4]=dict(step=4501,have=set())
    assert g.message(d,4501)['payload'] is not None
check('T08_late_no_budget_can_deliver_at_contact_without_cancelling_navigation',passive_late_delivery)


def blocked():
    d,g=committed();d.grid.evidence[:]=3
    cmd=NAV.copy();assert g.tick_navigation(d,3241,cmd,None,())
    assert d.drives[-1]==tuple(d.pose)
    assert not g.tick_navigation(d,3281,cmd,None,()) and g.phase=='ABORT'
check('T05_blocked_route_brakes_then_bounded_abort',blocked)


def avoidance():
    d,g=committed();g.phase='DELIVERED_HOLD';g.hold=tuple(d.pose);g.route=[]
    calls=[];d.local_escape.apply=lambda *a:calls.append(a)
    assert g.tick_navigation(d,3241,NAV.copy(),None,()) and calls
check('T06_delivered_hold_keeps_existing_avoidance',avoidance)


def cutoff():
    d,g=committed();assert not g.ordinary_submit_allowed(d,3300)
    g.observe(d,4590)
    assert not g.owns_navigation and g.ordinary_submit_allowed(d,4590)
    d.inventory_records[4]=(2500,1)
    assert not g.try_submit(d,4590,local_score)
check('T07_cutoff_releases_control_without_faking_team_clear',cutoff)


def manifest_only():
    d,g=committed();payload=g.candidates.snapshots[0]
    body=dict(epoch=g.plan.epoch,step=3241,point=(400.,0.),manifest=(('snapshot',4,3240,payload['digest']),))
    g.receive(d,dict(id=1,red_group_exchange=body),3241)
    assert set(g.candidates.snapshots)=={0} and not g.candidates.receipts
check('M01_manifest_not_actual_payload_receipt',manifest_only)


def corrupt():
    d,g=committed();other,h=committed(1);payload=h.candidates.snapshots[1]
    bad=dict(payload,digest='f'*64)
    assert not g.candidates.receive(d,1,('snapshot',bad),3242)
    bad=dict(payload,bearings=np.zeros((1,1),np.uint8));bad['digest']=digest({k:v for k,v in bad.items() if k!='digest'})
    assert not g.candidates.receive(d,1,('snapshot',bad),3242)
    assert 1 not in g.candidates.snapshots
check('M02_digest_and_shape_validation',corrupt)


def duplicate_payload():
    d,g=committed();other,h=committed(1);payload=h.candidates.snapshots[1]
    assert g.candidates.receive(d,1,('snapshot',payload),3242)
    before=d.memory.hits.copy();n=len(g.candidates.audit)
    assert g.candidates.receive(d,1,('snapshot',payload),3243)
    assert len(g.candidates.audit)==n and np.array_equal(before,d.memory.hits)
    bad=dict(payload,digest='0'*64);assert not g.candidates.receive(d,1,('snapshot',bad),3244)
check('M03_duplicate_idempotent_same_version_conflict_rejected',duplicate_payload)


def no_echo():
    d,g=committed();have=set(g.candidates.manifest())
    assert g.candidates.payload(3242,[have]) is None
check('M04_do_not_send_payload_back_to_existing_holder',no_echo)


def freeze_versions():
    d,g=committed();data=g.candidates.snapshots[0];before=data['digest'];bits=data['bearings'].copy()
    d.memory.hits[:]=7;d.submission_bearings.bits[:]=255
    assert digest({k:v for k,v in data.items() if k!='digest'})==before
    assert np.array_equal(data['bearings'],bits) and not data['bearings'].flags.writeable
check('M05_memory_and_bearings_frozen_together',freeze_versions)


def long_delivery():
    d,g=committed();other,h=committed(1)
    assert g.candidates.receive(d,1,('snapshot',h.candidates.snapshots[1]),4100)
    from swarm_rescue.solutions.red_hooks import cached_eligible
    assert not cached_eligible(4100,3240,4100)
check('M06_epoch_payload_survives_480steps_old_TTL_unchanged',long_delivery)


def owner_not_quality():
    d,g=committed();g.candidates.add_image(0,3240,np.ones((64,64)),{0:'x',1:'y'},3240)
    g.candidates.choose(d,3242,local_score,fusion=False)
    assert len(g.candidates.score_table)==1
check('M07_multiple_sources_not_quality_score_bonus',owner_not_quality)


def stock_first():
    d,g=committed();assert not g.candidates.images
    msg=g.message(d,3241)
    assert msg['receipts'] and msg['choice'] is None
    # Stock is in original red_inventory independently from this large payload.
    assert d.inventory_records[0][1]==0
check('M08_snapshot_build_does_not_gate_stock_records',stock_first)


def ranking():
    d,g=committed();good=np.zeros((64,64),np.uint8);good[10:12,14:16]=1
    bad=np.ones((64,64),np.uint8)
    g.candidates.add_image(1,3240,good,{1:'a'},3240)
    g.candidates.add_image(2,3241,bad,{2:'b'},3241)
    chosen=g.candidates.choose(d,3300,local_score,fusion=False)
    assert chosen['owner']==1 and len(g.candidates.score_table)==2
    assert g.candidates.reference_digest==digest(d.memory.hits>=3)
check('Q01_Q02_common_reference_can_choose_individual_over_more_walls',ranking)


def fill(d,g):
    d._render_submission=lambda memory=None:np.ones((64,64),np.uint8)
    for i in range(5):
        other,h=committed(i)
        g.candidates.receive(d,i if i!=d.identifier else (i+1)%5,('snapshot',h.candidates.snapshots[i]),3300)
        good=np.zeros((64,64),np.uint8);good[10:12,14:16]=1
        g.candidates.add_image(i,3240+i,good if i==1 else np.ones((64,64),np.uint8),{i:'e'},3300)
    g.candidates.fusion_built=True


def proxy():
    d,g=committed(4);fill(d,g)
    assert not g.try_submit(d,3300,local_score)
    assert not g.try_submit(d,3302,local_score)
    assert g.choice['image_owner']==1 and g.choice['executor']==4
    assert g.try_submit(d,3304,local_score)
    assert d.red_submission_step==3304 and g.phase=='SUBMITTED'
check('Q03_Q04_nonzero_executor_can_submit_other_owners_best_image',proxy)


def old_final_nonempty():
    d,g=committed();fill(d,g);g.candidates.install(d,1,3300)
    d.final_maps.snapshots[4]=(1,())
    image,cache,versions=RedHooks._submission_image(d,3300)
    assert np.array_equal(image,g.candidates.image(1)) and cache[1]==1
    assert d.deadline_submission.image is image
check('Q05_old_FinalMaps_cannot_override_new_selected_image',old_final_nonempty)


def waits():
    d,g=committed();fill(d,g)
    d.pre_submit_scan.waiting=lambda *a:(_ for _ in ()).throw(AssertionError('old scan wait'))
    d.final_maps.waiting=lambda *a:(_ for _ in ()).throw(AssertionError('old final wait'))
    d._prefer_own_submission=lambda *a:(_ for _ in ()).throw(AssertionError('old bid wait'))
    assert not g.try_submit(d,3300,local_score)
    assert not g.try_submit(d,3302,local_score) and g.try_submit(d,3304,local_score)
check('S01_new_exit_not_blocked_by_old_three_windows',waits)


def fast_gate():
    from swarm_rescue.solutions.fast_closeout import FastCloseout
    d,g=committed();f=FastCloseout(0,5)
    assert not f.submit(d,3300)
check('S02_old_fast_submission_blocked_without_touching_drop_code',fast_gate)


def hard_deadline():
    d,g=committed();fill(d,g);g.candidates.install(d,1,3300)
    d.elapsed_walltime=179.;d.elapsed_timestep=4000
    assert RedHooks._force_deadline_submission(d,4000)
    assert d.sent and np.array_equal(d.sent[0][1],g.candidates.image(1))
check('S03_hard_wall_deadline_precedes_unfinished_election',hard_deadline)


def no_heavy_fit():
    d,g=committed();g.candidates.add_image(0,3240,np.eye(64,dtype=np.uint8),{},3240)
    d.elapsed_walltime=175.
    with patch.object(SubmissionBearings,'render',side_effect=AssertionError('new fit')):
        g.candidates.choose(d,4590,local_score,fusion=False)
check('S04_low_budget_uses_existing_images_without_new_fit',no_heavy_fit)


def lease():
    d,g=committed();fill(d,g);g.try_submit(d,3300,local_score);g.try_submit(d,3302,local_score)
    choice=g.choice
    assert g.valid_choice(choice,3302)
    bad=dict(choice,executor=4);assert not g.valid_choice(bad,3302)
    d4,g4=committed(4);fill(d4,g4);g4.choice=choice;g4.choice_acks={4}
    assert not g4.try_submit(d4,3302,local_score)
check('S05_choice_digest_and_executor_lease',lease)


def disabled():
    d=Flight();d.group_exchange=None
    control(d)
    assert not d.sent and d.base_calls==1
check('R01_disabled_feature_preserves_ordinary_scan_wait',disabled)


def control_handoff():
    d,g=ready();cmd=control(d)
    assert g.started_step==3240 and g.owns_navigation and d.drives
    d,g=ready();d.previous_inventory=1;d.inventory_records[0]=(2500,1)
    control(d);assert g.started_step is None and d.placement_calls==1
check('control_integration_returns_and_keeps_second_drop_path_for_loaded_drone',control_handoff)


def partial(owner=0,phase='RETURN_LOCAL'):
    d,g=committed(owner);g.phase=phase
    good=np.zeros((64,64),np.uint8);good[10:12,14:16]=1
    g.candidates.add_image(owner,3240,good,{owner:'own'},3300)
    other=(owner+1)%5
    peer,h=committed(other)
    assert g.candidates.receive(d,other,('snapshot',h.candidates.snapshots[other]),3300)
    g.candidates.add_image(other,3240,np.ones((64,64),np.uint8),{other:'peer'},3300)
    return d,g


def phase_eligibility():
    for phase in ['RETURN_LOCAL','LOCAL_EXCHANGE','COURIER_TO_C','INTERGROUP_EXCHANGE','DELIVERED_HOLD','ABORT','OBSERVE']:
        d,g=partial(phase=phase)
        assert not g.ordinary_submit_allowed(d,3300),phase
        assert g.ordinary_submit_allowed(d,4590),phase
        assert not g.try_submit(d,3300,local_score)
        assert not g.try_submit(d,3302,local_score)
        assert g.try_submit(d,3304,local_score),phase
check('B01_returning_and_aborted_use_identical_eligibility_and_submission_step',phase_eligibility)


def incomplete_pool():
    d,g=partial()
    assert not g.complete() and set(g.candidates.images)=={0,1}
    g.try_submit(d,3300,local_score)
    assert g.candidates.best is not None and d.group_best_image is not None
    g.try_submit(d,3302,local_score)
    assert g.try_submit(d,3304,local_score) and not g.complete()
check('B02_two_personal_candidates_compared_and_submitted_without_five_sources',incomplete_pool)


def compare_before_clear():
    d,g=partial();d.inventory_records[4]=(3299,1)
    assert not g.try_submit(d,3300,local_score)
    assert d.group_best_image is not None and d.deadline_submission.image is not None
    assert g.choice is None and not d.sent
    d.inventory_records[4]=(3310,0)
    assert not g.try_submit(d,3310,local_score)
    assert not g.try_submit(d,3312,local_score)
    assert g.try_submit(d,3314,local_score)
check('B03_cache_before_team_clear_but_never_submit_unconfirmed_stock',compare_before_clear)


def pending_veto():
    d,g=partial();g.try_submit(d,3300,local_score);g.try_submit(d,3302,local_score)
    d.pending_drop=(1,np.zeros(2),3303)
    assert not g.try_submit(d,3304,local_score) and not d.sent
check('B04_pending_drop_still_vetoes_ordinary_submission',pending_veto)


def preserve_originals():
    d,g=partial();before={i:(v['digest'],g.candidates.image(i).copy()) for i,v in g.candidates.images.items()}
    g.try_submit(d,3300,local_score)
    g.candidates.remember_live(3350,np.ones((64,64),np.uint8))
    d.inventory_records[4]=(3349,1);g.try_submit(d,3350,local_score)
    assert not g.candidates.add_image(0,3350,np.ones((64,64),np.uint8),{},3350)
    for i,(checksum,image) in before.items():
        assert g.candidates.images[i]['digest']==checksum
        assert np.array_equal(g.candidates.image(i),image)
check('B05_comparison_and_live_refresh_do_not_overwrite_personal_originals',preserve_originals)


def refresh_live():
    d,g=partial();d.inventory_records[4]=(3299,1)
    g.try_submit(d,3300,local_score);old=g.best_installed
    d.memory.hits[20,20]=3
    good=np.zeros((64,64),np.uint8);good[10:12,14:16]=1;good[40:42,40:42]=1
    g.candidates.remember_live(3350,good)
    with patch.object(SubmissionBearings,'render',side_effect=AssertionError('existing live image must be reused')):
        assert not g.try_submit(d,3350,local_score)
    assert g.best_installed!=old and g.candidates.best['owner']==5
    assert np.array_equal(d.deadline_submission.image,good)
check('B06_new_existing_live_image_triggers_rescore_and_updates_emergency_cache',refresh_live)


def repeated_payload():
    d,g=partial();g.try_submit(d,3300,local_score);g.try_submit(d,3302,local_score)
    key=g.choice['key'];created=g.choice['created']
    for _ in range(100):
        assert g.candidates.receive(d,1,('snapshot',g.candidates.snapshots[1]),3303)
    assert not g.try_submit(d,3303,local_score)
    assert g.choice['key']==key and g.choice['created']==created
    assert g.try_submit(d,3304,local_score)
check('B07_repeated_payloads_do_not_restart_selection_or_choice_timer',repeated_payload)


def new_candidate():
    d,g=partial();g.try_submit(d,3300,local_score);g.try_submit(d,3302,local_score)
    old=g.choice['key']
    # Additional immutable candidate means actual new input, not a duplicate.
    image=g.candidates.image(0)
    g.candidates.add_image(2,3303,image,{2:'new'},3303)
    assert not g.try_submit(d,3303,local_score) and g.choice is None
    assert not g.try_submit(d,3305,local_score) and g.choice['key']!=old
    assert g.try_submit(d,3307,local_score)
check('B08_genuine_new_candidate_recompares_before_actual_submission',new_candidate)


def local_live_slot():
    d,g=partial();g.try_submit(d,3300,local_score)
    assert 5 in g.candidates.images and all(v[1]<5 for v in g.candidates.manifest())
    peer,h=partial(1)
    assert not h.candidates.receive(peer,0,('image',g.candidates.images[5]),3301)
check('B09_local_current_slot_does_not_collide_with_shared_personal_images',local_live_slot)


def hard_steps():
    d,g=partial();d.inventory_records[4]=(3299,1);g.try_submit(d,3300,local_score)
    d.elapsed_timestep=5396;d.elapsed_walltime=100
    with patch.object(SubmissionBearings,'render',side_effect=AssertionError('hard deadline must use cache')):
        assert RedHooks._force_deadline_submission(d,5396)
    assert d.deadline_submission_event['fallback']=='timestep' and d.sent
check('B10_timestep_fallback_uses_compared_cache_even_when_team_confirmation_missing',hard_steps)


def empty_pool():
    d,g=committed();backup=d.deadline_submission.backup_image.copy()
    g.candidates.add_image(0,3240,np.zeros((64,64),np.uint8),{},3300)
    with patch.object(SubmissionBearings,'render',return_value=np.zeros((64,64),np.uint8)):
        assert not g.try_submit(d,3300,local_score)
    assert d.group_best_image is None and d.deadline_submission.image is None
    assert np.array_equal(d.deadline_submission.backup_image,backup)
check('B11_empty_candidates_do_not_poison_valid_emergency_backup',empty_pool)


def comparison_not_navigation():
    d,g=partial();d.inventory_records[4]=(3299,1)
    before=(g.phase,list(g.route),d.messenger.state,list(d.drives),d.search_task)
    g.try_submit(d,3300,local_score)
    assert before==(g.phase,g.route,d.messenger.state,d.drives,d.search_task)
check('B12_pre_submit_comparison_does_not_change_navigation_ownership_or_commands',comparison_not_navigation)


def window_gate():
    d,g=partial();d._submission_window_open=lambda step:False
    for step in [3300,3302,3304]:assert not g.try_submit(d,step,local_score)
    assert d.group_best_image is not None and not d.sent
check('B13_existing_submission_window_check_is_preserved',window_gate)


def connected_election():
    d0,g0=partial(0);d1,g1=partial(1)
    g0.try_submit(d0,3300,local_score);g1.try_submit(d1,3300,local_score)
    d0.elapsed_timestep=3301;body=g0.message(d0,3301)
    g1.receive(d1,dict(id=0,red_group_exchange=body),3301)
    assert not g1.try_submit(d1,3302,local_score) and g1.choice is None
    assert not g0.try_submit(d0,3302,local_score)
    d0.elapsed_timestep=3303;body=g0.message(d0,3303)
    g1.receive(d1,dict(id=0,red_group_exchange=body),3303)
    assert g1.choice['executor']==0 and not g1.try_submit(d1,3304,local_score)
    assert g0.try_submit(d0,3304,local_score) and not d1.sent
check('B14_actually_connected_ready_peers_use_one_executor_independent_of_return_phase',connected_election)


def expired_choice():
    d0,g0=partial(0);d1,g1=partial(1)
    g0.try_submit(d0,3300,local_score);g0.try_submit(d0,3302,local_score)
    g1.try_submit(d1,3300,local_score)
    d0.elapsed_timestep=3303
    g1.receive(d1,dict(id=0,red_group_exchange=g0.message(d0,3303)),3303)
    assert not g1.try_submit(d1,3320,local_score)
    assert g1.choice['executor']==1
    assert g1.try_submit(d1,3322,local_score)
check('B15_disconnected_expired_proposal_cannot_block_submission_until_4590',expired_choice)


def post_cutoff_live():
    d,g=partial();d.inventory_records[4]=(3299,1)
    g.try_submit(d,3300,local_score)
    d.memory.hits[20,20]=3
    image=np.zeros((64,64),np.uint8);image[10:12,14:16]=1;image[40:42,40:42]=1
    g.candidates.remember_live(4590,image)
    with patch.object(SubmissionBearings,'render',side_effect=AssertionError('no fitting after cutoff')):
        assert not g.try_submit(d,4591,local_score)
    assert g.candidates.best['owner']==5 and g.candidates.best['version']==4590
    assert np.array_equal(d.group_best_image[0],image)
    assert np.array_equal(d.deadline_submission.image,image)
check('B16_post_4590_existing_live_image_replaces_stale_4230_choice_without_fitting',post_cutoff_live)


def low_wall_live():
    d,g=partial();d.inventory_records[4]=(3299,1)
    g.try_submit(d,3300,local_score)
    image=np.zeros((64,64),np.uint8);image[10:12,14:16]=1
    g.candidates.remember_live(4500,image);d.elapsed_walltime=173
    with patch.object(SubmissionBearings,'render',side_effect=AssertionError('no fitting at wall reserve')):
        assert not g.try_submit(d,4501,local_score)
    assert g.candidates.images[5]['version']==4500
    assert d.deadline_submission.image is not None
check('B17_wall_reserve_stops_new_render_but_keeps_comparing_existing_live_images',low_wall_live)


def real_partial(owner=0,phase='RETURN_LOCAL'):
    d,g=committed(owner);d.pre_submit_scan.__dict__.pop('finish',None);g.phase=phase
    good=np.zeros((64,64),np.uint8);good[10:12,14:16]=1
    g.candidates.add_image(owner,3240,good,{owner:'own'},3240)
    peer=(owner+1)%5;other,h=committed(peer)
    assert g.candidates.receive(d,peer,('snapshot',h.candidates.snapshots[peer]),3240)
    g.candidates.add_image(peer,3240,np.ones((64,64),np.uint8),{peer:'peer'},3240)
    return d,g


def poll(d,g,step):
    d.elapsed_timestep=step
    return g.try_submit(d,step,local_score)


def real_floor():
    d,g=real_partial()
    assert g.finish_floor(d)==3444
    for step in [3240,3241,3243,3245,3274,3420,3443]:
        assert not poll(d,g,step) and g.choice is None and not g.submission_ready
    assert d.group_best_image is not None and g.finish_refresh_step is None
    assert not poll(d,g,3444) and g.finish_refresh_step==3444
    assert not poll(d,g,3446) and poll(d,g,3448)
    assert d.red_submission_step==3448
check('C01_3245_caches_but_no_proposal_or_finish_until_real_3444_floor',real_floor)


def absolute_floor():
    d,g=real_partial();poll(d,g,3240)
    for _ in range(100):
        g.candidates.receive(d,1,('snapshot',g.candidates.snapshots[1]),3400)
        assert not poll(d,g,3400)
    assert g.finish_floor(d)==3444 and g.finish_refresh_step is None
    poll(d,g,3444);poll(d,g,3446);assert poll(d,g,3448)
check('C02_repeated_messages_do_not_restart_180plus24_allowance',absolute_floor)


def latest_evidence():
    d,g=real_partial();poll(d,g,3241);old=d.group_best_image[0].copy()
    d.memory.hits[20,20]=3;d.submission_bearings.bits[10,10]=4;d.map_revision[4]=3424
    assert not poll(d,g,3424) and np.array_equal(old,d.group_best_image[0])
    seen=[]
    def render(memory=None):
        assert memory.hits[20,20]==3 and d.submission_bearings.bits[10,10]==4
        seen.append(1)
        return np.repeat(np.repeat((memory.hits>=3).astype(np.uint8),2,axis=0),2,axis=1)
    d._render_submission=render
    assert not poll(d,g,3444)
    assert len(seen)==1 and g.candidates.best['owner']==5
    assert d.group_best_image[0][40,40]==1
check('C03_3424_ordinary_map_and_direction_evidence_enter_final_recomparison',latest_evidence)


def retain_previous_winner():
    d,g=real_partial();d.memory.hits[20,20]=3
    good=np.zeros((64,64),np.uint8);good[10:12,14:16]=1;good[40:42,40:42]=1
    g.candidates.remember_live(3240,good);poll(d,g,3241)
    assert g.candidates.best['owner']==5
    original={i:v['digest'] for i,v in g.candidates.images.items() if i<5}
    d._render_submission=lambda memory=None:np.ones((64,64),np.uint8)
    poll(d,g,3444);assert g.candidates.best['owner']==6
    assert np.array_equal(d.group_best_image[0],good)
    assert all(g.candidates.images[i]['digest']==v for i,v in original.items())
    assert all(v[1]<5 for v in g.candidates.manifest())
    poll(d,g,3446);assert poll(d,g,3448)
    assert np.array_equal(d.sent[-1][1],good)
check('C04_new_final_render_cannot_overwrite_better_previous_winner_or_personal_images',retain_previous_winner)


def same_frame_refresh():
    d,g=real_partial();poll(d,g,3241)
    d.memory.hits[20,20]=3
    d.candidate=None
    g.candidates.remember_live(3444,np.ones((64,64),np.uint8))
    count=[]
    def render(memory=None):
        count.append(1)
        return np.repeat(np.repeat((memory.hits>=3).astype(np.uint8),2,axis=0),2,axis=1)
    d._render_submission=render
    poll(d,g,3444)
    assert g.candidates.live_version==3444 and g.candidates.live_image[40,40]==1
    assert g.candidates.live_image[0,0]==0 and d.group_best_image[0][40,40]==1
    poll(d,g,3445);poll(d,g,3446);poll(d,g,3448)
    assert len(count)==1
check('C05_same_step_live_version_does_not_skip_final_refresh_and_it_runs_once',same_frame_refresh)


def low_budget_floor():
    d,g=real_partial();poll(d,g,3241)
    d.elapsed_walltime=168
    assert not g.can_finish(d,3245)
    d.elapsed_walltime=168.01
    assert g.can_finish(d,3245)
    d._render_submission=lambda *a:(_ for _ in ()).throw(AssertionError('no extra render in low budget'))
    assert not poll(d,g,3245) and g.finish_refresh_step is None
    assert poll(d,g,3247)
check('C06_existing_12second_budget_escape_does_not_render_or_wait_for_3444',low_budget_floor)


def deadlines_ignore_floor():
    d,g=real_partial();d.inventory_records[4]=(2500,1);poll(d,g,3241)
    d.elapsed_walltime=179;d.elapsed_timestep=3245
    assert RedHooks._force_deadline_submission(d,3245)
    assert d.deadline_submission_event['fallback']=='walltime' and d.red_submission_step==3245
    d,g=real_partial();d.inventory_records[4]=(2500,1);poll(d,g,3241)
    d.elapsed_walltime=100;d.elapsed_timestep=5396
    assert RedHooks._force_deadline_submission(d,5396)
    assert d.deadline_submission_event['fallback']=='timestep'
check('C07_wall_and_timestep_hard_fallbacks_bypass_ordinary_finish_allowance',deadlines_ignore_floor)


def map09_cache_path():
    d,g=real_partial();d.inventory_records[1]=(2832,1);d.inventory_records[3]=(2804,1)
    d._render_submission=lambda *a:(_ for _ in ()).throw(AssertionError('Map09 unknown stocks must not trigger final render'))
    assert not poll(d,g,3241)
    image=np.zeros((64,64),np.uint8);image[10:12,14:16]=1
    g.candidates.remember_live(4230,image);assert not poll(d,g,4231)
    d.memory.hits[20,20]=3;image[40:42,40:42]=1
    g.candidates.remember_live(4590,image);assert not poll(d,g,4591)
    assert g.finish_refresh_step is None and g.choice is None
    assert g.candidates.best['version']==4590 and np.array_equal(d.deadline_submission.image,image)
    d.elapsed_timestep=4853;d.elapsed_walltime=179
    assert RedHooks._force_deadline_submission(d,4853)
    assert np.array_equal(d.sent[-1][1],image)
check('C08_Map09_4230_and_4590_cache_updates_survive_unknown_last_bomb_and_finish_floor',map09_cache_path)


def real_all_phases():
    for phase in ['RETURN_LOCAL','LOCAL_EXCHANGE','COURIER_TO_C','INTERGROUP_EXCHANGE','DELIVERED_HOLD','ABORT','OBSERVE']:
        d,g=real_partial(phase=phase)
        assert not poll(d,g,3245) and not g.ordinary_submit_allowed(d,3245)
        poll(d,g,3444);poll(d,g,3446);assert poll(d,g,3448),phase
check('C09_real_180plus24_window_is_identical_across_all_return_and_abort_states',real_all_phases)


def legacy_exits():
    from swarm_rescue.solutions.fast_closeout import FastCloseout
    for phase in ['RETURN_LOCAL','ABORT']:
        d,g=real_partial(phase=phase);g.plan.acks=set()
        assert not g.ordinary_submit_allowed(d,3245)
        f=FastCloseout(0,5);assert not f.submit(d,3245)
check('C10_old_ordinary_and_fast_closeout_cannot_bypass_finish_floor_after_abort',legacy_exits)


def messenger_return_path():
    d,g=real_partial(phase='ABORT');d.messenger.tick=lambda *a:True
    d.lidar_values=lambda:(_ for _ in ()).throw(AssertionError('messenger must keep original scan skip'))
    d.elapsed_timestep=3245;control(d)
    assert d.group_best_image is not None and not d.sent
    for step in [3444,3446,3448]:d.elapsed_timestep=step;control(d)
    assert d.red_submission_step==3448 and g.finish_refresh_step==3444
check('C11_messenger_early_return_keeps_cache_and_finish_eligibility_without_extra_scan',messenger_return_path)


def after_observation():
    d,g=real_partial();order=[]
    d.lidar_values=lambda:np.full(181,150.)
    def observe(*args):
        d.memory.hits[20,20]=3;order.append('observed')
        return np.array([],dtype=np.int32),np.array([],dtype=np.uint8)
    d.memory.observe=observe
    d.submission_bearings.observe=lambda *a:(d.submission_bearings.bits.__setitem__((10,10),4),order.append('bearings'))
    def render(memory=None):
        assert memory.hits[20,20]==3 and d.submission_bearings.bits[10,10]==4
        order.append('final_render')
        return np.repeat(np.repeat((memory.hits>=3).astype(np.uint8),2,axis=0),2,axis=1)
    d._render_submission=render;d.elapsed_timestep=3444
    control(d)
    assert order.index('observed')<order.index('final_render') and order.index('bearings')<order.index('final_render')
check('C12_real_control_renders_final_candidate_after_existing_same_frame_scan_and_bearings',after_observation)


def final_map_evidence():
    d,g=real_partial();poll(d,g,3241)
    memory=MapMemory(64,64);memory.hits[20,20]=3
    d.final_maps.snapshots[4]=(4,3420,True,memory.packet())
    seen=[]
    def render(memory=None):
        assert memory.hits[20,20]==3 and d.memory.hits[20,20]==0
        seen.append(1)
        return np.repeat(np.repeat((memory.hits>=3).astype(np.uint8),2,axis=0),2,axis=1)
    d._render_submission=render;poll(d,g,3444)
    assert seen and g.finish_refresh_step==3444
check('C13_final_refresh_includes_existing_FinalMaps_snapshot_without_mutating_live_memory',final_map_evidence)


def derived_floor():
    d,g=real_partial()
    d.limit=6000;assert g.finish_floor(d)==3804
    d.limit=300;assert g.finish_floor(d)==DeadlineSubmission.window_start(300)==271
check('C14_finish_floor_uses_existing_constants_and_is_clamped_to_deadline_window',derived_floor)


def stock_before_final_render():
    for kind in ['own_stock','pending','unknown_peer']:
        d,g=real_partial();poll(d,g,3241)
        if kind=='own_stock':d.previous_inventory=1
        elif kind=='pending':d.pending_drop=(1,np.zeros(2),3443)
        else:d.inventory_records[4]=(3300,1)
        d._render_submission=lambda *a:(_ for _ in ()).throw(AssertionError('stock/pending veto precedes final fit'))
        assert not poll(d,g,3444) and g.finish_refresh_step is None and not d.sent
check('C15_real_stock_and_pending_checks_precede_final_refresh_and_submission',stock_before_final_render)


def empty_final_render():
    d,g=real_partial();poll(d,g,3241);old=d.group_best_image[0].copy()
    d._render_submission=lambda *a:np.zeros((64,64),np.uint8)
    poll(d,g,3444)
    assert np.array_equal(d.group_best_image[0],old) and g.finish_refresh_step==3444
    assert not d.sent
check('C16_empty_final_render_does_not_erase_valid_candidate_or_personal_originals',empty_final_render)

result=dict(status='PASS',scenario_groups=len(RESULTS),scenarios=RESULTS,
            archive_sha256=sha256(args.archive.read_bytes()).hexdigest(),
            loaded_red_hooks=sys.modules[RedHooks.__module__].__file__,
            physics_step_attempts=physics_attempts,physics_steps=0,map_objects_created=0,full_matches=0)
assert physics_attempts==0
if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

