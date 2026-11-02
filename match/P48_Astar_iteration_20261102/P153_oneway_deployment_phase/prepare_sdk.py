"""Freeze one new user-authorized stage rule on independent original A-star."""
from pathlib import Path
import ast,hashlib,json
F=Path(__file__).resolve().parent
BASE=Path('E:/codex/P48_astar_five_20261102')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
contract=json.loads((F/'CONTRACT_FIRST.json').read_text());assert contract['rule_sha256']==sha(F/'deployment_phase.py')
base=json.loads((BASE/'CANDIDATE_MANIFEST.json').read_text(encoding='utf-8-sig'))
project=F/'candidate_project';assert not project.exists();sol=project/'src/swarm_rescue/solutions';sol.mkdir(parents=True)
for n,h in base['payload_files'].items():
    p=BASE/'versions/P48_ASTAR/source'/n;assert sha(p)==h
    (project/'req.txt'if n=='req.txt'else sol/n).write_bytes(p.read_bytes())
(sol/'deployment_phase.py').write_bytes((F/'deployment_phase.py').read_bytes())
entry=sol/'my_drone_eval.py';text=entry.read_text(encoding='utf-8-sig')
assert text.count('class MyDroneEval(FreshOpportunityAuditMixin,')==1
text='from swarm_rescue.solutions.deployment_phase import OneWayDeploymentMixin\n'+text.replace('class MyDroneEval(FreshOpportunityAuditMixin,','class MyDroneEval(OneWayDeploymentMixin,FreshOpportunityAuditMixin,')
entry.write_bytes(text.encode())
for p in sol.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
files={p.relative_to(project).as_posix():sha(p)for p in project.rglob('*')if p.is_file()}
changes=[n for n,h in base['payload_files'].items()if sha(project/'req.txt'if n=='req.txt'else sol/n)!=h];assert changes==['my_drone_eval.py']
manifest=dict(status='FROZEN_ORIGINAL_ASTARA_PLUS_ONEWAY_PHASE',base_archive_sha256=base['sha256'],candidate_files=files,
              changed_parent_files=changes,new_modules=['deployment_phase.py'],official_release=False,
              concept='No further voluntary exploratory target/survey/sortie/commitment deferral after receiving an original valid fleet deployment plan; sensing stays active.',
              limits=['Transition is per receiver at actual message time, not simultaneous fleet barrier.',
                      'No mission completion guarantee; unreachable assignments use original replanning and relay return/hold. Original budget exit stays.'])
(F/'CANDIDATE_MANIFEST_FIRST.json').write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
(F/'BASE_WORKSPACE.json').write_bytes((BASE/'WORKSPACE_READY.json').read_bytes())
source=(F.parent/'P142_profile_and_task_chain/check_sdk_astar_profile.py').read_text()
source=source.replace('P142 frozen A* own-task-chain and optional read-only cProfile; authored physics only.','P153 strict one-way deployment phase on original A-star, same authored closure.')
source=source.replace('raw_local=GreedyMappingDrone._plan_route','phase_local_calls=[];phase_routes=[]\nraw_local=GreedyMappingDrone._plan_route')
source=source.replace('def audit_local(d,step,returning,peer_goals):','def audit_local(d,step,returning,peer_goals):\n phase_local_calls.append(dict(owner=int(d.identifier or 0),step=int(step),returning=bool(returning)))')
anchor="  if TRACE_ENABLED:route_details.append(dict(before=task_before,after=task_snapshot(self,step),returned_goal=None if result[1]is None else np.asarray(result[1]).tolist(),returned_waypoints=[np.asarray(p).tolist()for p in result[0]]))"
assert source.count(anchor)==1
source=source.replace(anchor,anchor+'''
  if self.deployment_started is not None:
   goal=result[1];target=self.placement_goal
   low=[e for e in phase_local_calls if e['owner']==int(self.identifier or 0)and e['step']==step]
   target_mode=target is not None and goal is not None and np.linalg.norm(np.asarray(goal)-target)<1.
   return_mode=bool(low)and low[-1]['returning']
   phase_routes.append(dict(owner=int(self.identifier or 0),step=step,inventory=int(self.carried_bombs_count()),
     deploy_target=bool(target_mode),relay_return_or_hold=bool(return_mode),sortie=self._sortie_state,
     valid_final_route=bool(target_mode or return_mode)))''')
source=source.replace(' out=dict(profile_enabled='," out=dict(deployment_events=[e for d in drones for e in d.deployment_events],deployment_counts=[d.deployment_counts for d in drones],deployment_started=[d.deployment_started for d in drones],phase_routes=phase_routes,profile_enabled=")
ast.parse(source);(F/'check_sdk_phase.py').write_bytes(source.encode())
parent=F.parent/'P142_profile_and_task_chain/BASELINE_FIRST.json'
pre=dict(status='FROZEN_BEFORE_USER_PHASE_RULE_FIRST_SDK',parent_result=str(parent),parent_result_sha256=sha(parent),code_sha256=sha(F/'check_sdk_phase.py'),manifest_sha256=sha(F/'CANDIDATE_MANIFEST_FIRST.json'),
         user_interpretation='Explore first, then execute all inventory; one-way per actual fleet-plan receipt, not same-pixel or instant simultaneous deployment, not waiting until clock expiration.',
         case='cross_sdk',horizon=1000,wall_rate=.05,authored_seed=615,maximum_cases=1,
         gates=['All original finite/callback/inventory/loop checks except known parent health flag; per-owner minimum health no worse.',
                'All five actually latch phase; all actual requests after phase, no executed final exploratory route after phase.',
                'Full actual pre-first-phase frame rows identical to retained parent, actual post-phase commands/route decisions change.',
                'All10, actual submitted map and surface credit, mean five raw maps, wall and time nonregress vs retained parent.',
                'Controllable subtotal >= parent+0.25; first failure retained and no parameter/seed/label rescue.'],
         unchanged=['Original readiness gate/coverage supplier/A-star/placement safety and confirmation/submission-budget guard','Map/sensing/SDK/threads/dependencies','No P145/P149 rule stacked'],
         source_reference='PX4 Mission Mode engineering state/mission distinction only, https://docs.px4.io/main/en/flight_modes_mc/mission; no autopilot or threshold transplantation.',
         automatic_native=False,automatic_five=False,native_rounds=0)
(F/'PREDECLARATION_FIRST.json').write_bytes((json.dumps(pre,ensure_ascii=False,indent=2)+'\n').encode())
workspace=(F.parent/'P149_ready_waiting_coordinator/prepare_workspace.py').read_text().replace('P149','P153')
ast.parse(workspace);(F/'prepare_workspace.py').write_bytes(workspace.encode())
runner=(F.parent/'P149_ready_waiting_coordinator/run_diagnostic.py').read_text()
runner=runner.replace('P149_Astar_ready_waiting_20261102','P153_Astar_oneway_deployment_20261102').replace('check_sdk_ready_waiting.py','check_sdk_phase.py').replace("'P149'","'P153'").replace("label='READY_WAITING_FIRST'","label='ONEWAY_PHASE_FIRST'")
start=runner.index("    a=load(parent);b=load(F/(label+'.json'))")
end=runner.index("\nif __name__=='__main__':",start)
runner=runner[:start]+'''    a=load(parent);b=load(F/(label+'.json'))
    original=a['coverage_evaluation'];candidate=b['coverage_evaluation']
    starts=[e for e in b['deployment_events']if e['kind']=='PHASE_BEGIN']
    first=min((e['step']for e in starts),default=len(a['rows'])+1)
    health_a=[min(r['health'][i]for r in a['rows'])for i in range(5)]
    health_b=[min(r['health'][i]for r in b['rows'])for i in range(5)]
    first_by_owner={e['owner']:e['step']for e in starts}
    drops=[]
    previous=[2]*5
    for row in b['rows']:
        for i,q in enumerate(row['inventory']):
            if q<previous[i]:drops.append(dict(owner=i,step=row['step'],after_phase=i in first_by_owner and row['step']>=first_by_owner[i]))
        previous=row['inventory']
    credit_a=a['submission_records'][0]['breakdown']['credit']if a['submission_records']else None
    credit_b=b['submission_records'][0]['breakdown']['credit']if b['submission_records']else None
    prefix=b['rows'][:first-1]==a['rows'][:first-1]
    checks=dict(original_nonhealth_sdk_checks=all(v for k,v in b['checks'].items()if k!='health_unchanged'),
      no_added_damage=all(x>=y for x,y in zip(health_b,health_a)),all_five_phase_started=len(first_by_owner)==5,
      identical_prefix=prefix,actual_decisions_changed=b['rows']!=a['rows'],
      all_final_routes_deploy_or_return=bool(b['phase_routes'])and all(e['valid_final_route']and e['sortie']!='SORTIE'for e in b['phase_routes']),
      all_drops_after_actual_phase=bool(drops)and all(e['after_phase']for e in drops),
      all10=candidate['actual_bomb_count']==10 and b['rows'][-1]['inventory']==[0]*5,
      map_nonregress=candidate['actual_submitted_map']is not None and candidate['actual_submitted_map']>=original['actual_submitted_map'],
      credit_nonregress=credit_b is not None and credit_b>=credit_a,
      mean5_map_nonregress=sum(e['score']for e in b['map_results'])>=sum(e['score']for e in a['map_results']),
      wall_nonregress=candidate['score_wall']>=original['score_wall'],time_nonregress=candidate['score_time']>=original['score_time'],
      subtotal_gain=candidate['controllable_subtotal']is not None and candidate['controllable_subtotal']>=original['controllable_subtotal']+.25)
    result=dict(status='PASS_ONEWAY_PHASE_AUTHOR_MECHANISM'if all(checks.values())else'STOP_FIRST_ONEWAY_PHASE_MECHANISM_GATE',checks=checks,
      physics_steps=b['physics_steps'],parent_steps=a['physics_steps'],baseline=original,candidate=candidate,
      phase_started=b['deployment_started'],phase_events=b['deployment_events'],phase_counts=b['deployment_counts'],phase_routes=b['phase_routes'],drops=drops,
      parent_health_min=health_a,candidate_health_min=health_b,native_rounds=0,automatic_native=False,automatic_five=False,
      limitation='One same authored arena/input seed, no BLUE, not full red score or official five-map gain; no simultaneous global barrier claimed.')
    write('RESULT_FIRST.json',result)
    write('STATUS.json',dict(utc=utc(),status=result['status'],native_rounds=0),False)
    print(json.dumps(dict(status=result['status'],checks=checks,physics_steps=b['physics_steps'],score=candidate),ensure_ascii=False),flush=True)
'''+runner[end:]
ast.parse(runner);(F/'run_diagnostic.py').write_bytes(runner.encode())
history=[]
for root in[F.parent,Path('E:/codex/PJ01_rule_refinement_20261101'),Path('E:/codex/UAV_rules_astar_restart_20261030')]:
    for p in root.rglob('*phase*.py'):
        if F in p.parents:continue
        history.append(dict(path=str(p),sha256=sha(p)))
assert all(r['sha256']!=sha(F/'deployment_phase.py')for r in history)
flight=dict(status='PASS_NO_EXACT_HISTORICAL_SOURCE_MATCH',rule_sha256=sha(F/'deployment_phase.py'),files_checked=len(history),history=history,
            conceptual_review=['Original ActiveCoverage already releases all inventory when acquisition stops; this does not claim new late inventory release.',
                               'New difference is no return to voluntary exploration after original plan receipt; no fixed 3R/late time threshold.',
                               'P149/P151 new waiting election is not imported; original fleet leadership/message protocol unchanged.'])
(F/'MECHANISM_PREFLIGHT_FIRST.json').write_bytes((json.dumps(flight,ensure_ascii=False,indent=2)+'\n').encode())
bound=['run_diagnostic.py','prepare_workspace.py','check_sdk_phase.py','PREDECLARATION_FIRST.json','CANDIDATE_MANIFEST_FIRST.json','MECHANISM_PREFLIGHT_FIRST.json','CONTRACT_FIRST.json']
(F/'LAUNCH_BINDING_FIRST.json').write_bytes((json.dumps(dict(script_sha256={n:sha(F/n)for n in bound}),indent=2)+'\n').encode())
print(json.dumps(dict(status=pre['status'],source_files=len(files),new_modules=manifest['new_modules'],contract_checks=len(contract['checks']))))
