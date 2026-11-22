"""Real candidate methods with sensor/message fixtures; no SDK rounds or physics."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace,MethodType
from zipfile import ZipFile
import ast,copy,importlib,json,os,sys,traceback
ROOT=Path(__file__).resolve().parent
SDK_SRC=Path(sys.argv[1]);sys.path.insert(0,str(SDK_SRC))
import swarm_rescue.solutions
swarm_rescue.solutions.__path__=[str(ROOT/'candidate'),*swarm_rescue.solutions.__path__]
import numpy as np
from swarm_rescue.solutions.red_hooks import RedHooks
from swarm_rescue.solutions.deadline_submission import BudgetSubmission,DeadlineSubmission
from swarm_rescue.solutions.coverage_placement import CoveragePlacementDrone
from swarm_rescue.solutions.group_exchange import GroupExchange
from swarm_rescue.solutions.final_map_relay import FinalMaps
import swarm_rescue.solutions.red_hooks as red_module
assert Path(red_module.__file__).resolve()==(ROOT/'candidate/red_hooks.py').resolve()
build=json.loads((ROOT/'BUILD.json').read_text())
def source_hashes():return {n:sha256((ROOT/'candidate'/n).read_bytes()).hexdigest() for n in build['candidate_files']}
assert source_hashes()==build['candidate_files']
checks=[]
def check(name,condition,**details):
    assert condition,name
    checks.append(dict(name=name,status='PASS',**details))

class NavigationReached(Exception):pass
class BaseStub:
    def control(self):
        self.navigation_calls+=1
        raise NavigationReached
# The complete, unmodified candidate control AST is tested with a base that
# records entry and raises, so no navigation or physics step can execute.
tree=ast.parse((ROOT/'candidate/red_hooks.py').read_bytes())
red_class=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RedHooks')
control=next(n for n in red_class.body if isinstance(n,ast.FunctionDef) and n.name=='control')
harness=ast.ClassDef(name='ControlHarness',bases=[ast.Name(id='BaseStub',ctx=ast.Load())],keywords=[],body=[copy.deepcopy(control)],decorator_list=[])
mod=ast.fix_missing_locations(ast.Module(body=[harness],type_ignores=[]))
ns=dict(BaseStub=BaseStub,CoveragePlacementDrone=CoveragePlacementDrone)
exec(compile(mod,'<candidate_control_ast>','exec'),ns)
ControlHarness=ns['ControlHarness']

def drone(owner=0,score=6000):
    d=ControlHarness()
    d.identifier=owner;d.limit=5400;d.team_size=5;d.walltime_limit=180.;d.elapsed_walltime=120.
    d.elapsed_timestep=5022;d.initial_inventory=2;d.previous_inventory=0;d.sensor_inventory=0;d.pending_drop=None
    d.inventory_records={p:(5000,0) for p in range(5)}
    d.map_quality=9000;d.map_bids={};d.final_maps=FinalMaps(owner,5);d.final_maps.snapshots={owner:None}
    d.budget_submission=BudgetSubmission(score=score);d.budget_submission_event=None;d.budget_submission_audit=[]
    d.deadline_submission=DeadlineSubmission();d.deadline_submission_event=None;d.deadline_versions={}
    d.group_best_image=(np.array([[1,0],[0,1]],dtype=np.uint8),None,{'fixture':1})
    d.deadline_submission.backup_image=np.array([[1,1],[0,0]],dtype=np.uint8)
    d.deadline_submission.backup_step=4995
    d.first_ready_to_submit_step=None;d.submitted=False;d.submissions=[];d.navigation_calls=0
    d.last_confirmed_drop_step=None;d.drop_records={};d.team_exchange_audit=[]
    d.carried_bombs_count=lambda:d.sensor_inventory
    d.submit_exploration_map=lambda image:d.submissions.append(image.copy())
    def forbidden(*a,**kw):raise AssertionError('budget requested fitting, fusion or navigation')
    d._render_submission=forbidden;d._submission_image=forbidden;d.final_maps.fuse=forbidden
    for name in ['_budget_submission_candidate','_budget_submission_gate','_try_budget_submission','_force_deadline_submission','_own_map_bid','_receive_team_coordination']:
        setattr(d,name,MethodType(getattr(RedHooks,name),d))
    d._sync_placement=MethodType(CoveragePlacementDrone._sync_placement,d)
    d._all_inventory_empty=MethodType(CoveragePlacementDrone._all_inventory_empty,d)
    return d

def run_budget(d,first=5022,last=5051,before=None):
    for step in range(first,last+1):
        d.elapsed_timestep=step
        if before:before(d,step)
        if d._try_budget_submission(step):return step
    return None

def run_control(d,step,wall):
    d.elapsed_timestep=step;d.elapsed_walltime=wall
    return d.control()

groups=[]
def group(name,fn):
    begin=len(checks);fn();groups.append(dict(name=name,status='PASS',checks=len(checks)-begin))

def stale_stock():
    d=drone();d.inventory_records.update({3:(2678,1),4:(1791,1)})
    records=copy.deepcopy(d.inventory_records);backup=d.deadline_submission.backup_image.copy()
    reason,unknown,carrying=d._budget_submission_gate(5022)
    check('stale_Map06_stock_eligible',reason is None and unknown==(3,4) and carrying==())
    check('stale_stock_not_forged_empty',not d._all_inventory_empty() and d.inventory_records==records)
    gx=SimpleNamespace(owner=0,candidates=SimpleNamespace(snapshots={0:1}),start=lambda:3240,refresh_comparison=lambda *a:None)
    check('ordinary_submit_still_requires_confirmation',not GroupExchange.try_submit(gx,d,5022,lambda *a:None))
    newer=np.array([[0,1],[1,1]],dtype=np.uint8)
    def refresh(obj,step):
        if step==5030:obj.group_best_image=(newer,None,{'fixture':2})
    actual=run_budget(d,before=refresh)
    check('stale_stock_budget_submitted_in_window',actual is not None and 5022<=actual<=5051,step=actual)
    check('latest_cached_image_used',np.array_equal(d.submissions[0],newer) and d.final_submission_versions=={'fixture':2})
    check('confirmation_gaps_reported',d.budget_submission_event['unconfirmed_peers']==(3,4) and d.budget_submission_event['team_confirmed'] is False)
    check('peer_records_and_original_backup_retained',d.inventory_records==records and np.array_equal(d.deadline_submission.backup_image,backup))
    check('budget_does_not_pollute_hard_state',d.deadline_submission_event is None and d.deadline_submission.score is None and d.deadline_submission.image is None)
    d=drone();d.group_best_image=None;expected=d.deadline_submission.backup_image.copy()
    check('own_backup_can_submit_without_renderer',run_budget(d) is not None and np.array_equal(d.submissions[0],expected) and d.budget_submission_event['image_source']=='backup_cache')
    d=drone();d.group_best_image=None;d.deadline_submission.backup_image=None
    check('empty_cache_does_not_start_fitting',run_budget(d) is None and not d.submissions)
    d=drone(score=None);step=run_budget(d)
    check('budget_initializes_existing_rank_without_normal_ready',step is not None and d.budget_submission.score==d.final_maps.rank(d.map_quality) and d.first_ready_to_submit_step is None)

def fresh_stock():
    d=drone();d.inventory_records[3]=(5022,1)
    check('recent_remaining_bomb_vetoes_entire_window',run_budget(d) is None and not d.submissions)
    check('veto_not_broadcast_as_ready',d._own_map_bid(5051)[2] is False)
    d=drone();d.inventory_records[3]=(5022-360,1)
    check('stock_age_360_still_fresh',d._budget_submission_gate(5022)[0]=='fresh_peer_stock')
    d.inventory_records[3]=(5022-361,1)
    check('stock_age_361_is_unknown',d._budget_submission_gate(5022)==(None,(3,),()))
    d.inventory_records[3]=(100,0)
    check('old_confirmed_zero_remains_confirmed',d._budget_submission_gate(5022)==(None,(),()))
    d=drone();d.inventory_records.pop(4)
    check('missing_confirmation_explicitly_unknown',d._budget_submission_gate(5022)==(None,(4,),()))
    d=drone();d.inventory_records[3]=(5020,1);d._try_budget_submission(5022)
    d._receive_team_coordination({'id':1,'red_inventory':{3:(5030,0)}},5030)
    check('actual_new_zero_unblocks_budget',d.inventory_records[3]==(5030,0) and run_budget(d,5030) is not None)
    d=drone();d._own_map_bid(5022);d.inventory_records[3]=(5030,1)
    check('new_remaining_bomb_revokes_prior_readiness',d._own_map_bid(5030)[2] is False and not d._try_budget_submission(5047))

def local_confirmation():
    for prior,sensor,label in [(1,1,'carrying'),(0,1,'sensor_disagrees'),(1,0,'not_yet_synced')]:
        d=drone();d.previous_inventory=prior;d.sensor_inventory=sensor
        check('local_'+label+'_rejected',d._budget_submission_gate(5047)[0]=='local_stock_or_pending' and not d._try_budget_submission(5047))
    d=drone();d.pending_drop=(1,np.array([10.,20.]),5047);d.previous_inventory=1;d.sensor_inventory=1
    d._sync_placement(5047)
    check('request_without_stock_drop_is_not_confirmation',d.pending_drop is not None and not d.drop_records and not d._try_budget_submission(5047))
    d._sync_placement(5048)
    check('rejected_request_does_not_create_drop',d.pending_drop is None and not d.drop_records and d.previous_inventory==1 and not d._try_budget_submission(5048))
    d=drone();d.pending_drop=(1,np.array([10.,20.]),5046);d.previous_inventory=1;d.sensor_inventory=0
    result=run_control(d,5047,120.)
    check('real_stock_drop_confirmed_before_budget',d.pending_drop is None and (0,2) in d.drop_records and d.last_confirmed_drop_step==5047 and d.submitted)
    check('budget_control_returns_empty_command',result==CoveragePlacementDrone._empty_command() and d.navigation_calls==0)
    d=drone();d.pending_drop=(1,np.array([10.,20.]),5047)
    check('pending_even_with_zero_stock_vetoes_unsynced_bid',d._own_map_bid(5047) is None and not d._try_budget_submission(5047))

def duplicate_messages():
    d=drone();d.inventory_records[3]=(2678,1);window=d.budget_submission.window(5400)
    first_score=d._own_map_bid(5022)[1]
    def repeat(obj,step):
        obj._receive_team_coordination({'id':1,'red_inventory':{3:(2678,1)}},step)
        obj.map_bids[1]=(step,9000,True)
        obj.map_quality=9999
        assert obj.budget_submission.window(5400)==window
    submitted=run_budget(d,before=repeat)
    check('repeated_forwarding_keeps_source_stamp',d.inventory_records[3]==(2678,1))
    check('duplicate_broadcast_does_not_restart_window',window==(5022,5051) and submitted==5047,step=submitted)
    check('election_score_stable_during_window',d.budget_submission.score==first_score)
    d=drone();d.inventory_records[3]=(5022,1)
    check('blocked_window_does_not_extend_after_expiry',run_budget(d) is None and not d._try_budget_submission(5383) and d.budget_submission.window(5400)==window)
    for limit in [100,5400,10000]:
        start,end=BudgetSubmission.window(limit)
        active=[s for s in range(max(0,start-1),end+2) if BudgetSubmission.active(s,limit)]
        check('absolute_window_length_'+str(limit),len(active) in (0,30) and (not active or active==list(range(start,end+1))))

def election():
    d=drone(score=6000);d.map_bids[3]=(5022,9000,True)
    step=run_budget(d)
    check('missing_higher_bidder_yield_is_bounded',step==5047 and step-5022+1<=30,step=step)
    d=drone(score=6000);d.map_bids={3:(5022,9000,False),4:(5021,10000,True),1:(5040,10000,True)}
    check('ineligible_old_and_future_bids_ignored',d.budget_submission.peer_ranks(5022,5400,d.map_bids)==[])
    low,high=drone(0,6000),drone(3,9000)
    low.map_bids[3]=(5022,9000,True);high.map_bids[0]=(5022,6000,True)
    winner=None
    for s in range(5022,5052):
        for d in [low,high]:
            if d._try_budget_submission(s):winner=(d.identifier,s);break
        if winner:break
    check('higher_candidate_not_fixed_to_drone_zero',winner==(3,5027),winner=winner)
    d=drone();d.map_bids[1]=(5051,10000,True)
    check('last_window_step_still_has_bounded_exit',d._try_budget_submission(5051))
    d=drone();check('no_budget_exit_after_30_steps',not d._try_budget_submission(5052) and not d.submissions)

def hard_fallback():
    for step,wall,reason in [(5030,179.,'walltime'),(5396,120.,'timestep')]:
        d=drone();d.deadline_submission.image=np.ones((2,2),dtype=np.uint8)
        def unexpected(*a):raise AssertionError('budget was called before hard fallback')
        d._try_budget_submission=unexpected
        result=run_control(d,step,wall)
        check('hard_'+reason+'_wins_first',d.deadline_submission_event['fallback']==reason and d.budget_submission_event is None and d.submitted and d.navigation_calls==0 and result==CoveragePlacementDrone._empty_command())
    d=drone();d.deadline_submission.fallback_reason(5029,5400,170.,180.)
    d.deadline_submission.image=np.ones((2,2),dtype=np.uint8)
    run_control(d,5030,178.)
    check('long_frame_adaptive_margin_preserved',d.deadline_submission_event['fallback']=='walltime' and d.budget_submission_event is None)
    check('original_1_5_second_reserve_preserved',DeadlineSubmission.MIN_WALL_MARGIN==1.5 and DeadlineSubmission.FALLBACK_STEPS==4 and DeadlineSubmission.window_start(5400)==5371)
    for step in [1,3240,3452,4996,5021,5052]:
        d=drone()
        try:run_control(d,step,0.)
        except NavigationReached:pass
        else:raise AssertionError('original control not reached outside budget: '+str(step))
        check('outside_budget_original_control_'+str(step),d.navigation_calls==1 and not d.submitted and d.budget_submission_event is None)
    # Compare the old and new bid method outside the budget window.
    with ZipFile(ROOT/'rowindex_baseline_snapshot.zip') as z:oldtree=ast.parse(z.read('red_hooks.py'))
    oldclass=next(n for n in oldtree.body if isinstance(n,ast.ClassDef) and n.name=='RedHooks')
    method=copy.deepcopy(next(n for n in oldclass.body if isinstance(n,ast.FunctionDef) and n.name=='_own_map_bid'))
    oldns=dict(DeadlineSubmission=DeadlineSubmission)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'<old_bid>','exec'),oldns)
    for step in [3452,4996,5021,5052,5371,5396]:
        d=drone();d.deadline_submission.score=6000
        check('outside_budget_bid_equal_'+str(step),d._own_map_bid(step)==oldns['_own_map_bid'](d,step))

try:
    for name,fn in [('旧投放确认不阻预算出口',stale_stock),('近期剩弹报告阻止结束',fresh_stock),('本机实投确认与待确认保护',local_confirmation),('重复广播不重启窗口',duplicate_messages),('高分未提交时有界退出',election),('双时限及长帧兜底优先',hard_fallback)]:group(name,fn)
    check('candidate_sources_unchanged_after_tests',source_hashes()==build['candidate_files'])
    result=dict(status='PASS',categories=groups,total_checks=len(checks),checks=checks,
        candidate_zip_sha256=build['candidate_zip_sha256'],source_files=source_hashes(),
        python=sys.version,numpy=np.__version__,sdk_src=str(SDK_SRC),controller_module=red_module.__file__,
        validation='real SDK imports and real candidate methods with sensor/message fixtures; control AST uses a base stub',
        full_matches=0,physics_steps=0,SDK_rounds=0,control_method_tests_are_not_simulations=True,
        window_5400=BudgetSubmission.window(5400),deadline_real_window_5400=DeadlineSubmission.window_start(5400))
except BaseException as exc:
    result=dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc(),categories=groups,checks=checks,full_matches=0,physics_steps=0)
    (ROOT/'COUNTEREXAMPLES.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    raise
(ROOT/'COUNTEREXAMPLES.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['checks','source_files']},indent=2,ensure_ascii=False))
