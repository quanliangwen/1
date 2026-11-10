import sys,os,json,ast,hashlib,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'deps'))
ROOTS={'r05':BASE/'r05/source','single':BASE/'single','double':BASE/'double/CCMCKP_dual_perturbation'}

def worker(version):
 import numpy as np
 from types import SimpleNamespace
 root=ROOTS[version];sys.path.insert(0,str(root));os.environ['CCMCKP_SEARCH_ABLATION_POLICY']=str(root/'selected_policy.json')
 from src.functions import func_tail_guided_search as mod
 from src.functions import func_tabu_search as legacy
 from src.functions.func_search_ablation import get_policy
 factors=[SimpleNamespace(id=i,cost=[10.,9.,8.,11.][i%4],samples=np.ones(30),sample_min=1.,sample_max=1.) for i in range(16)]
 nodes={c:list(range(c*4,c*4+4)) for c in range(4)}
 results={}
 def run(mc=True,**extra):
  calls=[]
  def oracle(items,tmax,M,CL,param,qc):
   value=.989 if any(f.id%4==2 for f in items) else .99
   calls.append({'ids':[f.id for f in items],'M':M,'p':value})
   return value
  oracle.reference_protocol=True;oracle.reference_mc=mc
  np.random.seed(101)
  r=mod.Data_Driven_Tabu_Search(oracle,([0,4,8,12],40.,.99,0),nodes,factors,.99,100.,[4,4,30],30,1000000,[],
   time_limit_seconds=3.,evaluation_budget=150,restart_no_improve_cycles=3,pair_exchange_pilot_samples=40,run_seed=101,**extra)
  logs=r.tabu_move_log+r.perturbation_log
  assert r.certified_feasible and r.probability+1e-12>=.99
  assert abs(sum(factors[i].cost for i in r.solution)-r.cost)<1e-9
  assert all(x['new_probability']+1e-12>=.99 for x in logs)
  assert all(x['M']==1000000 for x in calls)
  return {'solution':r.solution,'cost':r.cost,'probability':r.probability,'stop':r.stop_reason,'cycles':r.completed_cycles,
   'evaluations':r.evaluation_count,'rejected_calls':sum(x['p']<.99 for x in calls),'operators':sorted(set(x.get('operator','light') for x in r.perturbation_log)),
   'selection_policy':getattr(r,'operator_selection_policy',None),'strong_count':getattr(r,'strong_perturbation_count',None),
   'guided_count':getattr(r,'guided_perturbation_count',None),'trace':[(x['class_id'],x['old_factor'],x['new_factor'],x['new_probability']) for x in logs]}
 for mc in [True,False]:
  branch='mc' if mc else 'exact';results[branch+'_default']=run(mc)
  if version!='r05':results[branch+'_disabled']=run(mc,dual_perturbation_enabled=False)
  if version=='single':
   for policy in ['single','force_light','force_strong','force_guided','rule','ucb_w']:
    results[branch+'_'+policy]=run(mc,operator_selection_policy=policy)
 if version!='r05':
  # Intercept exact delegation; no evaluator or search behavior is mocked here.
  seen={}
  original=mod.legacy_search
  def spy(*args,**kw):seen.update(kw);return None
  mod.legacy_search=spy
  def exact(*a):return 1.
  mod.Data_Driven_Tabu_Search(exact,([],0,1,0),{},[],.99,1,[1,1,30],1,1000000,[],dual_perturbation_enabled=False,strong_perturb_no_improve=17,strong_perturb_class_ratio=.8)
  mod.legacy_search=original
  results['exact_forwarded_controls']={k:seen.get(k,'MISSING') for k in ['dual_perturbation_enabled','strong_perturb_no_improve','strong_perturb_class_ratio']}
 # Run the real unchanged author estimator, separately from the controlled oracle searches.
 from src.functions.func_reference_evaluation import reference_advanced_monte_carlo, ReferenceFactorView
 from src.functions.func_reference_author import _monte_carlo_evaluate
 assert _monte_carlo_evaluate(np.array([-1.,0.,1.]),0.)==1/3
 class RealFactor:
  def __init__(self,samples):self.samples=np.asarray(samples,dtype=float)
  def get_index_sample(self,index):return np.sort(self.samples)[::-1][index]
 special=[RealFactor([0.]*29+[100.]) for _ in range(2)]
 np.random.seed(101)
 p_real=reference_advanced_monte_carlo(special,1.,1000000,.99,[2,1,30],[])
 assert p_real==1. and reference_advanced_monte_carlo.last_samples_used==1000000
 varied=[RealFactor(np.arange(30)) for _ in range(2)]
 np.random.seed(101)
 first=reference_advanced_monte_carlo(varied,55.,1000000,.99,[2,1,30],[])
 state1=np.random.get_state()[1].copy()
 second=reference_advanced_monte_carlo(varied,55.,1000000,.99,[2,1,30],[])
 state2=np.random.get_state()[1].copy()
 assert not np.array_equal(state1,state2)
 results['real_author_estimator']={'strict_event_result':1/3,'last_sample_excluded_result':p_real,'fresh_draw_first':first,'fresh_draw_second':second,'M':1000000}
 # Verify an unconfigured direct launch does not read the adjacent policy JSON.
 del os.environ['CCMCKP_SEARCH_ABLATION_POLICY'];results['policy_without_explicit_flag_or_env']=get_policy()
 print(json.dumps(results))

if __name__=='__main__':
 if len(sys.argv)>1:worker(sys.argv[1])
 else:
  output={}
  for v in ROOTS:
   p=subprocess.run([sys.executable,__file__,v],capture_output=True,text=True)
   if p.returncode:raise RuntimeError(v+': '+p.stderr)
   output[v]=json.loads(p.stdout)
  for branch in ['mc','exact']:
   assert output['r05'][branch+'_default']['trace']==output['single'][branch+'_disabled']['trace']
  assert output['r05']['mc_default']['trace']==output['double']['mc_disabled']['trace']
  (BASE/'test_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
  for v,tests in output.items():
   print(v)
   for name,result in tests.items():print(name,{k:z for k,z in result.items() if k!='trace'})
