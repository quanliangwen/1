"""Second implementation: exact decimal-to-integer MITM, no raw helper import."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from itertools import product
from bisect import bisect_left
import json,pickle,hashlib,math,time
H=Path(__file__).parent;D=H/'research/final_audit_preflight';path=D/'FIRST3_APP_EXHAUSTIVE_JOINT_AUDIT.json';out=D/'FIRST3_APP_INTEGER_RECHECK.json'
if out.exists():raise RuntimeError('No second audit overwrite')
proof=json.load(open(path));rawref=json.load(open(H/'RAW_REFERENCE.json'));reference=json.load(open(H/'REFERENCE_SHA256.json'));distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];start=time.monotonic();native_seen={};dist_checked=set();checks=0;results=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digits(s):
 t=Decimal(s).as_tuple();return (-1 if t.sign else 1)*int(''.join(map(str,t.digits))),t.exponent
def integers(strings):
 values=[digits(x) for x in strings];e=min(x[1] for x in values);return [a*10**(p-e) for a,p in values],e
for r in reference['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original LSS changed')
for c in proof['cases']:
 P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance']
 for name,digest in c['input_sha256'].items():
  if sha(P/name)!=digest or rawref[str(P/name)]!=digest:raise RuntimeError('Raw input changed')
 groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
 if groups!=c['groups']:raise RuntimeError('Group partition changed')
 cost,ce=integers((P/'cost.txt').read_text().split());texts=[(P/f'{j}_sample.txt').read_text().split() for j in range(len(cost))];flat=[str(c['capacity'])]+[x for a in texts for x in a];values,e=integers(flat);T=values[0];samples=[];offset=1
 for a in texts:samples.append(values[offset:offset+len(a)]);offset+=len(a)
 wc=sum(cost[j] for j in c['witness_selection']);unit=Fraction(10)**ce
 if Fraction(c['witness_cost_exact'])!=wc*unit:raise RuntimeError('Witness exact cost mismatch')
 def count(selection):
  cut=len(selection)//2
  left=[sum(x) for x in product(*(samples[j] for j in selection[:cut]))];right=sorted(sum(x) for x in product(*(samples[j] for j in selection[cut:])));n=sum(bisect_left(right,T-x) for x in left);den=math.prod(len(samples[j]) for j in selection);return n,den
 def receipt(selection,key,expected_sha):
  identity=dict(instance=c['instance'],capacity=float(c['capacity']),selection=list(selection),seed=832273,draws=10000000,event='sum<=T');actual=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();p=H/'lss_cache'/(key+'.json')
  if actual!=key or sha(p)!=expected_sha:raise RuntimeError('Native SHA differs')
  if key not in native_seen:
   v=json.load(open(p))
   if any(v[k]!=x for k,x in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1' or v['search_feedback'] or not all(v[k] for k in ['original_full_module','original_sources_unmodified','aliases_only']) or v['passed']!=(v['real_probability']>=.985):raise RuntimeError('Wrong original native identity/role')
   if set(v['distribution_sha256'])!={f'{j}_dist.txt' for j in selection}:raise RuntimeError('Incomplete native input identity')
   for name,digest in v['distribution_sha256'].items():
    if (c['instance'],name,digest) not in dist_checked:
     if distref[c['instance']+'/'+name]!=digest or sha(P/name)!=digest:raise RuntimeError('Native distribution differs')
     dist_checked.add((c['instance'],name,digest))
   native_seen[key]=v
  return native_seen[key]
 wn,wd=count(c['witness_selection']);v=receipt(c['witness_selection'],c['witness_LSS_key'],c['witness_native_receipt_sha256'])
 if str(wn)!=c['witness_raw_numerator'] or str(wd)!=c['witness_raw_denominator'] or 100*wn<99*wd or not v['passed']:raise RuntimeError('Joint witness invalid')
 records={tuple(r['selection']):r for r in c['cheaper_choice_records']};counts=dict(at_or_above_witness=0,raw_refuted=0,LSS_refuted=0,LSS_unknown=0,better_joint=0);visited=set();total=0
 for q in product(*groups):
  total+=1;paid=sum(cost[j] for j in q)
  if paid>=wc:counts['at_or_above_witness']+=1;continue
  if q not in records:raise RuntimeError('Missing cheaper choice')
  visited.add(q);r=records[q];n,den=count(q);checks+=1
  if Fraction(r['cost_exact'])!=paid*unit or str(n)!=r['raw_numerator'] or str(den)!=r['raw_denominator']:raise RuntimeError('Integer independent count/cost differs')
  if 100*n<99*den:classification='raw_refuted'
  elif r['classification']=='LSS_unknown':classification='LSS_unknown'
  else:
   v=receipt(q,r['LSS_key'],r['native_receipt_sha256']);classification='better_joint' if v['passed'] else 'LSS_refuted'
   if v['real_probability']!=r['LSS_point']:raise RuntimeError('Native probability differs')
  if r['classification']!=classification:raise RuntimeError('Classification differs')
  counts[classification]+=1
 optimal=counts['LSS_unknown']==0 and counts['better_joint']==0
 if visited!=set(records) or counts!=c['counts'] or total!=c['full_choice_count'] or total!=math.prod(map(len,groups)) or optimal!=c['global_fixed_joint_optimal']:raise RuntimeError('Global enumeration/exclusion invalid')
 results.append(dict(index=c['index'],total_choices=total,cheaper_choices=len(records),joint_optimal=optimal,cost=c['witness_cost'],raw_numerator=str(wn),raw_denominator=str(wd),LSS_point=c['witness_LSS_point']))
result=dict(passed=True,method='independent decimal coefficient/exponent integer scaling and integer MITM, no optimizer/raw verifier modules imported',all3_global_fixed_joint_optimal=all(c['joint_optimal'] for c in results),full_choices_covered=sum(c['total_choices'] for c in results),cheaper_probabilities_independently_recounted=checks,unique_native_receipts_checked=len(native_seen),proof_sha256=sha(path),checker_sha256=sha(Path(__file__)),new_MC_calls=0,cases=results,scope='only3smallAPP cases and fixed original empirical99/original LSS985 point acceptance, not population CI or fullDRO ambiguity-set claim',seconds=time.monotonic()-start)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
