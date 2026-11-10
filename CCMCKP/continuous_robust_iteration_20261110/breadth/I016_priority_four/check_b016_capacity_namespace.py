"""Actual old selection/raw samples; two generous mathematical capacities only.

Both counts deliberately saturate at one, so selection/bins/numerator/denominator
are identical. The auditor must retain two capacity namespaces. These are math
fixtures, not new benchmark search outcomes or original-LSS evaluations.
"""
from pathlib import Path
from fractions import Fraction as F
import ast,json,pickle,hashlib
from independent_raw_recount import upward_grid_count
H=Path(__file__).resolve().parent;T=H/'research/B016_audit_preflight';T.mkdir(exist_ok=True);out=T/'CAPACITY_NAMESPACE_MATH_CHECK.json';source=H/'audit_i016_priority_breadth.py';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No namespace math evidence overwrite')
tree=ast.parse(source.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pool_check');code=compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec')
original=H/'formal/F001_I002_40x30/validation/cdf_lns_37_seed9707001.json.gz.post.json';post=json.load(open(original));q=post['selected']['selection'];case=next(c for c in json.load(open(H/'CASES.json')) if c['index']==37);P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/case['instance'];ref=json.load(open(H/'RAW_REFERENCE.json'))
for p in [P/'cost.txt',P/'node_to_factor.pkl']+[P/(str(j)+'_sample.txt') for j in q]:
 if sha(p)!=ref[str(p)]:raise RuntimeError('Actual original input changed')
arrays=[[F(x) for x in (P/(str(j)+'_sample.txt')).read_text().split()] for j in q];prices=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
total_max=sum((max(a) for a in arrays),F(0));capacities=[float(2*total_max+1),float(4*total_max+2)];env=dict(F=F,prices=prices,groups=groups,unique={},current_instance=case['instance']);exec(code,env);records=[]
for capacity in capacities:
 n,d=upward_grid_count(arrays,F(str(capacity)),1024)
 if n!=d:raise AssertionError('Deliberately generous mathematical capacity did not saturate')
 cert=dict(selection=q,method='exact_integer_upward_grid_count',strict_event='sum<T',all_original_samples=True,accepted=True,lower_numerator=str(n),denominator=str(d),bins=1024);record=dict(selection=q,cost=float(sum((prices[j] for j in q),F(0))),certificate=cert);env['current_capacity']=capacity;env['pool_check']([record]);records.append(dict(capacity=capacity,bins=1024,numerator=str(n),denominator=str(d)))
if len(env['unique'])!=2 or records[0]['numerator']!=records[1]['numerator'] or records[0]['denominator']!=records[1]['denominator']:raise AssertionError('Different capacities with identical scalar counts merged')
result=dict(passed=True,checks=1,scope=__doc__,auditor_sha256=sha(source),original_selection_post_sha256=sha(original),records=records,semantic_capacity_namespaces_retained=2,new_searches=0,new_original_MC_calls=0,not_benchmark_cost_or_probability_results=True)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
