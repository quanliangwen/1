"""Prepare two-case LSS-mainflow confirmation; never edit frozen legacy runs."""
from pathlib import Path
import json,hashlib,shutil,ast,zipfile,time
H=Path(__file__).resolve().parent;D=H/'iterations/I017_LSS_mainflow_two_case_confirmation';A=H/'artifact';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if (D/'REGISTRATION.json').exists():raise RuntimeError('New alignment confirmation already prepared')
D.mkdir(parents=True,exist_ok=True)
source=H/'reference/src/functions/func_localsearch.py';tree=ast.parse(source.read_text(encoding='utf8'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='Local_Search_DD')
loop=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.While));update=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and getattr(n.value.func,'id','')=='UpdateFeasibleSolutionList')
if update-loop!=3:raise RuntimeError('Unexpected original search/output boundary')
tail=ast.dump(ast.Module(body=fn.body[update:],type_ignores=[]),include_attributes=False)
code='''"""Only replace the small-instance search stage; original LSS evaluation/output.

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
'''
out=D/'lss_aligned_search.py';out.write_text(code,encoding='utf8');ast.parse(code)
reg=dict(time=time.time(),scope='ONLY user requested two small cases, full original LSS mainflow confirmation; no full40case or30run claim',cases=[dict(instance='APP_3_5_30_',capacity=21),dict(instance='APP_3_5_30_',capacity=27)],original_main='reference/src/exp_Result_Localsearch.py',original_search='reference/src/functions/func_localsearch.py',original_evaluation='reference/src/functions/func_cl_estimator.py',original_sources_sha256=json.load(open(H/'REFERENCE_SHA256.json'))['files'],algorithm_sha256=sha(out),decision='original dispatch advanced_exact_evaluation/advanced_monte_carlo and CL=.99; original Construct_Procedure, UpdateFeasibleSolutionList, outputvariants and param_test CSV writer unchanged',true_probability='original real_P_test used by original mainflow for CSV recording only; never acceptance/postselection/statistics filter',removed='external real probability hard gate; no independent integer-cert gate for output',replaced_original_search_statements=update-loop,original_output_tail_AST_sha256=hashlib.sha256(tail.encode()).hexdigest(),search_seed=9817001,MC_sample_size=1000000,real_P_seed=832273,new_runs_per_case=1,original_times_argument=0,native_python='python3 original NumPy1.24.4/SciPy1.10.1',legacy_frozen_runs_unchanged=True)
with (D/'REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
files=[out,D/'REGISTRATION.json',H/'prepare_lss_mainflow_confirmation.py',H/'run_lss_mainflow_confirmation.py',H/'reference_loader.py',H/'REFERENCE_SHA256.json',H/'RAW_REFERENCE.json']+[H/'reference'/r['path'] for r in reg['original_sources_sha256']]
if not all(p.is_file() for p in files):raise RuntimeError('Missing confirmation driver/source before source ZIP')
zfile=D/'I017_LSS_MAINFLOW_TWO_CASE_SOURCE.zip'
with zipfile.ZipFile(zfile,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(H).as_posix())
with zipfile.ZipFile(zfile) as z:assert z.testzip() is None
m=dict(file=zfile.name,bytes=zfile.stat().st_size,sha256=sha(zfile),zip_CRC_passed=True,scope=reg['scope'],files=[dict(path=p.relative_to(H).as_posix(),sha256=sha(p)) for p in files])
with (D/'SOURCE_MANIFEST.json').open('x') as f:json.dump(m,f,indent=2)
T=A/D.relative_to(H);T.mkdir(parents=True,exist_ok=True)
for p in [out,zfile,D/'REGISTRATION.json',D/'SOURCE_MANIFEST.json']:shutil.copy2(p,T/p.name)
for p in [H/'prepare_lss_mainflow_confirmation.py',H/'run_lss_mainflow_confirmation.py']:shutil.copy2(p,A/p.name)
print(json.dumps({k:v for k,v in m.items() if k!='files'}))
