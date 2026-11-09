"""Exhaustive independent exact raw/LSS fixed-point joint optimality, first3APP.

All125+125+625 choices covered; known original receipts only, no MC or search
feedback. Unknown native identity makes exclusion incomplete, never assumed bad.
"""
from pathlib import Path
from fractions import Fraction as F
import ast,json,hashlib,pickle,math,itertools,time
from independent_raw_recount import rational_joint_count,verify
H=Path(__file__).parent;D=H/'research/final_audit_preflight';out=D/'FIRST3_APP_EXHAUSTIVE_JOINT_AUDIT.json'
if out.exists():raise RuntimeError('No independent exhaustive audit overwrite')
start=time.monotonic();small=json.load(open(D/'SMALL_FORMAL_COMPATIBILITY.json'));witness={r['index']:r for r in small['rows']};cases={c['index']:c for c in json.load(open(H/'CASES.json')) if c['index'] in [21,22,23]};before={r['key']:r for r in json.load(open(H/'formal/F001_I002_40x30/CACHE_BEFORE_VALIDATION.json'))['files']};script=H/'audit_f001_final.py';text=script.read_text();tree=ast.parse(text);lines=text.splitlines();env=dict(H=H,Path=Path,F=F,json=json,hashlib=hashlib,pickle=pickle,math=math,cases=cases,models={},input_identities={},rawref=json.load(open(H/'RAW_REFERENCE.json')),reference=json.load(open(H/'REFERENCE_SHA256.json')),distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'],native={},dist_checked=set(),used=set())
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sha','checked_native']];models=next(n for n in tree.body if isinstance(n,ast.For) and lines[n.lineno-1].startswith('for i,c in cases.items()'));exec(compile(ast.fix_missing_locations(ast.Module(body=defs+[models],type_ignores=[])),str(script),'exec'),env);sha=env['sha']
for r in env['reference']['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original LSS source changed')
def native(c,selection):
 identity=dict(instance=c['instance'],capacity=float(c['tmax']),selection=list(selection),seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
 if key not in before:return None,key
 if sha(H/'lss_cache'/(key+'.json'))!=before[key]['sha256']:raise RuntimeError('Pre-formal native receipt changed')
 checked,v=env['checked_native'](c,dict(selection=list(selection)))
 if checked!=key:raise RuntimeError('Native key differs')
 return v,key
results=[]
for i,c in cases.items():
 p,cost,groups=env['models'][c['instance']];arrays={j:[F(x) for x in (p/f'{j}_sample.txt').read_text().split()] for g in groups for j in g};w=witness[i];ws=tuple(w['selection']);wc=sum((cost[j] for j in ws),F(0));wn,wd=rational_joint_count([arrays[j] for j in ws],F(str(c['tmax'])));v,wkey=native(c,ws)
 if 100*wn<99*wd or v is None or not v['passed'] or abs(float(wc)-w['known_joint_cost'])>1e-9:raise RuntimeError('Independent joint witness failed')
 records=[];counts=dict(at_or_above_witness=0,raw_refuted=0,LSS_refuted=0,LSS_unknown=0,better_joint=0);best_candidates=[]
 for selection in itertools.product(*groups):
  paid=sum((cost[j] for j in selection),F(0))
  if paid>=wc:counts['at_or_above_witness']+=1;continue
  n,den=rational_joint_count([arrays[j] for j in selection],F(str(c['tmax'])));r=dict(selection=list(selection),cost_exact=str(paid),cost=float(paid),raw_numerator=str(n),raw_denominator=str(den))
  if 100*n<99*den:r['classification']='raw_refuted'
  else:
   value,key=native(c,selection);r['LSS_key']=key
   if value is None:r['classification']='LSS_unknown'
   else:
    r['LSS_point']=value['real_probability'];r['native_receipt_sha256']=sha(H/'lss_cache'/(key+'.json'));r['classification']='better_joint' if value['passed'] else 'LSS_refuted'
    if value['passed']:best_candidates.append(r)
  counts[r['classification']]+=1;records.append(r)
 total=math.prod(map(len,groups))
 if sum(counts.values())!=total or len({tuple(r['selection']) for r in records})!=len(records):raise RuntimeError('Incomplete or duplicate choice-space enumeration')
 old_min_error=min(abs(r['cost']-w['original_best']) for r in records);old=[r for r in records if abs(r['cost']-w['original_best'])<=max(1e-9,old_min_error+1e-12)]
 result=dict(index=i,instance=c['instance'],capacity=c['tmax'],full_choice_count=total,group_sizes=list(map(len,groups)),groups=groups,counts=counts,global_fixed_joint_optimal=counts['LSS_unknown']==0 and counts['better_joint']==0,witness_selection=list(ws),witness_cost_exact=str(wc),witness_cost=float(wc),witness_raw_numerator=str(wn),witness_raw_denominator=str(wd),witness_raw_probability=float(F(wn,wd)),witness_LSS_point=v['real_probability'],witness_LSS_key=wkey,witness_native_receipt_sha256=sha(H/'lss_cache'/(wkey+'.json')),historical_best=w['original_best'],historical_cost_matching_records=old,input_sha256=env['input_identities'][c['instance']],cheaper_choice_records=records,better_joint=best_candidates);results.append(result);print(json.dumps({k:v for k,v in result.items() if k not in ['cheaper_choice_records','input_sha256','groups','historical_cost_matching_records','better_joint']}),flush=True)
result=dict(integrity_passed=True,scope='exhaustive exact decimal rational original empirical .99 plus original unchanged fixed10m seed832273 LSS point>=.985; global optimality only for these3cases and fixed acceptance predicate, not population CI or full ambiguity-set DRO',all3_global_fixed_joint_optimal=all(r['global_fixed_joint_optimal'] for r in results),fully_enumerated_choices=sum(r['full_choice_count'] for r in results),raw_exact_counts_for_all_cheaper_choices=sum(len(r['cheaper_choice_records']) for r in results),unique_original_LSS_receipts_checked=len(env['native']),new_MC_calls=0,optimizer_feedback=False,final_auditor_sha256=sha(script),independent_raw_verifier_sha256=sha(H/'independent_raw_recount.py'),proof_source_sha256=sha(Path(__file__)),source_compatibility_diagnostic_sha256=sha(D/'SMALL_FORMAL_COMPATIBILITY.json'),cases=results,seconds=time.monotonic()-start)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
