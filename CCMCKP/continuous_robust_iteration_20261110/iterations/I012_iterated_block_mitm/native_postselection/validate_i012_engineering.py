"""Post-freeze original-LSS cost-order selection, after F001 and I004 finish."""
from pathlib import Path
import json,gzip,hashlib,time,subprocess,fcntl,sys
H=Path(__file__).parent;I=H/'iterations/I012_iterated_block_mitm';J=I/'engineering40';R=J/'NATIVE_REGISTRATION.json';out=J/'result.json.gz.post.json';reg=json.load(open(R));state=J/'NATIVE_STATE.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('Native result exists; do not rerun')
for name,digest in reg['driver_sha256'].items():
 if sha(H/name)!=digest:raise RuntimeError('Native driver drift')
for name,digest in reg['source_sha256'].items():
 if sha(I/'candidate'/name)!=digest:raise RuntimeError('Frozen optimizer drift')
if sha(J/'result.json.gz')!=reg['frozen_search_sha256']:raise RuntimeError('Frozen search changed')
reference=json.load(open(H/'REFERENCE_SHA256.json'));distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];bench=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/reg['instance'];C=H/'lss_cache'
for r in reference['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original LSS source changed')
state.write_text(json.dumps(dict(stage='waiting_for_F001_and_I004',time=time.time(),no_native_calls_started=True),indent=2))
while not all((H/p).exists() for p in reg['wait_for']):time.sleep(15)
inventory=dict(time=time.time(),files=[dict(name=p.name,sha256=sha(p)) for p in sorted(C.glob('*.json'))],logs=[p.name for p in sorted(C.glob('*.log'))])
with (J/'CACHE_BEFORE_NATIVE.json').open('x') as f:json.dump(inventory,f,indent=2)
start=time.monotonic();tested=[];selected=None;error=None
state.write_text(json.dumps(dict(stage='native_postselection',time=time.time()),indent=2))
try:
 data=json.loads(gzip.decompress((J/'result.json.gz').read_bytes()));pool=data['candidate_shortlist']
 if pool!=sorted(pool,key=lambda r:(r['cost'],r['selection'])):raise RuntimeError('Cost order changed')
 for candidate in pool:
  identity=dict(instance=reg['instance'],capacity=float(reg['capacity']),selection=candidate['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();file=C/(key+'.json');new=False
  with (C/(key+'.lock')).open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   if not file.exists():
    with (C/(key+'.log')).open('x') as log:
     r=subprocess.run(['python3',str(H/'native_lss_eval.py'),'--instance',str(bench),'--capacity',str(reg['capacity']),'--selection',json.dumps(candidate['selection']),'--out',str(file)],stdout=log,stderr=subprocess.STDOUT,timeout=2400)
    if r.returncode:raise RuntimeError('Original LSS call failed '+key)
    new=True
   v=json.load(open(file))
   if any(v[k]!=x for k,x in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1' or v['passed']!=(v['real_probability']>=.985) or v['search_feedback']:raise RuntimeError('Original native identity mismatch')
   if set(v['distribution_sha256'])!={f'{j}_dist.txt' for j in identity['selection']}:raise RuntimeError('Incomplete distribution identity')
   for name,digest in v['distribution_sha256'].items():
    if distref[reg['instance']+'/'+name]!=digest or sha(bench/name)!=digest:raise RuntimeError('Distribution drift')
  tested.append(dict(key=key,selection=candidate['selection'],cost=candidate['cost'],real_probability=v['real_probability'],passed=v['passed'],new_call_for_this_task=new,call_seconds=v['seconds']))
  if v['passed']:selected=dict(candidate,real_probability=v['real_probability'],LSS_key=key);break
except Exception as ex:error=str(ex)
result=dict(scope='one frozen engineering run external original-LSS postselection, not30-run Avg',index=40,search_seed=9712000,accepted=selected is not None,selected=selected,tested=tested,logical_MC_seconds=sum(x['call_seconds'] for x in tested),new_calls_charged_to_this_task=sum(x['new_call_for_this_task'] for x in tested),actual_post_seconds=time.monotonic()-start,source_sha256=reg['frozen_search_sha256'],registration_sha256=sha(R),error=error,no_search_feedback=True,waited_for=reg['wait_for'])
with out.open('x') as f:json.dump(result,f,indent=2)
state.write_text(json.dumps(dict(stage='error' if error else 'finished',time=time.time(),accepted=result['accepted'],new_calls=result['new_calls_charged_to_this_task']),indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['selected','tested']}),flush=True)
if error:sys.exit(1)
