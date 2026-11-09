import pathlib,json,subprocess,time,concurrent.futures,hashlib,gzip
H=pathlib.Path(__file__).parent;I=H/'iterations/I004_robust_pair_exchange';D=I/'pilot';D.mkdir(exist_ok=True)
reg=json.load(open(I/'REGISTRATION.json'));cases=[c for c in json.load(open(H/'CASES.json')) if c['index'] in reg['pilot_cases']]
def run(task):
 method,c=task;name=f"{method}_{c['index']:02d}_seed970401.json.gz";out=D/name;started=time.time()
 if {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (I/'candidate').glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Pilot source mutated')
 cmd=['/home/junhao/miniconda3/bin/python','-u',str(I/'candidate/run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed','970401','--seconds','600','--risk-method',method,'--phase-seconds','180','--out',str(out)]
 with open(str(out)+'.log','x') as log:
  try:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=640);code=r.returncode
  except subprocess.TimeoutExpired:code='watchdog_timeout'
 row=dict(method=method,index=c['index'],seed=970401,exit=code,wall=time.time()-started)
 if code==0:
  data=json.loads(gzip.decompress(out.read_bytes()));meta=json.load(open(str(out)+'.run.json'));row.update(pool=data['raw_certified_pool_count'],shortlist=len(data['candidate_shortlist']),raw_cost=data['selected']['cost'] if data['selected'] else None,within_budget=meta['within_budget'],extension=data['extension'])
 with pathlib.Path(str(out)+'.terminal.json').open('x') as f:json.dump(row,f)
 print(json.dumps({k:v for k,v in row.items() if k!='extension'}),flush=True);return row
tasks=[(method,c) for c in cases for method in reg['methods']]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,tasks))
(D/'DISPATCH_RESULTS.json').write_text(json.dumps(rows,indent=2));(D/'FINISHED').write_text('done');print('I004_PILOT_SEARCH_FINISHED',flush=True)
