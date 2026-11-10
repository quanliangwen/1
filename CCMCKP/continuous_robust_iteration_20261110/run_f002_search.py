"""Frozen I016 formal1200 attempts. No native probability access or feedback."""
from pathlib import Path
import argparse,json,hashlib,subprocess,concurrent.futures,time,gzip,os
H=Path(__file__).resolve().parent;F=H/'formal/F002_I016_40x30'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run_search():
 reg=json.load(open(F/'REGISTRATION.json'));S=H/reg['candidate'];D=F/'search'
 if D.exists() and any(D.iterdir()):raise RuntimeError('Never repeat or replace registered formal attempts')
 if (F/'SEARCH_FINISHED').exists():raise RuntimeError('Formal search already finished')
 D.mkdir(exist_ok=True)
 cases=json.load(open(H/'CASES.json'))
 if [c['index'] for c in cases]!=reg['cases'] or len(cases)!=40 or len(reg['seeds'])!=30 or len(set(reg['seeds']))!=30:raise RuntimeError('Registered1200 dimensions changed')
 def identities():
  if {p.name:sha(p) for p in S.glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Frozen optimizer changed')
  for name,digest in reg['driver_sha256'].items():
   if sha(H/name)!=digest:raise RuntimeError('Frozen formal search driver changed')
  for name,digest in reg['vendor_sha256'].items():
   if sha(H/name)!=digest:raise RuntimeError('Frozen optimizer dependency changed')
  if sha(H/'CASES.json')!=reg['casebook_sha256']:raise RuntimeError('Frozen case/capacity book changed')
  for name,digest in reg['raw_input_sha256'].items():
   if sha(Path(name))!=digest:raise RuntimeError('Frozen original sample input changed')
 identities()
 for c in cases:c['m']=int(c['instance'].split('_')[1])
 def run(task):
  c,seed=task;out=D/f'cdf_pair_cover_{c["index"]:02d}_seed{seed}.json.gz';started=time.monotonic();code=None;error=None;row={}
  try:
   if {p.name:sha(p) for p in S.glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Frozen optimizer changed before attempt')
   cmd=['/home/junhao/miniconda3/bin/python','-u',str(S/'run.py'),'--instance',reg['benchmark']+'/'+c['instance'],'--capacity',str(c['tmax']),'--seed',str(seed),'--seconds',str(reg['search_seconds']),'--risk-method','cdf_pair_cover','--phase-seconds',str(reg['phase_seconds']),'--out',str(out)]
   with Path(str(out)+'.log').open('x') as f:
    try:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=reg['watchdog_seconds'],env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')).returncode
    except subprocess.TimeoutExpired:code='watchdog_timeout'
   if code==0:
    data=json.loads(gzip.decompress(out.read_bytes()));meta=json.load(open(str(out)+'.run.json'))
    if data['seed']!=seed or data['instance']!=c['instance'] or float(data['capacity'])!=float(c['tmax']) or meta['seed']!=seed or meta['source_sha256']!=reg['source_sha256']:raise RuntimeError('Completed formal attempt identity mismatch')
    row.update(search_elapsed=meta['elapsed'],within_budget=meta['within_budget'],pool=data['raw_certified_pool_count'],extension_seconds=data['extension']['extension_seconds'],result_sha256=sha(out),meta_sha256=sha(Path(str(out)+'.run.json')))
  except Exception as ex:error=repr(ex)
  row.update(method='cdf_pair_cover',index=c['index'],seed=seed,exit=code,error=error,wall_seconds=time.monotonic()-started,registration_sha256=sha(F/'REGISTRATION.json'))
  with Path(str(out)+'.terminal.json').open('x') as f:json.dump(row,f,indent=2)
  print(json.dumps(row),flush=True);return row
 pending=[(c,seed) for seed in reg['seeds'] for c in cases];running={};rows=[];peak=0;peaklarge=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=reg['search_workers']) as pool:
  while pending or running:
   large=sum(c['m']>=30 for c,_ in running.values())
   while len(running)<reg['search_workers']:
    eligible=next((i for i,(c,_) in enumerate(pending) if c['m']<30 or large<reg['large_case_workers']),None)
    if eligible is None:break
    task=pending.pop(eligible);running[pool.submit(run,task)]=task
    if task[0]['m']>=30:large+=1
   peak=max(peak,len(running));peaklarge=max(peaklarge,large)
   done,_=concurrent.futures.wait(running,timeout=30,return_when=concurrent.futures.FIRST_COMPLETED)
   for future in done:rows.append(future.result());del running[future]
   progress=dict(finished=len(rows),required=1200,running=len(running),large_running=sum(c['m']>=30 for c,_ in running.values()),pending=len(pending),ordinary_errors=sum(r['exit']!=0 or r['error'] is not None for r in rows),budget_failures=sum(r.get('within_budget') is False for r in rows),phase_failures=sum(r.get('extension_seconds',0)>reg['phase_seconds'] for r in rows),peak_workers=peak,peak_large_workers=peaklarge,time=time.time(),native_calls_by_this_controller=0)
   tmp=F/'SEARCH_PROGRESS.tmp';tmp.write_text(json.dumps(progress,indent=2));tmp.replace(F/'SEARCH_PROGRESS.json')
 identities()
 if len(rows)!=1200 or len({(r['index'],r['seed']) for r in rows})!=1200:raise RuntimeError('All registered attempts must be retained')
 with (D/'DISPATCH_RESULTS.json').open('x') as f:json.dump(rows,f,indent=2)
 with (F/'SEARCH_FINISHED').open('x') as f:json.dump(dict(time=time.time(),attempts=1200,ordinary_errors=progress['ordinary_errors'],scope='all attempts retained; pending independent raw audit and separate original native validation; no final Avg'),f,indent=2)
 print('F002_FULL40X30_SEARCH_FINISHED_PENDING_INDEPENDENT_AUDIT',flush=True)

if __name__=='__main__':run_search()
