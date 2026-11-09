"""Independent-start runner. Each output is new and self-contained."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
import argparse,json,time,random,hashlib,sys,math
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--instance',required=True);ap.add_argument('--capacity',required=True,type=float);ap.add_argument('--seed',type=int,default=900001);ap.add_argument('--seconds',type=float,default=600);ap.add_argument('--out',required=True);a=ap.parse_args()
if not math.isfinite(a.seconds) or not 30<=a.seconds<=600:ap.error('--seconds must be in [30,600]')
if not math.isfinite(a.capacity) or a.capacity<=0:ap.error('positive finite --capacity required')
source=Path(__file__).resolve().parent;bench=Path(a.instance).resolve();out=Path(a.out).resolve()
if not out.name.endswith('.json.gz'):ap.error('--out must end in .json.gz')
out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise RuntimeError('No overwrite')
with out.with_name(out.name+'.lock').open('x') as f:f.write(str(os.getpid()))
source_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')}
inputs=[bench/'cost.txt',bench/'node_to_factor.pkl']+sorted(bench.glob('*_sample.txt'))
inputs=[p for p in inputs if not p.name.endswith('_big_sample.txt')]
input_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
reads=set();experiment=source.parent.resolve();own={str(out.parent),str(out),str(out)+'.tmp',str(out)+'.run.json',str(out)+'.run.json.tmp'}
def guard(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve();text=str(p)
 if bench.parent==p or bench.parent in p.parents:
  if p!=bench and bench not in p.parents:raise PermissionError('Other benchmark or historical input: '+text)
  reads.add(text)
 if p==experiment or experiment in p.parents:
  if p!=source and source not in p.parents and text not in own:raise PermissionError('Cross-run input/output: '+text)
  reads.add(text)
sys.addaudithook(guard)
import numpy as np
from instance import load_instance
from stable_solver import StableSolver
from engine import atomic_json
np.random.seed(a.seed);random.seed(a.seed);started=time.monotonic();inst=load_instance(bench)
sol=StableSolver(inst,a.capacity,a.seed,a.seconds,out,started,'B_CDF_DRO_MITM');sol.run();elapsed=time.monotonic()-started
atomic_json(out.with_name(out.name+'.run.json'),dict(variant='S1',elapsed=elapsed,within_budget=elapsed<=a.seconds,selected=sol.best,seed=a.seed,budget=a.seconds,source_sha256=source_sha,input_sha256=input_sha,opened_task_paths=sorted(reads),no_historical_or_cross_run_solutions=True,numpy=np.__version__))
print(json.dumps(dict(elapsed=elapsed,selected=sol.best)),flush=True)
