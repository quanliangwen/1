import concurrent.futures,subprocess,pathlib,json,os,time,hashlib,fcntl,threading,shutil
H=pathlib.Path(__file__).resolve().parent;D=H/'formal30';D.mkdir(exist_ok=True)
lock=open(D/'supervisor.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
registration=json.load(open(H/'REGISTRATION.json'));cases=registration['cases'];source_sha=registration['source_sha256']
if not (H/'PRE_REGISTRATION_REMOTE_VERIFIED.json').exists():raise RuntimeError('Publish and verify frozen protocol first')
for p,v in json.load(open(H/'RAW_REFERENCE.json')).items():
 if '/benchmark/' in p and hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=v:raise RuntimeError('Input changed '+p)
for name,v in source_sha.items():
 if hashlib.sha256((H/'frozen_candidate'/name).read_bytes()).hexdigest()!=v:raise RuntimeError('Frozen source changed '+name)
with (D/'REGISTRATION.json').open('x') as f:json.dump(registration,f,indent=2)
active={};mutex=threading.Lock();PEAK=int(1.3*1024**3);RESERVE=28*1024**3
def memavail():return int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
def rss(pid):
 try:return int(pathlib.Path(f'/proc/{pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
 except Exception:return 0
def run(task):
 rep,c=task;key=(rep,c['index']);out=D/f"S10_{c['index']:02d}_r{rep:02d}.json.gz"
 while True:
  with mutex:
   growth=sum(max(0,PEAK-rss(pid)) for pid in active.values())
   if memavail()>=RESERVE+growth+PEAK and shutil.disk_usage(H).free>=4*1024**3:active[key]=0;break
  time.sleep(2)
 result=None
 try:
  actual={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'frozen_candidate').glob('*.py')}
  if actual!=source_sha:raise RuntimeError('Frozen source mismatch')
  cmd=['/home/junhao/miniconda3/bin/python','-u',str(H/'frozen_candidate/run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed',str(960000+rep),'--seconds','600','--out',str(out)]
  start=time.time()
  with open(str(out)+'.log','x') as log:
   p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
   with mutex:active[key]=p.pid
   try:code=p.wait(timeout=640)
   except subprocess.TimeoutExpired:p.kill();p.wait();code='watchdog_timeout'
  result=dict(index=c['index'],rep=rep,seed=960000+rep,exit=code,wall=time.time()-start)
 except Exception as ex:result=dict(index=c['index'],rep=rep,exit='supervisor_error',reason=str(ex))
 finally:
  with mutex:active.pop(key,None)
  if result is not None:
   with pathlib.Path(str(out)+'.terminal.json').open('x') as f:json.dump(result,f)
   print(json.dumps(result),flush=True)
 return result
tasks=[]
for rep in range(1,31):
 order=cases[(rep-1)%40:]+cases[:(rep-1)%40];tasks.extend((rep,c) for c in order)
with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:results=list(pool.map(run,tasks))
(D/'DISPATCH_RESULTS.json').write_text(json.dumps(results,indent=2));(D/'FINISHED').write_text('done');print('FORMAL_1200_FINISHED',flush=True)
