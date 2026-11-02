"""Actual candidate on authored arrays and original Dijkstra, zero SDK frames."""
from pathlib import Path
import ast,copy,hashlib,heapq,importlib.util,json,math,sys,types
import numpy as np
F=Path(__file__).resolve().parent;S=F/'candidate_project/src/swarm_rescue/solutions'
assert not(F/'NUMERIC_V2_FIRST.json').exists()
for n in ['swarm_rescue','swarm_rescue.solutions']:
 m=types.ModuleType(n);m.__path__=[];sys.modules[n]=m
def register(n,**attrs):
 m=types.ModuleType(n);m.__dict__.update(attrs);sys.modules[n]=m
def load(n,p):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);sys.modules[n]=m;spec.loader.exec_module(m);return m
t=ast.parse((S/'team_coverage.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef)and n.name=='path_costs')
g={'np':np,'math':math,'heapq':heapq};exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(fn)],type_ignores=[])),'actual_path_costs','exec'),g)
register('swarm_rescue.solutions.geometry_route_view',GeometryPlanningMemory=lambda m:m)
register('swarm_rescue.solutions.team_coverage',observed_wall_values=lambda m,radius,return_solids:(m.values.copy(),m.solids.copy()),path_costs=g['path_costs'])
register('swarm_rescue.solutions.farthest_wall_cover',owner_travel_budget=lambda b,k:math.inf if b is None else b.get(k,0.)if isinstance(b,dict)else b)
c=load('swarm_rescue.solutions.corner_cluster',S/'corner_cluster.py')
class Memory:
 CELL=16;FINE=2;width=800;height=800;shape=(50,50);step=100
 def __init__(self):
  self.free=np.ones(self.shape,bool);self.solids=np.zeros(self.shape,bool);self._blocked=np.zeros(self.shape,bool)
  self._blocked[25,25:44]=True;self._blocked[25:44,25]=True
  self.hits=np.zeros((400,400),np.uint8)
  self.hits[200:204,200:352]=3;self.hits[200:352,200:204]=3
  self.values=np.zeros(self.shape,np.float32);self.values[15:38,15:38]=1.
  self.corner_policy_state=dict(initial_total=10,confirmed=[],reserved={},previous_suffix={})
 def blocked(self):return self._blocked.copy()
 def world_to_cell(self,p):return(int(np.clip((self.height/2-p[1])//self.CELL,0,49)),int(np.clip((p[0]+self.width/2)//self.CELL,0,49)))
 def cell_to_world(self,rc):return np.array([(rc[1]+.5)*self.CELL-self.width/2,self.height/2-(rc[0]+.5)*self.CELL])
agents={k:(np.array([-200.+k*30.,240.]),2)for k in range(5)}
points=[np.array([float(x),float(y)])for x,y in [(-360,360),(-104,344),(104,344),(344,344),(-344,104),(104,104),(344,104),(-344,-344),(-104,-344),(344,-344)]]
base={k:points[2*k:2*k+2]for k in agents}
checks=[];cases=[]
def check(n,b):checks.append(dict(name=n,passed=bool(b)));assert b,n
def run(n,m,aa=None,bb=None,dd=None,**kwargs):
 before={k:hashlib.sha256(getattr(m,k).tobytes()).hexdigest()for k in ['free','hits','values','solids','_blocked']}
 result=c.corner_cluster_layout(m,agents if aa is None else aa,[]if dd is None else dd,72.,base if bb is None else bb,travel_budget=10000.,**kwargs)
 a=dict(m.corner_cluster_diagnostics);cases.append(dict(name=n,audit=a))
 check(n+'_map_unchanged',before=={k:hashlib.sha256(getattr(m,k).tobytes()).hexdigest()for k in before})
 if a['accepted']:
  check(n+'_fixed6',a['fixed_target']==6)
  check(n+'_floor',a['coverage_ratio']>=.9-1e-8)
  check(n+'_initial10',a['initial_total']==10)
 return result,a
m=Memory();rr,cc=np.indices(m.shape);xx=(cc+.5)*16-400;yy=400-(rr+.5)*16
corners=c._corners(m,m.free&~m.blocked(),xx,yy,72)
check('internal_L_detected',bool(corners))
result,witness=run('dense_internal',m)
check('actual_candidate6_positive',witness['accepted']and witness['clustered']>=6)
check('fixed_count_preserved',all(len(result[k])==2 for k in agents))
m.corner_policy_state['previous_suffix']=result
carried,a=run('carry_same_suffix',m)
check('suffix_carried_after_replan',a.get('carry_previous_suffix')and all(np.array_equal(x,y)for k in result for x,y in zip(result[k],carried[k])))
m=Memory();m.corner_policy_state['initial_total']=10
_,a=run('late2_no_prior_credit',m,aa={0:(np.array([-200.,240.]),2)},bb={0:base[0]})
check('late2_never_shrinks_to2',not a['accepted']and a['target_total']==6)
m=Memory();m.corner_policy_state={};_,a=run('no_initial_certificate',m)
check('missing_certificate_abstains',not a['accepted'])
m=Memory();m.hits[:]=0;_,a=run('no_hit',m)
check('unknown_not_inner_corner',not a['accepted'])
m=Memory();m.hits[:]=0;m.hits[200:204,50:350]=3;_,a=run('single_wall',m)
check('single_wall_not_inner_corner',not a['accepted'])
m=Memory();m.values[:]=1.;_,a=run('uniform',m)
check('uniform_floor_not_relaxed',not a['accepted']or a['coverage_ratio']>=.9)
m=Memory();m.free[:]=False;m.free[:8,:8]=True;_,a=run('unreachable_inner',m)
check('no_unknown_route',not a['accepted'])
m=Memory();_,a=run('forbidden_inner',m,forbidden_mask=np.ones(m.shape,bool))
check('forbidden_respected',not a['accepted'])
m=Memory();old=c.OPTIONAL_SECONDS;c.OPTIONAL_SECONDS=0
try:_,a=run('zero_time',m)
finally:c.OPTIONAL_SECONDS=old
check('bounded_fallback',not a['accepted'])
mission=load('swarm_rescue.solutions.corner_mission',S/'corner_mission.py')
class Parent:
 PLAN_FRESH_STEPS=240
 def __init__(self):
  self.fleet_plan=(100,0,{0:(2,[np.array([8.,8.]),np.array([80.,80.])])});self.blast_radius=72.;self.placement_goal=np.array([8.,8.]);self.identifier=0;self.q=2;self.calls=0;self.initial_inventory=2;self.team_size=5
 def carried_bombs_count(self):return self.q
 def _should_defer_commitment(self,*a):self.calls+=1;return True
class D(mission.CornerMissionMixin,Parent):pass
d=D();d.corner_context=dict(epoch=100,leader=0,signature=mission.plan_signature(d.fleet_plan),pivot=[0.,0.],anchor=[8.,8.],radius=144.,coverage_ratio=.91,initial_total=10,target_total=6)
check('matching_context_honored',not d._should_defer_commitment(5,100,20,10,4,100))
d.corner_context['target_total']=2;check('wrong_initial_quota_rejected',not d._valid_corner_context(d.corner_context,100))
d.corner_context['target_total']=6;d.corner_context['signature']='wrong';check('wrong_plan_rejected',d._should_defer_commitment(5,100,20,10,4,100))
result=dict(status='PASS_FIXED_INITIAL_QUOTA_INNER_CORNER_NUMERIC',checks=checks,cases=cases,SDK_frames=0,native_rounds=0,limitations='Actual candidate plus actual Dijkstra; authored geometry/value adapters, not physical SDK concentration or game score.')
(F/'NUMERIC_V2_FIRST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],checks=len(checks),positive=witness)))
