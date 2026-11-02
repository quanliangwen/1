"""Freeze one explicitly requested five-map corner-layout campaign, no control rerun."""
from pathlib import Path
import ast,hashlib,json,shutil,zipfile
F=Path(__file__).resolve().parent
B=Path('E:/codex/P48_astar_five_20261102')
V='P154_CORNER_ASTAR';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not(F/'TEST_PROTOCOL.json').exists()
contract=json.loads((F/'CORNER_CONTRACT_V2_FIRST.json').read_text());assert contract['status']=='PASS_CORNER_NUMERIC_AND_OBJECTIVE_MESSAGE_CONTRACTS'
assert all(sha(F/n)==h for n,h in contract['source_sha256'].items())
old=json.loads((B/'CANDIDATE_MANIFEST.json').read_text(encoding='utf-8-sig'))
S=F/'versions'/V/'source';S.mkdir(parents=True)
for n,h in old['payload_files'].items():
    p=B/'versions/P48_ASTAR/source'/n;assert sha(p)==h;(S/n).write_bytes(p.read_bytes())
for n in['corner_cluster.py','corner_mission.py']:(S/n).write_bytes((F/n).read_bytes())
p=S/'my_drone_eval.py';s=p.read_text(encoding='utf-8-sig');needle='class MyDroneEval(FreshOpportunityAuditMixin,';assert s.count(needle)==1
s='from swarm_rescue.solutions.corner_mission import CornerMissionMixin\n'+s.replace(needle,'class MyDroneEval(CornerMissionMixin,FreshOpportunityAuditMixin,');p.write_bytes(s.encode())
p=S/'team_coverage_lns.py';s=p.read_text(encoding='utf-8-sig');needle='    return refine_trust_region(memory,agents,drops,radius,base,travel_budget=travel_budget,forbidden_points=forbidden_points,forbidden_mask=forbidden_mask,_prepared=prepared)';assert s.count(needle)==1
s='from swarm_rescue.solutions.corner_cluster import corner_cluster_layout\n'+s
s=s.replace(needle,'    refined=refine_trust_region(memory,agents,drops,radius,base,travel_budget=travel_budget,forbidden_points=forbidden_points,forbidden_mask=forbidden_mask,_prepared=prepared)\n    return corner_cluster_layout(memory,agents,drops,radius,refined,travel_budget,forbidden_points,forbidden_mask,_prepared=prepared)');p.write_bytes(s.encode())
for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
payload={p.name:sha(p)for p in S.iterdir()};changes=[n for n,h in old['payload_files'].items()if payload[n]!=h];assert set(changes)=={'my_drone_eval.py','team_coverage_lns.py'}
archive=F/'versions'/V/'P154_corner_cluster_research.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED)as z:
    for p in sorted(S.iterdir()):z.writestr(p.name,p.read_bytes())
manifest=dict(sha256=sha(archive),payload_files=payload,base_archive_sha256=old['sha256'],changed_parent_files=changes,new_modules=['corner_cluster.py','corner_mission.py'],official_submission_ready=False)
(F/'CANDIDATE_MANIFEST.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
for n in['start_local_collector.py','check_scoped_serial.py','watch_completion.py']:(F/n).write_bytes((B/n).read_bytes())
s=(B/'collect_offline.py').read_text().replace('P48_astar_five_20261102','P154_corner_cluster_five_20261102').replace('P48_ASTAR_A',V+'_A')
s=s.replace('One requested P48 A* full five-map group','One requested coverage-guarded corner layout five-map group');(F/'collect_offline.py').write_bytes(s.encode())
s=(B/'launch_campaign.py').read_text().replace('FROZEN_P48_FIVE_SCORE_GENERALIZATION_LAUNCHED','FROZEN_CORNER_FIVE_LAUNCHED');(F/'launch_campaign.py').write_bytes(s.encode())
s=(B/'prepare_workspace.py').read_text().replace('P48_ASTAR',V).replace('P48_Astar_research.zip','P154_corner_cluster_research.zip');(F/'prepare_workspace.py').write_bytes(s.encode())
s=(B/'check_sdk_actual_zip_entry.py').read_text()
anchor='import numpy as np,numpy.random.mtrand,pandas as pd,cv2,yaml,pyglet'
s=s.replace(anchor,"class NoGurobi:\n def find_spec(self,fullname,path=None,target=None):\n  if fullname.split('.')[0]=='gurobipy':raise ImportError('Gurobi not permitted in this candidate')\nsys.meta_path.insert(0,NoGurobi())\n"+anchor)
anchor='    if arm==\'P26\':'
idx=s.index(anchor);end=s.index('\nfinally:window.close()',idx)
s=s[:idx]+'''    from swarm_rescue.solutions.bearing_memory import BearingMemory
    from swarm_rescue.solutions.corner_cluster import corner_cluster_layout
    from swarm_rescue.solutions.corner_mission import CornerMissionMixin
    assert CornerMissionMixin in MyDroneEval.__mro__
    probe=BearingMemory(800,800,identifier=0,team_size=5)
    probe.free[:]=True;probe.hits[1,1:110]=3;probe.hits[1:110,1]=3;probe.step=100
    probe_agents={k:(np.array([-160.+k*64.,0.]),2)for k in range(5)}
    points=[np.array([-320.+(i%5)*144.,320.-(i//5)*480.])for i in range(10)]
    probe_base={k:points[2*k:2*k+2]for k in range(5)}
    before=hashlib.sha256(probe.hits.tobytes()+probe.free.tobytes()).hexdigest()
    actual=corner_cluster_layout(probe,probe_agents,[],72.,probe_base,travel_budget=10000.)
    assert all(len(actual[k])==2 for k in range(5))and all(np.isfinite(p).all()for ps in actual.values()for p in ps)
    assert before==hashlib.sha256(probe.hits.tobytes()+probe.free.tobytes()).hexdigest()
    cluster_interface=dict(actual_BearingMemory_and_GeometryPlanningMemory=True,counts_preserved=True,map_arrays_unchanged=True,audit=probe.corner_cluster_diagnostics)
'''+s[end:]
s=s.replace("five_native_constructors_independent=True,","five_native_constructors_independent=True,cluster_interface=cluster_interface,")
(F/'check_sdk_actual_zip_entry.py').write_bytes(s.encode())
protocol=dict(status='FROZEN_EXPLICIT_CORNER_LAYOUT_DIRECT_FIVE',version=V,maps=['Map01','Map02','Map03','Map04','Map05'],native_rounds=10,RED_per_map=1,BLUE_per_map=1,external_seed=None,
              human_request='弹药主要集中在一个小角落增加蓝队难度，覆盖分不要降低太多；按此设计跑全图',
              coverage_floor=.90,coverage_floor_scope='Conditional current sensor-derived residual wall value vs same-call original layout, NOT guarantee of official actual coverage or global optimality.',
              target_cluster_fraction=.60,cluster_radius_in_blast_radii=2.,original_spacing_and_prohibitions=True,
              actual_cluster_metrics=['max actual final bomb count in accepted corner disks','same count with original12px arrival allowance, separately labelled'],
              baseline_mean=74.25588336546745,baseline_source=str(B/'FIVE_COMPARISON.json'),baseline_sha256=sha(B/'FIVE_COMPARISON.json'),
              qualification='32 authored numeric/protocol checks and actual ZIP ABI/SDK/5 constructors/interface before original finite five; explicit direct-five request means no score-screen pilot.',
              pilot_screening=False,automatic_B=False,automatic_iteration=False,official_upload=False,
              limitations=['A 90% predicted floor may legitimately reject majority clustering; record acceptance and actual concentration, do not call fallback a successful cluster trial.',
                           'New natural-random episodes; not paired seeded causal evidence. Retain all five legal scores, no score-based retries.',
                           'No P153 phase change or P145/P152 rendering changes stacked; original P48 A-star independent base.'],
              corner_contract_sha256=sha(F/'CORNER_CONTRACT_V2_FIRST.json'),candidate_manifest_sha256=sha(F/'CANDIDATE_MANIFEST.json'))
(F/'TEST_PROTOCOL.json').write_bytes((json.dumps(protocol,ensure_ascii=False,indent=2)+'\n').encode())
(F/'BASELINE_REFERENCE.json').write_bytes((B/'FIVE_COMPARISON.json').read_bytes())
s=(B/'declare_native.py').read_text().replace('P48_ASTAR',V).replace("assert read(F/'ASTAR_CONTRACT_FIRST.json')['status']=='PASS_ASTAR_SEARCH_AND_UNCHANGED_ENDPOINT_INTERFACES'","assert read(F/'CORNER_CONTRACT_V2_FIRST.json')['status']=='PASS_CORNER_NUMERIC_AND_OBJECTIVE_MESSAGE_CONTRACTS'\nassert entry['cluster_interface']['counts_preserved']and entry['cluster_interface']['map_arrays_unchanged']")
s=s.replace("retained_P48_mean=72.60267605460926","retained_P48_mean=74.25588336546745")
s=s.replace("Explicit user requests only A* navigation substitution and direct original five-map test. No pilot score gate. All other old ongoing iteration remains paused.","Explicit user requests coverage-guarded majority-corner placement and all original five maps; no control rerun or score pilot. Original SDK/BLUE/gates unchanged.")
s=s.replace("'ASTAR_CONTRACT_FIRST.json'","'CORNER_CONTRACT_V2_FIRST.json'")
(F/'declare_native.py').write_bytes(s.encode())
s=(B/'run_offline.py').read_text().replace('P48 A* navigation replacement group','coverage-guarded corner placement group')
needle="  rows.append(dict(map=name,full=row['full_score']"
assert s.count(needle)==1
extra='''  clusters=[];commits=[]
  for line in(result/(name+'_red')/'console.log').read_text(errors='replace').splitlines():
   if '[CORNER_CLUSTER] 'in line:clusters.append(json.loads(line.split('[CORNER_CLUSTER] ',1)[1]))
   if '[CORNER_COMMIT] 'in line:commits.append(json.loads(line.split('[CORNER_COMMIT] ',1)[1]))
  actual_bombs=json.loads((result/(name+'_red')/'round1_bombs.json').read_text())['bombs']
  accepted=[e for e in clusters if e.get('accepted')]
  concentration=[]
  for e in accepted:
   anchor=np.asarray(e['anchor'],float);radius=float(e['radius'])
   distances=[float(np.linalg.norm(np.array([p['x'],p['y']])-anchor))for p in actual_bombs]
   concentration.append(dict(corner=e['corner'],anchor=e['anchor'],radius=radius,actual_strict=sum(d<=radius for d in distances),actual_with12=sum(d<=radius+12 for d in distances)))
'''
s=s.replace(needle,extra+needle)
s=s.replace("blue_wallhit=row['blue']['max_walltime_reached'],actual_model_refreshes", "blue_wallhit=row['blue']['max_walltime_reached'],blue_public=row['blue'],layout_contribution=row['layout_contribution'],cluster_calls=len(clusters),cluster_accepted=len(accepted),cluster_commits=len(commits),cluster_model_audits=clusters,concentration=concentration,max_actual_cluster=max((e['actual_strict']for e in concentration),default=0),max_actual_cluster_with12=max((e['actual_with12']for e in concentration),default=0),actual_model_refreshes")
(F/'run_offline.py').write_bytes(s.encode())
s=(B/'run_and_launch.py').read_text().replace('P48_astar_five_20261102','P154_corner_cluster_five_20261102').replace('P48_ASTAR',V)
s=s.replace("assert json.loads((F/'ASTAR_CONTRACT_FIRST.json').read_text())['status'].startswith('PASS')","assert json.loads((F/'CORNER_CONTRACT_V2_FIRST.json').read_text())['status'].startswith('PASS')")
s=s.replace("'TEST_PROTOCOL.json']","'TEST_PROTOCOL.json','CORNER_CONTRACT_V2_FIRST.json','BASELINE_REFERENCE.json']")
(F/'run_and_launch.py').write_bytes(s.encode())
for p in F.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
print(json.dumps(dict(status=protocol['status'],payloads=len(payload),changed=changes,sha256=manifest['sha256'],native_rounds=10)))
