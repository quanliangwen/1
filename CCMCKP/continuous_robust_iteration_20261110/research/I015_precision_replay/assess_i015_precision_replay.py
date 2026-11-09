from pathlib import Path
import json,hashlib,gzip
H=Path(__file__).resolve().parent;D=H/'research/I015_precision_replay';out=D/'ASSESSMENT.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No replay assessment overwrite')
d=json.load(open(D/'RESULT.json'));reg=json.load(open(D/'REGISTRATION.json'));ind=json.load(open(H/'research/raw_precision/INDEPENDENT_I014_REFINED_RAW_RECHECK.json'));old=json.loads(gzip.decompress((H/'iterations/I014_hybrid_cdf_blocks/engineering39/result.json.gz').read_bytes()));source={p.name:sha(p) for p in (H/'iterations/I015_precision_closure/candidate').glob('*.py')};c=d['closure']
if d['registration_sha256']!=sha(D/'REGISTRATION.json') or d['source_sha256']!=source or reg['source_sha256']!=source or not c['phase_within_budget'] or c['budget_overrun'] or abs(d['available_seconds']-(180-old['extension']['extension_seconds']))>1e-9 or not d['not_cold_solver_performance'] or not d['uses_saved_vectors_for_external_replay_only']:raise RuntimeError('Replay scope, actual leftover budget or frozen source differs')
recounts={tuple(r['selection']):r for r in ind['rows']}
if not ind['passed'] or len(d['added_records'])!=2 or c['accepted']!=2 or c['refuted']!=1 or c['unresolved_remaining']!=1 or not c['all_initial_retained']:raise RuntimeError('Replay membership accounting differs')
for r in d['added_records']:
 proof=recounts[tuple(r['selection'])];cert=r['certificate']
 if cert['lower_numerator']!=proof['lower_numerator'] or cert['denominator']!=proof['denominator'] or cert['bins']!=proof['bins'] or 100*int(cert['lower_numerator'])<99*int(cert['denominator']) or abs(r['cost']-proof['cost'])>1e-9:raise RuntimeError('Recovered original raw certificate differs from independent recount')
result=dict(passed=True,scope='actual closure replay source/budget/membership verified against existing second-independent exact raw recounts; explicitly post-search saved vectors, NOT independent cold solver performance, new LSS or30-run Avg',available_seconds=d['available_seconds'],actual_closure_seconds=c['closure_seconds'],recovered_raw_points=2,raw_refuted=1,unresolved_remaining=1,all_original1017_retained=True,source_sha256=source,replay_sha256=sha(D/'RESULT.json'),independent_raw_recount_sha256=sha(H/'research/raw_precision/INDEPENDENT_I014_REFINED_RAW_RECHECK.json'),new_MC_calls=0)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))
