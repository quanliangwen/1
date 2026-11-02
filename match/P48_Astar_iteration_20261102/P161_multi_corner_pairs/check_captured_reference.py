"""Actual captured own coverage model, explicit nominal owner adapter.
Only a geometry/coverage construction witness, never an actual route execution.
Historical data are not loaded by production controllers.
"""
from pathlib import Path
import ast,copy,hashlib,heapq,importlib.util,json,math,sys,types
import cv2,numpy as np
F=Path(__file__).resolve().parent;S=F/'candidate_project/src/swarm_rescue/solutions';dest=F/'CAPTURED_REFERENCE_FIRST.json';assert not dest.exists()
snapshot=json.loads((F/'captured_author_model_reference.json').read_text())['snapshots'][0]
for name in ['swarm_rescue','swarm_rescue.solutions']:
 m=types.ModuleType(name);m.__path__=[];sys.modules[name]=m
def register(name,**attrs):m=types.ModuleType(name);m.__dict__.update(attrs);sys.modules[name]=m
t=ast.parse((S/'team_coverage.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef)and n.name=='path_costs');env={'np':np,'math':math,'heapq':heapq}
exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(fn)],type_ignores=[])),'actual_Dijkstra','exec'),env)
register('swarm_rescue.solutions.geometry_route_view',GeometryPlanningMemory=lambda m:m)
register('swarm_rescue.solutions.team_coverage',observed_wall_values=lambda m,radius,return_solids:(m.values.copy(),m.solids.copy()),path_costs=env['path_costs'])
register('swarm_rescue.solutions.farthest_wall_cover',owner_travel_budget=lambda b,k:float(b))
spec=importlib.util.spec_from_file_location('swarm_rescue.solutions.corner_cluster',S/'corner_cluster.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class M:
 CELL=float(snapshot['cell']);FINE=2;step=int(snapshot['step']);identifier=0
 def __init__(self):
  self.values=np.asarray(snapshot['values'],np.float32);self.shape=self.values.shape;self.solids=np.zeros(self.shape,bool);self.free=np.asarray(snapshot['walkable'],bool)
  self.xx=np.asarray(snapshot['xx'],float);self.yy=np.asarray(snapshot['yy'],float);self.width=2*(self.CELL/2-self.xx[0,0]);self.height=2*(self.yy[0,0]+self.CELL/2)
  self.corner_policy_state=dict(initial_total=10,confirmed=[],reserved={},previous_suffix={},regions=[])
 def blocked(self):return np.zeros(self.shape,bool)
 def world_to_cell(self,p):return(int(np.clip((self.height/2-p[1])//self.CELL,0,self.shape[0]-1)),int(np.clip((p[0]+self.width/2)//self.CELL,0,self.shape[1]-1)))
 def cell_to_world(self,p):return np.array([self.xx[p],self.yy[p]])
def captured_regions(memory,walkable,xx,yy,radius,retained):
 out=[]
 for old in snapshot['corners']:
  anchor=np.asarray(old['anchor']);physical=walkable&((xx-anchor[0])**2+(yy-anchor[1])**2<=radius**2+1e-8)
  _,labels=cv2.connectedComponents(physical.astype(np.uint8),connectivity=8);component=int(labels[memory.world_to_cell(anchor)])
  if component:out.append(dict(pivot=old['pivot'],anchor=old['anchor'],radius=float(radius),kind='inner',mask=physical&(labels==component)))
 return out
c._regions=captured_regions
m=M();points=[np.asarray(p,float)for p in snapshot['baseline_points']];base={k:points[2*k:2*k+2]for k in range(5)}
agents={k:(points[2*k],2)for k in range(5)}
result=c.corner_cluster_layout(m,agents,[],snapshot['radius'],base,travel_budget=10000.,forbidden_mask=~np.asarray(snapshot['allowed'],bool))
audit=m.multi_corner_diagnostics
out=dict(status='COMPLETE_CAPTURED_COVERAGE_REFERENCE',audit=audit,nominal_points={k:[p.tolist()for p in ps]for k,ps in result.items()},parent_snapshot_owner=snapshot['owner'],parent_snapshot_step=snapshot['step'],parent_snapshot_sha256=hashlib.sha256((F/'captured_author_model_reference.json').read_bytes()).hexdigest(),candidate_source_sha256=hashlib.sha256((S/'corner_cluster.py').read_bytes()).hexdigest(),SDK_frames_added=0,native_rounds=0,limitations=['Observed wall/allowed/walkable arrays and pivots are actual retained author controller data, never tournament true map.','Original ownership/poses were not captured; nominal owners start at assigned baseline points, budget10000. This is NOT actual owner route or execution evidence.','R-sized regions are recomputed on the captured geometric graph, not blindly treated as former2R regions.','Historical snapshot loaded only by this external diagnostic; production source never reads it.'])
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=out['status'],audit=audit)))
