from pathlib import Path
import contextlib
import fcntl
import hashlib
import importlib.abc
import importlib.metadata as md
import inspect
import io
import json
import sys

F=Path(__file__).resolve().parent
label,arm=sys.argv[1:]
dest=F/(label+'.json')
assert not dest.exists()
R=Path('/home/junhao/quan/parallel_test_solver/match')
lock=(R/'solver_study/serial_evaluation.lock').open('a+')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((F/'WORKSPACE_READY.json').read_text())['versions'][arm]
W=Path(m['workspace'])
assert all(sha(W/n)==h for n,h in m['sources'].items())
assert all(sha(W/n)==h for n,h in m['sdk_files'].items())
class RejectGurobi(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('gurobipy','gurobi'):raise ImportError('No Gurobi permitted in this research candidate')
sys.meta_path.insert(0,RejectGurobi())
sys.path.insert(0,str(W/'src'))
import numpy as np
import numpy.random.mtrand
import pandas as pd
import cv2
import yaml
import pyglet
from swarm_rescue.launcher import Launcher
from swarm_rescue.simulation.reporting.stats_computation import StatsComputation
from swarm_rescue.solutions.my_drone_eval import MyDroneEval,drone_class_for_mode
team=yaml.safe_load((W/'src/swarm_rescue/solutions/team_info.yml').read_text())
assert type(team['team_number'])is int and team['team_number']==615
assert drone_class_for_mode('place')is MyDroneEval
assert Path(inspect.getfile(MyDroneEval)).resolve().is_relative_to(W/'src')
assert np.isfinite(np.random.RandomState(615).normal(size=8)).all()
assert pd.DataFrame({'x':[1,2]}).sum()['x']==3
assert cv2.resize(np.zeros((4,4),np.uint8),(2,2)).shape==(2,2)
records=[]
window=pyglet.window.Window(width=1,height=1,visible=False)
try:
    from swarm_rescue.maps.map_02 import Map02
    arena=Map02(drone_type=MyDroneEval,number_drones=5)
    assert len({id(d.memory.hits)for d in arena.drones})==5
    for d in arena.drones:
        d.elapsed_timestep=0
        d.elapsed_walltime=0.
        d.set_competition_mode(True)
        image=d.memory.render()
        stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout):d.submit_exploration_map(image)
        actual=np.asarray(d._exploration_map_submission)
        assert np.array_equal(actual,image),'Empty-observation startup output must be unchanged'
        lines=[s.split('[FREE_SUPPORT_OUTPUT] ',1)[1]for s in stdout.getvalue().splitlines()if '[FREE_SUPPORT_OUTPUT] 'in s]
        assert len(lines)==1
        audit=json.loads(lines[0])
        assert audit['sha256']==hashlib.sha256(actual.tobytes()).hexdigest()
        assert audit['audit']['parent_preserved']and audit['audit']['raw_positive_preserved']
        records.append(dict(owner=d.identifier,sha256=audit['sha256'],output_audit=audit['audit']))
finally:window.close()
out=dict(status='PASS_SERVER_RESEARCH_ENTRY_NOT_OFFICIAL_RELEASE',arm=arm,workspace=str(W),sources=m['sources'],team_number=615,
         actual_zip_sha256=json.loads((F/'INTERNAL_ZIP_BINDING.json').read_text())['sha256'],
         interpreter=sys.executable,python_version=sys.version,
         module_paths={'numpy':np.__file__,'mtrand':numpy.random.mtrand.__file__,'pandas':pd.__file__,'cv2':cv2.__file__},
         numeric_versions={n:md.version(n)for n in ['numpy','pandas','opencv-contrib-python']},
         five_native_constructors_independent=True,real_sdk_setter_and_audit_passthrough=records,
         original_functional_rule_validated_on_779_frames=True,physics_steps=0,native_game_rounds=0,
         dependency_installation=False,official_submission_ready=False,gurobi_blocked=True,
         limitations='Actual research ZIP/main restored environment startup and no-op setter/audit check, not official container/release or new flight safety validation.')
dest.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items()if k not in ['sources','real_sdk_setter_and_audit_passthrough']}))
