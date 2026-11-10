"""Independent original-LSS prefix/physical-ledger verifier; never calls engine.

Usable on completed development fixtures for preflight, and on the actual formal
namespace after it terminates. Errors remain incomplete outcomes, never rejection.
"""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,pickle,math,time
from independent_raw_recount import verify
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(root,study):
 H=Path(root).resolve();D=H/study;started=time.monotonic();reg=json.load(open(D/'REGISTRATION.json'));result=json.load(open(D/'RESULT.json'));cat=json.load(open(D/'CATALOGUE.json'));reference=json.load(open(H/'REFERENCE_SHA256.json'));dist=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];isolation=json.load(open(D/'FORMAL_ISOLATION_AFTER.json'));validated={};models={};rawcache={}
 if result['registration_sha256']!=sha(D/'REGISTRATION.json') or result['unrecorded_private_attempt_keys'] or not isolation['original_receipts_unchanged']:raise RuntimeError('Original registration/isolation/physical attempt coverage differs')
 for n,d in {**reg['source_sha256'],**reg['input_sha256']}.items():
  if sha(H/n)!=d:raise RuntimeError('Frozen actual source/input changed')
 for r in reference['files']:
  if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original21 reference sources changed')
 private=result['private_new_outcomes']
 def checked(identity,key):
  if key in validated:return validated[key]
  if hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()!=key:raise RuntimeError('Original native key/selection/capacity differs')
  file=H/cat[key]['path'] if key in cat else D/'receipts'/(key+'.json')
  if key in cat and sha(file)!=cat[key]['sha256']:raise RuntimeError('Pinned completed receipt changed')
  v=json.load(open(file));P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/identity['instance']
  if any(v[k]!=x for k,x in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1' or not math.isfinite(v['real_probability']) or not 0<=v['real_probability']<=1 or not math.isfinite(v['seconds']) or v['seconds']<0 or v['passed']!=(v['real_probability']>=.985) or v['search_feedback'] or v['role']!='external_validation_and_postselection' or not all(v[k] for k in ['original_full_module','original_sources_unmodified','aliases_only']):raise RuntimeError('Original native source/env/data/event/point acceptance differs')
  if set(v['distribution_sha256'])!={str(j)+'_dist.txt' for j in identity['selection']}:raise RuntimeError('Incomplete original true-data identity')
  for n,d in v['distribution_sha256'].items():
   if dist[identity['instance']+'/'+n]!=d or sha(P/n)!=d:raise RuntimeError('Original true distribution changed')
  validated[key]=dict(key=key,passed=v['passed'],probability=v['real_probability'],seconds=v['seconds'],receipt_path=file.relative_to(H).as_posix(),receipt_sha256=sha(file));return validated[key]
 states={};required=set();selected={};selectedraw={}
 for name,info in reg['pools'].items():
  file=H/info['result_file']
  if sha(file)!=info['result_sha256']:raise RuntimeError('Frozen complete pool changed')
  data=json.loads(gzip.decompress(file.read_bytes()));P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/data['instance']
  if data['instance'] not in models:
   prices=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;models[data['instance']]=(prices,groups)
  prices,groups=models[data['instance']];pool=data['candidate_shortlist'];tested=[];missing=[];failed=[];keys=[];upper=None;choice=None
  if pool!=sorted(pool,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in pool})!=len(pool):raise RuntimeError('Frozen full pool not unique cost order')
  for candidate in pool:
   q=candidate['selection'];cert=candidate['certificate']
   if len(q)!=len(groups) or len(set(q))!=len(q) or any(j not in groups[g] for g,j in enumerate(q)) or cert['selection']!=q or cert['strict_event']!='sum<T' or not cert['all_original_samples'] or 100*int(cert['lower_numerator'])<99*int(cert['denominator']) or abs(candidate['cost']-float(sum((prices[j] for j in q),F(0))))>1e-9:raise RuntimeError('Pool canonical cost/original99 certificate differs')
   identity=dict(instance=data['instance'],capacity=float(data['capacity']),selection=q,seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();keys.append(key);required.add(key)
   if key not in cat and key not in private:missing.append(key);continue
   if key not in cat and private[key]['error']:failed.append(key);continue
   v=checked(identity,key);tested.append(dict(v,cost=candidate['cost']))
   if v['passed']:
    upper=dict(key=key,cost=candidate['cost'],selection=q,identity=identity);choice=dict(candidate,native_key=key,original_native_point=v['probability']);break
  complete=not missing and not failed;accepted=complete and upper is not None;reported=result['accounting']['pools'][name];logical=sum(v['seconds'] for v in tested)
  if reported['prefix_complete']!=complete or reported['accepted']!=accepted or reported['missing_keys']!=missing or reported['failed_keys']!=failed or reported['required_keys']!=keys or (reported['selected']['key'] if reported['selected'] else None)!=(upper['key'] if accepted else None) or abs(reported['logical_original_MC_seconds']-logical)>1e-8:raise RuntimeError('Independent direct prefix differs from controller/complete/error accounting')
  if (reported['known_feasible_upper']['key'] if reported['known_feasible_upper'] else None)!=(upper['key'] if upper else None):raise RuntimeError('Frozen-pool known upper differs')
  if accepted:
   cert=choice['certificate'];rk=(data['instance'],F(str(data['capacity'])),tuple(choice['selection']),cert['method'],cert.get('bins'),cert['lower_numerator'],cert.get('upper_numerator'),cert['denominator'])
   if rk not in rawcache:rawcache[rk]=verify(P,choice['selection'],data['capacity'],cert)
   selected[name]=choice;selectedraw[name]=rawcache[rk]
  states[name]=dict(prefix_complete=complete,accepted=accepted,selected_key=upper['key'] if accepted else None,cost=upper['cost'] if accepted else None,known_upper_cost=upper['cost'] if upper else None,original_native_point=choice['original_native_point'] if accepted else None,prefix_calls=len(keys),observed_successful_receipts=len(tested),cheaper_rejected=len(keys)-1 if accepted else None,logical_original_MC_seconds=logical,missing_keys=missing,failed_keys=failed,required_keys=keys,prefix=tested,source_seed=info['seed'])
 logs={p.stem for p in (D/'receipts').glob('*.log')};files={p.stem for p in (D/'receipts').glob('*.json')};attempted={k for k,r in private.items() if r['new_attempt']}
 if logs!=attempted or files-set(private) or files-attempted or result['private_log_keys']!=sorted(logs) or result['private_receipt_keys']!=sorted(files) or result['physical_attempt_logs']!=len(logs) or result['accounting']['physical_new_attempts']!=len(logs):raise RuntimeError('Every physical attempt/log/receipt must be accounted')
 errors=[];failedwall=0.
 for key,row in private.items():
  if key in cat:raise RuntimeError('New private call duplicated fixed read-only catalogue')
  if not math.isfinite(row['attempt_wall']) or row['attempt_wall']<0:raise RuntimeError('Invalid actual private-attempt timing')
  file=D/'receipts'/(key+'.json')
  if row['error']:
   if row['passed'] or row['probability'] is not None or (key in files and row['receipt_sha256']!=sha(file)):raise RuntimeError('Failed native attempt must remain unresolved with partial bytes preserved')
   errors.append(dict(key=key,error=row['error'],new_attempt=row['new_attempt'],attempt_wall=row['attempt_wall'],partial_receipt=key in files));failedwall+=row['attempt_wall'];continue
  if not row['new_attempt'] or key not in files:raise RuntimeError('Successful new native result lacks actual physical receipt')
  v=json.load(open(file));identity={k:v[k] for k in ['instance','capacity','selection','seed','draws','event']};check=checked(identity,key)
  if row['receipt_sha256']!=check['receipt_sha256'] or row['passed']!=check['passed'] or row['probability']!=check['probability'] or row['seconds']!=check['seconds']:raise RuntimeError('Actual private receipt differs from controller ledger')
 spec=sorted(attempted-required);successseconds=sum(validated[k]['seconds'] for k in attempted if not private[k]['error'])
 if spec!=result['accounting']['speculative_new_keys'] or abs(successseconds-result['physical_new_original_MC_seconds'])>1e-8 or abs(sum(r['attempt_wall'] for r in private.values())-result['private_attempt_wall_sum'])>1e-8 or result['accounting']['unique_required_identities']!=len(required) or result['accounting']['all_prefixes_complete']!=all(v['prefix_complete'] for v in states.values()):raise RuntimeError('Global unique/physical/speculative/timing accounting differs')
 expected_required={k for k in required if k in cat or k in private}
 if set(result['required_outcomes'])!=expected_required:raise RuntimeError('Controller required-outcome coverage differs')
 for key in expected_required:
  reported=result['required_outcomes'][key]
  if key in private and private[key]['error']:
   if reported!=private[key]:raise RuntimeError('Required native failure ledger changed')
  else:
   v=validated[key]
   if any(reported[n]!=v[n] for n in ['key','passed','probability','seconds','receipt_path','receipt_sha256']):raise RuntimeError('Required original receipt ledger changed')
 return dict(integrity_passed=True,passed=not result['controller_error'] and not errors and all(v['accepted'] for v in states.values()),scope=__doc__,pools=states,selected_by_pool=selected,selected_raw_recounts=selectedraw,controller_error=result['controller_error'],native_errors=errors,physical_new_MC_attempts=len(logs),physical_successful_MC_receipts=len(logs)-sum(r['new_attempt'] for r in errors),physical_new_original_MC_seconds=successseconds,physical_failed_attempt_wall_seconds=failedwall,speculative_extra_MC_keys=spec,speculative_extra_MC_seconds=sum(validated[k]['seconds'] for k in spec if not private[k]['error']),unique_required_identities=len(required),unique_receipts_checked=len(validated),selected_raw_unique_recounts=len(rawcache),shared_cache_original448_unchanged=True,result_sha256=sha(D/'RESULT.json'),registration_sha256=sha(D/'REGISTRATION.json'),no_new_MC_calls_by_auditor=True,seconds=time.monotonic()-started)
