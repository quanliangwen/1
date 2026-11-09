"""External cost-ordered postselection; never feeds a search worker.

Identical LSS calls reset the same seed and are cached with explicit mappings.
Every optimizer run remains independent. Failed attempts are retained.
"""
import pathlib,json,gzip,time,subprocess,hashlib,fcntl,concurrent.futures,sys
H=pathlib.Path(__file__).parent
mode=sys.argv[1] if len(sys.argv)>1 else 'formal'
D=H/('development' if mode=='development' else 'formal30');V=H/('development_validation' if mode=='development' else 'validation');V.mkdir(exist_ok=True)
C=V/'calls';C.mkdir(exist_ok=True);cases=json.load(open(H/'CASES.json'));reps=[0] if mode=='development' else range(1,31)
if mode=='formal':
 registration=json.load(open(H/'REGISTRATION.json'))
 for name,sha in registration['pipeline_sha256'].items():
  if hashlib.sha256((H/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('Registered pipeline changed '+name)
def evaluate(c,s):
 identity=dict(instance=c['instance'],capacity=float(c['tmax']),selection=list(s),seed=832273,draws=10000000,event='sum<=T')
 key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();out=C/(key+'.json')
 with open(C/(key+'.lock'),'a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if not out.exists():
   cmd=['python3',str(H/'native_lss_eval.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--selection',json.dumps(list(s)),'--out',str(out)]
   with open(C/(key+'.log'),'x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=2400)
   if r.returncode:raise RuntimeError('Original LSS evaluation failed '+key)
  result=json.load(open(out))
 return key,result
def run(c):
 for rep in reps:
  name=f"case_{c['index']:02d}.json.gz" if rep==0 else f"S10_{c['index']:02d}_r{rep:02d}.json.gz"
  source=D/name;output=V/(name+'.postselection.json')
  if output.exists():continue
  while True:
   if source.exists():
    data=json.loads(gzip.decompress(source.read_bytes()))
    if data['status']=='completed':break
   terminal=D/(name+'.terminal.json')
   if terminal.exists() and json.load(open(terminal)).get('exit')!=0:
    data=None;break
   time.sleep(3)
  start=time.monotonic();evaluations=[];selected=None
  try:
   if data is None:raise RuntimeError('Search failed')
   if not data['candidate_shortlist']:raise RuntimeError('Empty certified shortlist')
   for candidate in sorted(data['candidate_shortlist'],key=lambda r:(r['cost'],r['selection'])):
    key,result=evaluate(c,candidate['selection'])
    evaluations.append(dict(key=key,cost=candidate['cost'],selection=candidate['selection'],real_probability=result['real_probability'],passed=result['passed'],original_call_seconds=result['seconds']))
    if result['passed']:
     selected=dict(candidate,real_probability=result['real_probability'],LSS_key=key);break
   out=dict(index=c['index'],rep=rep,source=name,seed=data['seed'],selected=selected,accepted=selected is not None,tested=evaluations,shortlist_count=len(data['candidate_shortlist']),raw_pool_count=data['raw_certified_pool_count'],raw_best_cost=data['selected']['cost'] if data['selected'] else None,elapsed=time.monotonic()-start,logical_MC_seconds=sum(x['original_call_seconds'] for x in evaluations),input_search_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),postselection_rule='lowest-cost LSS>=.985 member of preregistered independently generated shortlist; no feedback to search')
  except Exception as ex:out=dict(index=c['index'],rep=rep,accepted=False,error=str(ex),tested=evaluations,elapsed=time.monotonic()-start)
  with output.open('x') as f:json.dump(out,f,indent=2)
  print(json.dumps(dict(index=c['index'],rep=rep,accepted=out['accepted'],tested=len(evaluations),cost=out.get('selected',{}).get('cost') if out.get('selected') else None)),flush=True)
 return c['index']
with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:list(pool.map(run,cases))
(V/'FINISHED').write_text('done');print('VALIDATION_FINISHED',flush=True)
