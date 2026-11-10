"""Freeze I016 formal40x30 only after both complete development comparisons."""
from pathlib import Path
import json,time,hashlib,os
H=Path(__file__).resolve().parent;F=H/'formal/F002_I016_40x30';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def register():
 prerequisites=['research/D005_I016_pair_prefix/INDEPENDENT_FINAL_AUDIT.json','research/D005_I016_pair_prefix/DEVELOPMENT_COMPARISON.json','research/D006_I016_breadth_prefix/INDEPENDENT_FINAL_AUDIT.json','research/D006_I016_breadth_prefix/DEVELOPMENT_COMPARISON.json']
 if not all((H/n).exists() for n in prerequisites):
  print(json.dumps(dict(ready=False,scope='F002 formal registration',reason='both whole registered native comparisons still required',searches_launched=0)));return
 if (F/'REGISTRATION.json').exists():raise RuntimeError('F002 already registered; inspect actual state')
 p=json.load(open(H/prerequisites[1]));b=json.load(open(H/prerequisites[3]));prior=json.load(open(H/'formal/F001_I002_40x30/FINAL_AUDIT_STATS.json'));old={r['index']:r for r in prior['summary']};new=p['summaries']['I016_pair_cover'];parent=p['summaries']['I015_parent']
 if not all(json.load(open(H/prerequisites[i]))['passed'] for i in [0,2]) or p['all_original_attempts_qualified']!=6 or b['all_original_attempts_qualified']!=8:raise RuntimeError('Actual whole6/8 qualification required')
 eligibility=dict(new_39_Avg=new['Avg'],parent_39_Avg=parent['Avg'],new_39_gap=new['Avg_minus_own_Best'],parent_39_gap=parent['Avg_minus_own_Best'],priority_rows=b['paired_rows'])
 if new['runs']!=3 or new['Avg']>=old[39]['avg']-1e-8 or new['Avg_minus_own_Best']>parent['Avg_minus_own_Best']+1e-8 or new['Std_population']>parent['Std_population']+1e-8:raise RuntimeError('Current complete stability evidence does not justify promotion')
 if {r['index'] for r in b['paired_rows']}!={35,37,38,40} or any(r['new_cost']>old[r['index']]['avg']+1e-8 for r in b['paired_rows']):raise RuntimeError('Priority cases worse than prior qualified formal Avg: analyze before promotion')
 cohort=json.load(open(H/'stability/I016_pair_cover_case39/REGISTRATION.json'));src=cohort['sources']['I016_pair_cover'];S=H/src['candidate']
 if {p.name:sha(p) for p in S.glob('*.py')}!=src['source_sha256']:raise RuntimeError('Qualified frozen optimizer changed')
 seeds=list(range(9717001,9717031));checked=0
 for folder in ['stability','breadth','iterations','formal']:
  for file in (H/folder).rglob('*.run.json'):
   meta=json.load(open(file));checked+=1
   if meta.get('seed') in seeds:raise RuntimeError('Formal seed already used: '+str(file))
 cases=json.load(open(H/'CASES.json'));raw=json.load(open(H/'RAW_REFERENCE.json'));rawids={};bench='/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark'
 if len(cases)!=40 or [r['index'] for r in cases]!=list(range(1,41)):raise RuntimeError('Exactly40 benchmark cases required')
 for c in cases:
  P=Path(bench)/c['instance']
  for file in [P/'cost.txt',P/'node_to_factor.pkl']+[p for p in P.glob('*_sample.txt') if not p.name.endswith('_big_sample.txt')]:
   digest=sha(file)
   if raw[str(file)]!=digest:raise RuntimeError('Original input changed')
   rawids[str(file)]=digest
 memory={l.split(':')[0]:int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')}
 if len(os.sched_getaffinity(0))<16 or memory['MemAvailable']<32*1024*1024:raise RuntimeError('Insufficient formal scheduling resources')
 drivers=['run_f002_search.py','launch_f002_search.py'];vendor={p.relative_to(H).as_posix():sha(p) for p in (S.parent/'vendor313').rglob('*.py')}
 reg=dict(time=time.time(),stage='frozen I016 formal40cases x30 fresh searches; no final performance claim',candidate=src['candidate'],source_sha256=src['source_sha256'],vendor_sha256=vendor,driver_sha256={n:sha(H/n) for n in drivers},eligibility=eligibility,eligibility_proof_sha256={n:sha(H/n) for n in prerequisites},benchmark=bench,cases=list(range(1,41)),methods=['cdf_pair_cover'],seeds=seeds,runs=1200,search_seconds=600,phase_seconds=180,watchdog_seconds=640,search_workers=16,large_case_workers=4,large_case_definition='m>=30',validation_workers=4,raw_input_sha256=rawids,prior_run_metadata_checked_for_fresh_seeds=checked,resources=dict(cpus=len(os.sched_getaffinity(0)),available_memory_kib=memory['MemAvailable']),acceptance='all original samples strictsum<T integerlower>=.99 plus unchanged originalfullLSS10m seed832273 sum<=T point>=.985; no tail gate',search_feedback='no true parameters, historical vectors, targets or validation cache access; worker audit-hook unchanged',failure_policy='all1200 registered attempts retained; no replacement or automatic restart; errors/timeouts/budget failures reported, incomplete qualification never averaged over success subset',validation_stage='after all1200 searches freeze, independent raw/source/input/lineage audit; then separately register and remotely verify native protocol/catalogue before original MC; this search controller performs no MC',statistics='Best/Avg/Std.P only over all30 jointlyqualified protocolvalid attempts percase; ownBest gap and oldBest gap; search/logical validation/new physical and speculative costs separately',continued_goal_active=True)
 F.mkdir(exist_ok=True)
 reg['casebook_sha256']=sha(H/'CASES.json')
 with (F/'REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
 print(json.dumps(dict(ready=True,registration_sha256=sha(F/'REGISTRATION.json'),runs=1200,source_files=len(src['source_sha256']),raw_files=len(rawids),vendor_py_files=len(vendor),searches_launched=0)))

if __name__=='__main__':register()
