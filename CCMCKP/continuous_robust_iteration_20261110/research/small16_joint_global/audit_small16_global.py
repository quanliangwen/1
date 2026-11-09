"""Complete small-case cost frontier audit. Cache-only native validation."""
from pathlib import Path
from fractions import Fraction as F
import ast,json,gzip,hashlib,pickle,math,itertools,time
from small_exact_integer_core import ExactHalfSums,decimal_integers
H=Path(__file__).parent;D=H/'research/small16_joint_global';D.mkdir(parents=True,exist_ok=True);out=D/'RESULT.json';proof_file=D/'choices.jsonl.gz';seconds=900
if out.exists() or proof_file.exists() or (D/'REGISTRATION.json').exists():raise RuntimeError('Audit already registered; inspect live process or results')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
check=json.load(open(H/'SMALL_EXACT_INTEGER_CORE_MATH_CHECK.json'))
if not check['passed'] or check['source_sha256']!=sha(H/'small_exact_integer_core.py'):raise RuntimeError('Verified exact kernel required')
diag_path=H/'research/final_audit_preflight/SMALL_FORMAL_COMPATIBILITY.json';diag=json.load(open(diag_path));witness={r['index']:r for r in diag['rows']};cases={r['index']:r for r in json.load(open(H/'CASES.json')) if r['index'] in witness};script=H/'audit_f001_final.py';text=script.read_text();tree=ast.parse(text);lines=text.splitlines();before={r['key']:r for r in json.load(open(H/'formal/F001_I002_40x30/CACHE_BEFORE_VALIDATION.json'))['files']};start=time.monotonic()
reg=dict(time=time.time(),scope='all16small original benchmark cost-frontier exact audit, not solver performance experiment or new MC',cases=sorted(cases),seconds=seconds,source_sha256={n:sha(H/n) for n in ['audit_small16_global.py','small_exact_integer_core.py','audit_f001_final.py']},math_check_sha256=sha(H/'SMALL_EXACT_INTEGER_CORE_MATH_CHECK.json'),diagnostic_sha256=sha(diag_path),native_inventory_count=len(before),no_new_MC=True,no_optimizer_feedback=True)
with (D/'REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
env=dict(H=H,Path=Path,F=F,json=json,hashlib=hashlib,pickle=pickle,math=math,cases=cases,models={},input_identities={},rawref=json.load(open(H/'RAW_REFERENCE.json')),reference=json.load(open(H/'REFERENCE_SHA256.json')),distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'],native={},dist_checked=set(),used=set())
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sha','checked_native']];models=next(n for n in tree.body if isinstance(n,ast.For) and lines[n.lineno-1].startswith('for i,c in cases.items()'));exec(compile(ast.fix_missing_locations(ast.Module(body=defs+[models],type_ignores=[])),str(script),'exec'),env)
for r in env['reference']['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original native source changed')
def native(c,q):
 identity=dict(instance=c['instance'],capacity=float(c['tmax']),selection=list(q),seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
 if key not in before:return None,key
 if sha(H/'lss_cache'/(key+'.json'))!=before[key]['sha256']:raise RuntimeError('Original native receipt changed')
 checked,v=env['checked_native'](c,dict(selection=list(q)))
 if checked!=key:raise RuntimeError('Original native identity differs')
 return v,key
results=[];current_instance=None;record_count=0;timed_out=False
with gzip.open(proof_file,'xt',encoding='utf8',compresslevel=6) as log:
 for i,c in sorted(cases.items()):
  P,cost_f,groups=env['models'][c['instance']];cost,exponent=decimal_integers((P/'cost.txt').read_text().split());w=witness[i];ws=tuple(w['selection']);wc=sum(cost[j] for j in ws);v,wkey=native(c,ws)
  if c['instance']!=current_instance:
   arrays=[(P/f'{j}_sample.txt').read_text().split() for j in range(len(cost))];counter=ExactHalfSums(arrays);current_instance=c['instance']
  wn,wd=counter.count(ws,c['tmax'])
  if 100*wn<99*wd or v is None or not v['passed']:raise RuntimeError('Actual joint witness invalid')
  total=math.prod(map(len,groups));counts=dict(at_or_above_witness=0,raw_refuted=0,LSS_refuted=0,LSS_unknown=0,better_joint=0);processed=0;cheaper=0;proof_hash=hashlib.sha256();native_keys=set([wkey]);t=time.monotonic()
  for q in itertools.product(*groups):
   if processed%100==0 and time.monotonic()-start>seconds-5:timed_out=True;break
   processed+=1;paid=sum(cost[j] for j in q)
   if paid>=wc:counts['at_or_above_witness']+=1;continue
   n,den=counter.count(q,c['tmax']);r=dict(index=i,selection=list(q),cost_units=str(paid),raw_numerator=str(n),raw_denominator=str(den));cheaper+=1
   if 100*n<99*den:r['classification']='raw_refuted'
   else:
    value,key=native(c,q);r['LSS_key']=key
    if value is None:r['classification']='LSS_unknown'
    else:r.update(classification='better_joint' if value['passed'] else 'LSS_refuted',LSS_point=value['real_probability'],native_receipt_sha256=sha(H/'lss_cache'/(key+'.json')));native_keys.add(key)
   counts[r['classification']]+=1;line=json.dumps(r,separators=(',',':'))+'\n';log.write(line);proof_hash.update(line.encode());record_count+=1
   if cheaper%1000==0:
    progress=dict(index=i,case_processed=processed,case_total=total,cheaper_recounted=cheaper,completed_cases=len(results),seconds=time.monotonic()-start,cache=counter.cache_stats());(D/'PROGRESS.json').write_text(json.dumps(progress,indent=2));print(json.dumps(progress),flush=True)
  if sum(counts.values())!=processed:raise RuntimeError('Enumeration accounting mismatch')
  complete=processed==total;optimal=complete and counts['LSS_unknown']==0 and counts['better_joint']==0
  result=dict(index=i,instance=c['instance'],capacity=c['tmax'],group_sizes=list(map(len,groups)),groups=groups,input_sha256=env['input_identities'][c['instance']],total_choices=total,processed_choices=processed,unprocessed_choices=total-processed,counts=counts,complete=complete,global_fixed_joint_optimal=optimal,witness_selection=list(ws),cost_exponent=exponent,witness_cost_units=str(wc),witness_cost_exact=str(wc*F(10)**exponent),witness_cost=float(wc*F(10)**exponent),witness_raw_numerator=str(wn),witness_raw_denominator=str(wd),witness_LSS_key=wkey,witness_LSS_point=v['real_probability'],native_keys=sorted(native_keys),proof_records=cheaper,proof_records_sha256=proof_hash.hexdigest(),seconds=time.monotonic()-t,cache=counter.cache_stats());results.append(result)
  with (D/f'case_{i:02d}.json').open('x') as f:json.dump(result,f,indent=2)
  print(json.dumps({k:v for k,v in result.items() if k not in ['groups','input_sha256','native_keys','cache']}),flush=True)
  if timed_out:break
result=dict(status='budget_exhausted' if timed_out else 'completed',integrity_passed=True,scope='fixed original empirical99 and original LSS985point only; not population CI/fullDRO ambiguity-set optimum',all16_global_fixed_joint_optimal=len(results)==16 and all(r['global_fixed_joint_optimal'] for r in results),cases=results,full_choices_registered=sum(math.prod(map(len,env['models'][c['instance']][2])) for c in cases.values()),choices_processed=sum(r['processed_choices'] for r in results),cheaper_choices_recounted=record_count,unique_native_receipts_checked=len(env['native']),proof_sha256=sha(proof_file),source_sha256=reg['source_sha256'],native_receipt_sha256={k:sha(H/'lss_cache'/(k+'.json')) for k in sorted(env['used'])},new_MC_calls=0,registration_sha256=sha(D/'REGISTRATION.json'),seconds=time.monotonic()-start)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['cases','source_sha256','native_receipt_sha256']}),flush=True)
