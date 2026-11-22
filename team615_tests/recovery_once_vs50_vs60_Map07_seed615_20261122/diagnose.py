"""Inspect captured public sensors only; no controller or physics replay."""
from pathlib import Path
from types import SimpleNamespace as NS
import importlib.util,json,math
import numpy as np
r=Path(__file__).resolve().parent
events=[json.loads(s) for s in (r/'Map07/received/placement_events.jsonl').read_text(encoding='utf8').splitlines()]
e=next(e for e in events if e['drone']==4 and e['event']=='recovery_started')
src=r.parent/'team615_first_drop_recovery_once_20261122/candidate/drop_departure.py'
spec=importlib.util.spec_from_file_location('frozen_departure',src);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
x=m.DropDeparture();scan=e['prior_scan']
x.before_drop_scan=(scan[0],np.array(scan[1]),np.array(scan[2]),np.array(scan[3]))
d=NS(pose=np.array(e['pose']),heading=0.)
first=np.array(e['first_point']);base=math.atan2(*(d.pose-first)[::-1]);rows=[]
for turn in (0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8):
    direction=base+turn*math.pi/8;goal=d.pose+36*x.vector(direction)
    rows.append(dict(turn=turn,world_direction=direction,goal=goal.tolist(),
        minimum_separation_met=bool(np.linalg.norm(goal-first)>=36.),
        pre_drop_tube_free=x._prior_free(d,direction,36.)))
a=np.asarray(e['angles']);values=np.asarray(e['lidar']);cone=math.atan2(23.,36.)
boundaries=np.sort(np.r_[(a-cone)%(2*np.pi),(a+cone)%(2*np.pi)])
probes=np.r_[boundaries,(boundaries+np.diff(np.r_[boundaries,boundaries[0]+2*np.pi])/2)%(2*np.pi)]
fractions=[]
for direction in probes:
    forecast=np.abs((a-direction+np.pi)%(2*np.pi)-np.pi)<cone
    fractions.append(np.count_nonzero(forecast & np.isfinite(values) & (values>0))/np.count_nonzero(forecast))
assert max(fractions)<.9
result=dict(step=e['step'],scan_step=scan[0],
    analysis='Pure _prior_free on captured pre-drop scan and position. Heading zero encodes world directions, not an assumed compass reading; live validity proof checks every angular membership-change boundary and interval midpoint and is independent of actual heading.',
    rows=rows,prior_and_separation_passes=sum(x['pre_drop_tube_free'] and x['minimum_separation_met'] for x in rows),
    current_rays=dict(total=len(values),positive_finite=int(np.count_nonzero(np.isfinite(values)&(values>0))),
        nonpositive_finite=int(np.count_nonzero(np.isfinite(values)&(values<=0))),minimum=float(values.min()),maximum=float(values.max()),
        semantic_kinds={'BOMB':len(e['semantic'])},minimum_required_forecast_valid_fraction=.9,
        maximum_forecast_valid_fraction_any_direction=float(max(fractions)),
        first_live_gate_fails_for_every_direction=True),new_matches=0,physics_steps=0)
(r/'PRIOR_TUBE_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
