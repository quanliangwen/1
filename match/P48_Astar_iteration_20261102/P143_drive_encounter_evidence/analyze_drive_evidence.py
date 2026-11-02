from pathlib import Path
import json
import math

F=Path(__file__).resolve().parent
p=F/'RESULT_FIRST.json'
data=json.loads(p.read_text(encoding='utf-8-sig'))
assert data['status']=='PASS_FAILED_ENCOUNTER_PROVENANCE_IDENTITY', 'Do not interpret an unmatched replay'
assert not(F/'MOTOR_REVIEW_FIRST.json').exists()
rows=[]
for event in data['drive_evidence']:
    loc=event['locals']
    drones=[s for s in event['semantic']if s['kind']=='DRONE']
    near=min(drones,key=lambda s:s['distance']) if drones else None
    match=[]
    if near is not None:
        for k,angle in enumerate(loc['angles']):
            delta=abs((angle-near['angle']+math.pi)%(2*math.pi)-math.pi)
            if delta<.1 and abs(loc['distances'][k]-near['distance'])<24:
                match.append(k)
    rows.append(dict(owner=event['owner'],step=event['step'],nearest_public_drone=near,
                     matching_public_ray_count=len(match),matching_rays_in_target_tube=sum(bool(loc['in_tube'][k])for k in match),
                     matching_close_repulsion_rays=sum(bool(loc['close'][k])for k in match),
                     corridor=loc.get('corridor'),speed=loc.get('speed'),measured_velocity=loc.get('velocity'),
                     measured_speed=math.hypot(*loc['velocity']),desired_velocity=loc.get('desired_velocity'),
                     command_norm=math.hypot(event['returning_command']['forward'],event['returning_command']['lateral']),
                     acceleration=loc.get('acceleration'),target=loc.get('target')))
out=dict(status='REVIEWED_IDENTICAL_DRIVE_INPUTS',rows=rows,original_health_failure_preserved=True,native_rounds=0,
         limits=['Nearest semantic DRONE has no proven peer identity. Matching rays use the old public angular/range band as a diagnostic, not a new mask.',
                 'Target tube and close-repulsion statistics are actual return locals from the unchanged motor.',
                 'No future motion, contact substep, or performance improvement is proved.'])
(F/'MOTOR_REVIEW_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps([r for r in rows if r['step']in[336,339,341,343,344]],ensure_ascii=False))
