"""Registered own-snapshot replay only; not a cold search or formal run."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import sys,json,gzip,time,hashlib
H=Path(__file__).resolve().parent;D=H/'research/third_group_repair_replay';reg=json.load(open(D/'REGISTRATION.json'));out=D/'REPLAY_RESULT.json.gz';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No own-snapshot replay repeat')
for n,d in reg['input_sha256'].items():
 if sha(H/n)!=d:raise RuntimeError('Registered replay input/source changed')
S=H/reg['candidate'];sys.path[:0]=[str(S),str(S.parent/'vendor313')]
import numpy as np
from instance import load_instance
from engine import worst_cdf_hist
from exact_oracle import ExactOracle
from third_group_repair import propose
P=Path(reg['benchmark']);source=H/reg['saved_own_result'];reads=set();allowed={source.resolve(),out.resolve(),(D/'REGISTRATION.json').resolve()}
def guard(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if p.name.endswith('_dist.txt') or 'lss_cache' in p.parts or p.name=='BASELINE_S10.json':raise PermissionError('No true/history/native input in replay')
 if H==p or H in p.parents:
  if p not in allowed and not (S==p or S in p.parents or S.parent/'vendor313'==p or S.parent/'vendor313' in p.parents):raise PermissionError('Other saved run/task not allowed in replay '+str(p))
  reads.add(str(p))
 if P==p or P in p.parents:
  if p.name not in reg['benchmark_input_sha256']:raise PermissionError('Unregistered benchmark input')
  reads.add(str(p))
sys.addaudithook(guard)
started=time.monotonic();end=started+reg['replay_seconds'];data=json.loads(gzip.decompress(source.read_bytes()));inst=load_instance(P);oracle=ExactOracle(inst,reg['capacity']);known={tuple(r['selection']) for r in data['candidate_shortlist']};pairs={};pairrecord=data['extension']['pair_cover']['robust_pairs']['records']
for r in pairrecord:
 if r['kind']!='joint_pair_neighborhood':continue
 for check in r['checked']:
  q=tuple(check['selection']);center=tuple(r['center'])
  if sum(a!=b for a,b in zip(q,center))==2:pairs[(center,q,r['delta'])]=dict(center=center,pair=q,delta=r['delta'],cost=check['cost'])
queue=sorted(pairs.values(),key=lambda r:(r['cost'],r['center'],r['pair'],r['delta']))[:reg['max_pair_centers']];histograms={};done=set();records=[];accepted=[];visited=0;generated=0
for item in queue:
 if time.monotonic()>end-1:break
 delta=item['delta']
 if delta not in histograms:histograms[delta]=np.asarray([worst_cdf_hist(a,reg['capacity'],reg['bins'],delta) for a in inst.samples])
 rows=propose(inst.groups,inst.costs,histograms[delta],item['center'],item['pair']);visited+=1;generated+=len(rows)
 for r in rows:
  q=tuple(r['selection'])
  if q in known or q in done:continue
  if time.monotonic()>end-.5:break
  done.add(q);cert=oracle.certify(q,reg['bins'],include_upper=True);r=dict(r,center=list(item['center']),pair=list(item['pair']),delta=delta,certificate=cert)
  r['classification']='raw_certified' if cert['accepted'] else 'integer_raw_refuted' if cert['infeasible'] else 'unresolved';records.append(r)
  if cert['accepted']:accepted.append(r)
elapsed=time.monotonic()-started
result=dict(scope=__doc__,registration_sha256=sha(D/'REGISTRATION.json'),source_saved_result_sha256=reg['input_sha256'][reg['saved_own_result']],old_complete_pool_members=len(known),saved_pair_centers=len(pairs),queued_pair_centers=len(queue),visited_pair_centers=visited,generated_proposals=generated,unique_fresh_checked=len(done),accepted_new_raw=len(accepted),integer_refuted=sum(r['classification']=='integer_raw_refuted' for r in records),unresolved=sum(r['classification']=='unresolved' for r in records),accepted=sorted(accepted,key=lambda r:(r['cost'],r['selection'])),records=records,seconds=elapsed,replay_budget=reg['replay_seconds'],within_replay_budget=elapsed<=reg['replay_seconds'],opened_paths=sorted(reads),new_original_MC_calls=0,old_pool_never_removed=True,no_native_qualification_claim=True,no_cold_timing_or_Avg_claim=True)
with out.open('xb') as f:f.write(gzip.compress(json.dumps(result).encode(),compresslevel=6))
print(json.dumps({k:v for k,v in result.items() if k not in ['records','accepted','opened_paths']}),flush=True)
