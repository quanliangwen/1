from pathlib import Path
import json,hashlib,subprocess,concurrent.futures,time,gzip
H=Path(__file__).parent;I=H/'stability/I002_case39';D=I/'search';D.mkdir(exist_ok=True);reg=json.load(open(I/'REGISTRATION.json'));S=H/'iterations'/reg['source_iteration']/'candidate';cases=[c for c in json.load(open(H/'CASES.json')) if c['index'] in reg['cases']]
def run(task):
 method,c,seed=task;out=D/f'{method}_{c["index"]:02d}_seed{seed}.json.gz';start=time.monotonic()
 if {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in S.glob('*.py')}!=reg['source_sha256']:raise RuntimeError('I002 source changed')
 cmd=['/home/junhao/miniconda3/bin/python','-u',str(S/'run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed',str(seed),'--seconds',str(reg['search_seconds']),'--risk-method',method,'--phase-seconds',str(reg['phase_seconds']),'--out',str(out)]
 with Path(str(out)+'.log').open('x') as f:
  try:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=reg['watchdog_seconds']);code=r.returncode
  except subprocess.TimeoutExpired:code='watchdog_timeout'
 row=dict(method=method,index=c['index'],seed=seed,exit=code,wall_seconds=time.monotonic()-start)
 if code==0:
  data=json.loads(gzip.decompress(out.read_bytes()));meta=json.load(open(str(out)+'.run.json'));row.update(search_elapsed=meta['elapsed'],within_budget=meta['within_budget'],pool=data['raw_certified_pool_count'],extension=data['extension'])
 with Path(str(out)+'.terminal.json').open('x') as f:json.dump(row,f)
 print(json.dumps({k:v for k,v in row.items() if k!='extension'}),flush=True);return row
tasks=[(method,c,seed) for seed in reg['seeds'] for c in cases for method in reg['methods']]
with concurrent.futures.ThreadPoolExecutor(max_workers=reg['workers']) as pool:rows=list(pool.map(run,tasks))
(D/'DISPATCH_RESULTS.json').write_text(json.dumps(rows,indent=2));(D/'FINISHED').write_text('done');print('STABILITY_SEARCH_FINISHED',flush=True)
