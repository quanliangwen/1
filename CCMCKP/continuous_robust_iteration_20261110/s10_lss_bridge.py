"""Unchanged S10 search subprocess; original LSS decision/output after search."""
from pathlib import Path
import ast,copy,json,gzip,subprocess,time,hashlib
import numpy as np
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def bind(experiment,original_module,root,study,output,capacity,registration):
 H=Path(root);D=Path(study);O=Path(output);state={};S=D/'S10_source'
 def construct(Evaluation,Aw,Au,fi,CL,T,param,MC,quick):
  if {p.name:sha(p) for p in S.glob('*.py')}!=registration['S10_source_sha256']:raise RuntimeError('Original S10 search code changed')
  file=O/'S10_search.json.gz';command=['/home/junhao/miniconda3/bin/python','-u',str(S/'run.py'),'--instance',registration['benchmark'],'--capacity',str(capacity),'--seed',str(registration['search_seed']),'--seconds','600','--out',str(file)]
  with (O/'S10_search.log').open('x') as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=640)
  if p.returncode:raise RuntimeError('Fresh original S10 search failed')
  data=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(str(file)+'.run.json'))
  if meta['source_sha256']!=registration['S10_source_sha256'] or not meta['within_budget'] or data['status']!='completed' or data['schema']!='CCMCKP_S10_raw_constraint_portfolio' or meta['seed']!=registration['search_seed'] or data['capacity']!=capacity:raise RuntimeError('Actual S10 identity/source/budget differs')
  pool=data['candidate_shortlist']
  if not pool or pool!=sorted(pool,key=lambda r:(r['cost'],r['selection'])):raise RuntimeError('Original S10 did not produce cost-ordered candidates')
  state.update(data=data,meta=meta,result_file=file,original_LSS_evaluations=0,probability_trace=[])
  for row in pool:
   q=np.asarray(row['selection'],dtype=int);prob=original_module.Solution_Evaluation(Evaluation,q,T,fi,CL,param,MC,quick);state['original_LSS_evaluations']+=1
   state['probability_trace'].append(dict(stage='S10_result_to_LSS_initial',selection=row['selection'],probability=prob))
   if prob>=CL:
    c=original_module.solution_cost(q,fi);return q,c,prob,state['original_LSS_evaluations'],[[c,prob,q,state['original_LSS_evaluations']]]
  raise RuntimeError('No S10-generated candidate passes original LSS decision')
 source=Path(original_module.__file__);tree=ast.parse(source.read_text(encoding='utf8'));fn=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='Local_Search_DD'))
 loop=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.While));update=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and getattr(n.value.func,'id','')=='UpdateFeasibleSolutionList');tail=ast.dump(ast.Module(body=fn.body[update:],type_ignores=[]),include_attributes=False)
 def feed_s10_pool(Evaluation,fi,CL,T,param,MC,quick,CostList,MonteCarloList,Eval_times,Tem_solution):
  # No new candidate generation here: all vectors come from this fresh S10 run.
  for row in state['data']['candidate_shortlist']:
   q=np.asarray(row['selection'],dtype=int);prob=original_module.Solution_Evaluation(Evaluation,q,T,fi,CL,param,MC,quick);Eval_times+=1;state['original_LSS_evaluations']+=1
   state['probability_trace'].append(dict(stage='S10_pool_original_LSS_decision',selection=row['selection'],probability=prob))
   if prob>=CL:
    c=original_module.solution_cost(q,fi);original_module.FeasibleSolutionList(q,c,prob,CostList,MonteCarloList);Tem_solution.append([c,prob,q,Eval_times])
  return Eval_times
 replacement=ast.parse('Eval_times = feed_s10_pool(EvaluationFunction,FactortoObject,ConfidenceLevel,T_max,param,MonteCarloTimes,QuickCheckList,CostList,MonteCarloList,Eval_times,Tem_solution)').body
 fn.body=fn.body[:loop]+replacement+fn.body[update:];env=dict(vars(original_module),feed_s10_pool=feed_s10_pool);exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(source)+' [S10 search bridge]','exec'),env)
 actual_tail=ast.dump(ast.Module(body=fn.body[loop+len(replacement):],type_ignores=[]),include_attributes=False)
 if tail!=actual_tail:raise RuntimeError('Original LSS pool update/output selection changed')
 experiment.Construct_Procedure=construct;experiment.Local_Search_DD=env['Local_Search_DD'];state['original_output_tail_AST_sha256']=hashlib.sha256(tail.encode()).hexdigest()
 return state
