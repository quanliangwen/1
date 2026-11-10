"""All THREE registered I016 searches, direct complete cached-prefix audit only.

Parent comparison stays pending until its three complete prefixes finish. No
registered I016 seed is omitted, no new MC is executed, no30-run claim is made.
"""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,pickle,math,statistics
from independent_raw_recount import verify
H=Path(__file__).resolve().parent;D=H/'research/D005_I016_pair_prefix';S=H/'stability/I016_pair_cover_case39';out=D/'CACHED_I016_SUBGROUP_AUDIT.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No complete registered subgroup audit overwrite')
reg=json.load(open(D/'REGISTRATION.json'));cohort=json.load(open(S/'REGISTRATION.json'));raw=json.load(open(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'));post=json.load(open(S/'POSTPROCESS_TERMINAL.json'));cat=json.load(open(D/'CATALOGUE.json'));reference=json.load(open(H/'REFERENCE_SHA256.json'));dist=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256']
if not raw['passed'] or not post['passed'] or raw['registration_sha256']!=sha(S/'REGISTRATION.json') or len(cohort['seeds'])!=3 or raw['required_searches']!=6:raise RuntimeError('Actual all6cold/raw protocol proof required first')
for n,digest in {**reg['source_sha256'],**reg['input_sha256']}.items():
 if sha(H/n)!=digest:raise RuntimeError('Frozen source/native protocol/cohort input changed')
for r in reference['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original21reference source changed')
P=Path(cohort['benchmark']);prices=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;checked={};rows=[];recounts={}
def native(identity,key):
 if key in checked:return checked[key]
 if key not in cat:raise RuntimeError('Cheaper subgroup member unknown: cannot report complete subgroup Avg')
 file=H/cat[key]['path']
 if sha(file)!=cat[key]['sha256']:raise RuntimeError('Pinned completed receipt changed')
 v=json.load(open(file))
 if any(v[k]!=x for k,x in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1' or v['passed']!=(v['real_probability']>=.985) or not math.isfinite(v['real_probability']) or not 0<=v['real_probability']<=1 or v['search_feedback'] or v['role']!='external_validation_and_postselection' or not all(v[k] for k in ['original_full_module','original_sources_unmodified','aliases_only']):raise RuntimeError('Original native identity/source/env/point/role differs')
 if set(v['distribution_sha256'])!={str(j)+'_dist.txt' for j in identity['selection']}:raise RuntimeError('Incomplete native distribution identity')
 for n,digest in v['distribution_sha256'].items():
  if dist[identity['instance']+'/'+n]!=digest or sha(P/n)!=digest:raise RuntimeError('Original true distribution changed')
 checked[key]=dict(key=key,passed=v['passed'],probability=v['real_probability'],seconds=v['seconds'],receipt_path=cat[key]['path'],receipt_sha256=cat[key]['sha256']);return checked[key]
expected={'I016_pair_cover_seed'+str(seed) for seed in cohort['seeds']}
if {k for k,v in reg['pools'].items() if v['label']=='I016_pair_cover'}!=expected:raise RuntimeError('Exactly all3registered I016 seeds required')
for seed in cohort['seeds']:
 name='I016_pair_cover_seed'+str(seed);info=reg['pools'][name];file=H/info['result_file'];data=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(str(file)+'.run.json'))
 if sha(file)!=info['result_sha256'] or data['seed']!=seed or meta['seed']!=seed or meta['source_sha256']!=cohort['sources']['I016_pair_cover']['source_sha256'] or data['capacity']!=cohort['capacity'] or data['instance']!=cohort['instance'] or not meta['within_budget'] or data['extension']['extension_seconds']>180:raise RuntimeError('Actual registered subgroup/source/seed/budget differs')
 tested=[];selected=None
 for candidate in sorted(data['candidate_shortlist'],key=lambda r:(r['cost'],r['selection'])):
  q=candidate['selection'];cert=candidate['certificate']
  if len(q)!=len(groups) or any(j not in groups[g] for g,j in enumerate(q)) or cert['selection']!=q or not cert['all_original_samples'] or cert['strict_event']!='sum<T' or 100*int(cert['lower_numerator'])<99*int(cert['denominator']) or abs(candidate['cost']-float(sum((prices[j] for j in q),F(0))))>1e-9:raise RuntimeError('Pool raw/canonical/cost identity differs')
  identity=dict(instance=data['instance'],capacity=float(data['capacity']),selection=q,seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();v=native(identity,key);tested.append(dict(v,cost=candidate['cost']))
  if v['passed']:
   selected=dict(candidate,native_key=key,original_native_point=v['probability']);recounts[name]=verify(P,q,data['capacity'],cert);break
 initial=info['initial_prefix']
 if not selected or not initial['prefix_complete'] or not initial['accepted'] or initial['selected']['key']!=selected['native_key'] or initial['required_keys']!=[r['key'] for r in tested] or not recounts[name]['passed']:raise RuntimeError('Direct complete prefix differs from registered state')
 rows.append(dict(seed=seed,cost=selected['cost'],selected=selected,original_native_point=selected['original_native_point'],independent_raw_lower=recounts[name]['lower'],prefix_calls=len(tested),cheaper_rejected=len(tested)-1,prefix=tested,search_seconds=info['search_seconds'],logical_original_MC_seconds=sum(r['seconds'] for r in tested)))
costs=[r['cost'] for r in rows];best=min(costs);avg=statistics.mean(costs)
result=dict(passed=True,scope=__doc__,label='I016_pair_cover',registered_runs=3,qualified_runs=3,all_registered_I016_seeds_included=True,Best=best,Avg=avg,Std_population=statistics.pstdev(costs),Avg_minus_own_Best=avg-best,rows=rows,selected_raw_recounts=recounts,unique_original_receipts_checked=len(checked),source_sha256=cohort['sources']['I016_pair_cover']['source_sha256'],native_study_registration_sha256=sha(D/'REGISTRATION.json'),cohort_raw_audit_sha256=sha(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'),parent_comparison_pending=True,whole6native_comparison_complete=False,new_MC_calls_by_this_auditor=0,fixed_MC_seed=832273,fixed_MC_draws=10000000,not3_independent_probability_estimates=True)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['rows','selected_raw_recounts','source_sha256']}))
