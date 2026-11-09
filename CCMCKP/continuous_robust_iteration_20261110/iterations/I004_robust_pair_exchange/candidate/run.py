import os,sys
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'vendor313'))
import argparse,time,json,hashlib,random,math,resource
ap=argparse.ArgumentParser();ap.add_argument('--instance',required=True);ap.add_argument('--capacity',required=True,type=float);ap.add_argument('--seed',type=int,required=True);ap.add_argument('--seconds',type=float,default=600);ap.add_argument('--out',required=True);ap.add_argument('--risk-method',choices=['none','cvar','gamma','mix','cdf_lns','ellipsoid','pair_exchange'],default='pair_exchange');ap.add_argument('--phase-seconds',type=float,default=180);a=ap.parse_args()
if not 30<=a.seconds<=600 or not math.isfinite(a.capacity) or a.capacity<=0:ap.error('invalid capacity or budget')
os.environ['S2_SEARCH_SEED']=str(a.seed)
out=Path(a.out).resolve();bench=Path(a.instance).resolve();out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise RuntimeError('No overwrite')
with out.with_name(out.name+'.lock').open('x') as f:f.write(str(os.getpid()))
source_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
inputs=[bench/'cost.txt',bench/'node_to_factor.pkl']+[p for p in bench.glob('*_sample.txt') if not p.name.endswith('_big_sample.txt')]
input_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
reads=set();protected=bench.parent.parent;task=ROOT.parent;project_scope=ROOT.parents[3];own={str(out),str(out)+'.tmp',str(out)+'.run.json',str(out)+'.run.json.tmp',str(out.parent)}
def guard(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if p.name.endswith('_dist.txt'):raise PermissionError('True-distribution parameters cannot enter the optimizer')
 if p==protected or protected in p.parents:
  if p!=bench and bench not in p.parents:raise PermissionError('Historical or other benchmark input: '+str(p))
  reads.add(str(p))
 if p==project_scope or project_scope in p.parents:
  if p!=ROOT and ROOT not in p.parents and p!=(task/'vendor313').resolve() and (task/'vendor313').resolve() not in p.parents and str(p) not in own:raise PermissionError('Cross-run/task input: '+str(p))
  reads.add(str(p))
sys.addaudithook(guard)
import numpy as np,scipy,flint
from instance import load_instance
from risk_solver import StrictSolver
from engine import atomic_json
random.seed(a.seed);np.random.seed(a.seed);started=time.monotonic();inst=load_instance(bench);s=StrictSolver(inst,a.capacity,a.seed,a.seconds,out,started,'B_CDF_DRO_MITM',risk_method=a.risk_method,phase_seconds=a.phase_seconds);s.run();elapsed=time.monotonic()-started
atomic_json(out.with_name(out.name+'.run.json'),dict(schema='I004_robust_pair_exchange_worker',risk_method=a.risk_method,elapsed=elapsed,within_budget=elapsed<=a.seconds,selected=s.best,seed=a.seed,budget=a.seconds,source_sha256=source_sha,input_sha256=input_sha,opened_task_paths=sorted(reads),python=sys.version,numpy=np.__version__,scipy=scipy.__version__,flint=flint.__version__,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,search_seed=a.seed))
print(json.dumps(dict(elapsed=elapsed,selected=s.best)),flush=True)
