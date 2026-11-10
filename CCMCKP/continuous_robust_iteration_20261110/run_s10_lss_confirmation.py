"""Fresh original S10 search plus unchanged LSS evaluator/output/recording."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,hashlib,time,random,importlib,csv,contextlib,argparse
H=Path(__file__).resolve().parent;D=H/'iterations/S10_LSS_mainflow_APP3_confirmation';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(capacity):
 reg=json.load(open(D/'REGISTRATION.json'));O=D/('case_T'+str(capacity));O.mkdir(exist_ok=True)
 if (O/'RUN_STARTED.json').exists():raise RuntimeError('Actual S10 confirmation may already run; no overwrite')
 for n,d in reg['driver_sha256'].items():
  if sha(H/n)!=d:raise RuntimeError('Frozen bridge driver changed')
 if {p.name:sha(p) for p in (D/'S10_source').glob('*.py')}!=reg['S10_source_sha256']:raise RuntimeError('S10 algorithm changed')
 with (O/'RUN_STARTED.json').open('x') as f:json.dump(dict(time=time.time(),pid=os.getpid(),capacity=capacity),f)
 from reference_loader import manifest,estimator
 import numpy as np,scipy
 from s10_lss_bridge import bind
 if np.__version__!='1.24.4' or scipy.__version__!='1.10.1':raise RuntimeError('Original LSS evaluation environment required')
 exp=importlib.import_module('src.exp_Result_Localsearch');original=importlib.import_module('src.functions.func_localsearch');factors=importlib.import_module('src.functions.func_solution_factor');state=bind(exp,original,H,D,O,capacity,reg)
 exp.my_file.REPO_DIR=str(O);(O/'result/Localsearch').mkdir(parents=True,exist_ok=True)
 names=[f'LocalSearch_app_3_5_30_{capacity}_{i}.csv' for i in range(4)];record=f'LocalSearch_app_3_5_30_{capacity}_record.csv';param=['3','5','30'];random.seed(reg['search_seed']);np.random.seed(reg['search_seed']);quick=estimator.factorization_list(30,3,.99,10,50);Evaluation=estimator.advanced_exact_evaluation if 30**3<10**7 else estimator.advanced_monte_carlo;started=time.monotonic()
 with (O/'mainflow.log').open('x') as log,contextlib.redirect_stdout(log):
  exp.create_csv(*names,record);Aw,Au,Av,fi=factors.Statistic_factor(param,5,reg['benchmark'])
  exp.param_test(Aw,Au,Av,fi,param,capacity,.99,1000000,Evaluation,30,*names,record,832273,quick,reg['benchmark'],'app',0)
 file=O/'result/Localsearch'/names[0]
 with file.open() as f:rows=list(csv.DictReader(f))
 if len(rows)!=1:raise RuntimeError('Missing actual original LSS output0 row')
 r=rows[0];data=state['data'];meta=state['meta'];q=json.loads(r['Solution'])
 if tuple(q) not in {tuple(v['selection']) for v in data['candidate_shortlist']}:raise RuntimeError('Final vector not from original S10 fresh search')
 for v in manifest['files']:
  if sha(H/'reference'/v['path'])!=v['sha256']:raise RuntimeError('Original LSS source changed')
 if {p.name:sha(p) for p in (D/'S10_source').glob('*.py')}!=reg['S10_source_sha256']:raise RuntimeError('Original S10 source changed during run')
 result=dict(instance='APP_3_5_30_',capacity=capacity,cost=float(r['Cost']),cost_6dp=format(float(r['Cost']),'.6f'),selection=q,original_LSS_confidence=float(r['Confidence Level']),recorded_real_probability=float(r['Real Confidence Level']),original_mainflow_search_seconds=float(r['Running Time']),S10_worker_search_seconds=meta['elapsed'],S10_search_seed=reg['search_seed'],S10_source_sha256=meta['source_sha256'],S10_source_files_unchanged=12,S10_original_algorithm_really_executed=True,S10_schema=data['schema'],S10_exhaustive=data['exhaustive'],S10_candidates=len(data['candidate_shortlist']),S10_result_file=state['result_file'].relative_to(H).as_posix(),S10_result_sha256=sha(state['result_file']),S10_runmeta_sha256=sha(Path(str(state['result_file'])+'.run.json')),original_output_csv=file.relative_to(H).as_posix(),original_output_csv_sha256=sha(file),original_LSS_output_tail_AST_sha256=state['original_output_tail_AST_sha256'],original_LSS_sources_unchanged=21,original_LSS_evaluation=Evaluation.__name__,original_LSS_param_test_and_CSV_writers_unchanged=True,extra_real_probability_hard_filter=False,old_S10_real_probability_postselector_called=False,search_algorithm_replaced_by_I017=False,wall_seconds_including_original_realP_reporting=time.monotonic()-started,registration_sha256=sha(D/'REGISTRATION.json'))
 with (O/'CONFIRMATION.json').open('x') as f:json.dump(result,f,indent=2)
 with (O/'ORIGINAL_LSS_DECISION_TRACE.json').open('x') as f:json.dump(state['probability_trace'],f,indent=2)
 print(json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,choices=[21,27],required=True);run(p.parse_args().capacity)
