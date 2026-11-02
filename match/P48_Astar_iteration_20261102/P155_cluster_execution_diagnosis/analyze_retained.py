"""Read already byte-reviewed own RED text only; no new game or raw re-audit."""
from pathlib import Path
import ast,hashlib,json,re,tarfile
F=Path(__file__).resolve().parent;F.mkdir(exist_ok=True)
P=F.parent/'P154_corner_cluster_five';G=P/'P154_CORNER_ASTAR_A'
assert json.loads((G/'CLIENT_FIRST_RAW_REVIEW.json').read_text(encoding='utf-8-sig'))['status']=='PASS'
out=F/'EXECUTION_DIAGNOSIS_FIRST.json';assert not out.exists()
matrix=json.loads((P/'FIVE_COMPARISON.json').read_text(encoding='utf-8-sig'))
rows=[]
with tarfile.open(G/'raw_results.tar.gz')as archive:
 for r in matrix['rows']:
  name=r['map']+'_red/console.log';raw=archive.extractfile(name).read();lines=raw.decode(errors='replace').splitlines()
  placements=[]
  for line in lines:
   m=re.match(r'\[placement\] drone=(\d+) step=(\d+) inventory=(\d+) position=\(([-.\d]+),([-.\d]+)\)',line)
   if m:placements.append(dict(owner=int(m[1]),step=int(m[2]),inventory=int(m[3]),position=[float(m[4]),float(m[5])]))
  accepted=[a for a in r['model_audits']if a.get('accepted')]
  audits=[]
  for a in accepted:
   prior=[p for p in placements if p['step']<a['step']]
   future=[p for p in placements if p['step']>=a['step']]
   in_circle=lambda p:sum((p['position'][k]-a['anchor'][k])**2 for k in [0,1])<=a['radius']**2
   audits.append(dict(step=a['step'],planned_suffix=a['planned'],model_clustered=a['clustered'],wanted_in_last_proposal=a.get('last_proposal',{}).get('wanted'),anchor=a['anchor'],radius=a['radius'],coverage_ratio=a['coverage_ratio'],confirmed_before=len(prior),actual_before_in_circle=sum(map(in_circle,prior)),actual_after_in_circle=sum(map(in_circle,future))))
  rows.append(dict(map=r['map'],own_red_text_sha256=hashlib.sha256(raw).hexdigest(),accepted=audits,placements=placements,commit_checks=r['objective_commit_checks'],first_full_plan_attempt=next((a for a in r['model_audits']if a.get('planned')==10),None)))
source=P/'versions/P154_CORNER_ASTAR/source'
findings=[
 dict(kind='PROVEN_FORMULA',issue='quota_shrinks_with_suffix',evidence='wanted=ceil(.60*sum(len(base[owner]))) in corner_cluster.py; does not reference initial total 10'),
 dict(kind='PROVEN_PROTOCOL',issue='only_first_goal_reserved',evidence='FleetCoverageMixin._reserved_first_goals reserves exactly one target per owner; next suffix passed to supplier can change second targets'),
 dict(kind='PROVEN_PROTOCOL',issue='objective_context_tied_to_entire_plan_and240steps',evidence='CornerMissionMixin._valid_corner_context compares full-plan SHA/epoch; unmatched/replaced plan returns original defer decision'),
 dict(kind='PROVEN_RECORD',issue='acceptance_not_whole_mission_execution',evidence='Map01 step744 suffix5 model3 but0 actual in selected circle; step969 suffix2 model2 but1 actual. Map02 step1183 suffix3 model2 and2 actual. Map05 step1540 suffix2 model2 and2 actual, one already placed before acceptance'),
 dict(kind='LIMITATION',issue='missing_historical_task_chain',evidence='Original own RED logs have no complete owner-target binding/ack/rejection/route records; cannot uniquely label each displaced target as defer, reject, stale plan or local replacement'),
]
result=dict(status='COMPLETE_RETAINED_OWN_RED_EXECUTION_DIAGNOSIS',rows=rows,findings=findings,source_sha256={n:hashlib.sha256((source/n).read_bytes()).hexdigest()for n in ['corner_cluster.py','corner_mission.py','fleet_mission.py']},new_SDK_frames=0,new_native_rounds=0,read_BLUE_console=False,deserialized_NPZ_pickle=False,repeated_first_raw_review=False)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],accepted=[dict(map=r['map'],accepted=r['accepted'])for r in rows]),ensure_ascii=False))

