import pathlib,json,subprocess,time,concurrent.futures,gzip,hashlib
H=pathlib.Path(__file__).parent;D=H/'frozen_smoke';D.mkdir(exist_ok=True);cases=json.load(open(H/'CASES.json'))
tasks=[(c,965400+k) for k,c in enumerate([c for c in cases if c['index'] in [21,22,23,24,25,26,27,28,36,39,40]],1)]+[(cases[39],965412)]
def run(task):
 c,seed=task;out=D/f"case_{c['index']:02d}_seed{seed}.json.gz";start=time.time()
 cmd=['/home/junhao/miniconda3/bin/python','-u',str(H/'frozen_candidate/run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed',str(seed),'--seconds','180','--out',str(out)]
 with open(str(out)+'.log','x') as log:
  try:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=220);code=r.returncode
  except subprocess.TimeoutExpired:code='timeout'
 result=dict(index=c['index'],seed=seed,exit=code,wall=time.time()-start)
 if code==0:
  d=json.loads(gzip.decompress(out.read_bytes()));meta=json.load(open(str(out)+'.run.json'))
  result.update(selected=d['selected'] is not None,shortlist=len(d['candidate_shortlist']),source_matches=meta['source_sha256']==json.load(open(H/'REGISTRATION.json'))['source_sha256'],elapsed=meta['elapsed'],within_budget=meta['within_budget'],tail_removed=d['config']['tail_use']=='removed_entirely',all_small_pool_retained=d['exhaustive'] is None or len(d['candidate_shortlist'])==d['raw_certified_pool_count'])
 print(json.dumps(result),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(run,tasks))
ok=all(r['exit']==0 and r['selected'] and r['shortlist'] and r['within_budget'] and r['source_matches'] and r['tail_removed'] and r['all_small_pool_retained'] for r in results)
(D/'SUMMARY.json').write_text(json.dumps(dict(all_passed=ok,runs=results),indent=2));print('FROZEN_SMOKE_FINISHED',ok,flush=True)
