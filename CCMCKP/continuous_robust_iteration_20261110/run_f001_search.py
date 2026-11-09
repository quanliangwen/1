"""Frozen I002 full40x30 search, eligible only after registered stability passes."""
from pathlib import Path
import json,hashlib,subprocess,concurrent.futures,time,gzip,collections
H=Path(__file__).parent;F=H/'formal/F001_I002_40x30';D=F/'search';D.mkdir(exist_ok=True);reg=json.load(open(F/'REGISTRATION.json'));S=H/'iterations/I002_cdf_neighborhood/candidate';cases=json.load(open(H/'CASES.json'))
if len(cases)!=40 or len(reg['seeds'])!=30:raise RuntimeError('Wrong formal experiment dimensions')
for c in cases:c['m']=int(c['instance'].split('_')[1])
def run(task):
 c,seed=task;out=D/f'cdf_lns_{c["index"]:02d}_seed{seed}.json.gz';start=time.monotonic()
 if {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in S.glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Formal source changed')
 cmd=['/home/junhao/miniconda3/bin/python','-u',str(S/'run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed',str(seed),'--seconds','600','--risk-method','cdf_lns','--phase-seconds','180','--out',str(out)]
 with Path(str(out)+'.log').open('x') as f:
  try:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=640);code=r.returncode
  except subprocess.TimeoutExpired:code='watchdog_timeout'
 row=dict(method='cdf_lns',index=c['index'],seed=seed,exit=code,wall_seconds=time.monotonic()-start)
 if code==0:
  data=json.loads(gzip.decompress(out.read_bytes()));meta=json.load(open(str(out)+'.run.json'));row.update(search_elapsed=meta['elapsed'],within_budget=meta['within_budget'],pool=data['raw_certified_pool_count'],extension=data['extension'])
 with Path(str(out)+'.terminal.json').open('x') as f:json.dump(row,f)
 print(json.dumps({k:v for k,v in row.items() if k!='extension'}),flush=True);return row
pending=[(c,seed) for seed in reg['seeds'] for c in cases];running={};rows=[]
# Cap large instances so a run receives a reproducible useful search budget.
# Native true-parameter validation is a separate stage, never concurrent here.
with concurrent.futures.ThreadPoolExecutor(max_workers=reg['search_workers']) as pool:
 while pending or running:
  large=sum(c['m']>=30 for c,_ in running.values())
  while len(running)<reg['search_workers']:
   eligible=next((i for i,(c,seed) in enumerate(pending) if c['m']<30 or large<reg['large_case_workers']),None)
   if eligible is None:break
   task=pending.pop(eligible);running[pool.submit(run,task)]=task
   if task[0]['m']>=30:large+=1
  done,_=concurrent.futures.wait(running,timeout=30,return_when=concurrent.futures.FIRST_COMPLETED)
  for future in done:rows.append(future.result());del running[future]
  (F/'SEARCH_PROGRESS.json').write_text(json.dumps(dict(finished=len(rows),required=1200,running=len(running),pending=len(pending),ordinary_errors=sum(r['exit']!=0 for r in rows)),indent=2))
(D/'DISPATCH_RESULTS.json').write_text(json.dumps(rows,indent=2));(D/'FINISHED').write_text('done');print('FULL40X30_SEARCH_FINISHED',flush=True)
