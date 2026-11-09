"""Complete-cohort audit and data for the final Excel. No partial30-run Avg."""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,pickle,math,statistics,time,sys
H=Path(__file__).parent;D=H/'formal/F001_I002_40x30';S=D/'search';V=D/'validation';out=D/'FINAL_AUDIT_STATS.json'
if not (S/'FINISHED').exists() or not (V/'FINISHED').exists():
 print(json.dumps(dict(ready=False,stage=json.load(open(D/'STAGE.json'))['stage'],search_terminal=len(list(S.glob('*.terminal.json'))),validation_terminal=len(list(V.glob('*.post.json'))),required=1200,final_statistics_written=False)));sys.exit(0)
if out.exists():raise RuntimeError('No final audit overwrite')
from independent_raw_recount import verify
start=time.monotonic();reg=json.load(open(D/'REGISTRATION.json'));cases={r['index']:r for r in json.load(open(H/'CASES.json'))};base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};rawref=json.load(open(H/'RAW_REFERENCE.json'));reference=json.load(open(H/'REFERENCE_SHA256.json'));distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];before=json.load(open(D/'CACHE_BEFORE_VALIDATION.json'));logs_before=json.load(open(D/'CACHE_LOGS_BEFORE_VALIDATION.json'));cutoff=(V/'FINISHED').stat().st_mtime
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for file in reference['files']:
 if sha(H/'reference'/file['path'])!=file['sha256']:raise RuntimeError('Original LSS source drift')
source={p.name:sha(p) for p in (H/'iterations/I002_cdf_neighborhood/candidate').glob('*.py')}
if source!=reg['source_sha256']:raise RuntimeError('Frozen optimizer source drift')
expected={f'cdf_lns_{i:02d}_seed{seed}.json.gz':(i,seed) for i in reg['cases'] for seed in reg['seeds']}
if len(expected)!=1200 or {p.name[:-len('.terminal.json')] for p in S.glob('*.terminal.json')}!=set(expected) or {p.name[:-len('.post.json')] for p in V.glob('*.post.json')}!=set(expected):raise RuntimeError('Not the registered1200unique attempts')
models={};input_identities={}
for i,c in cases.items():
 bench=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance']
 if c['instance'] not in models:
  cost=[F(x) for x in (bench/'cost.txt').read_text().split()];g=pickle.load(open(bench/'node_to_factor.pkl','rb'));g=[list(map(int,g[k])) for k in sorted(g,key=int)] if isinstance(g,dict) else [list(map(int,x)) for x in g]
  ids={name:rawref[str(bench/name)] for name in ['cost.txt','node_to_factor.pkl']+[f'{j}_sample.txt' for j in range(len(cost))]}
  for name,digest in ids.items():
   if sha(bench/name)!=digest:raise RuntimeError('Original raw input changed')
  models[c['instance']]=(bench,cost,g);input_identities[c['instance']]=ids
def check_choice(c,candidate):
 bench,cost,groups=models[c['instance']];s=candidate['selection'];cert=candidate['certificate']
 if len(s)!=len(groups) or any(j not in groups[g] for g,j in enumerate(s)) or len(set(s))!=len(s):raise RuntimeError('Invalid canonical selection')
 if cert['selection']!=s or cert['strict_event']!='sum<T' or not cert['all_original_samples'] or 100*int(cert['lower_numerator'])<99*int(cert['denominator']):raise RuntimeError('Invalid raw certificate')
 if not math.isclose(candidate['cost'],float(sum((cost[j] for j in s),F(0))),rel_tol=0.,abs_tol=1e-9):raise RuntimeError('Cost differs from original data')
native={};dist_checked=set();used=set();new_flags=[];recounts={};details=[];protocol_errors=[];logical_total=0.
def checked_native(c,candidate):
 identity=dict(instance=c['instance'],capacity=float(c['tmax']),selection=candidate['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
 if key not in native:
  p=H/'lss_cache'/(key+'.json');v=json.load(open(p));bench,_,_=models[c['instance']]
  if any(v[k]!=value for k,value in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1' or v['passed']!=(v['real_probability']>=.985):raise RuntimeError('Original native-call identity mismatch')
  if not all(v[k] for k in ['original_full_module','original_sources_unmodified','aliases_only']) or v['search_feedback']:raise RuntimeError('Wrong native evaluation role')
  if set(v['distribution_sha256'])!={f'{j}_dist.txt' for j in identity['selection']}:raise RuntimeError('Incomplete native data identity')
  for name,digest in v['distribution_sha256'].items():
   if (c['instance'],name,digest) not in dist_checked:
    if distref[c['instance']+'/'+name]!=digest or sha(bench/name)!=digest:raise RuntimeError('Original distribution changed')
    dist_checked.add((c['instance'],name,digest))
  native[key]=v
 used.add(key);return key,native[key]
for name,(i,seed) in sorted(expected.items(),key=lambda x:(x[1][0],x[1][1])):
 c=cases[i];file=S/name;t=json.load(open(str(file)+'.terminal.json'));post=json.load(open(V/(name+'.post.json')));row=dict(index=i,instance=c['instance'],tmax=c['tmax'],seed=seed,method='cdf_lns',search_exit=t['exit'],joint_accepted=False,protocol_valid=False)
 if t['index']!=i or t['seed']!=seed or post['index']!=i or post.get('search_seed',seed)!=seed:raise RuntimeError('Run identity mismatch')
 data=None;meta=None;pool=[]
 if t['exit']==0:
  data=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(str(file)+'.run.json'));bench,_,_=models[c['instance']]
  if meta['source_sha256']!=source or meta['input_sha256']!=input_identities[c['instance']] or meta['seed']!=seed or data['seed']!=seed or data['instance']!=c['instance'] or F(str(data['capacity']))!=F(str(c['tmax'])):raise RuntimeError('Search source/input/seed mismatch')
  for opened in meta['opened_task_paths']:
   p=Path(opened)
   if p.name.endswith('_dist.txt') or '/lss_cache/' in opened or p.name=='BASELINE_S10.json':raise RuntimeError('Optimizer read validation/history')
   if bench in p.parents and p.name not in meta['input_sha256']:raise RuntimeError('Unregistered benchmark read')
  if data['status']!='completed':raise RuntimeError('Exit0but incomplete result')
  pool=data['candidate_shortlist']
  if pool!=sorted(pool,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in pool})!=len(pool):raise RuntimeError('Pool is not unique cost ordered')
  for candidate in pool:check_choice(c,candidate)
  row.update(search_seconds=meta['elapsed'],search_wall_seconds=t['wall_seconds'],within_budget=meta['within_budget'],raw_pool=len(pool),search_result_sha256=sha(file))
  if meta['within_budget']!=(meta['elapsed']<=reg['search_seconds']):raise RuntimeError('Inconsistent budget report')
  if not meta['within_budget']:protocol_errors.append(dict(index=i,seed=seed,stage='search',error='budget_overrun'))
 else:
  row.update(search_seconds=t['wall_seconds'],search_wall_seconds=t['wall_seconds'],within_budget=False,raw_pool=0);protocol_errors.append(dict(index=i,seed=seed,stage='search',error=t['exit']))
 tested=post.get('tested',[]);first_pass=None;logical=0.
 if len(tested)>len(pool):raise RuntimeError('Validation tested outside source pool')
 for k,item in enumerate(tested):
  candidate=pool[k]
  if item['selection']!=candidate['selection'] or item['cost']!=candidate['cost']:raise RuntimeError('Not the frozen cost-order prefix')
  key,v=checked_native(c,candidate)
  if item['key']!=key or item['real_probability']!=v['real_probability'] or item['passed']!=v['passed'] or item['call_seconds']!=v['seconds']:raise RuntimeError('Postselector native record mismatch')
  logical+=item['call_seconds']
  if item['new_call_for_this_task']:new_flags.append(key)
  if item['passed']:
   if k!=len(tested)-1:raise RuntimeError('Postselection did not stop at first success')
   first_pass=(candidate,key,v)
 if post['accepted']!=(first_pass is not None):raise RuntimeError('Postselection success flag differs')
 if not post['accepted'] and not post.get('error') and len(tested)!=len(pool):raise RuntimeError('Unfinished cost-order postselection')
 row.update(logical_MC_seconds=logical,LSS_tested=len(tested),LSS_rejected=sum(not x['passed'] for x in tested),new_calls_charged_to_run=sum(x['new_call_for_this_task'] for x in tested),actual_post_seconds=post.get('actual_post_seconds'),post_error=post.get('error'))
 if post['accepted']:
  candidate,key,v=first_pass;selected=post['selected']
  if selected['selection']!=candidate['selection'] or selected['certificate']!=candidate['certificate'] or selected['cost']!=candidate['cost'] or selected['LSS_key']!=key or selected['real_probability']!=v['real_probability'] or post['source_sha256']!=sha(file):raise RuntimeError('Selected vector/certificate/source differs')
  cert=candidate['certificate'];semantic_cert={k:cert[k] for k in ['method','bins','lower_numerator','upper_numerator','denominator','strict_event','all_original_samples'] if k in cert}
  identity=[c['instance'],c['tmax'],candidate['selection'],semantic_cert];rk=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
  if rk not in recounts:
   result=verify(models[c['instance']][0],candidate['selection'],c['tmax'],candidate['certificate']);recounts[rk]=dict(result,key=rk,instance=c['instance'],capacity=c['tmax'],selection=candidate['selection'])
  row.update(joint_accepted=True,protocol_valid=t['exit']==0 and row['within_budget'],cost=selected['cost'],selection=selected['selection'],real_probability=v['real_probability'],original_raw_lower=selected['certificate']['lower'],independent_raw_lower=recounts[rk]['lower'],LSS_key=key,raw_recount_key=rk)
  if post['logical_MC_seconds']!=logical:raise RuntimeError('Logical MC timing differs')
 else:protocol_errors.append(dict(index=i,seed=seed,stage='validation',error=post.get('error','no qualified pool member')))
 logical_total+=logical;details.append(row)
before_map={r['key']:r for r in before['files']}
for key in used & set(before_map):
 if sha(H/'lss_cache'/(key+'.json'))!=before_map[key]['sha256']:raise RuntimeError('Historical native receipt overwritten')
physical=[p for p in (H/'lss_cache').glob('*.json') if p.stem not in before_map and p.stat().st_mtime<=cutoff];physical_keys={p.stem for p in physical};invoked_before={r['name'] for r in logs_before['files']};attempts=[p for p in (H/'lss_cache').glob('*.log') if p.name not in invoked_before and p.stat().st_mtime<=cutoff]
if set(new_flags)!=physical_keys or len(new_flags)!=len(set(new_flags)):raise RuntimeError('Physical calls differ from charged unique identities')
if physical_keys-used:raise RuntimeError('Unaccounted native output during formal validation')
summary=[]
for i in reg['cases']:
 rows=[r for r in details if r['index']==i];valid=[r for r in rows if r['protocol_valid']];costs=[r['cost'] for r in valid];complete=len(valid)==30
 if len(rows)!=30:raise RuntimeError('Missing registered seeds')
 summary.append(dict(index=i,instance=cases[i]['instance'],tmax=cases[i]['tmax'],attempts=30,joint_accepted=sum(r['joint_accepted'] for r in rows),protocol_valid=len(valid),best=min(costs) if costs else None,avg=statistics.mean(costs) if complete else None,std=statistics.pstdev(costs) if complete else None,mean_search_seconds=statistics.mean(r['search_seconds'] for r in rows),mean_search_wall_seconds=statistics.mean(r['search_wall_seconds'] for r in rows),mean_logical_MC_seconds=statistics.mean(r['logical_MC_seconds'] for r in rows),mean_standalone_logical_seconds=statistics.mean(r['search_seconds']+r['logical_MC_seconds'] for r in rows),minimum_real_probability=min((r['real_probability'] for r in valid),default=None),minimum_independent_raw_lower=min((r['independent_raw_lower'] for r in valid),default=None),old_best=base[i]['old_best'],S10_avg=base[i]['new_avg'],avg_minus_own_best=statistics.mean(costs)-min(costs) if complete else None,avg_minus_old_best=statistics.mean(costs)-base[i]['old_best'] if complete else None,old_best_known_joint_passed=base[i].get('old_Best_both_constraints_passed'),statistics_complete=complete))
result=dict(schema='F001_full_registered_cohort_independent_audit_and_Excel_data',integrity_passed=True,all1200_qualified=all(r['protocol_valid'] for r in details),registered_attempts=1200,joint_accepted=sum(r['joint_accepted'] for r in details),protocol_valid=sum(r['protocol_valid'] for r in details),source_sha256=source,raw_recount_verifier_sha256=sha(H/'independent_raw_recount.py'),independent_raw_recounts=list(recounts.values()),summary=summary,details=details,protocol_errors=protocol_errors,std_definition='population standard deviation over all30qualified costs; missing if any registered run invalid',postselection='original unchanged LSS cost-order first passing point>=.985; cached identical identities reused externally, never optimization feedback',native_inventory_before=len(before_map),native_invocation_logs_before=logs_before['invocation_logs'],unique_used_MC_keys=len(used),total_logical_MC_calls=sum(r['LSS_tested'] for r in details),physical_new_successful_MC_calls=len(physical),physical_new_invocation_attempts=len(attempts),physical_new_native_call_wall_seconds=sum(native[key]['seconds'] for key in physical_keys),total_logical_MC_seconds=logical_total,MC_seed=832273,MC_draws_per_identity=10000000,MC_event='sum<=T',MC_is_not_1200independent_random_seed_estimates=True,all_used_native_receipts=[dict(key=k,sha256=sha(H/'lss_cache'/(k+'.json')),instance=native[k]['instance'],capacity=native[k]['capacity'],selection=native[k]['selection'],probability=native[k]['real_probability'],passed=native[k]['passed'],seconds=native[k]['seconds'],was_preexisting=k in before_map) for k in sorted(used)],native_finish_time=cutoff,seconds=time.monotonic()-start)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','independent_raw_recounts','summary','details','all_used_native_receipts']}))
