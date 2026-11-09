"""External-only speculative original-LSS calls; optimizer is unchanged.

This may evaluate candidates beyond the primary selector's first passing one.
Those extra physical computations are explicitly recorded, not hidden in the
primary selector's logical cost. fcntl locks share exact identical calls only.
"""
from pathlib import Path
import json,gzip,hashlib,subprocess,fcntl,concurrent.futures,time,datetime
H=Path(__file__).parent;I=H/'iterations/I002_cdf_neighborhood';C=H/'lss_cache'
if (I/'PREFETCH_LAUNCH.json').exists():raise RuntimeError('No duplicate prefetch')
reg=json.load(open(I/'REGISTRATION.json'));base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};cases={r['index']:r for r in json.load(open(H/'CASES.json'))}
tasks=[]
for index in [39,40]:
 name=f'cdf_lns_{index:02d}_seed970201.json.gz';source=I/'pilot'/name
 meta=json.load(open(str(source)+'.run.json'))
 if meta['source_sha256']!=reg['source_sha256']:raise RuntimeError('Unregistered source')
 data=json.loads(gzip.decompress(source.read_bytes()))
 for r in data['candidate_shortlist']:
  if r['cost']>=base[index]['new_avg']-1e-8:break
  cert=r['certificate']
  if 100*int(cert['lower_numerator'])<99*int(cert['denominator']):raise RuntimeError('Missing raw certificate')
  identity=dict(instance=cases[index]['instance'],capacity=float(cases[index]['tmax']),selection=r['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
  if not (C/(key+'.json')).exists():tasks.append(dict(index=index,identity=identity,key=key,cost=r['cost']))
with (I/'PREFETCH_LAUNCH.json').open('x') as f:json.dump(dict(launched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),workers=16,external_only=True,primary_selector_unchanged=True,speculative_extra_cost_disclosed=True,tasks=tasks),f,indent=2)
def evaluate(task):
 key=task['key'];identity=task['identity'];out=C/(key+'.json');new=False;start=time.monotonic()
 with (C/(key+'.lock')).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if not out.exists():
   with (C/(key+'.log')).open('x') as log:
    r=subprocess.run(['python3',str(H/'native_lss_eval.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+identity['instance'],'--capacity',str(identity['capacity']),'--selection',json.dumps(identity['selection']),'--out',str(out)],stdout=log,stderr=subprocess.STDOUT,timeout=2400)
   if r.returncode:raise RuntimeError('Original LSS evaluation failed '+key)
   new=True
  d=json.load(open(out))
  if any(d[k]!=v for k,v in identity.items()) or d['passed']!=(d['real_probability']>=.985):raise RuntimeError('Wrong original call identity')
 result=dict(task,new_call_issued_here=new,record_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),real_probability=d['real_probability'],passed=d['passed'],native_seconds=d['seconds'],wall_seconds=time.monotonic()-start)
 print(json.dumps({k:v for k,v in result.items() if k!='identity'}),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:results=list(pool.map(evaluate,tasks))
(I/'PREFETCH_RESULTS.json').write_text(json.dumps(dict(results=results,new_calls=sum(r['new_call_issued_here'] for r in results),new_native_seconds=sum(r['native_seconds'] for r in results if r['new_call_issued_here']),warning='speculative evaluations may exceed original primary selector stopping point; charge all physical calls globally'),indent=2));print('PREFETCH_FINISHED',flush=True)
