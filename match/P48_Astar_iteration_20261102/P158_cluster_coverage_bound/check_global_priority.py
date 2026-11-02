"""Construction diagnostic on captured own model; ignores owner routes only.
No controller, new SDK, new score, true map or historical policy input.
"""
from pathlib import Path
import json
import cv2,numpy as np
F=Path(__file__).resolve().parent;dest=F/'GLOBAL_PRIORITY_FIRST.json';assert not dest.exists()
s=json.loads((F/'RESULT_FIRST.json').read_text())['snapshots'][0]
values=np.asarray(s['values'],np.float32);allowed=np.asarray(s['allowed'],bool);xx=np.asarray(s['xx']);yy=np.asarray(s['yy']);radius=s['radius'];cell=s['cell'];sep=40.+.71*cell
rc=int(np.ceil(radius/cell));ky,kx=np.mgrid[-rc:rc+1,-rc:rc+1];disk=((kx*cell)**2+(ky*cell)**2<=radius**2+1e-8).astype(np.float32)
rows=[]
for i,c in enumerate(s['corners']):
 region=np.asarray(c['region'],bool)
 potential=cv2.filter2D(region.astype(np.float32),-1,disk,borderType=cv2.BORDER_CONSTANT)>.5
 remain=values.copy();remain[potential]=0;outside_added=0.;valid=allowed.copy()&~region
 for _ in range(4):
  if not valid.any():break
  gains=cv2.filter2D(remain,-1,disk,borderType=cv2.BORDER_CONSTANT);gains[~valid]=-np.inf;flat=int(np.argmax(gains));loc=np.unravel_index(flat,values.shape)
  mask=(xx-xx[loc])**2+(yy-yy[loc])**2<=radius**2+1e-8
  outside_added+=float(remain[mask].sum());remain[mask]=0
  valid[(xx-xx[loc])**2+(yy-yy[loc])**2<sep**2]=False
 priority=float(values[potential].sum())+outside_added
 constructions=[]
 for cluster_first in [True,False]:
  remaining=values.copy();valid=allowed.copy();points=[];possible=True
  for stage in ([('in',6),('out',4)]if cluster_first else[('out',4),('in',6)]):
   kind,count=stage
   for _ in range(count):
    feasible=valid&(region if kind=='in'else~region)
    if not feasible.any():possible=False;break
    gains=cv2.filter2D(remaining,-1,disk,borderType=cv2.BORDER_CONSTANT);gains[~feasible]=-np.inf;loc=np.unravel_index(int(np.argmax(gains)),values.shape)
    p=[float(xx[loc]),float(yy[loc])];points.append(p)
    squared=(xx-p[0])**2+(yy-p[1])**2;remaining[squared<=radius**2+1e-8]=0;valid[squared<sep**2]=False
   if not possible:break
  coverage=float(values.sum()-remaining.sum());constructions.append(dict(cluster_first=cluster_first,complete=possible and len(points)==10,coverage=coverage,ratio=coverage/s['baseline'],points=points))
 rows.append(dict(index=i,anchor=c['anchor'],original_rank=c['rank'],global_priority=priority,constructions=constructions))
new_order=[r['index']for r in sorted(rows,key=lambda r:(-r['global_priority'],r['index']))]
out=dict(status='COMPLETE_CAPTURED_MODEL_GLOBAL_PRIORITY_CONSTRUCTION',rows=rows,original_order=list(range(len(rows))),new_order=new_order,SDK_frames_added=0,native_rounds=0,limitations=__doc__)
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(new_order=new_order,ratios=[dict(index=r['index'],priority=r['global_priority'],ratios=[a['ratio']for a in r['constructions']])for r in rows])))
