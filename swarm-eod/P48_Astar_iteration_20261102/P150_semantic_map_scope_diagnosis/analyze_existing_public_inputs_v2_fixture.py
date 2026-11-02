"""Actual recorded public motor inputs only; no new SDK, no truth attribution."""
from pathlib import Path
import ast,copy,hashlib,json,types,math
import numpy as np
F=Path(__file__).resolve().parent
dest=F/'PUBLIC_INPUT_REVIEW_V2_FIXTURE_FIRST.json';assert not dest.exists()
parent=F.parent/'P143_drive_encounter_evidence/DRIVE_EVIDENCE_FIRST.json'
j=json.loads(parent.read_text())
source=Path('E:/codex/P48_astar_five_20261102/versions/P48_ASTAR/source/greedy_mapping.py')
tree=ast.parse(source.read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='MapMemory')
fn=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='semantic_mask'))
fn.decorator_list=[];g={'np':np,'math':math}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(source),'exec'),g)
records=[]
for e in j['drive_evidence']:
    loc=e['locals'];d=np.asarray(loc['distances'],float);a=np.asarray(loc['angles'],float)
    sem=[types.SimpleNamespace(distance=o['distance'],angle=o['angle'],entity_type=types.SimpleNamespace(name=o['kind']))for o in e['semantic']]
    original=g['semantic_mask'](d,a,sem,kinds=('DRONE',))
    usable=np.isfinite(d)&(d>8)&(d<220)
    angular=original.copy();wide=original.copy();drone_rays=0
    for o in sem:
        if o.entity_type.name!='DRONE':continue
        drone_rays+=1;diff=np.abs((a-o.angle+np.pi)%(2*np.pi)-np.pi)
        angular|=(diff<.10)
        wide|=(diff<.20)&(np.abs(d-o.distance)<24)
    records.append(dict(owner=e['owner'],step=e['step'],actual_semantic_drone_rays=drone_rays,
                        original_drone_mask_usable_rays=int(np.count_nonzero(original&usable)),
                        within_same_angular_tube_but_depth_gap24=int(np.count_nonzero(angular&usable&~original)),
                        hypothetical_extra_wide_tube_rays=int(np.count_nonzero(wide&usable&~original))))
# The fixed .10rad already exceeds half the nominal 35-ray full-FOV spacing.
half_spacing=np.pi/34
out=dict(status='RECORDED_PUBLIC_RAY_SCOPE_REVIEW_NO_POLICY_CHANGE',
         input_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),original_mask_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
         records=records,frames=len(records),half_nominal_35ray_spacing_rad=half_spacing,
         existing_mask_halfwidth_rad=.10,existing_width_covers_nominal_half_spacing=.10>=half_spacing,
         hypothetical_extra_rays=sum(r['hypothetical_extra_wide_tube_rays']for r in records),
         limits=['These are actual holonomic_drive return-local arrays; they are not a trace of mapper writes or entity labels for every lidar ray.',
                 'Semantic output is a list of classified surface rays, NOT one object centre per entity. There are no public entity IDs.',
                 'The wider .20 tube is a diagnostic counterfactual count only, not a candidate parameter or chosen threshold.',
                 'Extra/unmasked rays are not established drone ghosts; a real wall can be adjacent at similar range.',
                 'No map precision or whole-game score change is measured, no SDK/native frame executed.'],
         decision='Reject blindly enlarging the angular/centre-based mask. Need observation-specific classification or cross-view evidence before any mapper change.',
         sdk_frames=0,native_rounds=0)
dest.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=out['status'],frames=len(records),hypothetical_extra_rays=out['hypothetical_extra_rays'])))
