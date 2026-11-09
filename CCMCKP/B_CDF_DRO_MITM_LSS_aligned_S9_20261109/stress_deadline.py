import pathlib,json,concurrent.futures,subprocess,time
H=pathlib.Path(__file__).parent;D=H/'deadline_stress';D.mkdir(exist_ok=True)
def run(seed):
 out=D/f'APP5_10_T16_seed{seed}.json.gz';cmd=['/home/junhao/miniconda3/bin/python','-u',str(H/'candidate/run.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_5_10_30_','--capacity','16','--seed',str(seed),'--seconds','180','--out',str(out)];start=time.time()
 with open(str(out)+'.log','x') as log:
  try:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=220);exit=p.returncode
  except subprocess.TimeoutExpired:exit='timeout'
 r=dict(seed=seed,exit=exit,wall=time.time()-start)
 if exit==0:
  s=json.load(open(str(out)+'.run.json'));r.update(selected_cost=None if not s['selected'] else s['selected']['cost'],elapsed=s['elapsed'],within_budget=s['within_budget'])
 (D/f'{seed}.terminal.json').write_text(json.dumps(r));print(json.dumps(r),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(run,range(955401,955413)))
(D/'SUMMARY.json').write_text(json.dumps(dict(scope='S9 development deadline stress, not formal final data',budget=180,max_workers=8,results=results,all_12_returned_within_budget=all(r['exit']==0 and r['within_budget'] and r['selected_cost'] is not None for r in results)),indent=2))
