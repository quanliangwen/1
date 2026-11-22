"""Real candidate methods, fixed public inputs only; no physics or SDK round."""
from pathlib import Path
from types import SimpleNamespace as NS,MethodType
from hashlib import sha256
import ast,copy,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,sys.argv[1])
import swarm_rescue.solutions
swarm_rescue.solutions.__path__=[str(ROOT/'candidate'),*swarm_rescue.solutions.__path__]
import numpy as np
from swarm_rescue.solutions.drop_departure import DropDeparture
from swarm_rescue.solutions.local_escape import LocalEscape
from swarm_rescue.solutions.coverage_placement import CoveragePlacementDrone
from swarm_rescue.solutions.placement_preferences import PlacementPreferences
from swarm_rescue.solutions.deadline_submission import DeadlineSubmission,BudgetSubmission
from swarm_rescue.solutions.final_map_relay import FinalMaps
from swarm_rescue.solutions.red_hooks import RedHooks
import swarm_rescue.solutions.red_hooks as hooks

checks=[];categories=[]
def check(name,ok,**details):
    assert ok,name
    checks.append(dict(name=name,status='PASS',**details))
def category(name,fn):
    start=len(checks);fn();categories.append(dict(name=name,status='PASS',checks=len(checks)-start))
def bomb(angle,distance,kind='BOMB'):
    return NS(angle=float(angle),distance=float(distance),entity_type=NS(name=kind),grasped=False)
def fixture():
    d=NS(identifier=4,team_size=5,limit=5400,walltime_limit=180.,elapsed_walltime=70.,elapsed_timestep=1000,
         initial_inventory=2,previous_inventory=2,sensor_inventory=2,pending_drop=None,
         pose=np.array([0.,0.]),heading=0.,grid=NS(pose_fixed=True),_odometry_only=False,
         placement=PlacementPreferences(),drop_records={},inventory_records={},route=[(100.,0.)],
         odom=np.zeros(3),last_coverage_step=0,placement_goal=None,waypoints=[],last_plan_step=0,
         angles=np.linspace(-np.pi,np.pi,181,endpoint=False),commands=[])
    d.odometer_values=lambda:d.odom.copy();d.lidar_rays_angles=lambda:d.angles
    d.carried_bombs_count=lambda:d.sensor_inventory
    d.local_escape=LocalEscape();d._inside_team_point=lambda p:bool(np.max(np.abs(p))<500.)
    def motion(desired,*args):
        d.commands.append(np.asarray(desired).copy())
        return dict(forward=float(desired[0]),lateral=float(desired[1]),rotation=0.)
    d.motion_command=motion
    return d,DropDeparture()
def sensors(d,r):
    predicted=r._own_surface(d,d.angles)
    values=np.where(np.isfinite(predicted),predicted,200.)
    angles=np.linspace(-np.pi,np.pi,35,endpoint=False)
    surface=r._own_surface(d,angles)
    semantic=[bomb(a,v) for a,v in zip(angles,surface) if np.isfinite(v)]
    return values,semantic
def confirmed():
    d,r=fixture();r.observe_recovery(d,1000,np.full(181,200.),[])
    d.pending_drop=(2,np.zeros(2),1000);d.sensor_inventory=1
    CoveragePlacementDrone._sync_placement(d,1001)
    d.pose=np.array([5.,0.]);values=np.full(181,12.)
    r.observe_recovery(d,1001,values,[]);r.update(d,1001,True)
    return d,r
def ready():
    d,r=confirmed()
    for step in range(1002,1064):
        d.elapsed_timestep=step
        values,semantic=sensors(d,r)
        r.observe_recovery(d,step,values,semantic);r.update(d,step,False)
        r.steer(d,{},step,values,semantic)
    assert r.started is None and r.recovery_failed and not d.commands
    return d,r
def tick(d,r,step=1064,wall=None,values=None,semantic=None):
    d.elapsed_timestep=step
    if wall is not None:d.elapsed_walltime=wall
    default_values,default_semantic=(sensors(d,r) if r.first_point is not None else (np.full(181,200.),[]))
    if values is None:values=default_values
    if semantic is None:semantic=default_semantic
    r.observe_recovery(d,step,values,semantic)
    c=dict(place_bomb=0)
    took=r.recover(d,c,step,values,semantic)
    return took,c

def trigger_cases():
    d,r=ready();took,c=tick(d,r)
    check('confirmed_failed_stalled_departure_recovers',took and r.recovery_used and r.recovery_started==1064)
    check('recovery_never_pulses',c['place_bomb']==0 and c['grasper']==0)
    check('original_departure_window_still_62_steps',r.last_tick==1063 and any(x[1]=='departure_ended' for x in r.audit))
    d,r=confirmed()
    for step in range(1002,1005):
        d.pose[0]+=12.;d.odom[0]=12.
        r.observe_recovery(d,step,np.full(181,200.),[]);r.update(d,step,False)
    check('normal_departure_not_marked_failed',r.started is None and not r.recovery_failed)
    check('normal_departure_no_recovery',not tick(d,r,1005)[0] and not r.recovery_used)
    for label,mutate in [
      ('not_failed',lambda d,r:setattr(r,'recovery_failed',False)),
      ('original_active',lambda d,r:setattr(r,'started',1001)),
      ('no_first_record',lambda d,r:setattr(r,'first_point',None)),
      ('29_samples',lambda d,r:r.recovery_trace.clear()),
      ('already_32px_away',lambda d,r:setattr(d,'pose',np.array([32.,0.]))),
      ('pending_request',lambda d,r:setattr(d,'pending_drop',(1,d.pose.copy(),1063))),
      ('no_pre_drop_evidence',lambda d,r:setattr(r,'before_drop_scan',None)),
      ('less_than_6_seconds',lambda d,r:setattr(d,'elapsed_walltime',174.01)),
      ('wrong_inventory',lambda d,r:setattr(d,'sensor_inventory',2))]:
        d,r=ready();mutate(d,r);check('trigger_reject_'+label,not tick(d,r)[0] and not r.recovery_used)
    d,r=ready();r.recovery_trace[-2]=(1062,np.array([20.,0.]))
    check('moving_trace_not_a_stall',not tick(d,r)[0] and not r.recovery_used)
    d,r=fixture();r.observe_recovery(d,1000,np.full(181,200.),[])
    d.pending_drop=(2,np.zeros(2),1000);CoveragePlacementDrone._sync_placement(d,1001)
    r.recovery_failed=True
    r.observe_recovery(d,1001,np.full(181,200.),[])
    check('SDK_rejection_not_first_drop_confirmation',not d.drop_records and r.first_point is None and not r.recovery_used)
    for label,unlocalized in [('pending_fixed_flag',False),('record_marked_unlocalized',True)]:
        d,r=fixture();r.observe_recovery(d,1000,np.full(181,200.),[])
        d.drop_records[(4,1)]=np.zeros(2);d.previous_inventory=d.sensor_inventory=1
        if unlocalized:d.placement.unlocalized_drops.add((4,1))
        else:d.placement.request=(1000,'coverage',False,2)
        r.observe_recovery(d,1001,np.full(181,200.),[])
        check('unreliable_first_release_not_used_'+label,r.first_point is None)
    d,r=ready();d.pose=np.array([31.,0.]);r.recovery_trace.clear()
    for step in range(1034,1064):r.recovery_trace.append((step,d.pose.copy()))
    check('under_32px_can_recover',tick(d,r)[0])

def bounded_cases():
    d,r=ready();tick(d,r)
    start=r.recovery_started;wall=r.recovery_wall_started
    for i in range(1,63):
        d.pose[0]=5.+.2*i;d.odom[0]=.2
        took,c=tick(d,r,start+i,wall+.01*i)
        if i<62:assert took,(i,r.audit[-4:],d.pose.tolist())
    check('62_step_cap',not took and r.recovery_started is None and len(d.commands)==62)
    check('absolute_start_not_extended',r.recovery_wall_started==wall and r.recovery_used)
    for i in range(63,75):
        check('no_restart_after_timeout_'+str(i),not tick(d,r,start+i,wall+.01*i)[0])
    d,r=ready();tick(d,r);took,_=tick(d,r,1065,73.)
    check('3_second_cap',not took and r.recovery_started is None and len(d.commands)==1)
    d,r=ready();tick(d,r)
    for i in range(1,20):took,_=tick(d,r,1064+i,70.+i*.01)
    check('20_step_no_progress_exit',not took and r.audit[-1][1]=='recovery_no_progress')
    check('no_restart_after_stall_exit',not tick(d,r,1084)[0])
    d,r=ready();tick(d,r)
    for i,position in enumerate((16.,27.,36.),1):
        d.pose=np.array([position,0.]);took,_=tick(d,r,1064+i)
    check('36px_reliable_separation_exits',not took and r.audit[-1][1]=='recovery_clear')
    check('separation_is_not_inventory_confirmation',d.sensor_inventory==1 and (4,2) not in d.drop_records)
    d,r=ready();tick(d,r);took,_=tick(d,r,1066)
    check('missed_control_frame_exits',not took and r.audit[-1][1]=='recovery_timeout_or_budget_exit')

def bomb_and_wall_cases():
    d,r=ready();values,semantic=sensors(d,r)
    own,objects=r._recovery_obstacles(d,d.angles,values,semantic)
    check('overlapping_own_bomb_recognized',own.all() and not objects)
    check('own_bomb_no_longer_blocks_certified_tube',r._recovery_clear(d,0.,36.,d.angles,values,own,objects))
    own,objects=r._recovery_obstacles(d,d.angles,values,[])
    check('geometry_alone_cannot_remove_returns',not own.any())
    check('unidentified_near_returns_still_block',not r._recovery_clear(d,0.,36.,d.angles,values,own,objects))
    d,r=ready();r.before_drop_scan=None
    check('masked_rays_without_prior_are_not_free',not tick(d,r)[0])
    d,r=ready();stamp,origin,angles,values=r.before_drop_scan
    r.before_drop_scan=(stamp,origin,angles,np.full_like(values,20.))
    took,_=tick(d,r)
    check('near_wall_in_prior_not_erased_by_bomb_filter',not took and r.audit[-1][1]=='recovery_no_safe_path')
    check('unsafe_initial_attempt_consumed_once',r.recovery_used and not tick(d,r,1065)[0])
    d,r=ready();values,semantic=sensors(d,r);values[90]=3.
    own,objects=r._recovery_obstacles(d,d.angles,values,semantic)
    check('nearby_wall_ray_outside_bomb_surface_not_removed',not own[90])
    check('live_wall_blocks_recovery_direction',not r._recovery_clear(d,0.,36.,d.angles,values,own,objects))
    d,r=ready();values,semantic=sensors(d,r)
    other=bomb(0.,20.);own,objects=r._recovery_obstacles(d,d.angles,values,semantic+[other])
    check('other_bomb_stays_an_obstacle',len(objects)==1 and not r._recovery_clear(d,0.,36.,d.angles,values,own,objects))
    d.drop_records[(0,1)]=np.array([24.,0.]);values,semantic=sensors(d,r)
    own,objects=r._recovery_obstacles(d,d.angles,values,semantic)
    check('ambiguous_shared_surface_not_ignored',not r._own_hit(d,0.,7.))
    d,r=ready();ranges=np.full(181,np.nan)
    check('all_missing_current_rays_cannot_use_old_scan_to_move',not tick(d,r,values=ranges)[0])

def live_safety_cases():
    for label,mutate in [
       ('GPS_lost',lambda d,r:setattr(d.grid,'pose_fixed',False)),
       ('odometry_only',lambda d,r:setattr(d,'_odometry_only',True)),
       ('nan_heading',lambda d,r:setattr(d,'heading',float('nan'))),
       ('GPS_jump',lambda d,r:setattr(d,'pose',np.array([80.,0.]))),
       ('nan_odometry',lambda d,r:setattr(d,'odom',np.array([np.nan,0.,0.]))),
       ('odom_jump',lambda d,r:setattr(d,'odom',np.array([15.,0.,0.]))),
       ('pending',lambda d,r:setattr(d,'pending_drop',(1,d.pose.copy(),1064))),
       ('stock_disagreement',lambda d,r:setattr(d,'sensor_inventory',2)),
       ('empty',lambda d,r:(setattr(d,'sensor_inventory',0),setattr(d,'previous_inventory',0)))]:
        d,r=ready();tick(d,r);mutate(d,r);took,_=tick(d,r,1065)
        check('active_recheck_'+label,not took and r.recovery_started is None and r.audit[-1][1]=='recovery_sensor_or_stock_exit')
    d,r=ready();tick(d,r);values,semantic=sensors(d,r);values[90]=3.
    took,c=tick(d,r,1065,values=values,semantic=semantic)
    check('new_wall_aborts_and_brakes_current_frame',took and r.recovery_started is None and c['forward']==0. and c['lateral']==0. and c['place_bomb']==0)
    d,r=ready();tick(d,r);values,semantic=sensors(d,r)
    took,c=tick(d,r,1065,values=values,semantic=semantic+[bomb(0.,15.,'DRONE')])
    check('new_drone_aborts_with_no_pulse',took and r.audit[-1][1]=='recovery_obstacle_exit' and c['place_bomb']==0)
    d,r=ready();tick(d,r);values,semantic=sensors(d,r);values[75:106]=np.nan
    took,_=tick(d,r,1065,values=values,semantic=semantic)
    check('new_unknown_forward_sector_aborts',r.recovery_started is None and r.audit[-1][1]=='recovery_obstacle_exit')
    d,r=ready();route=copy.deepcopy(d.route);records=copy.deepcopy(d.drop_records);tick(d,r)
    check('route_and_actual_drop_records_unchanged',d.route==route and records.keys()==d.drop_records.keys() and all(np.array_equal(v,d.drop_records[k]) for k,v in records.items()))

# Execute the complete candidate control method with a fixed-input base. No
# navigation, physics, sensor renderer or SDK Launcher is invoked.
class BaseStub:
    def control(self):
        self.common.append('base');return dict(place_bomb=1)
tree=ast.parse((ROOT/'candidate/red_hooks.py').read_bytes())
cls=next(c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='RedHooks')
control=next(m for m in cls.body if isinstance(m,ast.FunctionDef) and m.name=='control')
harness=ast.ClassDef(name='ControlHarness',bases=[ast.Name(id='BaseStub',ctx=ast.Load())],keywords=[],body=[copy.deepcopy(control)],decorator_list=[])
ns=dict(vars(hooks),BaseStub=BaseStub)
exec(compile(ast.fix_missing_locations(ast.Module(body=[harness],type_ignores=[])),'<unaltered_candidate_control>','exec'),ns)
Harness=ns['ControlHarness']
def integration_fixture():
    base,r=ready();d=Harness();d.__dict__.update(base.__dict__)
    d.elapsed_timestep=1064;d.submitted=False;d.last_confirmed_drop_step=None;d.common=[];d.drop_departure=r
    d.group_exchange=None;d.closeout=NS(state='IDLE',tick=lambda *a:d.common.append('closeout'))
    d.messenger=NS(tick=lambda *a:(d.common.append('messenger') or False))
    d.lidar_values=lambda:sensors(d,r)[0];d.semantic_values=lambda:sensors(d,r)[1]
    d.pre_submit_scan=NS(refresh_due=lambda *a:False)
    d.memory=NS(observe=lambda *a:(d.common.append('mapping') or ([],[])))
    d.fine_wall_coverage=NS(observe=lambda *a:None)
    d.submission_bearings=NS(observe=lambda *a:None)
    d.team_wall=NS(reservation='old');d.search_roaming=NS(departed=True)
    d.placement.maneuvers=NS(exit=None,waiting_exit=None,remember=lambda *a:None)
    d.placement._ordinary_start_step=lambda limit:limit
    d._update_drop_hints=lambda *a:None
    def forbidden(*a):raise AssertionError('later movement/placement overrode recovery')
    d.fast_closeout=NS(act=forbidden);d.second_drop=NS(observe_route=forbidden)
    d.deadline_submission=DeadlineSubmission();d.deadline_versions={};d.deadline_submission_event=None
    d.budget_submission=BudgetSubmission();d.budget_submission_event=None;d.budget_submission_audit=[]
    d.map_quality=9000;d.map_bids={};d.final_maps=FinalMaps(4,5);d.submissions=[]
    d.first_ready_to_submit_step=None;d.team_exchange_audit=[]
    d.carried_bombs_count=lambda:d.sensor_inventory
    d.odometer_values=lambda:d.odom.copy();d.lidar_rays_angles=lambda:d.angles
    d.submit_exploration_map=lambda image:d.submissions.append(image.copy())
    for name in ['_force_deadline_submission','_try_budget_submission','_budget_submission_gate','_budget_submission_candidate','_all_inventory_empty','_own_map_bid']:
        setattr(d,name,MethodType(getattr(RedHooks,name),d))
    d._sync_placement=MethodType(CoveragePlacementDrone._sync_placement,d)
    return d,r
def control_and_confirmation_cases():
    d,r=integration_fixture();c=d.control()
    check('full_control_recovery_owns_command_before_fast_closeout',r.recovery_started==1064 and c['place_bomb']==0 and np.linalg.norm(d.commands[-1])>0.)
    check('common_mapping_and_messenger_still_run',all(x in d.common for x in ['base','mapping','messenger']))
    check('recovery_does_not_claim_completion_in_full_control',d.sensor_inventory==1 and (4,2) not in d.drop_records and not d.submissions)
    # The existing actual SDK-inventory synchronizer is the success authority.
    d,r=ready();d.pending_drop=(1,np.array([40.,0.]),1064)
    CoveragePlacementDrone._sync_placement(d,1065)
    check('rejected_second_pulse_not_counted',d.previous_inventory==1 and (4,2) not in d.drop_records)
    d.pending_drop=(1,np.array([40.,0.]),1066);d.sensor_inventory=0
    CoveragePlacementDrone._sync_placement(d,1067)
    check('actual_stock_reduction_confirms_second',d.previous_inventory==0 and np.array_equal(d.drop_records[(4,2)],[40.,0.]))

def deadlines_and_scope():
    for label,step,wall in [('wall',1064,178.6),('steps',5396,70.)]:
        d,r=integration_fixture();r.recovery_used=True;r.recovery_started=1063;r.recovery_wall_started=70.
        d.elapsed_timestep=step;d.elapsed_walltime=wall
        d.deadline_submission.backup_image=np.array([[1,0],[0,1]],dtype=np.uint8)
        d.deadline_submission.backup_step=1000
        def forbidden(*a):raise AssertionError('hard deadline entered recovery/navigation')
        d.drop_departure.recover=forbidden
        c=d.control()
        check('hard_'+label+'_preempts_recovery',d.submitted and len(d.submissions)==1 and d.common==[] and c['place_bomb']==0)
    d,r=ready();d.elapsed_timestep=4961;r.recovery_trace.clear()
    for s in range(4931,4961):r.recovery_trace.append((s,d.pose.copy()))
    check('no_recovery_crosses_93pct_budget_start',not tick(d,r,4961)[0] and not r.recovery_used)
    check('hard_and_budget_constants_unchanged',DeadlineSubmission.MIN_WALL_MARGIN==1.5 and BudgetSubmission.window(5400)==(5022,5051))
    build=json.loads((ROOT/'BUILD.json').read_text())
    check('source_hashes_match_frozen_candidate',all(sha256((ROOT/'candidate'/n).read_bytes()).hexdigest()==h for n,h in build['candidate_files'].items()))
    check('only_two_source_files_changed',set(build['changed_files'])=={'red_hooks.py','drop_departure.py'} and build['unchanged_files']==54)

for label,fn in [('1_trigger_and_normal_departure',trigger_cases),('2_once_and_absolute_limits',bounded_cases),
                 ('3_own_bomb_wall_and_unknown',bomb_and_wall_cases),('4_live_safety_exit',live_safety_cases),
                 ('5_control_and_actual_confirmation',control_and_confirmation_cases),('6_deadlines_and_scope',deadlines_and_scope)]:
    category(label,fn)
result=dict(status='PASS',total_checks=len(checks),categories=categories,checks=checks,
    candidate_zip_sha256=json.loads((ROOT/'BUILD.json').read_text())['candidate_zip_sha256'],
    full_matches=0,physics_steps=0,SDK_rounds=0,V16_remains_competition_baseline=True)
(ROOT/'RECOVERY_COUNTEREXAMPLES.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
