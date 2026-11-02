"""Build one evidence-only replay of P142's preserved failure, not a rescue run."""
from pathlib import Path
import ast
import hashlib
import json

F=Path(__file__).resolve().parent
P=F.parent/'P142_profile_and_task_chain'
source=(P/'check_sdk_astar_profile.py').read_text(encoding='utf-8-sig')
source=source.replace('projection_events=[]','drive_evidence=[]\nprojection_events=[]')
anchor='class MyDroneEval(Original):\n'
assert source.count(anchor)==1
hook='''class MyDroneEval(Original):
 def _drive(self,distances,angles,semantic=()):
  step=int(self.elapsed_timestep)
  if not (332<=step<=346 and int(self.identifier or 0) in (1,4)):
   return super()._drive(distances,angles,semantic)
  from swarm_rescue.solutions.fast_exploration import holonomic_drive
  previous=sys.gettrace()
  assert previous is None,'Do not override an existing debugger/observer'
  def trace(frame,event,arg):
   if frame.f_code is not holonomic_drive.__code__:return None
   if event=='return':
    v=frame.f_locals
    fields={}
    for key in ['position','heading','target','delta','direction','velocity','target_distance','corridor','speed','desired_velocity','acceleration','projection','along','sideways','in_tube','finite','zone','distances','angles','close']:
     if key not in v:continue
     value=v[key]
     fields[key]=value.tolist() if isinstance(value,np.ndarray) else float(value) if isinstance(value,np.generic) else value
    drive_evidence.append(dict(owner=int(self.identifier or 0),step=step,locals=fields,
     semantic=[dict(kind=getattr(getattr(o,'entity_type',None),'name',''),distance=float(o.distance),angle=float(o.angle))for o in semantic or ()],
     returning_command=dict(arg),source='Actual holonomic_drive return locals, using its existing public sensor arguments; no extra getter call'))
   return trace
  sys.settrace(trace)
  try:return super()._drive(distances,angles,semantic)
  finally:sys.settrace(previous)
'''
source=source.replace(anchor,hook)
source=source.replace(' out=dict(profile_enabled=', ' out=dict(drive_evidence=drive_evidence,profile_enabled=')
source=source.replace('P142 frozen A* own-task-chain and optional read-only cProfile; authored physics only.',
                      'P143 evidence-only drive-locals replay of preserved P142 failure; no controller change.')
ast.parse(source)
dest=F/'check_sdk_drive_evidence.py'
assert not dest.exists()
dest.write_bytes(source.encode())
(F/'WORKSPACE_READY.json').write_bytes((P/'WORKSPACE_READY.json').read_bytes())
pre=dict(status='FROZEN_BEFORE_EVIDENCE_REPLAY',code_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
         parent_failure_sha256=hashlib.sha256((P/'BASELINE_FIRST.json').read_bytes()).hexdigest(),
         maximum_arms=1,maximum_frames=800,case='cross_sdk',authored_seed=615,wall_rate=.05,
         observe_owners=[1,4],observe_steps=[332,346],
         purpose='Add missing actual public sensing/motor provenance to preserved failed encounter; not retry for performance or qualification.',
         mandatory_identity=['All 779 existing frame rows/health/commands/map hashes same','Same submission hashes','Same failure at344 and final health','No extra sensor getter call or control/source/SDK change'],
         automatic_native=False,automatic_five=False,automatic_retry=False,native_rounds=0)
(F/'PREDECLARATION_FIRST.json').write_bytes((json.dumps(pre,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=pre['status'],sha256=pre['code_sha256'])))
