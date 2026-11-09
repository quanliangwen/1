import pathlib,json,numpy as np,pickle,itertools,math
H=pathlib.Path(__file__).parent;B=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark');base={r['index']:r for r in json.load(open(H/'BASELINE_REFERENCE.json'))['rows']}
for c in json.load(open(H/'CASES.json')):
 if not 21<=c['index']<=28:continue
 p=B/c['instance'];cost=np.loadtxt(p/'cost.txt');gs=list(pickle.load(open(p/'node_to_factor.pkl','rb')).values());gamma={int(q.name.split('_')[0]):q.read_text().split()[1]=='gamma' for q in p.glob('*_dist.txt')};i=c['index'];old=base[i]['best'];prob=np.array([1.]);bounds=[1.]
 for k in range(len(gs)):
  prob=np.convolve(prob,[.9,.09,.009,.001]);bounds.append(float(prob[:int(c['tmax']//10)+1].sum()))
 maximum_k=max(k for k,v in enumerate(bounds) if v>=.985);mincost=math.inf;under=0;unpruned=0
 for s in itertools.product(*gs):
  k=sum(not gamma[j] for j in s);v=float(cost[list(s)].sum())
  if k<=maximum_k:mincost=min(mincost,v)
  if v<=old+1e-8:
   under+=1
   if k<=maximum_k:unpruned+=1
 print(i,'old',old,'allowed_nontail_k',maximum_k,'analytic_cost_floor',mincost,'under_old',under,'not_refuted_by_offset_bound',unpruned,flush=True)
