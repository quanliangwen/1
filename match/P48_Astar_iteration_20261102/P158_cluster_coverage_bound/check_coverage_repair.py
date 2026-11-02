"""Captured-model single-site coverage repair diagnostic; no owner routes."""
from pathlib import Path
import json,time
import cv2,numpy as np
F=Path(__file__).resolve().parent;dest=F/'COVERAGE_REPAIR_FIRST.json';assert not dest.exists()
s=json.loads((F/'RESULT_FIRST.json').read_text())['snapshots'][0];diagnosis=json.loads((F/'GLOBAL_PRIORITY_FIRST.json').read_text())
v=np.asarray(s['values'],np.float32);allowed=np.asarray(s['allowed'],bool);xx=np.asarray(s['xx']);yy=np.asarray(s['yy']);radius=s['radius'];cell=s['cell'];sep=40+.71*cell
rc=int(np.ceil(radius/cell));ky,kx=np.mgrid[-rc:rc+1,-rc:rc+1];disk=((kx*cell)**2+(ky*cell)**2<=radius**2+1e-8).astype(np.float32)
rows=[];started=time.perf_counter()
for index in diagnosis['new_order'][:4]:
 item=diagnosis['rows'][index];region=np.asarray(s['corners'][index]['region'],bool);points=[np.array(p)for p in item['constructions'][0]['points']]
 masks=[(xx-p[0])**2+(yy-p[1])**2<=radius**2+1e-8 for p in points]
 inside=[bool(region[np.argmin(abs(yy[:,0]-p[1])),np.argmin(abs(xx[0,:]-p[0]))])for p in points]
 counts=np.sum(masks,axis=0);history=[]
 for iteration in range(20):
  value=float(v[counts>0].sum());best=None
  for i,p in enumerate(points):
   after=counts-masks[i];remaining=np.where(after>0,0,v).astype(np.float32)
   gains=cv2.filter2D(remaining,-1,disk,borderType=cv2.BORDER_CONSTANT)
   legal=allowed.copy()
   if sum(inside)-int(inside[i])<6:legal &= region
   for j,q in enumerate(points):
    if j!=i:legal &= (xx-q[0])**2+(yy-q[1])**2>=sep**2-1e-8
   if not legal.any():continue
   gains[~legal]=-np.inf;flat=int(np.argmax(gains));loc=np.unravel_index(flat,v.shape)
   newmask=(xx-xx[loc])**2+(yy-yy[loc])**2<=radius**2+1e-8
   score=float(v[(after>0)|newmask].sum())
   if score>value+1e-5 and(best is None or score>best[0]+1e-5):best=(score,i,loc,newmask,after)
  if best is None:break
  score,i,loc,newmask,after=best;points[i]=np.array([xx[loc],yy[loc]]);masks[i]=newmask;counts=after+newmask;inside[i]=bool(region[loc]);history.append(score)
 rows.append(dict(index=index,before_ratio=item['constructions'][0]['ratio'],after_ratio=float(v[counts>0].sum())/s['baseline'],moves=len(history),history=history,points=[p.tolist()for p in points],clustered=sum(inside)))
out=dict(status='COMPLETE_CAPTURED_MODEL_BOUNDED_COVERAGE_REPAIR',rows=rows,seconds=time.perf_counter()-started,SDK_frames_added=0,native_rounds=0,limitations='Author captured belief only; preserves six/spacing on same grid, ignores ownership/actual paths/dynamics; not game or exact global-optimum guarantee.')
dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
