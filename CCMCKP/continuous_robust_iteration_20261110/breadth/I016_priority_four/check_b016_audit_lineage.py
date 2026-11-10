"""Real prior engineering inputs + in-memory corruptions of new lineage code.

This executes only the pool/lineage/phase/precision branch extracted from the
new auditor, not its eight-new-search/source-read or independent recount branches.
No synthetic or renamed search outcomes are written and no MC/search is run.
"""
from pathlib import Path
from fractions import Fraction as F
import ast,json,gzip,copy,pickle,hashlib
H=Path(__file__).resolve().parent;T=H/'research/B016_audit_preflight';T.mkdir(exist_ok=True);out=T/'LINEAGE_PREFLIGHT.json';source=H/'audit_i016_priority_breadth.py';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No audit preflight evidence overwrite')
tree=ast.parse(source.read_text());pool_function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pool_check');loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [a.id for a in n.target.elts]==['label','index','seed'])
start=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ext' for t in n.targets))
if not isinstance(loop.body[-1],ast.Expr) or not isinstance(loop.body[-1].value,ast.Call) or not isinstance(loop.body[-1].value.func,ast.Attribute) or loop.body[-1].value.func.attr!='append':raise RuntimeError('Unexpected auditor block structure')
pool_code=compile(ast.Module(body=[pool_function],type_ignores=[]),str(source),'exec');lineage_code=compile(ast.Module(body=loop.body[start:-1],type_ignores=[]),str(source),'exec');records=[];inputs={}
for label,iteration,method in [('I015_parent','I015_precision_closure','hybrid'),('I016_pair_cover','I016_cdf_pair_cover','pair_cover')]:
 J=H/'iterations'/iteration/'engineering39';file=J/'result.json.gz';original=json.loads(gzip.decompress(file.read_bytes()));audit=json.load(open(J/'INDEPENDENT_RAW_AUDIT.json'));meta=json.load(open(str(file)+'.run.json'));reg=json.load(open(J/'REGISTRATION.json'))
 if not audit['passed'] or audit['result_sha256']!=sha(file) or meta['source_sha256']!=reg['source_sha256']:raise RuntimeError('Actual already-audited original engineering fixture required')
 P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/original['instance'];prices=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
 inputs[file.relative_to(H).as_posix()]=sha(file)
 def run(data):
  env=dict(data=data,label=label,F=F,prices=prices,groups=groups,unique={},current_instance=original['instance'],current_capacity=original['capacity'])
  exec(pool_code,env);exec(lineage_code,env);return env
 positive=run(copy.deepcopy(original))
 expected=audit['unique_semantic_raw_certificates_recounted']
 if len(positive['unique'])!=expected or len(positive['final'])!=original['raw_certified_pool_count']:raise AssertionError('New branch semantic certificate enumeration differs from actual prior independent audit')
 records.append(dict(label=label,test='original real engineering pool/lineage passes, semantic enumeration matches prior independent recount',passed=True,actual_original_seed=original['seed'],semantic_certificates=expected))
 mutations=[]
 mutations.append(('changed canonical price',lambda d:d['candidate_shortlist'][0].__setitem__('cost',d['candidate_shortlist'][0]['cost']+1)))
 mutations.append(('unaccepted integer lower',lambda d:d['candidate_shortlist'][0]['certificate'].__setitem__('lower_numerator','0')))
 mutations.append(('nonstrict event',lambda d:d['candidate_shortlist'][0]['certificate'].__setitem__('strict_event','sum<=T')))
 mutations.append(('lost original sample flag',lambda d:d['candidate_shortlist'][0]['certificate'].__setitem__('all_original_samples',False)))
 mutations.append(('phase exceeds180',lambda d:d['extension'].__setitem__('extension_seconds',181)))
 mutations.append(('precision phase reset',lambda d:d['extension']['precision_closure'].__setitem__('shared_deadline',d['extension']['precision_closure']['phase_started']+181)))
 mutations.append(('CDF retained flag false',lambda d:d['extension'][method].__setitem__('all_own_cdf_retained',False)))
 mutations.append(('CDF stage counts forged',lambda d:d['extension'][method]['robust_cdf_lns'].__setitem__('new_certified',d['extension'][method]['robust_cdf_lns']['new_certified']+1)))
 mutations.append(('precision initial pool mismatch',lambda d:d['extension']['precision_closure'].__setitem__('initial_pool',d['extension']['precision_closure']['initial_pool']+1)))
 if original['extension']['precision_closure']['records']:
  mutations.append(('precision foreign decision',lambda d:d['extension']['precision_closure']['records'][0]['initial_decision'].__setitem__('decision','not_own_unresolved')))
 def remove_cdf(d):
  q=tuple(d['extension'][method]['cdf_pool_records'][0]['selection']);d['candidate_shortlist']=[r for r in d['candidate_shortlist'] if tuple(r['selection'])!=q];d['raw_certified_pool_count']=len(d['candidate_shortlist'])
 mutations.append(('remove retained CDF member',remove_cdf))
 if method=='pair_cover':
  mutations.append(('pair retained flag false',lambda d:d['extension']['pair_cover'].__setitem__('all_own_pair_retained',False)))
  mutations.append(('pair pool count forged',lambda d:d['extension']['pair_cover'].__setitem__('pair_pool',d['extension']['pair_cover']['pair_pool']+1)))
  def remove_pair(d):
   cdf={tuple(r['selection']) for r in d['extension']['pair_cover']['cdf_pool_records']};q=next(tuple(r['selection']) for r in d['extension']['pair_cover']['pair_pool_records'] if tuple(r['selection']) not in cdf);d['candidate_shortlist']=[r for r in d['candidate_shortlist'] if tuple(r['selection'])!=q];d['raw_certified_pool_count']=len(d['candidate_shortlist'])
  mutations.append(('remove retained pair-specific member',remove_pair))
 for name,mutate in mutations:
  value=copy.deepcopy(original);mutate(value)
  try:run(value)
  except RuntimeError:records.append(dict(label=label,test=name,passed=True,invalid_data_rejected=True))
  else:raise AssertionError('New lineage code silently accepted '+label+': '+name)
result=dict(passed=True,checks=len(records),scope=__doc__,auditor_sha256=sha(source),fixture_source_sha256=inputs,records=records,full_new_eight_search_audit_executed=False,new_MC_calls=0,new_searches=0)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
