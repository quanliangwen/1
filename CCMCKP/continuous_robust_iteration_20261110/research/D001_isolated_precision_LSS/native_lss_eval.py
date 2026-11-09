"""Unmodified full original LSS evaluation in its original Python environment."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import pathlib,json,hashlib,time,argparse
import numpy as np
from reference_loader import H,real_module,manifest
ap=argparse.ArgumentParser();ap.add_argument('--instance',required=True);ap.add_argument('--capacity',type=float,required=True);ap.add_argument('--selection',required=True);ap.add_argument('--seed',type=int,default=832273);ap.add_argument('--out',required=True);a=ap.parse_args()
p=pathlib.Path(a.instance);s=list(map(int,json.loads(a.selection)));out=pathlib.Path(a.out)
if out.exists():raise RuntimeError('No overwrite of LSS evidence')
registry=json.load(open(H/'LSS_DATA_REFERENCE.json'));dist_sha={}
for j in s:
 name=f'{j}_dist.txt';actual=hashlib.sha256((p/name).read_bytes()).hexdigest()
 if registry['dataset_sha256'][p.name+'/'+name]!=actual:raise RuntimeError('Original distribution hash mismatch')
 dist_sha[name]=actual
t=time.monotonic();prob=float(real_module.real_P_test(np.array(s,dtype=int),a.capacity,a.seed,str(p),'app' if p.name.startswith('APP') else 'lab'))
result=dict(instance=p.name,capacity=a.capacity,selection=s,seed=a.seed,draws=10000000,event='sum<=T',real_probability=prob,passed=prob>=.985,seconds=time.monotonic()-t,original_full_module=True,original_sources_unmodified=True,aliases_only=True,reference_zip_sha256=manifest['zip_sha256'],distribution_sha256=dist_sha,source_sha256=manifest['files'],numpy=np.__version__,scipy=__import__('scipy').__version__,search_feedback=False,role='external_validation_and_postselection')
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(probability=prob,seconds=result['seconds'])),flush=True)
