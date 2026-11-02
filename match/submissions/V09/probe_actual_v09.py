from pathlib import Path
import importlib.abc,importlib.metadata as md,json,sys,hashlib,subprocess
F=Path(__file__).resolve().parent;label=sys.argv[1];dest=F/('ABI_'+label+'.json');assert not dest.exists()
R=Path('/home/junhao/quan/parallel_test_solver/match');shared=R/'.venv/lib/python3.11/site-packages';sys.path.append(str(shared))
build=json.loads((F/'BUILD.json').read_text());ws=json.loads((F/'WORKSPACE_READY.json').read_text());W=Path(ws['workspace']);sys.path.insert(0,str(W/'src'))
class NoGurobi(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='gurobipy'or fullname.startswith('gurobipy.'):raise ImportError('Gurobi explicitly unavailable for P48 release check')
sys.meta_path.insert(0,NoGurobi())
import numpy as np,numpy.random.mtrand as mt,pandas as pd,cv2
assert np.isfinite(np.random.RandomState(615).normal(size=128)).all()
assert pd.DataFrame({'a':[1.,2.,3.]}).a.sum()==6.
assert cv2.filter2D(np.ones((8,8),np.float32),-1,np.ones((3,3),np.float32)).shape==(8,8)
for n,h in build['payload_files_sha256'].items():assert hashlib.sha256((W/'req.txt'if n=='req.txt'else W/'src/swarm_rescue/solutions'/n).read_bytes()).hexdigest()==h
for n,h in ws['sdk_files'].items():assert hashlib.sha256((W/n).read_bytes()).hexdigest()==h
from swarm_rescue.launcher import Launcher
from swarm_rescue.simulation.reporting.stats_computation import StatsComputation
from swarm_rescue.simulation.reporting.team_info import TeamInfo
from swarm_rescue.solutions.my_drone_eval import MyDroneEval,drone_class_for_mode
assert type(TeamInfo().team_number)is int and TeamInfo().team_number==615 and drone_class_for_mode('place')is MyDroneEval
import pyglet
window=pyglet.window.Window(width=1,height=1,visible=False)
try:
 from swarm_rescue.maps.map_01 import Map01
 arena=Map01(drone_type=MyDroneEval,number_drones=5)
 assert len(arena.drones)==5 and len({id(d.memory.hits)for d in arena.drones})==5
finally:window.close()
assert 'gurobipy'not in sys.modules
for name,m in list(sys.modules.items()):
 if name.startswith('swarm_rescue.solutions')and getattr(m,'__file__',None):
  p=Path(m.__file__).resolve();assert p.is_relative_to((W/'src/swarm_rescue/solutions').resolve());assert hashlib.sha256(p.read_bytes()).hexdigest()==build['payload_files_sha256'][p.name]
report=F/('INSTALL_DRY_RUN_'+label+'.json');assert not report.exists()
helper=''if label!='native_main'else 'sys.path.append('+repr(str(F/'env_numpy1/lib/python3.11/site-packages'))+');'
code='import sys,runpy;'+helper+'sys.path.append('+repr(str(shared))+');sys.argv='+repr(['pip','install','--dry-run','--no-index','--report',str(report),'-r',str(W/'req.txt')])+";runpy.run_module('pip',run_name='__main__')"
dry=subprocess.run([sys.executable,'-I','-c',code],capture_output=True,text=True);(F/('INSTALL_DRY_RUN_'+label+'.log')).write_text(dry.stdout+'\n'+dry.stderr);assert dry.returncode==0,dry.stderr
assert json.loads(report.read_text()).get('install',[])==[]
paths={n:m.__file__for n,m in [('numpy',np),('numpy.random.mtrand',mt),('pandas',pd),('cv2',cv2)]}
if label!='native_main':assert all(Path(p).resolve().is_relative_to(Path(sys.prefix).resolve())for p in paths.values())
out=dict(status='PASS',dependency_profile='p48-sdk-v09',label=label,submission_zip_sha256=build['submission_zip_sha256'],payload_files_sha256=build['payload_files_sha256'],python=sys.version,executable=sys.executable,distribution_versions={n:md.version(n)for n in ['numpy','pandas','opencv-contrib-python']},critical_module_paths=paths,numeric_random_pandas_cv_operations='PASS',sdk_launcher_and_stats_import='PASS',controller_factory_import='PASS',all_payload_hashes_match=True,team_number=615,five_independent_native_constructors='PASS',gurobi_import_blocked_and_not_loaded=True,installation_dry_run=dict(status='PASS',planned_installations=[]),SDK_frames=0,native_game_rounds=0,scope='New isolated pinned numeric environments for numpy1/2, current frozen SDK numerical stack for native_main; SDK124 code and auxiliary dependencies read-only from current restored match installation. No package installed or replaced in match environment. Not an official image or website test.',official_container_verified=False)
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['status','label','distribution_versions','submission_zip_sha256']}))
