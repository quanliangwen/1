import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import pathlib,sys,time,json,itertools,numpy as np
H=pathlib.Path(__file__).parent;sys.path[:0]=[str(H/'vendor313'),str(H/'candidate')]
from small_guidance import all_small_guides
rng=np.random.default_rng(1109);errors=[]
for m,k,B in [(3,2,64),(4,3,128),(5,2,64)]:
 groups=[np.arange(i*k,(i+1)*k) for i in range(m)];h=rng.random((m*k,B));h[:,B//3:]=0.;h=h/h.sum(axis=1)[:,None]*.997
 scores,complete=all_small_guides(groups,h,time.monotonic()+20);assert complete and len(scores)==k**m
 for s,p in scores.items():
  v=np.array([1.])
  for j in s:v=np.convolve(v,h[j])
  expected=v[:B].sum();errors.append(abs(p-expected));assert abs(p-expected)<1e-12
x,c=all_small_guides([np.array([0]),np.array([1])],np.ones((2,16))/16,time.monotonic()-1);assert not c and not x
from instance import load_instance
from strict_solver import StrictSolver
inst=load_instance('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_5_10_30_');sol=StrictSolver(inst,16.,955311,600,H/'test_not_a_run.json.gz',time.monotonic(),'B_CDF_DRO_MITM');anchor=tuple(int(g[0]) for g in sol.groups);sol.gradients(anchor);start=time.monotonic();scores,complete=all_small_guides(sol.groups,sol.guide_hist,start+60);seconds=time.monotonic()-start;assert complete and len(scores)==100000
keys=list(scores);diff=[]
for k in rng.choice(len(keys),size=100,replace=False):
 s=keys[int(k)];diff.append(abs(scores[s]-sol.guide_probability(s)))
assert max(diff)<2e-7
r=dict(synthetic_max_error=max(errors),expired_deadline_returns_no_work=True,real_instance='APP_5_10_30_',real_model_choices=len(scores),real_batch_seconds=seconds,real_model_reference_FFT_comparisons=100,maximum_error_vs_original_tilted_FFT=max(diff),complete=complete,not_a_formal_or_development_search=True);(H/'BATCH_GUIDANCE_VERIFICATION.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
