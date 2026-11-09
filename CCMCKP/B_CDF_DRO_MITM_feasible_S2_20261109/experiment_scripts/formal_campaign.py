import concurrent.futures,subprocess,pathlib,json,os,time,hashlib,fcntl,threading,shutil
H=pathlib.Path(__file__).resolve().parent;D=H/'formal30';D.mkdir(exist_ok=True);lock=open(D/'supervisor.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
cases=json.load(open(H/'CASES.json'));raw_registry=json.load(open(H/'RAW_REFERENCE.json'));source_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'candidate').glob('*.py')}
# Freeze checks outside each solver clock, exactly as declared.
raw_items=[(p,v) for p,v in raw_registry.items() if '/benchmark/' in p]
for p,v in raw_items:
 if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=v:raise RuntimeError('Input hash mismatch: '+p)
registration=dict(schema='S2R2_formal_40x30',cases=cases,repetitions=30,seeds=list(range(920001,920031)),seconds=600,watchdog=640,max_workers=64,memory_reserve_gib=24,projected_worker_peak_gib=1.25,source_sha256=source_sha,raw_input_registry_sha256=hashlib.sha256((H/'RAW_REFERENCE.json').read_bytes()).hexdigest(),raw_files_verified=len(raw_items),all_original_samples=True,acceptance='exact upward-rounded integer polynomial count; 100*numerator>=99*denominator; final independent recount inside run',no_prior_or_cross_run_solutions=True,no_replacement_of_ordinary_failures=True,old_best_is_cost_reference_not_assumed_feasible=True,development_seeds=[955201,955202],small_case_enumeration='all selections cost-ordered; first certified feasible accepted after exact upper-bound refutations of all cheaper choices',imports_and_source_input_checks_outside_search_clock=True,search_clock_includes='instance load, construction, rational parsing, all search, exact acceptance, final exact recount, main output fsync')
with (D/'REGISTRATION.json').open('x') as f:json.dump(registration,f,indent=2)
(D/'RAW_INPUT_SHA256.json').write_text(json.dumps({p:v for p,v in raw_items},indent=2));(D/'CASES.json').write_text(json.dumps(cases,indent=2))
active={};mutex=threading.Lock();PEAK=1.25*1024**3;RESERVE=24*1024**3

def memavail():
 return int(next(line.split()[1] for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024

def rss(pid):
 try:return int(pathlib.Path(f'/proc/{pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
 except Exception:return 0

def run(task):
 rep,c=task;i=c['index'];key=(rep,i);out=D/f'S2_{i:02d}_r{rep:02d}.json.gz'
 while True:
  with mutex:
   growth=sum(max(0,PEAK-rss(pid)) for pid in active.values())
   if memavail()>=RESERVE+growth+PEAK and shutil.disk_usage(H).free>=4*1024**3:
    active[key]=0;break
  time.sleep(2)
 result=None
 try:
  if {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'candidate').glob('*.py')}!=source_sha:raise RuntimeError('Frozen source changed')
  cmd=['/home/junhao/miniconda3/bin/python','-u',str(H/'candidate/run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed',str(920000+rep),'--seconds','600','--out',str(out)]
  with open(str(out)+'.log','x') as log:
   started=time.time();p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
   with mutex:active[key]=p.pid
   try:code=p.wait(timeout=640)
   except subprocess.TimeoutExpired:p.kill();p.wait();code='watchdog_timeout'
  result=dict(index=i,rep=rep,seed=920000+rep,exit=code,wall=time.time()-started)
 except Exception as ex:result=dict(index=i,rep=rep,exit='supervisor_error',reason=str(ex))
 finally:
  with mutex:active.pop(key,None)
  if result is not None:
   (D/f'S2_{i:02d}_r{rep:02d}.terminal.json').write_text(json.dumps(result));print(json.dumps(result),flush=True)
 return result
# Deterministic case rotation spreads long and short cases across repetition blocks.
tasks=[]
for rep in range(1,31):
 order=cases[(rep-1)%40:]+cases[:(rep-1)%40];tasks.extend((rep,c) for c in order)
with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:results=list(pool.map(run,tasks))
(D/'DISPATCH_RESULTS.json').write_text(json.dumps(results,indent=2));print('FORMAL_1200_FINISHED',flush=True)
