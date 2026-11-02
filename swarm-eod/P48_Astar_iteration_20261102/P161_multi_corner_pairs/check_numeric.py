"""Real multi-corner function/original Dijkstra, explicit authored adapters."""
from pathlib import Path
import ast,copy,hashlib,heapq,importlib.util,json,math,sys,types
import numpy as np
F=Path(__file__).resolve().parent;S=F/'candidate_project/src/swarm_rescue/solutions';assert not(F/'NUMERIC_FIRST.json').exists()
for name in ['swarm_rescue','swarm_rescue.solutions']:
 m=types.ModuleType(name);m.__path__=[];sys.modules[name]=m
def register(name,**attrs):m=types.ModuleType(name);m.__dict__.update(attrs);sys.modules[name]=m
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
tree=ast.parse((S/'team_coverage.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='path_costs')
env={'np':np,'math':math,'heapq':heapq};exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(fn)],type_ignores=[])),'original_path_costs','exec'),env)
register('swarm_rescue.solutions.geometry_route_view',GeometryPlanningMemory=lambda m:m)
register('swarm_rescue.solutions.team_coverage',observed_wall_values=lambda m,radius,return_solids:(m.values.copy(),m.solids.copy()),path_costs=env['path_costs'])
register('swarm_rescue.solutions.farthest_wall_cover',owner_travel_budget=lambda b,k:math.inf if b is None else b.get(k,0.)if isinstance(b,dict)else b)
c=load('swarm_rescue.solutions.corner_cluster',S/'corner_cluster.py')
class Memory:
 CELL=16;FINE=2;width=800;height=800;shape=(50,50);step=100
 def __init__(self):
  self.free=np.ones(self.shape,bool);self.solids=np.zeros(self.shape,bool);self._blocked=np.zeros(self.shape,bool)
  self._blocked[:2,:]=True;self._blocked[-2:,:]=True;self._blocked[:,:2]=True;self._blocked[:,-2:]=True
  self.hits=np.zeros((400,400),np.uint8);self.hits[1,1:140]=3;self.hits[1:140,1]=3;self.hits[-2,-140:-1]=3;self.hits[-140:-1,-2]=3
  self.values=np.zeros(self.shape,np.float32);self.values[3:13,3:13]=1.;self.values[37:47,37:47]=1.
  self.corner_policy_state=dict(initial_total=10,confirmed=[],reserved={},previous_suffix={},regions=[])
 def blocked(self):return self._blocked.copy()
 def world_to_cell(self,p):return(int(np.clip((400-p[1])//16,0,49)),int(np.clip((p[0]+400)//16,0,49)))
 def cell_to_world(self,rc):return np.array([(rc[1]+.5)*16-400,400-(rc[0]+.5)*16])
agents={k:(np.array([-200.+k*80.,0.]),2)for k in range(5)}
pts=[np.array([float(x),float(y)])for x,y in [(-360,360),(-104,344),(104,344),(344,344),(-344,104),(104,104),(344,104),(-344,-344),(-104,-344),(344,-344)]]
base={k:pts[2*k:2*k+2]for k in agents};checks=[];cases=[]
def check(name,passed):checks.append(dict(name=name,passed=bool(passed)));assert passed,name
def run(name,m,aa=None,bb=None,dd=None,**kwargs):
 before={k:hashlib.sha256(getattr(m,k).tobytes()).hexdigest()for k in ['free','hits','values','solids','_blocked']}
 rr=c.corner_cluster_layout(m,agents if aa is None else aa,[]if dd is None else dd,72.,base if bb is None else bb,travel_budget=kwargs.pop('travel_budget',10000.),**kwargs)
 a=dict(m.multi_corner_diagnostics);cases.append(dict(name=name,audit=a));check(name+'_maps_unchanged',before=={k:hashlib.sha256(getattr(m,k).tobytes()).hexdigest()for k in before})
 if a['accepted']:
  points=[p for ps in rr.values()for p in ps];committed=[np.asarray(p)for p in m.corner_policy_state['confirmed']]+[np.asarray(p)for p in m.corner_policy_state['reserved'].values()]
  check(name+'_atleast2',len(a['regions'])>=2)
  check(name+'_each2or3',all(2<=sum(np.linalg.norm(p-np.asarray(r['anchor']))<=72+1e-8 for p in committed+points)<=3 for r in a['regions']))
  check(name+'_distinct',all(np.linalg.norm(np.asarray(r['anchor'])-np.asarray(s['anchor']))>=195.36-1e-8 for i,r in enumerate(a['regions'])for s in a['regions'][i+1:]))
  check(name+'_floor70',a['coverage_ratio']>=.7-1e-8)
  check(name+'_safe_spacing',all(np.linalg.norm(p-q)>=51.36-1e-8 for i,p in enumerate(points)for q in points[i+1:]))
  json.dumps(a)
 return rr,a
m=Memory();result,witness=run('two_opposite_measured_corners',m)
check('positive_multi_region_witness',witness['accepted']);check('all_owner_counts_preserved',all(len(result[k])==2 for k in agents))
m.corner_policy_state.update(previous_suffix=result,regions=witness['regions'])
carried,a=run('full_suffix_carry',m);check('carry_actually_used',a.get('carried_suffix')and all(np.array_equal(p,q)for k in result for p,q in zip(result[k],carried[k])))
# A reserved or rejected placement is not a newly discovered physical wall.
m=Memory();rr,cc=np.indices(m.shape);xx=(cc+.5)*16-400;yy=400-(rr+.5)*16
physical=m.free&~m.blocked();regions=c._regions(m,physical,xx,yy,72.,[]);anchor=np.asarray(regions[0]['anchor'])
legal=physical&((xx-anchor[0])**2+(yy-anchor[1])**2>=51.36**2)
check('excluded_anchor_not_placement_legal',not legal[m.world_to_cell(anchor)])
retained=c._regions(m,physical,xx,yy,72.,[c.descriptor(regions[0],2)]if hasattr(c,'descriptor')else[dict(pivot=regions[0]['pivot'],anchor=anchor.tolist(),kind=regions[0]['kind'],radius=72.,planned_count=2)])
check('point_exclusion_does_not_erase_geometric_region',any(np.linalg.norm(np.asarray(r['anchor'])-anchor)<1e-8 for r in retained))
# Prefix acknowledged: all 5 first sites reserved, exact 5 original tails.
m=Memory();reserved={k:result[k][0]for k in result};suffix={k:result[k][1:]for k in result};m.corner_policy_state.update(reserved=reserved,previous_suffix=suffix,regions=witness['regions'])
rr,a=run('reserved_prefix_tail',m,aa={k:(reserved[k],1)for k in reserved},bb=suffix,dd=list(reserved.values()))
check('reserved_tail_kept',a.get('carried_suffix'))
m=Memory();m.hits[-140:,:]=0;m.hits[:,-140:]=0;_,a=run('single_measured_corner',m);check('one_corner_not_multi',not a['accepted'])
m=Memory();m.hits[:]=0;_,a=run('no_hits',m);check('no_invented_corners',not a['accepted'])
m=Memory();m.free[:]=False;_,a=run('no_known_free',m);check('unknown_not_walkable',not a['accepted'])
m=Memory();_,a=run('all_forbidden',m,forbidden_mask=np.ones(m.shape,bool));check('forbidden_not_ignored',not a['accepted'])
m=Memory();_,a=run('zero_route_budget',m,travel_budget=0.);check('no_unbudgeted_bundle',not a['accepted'])
m=Memory();old=c.OPTIONAL_SECONDS;c.OPTIONAL_SECONDS=0
try:_,a=run('zero_optional_clock',m)
finally:c.OPTIONAL_SECONDS=old
check('bounded_fallback',not a['accepted'])
mission=load('swarm_rescue.solutions.corner_mission',S/'corner_mission.py')
class Parent:
 PLAN_FRESH_STEPS=240
 def __init__(self):
  self.fleet_plan=(100,0,{0:(2,[np.array([-360.,360.]),np.array([320.,-320.])])});self.blast_radius=72.;self.placement_goal=np.array([-360.,360.]);self.identifier=0;self.q=2;self.calls=0;self.initial_inventory=2;self.team_size=5;self.memory=Memory()
 def carried_bombs_count(self):return self.q
 def _should_defer_commitment(self,*args):self.calls+=1;return True
class D(mission.CornerMissionMixin,Parent):pass
d=D();d.corner_context=dict(epoch=100,leader=0,signature=mission.plan_signature(d.fleet_plan),regions=[dict(pivot=[-400.,400.],anchor=[-360.,360.],radius=72.,kind='outer',planned_count=2),dict(pivot=[400.,-400.],anchor=[360.,-360.],radius=72.,kind='outer',planned_count=2)],coverage_ratio=.75,initial_total=10)
check('two_corner_context_valid',d._valid_corner_context(d.corner_context,100));check('matching_group_target_honoured',not d._should_defer_commitment(5,100,20,10,4,100))
d.corner_context['regions'][1]['anchor']=[-350.,350.];check('duplicate_corner_context_rejected',not d._valid_corner_context(d.corner_context,100))
d.corner_context['regions'][1]['anchor']=[360.,-360.];d.corner_context['regions'][0]['planned_count']=4;check('four_in_one_rejected',not d._valid_corner_context(d.corner_context,100))
d.corner_context['regions'][0]['planned_count']=2;d.corner_context['coverage_ratio']=.69;check('below70_context_rejected',not d._valid_corner_context(d.corner_context,100))
d.corner_context['coverage_ratio']=.75;d.corner_context['signature']='wrong';check('wrong_plan_reverts_original',d._should_defer_commitment(5,100,20,10,4,100))
out=dict(status='PASS_MULTI_CORNER_NUMERIC_PROTOCOL',checks=checks,cases=cases,source_sha256={n:hashlib.sha256((S/n).read_bytes()).hexdigest()for n in ['corner_cluster.py','corner_mission.py']},SDK_frames=0,native_rounds=0,limitations='Authored arrays with explicit geometry/value adapters and original Dijkstra; no physical group placement or official score claim.')
(F/'NUMERIC_FIRST.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=out['status'],checks=len(checks),positive=witness)))
