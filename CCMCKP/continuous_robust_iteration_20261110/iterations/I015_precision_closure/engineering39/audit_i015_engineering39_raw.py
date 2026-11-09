"""Independent recount of every engineering raw candidate; cache-only inventory."""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,time,math
from independent_raw_recount import upward_grid_count
H=Path(__file__).resolve().parent;I=H/'iterations/I015_precision_closure';J=I/'engineering39';out=J/'INDEPENDENT_RAW_AUDIT.json'
if out.exists():raise RuntimeError('No audit overwrite')
start=time.monotonic();p=J/'result.json.gz';d=json.loads(gzip.decompress(p.read_bytes()));meta=json.load(open(str(p)+'.run.json'));assessment=json.load(open(J/'ASSESSMENT.json'));check=json.load(open(H/'INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json'))
if not assessment['passed'] or not check['passed'] or hashlib.sha256((H/'independent_raw_recount.py').read_bytes()).hexdigest()!=check['source_sha256']:raise RuntimeError('Independent verifier/source check required')
bench=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/d['instance'];ref=json.load(open(H/'RAW_REFERENCE.json'));arrays={}
for name,sha in meta['input_sha256'].items():
 data=(bench/name).read_bytes()
 if hashlib.sha256(data).hexdigest()!=sha or ref[str(bench/name)]!=sha:raise RuntimeError('Original input changed')
 if name.endswith('_sample.txt'):arrays[int(name.split('_')[0])]=[F(x) for x in data.decode().split()]
final_pool=d['candidate_shortlist'];cdf=d['extension']['hybrid']['cdf_pool_records'];unique={}
for r in final_pool+cdf:
 c=r['certificate'];key=(tuple(r['selection']),c['method'],c['bins'],c['lower_numerator'],c['denominator']);unique[key]=r
pool=list(unique.values());results=[];minimum=None
for index,r in enumerate(pool,1):
 cert=r['certificate'];s=r['selection']
 if cert['method']!='exact_integer_upward_grid_count' or cert['selection']!=s:raise RuntimeError('Unexpected raw certificate')
 n,den=upward_grid_count([arrays[j] for j in s],F(str(d['capacity'])),cert['bins'])
 if str(n)!=cert['lower_numerator'] or str(den)!=cert['denominator'] or 100*n<99*den:raise RuntimeError('Independent raw recount failed')
 value=F(n,den);minimum=value if minimum is None else min(minimum,value);results.append(dict(selection=s,bins=cert['bins'],numerator=str(n),denominator=str(den)))
 if index%50==0 or index==len(pool):
  (J/'RAW_AUDIT_PROGRESS.json').write_text(json.dumps(dict(done=index,required=len(pool),seconds=time.monotonic()-start)))
  print(json.dumps(dict(raw_recounted=index,required=len(pool),seconds=time.monotonic()-start)),flush=True)
# Existing original LSS calls are read only after the optimizer has finished.
# Missing records remain unknown: no simulation or search feedback is performed.
pool=final_pool;reference=json.load(open(H/'REFERENCE_SHA256.json'));distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];known=[];unknown=[];dist_checked=set()
for r in pool:
 identity=dict(instance=d['instance'],capacity=float(d['capacity']),selection=r['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();cache=H/'lss_cache'/(key+'.json')
 if not cache.exists():unknown.append(dict(key=key,cost=r['cost'],selection=r['selection']));continue
 v=json.load(open(cache))
 if any(v[k]!=value for k,value in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['passed']!=(v['real_probability']>=.985) or v['numpy']!='1.24.4' or v['scipy']!='1.10.1':raise RuntimeError('Cached LSS identity differs')
 if set(v['distribution_sha256'])!={f'{j}_dist.txt' for j in r['selection']}:raise RuntimeError('Incomplete distribution identity')
 for name,sha in v['distribution_sha256'].items():
  if (name,sha) not in dist_checked:
   if distref[d['instance']+'/'+name]!=sha or hashlib.sha256((bench/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('Cached distribution identity differs')
   dist_checked.add((name,sha))
 known.append(dict(key=key,cost=r['cost'],selection=r['selection'],real_probability=v['real_probability'],passed=v['passed']))
for rec in reference['files']:
 if hashlib.sha256((H/'reference'/rec['path']).read_bytes()).hexdigest()!=rec['sha256']:raise RuntimeError('Original LSS source drift')
cdf_set={tuple(r['selection']) for r in cdf};current=assessment['current_I002_qualified_reference'];passing=[v for v in known if v['passed']];best=min(passing,key=lambda v:(v['cost'],v['selection'])) if passing else None
result=dict(passed=True,scope='all final-pool and saved-own-CDF semantic raw certificates independently recounted; existing original LSS identity inventory only, missing identities remain unvalidated; NOT full cost-order LSS postselection or30-run Avg',unique_semantic_raw_certificates_recounted=len(results),final_pool_records=len(final_pool),saved_CDF_records=len(cdf),all_saved_CDF_retained_by_selection={tuple(r['selection']) for r in cdf}<={tuple(r['selection']) for r in final_pool},minimum_independent_raw_lower=float(minimum),candidate_recounts=results,known_LSS_records=len(known),unknown_LSS_records=len(unknown),lower_than_current_known_pass=sum(v['cost']<current-1e-9 and v['passed'] for v in known),lower_than_current_known_reject=sum(v['cost']<current-1e-9 and not v['passed'] for v in known),lower_than_current_unknown=sum(v['cost']<current-1e-9 for v in unknown),known_LSS_qualified_upper_cost=best['cost'] if best else None,CDF_stage_known_LSS_qualified_upper_cost=min((r['cost'] for r in passing if tuple(r['selection']) in cdf_set),default=None),known_LSS_qualified_upper_record=best,known_records=known,unknown_records=unknown,new_native_MC_calls=0,used_only_after_frozen_search=True,no_optimizer_feedback=True,result_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),independent_verifier_sha256=check['source_sha256'],seconds=time.monotonic()-start)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['candidate_recounts','known_records','unknown_records','known_LSS_qualified_upper_record']}))
