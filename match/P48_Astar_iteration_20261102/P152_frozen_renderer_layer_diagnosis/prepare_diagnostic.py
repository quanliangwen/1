"""Prepare one evidence replay: renderer layers ONLY AFTER all control is frozen."""
from pathlib import Path
import ast,hashlib,json
F=Path(__file__).resolve().parent
P=F.parent/'P142_profile_and_task_chain'
assert not(F/'check_sdk_renderer_layers.py').exists()
source=(P/'check_sdk_astar_profile.py').read_text()
source=source.replace('P142 frozen A* own-task-chain and optional read-only cProfile; authored physics only.',
                      'P152 frozen-output renderer-layer evidence only; identical original P48 A-star controller.')
anchor=' frozen_images=[d.memory.render().copy()for d in drones]\n'
assert source.count(anchor)==1
block=''' # No following controller/sensor/motion call may use these diagnostic images.
 from swarm_rescue.solutions.greedy_mapping import MapMemory
 from swarm_rescue.solutions.anchor_mapping import AnchoredMapMemory
 from swarm_rescue.solutions.frame_mapping import InferredFrameMemory
 from swarm_rescue.solutions.short_wall_support import add_short_wall_support
 from swarm_rescue.solutions.bearing_memory import BearingMemory
 frozen_layers=[];layer_integrity=[]
 def digest_arrays(mem):
  return {n:hashlib.sha256(v.tobytes()).hexdigest()for n,v in vars(mem).items()if isinstance(v,np.ndarray)}
 for owner,d in enumerate(drones):
  before=digest_arrays(d.memory)
  raw=MapMemory.render(d.memory).copy()
  anchored=AnchoredMapMemory.render(d.memory).copy()
  short=add_short_wall_support(d.memory,anchored,mode='box_dense',density=2).copy()
  frame=InferredFrameMemory.render(d.memory).copy()
  full=BearingMemory.render(d.memory).copy()
  layers=[('raw_support_reference_not_live_parent',raw),('anchored_actual_parent',anchored),
          ('compact_short_support_actual',short),('inferred_frame_actual',frame),('full_bearing_actual',full)]
  layer_integrity.append(dict(owner=owner,all_memory_arrays_identical=before==digest_arrays(d.memory),
                              full_matches_original_frozen_image=np.array_equal(full,frozen_images[owner])))
  frozen_layers.extend((owner,name,image)for name,image in layers)
 assert all(x['all_memory_arrays_identical']and x['full_matches_original_frozen_image']for x in layer_integrity)
 # All five layers fixed before any author truth/scoring call.
'''
source=source.replace(anchor,anchor+block)
anchor=' holds=[]\n'
assert source.count(anchor)==1
evaluation=''' renderer_layer_review=[]
 previous={}
 for owner,name,image in frozen_layers:
  score=scorer.score(truth,image,0.)
  prior=previous.get(owner)
  renderer_layer_review.append(dict(owner=owner,layer=name,score=float(score.score),breakdown=breakdown_to_dict(score),
   image_sha256=hashlib.sha256(image.tobytes()).hexdigest(),pixels=int(np.count_nonzero(image)),
   added_pixels_vs_previous=None if prior is None else int(np.count_nonzero((image>0)&(prior==0))),
   removed_pixels_vs_previous=None if prior is None else int(np.count_nonzero((image==0)&(prior>0)))))
  previous[owner]=image
  if owner==0:assert cv2.imwrite(str(F/(label+'_'+name+'.png')),image*255)
'''
source=source.replace(anchor,evaluation+anchor)
source=source.replace(' out=dict(profile_enabled=', ' out=dict(renderer_layer_review=renderer_layer_review,layer_integrity=layer_integrity,profile_enabled=')
ast.parse(source);(F/'check_sdk_renderer_layers.py').write_bytes(source.encode())
(F/'WORKSPACE_READY.json').write_bytes((P/'WORKSPACE_READY.json').read_bytes())
pre=dict(status='FROZEN_BEFORE_LAYER_EVIDENCE_REPLAY',code_sha256=hashlib.sha256((F/'check_sdk_renderer_layers.py').read_bytes()).hexdigest(),
         parent_failure_sha256=hashlib.sha256((P/'BASELINE_FIRST.json').read_bytes()).hexdigest(),
         maximum_arms=1,maximum_frames=800,case='cross_sdk',authored_seed=615,wall_rate=.05,
         purpose='After all actual commands/placements/submissions freeze, score exact renderer layers to distinguish measured line/short/frame/bearing precision loss. No mapper or policy modification.',
         mandatory_identity=['All original 779 frame rows/commands/health/map state hashes','Same submissions, actual map scores and task/gate chains',
                             'All own memory ndarray digests unchanged by post-freeze diagnostic calls; actual full output identical',
                             'No future control call sees author truth or any diagnostic score'],
         original_health_failure_not_rescued=True,performance_or_release_qualification=False,
         automatic_native=False,automatic_five=False,automatic_retry=False,native_rounds=0)
(F/'PREDECLARATION_FIRST.json').write_bytes((json.dumps(pre,ensure_ascii=False,indent=2)+'\n').encode())
runner=(F.parent/'P143_drive_encounter_evidence/run_diagnostic.py').read_text()
runner=runner.replace('P143_Astar_drive_encounter_evidence_20261102','P152_Astar_frozen_renderer_layers_20261102').replace('check_sdk_drive_evidence.py','check_sdk_renderer_layers.py').replace('DRIVE_EVIDENCE_FIRST','RENDERER_LAYERS_FIRST')
runner=runner.replace('RUNNING_READ_ONLY_FAILED_ENCOUNTER_PROVENANCE','RUNNING_POST_FREEZE_RENDERER_LAYER_EVIDENCE')
runner=runner.replace("actual_motor_returns=len(b['drive_evidence'])==30,\n                intended_scope=all(e['owner']in[1,4]and 332<=e['step']<=346 for e in b['drive_evidence']))", "layer_count=len(b['renderer_layer_review'])==25,\n                frozen_layer_integrity=all(e['all_memory_arrays_identical']and e['full_matches_original_frozen_image']for e in b['layer_integrity']))")
runner=runner.replace('PASS_FAILED_ENCOUNTER_PROVENANCE_IDENTITY','PASS_FROZEN_RENDERER_LAYER_IDENTITY')
runner=runner.replace("drive_evidence=b['drive_evidence']", "renderer_layer_review=b['renderer_layer_review'],layer_integrity=b['layer_integrity']")
runner=runner.replace("limitation='Not rescue of P142 failure, not a passing performance trial. Only own public motor inputs/locals; not actual substep contact identity.'", "limitation='Post-freeze authored output-layer ablation only. Original health failure retained; no whole-game improvement, candidate qualification or official-map cause claim.'")
runner=runner.replace("events=len(b['drive_evidence'])", "layers=len(b['renderer_layer_review'])")
ast.parse(runner);(F/'run_diagnostic.py').write_bytes(runner.encode())
print(json.dumps(dict(status=pre['status'],new_controller_files=0,new_SDK_files=0,maximum_cases=1,native_rounds=0)))
