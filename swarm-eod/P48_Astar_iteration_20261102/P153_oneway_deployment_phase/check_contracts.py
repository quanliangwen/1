"""Protocol/forwarding fixtures, original route and completion bodies via AST. No SDK."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,sys,types
import numpy as np
F=Path(__file__).resolve().parent
assert not(F/'CONTRACT_FIRST.json').exists()
BASE=Path('E:/codex/P48_astar_five_20261102/versions/P48_ASTAR/source')
def original_function(name,cls,method):
    p=BASE/name;t=ast.parse(p.read_text(encoding='utf-8-sig'))
    c=next(x for x in t.body if isinstance(x,ast.ClassDef)and x.name==cls)
    f=copy.deepcopy(next(x for x in c.body if isinstance(x,ast.FunctionDef)and x.name==method));f.decorator_list=[]
    g={'np':np};exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),str(p),'exec'),g);return g[method]
for n in['swarm_rescue','swarm_rescue.solutions']:
    m=types.ModuleType(n);m.__path__=[];sys.modules[n]=m
g=types.ModuleType('swarm_rescue.solutions.greedy_mapping')
g.GreedyMappingDrone=type('GreedyMappingDrone',(),dict(_plan_route=original_function('greedy_mapping.py','GreedyMappingDrone','_plan_route')))
sys.modules[g.__name__]=g
spec=importlib.util.spec_from_file_location('phase_rule',F/'deployment_phase.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
checks=[]
def check(name,ok):
    checks.append(dict(name=name,passed=bool(ok)));assert ok,name
class Memory:
    def __init__(self):self.calls=[];self.returnable=True
    def route(self,pose,identifier=0,peers=(),destination=None):
        self.calls.append(None if destination is None else np.asarray(destination).tolist())
        return ([np.asarray(destination).copy()],np.asarray(destination).copy())if self.returnable else([],None)
class Parent:
    PLAN_FRESH_STEPS=240;STATE_FRESH_STEPS=120
    def __init__(self):
        self.identifier=0;self.fleet_plan=None;self.fleet_states={i:(100,np.array([16.*i,0.]),2)for i in range(3)}
        self.pose=np.array([0.,0.]);self.rally=np.array([40.,0.]);self.heading=0.;self.qty=2;self.elapsed_timestep=100
        self.survey_plan=(100,0,0,np.array([80.,0.]),180);self._sortie_state='RETURN';self.last_plan_step=99
        self.placement_goal=None;self.memory=Memory();self.team_size=3;self.escape_until=-1;self.waypoints=[];self.submitted=False
        self.calls={};self.output=([np.array([80.,0.])],np.array([80.,0.]));self.command=dict(forward=.9,lateral=.5,rotation=.2,grasper=0,place_bomb=0)
    def carried_bombs_count(self):return self.qty
    def _sortie_return(self,step):self._sortie_state='RETURN'
    def _messages(self):self.calls['messages']=self.calls.get('messages',0)+1
    def _should_defer_commitment(self,*args):self.calls['defer']=self.calls.get('defer',0)+1;return True
    def _build_survey_plan(self,*args):self.calls['survey']=self.calls.get('survey',0)+1;return 'survey'
    def _sortie_admit(self,*args):self.calls['sortie']=self.calls.get('sortie',0)+1;return 'sortie'
    def _plan_route(self,*args):self.calls['route']=self.calls.get('route',0)+1;return self.output
    def _maybe_place(self,command,*args):self.calls['place']=self.calls.get('place',0)+1;command['place_bomb']=1
    def measured_velocity(self):return np.array([2.,-1.])
    def control(self):return dict(self.command)
class D(mod.OneWayDeploymentMixin,Parent):pass
def valid():return(100,0,{0:(2,[np.array([80.,0.]),np.array([160.,0.])]),1:(2,[np.array([80.,80.])])})
d=D();ans=d._plan_route(100,False,[])
check('no_plan_original_exploration_forwarded',ans is d.output and d.deployment_started is None)
check('prephase_defer_original',d._should_defer_commitment(1,300,50,20,4,100)is True)
check('prephase_survey_original',d._build_survey_plan(100)=='survey')
check('prephase_sortie_original',d._sortie_admit(100,[])=='sortie')
c={};d._maybe_place(c,100,[]);check('no_plan_cannot_place',not c)
for label,plan in[
    ('future',(101,0,valid()[2])),('expired',(-140,0,valid()[2])),('wrong_leader',(100,1,valid()[2])),
    ('empty_goals',(100,0,{0:(2,[])})),('nan_goal',(100,0,{0:(2,[np.array([np.nan,0.])])})),
    ('malformed_goal',(100,0,{0:(2,[['bad',0.]])})),('bool_epoch',(True,0,valid()[2]))]:
    x=D();x.fleet_plan=plan;check(label+'_does_not_start_phase',not x._latch_deployment(100))
d.fleet_plan=valid();d._messages()
check('received_valid_plan_latches_phase',d.deployment_started==(100,100,0))
check('accepted_plan_forces_current_replan',d.last_plan_step==-1000)
check('phase_cancel_optional_survey',d.survey_plan is None)
check('postphase_defer_disabled',d._should_defer_commitment(99,300,50,20,4,100)is False and d.calls['defer']==1)
check('postphase_survey_not_built',d._build_survey_plan(100)is None and d.calls['survey']==1)
check('postphase_empty_sortie_not_admitted',d._sortie_admit(100,[])is None and d.calls['sortie']==1)
d.placement_goal=np.array([80.,0.]);r=d._plan_route(100,False,[])
check('valid_placement_route_unchanged',r is d.output and not d.memory.calls)
d.placement_goal=None;r=d._plan_route(124,False,[])
check('exploratory_fallback_redirects_to_relay',np.array_equal(r[1],d.rally)and d.memory.calls==[[40.,0.]])
d.memory.returnable=False;r=d._plan_route(148,False,[])
check('no_known_relay_route_holds_without_fake_path',r==([],None)and d._deployment_hold)
c=d.control();check('holding_brakes_instead_of_laser_fallback',c['forward']<0 and c['lateral']>0 and c['place_bomb']==0)
d.escape_until=200;check('existing_emergency_escape_preserved',d.control()==d.command)
d.escape_until=-1;d.command['place_bomb']=1;check('valid_drop_command_not_cancelled',d.control()==d.command)
d.command['place_bomb']=0;d.fleet_plan=None;check('phase_never_reverts_when_plan_expires',d._latch_deployment(1000))
d.qty=0;r=d._plan_route(1000,True,[]);check('empty_return_original_route_preserved',r is d.output)
x=D();x._sortie_state='SORTIE';x.fleet_plan=valid();x._latch_deployment(100);check('preexisting_optional_sortie_recalled',x._sortie_state=='RETURN')
check('submission_condition_not_overridden','_submission_due'not in vars(mod.OneWayDeploymentMixin))
# Execute actual current completion guard; these are guards, not SDK finish tests.
class Completion:
    _submission_due=original_function('completion_consensus.py','CompletionConsensusMixin','_submission_due')
    _record_own_completion=original_function('completion_consensus.py','CompletionConsensusMixin','_record_own_completion')
    def __init__(self):self.remaining=100;self.qty=0;self.identifier=0;self.team_size=3;self.completion_certificates={};self.cached_packet=1;self.map_quality_records={};self.STATE_FRESH_STEPS=120
    def _remaining_steps(self):return self.remaining
    def carried_bombs_count(self):return self.qty
    def _map_quality(self):return(.99,100)
x=Completion();check('last_own_bomb_not_enough_without_all_certificates',not x._submission_due(100))
x.completion_certificates={0:100,1:99,2:98};check('all_certificates_and_no_better_peer_may_submit',x._submission_due(100))
x.qty=1;check('positive_budget_with_remaining_bomb_does_not_submit',not x._submission_due(100))
x.remaining=0;check('zero_budget_can_submit_with_remaining_bomb',x._submission_due(100))
out=dict(status='PASS_ONEWAY_PHASE_CONTRACT_AND_CURRENT_COMPLETION_GUARDS',checks=checks,
         rule_sha256=hashlib.sha256((F/'deployment_phase.py').read_bytes()).hexdigest(),sdk_frames=0,native_rounds=0,
         limits=['Explicit protocol/memory fixture, not real SDK or performance.',
                 'Single local phase latch after original accepted fleet plan; no claim of simultaneous global transition or guaranteed completed route.'])
(F/'CONTRACT_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=out['status'],checks=len(checks))))
