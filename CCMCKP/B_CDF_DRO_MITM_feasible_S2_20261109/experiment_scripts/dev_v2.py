import pathlib,json,subprocess,concurrent.futures,time
H=pathlib.Path(__file__).parent;D=H/'development_v2';D.mkdir(exist_ok=True)
cases=json.load(open('/home/quanliangwen/work/cdf_stability_20261109/frozen/original_experiment/cases.json'))
def run(c):
 out=D/f"S2_{c['index']:02d}.json.gz";cmd=['/home/junhao/miniconda3/bin/python','-u',str(H/'source_v2/run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--seed','955202','--seconds','600','--out',str(out)]
 with open(str(out)+'.log','x') as log:
  t=time.time()
  try:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=640);exit=p.returncode
  except subprocess.TimeoutExpired:exit='timeout'
 result=dict(index=c['index'],exit=exit,wall=time.time()-t);(D/f"S2_{c['index']:02d}.terminal.json").write_text(json.dumps(result));print(json.dumps(result),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as p:list(p.map(run,[c for c in cases if c['index'] in [11,19,20,30,31,32,35,36,37,38,39,40]]))
(D/'FINISHED').write_text('all 40 accounted for')
