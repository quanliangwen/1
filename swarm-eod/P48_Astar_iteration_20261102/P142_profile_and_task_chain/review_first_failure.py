"""Post-freeze diagnosis of the first A* authored health regression, no rerun."""
from pathlib import Path
import hashlib
import json
import math

F=Path(__file__).resolve().parent
p=F/'BASELINE_FIRST.json'
d=json.loads(p.read_text(encoding='utf-8-sig'))
assert not(F/'HEALTH_REVIEW_FIRST.json').exists()
rows=d['rows']
first=next(r for r in rows if r['health']!=[50]*5)
step=first['step']
events=[]
for row in rows[max(0,step-8):step+2]:
    a,b=row['positions'][1],row['positions'][4]
    prev=rows[row['step']-2] if row['step']>1 else row
    va=[a[k]-prev['positions'][1][k] for k in range(2)]
    vb=[b[k]-prev['positions'][4][k] for k in range(2)]
    r=[b[k]-a[k] for k in range(2)]
    v=[vb[k]-va[k] for k in range(2)]
    vv=sum(x*x for x in v)
    tca=max(0.,min(4.,-sum(x*y for x,y in zip(r,v))/vv)) if vv>1e-12 else 0.
    events.append(dict(step=row['step'],health=[row['health'][i]for i in [1,4]],
                       pair_center_distance=math.hypot(*r),relative_speed=math.hypot(*v),
                       linear_tca_steps=tca,linear_closest_distance=math.hypot(*(r[k]+tca*v[k]for k in range(2))),
                       positions=[a,b],sampled_displacements=[va,vb],goals=[row['goals'][i]for i in [1,4]],
                       commands=[row['commands'][i]for i in [1,4]]))
tasks=[e for e in d['route_details'] if e['before']['owner'] in [1,4] and step-48<=e['before']['step']<=step]
out=dict(status='POST_FREEZE_FIRST_HEALTH_CHANGE',input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
         first_step=step,owners=[i for i,x in enumerate(first['health'])if x!=50],
         samples=events,nearby_planning_events=tasks,final_health=rows[-1]['health'],
         actual_completed=d['coverage_evaluation']['actual_bomb_count'],physics_steps=d['physics_steps'],
         cprofile_arm_started=False,native_rounds=0,
         limits=['Simultaneous health changes and small pair distance support a pair-interaction hypothesis; callback/substep contact identity was not logged.',
                 'Constant-velocity closest approach is an offline diagnostic only, not guaranteed future motion or a deployed rule.',
                 'No direct current lidar/semantic samples were retained at this encounter, so sensor invisibility/repulsion failure is not established.',
                 'No claim that A* caused damage relative to original P48; no paired original P48 rerun.'])
(F/'HEALTH_REVIEW_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(first_step=step,owners=out['owners'],samples=[{k:x[k]for k in ['step','pair_center_distance','linear_tca_steps','linear_closest_distance']}for x in events]),ensure_ascii=False))
