"""Static observer scope, actual local frozen payload hashes; zero SDK."""
from pathlib import Path
import ast,hashlib,json
F=Path(__file__).resolve().parent
assert not(F/'STATIC_CONTRACT_FIRST.json').exists()
p=F/'check_sdk_renderer_layers.py';text=p.read_text();tree=ast.parse(text)
parent=F.parent/'P142_profile_and_task_chain/check_sdk_astar_profile.py'
old=parent.read_text()
start=text.index('  for step in range(1,horizon+1):')
end=text.index(' if profile_mode=="ON":profiler.disable()',start)
oldstart=old.index('  for step in range(1,horizon+1):');oldend=old.index(' if profile_mode=="ON":profiler.disable()',oldstart)
freeze=text.index(' frozen_images=');layers=text.index(' frozen_layers=[]');truth=text.index(' truth=walls_only_grid(pg)')
tail=text[freeze:]
checks=dict(original_control_loop_byte_identical=text[start:end]==old[oldstart:oldend],
            original_all_control_steps_before_freeze=start<end<freeze<layers<truth,
            no_sensor_control_or_pgstep_after_freeze=all(token not in tail for token in ['.control(','.lidar_values(','.semantic_values(','.step(commands']),
            truth_not_read_by_layer_renderers='truth'not in text[layers:truth].replace('# All five layers fixed before any author truth/scoring call.',''),
            actual_full_image_identity_asserted="full_matches_original_frozen_image"in text,
            all_ndarray_identity_asserted="all_memory_arrays_identical"in text,
            proposed_layers_not_used_for_any_submission='submit_exploration_map'not in tail,
            parent_health_failure_preserved=json.loads((F/'PREDECLARATION_FIRST.json').read_text())['original_health_failure_not_rescued'],
            no_automatic_native_or_five=not json.loads((F/'PREDECLARATION_FIRST.json').read_text())['automatic_native'])
assert all(checks.values()),checks
base=Path('E:/codex/P48_astar_five_20261102')
manifest=json.loads((base/'CANDIDATE_MANIFEST.json').read_text(encoding='utf-8-sig'))
for n,h in manifest['payload_files'].items():assert hashlib.sha256((base/'versions/P48_ASTAR/source'/n).read_bytes()).hexdigest()==h
out=dict(status='PASS_POST_FREEZE_OBSERVER_SCOPE_AND_ORIGINAL_LOOP',checks=checks,
         parent_payloads_unchanged=len(manifest['payload_files']),sdk_frames=0,native_rounds=0,
         limitations=['AST checks do not prove runtime image equality; first actual replay still must match all rows/submissions/task/gate chains and memory array digests.'])
(F/'STATIC_CONTRACT_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
runner=F/'run_diagnostic.py';s=runner.read_text()
anchor="    pre=load(F/'PREDECLARATION_FIRST.json')\n"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"    binding=load(F/'LAUNCH_BINDING_FIRST.json')\n    assert all(hashlib.sha256((F/n).read_bytes()).hexdigest()==h for n,h in binding['script_sha256'].items())\n")
ast.parse(s);runner.write_bytes(s.encode())
bound=['run_diagnostic.py','check_sdk_renderer_layers.py','PREDECLARATION_FIRST.json','WORKSPACE_READY.json','STATIC_CONTRACT_FIRST.json']
(F/'LAUNCH_BINDING_FIRST.json').write_bytes((json.dumps(dict(script_sha256={n:hashlib.sha256((F/n).read_bytes()).hexdigest()for n in bound}),indent=2)+'\n').encode())
print(json.dumps(dict(status=out['status'],checks=len(checks),unchanged_payloads=len(manifest['payload_files']))))
