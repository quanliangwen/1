from pathlib import Path
import hashlib,json
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP')
V=B/'work/egs_oa_validation_20261123';H=B/'work/egs_large_pilot_20261123'
assert Path.cwd().resolve()==B.resolve()
expected={'evaluation.cpp': '07a81ee3a1df0cdae4f9488fa2f0bdbea16108fc1445507b2564d0febc1a950c', 'evaluation.hpp': '2984b226bce88dfc9f656a93b03478f2cc0354186b0253add5371bb3b4198fd9', 'report.cpp': '575e4b942390e15ffd6d56a1e381798758c0863bbefa173a486ef542dc62ab25', 'report.hpp': '781a432462142157e7e88dfe5d00fb39c1ffe263850b534f61ffec6db59db889', 'model.cpp': 'eac2543909e8e23b5598e399fa9cd0f1b9889050fa1d9553a5f63fe6ae25b6b5', 'model.hpp': 'fa6f696fded659cc85b29cb4c57b29c0e2e2b2155d5ec5674a3740b6531bf664', 'rng.cpp': '711aeeed07d3a8169b68c23058dd93164975d61a6b3698b6cc5844a818837b35', 'rng.hpp': '525862681c037e39a187dc4307c014bd0ecf9d415548f78307a1d45f60864836', 'normal.hpp': 'c9c699dcbf0de8302b20e810b12420a3526401f8305a2f4f880cadeb016830b9', 'BENCHMARK_MANIFEST.json': '5461a20ccdb0b28d7dc6acffc0b6139a2f4c892ccc85e388bb53f8db5b98f89d'}
sources={}
for label,folder in [('compiled_baseline_source',V/'baseline'),('compiled_EGS_source',V/'source'),('trial_candidate_source',H/'candidate')]:
 rows={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in expected}
 assert rows==expected,label
 sources[label]=rows
P=json.loads((H/'PROTOCOL.json').read_text())
search_hashes={'baseline': {'search.cpp': '4843f75ffa7d3fe1c394891b13f5ff69eb496b1dd440b65bd4fbeaf428c45f6a', 'main.cpp': '9a6a24b8376febee9b026b0d3e4a368e76661d4d5dfa2edc6c58a4434627b117'}, 'candidate': {'search.cpp': '9a7af6de1da87258e80ca3b1f8a243e78c0be473ae388e54363f7238d015d75b', 'main.cpp': 'd46a49b5262bedec6411cd5b2debaf926fa815be6518ff6739875d9f3d5109f2'}}
for label,folder in [('baseline',V/'baseline'),('candidate',V/'source'),('candidate',H/'candidate')]:
 for name in ['search.cpp','main.cpp']:
  assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==search_hashes[label][name]
binaries={}
for label,trial,build in [('S10',H/'bin/baseline',V/'baseline_build/ccmckp_s10'),('EGS',H/'bin/candidate',V/'build/ccmckp_s10')]:
 digest=hashlib.sha256(trial.read_bytes()).hexdigest()
 assert digest==hashlib.sha256(build.read_bytes()).hexdigest()
 assert digest==P['source_and_binary_pins']['bin/'+('baseline' if label=='S10' else 'candidate')]
 binaries[label]=digest
assert (H/'COMPLETED.json').exists()
print(json.dumps({'status':'PASS','sources':sources,'search_main_hashes':search_hashes,'binaries':binaries,'protocol_sha256':hashlib.sha256((H/'PROTOCOL.json').read_bytes()).hexdigest(),'all_270_source_input_pins_unchanged':json.loads((H/'COMPLETED.json').read_text())['all_source_and_input_pins_unchanged'],'read_only':True}))
