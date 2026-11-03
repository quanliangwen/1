from pathlib import Path
import ast,json,math,heapq,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
W=Path(__file__).parent;OUT=W/'deliverables';OUT.mkdir(exist_ok=True)
import sys
if len(sys.argv)<2:raise SystemExit('Usage: python analysis_reproducible.py /path/to/SDK/src/swarm_rescue')
sdk=Path(sys.argv[1]).resolve()
rels=['maps/map_07.py','maps/walls_07.py','simulation/gui_map/closed_playground.py','simulation/elements/normal_wall.py','simulation/drone/bomb_deployer.py','simulation/reporting/place_score_manager.py']
sources={rel:(sdk/rel).read_text(encoding='utf8') for rel in rels}
tree=ast.parse(sources['maps/walls_07.py']);rects=[];wall_lines=[];boxes=[]
for node in ast.walk(tree):
 if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name):continue
 if node.func.id not in ['NormalWall','NormalBox']:continue
 k={a.arg:ast.literal_eval(a.value) for a in node.keywords}
 if node.func.id=='NormalBox':
  x,y=k['up_left_point'];w,h=k['width'],k['height'];bounds=[x,y-h,x+w,y];boxes.append(bounds)
 else:
  (x0,y0),(x1,y1)=k['pos_start'],k['pos_end'];wall_lines.append([x0,y0,x1,y1])
  if x0==x1:bounds=[x0-3,min(y0,y1),x0+3,max(y0,y1)]
  else:assert y0==y1;bounds=[min(x0,x1),y0-3,max(x0,x1),y0+3]
 rects.append(bounds)
rects += [[-830,-561,-824,561],[-830,555,830,561],[824,-561,830,561],[-830,-561,830,-555]]
rects=np.array(rects,dtype=float)
disposal=[-825.5,-555,-614.5,-301]
STEP=2.0;R=135.0
xs=np.arange(-830,831,STEP);ys=np.arange(-561,562,STEP);X,Y=np.meshgrid(xs,ys)
truth=np.zeros(X.shape,bool);boundary=np.zeros(X.shape,bool)
for x0,y0,x1,y1 in rects:
 mask=(X>=x0)&(X<=x1)&(Y>=y0)&(Y<=y1);truth|=mask
 if x0<=-830 or x1>=830 or y0<=-561 or y1>=561:boundary|=mask
weights=np.where(truth,np.where(boundary,.5,1.),0.)
def clearance(p):
 p=np.atleast_2d(p);dx=np.maximum(np.maximum(rects[None,:,0]-p[:,None,0],p[:,None,0]-rects[None,:,2]),0)
 dy=np.maximum(np.maximum(rects[None,:,1]-p[:,None,1],p[:,None,1]-rects[None,:,3]),0)
 return np.sqrt(dx*dx+dy*dy).min(axis=1)
gx=np.arange(-790,791,20);gy=np.arange(-521,522,20);GX,GY=np.meshgrid(gx,gy)
points=np.column_stack((GX.ravel(),GY.ravel()));clear=clearance(points).reshape(GX.shape);free=clear>=35
dist=np.full(free.shape,np.inf);prev={};start=(int(np.argmin(abs(gy+428))),int(np.argmin(abs(gx+720))))
assert free[start];dist[start]=0;queue=[(0.,start)]
while queue:
 cost,(i,j)=heapq.heappop(queue)
 if cost!=dist[i,j]:continue
 for di,dj in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
  ni,nj=i+di,j+dj
  if not(0<=ni<len(gy) and 0<=nj<len(gx)) or not free[ni,nj]:continue
  if di and dj and not(free[i,nj] and free[ni,j]):continue
  mid=((gx[j]+gx[nj])/2,(gy[i]+gy[ni])/2)
  if clearance(mid)[0]<35:continue
  nc=cost+20*math.hypot(di,dj)
  if nc<dist[ni,nj]:dist[ni,nj]=nc;prev[(ni,nj)]=(i,j);heapq.heappush(queue,(nc,(ni,nj)))
valid=free&np.isfinite(dist)
valid &= ~((GX>disposal[0]-12)&(GX<disposal[2]+12)&(GY>disposal[1]-12)&(GY<disposal[3]+12))
ci,cj=np.where(valid);P=np.column_stack((gx[cj],gy[ci]));D=dist[ci,cj]
pi=np.rint((P[:,1]+561)/STEP).astype(int);pj=np.rint((P[:,0]+830)/STEP).astype(int)
maze=(P[:,0]<-200)&(P[:,1]>-297)
detour=D/np.maximum(np.hypot(P[:,0]+720,P[:,1]+428),1)
kr=int(math.ceil(R/STEP));kY,kX=np.mgrid[-kr:kr+1,-kr:kr+1];kernel=(kX*kX+kY*kY)<=(R/STEP)**2
fft_shape=tuple(2**int(math.ceil(math.log2(v))) for v in [truth.shape[0]+2*kr,truth.shape[1]+2*kr])
KF=np.fft.rfft2(kernel,fft_shape)
def gainmap(covered):
 conv=np.fft.irfft2(np.fft.rfft2(weights*(~covered),fft_shape)*KF,fft_shape)
 return conv[kr:kr+truth.shape[0],kr:kr+truth.shape[1]][pi,pj]
def mask(p):return (X-p[0])**2+(Y-p[1])**2<=R*R
def build(quota):
 covered=np.zeros(truth.shape,bool);chosen=[];available=np.ones(len(P),bool);rows=[]
 for turn in range(10):
  gain=gainmap(covered);eligible=available.copy()
  if turn<quota:eligible &= maze
  if not eligible.any():raise RuntimeError('no candidate')
  if turn<quota:
   # Preserve most of the best marginal wall gain; among comparable options
   # prefer longer obstacle-aware transport paths. This is not a BLUE score.
   eligible &= gain>=.85*max(gain[eligible].max(),1)
   score=D.copy()
  else:score=gain.copy()
  score[~eligible]=-np.inf;k=int(np.argmax(score));p=P[k];newmask=mask(p)
  added=float(weights[newmask&~covered].sum()*STEP**2);covered|=newmask
  chosen.append(k);rows.append({'id':turn+1,'x':int(p[0]),'y':int(p[1]),'group':'maze' if turn<quota else 'coverage','incremental_weighted_wall_area_estimate':round(added,1),'wall_clearance_world_px':round(float(clear[ci[k],cj[k]]),1),'static_path_from_disposal_world_px':round(float(D[k]),1),'static_detour_ratio':round(float(detour[k]),2),'placement_order_is_not_drone_execution_order':True})
  available &= np.hypot(P[:,0]-p[0],P[:,1]-p[1])>=24
 value=float(weights[covered].sum()*STEP**2)
 return {'maze_quota':quota,'weighted_wall_coverage_estimate':value,'points':rows,'mean_static_path_world_px':round(float(np.mean(D[chosen])),1)},covered
plans=[];base,base_mask=build(0)
for q in range(1,6):
 plan,m=build(q);plan['relative_to_same_candidate_geometric_greedy']=plan['weighted_wall_coverage_estimate']/base['weighted_wall_coverage_estimate'];plans.append((plan,m))
eligible=[(p,m) for p,m in plans if p['relative_to_same_candidate_geometric_greedy']>=.85]
chosen,covered=max(eligible,key=lambda item:item[0]['maze_quota']) if eligible else plans[0]
chosen['selected_threshold_is_heuristic_not_official']=.85
example=chosen['points'][3];node=(int(np.where(gy==example['y'])[0][0]),int(np.where(gx==example['x'])[0][0]));route=[node]
while node!=start:node=prev[node];route.append(node)
route=list(reversed(route));simple=[route[0]]
for a,b,c in zip(route,route[1:],route[2:]):
 if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):simple.append(b)
simple.append(route[-1]);example_route=[[int(gx[j]),int(gy[i])] for i,j in simple]
chosen['example_static_route']={'point_id':example['id'],'path_world':example_route,'not_actual_drone_trajectory':True}
for i,row in enumerate(chosen['points']):
 for other in chosen['points'][i+1:]:assert math.hypot(row['x']-other['x'],row['y']-other['y'])>=24
 assert row['wall_clearance_world_px']>=35
 result=clearance([row['x'],row['y']]);assert result[0]>=35
comparison=[{'maze_quota':p['maze_quota'],'weighted_wall_coverage_estimate':p['weighted_wall_coverage_estimate'],'relative_to_same_candidate_geometric_greedy':p.get('relative_to_same_candidate_geometric_greedy',1.),'mean_static_path_world_px':p['mean_static_path_world_px']} for p in [base]+[p for p,m in plans]]
result={'map':'Map07','width':1660,'height':1122,'blast_radius_ratio_assumed_from_pdf_default':.12,'blast_radius_world_px':135,'boundary_weight':.5,'number_of_points':10,'minimum_bomb_separation_sdk':24,'chosen_clearance_heuristic':35,'navigation_grid_world_px':20,'wall_coverage_sampling_world_px':2,'geometry_candidate_greedy_reference':base,'recommended_trial_layout':chosen,'quota_comparison':comparison,'world_coordinates':'map center origin; +x right; +y up','status':'STATIC_GEOMETRIC_TRIAL_ONLY_NOT_GAME_VALIDATED','limitations':['Not an official wall score; geometric masks and candidate restrictions approximate SDK rasterization.','No BLUE matches, no simulation, no actual deployment/transport qualification performed.','Path length/maze membership are difficulty proxies, not a predicted BLUE score.','The illustration assumes ten bombs; use the actual expected_count for each round.','The PDF default radius/weight are assumed; uploaded round configuration may differ.','The original image SDK version was not verified; read-only current retained public SDK geometry matches the visible schematic.','The 35px clearance, 85% retained coverage threshold and maze quota are trial heuristics, not competition rules.'],'source_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in sources.items()}}
(OUT/'layout_analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei','DejaVu Sans'];plt.rcParams['axes.unicode_minus']=False
fig=plt.figure(figsize=(16,10),facecolor='white');ax=fig.add_axes([.055,.12,.69,.78]);ax.set_aspect('equal');ax.set_xlim(-850,850);ax.set_ylim(-580,580);ax.set_facecolor('#f7f9fc')
for x0,y0,x1,y1 in rects:ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#8d96a3',ec='none',zorder=2))
overlay=np.zeros((*truth.shape,4));overlay[truth&covered]=[.12,.65,.42,.8];ax.imshow(overlay,origin='lower',extent=[xs[0]-1,xs[-1]+1,ys[0]-1,ys[-1]+1],interpolation='nearest',zorder=3)
ax.add_patch(Rectangle((disposal[0],disposal[1]),disposal[2]-disposal[0],disposal[3]-disposal[1],fc='#c7e4ff',ec='#4c8ab6',lw=1.3,zorder=4));ax.text(-720,-425,'处置区',ha='center',va='center',fontsize=11,color='#185886',zorder=5)
ax.plot([x for x,y in example_route],[y for x,y in example_route],color='#7955a8',lw=1.2,ls='--',alpha=.8,zorder=5)
for row in chosen['points']:
 x,y=row['x'],row['y'];color='#d47416' if row['group']=='maze' else '#3267b0'
 ax.add_patch(Circle((x,y),R,fc=color,ec=color,alpha=.11,lw=1.3,zorder=6));ax.add_patch(Circle((x,y),R,fill=False,ec=color,alpha=.8,lw=1.0,zorder=7))
 ax.scatter([x],[y],s=180,color=color,edgecolors='white',linewidth=1.3,zorder=8)
 ax.text(x,y,str(row['id']),ha='center',va='center',fontsize=9,fontweight='bold',color='white',zorder=9)
ax.set_xlabel('地图坐标 x（像素）',fontsize=11);ax.set_ylabel('地图坐标 y（像素）',fontsize=11);ax.tick_params(labelsize=9)
fig.text(.055,.955,'Map07：覆盖与迷宫难度兼顾的候选布局',fontsize=21,fontweight='bold',color='#182b41')
fig.text(.055,.918,'按10枚示意，尚未实赛验证；圆半径按 PDF 默认值 R = round(0.12 × 1122) = 135',fontsize=11,color='#566477')
ratio=chosen['relative_to_same_candidate_geometric_greedy'];q=chosen['maze_quota']
lines=[('橙色 1–'+str(q)+'：迷宫候选','#d47416'),('蓝色 '+str(q+1)+'–10：补足覆盖','#3267b0'),('绿色墙面：圆内被计入的墙','#159463'),('紫虚线：到4号点的静态绕行路','#7955a8'),('',None),('本图选点规则','#182b41'),('① 在可通行区域选点；离墙≥35。','#344256'),('② 任意两枚间距≥24（SDK限制）。','#344256'),('③ 先试迷宫配额，再补新增覆盖。','#344256'),('④ 近似覆盖保留率至少85%。','#344256'),('⑤ 路程与绕行只作难度代理。','#344256'),('⑥ 必须复核红队布放与蓝队回放。','#344256'),('',None),('本方案的静态比较','#182b41'),(f'迷宫配额：{q} / 10', '#344256'),(f'覆盖保留率：{ratio*100:.1f}%','#344256'),('参照=同一候选集合的覆盖贪心','#566477'),('不是官方覆盖分，也不是蓝队分。','#9a4a1d'),('',None),('圈有重叠不等于浪费：','#182b41'),('只有重复覆盖同一墙体才不加分。','#344256')]
y=.855
for text,color in lines:
 if text:fig.text(.765,y,text,fontsize=11 if '①' not in text else 10.4,color=color)
 y-=.036
fig.text(.055,.055,'几何来源：保留 SDK 的 map_07.py / walls_07.py。仅验证静态净空、图连通性、间距；未运行对抗测试。',fontsize=10,color='#566477')
fig.savefig(OUT/'map07_coordinate_layout.png',dpi=155);fig.savefig(OUT/'map07_coordinate_layout.svg');plt.close(fig)
print(json.dumps({'selected_quota':q,'retained_coverage':round(ratio,4),'comparison':comparison,'points':chosen['points']},ensure_ascii=False,indent=2))
