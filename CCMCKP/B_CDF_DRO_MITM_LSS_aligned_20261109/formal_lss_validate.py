import pathlib,json,gzip,hashlib,subprocess,concurrent.futures,time,os,fcntl
H=pathlib.Path(__file__).resolve().parent;D=H/'formal30_lss';V=H/'formal30_lss_validation';V.mkdir(exist_ok=True)
lock=open(V/'supervisor.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
cases=json.load(open(H/'CASES.json'));case_map={c['index']:c for c in cases};seen=set();requests={};links=[];futures={};finished=[];errors=[]
def atomic(p,obj):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2));os.replace(tmp,p)
def evaluate(t):
 out=V/(t['key']+'.json');cmd=['python3','-u',str(H/'lss_real_eval.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+t['instance'],'--capacity',str(t['capacity']),'--selection',json.dumps(t['selection']),'--out',str(out)]
 started=time.time()
 with open(str(out)+'.log','x') as log:
  try:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1200);code=p.returncode
  except subprocess.TimeoutExpired:code='timeout'
 r=dict(key=t['key'],index=t['index'],exit=code,wall=time.time()-started)
 if code==0:
  z=json.load(open(out));r.update(real_probability=z['real_probability'],passed=z['real_probability']>=.985)
 atomic(V/(t['key']+'.terminal.json'),r);print(json.dumps(r),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 while True:
  for p in sorted(D.glob('LSS_*.terminal.json')):
   if p.name in seen:continue
   seen.add(p.name);t=json.load(open(p));i=t['index'];rep=t['rep'];c=case_map[i]
   item=dict(index=i,rep=rep,seed=930000+rep,optimizer_exit=t['exit'])
   try:
    if t['exit']!=0:raise RuntimeError('optimizer failed')
    r=json.load(gzip.open(D/f'LSS_{i:02d}_r{rep:02d}.json.gz','rt'));s=r['selected']
    if not s:raise RuntimeError('no returned selection')
    key=hashlib.sha256(json.dumps([c['instance'],c['tmax'],s['selection'],832273],separators=(',',':')).encode()).hexdigest()
    item.update(key=key,selection=s['selection'],cost=s['cost'])
    if key not in requests:
     task=dict(key=key,index=i,instance=c['instance'],capacity=c['tmax'],selection=s['selection']);requests[key]=task;futures[pool.submit(evaluate,task)]=key
   except Exception as e:item['error']=str(e);errors.append(item)
   links.append(item)
  for f,key in list(futures.items()):
   if f.done():
    try:finished.append(f.result())
    except Exception as e:finished.append(dict(key=key,exit='evaluator_supervisor_error',reason=str(e)))
    del futures[f]
  atomic(V/'REQUESTS.json',list(requests.values()));atomic(V/'LINKS.json',links);atomic(V/'STATUS.json',dict(accounted_optimizer_runs=len(seen),required_runs=1200,unique_requested=len(requests),unique_finished=len(finished),active_unique=len(futures),optimizer_errors=errors,evaluator_errors=[r for r in finished if r['exit']!=0],threshold=.985,draws=10000000,seed=832273))
  if len(seen)==1200 and not futures:break
  time.sleep(5)
atomic(V/'DISPATCH_RESULTS.json',finished);(V/'FINISHED').write_text('All 1200 attempts accounted for; inspect errors and probabilities before declaring success.');print('LSS_1200_REFERENCES_FINISHED',flush=True)
