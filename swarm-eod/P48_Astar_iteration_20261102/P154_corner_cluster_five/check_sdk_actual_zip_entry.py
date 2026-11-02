from pathlib import Path
import sys,json,hashlib,inspect,importlib.metadata as md,fcntl
lock=Path("/home/junhao/quan/parallel_test_solver/match/solver_study/serial_evaluation.lock").open("a+");fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
F=Path(__file__).resolve().parent;label,arm=sys.argv[1:];dest=F/(label+'.json');assert not dest.exists()
m=json.loads((F/'WORKSPACE_READY.json').read_text())['versions'][arm];W=Path(m['workspace']);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(W/n)==v for n,v in m['sources'].items()) and all(sha(W/n)==v for n,v in m['sdk_files'].items())
sys.path.insert(0,str(W/'src'))
class NoGurobi:
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0]=='gurobipy':raise ImportError('Gurobi not permitted in this candidate')
sys.meta_path.insert(0,NoGurobi())
import numpy as np,numpy.random.mtrand,pandas as pd,cv2,yaml,pyglet
from swarm_rescue.launcher import Launcher
from swarm_rescue.simulation.reporting.stats_computation import StatsComputation
from swarm_rescue.solutions.my_drone_eval import MyDroneEval,drone_class_for_mode
team=yaml.safe_load((W/'src/swarm_rescue/solutions/team_info.yml').read_text());assert type(team['team_number'])is int and team['team_number']==615
assert drone_class_for_mode('place') is MyDroneEval and Path(inspect.getfile(MyDroneEval)).resolve().is_relative_to(W/'src')
assert np.isfinite(np.random.RandomState(615).normal(size=8)).all() and pd.DataFrame({'x':[1,2]}).sum()['x']==3 and cv2.resize(np.zeros((4,4),np.uint8),(2,2)).shape==(2,2)
window=pyglet.window.Window(width=1,height=1,visible=False)
try:
    from swarm_rescue.maps.map_02 import Map02
    arena=Map02(drone_type=MyDroneEval,number_drones=5)
    independent=len({id(d.memory.hits) for d in arena.drones})==5
    assert independent
    from swarm_rescue.solutions.bearing_memory import BearingMemory
    from swarm_rescue.solutions.corner_cluster import corner_cluster_layout
    from swarm_rescue.solutions.corner_mission import CornerMissionMixin
    assert CornerMissionMixin in MyDroneEval.__mro__
    probe=BearingMemory(800,800,identifier=0,team_size=5)
    probe.free[:]=True;probe.hits[1,1:110]=3;probe.hits[1:110,1]=3;probe.step=100
    probe_agents={k:(np.array([-160.+k*64.,0.]),2)for k in range(5)}
    points=[np.array([-320.+(i%5)*144.,320.-(i//5)*480.])for i in range(10)]
    probe_base={k:points[2*k:2*k+2]for k in range(5)}
    before=hashlib.sha256(probe.hits.tobytes()+probe.free.tobytes()).hexdigest()
    actual=corner_cluster_layout(probe,probe_agents,[],72.,probe_base,travel_budget=10000.)
    assert all(len(actual[k])==2 for k in range(5))and all(np.isfinite(p).all()for ps in actual.values()for p in ps)
    assert before==hashlib.sha256(probe.hits.tobytes()+probe.free.tobytes()).hexdigest()
    cluster_interface=dict(actual_BearingMemory_and_GeometryPlanningMemory=True,counts_preserved=True,map_arrays_unchanged=True,audit=probe.corner_cluster_diagnostics)

finally:window.close()
out=dict(status='PASS_SERVER_RESEARCH_ENTRY_NOT_OFFICIAL_RELEASE',arm=arm,workspace=str(W),sources=m['sources'],team_number=615,
    actual_zip_sha256=json.loads((F/'INTERNAL_ZIP_BINDING.json').read_text())['sha256'],interpreter=sys.executable,python_version=sys.version,module_paths={'numpy':np.__file__,'mtrand':numpy.random.mtrand.__file__,'pandas':pd.__file__,'cv2':cv2.__file__},numeric_versions={n:md.version(n) for n in ['numpy','pandas','opencv-contrib-python']},five_native_constructors_independent=True,cluster_interface=cluster_interface,
    physics_steps=0,native_game_rounds=0,dependency_installation=False,official_submission_ready=False)
dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='sources'}))
