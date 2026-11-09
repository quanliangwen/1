import pathlib,json,gzip,time,hashlib,subprocess,fcntl,concurrent.futures
H=pathlib.Path(__file__).parent;I=H/'iterations/I003_ellipsoid_frontier';D=I/'pilot';V=I/'pilot_validation';V.mkdir(exist_ok=True);C=H/'lss_cache';C.mkdir(exist_ok=True)
reg=json.load(open(I/'REGISTRATION.json'));cases=[c for c in json.load(open(H/'CASES.json')) if c['index'] in reg['pilot_cases']];baseline={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']}
def evaluate(c,candidate):
 identity=dict(instance=c['instance'],capacity=float(c['tmax']),selection=candidate['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();out=C/(key+'.json');new=False
 with (C/(key+'.lock')).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if not out.exists():
   with (C/(key+'.log')).open('x') as log:r=subprocess.run(['python3',str(H/'native_lss_eval.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--selection',json.dumps(candidate['selection']),'--out',str(out)],stdout=log,stderr=subprocess.STDOUT,timeout=2400)
   if r.returncode:raise RuntimeError('New original LSS call failed '+key)
   new=True
  d=json.load(open(out))
  if any(d[k]!=v for k,v in identity.items()) or d['passed']!=(d['real_probability']>=.985):raise RuntimeError('Invalid cache identity')
 return key,d,new
def run(task):
 method,c=task;name=f"{method}_{c['index']:02d}_seed970301.json.gz";out=V/(name+'.post.json')
 if out.exists():return
 source=D/name;terminal=pathlib.Path(str(source)+'.terminal.json')
 while not terminal.exists():time.sleep(3)
 terms=json.load(open(terminal));start=time.monotonic();tested=[];selected=None
 try:
  if terms['exit']!=0:raise RuntimeError('Pilot search failed')
  data=json.loads(gzip.decompress(source.read_bytes()))
  if data['status']!='completed':raise RuntimeError('Incomplete search')
  for candidate in data['candidate_shortlist']:
   key,d,new=evaluate(c,candidate);tested.append(dict(key=key,selection=candidate['selection'],cost=candidate['cost'],real_probability=d['real_probability'],passed=d['passed'],new_call_for_this_task=new,call_seconds=d['seconds']))
   if d['passed']:selected=dict(candidate,real_probability=d['real_probability'],LSS_key=key);break
  result=dict(method=method,index=c['index'],accepted=selected is not None,selected=selected,tested=tested,logical_MC_seconds=sum(x['call_seconds'] for x in tested),new_calls_charged_to_this_task=sum(x['new_call_for_this_task'] for x in tested),actual_post_seconds=time.monotonic()-start,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),S10_cost=baseline[c['index']]['new_avg'],old_best=baseline[c['index']]['old_best'],development_only=True,no_search_feedback=True)
 except Exception as ex:result=dict(method=method,index=c['index'],accepted=False,error=str(ex),tested=tested,development_only=True)
 with out.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(method=method,index=c['index'],accepted=result['accepted'],cost=selected['cost'] if selected else None,tested=len(tested))),flush=True)
tasks=[(method,c) for c in cases for method in reg['methods']]
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:list(pool.map(run,tasks))
(V/'FINISHED').write_text('done');print('I003_PILOT_VALIDATION_FINISHED',flush=True)
