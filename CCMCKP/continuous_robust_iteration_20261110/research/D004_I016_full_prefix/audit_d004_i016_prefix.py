"""Independent direct prefix scan, selected raw recount and physical-MC ledger."""
from pathlib import Path
from fractions import Fraction as F
import json, gzip, hashlib, math, pickle
from independent_raw_recount import verify

H=Path(__file__).resolve().parent;D=H/'research/D004_I016_full_prefix';out=D/'INDEPENDENT_FINAL_AUDIT.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No independent final audit overwrite')
reg=json.load(open(D/'REGISTRATION.json'));result=json.load(open(D/'RESULT.json'));catalogue=json.load(open(D/'CATALOGUE.json'));reference=json.load(open(H/'REFERENCE_SHA256.json'));dist=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];isolation=json.load(open(D/'FORMAL_ISOLATION_AFTER.json'));validated={}
if result['controller_error'] or not result['accounting']['all_prefixes_complete'] or result['unrecorded_private_attempt_keys'] or result['registration_sha256']!=sha(D/'REGISTRATION.json') or not isolation['original_receipts_unchanged']:raise RuntimeError('Actual full prefix/controller/isolation not complete')
for n,digest in reg['source_sha256'].items():
 if sha(H/n)!=digest:raise RuntimeError('Registered prefix source changed')
for n,digest in reg['input_sha256'].items():
 if sha(H/n)!=digest:raise RuntimeError('Frozen pool/audit/catalogue input changed')
for item in reference['files']:
 if sha(H/'reference'/item['path'])!=item['sha256']:raise RuntimeError('Original reference source changed')

def checked_native(identity,key):
 if key in validated:return validated[key]
 actual=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
 if actual!=key:raise RuntimeError('Validation identity key changed')
 file=H/catalogue[key]['path'] if key in catalogue else D/'receipts'/(key+'.json')
 if key in catalogue and sha(file)!=catalogue[key]['sha256']:raise RuntimeError('Pinned old receipt changed')
 v=json.load(open(file));P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/identity['instance']
 if any(v[k]!=x for k,x in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1' or not math.isfinite(v['real_probability']) or not 0<=v['real_probability']<=1 or v['passed']!=(v['real_probability']>=.985) or v['search_feedback'] or v['role']!='external_validation_and_postselection' or not all(v[k] for k in ['original_full_module','original_sources_unmodified','aliases_only']):raise RuntimeError('Original native source/env/identity/event/point gate changed')
 if set(v['distribution_sha256'])!={str(j)+'_dist.txt' for j in identity['selection']}:raise RuntimeError('Incomplete original native dataset identity')
 for name,digest in v['distribution_sha256'].items():
  if dist[identity['instance']+'/'+name]!=digest or sha(P/name)!=digest:raise RuntimeError('Original true-data distribution changed')
 validated[key]=dict(key=key,passed=v['passed'],probability=v['real_probability'],seconds=v['seconds'],receipt_path=file.relative_to(H).as_posix(),receipt_sha256=sha(file));return validated[key]

states={};required=set();raw_results={};selected_by_pool={}
for label,info in reg['pools'].items():
 file=H/info['result_file'];data=json.loads(gzip.decompress(file.read_bytes()));P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/data['instance'];prices=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;pool=sorted(data['candidate_shortlist'],key=lambda r:(r['cost'],r['selection']));tested=[];selected=None
 for candidate in pool:
  q=candidate['selection'];cert=candidate['certificate']
  if len(q)!=len(groups) or any(j not in groups[g] for g,j in enumerate(q)) or cert['selection']!=q or 100*int(cert['lower_numerator'])<99*int(cert['denominator']) or abs(candidate['cost']-float(sum((prices[j] for j in q),F(0))))>1e-9:raise RuntimeError('Pool group/cost/raw certificate identity differs')
  identity=dict(instance=data['instance'],capacity=float(data['capacity']),selection=q,seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();v=checked_native(identity,key);required.add(key);tested.append(dict(v,cost=candidate['cost']))
  if v['passed']:
   selected=dict(candidate,native_key=key,original_native_point=v['probability']);raw_results[label]=verify(P,q,data['capacity'],cert);break
 reported=result['accounting']['pools'][label]
 if not selected or reported['selected']['key']!=selected['native_key'] or [r['key'] for r in tested]!=reported['required_keys'] or not reported['accepted'] or not reported['prefix_complete'] or abs(sum(r['seconds'] for r in tested)-reported['logical_original_MC_seconds'])>1e-8:raise RuntimeError('Independent direct prefix differs from reported selection/accounting')
 selected_by_pool[label]=selected;states[label]=dict(cost=selected['cost'],original_native_point=selected['original_native_point'],selected_key=selected['native_key'],prefix_calls=len(tested),cheaper_rejected=len(tested)-1,logical_original_MC_seconds=sum(r['seconds'] for r in tested),prefix=tested,source_seed=info['seed'])

private=result['private_new_outcomes'];logkeys={p.stem for p in (D/'receipts').glob('*.log')};receiptkeys={p.stem for p in (D/'receipts').glob('*.json')}
if set(private)!=logkeys or logkeys!=receiptkeys or len(logkeys)!=result['accounting']['physical_new_attempts'] or len(logkeys)!=result['physical_attempt_logs']:raise RuntimeError('Private physical attempts/receipts/logs not fully accounted')
for key,row in private.items():
 file=D/'receipts'/(key+'.json');v=json.load(open(file));identity={k:v[k] for k in ['instance','capacity','selection','seed','draws','event']};checked=checked_native(identity,key)
 if row['error'] or not row['new_attempt'] or row['receipt_sha256']!=checked['receipt_sha256'] or row['passed']!=checked['passed'] or row['probability']!=checked['probability'] or row['seconds']!=checked['seconds']:raise RuntimeError('Actual private call differs from controller ledger')
speculative=sorted(logkeys-required)
if speculative!=result['accounting']['speculative_new_keys'] or abs(sum(validated[k]['seconds'] for k in logkeys)-result['physical_new_original_MC_seconds'])>1e-8:raise RuntimeError('Physical/speculative original-MC accounting differs')
audit=dict(passed=True,scope='independent direct scans of complete frozen single I016 cold cost prefixes, selected original raw integer recounts, original native identities and all new physical/speculative calls; one cold engineering result, not30-run Avg or global optimum',pools=states,selected_by_pool=selected_by_pool,selected_raw_recounts=raw_results,physical_new_MC_attempts=len(logkeys),physical_new_original_MC_seconds=sum(validated[k]['seconds'] for k in logkeys),speculative_extra_MC_keys=speculative,speculative_extra_MC_seconds=sum(validated[k]['seconds'] for k in speculative),unique_required_identities=len(required),unique_receipts_checked=len(validated),shared_cache_original448_unchanged=True,shared_inventory_identical=isolation['inventory_identical_to_before'],shared_log_names_identical=isolation['log_names_identical_to_before'],result_sha256=sha(D/'RESULT.json'),registration_sha256=sha(D/'REGISTRATION.json'),no_new_MC_calls_by_auditor=True)
with out.open('x') as stream:json.dump(audit,stream,indent=2)
print(json.dumps({k:v for k,v in audit.items() if k not in ['pools','selected_by_pool','selected_raw_recounts']}));print(json.dumps({k:{n:v[n] for n in ['cost','original_native_point','prefix_calls','cheaper_rejected']} for k,v in states.items()}))
