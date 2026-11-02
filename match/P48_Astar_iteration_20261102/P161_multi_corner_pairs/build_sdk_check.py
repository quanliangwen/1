from pathlib import Path
import hashlib,json,datetime
F=Path(__file__).resolve().parent;P=F.parent/'P159_cluster_coverage70'
text=(P/'check_sdk_inner.py').read_text()
text=text.replace("a=getattr(self.memory,'corner_cluster_diagnostics',None)","a=getattr(self.memory,'multi_corner_diagnostics',None)")
start=text.index(' accepted=[]\n');end=text.index(' scores=dict(',start)
replacement=''' accepted=[]
 for route in routes:
  a=route['audit']
  if a and a.get('accepted'):
   key=(a['step'],tuple(tuple(r['anchor'])for r in a['regions']),route['owner'])
   if not any(e['key']==key for e in accepted):accepted.append(dict(key=key,audit=a))
 concentration=[]
 for e in accepted:
  groups=[]
  for r in e['audit']['regions']:
   distances=[float(np.linalg.norm(np.asarray(p)-np.asarray(r['anchor'])))for p in positions]
   groups.append(dict(anchor=r['anchor'],pivot=r['pivot'],kind=r['kind'],radius=float(r['radius']),planned_count=int(r['planned_count']),physical_strict=sum(d<=r['radius']+1e-8 for d in distances),physical_with12=sum(d<=r['radius']+12+1e-8 for d in distances)))
  concentration.append(dict(owner=e['key'][2],step=e['audit']['step'],groups=groups,valid_small_groups=sum(2<=r['physical_strict']<=3 for r in groups),overfull_groups=sum(r['physical_strict']>3 for r in groups),grouped=sum(r['physical_strict']for r in groups if 2<=r['physical_strict']<=3)))
'''
text=text[:start]+replacement+text[end:]
needle=' # All actions/output images frozen before authored truth/actual objects used for evaluation.\n'
assert text.count(needle)==1
text=text.replace(needle," (F/(arm+'_CONTROL_FROZEN_FIRST.json')).write_text(json.dumps(dict(rows=rows,events=events,routes=routes,drops=drops),default=numeric_json,ensure_ascii=False)+'\\n')\n"+needle)
needle='point=lambda p:None if p is None else np.asarray(p).tolist()\n'
text=text.replace(needle,needle+'''def numeric_json(item):
 if isinstance(item,np.generic):return item.item()
 if isinstance(item,np.ndarray):return item.tolist()
 raise TypeError(type(item).__name__)
assert json.loads(json.dumps(dict(n=np.int64(3),b=np.bool_(True),a=np.array([1.])),default=numeric_json))==dict(n=3,b=True,a=[1.])
''')
text=text.replace("json.dumps(out,ensure_ascii=False,indent=2)","json.dumps(out,ensure_ascii=False,indent=2,default=numeric_json)")
text=text.replace("max_cluster=max((e['physical_strict']for e in concentration),default=0)","max_small_groups=max((e['valid_small_groups']for e in concentration),default=0)")
(F/'check_sdk_multi.py').write_text(text,encoding='utf-8')
runner=(P/'run_small.py').read_text().replace('P159_cluster_coverage70_20261102','P161_multi_corner_pairs_20261102').replace("for arm in ['P159']:","for arm in ['P161']:")
runner=runner.replace('CANDIDATE_MANIFEST_V2.json','CANDIDATE_MANIFEST_FIRST.json').replace('check_sdk_inner.py','check_sdk_multi.py')
runner=runner.replace("F/'P159_SDK_FIRST.json'","F/'P161_SDK_FIRST.json'")
start=runner.index(" cluster=max(");end=runner.index(" save('RESULT_FIRST.json'",start)
replacement=''' cohorts=[]
 for layout in b['concentration']:
  old_counts=[sum(float(np.linalg.norm(np.asarray(p)-np.asarray(r['anchor'])))<=r['radius']+1e-8 for p in a['actual_bombs'])for r in layout['groups']]
  old_grouped=sum(n for n in old_counts if 2<=n<=3)
  cohorts.append(dict(step=layout['step'],owner=layout['owner'],candidate_counts=[r['physical_strict']for r in layout['groups']],baseline_counts=old_counts,candidate_small_groups=layout['valid_small_groups'],baseline_small_groups=sum(2<=n<=3 for n in old_counts),candidate_grouped=layout['grouped'],baseline_grouped=old_grouped,overfull=layout['overfull_groups'],groups=layout['groups']))
 good=[c for c in cohorts if c['candidate_small_groups']>=2 and c['overfull']==0]
 best=max(good,key=lambda c:(c['candidate_grouped']-c['baseline_grouped'],c['candidate_small_groups']))if good else None
 checks=dict(actual_two_small_corners=bool(good),all10=b['placed']==10,official_callbacks=a['official_callbacks']and b['official_callbacks'],finite=a['numeric_finite']and b['numeric_finite'],no_added_total_damage=sum(b['health_min'])>=sum(a['health_min']),actual_loop_under90=a['elapsed_seconds']<90 and b['elapsed_seconds']<90,submitted=sb['map_raw']is not None,map_loss_at_most_half_pp=sb['map_raw']is not None and sa['map_raw']is not None and sb['map_raw']>=sa['map_raw']-.5,wall_retained70=sb['wall_raw']>=.7*sa['wall_raw'],time_nonregress=sb['time_raw']>=sa['time_raw'],controllable_loss_within_wall_allowance=sb['controllable_subtotal']is not None and sa['controllable_subtotal']is not None and sb['controllable_subtotal']>=sa['controllable_subtotal']-(.2*.3*sa['wall_raw']+.25),actual_benefit=bool(best)and (best['candidate_grouped']>best['baseline_grouped']or sb['controllable_subtotal']>sa['controllable_subtotal']+1e-6))
 deltas={k:None if sa[k]is None or sb[k]is None else sb[k]-sa[k]for k in ['map_raw','wall_raw','time_raw','layout_raw','map_weighted','wall_weighted','time_weighted','layout_weighted','controllable_subtotal','full_red_score']}
 result=dict(status='PASS_AUTHOR_MULTI_CORNER_MECHANISM'if all(checks.values())else'STOP_FIRST_AUTHOR_MULTI_CORNER_GATE',checks=checks,baseline=sa,candidate=sb,deltas=deltas,baseline_placed=a['placed'],candidate_placed=b['placed'],baseline_steps=a['physics_steps'],candidate_steps=b['physics_steps'],baseline_health=a['health_min'],candidate_health=b['health_min'],cohorts=cohorts,best=best,native_rounds=0,automatic_five=False,automatic_native=False,scope='Same authored physical arena/seed, no BLUE: only controllable subtotal, not a full red score or five-map improvement.')
'''
runner=runner[:start]+replacement+runner[end:]
runner=runner.replace('import ast,datetime,hashlib,json,os,subprocess,time,traceback','import ast,datetime,hashlib,json,os,subprocess,time,traceback\nimport numpy as np')
(F/'run_small.py').write_text(runner,encoding='utf-8')
baseline=F.parent/'P156_fixed_quota_inner_corner/P48_ASTAR_SDK_FIRST.json'
pre=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),human_request='2 or3 bombs per separate corner, practice',min_corners=2,per_corner=[2,3],radius_in_blast_radii=1.,center_separation='2R+51.36 at CELL16',coverage_floor=.7,SDK_arms=['P161'],SDK_horizon=1600,author_seed=615,author_wall_rate=.05,baseline_not_repeated=True,baseline_path=str(baseline),baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),SDK_script_sha256=hashlib.sha256((F/'check_sdk_multi.py').read_bytes()).hexdigest(),candidate_manifest_sha256=hashlib.sha256((F/'CANDIDATE_MANIFEST_FIRST.json').read_bytes()).hexdigest(),pass_checks=['>=2 actual corners each2or3, no overfull selected corner','all10','map_loss<=.5pp','wall>=70% baseline','time_nonregress','total_health_nonregress','more_grouped_than_baseline_same_circles_or_controllable_gain','controllable_loss<=.2*.3*baseline_wall+.25'],native_rounds=0,automatic_native=False,automatic_five=False,formal_pilot_if_promising='separately freeze actual ZIP/ABI/SDK then one original Map02 RED+BLUE, raw audit; no automatic five',layout_and_full_red_score='not evaluated without BLUE')
(F/'PREDECLARATION_FIRST.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n')
print('Frozen multi-corner SDK script and small-test gates, old baseline not repeated')
