from pathlib import Path
import difflib,hashlib,json,zipfile
R=Path(__file__).resolve().parent
S=Path('E:/codex/S10_EGS_OA_20261123/source')
Z=Path('E:/CCMCKP/10.28/统一/S10_Cpp_Gurobi_Unified_Source.zip')
sha=lambda b:hashlib.sha256(b).hexdigest()
names=['evaluation.cpp','evaluation.hpp','report.cpp','report.hpp','model.cpp','model.hpp','rng.cpp','rng.hpp','normal.hpp','BENCHMARK_MANIFEST.json']
with zipfile.ZipFile(Z) as z:
    suffix=next(n for n in z.namelist() if n.endswith('evaluation.cpp'))
    prefix=suffix[:-len('evaluation.cpp')]
    files={n:z.read(prefix+n) for n in names}
    old_main=z.read(prefix+'main.cpp').decode('utf-8')
    old_search=z.read(prefix+'search.cpp').decode('utf-8')
def function(text,signature):
    text=text.replace('\r\n','\n')
    start=text.index(signature);opening=text.index('{',start);depth=0
    for i in range(opening,len(text)):
        if text[i]=='{':depth+=1
        elif text[i]=='}':
            depth-=1
            if not depth:return text[start:i+1]
    raise ValueError(signature)
critical=['Search::Search(','double Search::native_check(','double Search::accept(','void Search::final_check(']
function_results={k:{'same':function(old_search,k)==function((S/'search.cpp').read_text(),k),'sha256':sha(function(old_search,k).encode())} for k in critical}
comparisons={name:{'original_sha256':sha(files[name]),'candidate_sha256':sha((S/name).read_bytes()),'byte_identical':files[name]==(S/name).read_bytes()} for name in names}
assert all(x['byte_identical'] for x in comparisons.values()) and all(x['same'] for x in function_results.values())
new_main=(S/'main.cpp').read_text()
diff=''.join(difflib.unified_diff(old_main.splitlines(True),new_main.splitlines(True),fromfile='uploaded_S10/main.cpp',tofile='EGS/main.cpp'))
D=R/'delivery';D.mkdir(exist_ok=True)
(D/'MAIN_CPP_DIFF.txt').write_text(diff,encoding='utf-8')
result={'reference_archive':str(Z),'reference_archive_sha256':sha(Z.read_bytes()),'zip_prefix':prefix,
    'probability_and_input_files':comparisons,'search_acceptance_functions':function_results,
    'no_algorithm_execution_or_new_MC':True}
(D/'LOCAL_SOURCE_COMPARISON.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
remote='''from pathlib import Path
import hashlib,json
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP')
V=B/'work/egs_oa_validation_20261123';H=B/'work/egs_large_pilot_20261123'
assert Path.cwd().resolve()==B.resolve()
expected=EXPECTED
sources={}
for label,folder in [('compiled_baseline_source',V/'baseline'),('compiled_EGS_source',V/'source'),('trial_candidate_source',H/'candidate')]:
 rows={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in expected}
 assert rows==expected,label
 sources[label]=rows
P=json.loads((H/'PROTOCOL.json').read_text())
search_hashes=SEARCH_HASHES
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
'''.replace('EXPECTED',repr({name:sha(content) for name,content in files.items()})).replace('SEARCH_HASHES',repr({'baseline':{'search.cpp':sha(old_search.encode()),'main.cpp':sha(old_main.encode())},'candidate':{n:sha((S/n).read_bytes()) for n in ['search.cpp','main.cpp']}}))
(R/'check_server_remote.py').write_text(remote,encoding='utf-8')
print(json.dumps({'unchanged_probability_files':len(comparisons),'unchanged_search_acceptance_functions':len(critical),'original_zip_sha256':result['reference_archive_sha256']},ensure_ascii=False))
