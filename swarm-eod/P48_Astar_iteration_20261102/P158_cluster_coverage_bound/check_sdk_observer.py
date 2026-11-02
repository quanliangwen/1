"""Real public sensors/messages/actuation, one authored internal-wall arena.
Fixed author seed and synthetic wall inputs only for paired small closure.
No official maps/BLUE; no complete red score without a BLUE stage.
"""
from pathlib import Path
from types import SimpleNamespace
import contextlib,fcntl,hashlib,io,json,random,sys,time,traceback
import numpy as np
F=Path(__file__).resolve().parent;arm=sys.argv[1];dest=F/(arm+'_SDK_FIRST.json');assert not dest.exists()
R=Path('/home/junhao/quan/parallel_test_solver/match');m=json.loads((F/'WORKSPACE_READY.json').read_text())['versions'][arm];W=Path(m['workspace']);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(W/n)==h for n,h in m['sources'].items());assert all(sha(W/n)==h for n,h in m['sdk_files'].items())
sys.path.insert(0,str(W/'src'))
import pandas,cv2,numpy.random.mtrand
assert np.random.default_rng(615).normal(size=3).shape==(3,)
from swarm_rescue.launcher import Launcher
from swarm_rescue.simulation.reporting.stats_computation import StatsComputation
from swarm_rescue.solutions.my_drone_eval import MyDroneEval as Original

# Observation only: capture actual local frame arrays at the first 10-slot call.
# Do not invoke geometry/value helpers an extra time or mutate their caches.
import swarm_rescue.solutions.team_coverage_lns as supplier_module
raw_corner=supplier_module.corner_cluster_layout
model_snapshots=[]
def capture_profile(frame,event,arg):
 if event!='return' or frame.f_code is not raw_corner.__code__ or model_snapshots:return
 local=frame.f_locals
 if local.get('total')!=10 or 'ranked'not in local:return
 export={}
 for name in ['allowed','walkable','values','residual','xx','yy']:
  if name in local:export[name]=np.asarray(local[name]).tolist()
 export.update(baseline=float(local['baseline']),baseline_points=[np.asarray(p).tolist()for p in local['baseline_points']],radius=float(local['radius']),cell=float(local['pm'].CELL),initial_total=local['state']['initial_total'],target_total=local['target_total'],step=int(local['memory'].step),owner=int(local['memory'].identifier),corners=[dict(rank=float(x[0]),pivot=[x[1],x[2]],anchor=np.asarray(x[3]).tolist(),region=np.asarray(x[4]).tolist())for x in local['ranked']])
 model_snapshots.append(export)
def capture_corner(*args,**kwargs):
 if model_snapshots:return raw_corner(*args,**kwargs)
 previous=sys.getprofile();sys.setprofile(capture_profile)
 try:return raw_corner(*args,**kwargs)
 finally:sys.setprofile(previous)
supplier_module.corner_cluster_layout=capture_corner
from swarm_rescue.simulation.gui_map.playground import Playground
from swarm_rescue.simulation.gui_map.closed_playground import ClosedPlayground
from swarm_rescue.simulation.elements.normal_wall import NormalWall
from swarm_rescue.simulation.elements.disposal_center import DisposalCenter
from swarm_rescue.simulation.utils.misc_data import MiscData
events=[];routes=[];drops=[];submissions=[]
point=lambda p:None if p is None else np.asarray(p).tolist()
class Drone(Original):
 def _plan_route(self,step,returning,peer_goals):
  before=dict(goal=point(self.assignment_goal),inventory=int(self.carried_bombs_count()),epoch=None if self.fleet_plan is None else self.fleet_plan[0])
  result=super()._plan_route(step,returning,peer_goals)
  a=getattr(self.memory,'corner_cluster_diagnostics',None)
  routes.append(dict(owner=int(self.identifier or 0),step=step,before=before,after=dict(goal=point(self.assignment_goal),placement=point(self.placement_goal),inventory=int(self.carried_bombs_count()),epoch=None if self.fleet_plan is None else self.fleet_plan[0]),context_valid=getattr(self,'_valid_corner_context',lambda *a:False)(getattr(self,'corner_context',None),step),audit=None if a is None else dict(a)))
  return result
 def _should_defer_commitment(self,*args):
  result=super()._should_defer_commitment(*args)
  events.append(dict(kind='DEFER',owner=int(self.identifier or 0),step=int(self.elapsed_timestep),target=point(self.placement_goal),decision=bool(result)))
  return result
 def _reject_assignment(self,step,p):
  events.append(dict(kind='REJECT',owner=int(self.identifier or 0),step=step,target=point(p)))
  return super()._reject_assignment(step,p)
 def _sync_placement(self,step):
  before=self.previous_inventory;result=super()._sync_placement(step)
  if before is not None and int(self.carried_bombs_count())<before:drops.append(dict(owner=int(self.identifier or 0),step=step,inventory=int(self.carried_bombs_count()),own_pose=point(self.pose),context=getattr(self,'corner_context',None)))
  return result
 def submit_exploration_map(self,image):
  result=super().submit_exploration_map(image);submissions.append(dict(owner=int(self.identifier or 0),step=int(self.elapsed_timestep),image=self._exploration_map_submission.copy()));return result
class OfficialInteractionPlayground(Playground):
 _handle_interactions=ClosedPlayground._handle_interactions
 get_closest_drone=ClosedPlayground.get_closest_drone
lock=(R/'solver_study/serial_evaluation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);pg=None
try:
 np.random.seed(615);random.seed(615);pg=OfficialInteractionPlayground(size=(800,600));ClosedPlayground._walls_creation(pg,6)
 # Identical fixed arena for both arms; no wall geometry supplied to policy.
 segments=[((-40.,-180.),(-40.,160.)),((-40.,40.),(200.,40.)),((80.,-120.),(240.,-120.)),((140.,160.),(260.,160.))]
 for a,b in segments:
  wall=NormalWall(a,b);pg.add(wall,wall.wall_coordinates)
 center=DisposalCenter(size=(40,40));pg.add(center,((280.,220.),0.))
 fixture=SimpleNamespace(disposal_center=center,_bombs=[],_number_bombs=0,playground=pg)
 drones=[]
 for i,p in enumerate([(-260.,-200.),(-180.,-200.),(-260.,-120.),(-180.,-120.),(-100.,-200.)]):
  d=Drone(i,misc_data=MiscData(size_area=(800,600),number_drones=5,max_timestep_limit=2000,max_walltime_limit=90));pg.add(d,(p,0.));d.enable_bomb_deployer(fixture,2);d.set_competition_mode(True);drones.append(d)
 pg.reset();rows=[];start=time.monotonic();capture=io.StringIO()
 with contextlib.redirect_stdout(capture):
  for step in range(1,1601):
   commands={};messages={}
   for d in drones:
    d.elapsed_timestep=step;d.elapsed_walltime=.05*step
    commands[d]=d.control();messages[d]={d.communicator:(None,d.define_message_for_all())}
   pg.step(commands,messages)
   rows.append(dict(step=step,health=[d.drone_health for d in drones],inventory=[int(d.carried_bombs_count())for d in drones],positions=[list(d.base._pm_body.position)for d in drones],commands=[commands[d]for d in drones]))
   if any(d.submitted for d in drones):break
 elapsed=time.monotonic()-start
 # All actions/output images frozen before authored truth/actual objects used for evaluation.
 frozen_images=[d.memory.render().copy()for d in drones]
 from swarm_rescue.simulation.reporting.place_score_manager import PlaceScoreManager,walls_and_boundary_grid
 from swarm_rescue.tools.map_exploration_scoring import MapExplorationScorer,breakdown_to_dict
 wall_truth,boundary_truth=walls_and_boundary_grid(pg);scorer=MapExplorationScorer();manager=PlaceScoreManager()
 positions=[np.asarray(b.true_position(),float).tolist()for b in fixture._bombs]
 wall_score=manager.compute_wall_score(positions,wall_truth,boundary_mask=boundary_truth,expected_n_bombs=10)
 time_score=manager.compute_time_score(len(rows),2000)
 submitted=[dict(owner=s['owner'],step=s['step'],score=scorer.score(wall_truth,s['image'],0.).score,breakdown=breakdown_to_dict(scorer.score(wall_truth,s['image'],0.)))for s in submissions]
 map_score=None if not submitted else submitted[0]['score']
 accepted=[]
 for route in routes:
  a=route['audit']
  if a and a.get('accepted'):
   key=(a['step'],tuple(a['anchor']),route['owner'])
   if not any(e['key']==key for e in accepted):accepted.append(dict(key=key,audit=a))
 concentration=[dict(owner=e['key'][2],step=e['audit']['step'],anchor=e['audit']['anchor'],radius=e['audit']['radius'],model_clustered=e['audit']['clustered'],physical_strict=sum(np.linalg.norm(np.asarray(p)-np.asarray(e['audit']['anchor']))<=e['audit']['radius']+1e-8 for p in positions),physical_with12=sum(np.linalg.norm(np.asarray(p)-np.asarray(e['audit']['anchor']))<=e['audit']['radius']+12+1e-8 for p in positions))for e in accepted]
 scores=dict(map_raw=map_score,wall_raw=100*wall_score.score,time_raw=100*time_score.score,layout_raw=None,map_weighted=None if map_score is None else .5*map_score,wall_weighted=20*wall_score.score,time_weighted=10*time_score.score,layout_weighted=None,controllable_subtotal=None if map_score is None else .5*map_score+20*wall_score.score+10*time_score.score,full_red_score=None,BLUE_evaluated=False,wall_breakdown=wall_score.breakdown)
 out=dict(status='AUTHOR_SDK_COMPLETED',arm=arm,source_sha256=m['sources'],SDK_sha256=m['sdk_files'],ABI=dict(numpy=np.__version__,pandas=pandas.__version__,opencv=cv2.__version__),physics_steps=len(rows),elapsed_seconds=elapsed,rows=rows,events=events,routes=routes,drops=drops,accepted=accepted,concentration=concentration,actual_bombs=positions,placed=len(positions),submitted=submitted,scores=scores,health_min=[min(r['health'][i]for r in rows)for i in range(5)],numeric_finite=all(np.isfinite(list(c.values())).all()for r in rows for c in r['commands']),official_callbacks=type(pg)._handle_interactions is ClosedPlayground._handle_interactions and len(pg.space._handlers)==7,native_rounds=0,truth_only_after_output_freeze=True,production_public_getters_overridden=False,limitation=__doc__)
 (F/(arm+'_own_author_console_FIRST.log')).write_text(capture.getvalue())
 out['model_snapshots']=model_snapshots
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=out['status'],arm=arm,scores=scores,steps=len(rows),placed=len(positions),health=out['health_min'],max_cluster=max((e['physical_strict']for e in concentration),default=0))))
finally:
 if pg is not None:pg.cleanup();pg.close_window()
 fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
