"""Review post-control recording replay, never rescue original qualification."""
from pathlib import Path
import json,math
F=Path(__file__).resolve().parent;Q=F/'recording_recovery';read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not(F/'RECORDED_SCORE_REVIEW_FIRST.json').exists()
record=read(Q/'RECORDING_REVIEW_FIRST.json');assert record['status']=='PASS_AVAILABLE_ORIGINAL_RECORDS_MATCH'
original_error=read(F/'FIRST_ERROR.json');a=read(F.parent/'P156_fixed_quota_inner_corner/P48_ASTAR_SDK_FIRST.json');b=read(Q/'P159_SDK_FIRST.json')
assert b['source_sha256']==read(F/'CANDIDATE_MANIFEST_V2.json')['candidate_files']
cluster=max((x['physical_strict']for x in b['concentration']),default=0);sa,sb=a['scores'],b['scores']
checks=dict(actual_cluster6=cluster>=6,all10=b['placed']==10,map_loss_at_most_half_pp=sb['map_raw']is not None and sb['map_raw']>=sa['map_raw']-.5,wall_retained70=sb['wall_raw']>=.7*sa['wall_raw'],time_nonregress=sb['time_raw']>=sa['time_raw'],no_added_total_damage=sum(b['health_min'])>=sum(a['health_min']),actual_loop_under90=b['elapsed_seconds']<90,available_original_logs_match=all(record['checks'].values()))
result=dict(status='RECORDED_AUTHOR_MECHANISM_REJECTED'if not all(checks.values())else'RECORDED_AUTHOR_MECHANISM_ONLY_NO_QUALIFICATION',checks=checks,baseline=sa,candidate=sb,baseline_steps=a['physics_steps'],candidate_steps=b['physics_steps'],baseline_placed=a['placed'],candidate_placed=b['placed'],baseline_health=a['health_min'],candidate_health=b['health_min'],actual_max_cluster=cluster,concentration=b['concentration'],new_native_rounds=0,automatic_native=False,automatic_five=False,qualification_rescued=False,first_recording_error_preserved=True,score_source='Post-control recording replay; matching all available original plans/placement/model logs, not full missing original frame identity or additional performance sample',original_error=original_error)
(F/'RECORDED_SCORE_REVIEW_FIRST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],checks=checks,scores=sb,cluster=cluster)))
