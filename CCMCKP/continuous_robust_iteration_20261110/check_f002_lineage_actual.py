"""Actual9 fixture branches: 7 completed I016 large runs and2 fresh small probes.

Small probes are audit engineering only, not formal1200 or30-run performance.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse,json,gzip,hashlib,pickle,subprocess,os,time
H=Path(__file__).resolve().parent;D=H/'research/F002_lineage_preflight';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def register():
 D.mkdir(exist_ok=True);cohort=json.load(open(H/'stability/I016_pair_cover_case39/REGISTRATION.json'));src=cohort['sources']['I016_pair_cover'];casebook=json.load(open(H/'CASES.json'));cases=[dict(casebook[i-1],seed=9716680+i) for i in [1,2]]
 for n in ['stability/I016_pair_cover_case39/INDEPENDENT_SEARCH_RAW_AUDIT.json','breadth/I016_priority_four/INDEPENDENT_SEARCH_RAW_AUDIT.json']:
  if not json.load(open(H/n))['passed']:raise RuntimeError('Whole actual original cohort audit required')
 inputs={n:sha(H/n) for n in ['f002_lineage.py','check_f002_lineage_actual.py','audit_i016_priority_breadth.py','independent_raw_recount.py','INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json']}
 r=dict(time=time.time(),scope=__doc__,source=src,cases=cases,budget=600,phase_seconds=180,watchdog_seconds=640,input_sha256=inputs)
 with (D/'REGISTRATION.json').open('x') as f:json.dump(r,f,indent=2)
 print(json.dumps(dict(registered=True,registration_sha256=sha(D/'REGISTRATION.json'),new_search_probes_launched=0)))
def run():
 reg=json.load(open(D/'REGISTRATION.json'));out=D/'ACTUAL_LINEAGE_CHECK.json'
 if out.exists():raise RuntimeError('Actual lineage check already complete')
 for n,d in reg['input_sha256'].items():
  if sha(H/n)!=d:raise RuntimeError('Registered audit fixture code changed')
 from f002_lineage import check
 from independent_raw_recount import verify
 S=H/reg['source']['candidate'];rows=[];smallraw={};bench=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark');fixtures=[]
 if {p.name:sha(p) for p in S.glob('*.py')}!=reg['source']['source_sha256']:raise RuntimeError('Frozen I016 source changed')
 for c in reg['cases']:
  file=D/('small_case'+str(c['index'])+'_seed'+str(c['seed'])+'.json.gz')
  if file.exists() or Path(str(file)+'.log').exists():raise RuntimeError('Probe may already run; do not repeat')
  with Path(str(file)+'.log').open('x') as log:p=subprocess.run(['/home/junhao/miniconda3/bin/python','-u',str(S/'run.py'),'--instance',str(bench/c['instance']),'--capacity',str(c['tmax']),'--seed',str(c['seed']),'--seconds','600','--phase-seconds','180','--risk-method','cdf_pair_cover','--out',str(file)],stdout=log,stderr=subprocess.STDOUT,timeout=640,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
  with Path(str(file)+'.terminal.json').open('x') as f:json.dump(dict(exit=p.returncode,scope='actual small audit engineering probe, not formal run'),f)
  if p.returncode:raise RuntimeError('Actual small probe failed; preserve and inspect')
  fixtures.append((file,None))
 for study in ['stability/I016_pair_cover_case39','breadth/I016_priority_four']:
  a=json.load(open(H/study/'INDEPENDENT_SEARCH_RAW_AUDIT.json'));proof=json.loads(gzip.decompress((H/a['raw_recounts_file']).read_bytes()));reg0=json.load(open(H/study/'REGISTRATION.json'));seen={(r.get('instance',reg0.get('instance')),F(str(r.get('capacity',reg0.get('capacity')))),tuple(r['selection']),r['bins'],r['numerator'],r['denominator']) for r in proof}
  fixtures.extend((H/p['result_file'],seen) for p in a['pools'] if p['label']=='I016_pair_cover')
 for file,seen in fixtures:
  data=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(str(file)+'.run.json'));P=bench/data['instance'];cost=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
  if meta['source_sha256']!=reg['source']['source_sha256'] or not meta['within_budget']:raise RuntimeError('Actual source/global budget mismatch')
  unique,report=check(data,cost,groups)
  if seen is not None:
   if any((k[0],F(str(k[1])),*k[2:]) not in seen for k in unique):raise RuntimeError('Reused branch adds certificate absent from independent whole-cohort recount')
  else:
   for candidate in data['candidate_shortlist']:
    key=(data['instance'],data['capacity'],tuple(candidate['selection']),candidate['certificate']['lower_numerator'],candidate['certificate']['denominator'])
    if key not in smallraw:smallraw[key]=verify(P,candidate['selection'],data['capacity'],candidate['certificate'])
  rows.append(dict(result_file=file.relative_to(H).as_posix(),result_sha256=sha(file),semantic_certificates=len(unique),independent_prior_large_recounts_matched=seen is not None,report=report))
 v=dict(passed=True,scope=__doc__,fixtures=len(rows),small_probes=2,complete_large_real_fixtures=7,small_semantic_certificates_independently_recounted=len(smallraw),registration_sha256=sha(D/'REGISTRATION.json'),lineage_source_sha256=sha(H/'f002_lineage.py'),new_original_MC_calls=0,no_formal_run_or_Avg_claim=True,rows=rows)
 with out.open('x') as f:json.dump(v,f,indent=2)
 print(json.dumps({k:x for k,x in v.items() if k!='rows'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['register','run'],required=True);a=p.parse_args();register() if a.phase=='register' else run()
