"""Actual original/new return methods, fixed sensors; no matches or physics."""
from pathlib import Path
from types import SimpleNamespace as NS
from zipfile import ZipFile
from hashlib import sha256
import ast,copy,json,sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,sys.argv[1])
import swarm_rescue.solutions
swarm_rescue.solutions.__path__=[str(ROOT/'candidate'),*swarm_rescue.solutions.__path__]
import numpy as np
import swarm_rescue.solutions.group_exchange as module
from swarm_rescue.solutions.group_exchange import GroupExchange
from swarm_rescue.solutions.pre_submit_scan import PreSubmitScan
from swarm_rescue.solutions.final_map_relay import FinalMaps
from swarm_rescue.solutions.deadline_submission import DeadlineSubmission,BudgetSubmission
from swarm_rescue.solutions.second_drop_site import SecondDropSite
build=json.loads((ROOT/'BUILD.json').read_text())
with ZipFile(ROOT/'snapshot60.zip') as z:tree=ast.parse(z.read('group_exchange.py'))
cls=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GroupExchange'))
ns=dict(vars(module));exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),'<frozen_return60>','exec'),ns)
Original=ns['GroupExchange']
checks=[]
def check(name,ok,**details):
    assert ok,name
    checks.append(dict(name=name,status='PASS',**details))
def fixture(kind=GroupExchange,limit=5400):
    g=kind(0,5,limit,(200,160));g.plan.root=(77,0.,0.);g.plan.acks=set(range(5))
    g.plan.trail=[(0.,0.),(30.,0.)];g.plan.branch_group=(0,3);g.plan.local_region=(0.,0.)
    d=NS(limit=limit,team_size=5,identifier=0,walltime_limit=240. if limit==7200 else 180.,elapsed_walltime=70.,
         elapsed_timestep=limit//2,previous_inventory=0,pending_drop=None,pose=np.array([30.,0.]),
         grid=NS(cell=lambda p:0,evidence=np.array([-1]),clearance=np.array([100.]),route=lambda *a:[]),
         placement=NS(maneuvers=NS(exit=None,waiting_exit=None)),drop_departure=NS(controls_step=-1),
         messenger=NS(state='IDLE',audit=[]),route=[(40.,0.)],search_task=object(),
         _all_inventory_empty=lambda:False,pre_submit_scan=PreSubmitScan())
    return d,g
for limit in (5400,7200):
    new=limit//2;old=limit*3//5
    for step,eligible in [(new-1,False),(new,True),(old-1,True),(old,True)]:
        d,g=fixture(limit=limit);intent=g.prepare_return(d,step)
        check(f'new_boundary_{limit}_{step}',(intent is not None)==eligible)
        if intent is not None:
            check(f'original_route_preserved_{limit}_{step}',intent.target==(0.,0.) and intent.route==((0.,0.),) and intent.eta==55)
    d,g=fixture(limit=limit)
    check('not_eligible_at_40_'+str(limit),g.prepare_return(d,limit*2//5) is None)
    d,g=fixture(Original,limit)
    check('old_candidate_not_ready_at_50_'+str(limit),g.prepare_return(d,new) is None)
    d,g=fixture(limit=limit)
    check('shared_start_still_60_'+str(limit),g.start()==old)
    check('fixed_submit_floor_unchanged_'+str(limit),g.finish_floor(d)==old+180+24)
    check('return_cutoff_still_85_'+str(limit),g.cutoff()==limit*85//100)
    d,g=fixture(limit=limit);g.candidates.freeze_local=lambda *a:None
    intent=g.prepare_return(d,new);g.commit_return(d,intent,new)
    check('commit_can_start_at_50_'+str(limit),g.started_step==new and g.phase=='RETURN_LOCAL' and d.route==[])
changes=[('stock',lambda d,g:setattr(d,'previous_inventory',1)),
         ('pending',lambda d,g:setattr(d,'pending_drop',(1,np.zeros(2),2699))),
         ('escape',lambda d,g:setattr(d.placement.maneuvers,'exit',object())),
         ('waiting_escape',lambda d,g:setattr(d.placement.maneuvers,'waiting_exit',object())),
         ('first_departure',lambda d,g:setattr(d.drop_departure,'controls_step',2700)),
         ('no_root',lambda d,g:setattr(g.plan,'root',None)),
         ('unsafe_join',lambda d,g:d.grid.evidence.fill(1)),
         ('wall_budget',lambda d,g:setattr(d,'elapsed_walltime',173.))]
for label,change in changes:
    d,g=fixture();change(d,g)
    check('early_return_protection_'+label,g.prepare_return(d,2700) is None)
for step in (3240,3400,4500,4580,4590,5022):
    a,g=fixture();b,old=fixture(Original)
    x=g.prepare_return(a,step);y=old.prepare_return(b,step)
    check('same_behavior_at_old_window_'+str(step),x==y)
d,g=fixture();d.carried_bombs_count=lambda:1
gate,evidence=SecondDropSite().completion_checks(d,2700,None,[],stationary=False)
check('last_bomb_completion_still_inactive_at_50',gate=='early' and evidence is None)
check('hard_margin_and_budget_unchanged',DeadlineSubmission.MIN_WALL_MARGIN==1.5 and BudgetSubmission.window(5400)==(5022,5051))
hashes={n:sha256((ROOT/'candidate'/n).read_bytes()).hexdigest() for n in build['candidate_files']}
check('all_source_hashes_unchanged',hashes==build['candidate_files'])
result=dict(status='PASS',total_checks=len(checks),checks=checks,candidate_zip_sha256=build['candidate_zip_sha256'],
 source_files=hashes,thresholds={'Map05':{'old':4320,'new':3600},'Map06':{'old':3240,'new':2700},'Map07':{'old':3240,'new':2700}},
 full_matches=0,physics_steps=0,SDK_rounds=0,V16_remains_competition_baseline=True)
(ROOT/'RETURN50_TESTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('checks','source_files')},indent=2))
