"""One bounded negative check on already frozen own motor inputs; no SDK."""
from pathlib import Path
import hashlib
import json
import math

F=Path(__file__).resolve().parent
p=F.parent/'P143_drive_encounter_evidence/RESULT_FIRST.json'
d=json.loads(p.read_text(encoding='utf-8-sig'))
assert d['status']=='PASS_FAILED_ENCOUNTER_PROVENANCE_IDENTITY'
assert not(F/'RESULT_FIRST.json').exists()
rows=[]
for e in d['drive_evidence']:
    v=e['locals']
    vx,vy=v['velocity']
    speed=math.hypot(vx,vy)
    if speed<1e-9:continue
    heading=v['heading']
    cosine=[math.cos(heading+a)*vx/speed+math.sin(heading+a)*vy/speed for a in v['angles']]
    lateral=[dist*math.sqrt(max(0.,1-proj*proj))for dist,proj in zip(v['distances'],cosine)]
    tube=[bool(valid and proj>0 and side<23)for valid,proj,side in zip(v['finite'],cosine,lateral)]
    near=min([x for x in e['semantic']if x['kind']=='DRONE'],key=lambda x:x['distance'],default=None)
    matches=[]
    if near:
        matches=[k for k,a in enumerate(v['angles'])if abs((a-near['angle']+math.pi)%(2*math.pi)-math.pi)<.1 and abs(v['distances'][k]-near['distance'])<24]
    rows.append(dict(owner=e['owner'],step=e['step'],speed=speed,
                     current_target_tube_matches=sum(bool(v['in_tube'][k])for k in matches),
                     momentum_tube_matches=sum(tube[k]for k in matches),
                     nearest_semantic=near,momentum_corridor=min([v['distances'][k]*cosine[k]for k in range(len(tube))if tube[k]],default=300.)))
witness=[r for r in rows if r['owner']==1 and r['step']==339]
assert len(witness)==1
result=dict(status='REJECT_MOMENTUM_TUBE_AS_SUFFICIENT_FIX'if witness[0]['momentum_tube_matches']==0 else'REQUIRES_FURTHER_ANALYSIS',
            input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),rows=rows,witness=witness[0],
            hypothesis='Adding the same 23px static ray tube along measured own velocity should detect the crossing peer earlier.',
            conclusion='At step339 owner1 still has zero nearest-DRONE matching rays in that momentum tube. This simple addition alone does not establish early crossing detection.',
            limitations=['No candidate action replay, multi-step guarantee, peer identity, or score change inferred.','This does not reject all inertial or relative-velocity methods.'],
            sdk_frames=0,native_rounds=0,candidate_modified=False)
(F/'RESULT_FIRST.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=result['status'],witness=result['witness'])))
