"""Actual cluster code/original Dijkstra on authored arrays; no SDK import."""
from pathlib import Path
import ast,copy,hashlib,heapq,importlib.util,json,math,sys,types
import numpy as np
F=Path(__file__).resolve().parent
assert not(F/'CORNER_CONTRACT_FIRST.json').exists()
for n in['swarm_rescue','swarm_rescue.solutions']:
    m=types.ModuleType(n);m.__path__=[];sys.modules[n]=m
def register(n,**attrs):
    m=types.ModuleType(n);m.__dict__.update(attrs);sys.modules[n]=m
def load(n,p):
    spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);sys.modules[n]=m;spec.loader.exec_module(m);return m
original=F/'team_coverage_reference.py'
t=ast.parse(original.read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef)and n.name=='path_costs')
g={'np':np,'math':math,'heapq':heapq};exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(fn)],type_ignores=[])),str(original),'exec'),g)
register('swarm_rescue.solutions.geometry_route_view',GeometryPlanningMemory=lambda m:m)
register('swarm_rescue.solutions.team_coverage',observed_wall_values=lambda m,radius,return_solids:(m.values.copy(),m.solids.copy()),path_costs=g['path_costs'])
register('swarm_rescue.solutions.farthest_wall_cover',owner_travel_budget=lambda b,k:math.inf if b is None else b.get(k,0.)if isinstance(b,dict)else b)
c=load('swarm_rescue.solutions.corner_cluster',F/'corner_cluster.py')
class Memory:
    CELL=16;FINE=2;width=800;height=800;shape=(50,50);hit_shape=(400,400);step=100
    def __init__(self,dense=True):
        self.free=np.ones(self.shape,bool);self._blocked=np.zeros(self.shape,bool);self._blocked[:2,:]=True;self._blocked[-2:,:]=True;self._blocked[:,:2]=True;self._blocked[:,-2:]=True
        self.solids=np.zeros(self.shape,bool);self.hits=np.zeros(self.hit_shape,np.uint8)
        self.hits[1,1:110]=3;self.hits[1:110,1]=3
        self.values=np.zeros(self.shape,np.float32)
        if dense:self.values[3:13,3:13]=1.
        else:self.values[:]=1.
    def blocked(self):return self._blocked.copy()
    def world_to_cell(self,p):return(int(np.clip((self.height/2-p[1])//self.CELL,0,49)),int(np.clip((p[0]+self.width/2)//self.CELL,0,49)))
    def cell_to_world(self,rc):return np.array([(rc[1]+.5)*self.CELL-self.width/2,self.height/2-(rc[0]+.5)*self.CELL])
agents={0:(np.array([-200.,240.]),2),1:(np.array([-160.,240.]),2),2:(np.array([-200.,160.]),2),3:(np.array([160.,-160.]),2),4:(np.array([240.,-160.]),2)}
base={0:[np.array([-360.,360.]),np.array([-104.,344.])],1:[np.array([104.,344.]),np.array([344.,344.])],2:[np.array([-344.,104.]),np.array([104.,104.])],3:[np.array([344.,104.]),np.array([-344.,-344.])],4:[np.array([-104.,-344.]),np.array([344.,-344.])]}
checks=[];cases=[]
def check(name,ok):checks.append(dict(name=name,passed=bool(ok)));assert ok,name
def run(name,m,**kw):
    before={n:hashlib.sha256(getattr(m,n).tobytes()).hexdigest()for n in['free','hits','values','solids','_blocked']}
    result=c.corner_cluster_layout(m,agents,[],72.,base,travel_budget=10000.,**kw)
    a=dict(m.corner_cluster_diagnostics);cases.append(dict(name=name,audit=a))
    check(name+'_counts_preserved',all(len(result[k])==2 for k in agents))
    check(name+'_map_arrays_unchanged',before=={n:hashlib.sha256(getattr(m,n).tobytes()).hexdigest()for n in before})
    if a['accepted']:
        check(name+'_coverage_floor',a['coverage_ratio']>=.9-1e-7)
        check(name+'_majority',a['clustered']>=6)
        points=[p for ps in result.values()for p in ps]
        check(name+'_all_spacing',all(np.linalg.norm(p-q)>=51.36-1e-7 for i,p in enumerate(points)for q in points[i+1:]))
    return result,a
result,witness=run('corner_dense',Memory())
check('actual_majority_proposal_witness',witness['accepted'])
result,a=run('uniform_distributed',Memory(False))
check('uniform_does_not_sacrifice_coverage',not a['accepted']or a['coverage_ratio']>=.9)
m=Memory();m.hits[:]=0;result,a=run('no_measured_corner',m)
check('no_unobserved_corner_fabricated',not a['accepted']and a['reason']=='no_two_measured_corner_surfaces')
m=Memory();mask=np.zeros(m.shape,bool);mask[:20,:20]=True;result,a=run('forbidden_corner',m,forbidden_mask=mask)
check('forbidden_corner_respected',not a['accepted'])
m=Memory();m.free[:]=False;m.free[25:,25:]=True;result,a=run('unreachable_corner',m)
check('no_unknown_or_disconnected_cluster',not a['accepted'])
m=Memory();old=c.OPTIONAL_SECONDS;c.OPTIONAL_SECONDS=0.
try:result,a=run('expired_optional_budget',m)
finally:c.OPTIONAL_SECONDS=old
check('timeout_keeps_original',not a['accepted'])
m=Memory();m.corner_cluster_calls=12;result,a=run('optional_calls_bounded',m)
check('optional_call_limit',not a['accepted']and a['reason']=='optional_call_limit')
mission=load('swarm_rescue.solutions.corner_mission',F/'corner_mission.py')
class Parent:
    PLAN_FRESH_STEPS=240
    def __init__(self):self.fleet_plan=(100,0,{0:(2,[np.array([8.,8.]),np.array([80.,80.])])});self.blast_radius=72.;self.placement_goal=np.array([8.,8.]);self.identifier=0;self.q=2;self.calls=0
    def carried_bombs_count(self):return self.q
    def _should_defer_commitment(self,*a):self.calls+=1;return True
class D(mission.CornerMissionMixin,Parent):pass
d=D();d.corner_context=dict(epoch=100,leader=0,signature=mission.plan_signature(d.fleet_plan),anchor=[8.,8.],radius=144.,coverage_ratio=.91)
check('matching_corner_joint_objective_honoured',not d._should_defer_commitment(5,100,20,10,4,100)and d.calls==0)
d.placement_goal=np.array([300.,300.]);check('unrelated_target_original_defer',d._should_defer_commitment(5,100,20,10,4,100)and d.calls==1)
d.placement_goal=np.array([8.,8.]);d.corner_context['signature']='wrong';check('wrong_plan_context_rejected',d._should_defer_commitment(5,100,20,10,4,100)and d.calls==2)
d.corner_context['signature']=mission.plan_signature(d.fleet_plan);d.corner_context['coverage_ratio']=.8
check('coverage_floor_in_message_required',not d._valid_corner_context(d.corner_context,100))
d.corner_context['coverage_ratio']=.91;check('expired_context_rejected',not d._valid_corner_context(d.corner_context,340))
out=dict(status='PASS_CORNER_NUMERIC_AND_OBJECTIVE_MESSAGE_CONTRACTS',checks=checks,cases=cases,
         source_sha256={n:hashlib.sha256((F/n).read_bytes()).hexdigest()for n in['corner_cluster.py','corner_mission.py']},
         SDK_imports=0,SDK_frames=0,native_rounds=0,limitations=['Authored arrays with explicit geometry/value adapters and actual original Dijkstra; not physical game score or official map evidence.'])
(F/'CORNER_CONTRACT_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=out['status'],checks=len(checks),accepted_case=witness)))
