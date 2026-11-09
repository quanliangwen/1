"""Convenience wrapper for one independent S10 search and LSS postselection.

Uses the identical frozen worker and original evaluation executable used by the
40x30 campaign. It does not modify or feed validation results into the search.
"""
import argparse,pathlib,subprocess,json,gzip,time,hashlib,sys
H=pathlib.Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--instance',required=True);ap.add_argument('--capacity',type=float,required=True);ap.add_argument('--seed',type=int,required=True);ap.add_argument('--seconds',type=float,default=600);ap.add_argument('--out-dir',required=True);ap.add_argument('--solver-python',default='/home/junhao/miniconda3/bin/python');ap.add_argument('--lss-python',default='python3');a=ap.parse_args()
D=pathlib.Path(a.out_dir).resolve();D.mkdir(parents=True,exist_ok=False);out=D/'search.json.gz';started=time.monotonic()
with (D/'search.log').open('x') as log:
 r=subprocess.run([a.solver_python,'-u',str(H/'frozen_candidate/run.py'),'--instance',str(pathlib.Path(a.instance).resolve()),'--capacity',str(a.capacity),'--seed',str(a.seed),'--seconds',str(a.seconds),'--out',str(out)],stdout=log,stderr=subprocess.STDOUT)
if r.returncode:raise RuntimeError('Search failed; retained search.log')
data=json.loads(gzip.decompress(out.read_bytes()));meta=json.load(open(str(out)+'.run.json'));tested=[];selected=None
if data['status']!='completed':raise RuntimeError('Incomplete search')
for candidate in sorted(data['candidate_shortlist'],key=lambda c:(c['cost'],c['selection'])):
 identity=dict(instance=data['instance'],capacity=float(a.capacity),selection=candidate['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();call=D/(key+'.json')
 with (D/(key+'.log')).open('x') as log:
  r=subprocess.run([a.lss_python,str(H/'native_lss_eval.py'),'--instance',str(pathlib.Path(a.instance).resolve()),'--capacity',str(a.capacity),'--selection',json.dumps(candidate['selection']),'--out',str(call)],stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError('LSS call failed; retained '+key+'.log')
 result=json.load(open(call));tested.append(dict(key=key,cost=candidate['cost'],selection=candidate['selection'],real_probability=result['real_probability'],passed=result['passed'],original_call_seconds=result['seconds']))
 if result['passed']:
  selected=dict(candidate,real_probability=result['real_probability'],LSS_key=key);break
result=dict(schema='S10_one_case_search_plus_LSS_postselection',seed=a.seed,accepted=selected is not None,selected=selected,tested=tested,search_seconds=meta['elapsed'],logical_MC_seconds=sum(c['original_call_seconds'] for c in tested),actual_pipeline_wall_seconds=time.monotonic()-started,raw_best=data['selected'],tail_reconstruction='removed_entirely',no_validation_feedback_into_search=True,formal_campaign=False)
with (D/'RESULT.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(accepted=result['accepted'],cost=selected['cost'] if selected else None,real_probability=selected['real_probability'] if selected else None,tested=len(tested),seconds=result['actual_pipeline_wall_seconds'])),flush=True)
if selected is None:sys.exit(2)
