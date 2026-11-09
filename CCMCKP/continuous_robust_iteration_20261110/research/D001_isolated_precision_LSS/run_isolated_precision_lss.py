"""Private original-LSS receipts only; never opens shared formal/cache records."""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib,time,subprocess,pickle,os
H=Path(__file__).resolve().parent;D=H/'research/D001_isolated_precision_LSS';reg=json.load(open(D/'REGISTRATION.json'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out=D/'RESULT.json';state=D/'STATE.json';C=D/'receipts';C.mkdir(exist_ok=True)
if out.exists() or (D/'FINISHED').exists() or any(C.iterdir()):raise RuntimeError('Isolated study may already have run; never repeat automatically')
def identities():
 for n,digest in reg['source_sha256'].items():
  if sha(H/n)!=digest:raise RuntimeError('Registered original-native study driver changed')
 for n,digest in reg['input_sha256'].items():
  if sha(H/n)!=digest:raise RuntimeError('Registered study evidence/reference changed')
identities();reference=json.load(open(H/'REFERENCE_SHA256.json'));dist=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256']
for r in reference['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original LSS source changed')
started=time.monotonic();rows=[]
for task in reg['tasks']:
 identity=task['identity'];key=task['key'];file=C/(key+'.json');log=C/(key+'.log');error=None;v=None;tick=time.monotonic();state.write_text(json.dumps(dict(stage='original_native_private_receipt',done=len(rows),required=6,index=task['index'],cost=task['cost'],key=key,time=time.time()),indent=2))
 try:
  identities();P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/identity['instance'];q=identity['selection'];raw=task['raw_certificate'];costs=[F(s) for s in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
  if len(q)!=len(groups) or any(j not in groups[g] for g,j in enumerate(q)) or 100*int(raw['lower_numerator'])<99*int(raw['denominator']) or abs(float(sum((costs[j] for j in q),F(0)))-task['cost'])>1e-9:raise RuntimeError('Canonical original-raw99/price differs')
  for name,digest in raw['input_sha256'].items():
   if sha(P/name)!=digest:raise RuntimeError('Independently certified raw data changed')
  # Explicit absolute private output path. Original evaluator only reads original
  # reference modules/distributions and writes this path; no shared cache helper.
  with log.open('x') as f:r=subprocess.run(['python3','-u',str(H/'native_lss_eval.py'),'--instance',str(P),'--capacity',str(identity['capacity']),'--selection',json.dumps(q),'--seed','832273','--out',str(file.resolve())],cwd=H,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=f,stderr=subprocess.STDOUT,timeout=reg['watchdog_per_call'])
  if r.returncode:raise RuntimeError('Original LSS subprocess failed '+str(r.returncode))
  v=json.load(open(file))
  if any(v[k]!=x for k,x in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1' or v['passed']!=(v['real_probability']>=.985) or v['search_feedback'] or v['role']!='external_validation_and_postselection' or not all(v[k] for k in ['original_full_module','original_sources_unmodified','aliases_only']):raise RuntimeError('Original native identity/source/environment/role differs')
  if set(v['distribution_sha256'])!={str(j)+'_dist.txt' for j in q}:raise RuntimeError('Native distribution identity incomplete')
  for name,digest in v['distribution_sha256'].items():
   if dist[identity['instance']+'/'+name]!=digest or sha(P/name)!=digest:raise RuntimeError('Original distribution identity changed')
 except Exception as ex:error=str(ex)
 rows.append(dict(index=task['index'],cost=task['cost'],key=key,origin=task['origin'],error=error,qualified=error is None and v['passed'],native_point=v['real_probability'] if v is not None else None,original_native_seconds=v['seconds'] if v is not None else None,actual_attempt_wall=time.monotonic()-tick,receipt_sha256=sha(file) if file.exists() else None,private_receipt=file.relative_to(H).as_posix(),physical_new_MC_attempts=1 if log.exists() else 0))
 (D/'PROGRESS.json').write_text(json.dumps(dict(done=len(rows),required=6,rows=rows,seconds=time.monotonic()-started),indent=2));print(json.dumps(rows[-1]),flush=True)
result=dict(scope=reg['scope'],rows=rows,errors=[r['error'] for r in rows if r['error']],qualified=sum(r['qualified'] for r in rows),physical_new_MC_attempts=sum(r['physical_new_MC_attempts'] for r in rows),original_MC_seconds=sum(r['original_native_seconds'] or 0 for r in rows),actual_wall=time.monotonic()-started,registration_sha256=sha(D/'REGISTRATION.json'),all_outputs_private=True,shared_formal_cache_accessed=False,no_search_feedback=True,no_cold_solver_gain_or30run_Avg_claim=True,accounting=reg['accounting'])
with out.open('x') as f:json.dump(result,f,indent=2)
(D/'FINISHED').write_text('all six attempts terminal; inspect RESULT qualification/errors\n');state.write_text(json.dumps(dict(stage='finished_with_errors' if result['errors'] else 'finished',time=time.time(),qualified=result['qualified']),indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
