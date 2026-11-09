import pathlib,subprocess,concurrent.futures,json,time,gzip
H=pathlib.Path(__file__).parent;D=H/'development';D.mkdir(exist_ok=True)
cases=json.load(open(H/'CASES.json'))
def run(c):
 out=D/f"case_{c['index']:02d}.json.gz"
 cmd=['/home/junhao/miniconda3/bin/python','-u',str(H/'candidate/run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed','965001','--seconds','180','--out',str(out)]
 start=time.time()
 with open(str(out)+'.log','x') as f:
  try:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=220);code=r.returncode
  except subprocess.TimeoutExpired:code='timeout'
 result=dict(index=c['index'],exit=code,elapsed=time.time()-start)
 if out.exists():
  s=json.loads(gzip.decompress(out.read_bytes()));result.update(pool=s['raw_certified_pool_count'],shortlist=len(s['candidate_shortlist']),cost=s['selected']['cost'] if s['selected'] else None,enumeration=s['exhaustive'])
 (D/f"case_{c['index']:02d}.terminal.json").write_text(json.dumps(result));print(json.dumps(result),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:results=list(pool.map(run,cases))
(D/'SUMMARY.json').write_text(json.dumps(results,indent=2));print('DEVELOPMENT_FINISHED',flush=True)
