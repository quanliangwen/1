from pathlib import Path
import ast
import hashlib
import json

F = Path(__file__).resolve().parent
parent = Path('E:/codex/PJ01_rule_refinement_20261102/P137_P35_sensed_placement_constraints/check_sdk_sensed_placement.py')
source = parent.read_text(encoding='utf-8-sig')
tree = ast.parse(source)
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MyDroneEval')
lines = source.splitlines(keepends=True)
for node in sorted([n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('_placement_forbidden', '_point_conflicts_with_drop')], key=lambda n: n.lineno, reverse=True):
    del lines[node.lineno-1:node.end_lineno]
source = ''.join(lines)
assert 'sensed_placement_constraints' not in source
source = source.replace('"""P137 sensed placement constraint, real original SDK5body mechanisms."""',
                        '"""P142 frozen A* own-task-chain and optional read-only cProfile; authored physics only."""')
old = 'label,arm,case,horizon,wall_rate=sys.argv[1:];'
assert source.count(old) == 1
source = source.replace(old, 'label,arm,case,horizon,wall_rate,profile_mode=sys.argv[1:];')
source = source.replace('TRACE_ENABLED=False', 'TRACE_ENABLED=True')
source = source.replace('import cv2\n', 'import cv2\nimport cProfile,pstats\n')
anchor = ' with contextlib.redirect_stdout(io.StringIO()):\n  for step in range(1,horizon+1):'
assert source.count(anchor) == 1
source = source.replace(anchor, ' profiler=cProfile.Profile()\n if profile_mode=="ON":profiler.enable()\n' + anchor)
anchor = ' elapsed=time.monotonic()-start\n'
assert source.count(anchor) == 1
source = source.replace(anchor, ' if profile_mode=="ON":profiler.disable()\n' + anchor + ''' profile_rows=[]
 if profile_mode=="ON":
  for (file,line,name),(primitive,total,exclusive,cumulative,callers) in pstats.Stats(profiler).stats.items():
   profile_rows.append(dict(file=file,line=line,name=name,primitive_calls=primitive,calls=total,exclusive_seconds=exclusive,cumulative_seconds=cumulative))
  profile_rows.sort(key=lambda r:r['exclusive_seconds'],reverse=True)
''')
anchor = " out=dict(semantic_plan_events="
assert source.count(anchor) == 1
source = source.replace(anchor, ' out=dict(profile_enabled=profile_mode=="ON",profile_rows=profile_rows,semantic_plan_events=')
ast.parse(source)
dest = F/'check_sdk_astar_profile.py'
assert not dest.exists()
dest.write_bytes(source.encode('utf-8'))
base = json.loads(Path('E:/codex/P48_astar_five_20261102/WORKSPACE_READY.json').read_text(encoding='utf-8-sig'))
(F/'WORKSPACE_READY.json').write_bytes((json.dumps(base,indent=2)+'\n').encode())
pre = dict(status='FROZEN_BEFORE_FIRST_FRAME', base='P48_ASTAR',
           base_archive_sha256='7fdac2836596f050353dc6d6e1fff3f084b5f16eb25af7cf0e62c551cfcc810d',
           maximum_cases=1, maximum_arms=2, maximum_frames_per_arm=800,
           authored_case='cross_sdk', authored_seed=615, authored_wall_rate=.05,
           code_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
           inherited_harness_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
           observer='Read-only task snapshots in both arms; cProfile only in ON arm. No candidate/controller/SDK source edits.',
           gates=['All original health/finite/callback/inventory checks in each arm',
                  'All per-frame actions/poses/map-state hashes/inventory/health equal between arms',
                  'All five final rendered map scores and submitted image SHA equal',
                  'Control gate/assignment/commitment chains identical, ignoring timings',
                  'First real error stops chain; no automatic retry/native/five'],
           evaluation='Author truth only after all outputs freeze. Not official Map04 reproduction or tournament score.',
           native_rounds=0, automatic_native=False, automatic_five=False)
(F/'PREDECLARATION_FIRST.json').write_bytes((json.dumps(pre,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status='BUILT_READ_ONLY_DIAGNOSTIC',sha256=pre['code_sha256'])))
