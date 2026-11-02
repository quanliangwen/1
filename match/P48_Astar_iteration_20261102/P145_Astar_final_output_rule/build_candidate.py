"""Adapt the single historical output rule to the frozen A* base, no new heuristic."""
from pathlib import Path
import ast
import hashlib
import json

F=Path(__file__).resolve().parent
BASE=Path('E:/codex/P48_astar_five_20261102')
OLD=Path('E:/codex/PJ01_rule_refinement_20261102/P125_P35_cross_source_output/candidate_project/src/swarm_rescue/solutions')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((BASE/'CANDIDATE_MANIFEST.json').read_text(encoding='utf-8-sig'))
source=BASE/'versions/P48_ASTAR/source'
project=F/'candidate_project'
assert not project.exists()
sol=project/'src/swarm_rescue/solutions'
sol.mkdir(parents=True)
files={}
for name,expected in baseline['payload_files'].items():
    src=source/name
    assert sha(src)==expected,(name,'Frozen A* input changed')
    target=project/'req.txt' if name=='req.txt' else sol/name
    target.write_bytes(src.read_bytes())
for name in ['free_bearing_support.py','free_bearing_output.py']:
    (sol/name).write_bytes((OLD/name).read_bytes())
entry=sol/'my_drone_eval.py'
text=entry.read_text(encoding='utf-8-sig')
assert text.count('class MyDroneEval(FreshOpportunityAuditMixin,')==1
text='from swarm_rescue.solutions.free_bearing_output import CrossSourceFreeOutputMixin\n'+text
text=text.replace('class MyDroneEval(FreshOpportunityAuditMixin,','class MyDroneEval(CrossSourceFreeOutputMixin,FreshOpportunityAuditMixin,')
ast.parse(text)
entry.write_bytes(text.encode())
for p in project.rglob('*'):
    if p.is_file():
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'))
        files[p.relative_to(project).as_posix()]=sha(p)
changes=[]
for name,expected in baseline['payload_files'].items():
    target=project/'req.txt' if name=='req.txt' else sol/name
    if sha(target)!=expected:changes.append(name)
assert changes==['my_drone_eval.py'] or set(changes)=={'my_drone_eval.py'}
assert sha(sol/'free_bearing_support.py')==sha(OLD/'free_bearing_support.py')
assert sha(sol/'free_bearing_output.py')==sha(OLD/'free_bearing_output.py')
manifest=dict(status='INDEPENDENT_ASTARA_OUTPUT_RULE_NOT_YET_SDK_TESTED',
              rule='Single historical P125 final-output consistency rule on a new A* base; not claimed as a new mechanism or inheritance of historical performance qualification.',
              base_archive_sha256=baseline['sha256'],candidate_files=files,changed_parent_files=changes,
              added_files=['free_bearing_support.py','free_bearing_output.py'],
              helper_source_sha256=sha(sol/'free_bearing_support.py'),wrapper_source_sha256=sha(sol/'free_bearing_output.py'),
              unchanged=['All A* search modules','exploration and task decisions','raw navigation/bearing/render memory','placement','motion','req','SDK'],
              contest_release=False,native_rounds=0)
(F/'CANDIDATE_MANIFEST_FIRST.json').write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())

parent=F.parent/'P142_profile_and_task_chain'
text=(parent/'check_sdk_astar_profile.py').read_text(encoding='utf-8-sig')
text=text.replace('P142 frozen A* own-task-chain and optional read-only cProfile; authored physics only.',
                  'P145 A* single historical final-output rule; authored physical control is compared with preserved A* parent.')
text=text.replace("diagnostics=getattr(self,'last_observed_fragment_audit',{})", "diagnostics=getattr(self,'last_free_support_output_audit',{})")
anchor=' truth=walls_only_grid(pg);scorer=MapExplorationScorer()'
assert text.count(anchor)==1
text=text.replace(anchor, ''' # All parent/filtered outputs freeze before evaluator-only authored truth.
 from swarm_rescue.solutions.free_bearing_output import complete_free_supported_output
 filtered_outputs=[]
 for drone,image in zip(drones,frozen_images):
  filtered,audit=complete_free_supported_output(drone.memory,image,int(drone.elapsed_timestep))
  filtered_outputs.append((filtered.copy(),audit))
'''+anchor)
anchor=' out=dict(profile_enabled='
assert text.count(anchor)==1
text=text.replace(anchor, ''' filtered_map_results=[]
 for i,(filtered,audit) in enumerate(filtered_outputs):
  breakdown=scorer.score(truth,filtered,0.)
  filtered_map_results.append(dict(owner=i,score=breakdown.score,breakdown=breakdown_to_dict(breakdown),audit=audit,sha256=hashlib.sha256(filtered.tobytes()).hexdigest()))
 out=dict(filtered_map_results=filtered_map_results,profile_enabled=''')
ast.parse(text)
(F/'check_sdk_output_rule.py').write_bytes(text.encode())
workspace=json.loads((BASE/'WORKSPACE_READY.json').read_text(encoding='utf-8-sig'))['versions']['P48_ASTAR']
(F/'BASE_WORKSPACE.json').write_bytes((json.dumps(workspace,indent=2)+'\n').encode())
pre=dict(status='FROZEN_BEFORE_FIRST_CANDIDATE_FRAME',
         code_sha256=sha(F/'check_sdk_output_rule.py'),manifest_sha256=sha(F/'CANDIDATE_MANIFEST_FIRST.json'),
         parent_result=str(parent/'BASELINE_FIRST.json'),parent_result_sha256=sha(parent/'BASELINE_FIRST.json'),
         cases=[dict(label='CROSS_OUTPUT_FIRST',case='cross_sdk',horizon=800,wall_rate=.05)],maximum_cases=1,
         gates=['All complete frame rows, task/gate chains and original raw map scores identical to retained A* parent',
                'Original health failure must be preserved, not reclassified as health-safe: no added damage and no rescue run',
                'All10, actual original SDK callbacks, finite commands/inventory and loop<90s',
                'Actual submitted map >= parent+0.25 percentage points',
                'All five counterfactual final maps and true surface credit >= original corresponding maps',
                'Actual output COMPLETE/erased>0/raw and parent preserved/helper<=0.5sec',
                'All filtered outputs frozen before author truth read; failed gate stops without tuning/retry'],
         qualification_limit='Parent authored collision remains unresolved. Output-only adaptation does not demonstrate collision repair or a new health-safe controller.',
         native_rounds=0,automatic_native=False,automatic_five=False,official_release=False)
(F/'PREDECLARATION_FIRST.json').write_bytes((json.dumps(pre,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(files=len(files),changes=changes,helper_sha=manifest['helper_source_sha256'])))
