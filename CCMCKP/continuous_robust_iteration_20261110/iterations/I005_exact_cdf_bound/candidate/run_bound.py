import os,sys
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'vendor313'))
import argparse,hashlib,time,json
ap=argparse.ArgumentParser();ap.add_argument('--instance',required=True);ap.add_argument('--capacity',required=True);ap.add_argument('--cost-limit',required=True);ap.add_argument('--bins',type=int,default=256);ap.add_argument('--seconds',type=float,default=30);ap.add_argument('--out',required=True);a=ap.parse_args()
bench=Path(a.instance).resolve();out=Path(a.out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
own={str(out),str(out)+'.proof.jsonl.gz',str(out)+'.run.json',str(out.parent)}
if any(Path(x).exists() for x in own if x!=str(out.parent)):raise RuntimeError('No overwrite')
source_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')};inputs=[bench/'cost.txt',bench/'node_to_factor.pkl']+[p for p in bench.glob('*_sample.txt') if not p.name.endswith('_big_sample.txt')];input_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs};reads=set();work_scope=ROOT.parents[3];protected=bench.parent.parent;vendor=(ROOT.parent/'vendor313').resolve()
def guard(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if p.name.endswith('_dist.txt'):raise PermissionError('No true distribution in proof search')
 if p==protected or protected in p.parents:
  if p!=bench and bench not in p.parents:raise PermissionError('Other benchmark/history data')
  reads.add(str(p))
 if p==work_scope or work_scope in p.parents:
  if p!=ROOT and ROOT not in p.parents and p!=vendor and vendor not in p.parents and str(p) not in own:raise PermissionError('Cross-run/history/cache input')
  reads.add(str(p))
sys.addaudithook(guard)
from instance import load_instance
from prefix_bound import PrefixBound
start=time.monotonic();inst=load_instance(bench);bound=PrefixBound(inst,a.capacity,a.cost_limit,a.bins,a.seconds,out);result=bound.run()
with Path(str(out)+'.run.json').open('x') as f:json.dump(dict(source_sha256=source_sha,input_sha256=input_sha,opened_task_paths=sorted(reads),seconds=time.monotonic()-start,budget=a.seconds,no_true_distribution=True,no_historical_vector=True),f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['pending_frontier','candidates','groups']}),flush=True)
