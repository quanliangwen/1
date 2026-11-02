"""External diagnostic of the one LP-unrejected corner; never a controller."""
from pathlib import Path
import os,json,time,warnings
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix,hstack,vstack,eye
from scipy.spatial import cKDTree
F=Path(__file__).resolve().parent;dest=F/'SPACING_BOUND_FIRST.json';assert not dest.exists()
read=lambda p:json.loads(p.read_text())
bounds=read(F/'COVERAGE_BOUND_V2_SERIALIZATION_FIXED_FIRST.json');s=read(F/'RESULT_FIRST.json')['snapshots'][0]
remaining=[r for r in bounds['rows']if not r['model_rejected']];assert len(remaining)<=2
allowed=np.asarray(s['allowed'],bool);values=np.asarray(s['values'],float);xx=np.asarray(s['xx']);yy=np.asarray(s['yy']);wall=values>0
cx=xx[allowed];cy=yy[allowed];nx=len(cx);weights=values[wall];ny=len(weights);radius=s['radius']
coverage=((xx[wall,None]-cx[None,:])**2+(yy[wall,None]-cy[None,:])**2<=radius**2+1e-8)
Acover=hstack([-csr_matrix(coverage.astype(float)),eye(ny,format='csr')],format='csr')
separation=40.+.71*s['cell'];pairs=cKDTree(np.column_stack([cx,cy])).query_pairs(separation-1e-8,output_type='ndarray')
pr=np.repeat(np.arange(len(pairs)),2);pc=pairs.ravel();Aspace=csr_matrix((np.ones(len(pc)),(pr,pc)),shape=(len(pairs),nx+ny))
rows=[];start=time.perf_counter()
for row in remaining:
 region=np.asarray(s['corners'][row['index']]['region'],bool)[allowed]
 A=vstack([Acover,Aspace,csr_matrix(np.r_[np.ones(nx),np.zeros(ny)][None,:]),csr_matrix(np.r_[-region.astype(float),np.zeros(ny)][None,:]),csr_matrix(np.r_[(~region).astype(float),np.zeros(ny)][None,:])],format='csr')
 b=np.r_[np.zeros(ny),np.ones(len(pairs)),10.,-6.,4.]
 with warnings.catch_warnings(record=True)as msgs:
  solution=milp(np.r_[np.zeros(nx),-weights],integrality=np.r_[np.ones(nx),np.zeros(ny)],bounds=Bounds(0,1),constraints=LinearConstraint(A,-np.inf,b),options=dict(time_limit=10.,threads=1,mip_rel_gap=0.))
 dual=getattr(solution,'mip_dual_bound',None);upper=None if dual is None or not np.isfinite(dual)else -float(dual)+1e-5*(1+abs(float(dual)))
 primal=None if solution.fun is None else -float(solution.fun)
 witness=[]
 if solution.x is not None:
  selected=solution.x[:nx]>.5;witness=np.column_stack([cx[selected],cy[selected]]).tolist()
 rows.append(dict(index=row['index'],anchor=row['anchor'],status=int(solution.status),message=solution.message,primal=primal,conservative_upper=upper,upper_ratio=None if upper is None else upper/s['baseline'],model_rejected=upper is not None and upper<.9*s['baseline'],witness=witness,warnings=[str(w.message)for w in msgs]))
out=dict(status='COMPLETE_SPACING_INTEGER_EXTERNAL_DIAGNOSIS',rows=rows,fixed_initial=10,required_corner=6,separation=separation,spacing_constraints=len(pairs),seconds=time.perf_counter()-start,all_captured_corners_rejected=bool(bounds['all_eligible_checked'])and all(r['model_rejected']for r in rows),scope='Only this captured observed-grid model/inner-corner domains; ignores actual owner routes and dynamics, no proof for unknown future map/continuous points; not integrated into control.',new_SDK_frames=0,new_native_rounds=0,production_dependencies_changed=False)
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
