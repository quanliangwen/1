"""Bound actual own observed wall model; no SDK/BLUE/truth, no control output.

LP permits fractional placements, ignores spacing/routes/owner inventory.
Its conservative dual bound can reject a corner; a high bound proves nothing
about a physically executable six-bomb layout or an official score.
"""
from pathlib import Path
import json,os,time,warnings
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,hstack,vstack,eye
F=Path(__file__).resolve().parent
assert not(F/'COVERAGE_BOUND_FIRST.json').exists()
read=lambda p:json.loads(p.read_text())
result=read(F/'RESULT_FIRST.json');assert result['status']=='PASS_READONLY_OBSERVATION_IDENTITY'
s=result['snapshots'][0];allowed=np.asarray(s['allowed'],bool);values=np.asarray(s['values'],float)
xx=np.asarray(s['xx'],float);yy=np.asarray(s['yy'],float);radius=s['radius']
wall=values>0;weights=values[wall];cx=xx[allowed];cy=yy[allowed]
assert len(cx)<=10000 and len(weights)<=10000
coverage=((xx[wall,None]-cx[None,:])**2+(yy[wall,None]-cy[None,:])**2<=radius**2+1e-8)
nx=len(cx);ny=len(weights);A_cover=hstack([-csr_matrix(coverage.astype(float)),eye(ny,format='csr')],format='csr')
objective=np.r_[np.zeros(nx),weights];rows=[];started=time.perf_counter()
for idx,corner in enumerate(s['corners'][:64]):
 inside=np.asarray(corner['region'],bool)[allowed]
 if int(inside.sum())<6:
  rows.append(dict(index=idx,anchor=corner['anchor'],status='INSUFFICIENT_DISTINCT_CELLS',possible_cells=int(inside.sum()),model_rejected=True));continue
 cardinality=csr_matrix(np.r_[np.ones(nx),np.zeros(ny)][None,:])
 required=csr_matrix(np.r_[-inside.astype(float),np.zeros(ny)][None,:])
 outside=csr_matrix(np.r_[(~inside).astype(float),np.zeros(ny)][None,:])
 A=vstack([A_cover,cardinality,required,outside],format='csr');b=np.r_[np.zeros(ny),10.,-6.,4.]
 with warnings.catch_warnings(record=True)as messages:
  lp=linprog(-objective,A_ub=A,b_ub=b,bounds=(0,1),method='highs',options=dict(time_limit=3.,threads=1))
 # Any nonnegative lambda gives a valid bound over the variable box.
 # It remains conservative without trusting primal rounding or zero MIP gap.
 marg=getattr(getattr(lp,'ineqlin',None),'marginals',None)
 lam=np.zeros(len(b))if marg is None else np.maximum(0.,-np.asarray(marg,float))
 reduced=objective-A.T@lam
 raw_upper=float(b@lam+np.maximum(0.,reduced).sum())
 rounding_margin=1e-6*(1+np.abs(b@lam)+np.abs(objective).sum()+np.abs(A.T@lam).sum())
 upper=raw_upper+rounding_margin
 rows.append(dict(index=idx,pivot=corner['pivot'],anchor=corner['anchor'],LP_status=int(lp.status),message=lp.message,LP_primal=None if lp.fun is None else float(-lp.fun),conservative_upper=upper,upper_ratio=upper/s['baseline'],coverage_floor=.9,model_rejected=upper<.9*s['baseline'],rounding_margin=rounding_margin,warnings=[str(w.message)for w in messages]))
out=dict(status='COMPLETE_FRACTIONAL_RELAXATION_BOUND_DIAGNOSIS',snapshot_owner=s['owner'],snapshot_step=s['step'],snapshot_initial_total=s['initial_total'],baseline_model_union=s['baseline'],target_cluster6=True,placement_variables=nx,wall_variables=ny,eligible_corners=len(s['corners']),checked_corners=len(rows),all_eligible_checked=len(rows)==len(s['corners']),rows=rows,all_checked_rejected=bool(rows)and all(r['model_rejected']for r in rows),seconds=time.perf_counter()-started,production_dependencies_changed=False,SDK_frames_added=0,native_rounds=0,limitations=__doc__)
(F/'COVERAGE_BOUND_FIRST.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items()if k!='rows'}));print(json.dumps([dict(anchor=r['anchor'],upper_ratio=r.get('upper_ratio'),rejected=r['model_rejected'])for r in rows]))
