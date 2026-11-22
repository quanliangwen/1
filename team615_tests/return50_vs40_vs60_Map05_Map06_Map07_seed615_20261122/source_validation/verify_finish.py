"""Actual candidate methods and SDK types, with fixed public sensor/messages.

No Launcher, round, physics step, replayed controller or evaluation is run.
"""
from pathlib import Path
from types import SimpleNamespace as NS, MethodType
from hashlib import sha256
import ast, copy, json, sys, traceback

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,sys.argv[1])
import swarm_rescue.solutions
swarm_rescue.solutions.__path__=[str(ROOT/'candidate'),*swarm_rescue.solutions.__path__]
import numpy as np
from swarm_rescue.solutions.red_hooks import RedHooks,local_score
from swarm_rescue.solutions.coverage_placement import CoveragePlacementDrone
from swarm_rescue.solutions.placement_preferences import PlacementPreferences,SDK_SPACING
from swarm_rescue.solutions.second_drop_site import SecondDropSite
from swarm_rescue.solutions.group_exchange import GroupExchange
from swarm_rescue.solutions.map_candidates import MapCandidates
from swarm_rescue.solutions.greedy_mapping import MapMemory
from swarm_rescue.solutions.submission_renderer import SubmissionBearings
from swarm_rescue.solutions.pre_submit_scan import PreSubmitScan
from swarm_rescue.solutions.final_map_relay import FinalMaps
from swarm_rescue.solutions.deadline_submission import DeadlineSubmission,BudgetSubmission
from swarm_rescue.solutions.partial_map_submit import provisional_map
import swarm_rescue.solutions.red_hooks as red_module
assert Path(red_module.__file__).resolve()==(ROOT/'candidate/red_hooks.py').resolve()
build=json.loads((ROOT/'BUILD.json').read_text())
checks=[];categories=[]
def hashes():return {n:sha256((ROOT/'candidate'/n).read_bytes()).hexdigest() for n in build['candidate_files']}
assert hashes()==build['candidate_files']
def check(name,ok,**details):
    assert ok,name
    checks.append(dict(name=name,status='PASS',**details))
def category(name,fn):
    n=len(checks);fn();categories.append(dict(name=name,checks=len(checks)-n,status='PASS'))
def bind(d,cls,names):
    for name in names:setattr(d,name,MethodType(getattr(cls,name),d))

def placement_drone():
    d=NS(identifier=4,team_size=5,limit=5400,walltime_limit=180.,elapsed_walltime=90.,elapsed_timestep=3248,
         initial_inventory=2,previous_inventory=1,sensor_inventory=1,pending_drop=None,pose=np.array([0.,0.]),
         heading=0.,size_area=(2000,2000),home=np.array([-500.,-500.]),_odometry_only=False,
         blast_radius=135.,last_attempt_step=1000,last_coverage_step=1000,placement_goal=None,waypoints=[],last_plan_step=0,
         route=[np.array([40.,0.])],odom=np.array([0.,0.,0.]),gain=.01,exit_clear=True,
         drop_records={(4,1):np.array([-100.,0.])},inventory_records={4:(1001,1)},team_exchange_audit=[],drive_calls=[])
    d.grid=NS(pose_fixed=True,cell=lambda p:0,evidence=np.array([-1]),clearance=np.array([100.]))
    d.memory=NS(semantic_mask=MapMemory.semantic_mask)
    d.search_roaming=NS(departed=True);d.drop_departure=NS(started=None,controls_step=-1)
    d.placement=PlacementPreferences();d.placement.last_drop_point=d.drop_records[(4,1)].copy()
    d.second_drop=SecondDropSite()
    d.team_wall=NS(reservation=None,query=lambda *a:(lambda p:(d.gain,1.,[1,0,0])))
    d.local_escape=NS(clearance=lambda *a:d.exit_clear)
    d.angles=np.linspace(-np.pi,np.pi,32,endpoint=False)
    d.ranges=np.full(32,200.)
    d.odometer_values=lambda:d.odom.copy();d.lidar_rays_angles=lambda:d.angles
    d.carried_bombs_count=lambda:d.sensor_inventory
    def drive(point,velocity):
        d.drive_calls.append((np.asarray(point).copy(),np.asarray(velocity).copy()))
        return dict(forward=0.,lateral=0.,rotation=0.)
    d.drive=drive
    bind(d,RedHooks,['_inside_team_point','_placement_block','_receive_team_coordination'])
    bind(d,CoveragePlacementDrone,['_placement_spacing','_known_bomb_positions','_sync_placement','_all_inventory_empty'])
    return d
def drop(d,step=3248):
    d.elapsed_timestep=step;c=dict(place_bomb=0)
    old=copy.deepcopy(d.route)
    took=d.placement.complete_last(d,c,step,d.ranges,[])
    assert len(old)==len(d.route) and all(np.array_equal(a,b) for a,b in zip(old,d.route))
    return took,c

def last_bomb_scope():
    d=placement_drone();took,c=drop(d)
    check('small_positive_gain_can_place_on_current_route',took and c['place_bomb']==1 and d.pending_drop is not None)
    check('request_does_not_claim_actual_completion',d.sensor_inventory==1 and (4,2) not in d.drop_records)
    check('SDK_24px_and_old_114_75px_preserved',SDK_SPACING==24. and d._placement_spacing(3248)==114.75)
    for field,value,label in [('initial_inventory',3,'different_quota'),('previous_inventory',2,'first_bomb'),
                              ('sensor_inventory',2,'stock_disagreement'),('pending_drop',(1,np.zeros(2),3247),'pending'),
                              ('_odometry_only',True,'odometry_only')]:
        d=placement_drone();setattr(d,field,value);took,c=drop(d)
        check('no_completion_'+label,not took and c['place_bomb']==0)
    d=placement_drone();check('before_60_percent_inactive',not drop(d,3238)[0])
    for limit in (5400,7200):
        d=placement_drone();d.limit=limit;start=limit*3//5
        check('map_limit_before_60_'+str(limit),not drop(d,start-2)[0])
        check('map_limit_after_60_'+str(limit),drop(d,start+8)[1]['place_bomb']==1)
    d=placement_drone();d.placement.last_drop_point=None
    check('unconfirmed_first_drop_not_eligible',not drop(d)[0])
    for label,change in [
      ('GPS',lambda d:setattr(d.grid,'pose_fixed',False)),
      ('first_departure',lambda d:setattr(d.drop_departure,'started',3200)),
      ('zero_gain',lambda d:setattr(d,'gain',0.)),('negative_gain',lambda d:setattr(d,'gain',-.01)),
      ('nan_gain',lambda d:setattr(d,'gain',float('nan'))),
      ('no_route',lambda d:setattr(d,'route',[])),('wall_cell',lambda d:d.grid.evidence.fill(1)),
      ('clearance',lambda d:d.grid.clearance.fill(5.9)),('exit_blocked',lambda d:setattr(d,'exit_clear',False)),
      ('disposal',lambda d:setattr(d,'home',np.array([10.,0.]))),
      ('no_lidar',lambda d:setattr(d,'ranges',np.full(32,np.nan))),
      ('bad_odometry',lambda d:setattr(d,'odom',np.array([np.nan,0.,0.]))),
      ('wall_budget',lambda d:setattr(d,'elapsed_walltime',176.1))]:
        d=placement_drone();change(d);took,c=drop(d)
        check('safety_reject_'+label,not took and c['place_bomb']==0)
    d=placement_drone();d.angles=np.array([-1.62,-1.52,1.52,1.62]);d.ranges=np.full(4,50.)
    check('real_live_narrow_corridor_rejected',not drop(d)[0])
    for distance,expected in [(23.99,False),(24.,False),(31.99,False),(32.,True),(40.,True)]:
        d=placement_drone();d.drop_records[(4,1)]=np.array([-distance,0.]);d.placement.last_drop_point=d.drop_records[(4,1)].copy()
        check('conservative_spacing_'+str(distance),drop(d)[0]==expected)
    d=placement_drone()
    d.placement._protected_turn=lambda *a:(_ for _ in ()).throw(AssertionError('historical turn gate used'))
    d.placement._patch_open=lambda *a:(_ for _ in ()).throw(AssertionError('quality density gate used'))
    d.placement.rejected_patch.blocked=lambda *a:True
    d.placement._forward_gain=lambda *a:999.
    d.placement.deep.here=lambda *a:False
    check('historical_and_quality_holds_do_not_block_safe_last_bomb',drop(d)[1]['place_bomb']==1)

def braking_and_confirmation():
    d=placement_drone();d.odom[0]=3.;took,c=drop(d)
    check('moving_drone_brakes_without_pulse',took and c['place_bomb']==0 and d.pending_drop is None)
    check('braking_does_not_install_a_new_waypoint',len(d.drive_calls)==1 and np.array_equal(d.drive_calls[0][0],d.pose))
    d.odom[0]=0.;took,c=drop(d,3249)
    check('stationary_recheck_then_pulse',took and c['place_bomb']==1)
    d._sync_placement(3250);d.placement.finish_request(d,3250)
    check('SDK_rejection_keeps_one_bomb_and_no_fake_record',d.previous_inventory==1 and d.pending_drop is None and (4,2) not in d.drop_records)
    check('rejection_has_zero_pulse_retry_gap',not drop(d,3250)[0] and d.placement.next_request==3256)
    d=placement_drone();drop(d);d.sensor_inventory=0;d._sync_placement(3249);d.placement.finish_request(d,3249)
    check('inventory_drop_is_the_only_success_confirmation',d.previous_inventory==0 and d.inventory_records[4]==(3249,0) and (4,2) in d.drop_records)
    check('confirmed_bomb_not_requested_again',not drop(d,3258)[0])
    d=placement_drone();d.odom[0]=3.;drop(d);took,c=drop(d,3278)
    check('braking_has_absolute_30_step_timeout',not took and c['place_bomb']==0 and d.second_drop.completion_plan is None)
    for name,change in [('new_bomb',lambda d:d.drop_records.update({(1,1):np.array([20.,0.])})),
                        ('lost_GPS',lambda d:setattr(d.grid,'pose_fixed',False)),
                        ('lost_gain',lambda d:setattr(d,'gain',0.)),
                        ('avoidance_drift',lambda d:setattr(d,'pose',np.array([9.,0.]))),
                        ('blocked_exit',lambda d:setattr(d,'exit_clear',False))]:
        d=placement_drone();d.odom[0]=3.;drop(d);change(d);d.odom[0]=0.;took,c=drop(d,3249)
        check('arrival_recheck_'+name,not took and c['place_bomb']==0 and d.second_drop.completion_plan is None)

def exchange_drone(owner=0):
    d=placement_drone();d.identifier=owner;d.previous_inventory=0;d.sensor_inventory=0;d.pending_drop=None
    d.size_area=(200,160);d.pose=np.array([0.,0.]);d.home=None
    d.elapsed_timestep=3300;d.elapsed_walltime=100.
    d.inventory_records={i:(3200,0) for i in range(5)}
    d.memory=MapMemory(200,160);d.memory.hits[10:15,10:15]=3
    d.submission_bearings=SubmissionBearings(200,160)
    d.final_maps=FinalMaps(owner,5);d.final_maps.freeze(3240,d.memory)
    d.deadline_submission=DeadlineSubmission();d.budget_submission=BudgetSubmission();d.deadline_versions={}
    d.pre_submit_scan=PreSubmitScan();d.map_quality=3000;d.map_revision={}
    d.map_bids={};d.own_sent_bids=[];d.last_eligible_bid_comparison={};d.submission_priority_audit=None
    d.submission_wait_started=None;d.submission_wait_for=None;d.first_ready_to_submit_step=None
    d.group_best_image=None;d.submitted=False;d.submissions=[];d.render_calls=0
    d.render_image=np.zeros((160,200),np.uint8);d.render_image[20:30,20:30]=1
    def render(*a):d.render_calls+=1;return d.render_image.copy()
    d._render_submission=render;d.submit_exploration_map=lambda image:d.submissions.append(image.copy())
    d.messenger=NS(state='IDLE',audit=[]);d.search_task=None
    d.grid.tight=np.array([False]);d.grid.HULL_CLEARANCE=14.;d.grid.route=lambda *a:[]
    bind(d,RedHooks,['_submission_window_open','_own_map_bid','_prefer_own_submission'])
    d.group_exchange=GroupExchange(owner,5,5400,d.size_area)
    g=d.group_exchange;g.candidates.freeze_local(d,3240)
    g.candidates.add_image(owner,3240,d.render_image,{owner:g.candidates.snapshots[owner]['digest']},3240)
    g.candidates.remember_live(3300,d.render_image)
    return d
def message(source,target,step,payload=None,inventory=None,receipts=None):
    g=source.group_exchange
    return dict(id=source.identifier,red_inventory=copy.deepcopy(source.inventory_records if inventory is None else inventory),
                red_group_exchange=dict(epoch=g.plan.epoch,step=step,point=tuple(source.pose),fixed=True,
                    phase=g.phase,group=g.group,eta=100,role=g.role,
                    receipts=g.candidates.manifest() if receipts is None else receipts,payload=payload))
def deliver(target,msg,step):
    target.elapsed_timestep=step
    target._receive_team_coordination(msg,step)
    target.group_exchange.receive(target,msg,step)
def pair():
    a,b=exchange_drone(0),exchange_drone(3)
    for target,source in [(a,b),(b,a)]:
        g=source.group_exchange
        for kind,store in [('snapshot',g.candidates.snapshots),('image',g.candidates.images)]:
            deliver(target,message(source,target,3300,payload=(kind,store[source.identifier])),3300)
    for target,source in [(a,b),(b,a)]:deliver(target,message(source,target,3300),3300)
    for d in (a,b):d.group_exchange.refresh_comparison(d,3300,local_score)
    return a,b

def confirmation_receipts():
    a,b=pair();g=a.group_exchange
    a.inventory_records[1]=(1928,1);b.inventory_records[1]=(2393,0)
    deliver(a,message(b,a,3301),3301)
    check('real_relayed_zero_replaces_Map06_stale_positive',a.inventory_records[1]==(2393,0))
    check('relay_preserves_origin_timestamp',a.inventory_records[1][0]!=3301)
    check('receipt_records_actual_peer_zero_knowledge',1 in g.peer_zero_receipts[3][1])
    deliver(a,message(b,a,3302,inventory={1:(1928,1)}),3302)
    check('old_positive_does_not_undo_confirmed_zero',a.inventory_records[1]==(2393,0))
    for record in [(3304,0),(1928,1)]:
        a,b=pair();a.inventory_records[1]=(1928,1)
        # A future record is rejected by the unchanged origin merger.
        deliver(a,message(b,a,3303,inventory={1:record}),3303)
        check('no_false_zero_'+str(record),a.inventory_records[1]==(1928,1) and not a.group_exchange.exchange_finish_ready(a,3303))
    a,b=pair();a.inventory_records.pop(1);b.inventory_records.pop(1)
    deliver(a,message(b,a,3301),3301)
    check('missing_confirmation_is_not_zero',1 not in a.inventory_records and not a.group_exchange.exchange_finish_ready(a,3301))
    a,b=pair();g=a.group_exchange
    deliver(a,message(b,a,3301,inventory={i:(3200,0) for i in (0,1,2,3)}),3301)
    check('peer_missing_zero_does_not_ack_team_completion',not g.exchange_finish_ready(a,3301))
    a,b=pair();g=a.group_exchange;g.peer_zero_receipts.clear()
    check('map_receipts_alone_are_not_stock_receipts',not g.exchange_finish_ready(a,3300))
    a,b=pair();g=a.group_exchange
    check('stale_contact_cannot_start_early_finish',not g.exchange_finish_ready(a,3313))
    a,b=pair();g=a.group_exchange;g.peer_status[3]['have']=set()
    check('zero_stock_without_payload_ack_is_not_exchange_complete',not g.exchange_finish_ready(a,3300))

def early_finish():
    a,b=pair();g=a.group_exchange
    check('actual_pair_exchange_arms_without_five_maps',g.exchange_finish_ready(a,3300) and len(g.candidates.snapshots)==2)
    check('low_proxy_would_have_been_provisional',provisional_map(3300,a.map_quality,{},80.))
    check('short_refresh_not_skipped',not g.can_finish(a,3323) and g.can_finish(a,3324))
    check('first_round_yield_preserved',g.yield_first_round(a,3324) and not g.yield_first_round(a,3330))
    for step in range(3301,3325):
        deliver(a,message(b,a,step),step);g.exchange_finish_ready(a,step)
    check('duplicates_do_not_restart_finish_or_yield',g.early_finish_started==3300)
    for step in range(3324,3400):
        a.elapsed_timestep=step
        if g.try_submit(a,step,local_score):break
    check('submit_before_old_3444_floor',a.submitted and a.red_submission_step<3444,step=a.red_submission_step)
    check('short_refresh_and_yield_overlap',a.red_submission_step<3300+24+30+30)
    check('only_one_final_refresh_render',a.render_calls==1)
    check('own_original_image_is_retained',0 in g.candidates.images and g.candidates.images[0]['version']==3240)
    check('submit_has_valid_choice_and_absolute_slot',g.choice is not None and g.choice_in_slot(a,g.choice,a.red_submission_step))
    a,b=pair();g=a.group_exchange;g.phase='INTERGROUP_EXCHANGE';g.candidates.snapshots.pop(3)
    check('phase_name_without_actual_payload_cannot_arm',not g.exchange_finish_ready(a,3300))
    for name,mut in [('pending',lambda d:setattr(d,'pending_drop',(1,d.pose.copy(),3300))),
                     ('sensor_stock',lambda d:setattr(d,'sensor_inventory',1)),
                     ('peer_stock',lambda d:d.inventory_records.update({4:(3299,1)}))]:
        a,b=pair();mut(a);g=a.group_exchange
        check('early_end_veto_'+name,not g.exchange_finish_ready(a,3300) and not g.try_submit(a,3330,local_score))
    a=exchange_drone();g=a.group_exchange
    check('ordinary_old_floor_retained_without_real_exchange',not g.can_finish(a,3443) and g.can_finish(a,3444))
    a,b=pair();g=a.group_exchange;g.plan.root=(77,0.,0.);g.plan.acks=set(range(5))
    g.exchange_finish_ready(a,3300);a.first_ready_to_submit_step=3324
    check('ordinary_path_bypasses_old_active_exchange_hold',g.ordinary_submit_allowed(a,3354))
    a=exchange_drone();g=a.group_exchange;g.plan.root=(77,0.,0.);g.plan.acks=set(range(5))
    a.first_ready_to_submit_step=3444
    check('ordinary_active_hold_kept_without_completion',not g.ordinary_submit_allowed(a,3504))
    a,b=pair();g=a.group_exchange;g.exchange_finish_ready(a,3300)
    a.inventory_records[4]=(3310,1)
    check('latched_early_ready_does_not_override_remaining_stock',not g.exchange_finish_ready(a,3324) and not g.can_finish(a,3324))

def election():
    a,b=pair();a.map_quality=1000;b.map_quality=9900
    for d in (a,b):d.group_exchange.exchange_finish_ready(d,3300)
    check('all_owners_share_absolute_slots',all(a.group_exchange.submission_slot(a,t)==b.group_exchange.submission_slot(b,t) for t in range(3300,3380)))
    winner=None
    for step in range(3300,3420):
        for d in (a,b):d.elapsed_timestep=step
        bids={d.identifier:d._own_map_bid(step) for d in (a,b)}
        for target,source in [(a,b),(b,a)]:
            if bids[source.identifier] is not None:target.map_bids[source.identifier]=bids[source.identifier]
        for d in (a,b):
            if d.group_exchange.try_submit(d,step,local_score):winner=(d.identifier,step);break
        if winner:break
    check('higher_ranked_nonzero_drone_submits_first',winner is not None and winner[0]==3 and not a.submitted,winner=winner)
    check('six_step_slots_and_no_simultaneous_fixture_submit',len(a.submissions)+len(b.submissions)==1 and GroupExchange.SUBMISSION_SLOT_STEPS==6)
    table=[dict(owner=0,version=3240,score=.800,digest='a'*64),dict(owner=3,version=3350,score=.798,digest='b'*64)]
    check('near_tie_still_prefers_newer_image',MapCandidates.select_candidate(table,ordinary=True)['owner']==3)
    table[1]['score']=.796
    check('clear_score_gap_still_prefers_better_map',MapCandidates.select_candidate(table,ordinary=True)['owner']==0)

def retry_drone():
    d=exchange_drone();d.inventory_records[1]=(1928,1);g=d.group_exchange
    g.plan.root=(77,0.,0.);g.plan.acks=set(range(5));g.plan.trail=[(0.,0.),(30.,0.)]
    g.plan.branch_group=(0,3);g.plan.local_region=(0.,0.)
    d.pose=np.array([30.,0.]);d.elapsed_timestep=3300;g.release(d,'ABORT')
    return d
def bounded_retry():
    d=retry_drone();g=d.group_exchange
    check('abort_retry_cooldown',g.prepare_return(d,3319) is None and not g.confirmation_retry_used)
    intent=g.prepare_return(d,3320)
    check('one_retry_uses_original_root_and_route',intent is not None and intent.target==(0.,0.) and intent.route==((0.,0.),))
    g.commit_return(d,intent,3320);d.elapsed_timestep=3360;g.release(d,'ABORT')
    check('second_abort_cannot_restart_mission',g.prepare_return(d,3380) is None and g.confirmation_retry_used)
    d=retry_drone();g=d.group_exchange;d.grid.evidence.fill(1);calls=[]
    d.grid.route=lambda *args:(calls.append(args) or [])
    check('unsafe_retry_join_rejected',g.prepare_return(d,3320) is None and g.confirmation_retry_used)
    g.prepare_return(d,3321)
    check('unsafe_retry_not_replanned_every_frame',len(calls)==1)
    d=retry_drone();d.inventory_records[1]=(2393,0)
    check('no_confirmation_gap_no_retry',d.group_exchange.prepare_return(d,3320) is None)
    d=retry_drone();d.sensor_inventory=1;d.previous_inventory=1
    check('carrying_bomb_does_not_retry_return',d.group_exchange.prepare_return(d,3320) is None)
    d=retry_drone();g=d.group_exchange;g.plan.trail=[(0.,0.),(800.,0.)];d.pose=np.array([800.,0.])
    check('insufficient_route_budget_rejected',g.prepare_return(d,4400) is None)
    a,b=pair();g=a.group_exchange;g.group=(0,3)
    a.inventory_records[3]=(1928,1)
    check('local_handoff_requires_group_real_zero',not g._exchange_acked(a,3300,g.group))
    a.inventory_records[3]=(3297,0)
    check('local_handoff_completes_after_zero_and_payload_ack',g._exchange_acked(a,3300,g.group))

def control_integration():
    # Execute the actual full control AST on a minimal harness. All unrelated
    # stages are inert fixtures; no Drone base or physics controller executes.
    class Base:
        def control(self):return dict(place_bomb=0)
    tree=ast.parse((ROOT/'candidate/red_hooks.py').read_bytes())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RedHooks')
    fn=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='control'))
    wrapper=ast.ClassDef(name='Harness',bases=[ast.Name(id='Base',ctx=ast.Load())],keywords=[],body=[fn],decorator_list=[])
    env=dict(Base=Base,**vars(red_module))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper],type_ignores=[])),'<real_control_ast>', 'exec'),env)
    d=env['Harness']();src=placement_drone();d.__dict__.update(src.__dict__)
    d.elapsed_timestep=3258
    # Rebind fixture closures to the same underlying mutable values used by
    # the candidate methods, then install only the stages reached before pulse.
    d._sync_placement=lambda step:None;d._force_deadline_submission=lambda step:False;d._try_budget_submission=lambda step:False
    d.submitted=False;d.group_exchange=None;d.closeout=NS(tick=lambda *a:None,state=None)
    d.messenger=NS(tick=lambda *a:False);d.lidar_values=lambda:d.ranges;d.semantic_values=lambda:[]
    d.pre_submit_scan=NS(refresh_due=lambda *a:False);d.red_packet=None
    d._update_drop_hints=lambda *a:None
    d.placement.maneuvers.remember=lambda *a:None
    d.placement.local_exit.observe=lambda *a:None;d.placement.branch_exit.observe=lambda *a:None
    d.drop_departure.update=lambda *a:None;d.drop_departure.steer=lambda *a:None
    d.second_drop.observe_route=lambda *a:None;d.fast_closeout=NS(act=lambda *a:False)
    d.local_escape.apply=lambda *a:None
    result=d.control()
    check('real_control_reaches_completion_before_old_approach',result['place_bomb']==1 and d.pending_drop is not None)
    old=ROOT/'candidate/deadline_submission.py'
    check('hard_fallback_reserve_unchanged',DeadlineSubmission.MIN_WALL_MARGIN==1.5 and DeadlineSubmission.FALLBACK_STEPS==4)
    check('budget_window_unchanged',BudgetSubmission.window(5400)==(5022,5051))

try:
    for name,fn in [('末弹适用范围与安全复核',last_bomb_scope),('刹停到点与实投确认',braking_and_confirmation),
                    ('旧确认补齐与真实交接回执',confirmation_receipts),('交互后提前交图与等待分离',early_finish),
                    ('选图竞价与共享时间槽',election),('一次返航重试及原安全路线',bounded_retry),
                    ('完整控制入口与兜底保留',control_integration)]:category(name,fn)
    check('all_source_hashes_unchanged_after_checks',hashes()==build['candidate_files'])
    result=dict(status='PASS',categories=categories,total_checks=len(checks),checks=checks,
                candidate_zip_sha256=build['candidate_zip_sha256'],source_files=hashes(),python=sys.version,numpy=np.__version__,
                sdk_src=sys.argv[1],full_matches=0,physics_steps=0,SDK_rounds=0,V16_remains_competition_baseline=True)
except BaseException as e:
    result=dict(status='FAIL',error=repr(e),traceback=traceback.format_exc(),categories=categories,checks=checks,full_matches=0,physics_steps=0)
    (ROOT/'COUNTEREXAMPLES.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    raise
(ROOT/'COUNTEREXAMPLES.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('checks','source_files')},indent=2,ensure_ascii=False))
