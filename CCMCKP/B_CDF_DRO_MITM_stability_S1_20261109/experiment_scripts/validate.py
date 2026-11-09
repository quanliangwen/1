import concurrent.futures,subprocess,pathlib,json,os,time,hashlib,fcntl
H=pathlib.Path(__file__).resolve().parent;outdir=H/'validation';outdir.mkdir(exist_ok=True)
lock=open(outdir/'supervisor.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
cases=json.load(open(H/'frozen/original_experiment/cases.json'))
source_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'candidate').glob('*.py')}
registration=dict(schema='S1_fixed_validation',cases=cases,repetitions=5,seeds=list(range(900001,900006)),seconds=600,max_workers=12,source_sha256=source_sha,development_seeds=[832273],no_warm_start=True,ordinary_failures_not_replaced=True)
with (outdir/'REGISTRATION.json').open('x') as f:json.dump(registration,f,indent=2)
tasks=[(rep,c) for rep in range(1,6) for c in cases]
def run(task):
 rep,c=task;i=c['index'];out=outdir/f'S1_{i:02d}_r{rep:02d}.json.gz'
 while True:
  memory={a.split(':')[0]:int(a.split()[1]) for a in pathlib.Path('/proc/meminfo').read_text().splitlines() if ':' in a}
  if memory['MemAvailable']>24*1024**2:break
  time.sleep(5)
 if {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'candidate').glob('*.py')}!=source_sha:raise RuntimeError('source mutated')
 cmd=['python3','-u',str(H/'candidate/run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed',str(900000+rep),'--seconds','600','--out',str(out)]
 with open(str(out)+'.log','x') as log:
  started=time.time()
  try:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=630);exit_code=r.returncode
  except subprocess.TimeoutExpired:exit_code='timeout'
 result=dict(index=i,rep=rep,exit=exit_code,wall=time.time()-started)
 (outdir/f'S1_{i:02d}_r{rep:02d}.terminal.json').write_text(json.dumps(result))
 print(json.dumps(result),flush=True)
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(run,tasks))
(outdir/'DISPATCH_RESULTS.json').write_text(json.dumps(results,indent=2))
