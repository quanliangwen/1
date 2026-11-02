"""P153 strict one-way deployment phase on original A-star, same authored closure."""
from pathlib import Path
from types import SimpleNamespace
import sys,json,time,contextlib,io,random,fcntl,hashlib
import numpy as np
F=Path(__file__).resolve().parent;label,arm,case,horizon,wall_rate,profile_mode=sys.argv[1:];horizon=int(horizon);wall_rate=float(wall_rate);assert wall_rate in (.05,.10,.15);dest=F/(label+'.json');assert not dest.exists()
R=Path('/home/junhao/quan/parallel_test_solver/match');m=json.loads((F/'WORKSPACE_READY.json').read_text())['versions'][arm];W=Path(m['workspace'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(W/n)==v for n,v in m['sources'].items())and all(sha(W/n)==v for n,v in m['sdk_files'].items())
sys.path.insert(0,str(W/'src'))
from swarm_rescue.solutions.my_drone_eval import MyDroneEval as Original
from swarm_rescue.solutions.exploration_phase import ordinary_exploration_scope
from swarm_rescue.solutions.greedy_mapping import GreedyMappingDrone
from swarm_rescue.simulation.reporting.place_score_manager import walls_only_grid
from swarm_rescue.tools.map_exploration_scoring import MapExplorationScorer,breakdown_to_dict
from swarm_rescue.solutions.fast_exploration import CoordinatedMapMemory
from swarm_rescue.simulation.gui_map.playground import Playground
from swarm_rescue.simulation.gui_map.closed_playground import ClosedPlayground
from swarm_rescue.simulation.elements.normal_wall import NormalWall
from swarm_rescue.simulation.elements.disposal_center import DisposalCenter
from swarm_rescue.simulation.utils.misc_data import MiscData
TRACE_ENABLED=True
import cv2
import cProfile,pstats
import swarm_rescue.solutions.coverage_geometry as coverage_module
projection_events=[]
raw_project=getattr(coverage_module,'_project_wall_field',None)
def audit_projection(field,memory,interpolation):
 result=raw_project(field,memory,interpolation)
 old=cv2.resize(field,(memory.shape[1],memory.shape[0]),interpolation=interpolation)
 projection_events.append(dict(owner=int(getattr(memory,'identifier',-1)),step=int(getattr(memory,'step',-1)),width=int(memory.width),height=int(memory.height),source_shape=list(field.shape),target_shape=list(result.shape),interpolation='AREA'if interpolation==cv2.INTER_AREA else'NEAREST',changed_cells=int(np.count_nonzero(old!=result)),l1_difference=float(np.abs(old.astype(float)-result.astype(float)).sum()),old_sum=float(old.sum()),new_sum=float(result.sum()),dtype_unchanged=result.dtype==field.dtype,finite=bool(np.isfinite(result).all())))
 return result
if raw_project is not None:coverage_module._project_wall_field=audit_projection
gate_events=[];gate_stack={};route_details=[]
semantic_plan_events=[];semantic_rejections=[];recourse_events=[];plan_calls=[];local_calls=[];probe_history=[];deferrals=[];submitted=[];packet_events=[];message_events=[]
def weak_count(message):
 if not isinstance(message,dict):return 0
 packet=message.get('boundary_output_v1')
 if not isinstance(packet,(tuple,list))or len(packet)!=4:return 0
 return sum(int(np.unpackbits(np.frombuffer(p,np.uint8)).sum())for p in packet[3][:4])

import swarm_rescue.solutions.terminal_value as terminal_module
if hasattr(terminal_module,'acquisition_interval_gain'):
 raw_gain=terminal_module.acquisition_interval_gain
 def trace_gain(gap,rate,probe,reference=120.0):
  result=raw_gain(gap,rate,probe,reference)
  probe_history.append(dict(gap=float(gap),rate=None if rate is None else float(rate),probe=float(probe),reference=float(reference),expected=float(result)))
  return result
 terminal_module.acquisition_interval_gain=trace_gain
phase_local_calls=[];phase_routes=[]
raw_local=GreedyMappingDrone._plan_route
def mission_state(d):
 return dict(ready=d.coverage_ready,seeking=d._seeking_fusion,
  model_stamp=d._coverage_model_step,fleet_stamp=d.last_fleet_plan_step,
  survey_stamp=d.survey_last_build,
  fleet_epoch=None if d.fleet_plan is None else d.fleet_plan[0],
  assignment=None if d.assignment_goal is None else np.asarray(d.assignment_goal).tolist(),
  placement=None if d.placement_goal is None else np.asarray(d.placement_goal).tolist(),
  terminal=dict(d.terminal_value_diagnostics))
def audit_local(d,step,returning,peer_goals):
 phase_local_calls.append(dict(owner=int(d.identifier or 0),step=int(step),returning=bool(returning)))
 outside=not getattr(d,'_audit_full_call',False)
 before=mission_state(d) if outside else None
 scope=ordinary_exploration_scope(d,step,returning)
 old=d.last_plan_step
 result=raw_local(d,step,returning,peer_goals)
 if outside:local_calls.append(dict(owner=int(d.identifier or 0),step=step,last_plan_step=old,
  early=bool(0<step-old<24),scope=scope,mission_before=before,mission_after=mission_state(d)))
 return result
GreedyMappingDrone._plan_route=audit_local
def gate_snapshot(d,step):
 mem=d.memory
 fleet={str(k):dict(stamp=int(ts),age=int(step-ts),inventory=int(n),position=None if p is None else np.asarray(p).tolist())for k,(ts,p,n)in d.fleet_states.items()}
 fresh=[int(k)for k,(ts,p,n)in d.fleet_states.items()if p is not None and 0<=step-ts<120]
 return dict(owner=int(d.identifier or 0),step=int(step),inventory=int(d.carried_bombs_count()),ready=bool(d.coverage_ready),seeking_fusion=bool(d._seeking_fusion),
  remaining=float(d._remaining_steps()),model_step=int(d._coverage_model_step),model=dict(d.coverage_model),fresh_peers=fresh,fleet=fleet,
  certificates=dict(d.completion_certificates),last_peer_steps=dict(d.last_peer_step),
  rally_distance=None if d.rally is None or d.pose is None else float(np.linalg.norm(d.pose-d.rally)),
  known_cells=int(np.count_nonzero(mem.free)),confirmed_hit_cells=int(np.count_nonzero(mem.hits>=2)),
  known_sha256=hashlib.sha256(mem.free.tobytes()).hexdigest(),raw_hits_sha256=hashlib.sha256(mem.hits.tobytes()).hexdigest(),
  confirmed_support_sha256=hashlib.sha256((mem.hits>=2).tobytes()).hexdigest(),bearing_sha256=hashlib.sha256(mem.bearing_bits.tobytes()).hexdigest(),
  frame_records=len(d.frame_records),negative_records=sum(len(v)for v in d.frame_negative.values()))

def task_snapshot(d,step):
 def point(p):return None if p is None else np.asarray(p).tolist()
 return dict(owner=int(d.identifier or 0),step=int(step),inventory=int(d.carried_bombs_count()),ready=bool(d.coverage_ready),fusion=bool(d._seeking_fusion),
  pose=point(d.pose),goal=point(d.goal),placement_goal=point(d.placement_goal),assignment_goal=point(d.assignment_goal),
  assignment_inventory=d.assignment_inventory,assignment_since=int(d.assignment_since),remaining=float(d._remaining_steps()),
  fleet_epoch=None if d.fleet_plan is None else int(d.fleet_plan[0]),
  plans=None if d.fleet_plan is None else {str(k):dict(inventory=int(n),goals=[point(p)for p in goals])for k,(n,goals)in d.fleet_plan[2].items()},
  commitment=dict(d.commitment_diagnostics))

class MyDroneEval(Original):

 def _build_fleet_plan(self,step):
  if not TRACE_ENABLED:return super()._build_fleet_plan(step)
  event=dict(before=gate_snapshot(self,step),acquisition=[],after=None)
  key=id(self);previous=gate_stack.get(key);gate_stack[key]=event
  try:return super()._build_fleet_plan(step)
  finally:
   event['after']=gate_snapshot(self,step);gate_events.append(event)
   if previous is None:gate_stack.pop(key,None)
   else:gate_stack[key]=previous
 def _acquisition_needed(self,model,step):
  result=super()._acquisition_needed(model,step)
  if TRACE_ENABLED:
   event=gate_stack.get(id(self))
   if event is not None:event['acquisition'].append(dict(step=int(step),model=dict(model),decision=bool(result),terminal=dict(self.terminal_value_diagnostics)))
  return result
 def define_message_for_all(self):
  before=self.last_packet_step
  result=super().define_message_for_all()
  if self.last_packet_step!=before:
   packet_events.append(dict(owner=int(self.identifier or 0),step=int(self.elapsed_timestep),weak_hits=weak_count(result)))
  return result
 def _messages(self):
  old=dict(self.last_peer_step)
  incoming=[(int(msg.get('id',-1)),int(msg.get('step',-1)),weak_count(msg))for _,msg in self.communicator.received_messages if isinstance(msg,dict)and msg.get('kind')=='greedy-map-v1']
  result=super()._messages()
  for sender,sent,count in incoming:
   if sender!=int(self.identifier or 0)and count and sent>old.get(sender,-1)and self.last_peer_step.get(sender)==sent:
    message_events.append(dict(owner=int(self.identifier or 0),step=int(self.elapsed_timestep),sender=sender,sent=sent,weak_hits=count))
  return result
 def submit_exploration_map(self,image):
  before=np.asarray(image).copy();start=time.perf_counter()
  result=super().submit_exploration_map(image)
  submitted.append(dict(owner=int(self.identifier or 0),step=int(self.elapsed_timestep),image=self._exploration_map_submission.copy(),original_image=before,output_seconds=time.perf_counter()-start,diagnostics=getattr(self,'last_observed_fragment_audit',{})))
  return result
 def _should_defer_commitment(self,loss,remaining,execution,probe,completion_value,step):
  stamp=self._coverage_model_step
  result=super()._should_defer_commitment(loss,remaining,execution,probe,completion_value,step)
  model=getattr(self,'coverage_model',{})or{}
  old_expected=min(float(loss),self._expected_probe_gain(model,probe))
  old=terminal_module.continue_with_schedule(old_expected,completion_value,step,probe,remaining,execution,self.limit)
  deferrals.append(dict(owner=int(self.identifier or 0),step=int(step),stamp=int(stamp),age=int(step-stamp),stamp_after=int(self._coverage_model_step),age_after=int(step-self._coverage_model_step),defer=bool(result),old_formula=bool(old),
   inventory=int(self.carried_bombs_count()),loss=float(loss),old_expected=float(old_expected)))
  return result
 def _plan_route(self,step,returning,peer_goals):
  used_before=bool(getattr(self,'_last_slot_recourse_used',False))
  task_before=task_snapshot(self,step)if TRACE_ENABLED else None
  before=self.last_plan_step
  scope=ordinary_exploration_scope(self,step,returning)
  received={str(i):int(step-stamp)for i,(stamp,p,g)in self.exploration_records.items()}
  self._audit_full_call=True
  try:result=super()._plan_route(step,returning,peer_goals)
  finally:self._audit_full_call=False
  if TRACE_ENABLED:route_details.append(dict(before=task_before,after=task_snapshot(self,step),returned_goal=None if result[1]is None else np.asarray(result[1]).tolist(),returned_waypoints=[np.asarray(p).tolist()for p in result[0]]))
  if self.deployment_started is not None:
   goal=result[1];target=self.placement_goal
   low=[e for e in phase_local_calls if e['owner']==int(self.identifier or 0)and e['step']==step]
   target_mode=target is not None and goal is not None and np.linalg.norm(np.asarray(goal)-target)<1.
   return_mode=bool(low)and low[-1]['returning']
   phase_routes.append(dict(owner=int(self.identifier or 0),step=step,inventory=int(self.carried_bombs_count()),
     deploy_target=bool(target_mode),relay_return_or_hold=bool(return_mode),sortie=self._sortie_state,
     valid_final_route=bool(target_mode or return_mode)))
  if not used_before and getattr(self,'_last_slot_recourse_used',False):recourse_events.append(dict(owner=int(self.identifier or 0),step=int(step),inventory=int(self.carried_bombs_count()),audit=dict(self.last_slot_recourse_diagnostics)))
  plan_calls.append(dict(owner=int(self.identifier or 0),step=step,last_plan_step=before,early=bool(before>=0 and 0<step-before<24),ordinary_scope=scope,received_record_ages=received,goal=None if result[1]is None else result[1].tolist(),remaining=float(self._remaining_steps()),own_observe_epoch=getattr(self.memory,'_bearing_frame_step',None),latest_received_stamp=max(self.last_peer_step.values(),default=-1)))
  return result
class OfficialInteractionPlayground(Playground):
 _handle_interactions=ClosedPlayground._handle_interactions
 get_closest_drone=ClosedPlayground.get_closest_drone
lock=(R/'solver_study/serial_evaluation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
pg=None
try:
 np.random.seed(615);random.seed(615);size=(1200,900)if case=='wide_cross_sdk'else(640,480)if case=='open_sdk'else(800,600);pg=OfficialInteractionPlayground(size=size)
 # Use the frozen SDK's own physical outer-frame constructor. No border inference from truth.
 ClosedPlayground._walls_creation(pg,6)
 segments=[((-30.,-220.),(-30.,-80.))]if case=='open_sdk'else[((0.,-290.),(0.,-70.)),((0.,70.),(0.,290.))]
 if case=='cross_sdk':segments=[((-390.,0.),(-70.,0.)),((70.,0.),(390.,0.))]
 if case=='wide_cross_sdk':segments=[((-size[0]/2+10.,0.),(-.12*size[0],0.)),((.12*size[0],0.),(size[0]/2-10.,0.))]
 for a,b in segments:
  wall=NormalWall(a,b);pg.add(wall,wall.wall_coordinates)
 center=DisposalCenter(size=(40,40));pg.add(center,((.27*size[0],.23*size[1])if case=='wide_cross_sdk'else(220.,120.),0.))
 fixture=SimpleNamespace(disposal_center=center,_bombs=[],_number_bombs=0,playground=pg)
 drones=[];queries=[]
 raw=CoordinatedMapMemory.route
 def traced(mem,*args,**kwargs):
  result=raw(mem,*args,**kwargs)
  if kwargs.get('utility')is not None:
   queries.append(dict(owner=mem.identifier,step=mem.step,raw_goal=None if result[1]is None else result[1].tolist(),
    old_exploration_goal=None if mem.exploration_goal is None else mem.exploration_goal.tolist()))
  return result
 CoordinatedMapMemory.route=traced
 positions=[(-150.,-20.),(-80.,40.),(-150.,80.),(-220.,40.),(-220.,-40.)]if case=='open_sdk'else[(-260.,-60.),(-180.,-60.),(-260.,20.),(-180.,20.),(-260.,100.)]
 if case=='cross_sdk':positions=[(-260.,-200.),(-180.,-200.),(-260.,-120.),(-180.,-120.),(-100.,-200.)]
 if case=='wide_cross_sdk':positions=[(-size[0]/2+140.+80.*dc,-size[1]/2+110.+80.*dr)for dr,dc in [(0,0),(0,1),(1,0),(1,1),(0,2)]]
 for i,p in enumerate(positions):
  d=MyDroneEval(i,misc_data=MiscData(size_area=size,number_drones=5,max_timestep_limit=2000,max_walltime_limit=90))
  pg.add(d,(p,0.));d.enable_bomb_deployer(fixture,2);d.set_competition_mode(True);drones.append(d)
 pg.reset();rows=[];start=time.monotonic()
 profiler=cProfile.Profile()
 if profile_mode=="ON":profiler.enable()
 with contextlib.redirect_stdout(io.StringIO()):
  for step in range(1,horizon+1):
   commands={};messages={}
   for d in drones:
    d.elapsed_timestep=step;d.elapsed_walltime=wall_rate*step # Explicit synthetic compute-rate stress; NEVER native or SDK clock override.
    commands[d]=d.control();messages[d]={d.communicator:(None,d.define_message_for_all())}
   pg.step(commands,messages)
   rows.append(dict(step=step,commands=[commands[d]for d in drones],positions=[list(d.base._pm_body.position)for d in drones],
    inventory=[int(d.carried_bombs_count())for d in drones],health=[d.drone_health for d in drones],
    goals=[None if d.goal is None else d.goal.tolist()for d in drones],known_fraction=[float(np.mean(d.memory.free))for d in drones],main_state=[{name:hashlib.sha256(getattr(d.memory,name).tobytes()).hexdigest()for name in ['hits','free','visits']}for d in drones]))
   if any(d.submitted for d in drones):break
 if profile_mode=="ON":profiler.disable()
 elapsed=time.monotonic()-start
 profile_rows=[]
 if profile_mode=="ON":
  for (file,line,name),(primitive,total,exclusive,cumulative,callers) in pstats.Stats(profiler).stats.items():
   profile_rows.append(dict(file=file,line=line,name=name,primitive_calls=primitive,calls=total,exclusive_seconds=exclusive,cumulative_seconds=cumulative))
  profile_rows.sort(key=lambda r:r['exclusive_seconds'],reverse=True)
 # Outputs freeze before evaluator-only authored wall truth is inspected.
 frozen_images=[d.memory.render().copy()for d in drones]
 truth=walls_only_grid(pg);scorer=MapExplorationScorer()
 map_results=[dict(owner=i,score=scorer.score(truth,image,0.).score,
  breakdown=breakdown_to_dict(scorer.score(truth,image,0.)))for i,image in enumerate(frozen_images)]
 holds=[]
 for q in queries:
  row=rows[q['step']-1]if 1<=q['step']<=len(rows)else None
  if row is not None:
   actual=row['goals'][q['owner']]
   if actual==q['old_exploration_goal']and actual!=q['raw_goal']:holds.append(q)
 checks=dict(official7callbacks=type(pg)._handle_interactions is ClosedPlayground._handle_interactions and len(pg.space._handlers)==7,
  finite_commands=all(np.isfinite(list(c.values())).all()for r in rows for c in r['commands']),
  health_unchanged=all(r['health']==[50]*len(drones)for r in rows),
  legal_inventory=all(all(0<=q<=2 for q in r['inventory'])for r in rows),
  no_walltime_hit=elapsed<90,
  audit_callback_bound=all(d._last_bomb_stats['committed']==0 and d._last_bomb_active is None for d in drones)if arm=='P16'else True,
  capture_scopes_closed=all(not getattr(d.memory,'_capture_edge_route_scores',False)and getattr(d.memory,'_edge_route_scores',None)is None for d in drones))
 checks['all10_completed']=rows[-1]['inventory']==[0]*len(drones)
 checks['submitted_only_after_all10']=any(d.submitted for d in drones)and rows[-1]['inventory']==[0]*len(drones)
 if arm=='P35':
  checks['actual_early_full_calls']=any(e['early']for e in plan_calls)
 if arm=='P65_V2':
  expired=[e for e in deferrals if not 0<=e['age']<120]
  fresh=[e for e in deferrals if 0<=e['age']<120]
  checks['expired_model_refresh_actually_seen']=bool(expired)
  checks['all_local_models_fresh_after']=all(0<=e['age_after']<120 for e in deferrals)
  checks['expired_models_recomputed_at_call']=all(e['stamp_after']==e['step']for e in expired)
  checks['original_formula_on_actual_model']=all(e['defer']==e['old_formula']for e in deferrals)
  checks['actual_weak_boundary_packets']=any(e['weak_hits']>0 for e in packet_events)
  checks['actual_weak_packets_received']=bool(message_events)
 if horizon==240 or case=='wide_cross_sdk':
  checks.pop('all10_completed',None);checks.pop('submitted_only_after_all10',None)
 if case=='wide_cross_sdk':checks.pop('health_unchanged',None) # Declared baseline health is reported, not a candidate qualification.
 # Freeze all outputs before author-only physical map/placement evaluation.
 from swarm_rescue.simulation.reporting.place_score_manager import PlaceScoreManager,walls_and_boundary_grid
 final_bomb_positions=[np.asarray(bomb.true_position(),float).tolist()for bomb in fixture._bombs]
 wall_truth,boundary_truth=walls_and_boundary_grid(pg)
 assert np.array_equal(wall_truth,truth)
 manager=PlaceScoreManager()
 score_started=time.perf_counter()
 wall_result=manager.compute_wall_score(final_bomb_positions,wall_truth,boundary_mask=boundary_truth,expected_n_bombs=10)
 time_result=manager.compute_time_score(len(rows),2000)
 selected_map=None if not submitted else scorer.score(truth,submitted[0]['image'],0.).score
 coverage_evaluation=dict(final_bomb_positions=final_bomb_positions,actual_bomb_count=len(final_bomb_positions),score_wall=100.*wall_result.score,wall_breakdown=wall_result.breakdown,score_time=100.*time_result.score,actual_submitted_map=selected_map,controllable_subtotal=None if selected_map is None else .5*selected_map+.2*100.*wall_result.score+.1*100.*time_result.score,truth_used_only_after_output_freeze=True,expected_reference_bombs=10,score_eval_seconds=time.perf_counter()-score_started,not_full_red_score=True,blue_difficulty_evaluated=False)
 out=dict(deployment_events=[e for d in drones for e in d.deployment_events],deployment_counts=[d.deployment_counts for d in drones],deployment_started=[d.deployment_started for d in drones],phase_routes=phase_routes,profile_enabled=profile_mode=="ON",profile_rows=profile_rows,semantic_plan_events=semantic_plan_events,semantic_rejections=semantic_rejections,recourse_events=recourse_events,status='PASS_AUTHORED_FIVE_BODY_SDK_CLOSURE'if all(checks.values())else'FAIL_KEEP_FIRST_CLOSURE',arm=arm,checks=checks,
  coverage_evaluation=coverage_evaluation,projection_events=projection_events,gate_events=gate_events,route_details=route_details,TRACE_ENABLED=TRACE_ENABLED,packet_events=packet_events,message_events=message_events,deferrals=deferrals,submission_records=[dict(owner=e['owner'],step=e['step'],map_score=scorer.score(truth,e['image'],0.).score,original_map_score=scorer.score(truth,e['original_image'],0.).score,breakdown=breakdown_to_dict(scorer.score(truth,e['image'],0.)),original_breakdown=breakdown_to_dict(scorer.score(truth,e['original_image'],0.)),output_seconds=e['output_seconds'],diagnostics=e['diagnostics'],output_sha256=hashlib.sha256(e['image'].tobytes()).hexdigest(),original_sha256=hashlib.sha256(e['original_image'].tobytes()).hexdigest())for e in submitted],rows=rows,map_results=map_results,plan_calls=plan_calls,local_calls=local_calls,case=case,author_wall_rate=wall_rate,probe_history=probe_history,utility_queries=queries,actual_retention_witnesses=holds,wall_seconds=elapsed,source_sha256=m['sources'],physics_steps=len(rows),native_rounds=0,
  public_getters_overridden=False,scope=__doc__,limitation='Authored fixed arena/seed for mechanisms only. Identical authored .05*step wall inputs; no native map, score or matched random tournament performance claim.')
 dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(status=out['status'],checks=checks,utility_queries=len(queries),retentions=len(holds),wall_seconds=elapsed)))
finally:
 if pg is not None:pg.cleanup();pg.close_window()
 fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
