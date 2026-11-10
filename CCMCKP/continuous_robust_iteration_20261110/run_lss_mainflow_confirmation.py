"""Run unchanged original LSS experiment main, with only search-stage replacement."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,json,hashlib,time,random,importlib,csv,contextlib,argparse
H=Path(__file__).resolve().parent;D=H/'iterations/I017_LSS_mainflow_two_case_confirmation';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(capacity):
 reg=json.load(open(D/'REGISTRATION.json'));m=json.load(open(D/'SOURCE_MANIFEST.json'));O=D/('case_T'+str(capacity));O.mkdir(exist_ok=True);out=O/'CONFIRMATION.json'
 if out.exists() or (O/'RUN_STARTED.json').exists():raise RuntimeError('Confirmation may already run; never overwrite')
 if capacity not in [c['capacity'] for c in reg['cases']]:raise RuntimeError('Unregistered case')
 for r in m['files']:
  if sha(H/r['path'])!=r['sha256']:raise RuntimeError('Frozen source changed')
 with (O/'RUN_STARTED.json').open('x') as f:json.dump(dict(time=time.time(),pid=os.getpid(),capacity=capacity),f)
 from reference_loader import manifest,estimator
 import numpy as np,scipy
 if np.__version__!='1.24.4' or scipy.__version__!='1.10.1':raise RuntimeError('Original LSS numerical environment required')
 experiment=importlib.import_module('src.exp_Result_Localsearch');original=importlib.import_module('src.functions.func_localsearch');factor_module=importlib.import_module('src.functions.func_solution_factor')
 sys.path.insert(0,str(D));from lss_aligned_search import build
 adapted,proof=build(original);experiment.Local_Search_DD=adapted
 # Configure the original writer's root; its CSV/selection/evaluation code stays unchanged.
 experiment.my_file.REPO_DIR=str(O);(O/'result/Localsearch').mkdir(parents=True,exist_ok=True)
 instance='/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_3_5_30_';param=['3','5','30'];names=[f'LocalSearch_app_3_5_30_{capacity}_{i}.csv' for i in range(4)];record=f'LocalSearch_app_3_5_30_{capacity}_record.csv'
 random.seed(reg['search_seed']);np.random.seed(reg['search_seed']);quick=estimator.factorization_list(30,3,.99,10,50);Evaluation=estimator.advanced_exact_evaluation if 30**3<10**7 else estimator.advanced_monte_carlo
 started=time.monotonic()
 with (O/'mainflow.log').open('x') as log,contextlib.redirect_stdout(log):
  experiment.create_csv(*names,record)
  Aw,Au,Av,fi=factor_module.Statistic_factor(param,5,instance)
  experiment.param_test(Aw,Au,Av,fi,param,capacity,.99,reg['MC_sample_size'],Evaluation,30,*names,record,reg['real_P_seed'],quick,instance,'app',0)
 raw=O/'result/Localsearch'/names[0]
 with raw.open() as f:rows=list(csv.DictReader(f))
 if len(rows)!=1:raise RuntimeError('Expected one actual original mainflow row')
 r=rows[0]
 for file in manifest['files']:
  if sha(H/'reference'/file['path'])!=file['sha256']:raise RuntimeError('Original LSS source changed')
 result=dict(scope=reg['scope'],instance='APP_3_5_30_',capacity=capacity,cost=float(r['Cost']),cost_6dp=format(float(r['Cost']),'.6f'),confidence_level=float(r['Confidence Level']),real_confidence_level=float(r['Real Confidence Level']),solution=r['Solution'],running_time=float(r['Running Time']),original_csv=raw.relative_to(H).as_posix(),original_csv_sha256=sha(raw),original_output_tail_AST_unchanged=proof['original_output_tail_AST_unchanged'],original_tail_AST_sha256=hashlib.sha256(proof['original_tail_AST'].encode()).hexdigest(),original_evaluation_function=Evaluation.__name__,original_param_test_and_writers_unmodified=True,original_construct_and_postsearch_pool_update_unmodified=True,original_reference_sources_verified=len(manifest['files']),true_probability_hard_gate=False,independent_raw_integer_hard_gate=False,numpy=np.__version__,scipy=scipy.__version__,wall_including_real_probability_reporting=time.monotonic()-started,registration_sha256=sha(D/'REGISTRATION.json'))
 if result['original_tail_AST_sha256']!=reg['original_output_tail_AST_sha256'] or result['confidence_level']<.99:raise RuntimeError('Original LSS decision/output contract differs')
 with out.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,choices=[21,27],required=True);run(p.parse_args().capacity)
