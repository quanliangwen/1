"""Independent full cost/receipt/partition audit + C++128 every-count replay."""
from pathlib import Path
from fractions import Fraction
from itertools import product
import json,gzip,hashlib,pickle,math,subprocess,time
from cpp_audit_codec import scale,write_model
H=Path(__file__).parent;D=H/'research/small16_joint_global';out=D/'INDEPENDENT_CPP_RECHECK.json';input_file=D/'cpp_full.in';start=time.monotonic()
if out.exists() or input_file.exists():raise RuntimeError('No C++ full recheck overwrite')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=json.load(open(D/'RESULT.json'));reg=json.load(open(D/'REGISTRATION.json'));cpp=json.load(open(D/'CPP_MATH_CHECK.json'));binary=D/'small_exact_checker';reference=json.load(open(H/'REFERENCE_SHA256.json'));distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];rawref=json.load(open(H/'RAW_REFERENCE.json'));before={r['key']:r for r in json.load(open(H/'formal/F001_I002_40x30/CACHE_BEFORE_VALIDATION.json'))['files']};old={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']}
if p['status']!='completed' or len(p['cases'])!=16 or not cpp['passed'] or cpp['binary_sha256']!=sha(binary) or cpp['source_sha256']!=sha(H/'small_exact_checker.cpp') or cpp['codec_sha256']!=sha(H/'cpp_audit_codec.py') or p['proof_sha256']!=sha(D/'choices.jsonl.gz') or p['registration_sha256']!=sha(D/'REGISTRATION.json'):raise RuntimeError('Complete proof/math/binary identity required')
for name,digest in reg['source_sha256'].items():
 if sha(H/name)!=digest:raise RuntimeError('Registered source changed')
for r in reference['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original LSS source changed')
expected=set(range(1,9))|set(range(21,29));cases={c['index']:c for c in p['cases']};records={i:[] for i in expected};record_hashes={i:hashlib.sha256() for i in expected}
if set(cases)!=expected:raise RuntimeError('Not the sixteen original small cases')
with gzip.open(D/'choices.jsonl.gz','rt') as f:
 for line in f:
  r=json.loads(line)
  if r['index'] not in records:raise RuntimeError('Proof outside registered cases')
  records[r['index']].append(r);record_hashes[r['index']].update(line.encode())
native_seen={};dist_checked=set();results=[];queries_total=0
with input_file.open('x') as stream:
 stream.write('16\n')
 for i,c in sorted(cases.items()):
  P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance']
  for name,digest in c['input_sha256'].items():
   if sha(P/name)!=digest or rawref[str(P/name)]!=digest:raise RuntimeError('Raw input changed')
  groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[list(map(int,groups[k])) for k in sorted(groups,key=int)] if isinstance(groups,dict) else [list(map(int,g)) for g in groups]
  if groups!=c['groups']:raise RuntimeError('Group partition differs')
  cost,exponent=scale((P/'cost.txt').read_text().split());unit=Fraction(10)**exponent;wc=sum(cost[j] for j in c['witness_selection']);samples=[(P/f'{j}_sample.txt').read_text().split() for j in range(len(cost))];m=len(groups)
  if exponent!=c['cost_exponent'] or str(wc)!=c['witness_cost_units'] or wc*unit!=Fraction(c['witness_cost_exact']):raise RuntimeError('Exact witness cost differs')
  recs={tuple(r['selection']):r for r in records[i]}
  if len(recs)!=len(records[i]) or len(recs)!=c['proof_records'] or record_hashes[i].hexdigest()!=c['proof_records_sha256']:raise RuntimeError('Duplicate/missing/changed proof records')
  def native(selection,key):
   identity=dict(instance=c['instance'],capacity=float(c['capacity']),selection=list(selection),seed=832273,draws=10000000,event='sum<=T');actual=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
   if actual!=key:raise RuntimeError('Native identity differs')
   if key not in before:return None
   file=H/'lss_cache'/(key+'.json')
   if sha(file)!=before[key]['sha256'] or sha(file)!=p['native_receipt_sha256'][key]:raise RuntimeError('Original receipt changed')
   if key not in native_seen:
    v=json.load(open(file))
    if any(v[k]!=x for k,x in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1' or v['search_feedback'] or not all(v[k] for k in ['original_full_module','original_sources_unmodified','aliases_only']) or v['passed']!=(v['real_probability']>=.985):raise RuntimeError('Original native source/environment/role differs')
    if set(v['distribution_sha256'])!={f'{j}_dist.txt' for j in selection}:raise RuntimeError('Incomplete native inputs')
    for name,digest in v['distribution_sha256'].items():
     if (c['instance'],name,digest) not in dist_checked:
      if distref[c['instance']+'/'+name]!=digest or sha(P/name)!=digest:raise RuntimeError('Original distribution changed')
      dist_checked.add((c['instance'],name,digest))
    native_seen[key]=v
   return native_seen[key]
  witness=native(c['witness_selection'],c['witness_LSS_key']);wn=int(c['witness_raw_numerator']);wd=int(c['witness_raw_denominator'])
  if witness is None or not witness['passed'] or 100*wn<99*wd or witness['real_probability']!=c['witness_LSS_point']:raise RuntimeError('Joint witness invalid')
  queries=[(c['capacity'],wn,wd,c['witness_selection'])];counts=dict(at_or_above_witness=0,raw_refuted=0,LSS_refuted=0,LSS_unknown=0,better_joint=0);visited=set();total=0;used={c['witness_LSS_key']}
  for q in product(*groups):
   total+=1;paid=sum(cost[j] for j in q)
   if paid>=wc:counts['at_or_above_witness']+=1;continue
   if q not in recs:raise RuntimeError('Missing cheaper selection')
   r=recs[q];visited.add(q);n=int(r['raw_numerator']);den=int(r['raw_denominator'])
   if str(paid)!=r['cost_units'] or den!=math.prod(len(samples[j]) for j in q) or not 0<=n<=den:raise RuntimeError('Wrong exact cost/count denominator')
   queries.append((c['capacity'],n,den,q))
   if 100*n<99*den:classification='raw_refuted'
   else:
    value=native(q,r['LSS_key'])
    if value is None:classification='LSS_unknown'
    else:
     classification='better_joint' if value['passed'] else 'LSS_refuted';used.add(r['LSS_key'])
     if value['real_probability']!=r['LSS_point'] or sha(H/'lss_cache'/(r['LSS_key']+'.json'))!=r['native_receipt_sha256']:raise RuntimeError('Native probability/receipt mismatch')
   if classification!=r['classification']:raise RuntimeError('Wrong joint classification')
   counts[classification]+=1
  optimal=counts['LSS_unknown']==0 and counts['better_joint']==0
  if visited!=set(recs) or counts!=c['counts'] or total!=c['total_choices'] or c['processed_choices']!=total or used!=set(c['native_keys']) or optimal!=c['global_fixed_joint_optimal']:raise RuntimeError('Complete-space partition/exclusion claim false')
  write_model(stream,samples,m,queries);queries_total+=len(queries);results.append(dict(index=i,instance=c['instance'],capacity=c['capacity'],total_choices=total,cheaper_choices=len(recs),counts=counts,joint_optimal=optimal,joint_optimal_cost=float(wc*unit),joint_optimal_cost_exact=str(wc*unit),old_best=old[i]['old_best'],historical_gap_over1e_6=float(wc*unit)-old[i]['old_best']>1e-6,witness_raw_numerator=str(wn),witness_raw_denominator=str(wd),witness_LSS_point=witness['real_probability']))
with input_file.open() as stream:r=subprocess.run([str(binary)],stdin=stream,capture_output=True,text=True,timeout=600)
with (D/'cpp_full.log').open('x') as f:f.write(r.stdout+r.stderr)
if r.returncode or not r.stdout.endswith(f'ALL_OK 16 {queries_total}\n'):raise RuntimeError('Independent C++ exact recheck failed '+r.stdout[-1000:]+r.stderr)
if set(native_seen)!=set(p['native_receipt_sha256']):raise RuntimeError('Native evidence coverage differs')
result=dict(passed=True,all16_global_fixed_joint_optimal=all(c['joint_optimal'] for c in results),full_choices_covered=sum(c['total_choices'] for c in results),cheaper_choices_recounted=sum(c['cheaper_choices'] for c in results),independent_CPP_exact_counts=queries_total,unique_original_native_receipts=len(native_seen),new_MC_calls=0,cases=results,method='independent decimal common scale including capacities; C++ signed128 cached sums/std::lower_bound for every cheaper choice +16witnesses; independent original-data/cost/partition/native-receipt validation',scope='only16small cases and fixed empirical99/originalLSS985point predicate, not population CI or fullDRO ambiguity-set optimum',proof_sha256=p['proof_sha256'],result_sha256=sha(D/'RESULT.json'),cpp_source_sha256=sha(H/'small_exact_checker.cpp'),cpp_binary_sha256=sha(binary),checker_source_sha256=sha(Path(__file__)),codec_sha256=sha(H/'cpp_audit_codec.py'),input_sha256=sha(input_file),log_sha256=sha(D/'cpp_full.log'),CPP_math_check_sha256=sha(D/'CPP_MATH_CHECK.json'),seconds=time.monotonic()-start)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
