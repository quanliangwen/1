"""Cost-only complexity estimate, not feasibility or global optimality proof."""
import pathlib,json,pickle,itertools,time,numpy as np
H=pathlib.Path(__file__).parent;cases=json.load(open(H/'CASES.json'));baseline={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};rows=[]
for c in cases:
 if c['index'] not in [30,32]:continue
 p=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(p/'cost.txt');groups=pickle.load(open(p/'node_to_factor.pkl','rb'))
 groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
 def half(gs):
  values=np.array([0.])
  for g in gs:values=(values[:,None]+cost[np.asarray(g,int)][None,:]).reshape(-1)
  return np.sort(values)
 t=time.monotonic();left=half(groups[:len(groups)//2]);right=half(groups[len(groups)//2:]);ref=baseline[c['index']]
 counts={}
 for tag,cap in [('old_best',ref['old_best']),('S10',ref['new_avg'])]:counts[tag]=int(np.searchsorted(right,cap+1e-8-left,side='right').sum())
 rows.append(dict(index=c['index'],instance=c['instance'],minimum_cost_sum=float(sum(cost[g].min() for g in groups)),half_states=[len(left),len(right)],cost_prefix_counts_estimated=counts,seconds=time.monotonic()-t,scope='floating cost-only count estimate with1e-8 tolerance; not a feasibility or optimality certificate'))
(H/'COST_PREFIX_DIAGNOSTIC.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
