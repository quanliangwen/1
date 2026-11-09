import pathlib,json,itertools,pickle,numpy as np,hashlib,subprocess,concurrent.futures,time,os
H=pathlib.Path(__file__).parent;D=H/'old_cost_acceptance_exhaustion';D.mkdir(exist_ok=True);B=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark');base={r['index']:r for r in json.load(open(H/'BASELINE_REFERENCE.json'))['rows']};requests={};links=[];known={}
for folder in [pathlib.Path('/home/quanliangwen/work/cdf_feasible_S2_20261109/lss_common')]+list(H.glob('*_lss')):
 for p in folder.glob('*.json'):
  try:
   v=json.load(open(p))
   if v.get('schema')=='uploaded_LSS_real_P_test':
    k=hashlib.sha256(json.dumps([v['instance'],v['capacity'],v['selection'],832273],separators=(',',':')).encode()).hexdigest();known[k]=p
  except Exception:pass
for c in json.load(open(H/'CASES.json')):
 if c['index'] not in [21,22,23,24]:continue
 p=B/c['instance'];cost=np.loadtxt(p/'cost.txt');gs=list(pickle.load(open(p/'node_to_factor.pkl','rb')).values())
 for s in itertools.product(*gs):
  s=list(map(int,s));v=float(cost[s].sum())
  if v>base[c['index']]['best']+1e-8:continue
  key=hashlib.sha256(json.dumps([c['instance'],c['tmax'],s,832273],separators=(',',':')).encode()).hexdigest();r=dict(key=key,index=c['index'],instance=c['instance'],capacity=c['tmax'],selection=s,cost=v);requests[key]=r;links.append(r)
(D/'REGISTRATION.json').write_text(json.dumps(dict(purpose='Exhaust all selections costing no more than old CDF Best for APP3/APP4 small cases; postprocessing only; no optimizer feedback',final_acceptance='uploaded original LSS real_P_test >=0.985',draws=10000000,seed=832273,requests=list(requests.values())),indent=2))
def run(t):
 key=t['key'];out=D/(key+'.json')
 if key in known:
  out.write_bytes(known[key].read_bytes());v=json.load(open(out));r=dict(**t,exit=0,reused_reference=str(known[key]),real_probability=v['real_probability'])
 else:
  cmd=['python3','-u',str(H/'lss_real_eval.py'),'--instance',str(B/t['instance']),'--capacity',str(t['capacity']),'--selection',json.dumps(t['selection']),'--out',str(out)];start=time.time()
  with open(str(out)+'.log','x') as log:
   try:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1200);code=p.returncode
   except subprocess.TimeoutExpired:code='timeout'
  r=dict(**t,exit=code,wall=time.time()-start)
  if code==0:r['real_probability']=json.load(open(out))['real_probability']
 (D/(key+'.terminal.json')).write_text(json.dumps(r));print(json.dumps({k:r[k] for k in ['index','key','exit','real_probability'] if k in r}),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(run,requests.values()))
summary=[]
for i in [21,22,23,24]:
 a=[r for r in results if r['index']==i];complete=all(r['exit']==0 for r in a);summary.append(dict(index=i,old_best=base[i]['best'],selections_at_or_below_old_best=len(a),complete=complete,max_LSS_real_probability=max((r.get('real_probability',-1) for r in a),default=None),accepted=sum(r.get('real_probability',-1)>=.985 for r in a),all_cost_prefix_selections_rejected=complete and all(r['real_probability']<.985 for r in a)))
(D/'SUMMARY.json').write_text(json.dumps(dict(scope='finite original fixed-seed LSS test on all cost-prefix selections; not a population optimality proof',rows=summary,results=results),indent=2));print('EXHAUSTION_FINISHED',flush=True)
