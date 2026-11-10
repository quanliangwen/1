"""Only replace the small-instance search stage; original LSS evaluation/output.

This confirmation deliberately supports only APP_3_5_30 with T21/T27. It reuses
the current solver's cost-ordered complete small-case search, with the ORIGINAL
LSS evaluator as its sole feasibility decision. No true-probability selection.
"""
import itertools,ast,copy
import numpy as np
from pathlib import Path

def build(original_module):
 source=Path(original_module.__file__);tree=ast.parse(source.read_text(encoding='utf8'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='Local_Search_DD');fn=copy.deepcopy(fn)
 loop=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.While));update=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and getattr(n.value.func,'id','')=='UpdateFeasibleSolutionList')
 before=ast.dump(ast.Module(body=fn.body[update:],type_ignores=[]),include_attributes=False)
 def exhaustive_stage(EvaluationFunction,node_resort_v,fi,CL,T,param,MC,quick,CostList,MonteCarloList,Eval_times,Tem_solution):
  if list(map(int,param[:3]))!=[3,5,30] or float(T) not in [21.,27.]:raise ValueError('Two requested small cases only; no unverified large-case claim')
  groups=[node_resort_v[k] for k in sorted(node_resort_v)];choices=sorted(itertools.product(*groups),key=lambda q:(original_module.solution_cost(q,fi),q))
  for q in choices:
   probability=original_module.Solution_Evaluation(EvaluationFunction,np.asarray(q,dtype=int),T,fi,CL,param,MC,quick);Eval_times+=1
   if probability>=CL:
    cost=original_module.solution_cost(q,fi);original_module.FeasibleSolutionList(np.asarray(q,dtype=int),cost,probability,CostList,MonteCarloList);Tem_solution.append([cost,probability,np.asarray(q,dtype=int),Eval_times])
  return Eval_times
 replacement=ast.parse('Eval_times = exhaustive_stage(EvaluationFunction,node_resort_v,FactortoObject,ConfidenceLevel,T_max,param,MonteCarloTimes,QuickCheckList,CostList,MonteCarloList,Eval_times,Tem_solution)').body
 fn.body=fn.body[:loop]+replacement+fn.body[update:];env=dict(vars(original_module),exhaustive_stage=exhaustive_stage);adapted=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));exec(compile(adapted,str(source)+' [search-stage-only adapter]','exec'),env)
 after=ast.dump(ast.Module(body=fn.body[loop+len(replacement):],type_ignores=[]),include_attributes=False)
 if before!=after:raise RuntimeError('Original LSS update/selection/output code changed')
 return env['Local_Search_DD'],dict(original_output_tail_AST_unchanged=True,replaced_original_statements=update-loop,original_tail_AST=before)
