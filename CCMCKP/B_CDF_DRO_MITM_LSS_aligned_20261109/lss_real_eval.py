"""Run the uploaded LSS real_P_test body and generators without semantic changes.
Only import/path wiring is adapted; function AST and raw source SHA are checked.
"""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import ast,pathlib,json,argparse,hashlib,time,types,math,contextlib
import numpy as np
from scipy.stats import truncnorm,fatiguelife,gamma
H=pathlib.Path(__file__).parent;R=H/'lss_eval_reference'
manifest=json.load(open(R/'REFERENCE_MANIFEST.json'))
for name,expected in manifest['source_sha256'].items():
 if hashlib.sha256((R/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('LSS source altered: '+name)
ns=dict(np=np,math=math,truncnorm=truncnorm,fatiguelife=fatiguelife,gamma=gamma,my_file=types.SimpleNamespace(real_path_of=lambda folder,name:str(pathlib.Path(folder)/name)))
asts={}
for filename,names in [('benchmark_LAB.py',['Uniform','Fatiguelife','Truncated_norm','Bimodal','Gamma_']),('benchmark_APP.py',['Uniform_h','Fatiguelife_h','Truncated_norm_h','Bimodal_h','Gamma_h']),('func_realP_statistical.py',['real_P_test'])]:
 tree=ast.parse((R/filename).read_text(encoding='utf8'));nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if len(nodes)!=len(names):raise RuntimeError('Missing reference function')
 for n in nodes:asts[n.name]=hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(R/filename),'exec'),ns)

def evaluate(selection,capacity,instance,seed=832273):
 instance=pathlib.Path(instance);dist_sha={}
 for j in selection:
  name=f'{int(j)}_dist.txt';p=instance/name;actual=hashlib.sha256(p.read_bytes()).hexdigest();key=instance.name+'/'+name
  if manifest['dataset_sha256'].get(key)!=actual:raise RuntimeError('Reference distribution file mismatch: '+key)
  dist_sha[name]=actual
 sign='app' if instance.name.startswith('APP') else 'lab';start=time.monotonic()
 p=float(ns['real_P_test'](np.asarray(selection,dtype=int),capacity,seed,str(instance),sign))
 return dict(schema='uploaded_LSS_real_P_test',selection=list(map(int,selection)),capacity=capacity,instance=instance.name,real_probability=p,seed=seed,draws=10000000,event='sum<=T',elapsed=time.monotonic()-start,reference_zip_sha256=manifest['zip_sha256'],source_sha256=manifest['source_sha256'],function_ast_sha256=asts,distribution_sha256=dist_sha,numpy=np.__version__,scipy=__import__('scipy').__version__,threshold_not_applied=True,no_optimizer_feedback=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--instance',required=True);ap.add_argument('--capacity',type=float,required=True);ap.add_argument('--selection',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=pathlib.Path(a.out)
 if out.exists():raise RuntimeError('No overwrite')
 s=json.loads(a.selection);result=evaluate(s,a.capacity,a.instance);out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(real_probability=result['real_probability'],elapsed=result['elapsed'])))
