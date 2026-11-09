"""External-only lookahead to the first known passing prefix; no search changes."""
from pathlib import Path
import json,gzip,hashlib,subprocess,fcntl,concurrent.futures,time,datetime
H=Path(__file__).parent;I=H/'stability/I002_case39';C=H/'lss_cache';reg=json.load(open(I/'REGISTRATION.json'));c=next(c for c in json.load(open(H/'CASES.json')) if c['index']==39)
if (I/'PREFETCH_LAUNCH.json').exists():raise RuntimeError('No duplicate prefetch')
tasks={}
for seed in reg['seeds']:
 source=I/'search'/f'cdf_lns_39_seed{seed}.json.gz';meta=json.load(open(str(source)+'.run.json'))
 if meta['source_sha256']!=reg['source_sha256']:raise RuntimeError('Source mutation')
 for q in json.loads(gzip.decompress(source.read_bytes()))['candidate_shortlist']:
  if 100*int(q['certificate']['lower_numerator'])<99*int(q['certificate']['denominator']):raise RuntimeError('Raw certificate missing')
  identity=dict(instance=c['instance'],capacity=float(c['tmax']),selection=q['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();out=C/(key+'.json')
  if out.exists():
   d=json.load(open(out))
   if any(d[k]!=v for k,v in identity.items()):raise RuntimeError('Cached identity mismatch')
   if d['passed']:break
  else:tasks[key]=dict(key=key,identity=identity,cost=q['cost'])
tasks=sorted(tasks.values(),key=lambda t:(t['cost'],t['key']))
with (I/'PREFETCH_LAUNCH.json').open('x') as f:json.dump(dict(time=time.time(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),workers=8,external_only=True,prefix_policy='only missing candidates before first cached passing point in each frozen independent pool',extra_cost_disclosed=True,tasks=tasks),f,indent=2)
def evaluate(task):
 key=task['key'];identity=task['identity'];out=C/(key+'.json');new=False;start=time.monotonic()
 with (C/(key+'.lock')).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if not out.exists():
   with (C/(key+'.log')).open('x') as log:r=subprocess.run(['python3',str(H/'native_lss_eval.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+identity['instance'],'--capacity',str(identity['capacity']),'--selection',json.dumps(identity['selection']),'--out',str(out)],stdout=log,stderr=subprocess.STDOUT,timeout=2400)
   if r.returncode:raise RuntimeError('Original LSS failure')
   new=True
  d=json.load(open(out))
  if any(d[k]!=v for k,v in identity.items()) or d['passed']!=(d['real_probability']>=.985):raise RuntimeError('Wrong original call')
 result=dict(task,new_call_issued_here=new,record_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),real_probability=d['real_probability'],passed=d['passed'],native_seconds=d['seconds'],wall_seconds=time.monotonic()-start)
 print(json.dumps({k:v for k,v in result.items() if k!='identity'}),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(evaluate,tasks))
(I/'PREFETCH_RESULTS.json').write_text(json.dumps(dict(results=results,new_calls=sum(r['new_call_issued_here'] for r in results),new_native_seconds=sum(r['native_seconds'] for r in results if r['new_call_issued_here']),warning='all physical calls charged; primary cost-order stopping point unchanged'),indent=2));print('PREFETCH_FINISHED',flush=True)
