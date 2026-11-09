from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,pickle,collections
H=Path(__file__).resolve().parent;I=H/'iterations/I015_precision_closure';J=I/'engineering39';out=J/'ASSESSMENT.json'
if out.exists():raise RuntimeError('No assessment overwrite')
file=J/'result.json.gz';d=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(str(file)+'.run.json'));reg=json.load(open(J/'REGISTRATION.json'));source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (I/'candidate').glob('*.py')}
if meta['source_sha256']!=source or reg['source_sha256']!=source or d['status']!='completed' or meta['seed']!=reg['seed'] or d['seed']!=reg['seed'] or d['capacity']!=reg['capacity'] or d['instance']!=reg['instance']:raise RuntimeError('Cold run identity/source differs')
for name in ['MATH_CHECK.json','CDF_MATH_CHECK.json','SCHEDULE_CHECK.json','HYBRID_INTEGRATION_CHECK.json','PRECISION_SCHEDULE_CHECK.json','PRECISION_INTEGRATION_CHECK.json']:
 check=json.load(open(I/name))
 if not check['passed'] or check['source_sha256']!=source:raise RuntimeError('Source/check differs')
P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/reg['instance'];rawref=json.load(open(H/'RAW_REFERENCE.json'));cost=[F(s) for s in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
for name,digest in meta['input_sha256'].items():
 if hashlib.sha256((P/name).read_bytes()).hexdigest()!=digest or rawref[str(P/name)]!=digest:raise RuntimeError('Original input changed')
for opened in meta['opened_task_paths']:
 p=Path(opened)
 if p.name.endswith('_dist.txt') or '/lss_cache/' in opened or p.name=='BASELINE_S10.json':raise RuntimeError('Optimizer used true/history data')
 if P in p.parents and p.name not in meta['input_sha256']:raise RuntimeError('Unregistered benchmark read')
def check_pool(pool):
 if pool!=sorted(pool,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in pool})!=len(pool):raise RuntimeError('Pool not unique cost ordered')
 for r in pool:
  q=r['selection'];c=r['certificate']
  if len(q)!=len(groups) or any(j not in groups[g] for g,j in enumerate(q)) or c['selection']!=q or c['strict_event']!='sum<T' or not c['all_original_samples'] or 100*int(c['lower_numerator'])<99*int(c['denominator']):raise RuntimeError('Invalid canonical original raw certificate')
  if abs(r['cost']-float(sum((cost[j] for j in q),F(0))))>1e-9:raise RuntimeError('Cost differs')
pool=d['candidate_shortlist'];ext=d['extension'];h=ext['hybrid'];cdf=h['cdf_pool_records'];pc=ext['precision_closure'];added={tuple(r['selection']) for r in pc['records'] if r['status']=='raw_certified'};pre_pool=[r for r in pool if tuple(r['selection']) not in added];check_pool(pool);check_pool(cdf);check_pool(pre_pool);final_set={tuple(r['selection']) for r in pool};cdf_set={tuple(r['selection']) for r in cdf}
if not h['cdf_executed'] or not h['all_own_cdf_retained'] or not h['all_initial_retained'] or not cdf_set<=final_set or h['cdf_pool']!=len(cdf) or h['final_pool']!=len(pre_pool) or h['initial_pool']!=ext['base_pool']:raise RuntimeError('Own-CDF origin/retention failure')
c=h['robust_cdf_lns'];b=h['robust_blocks']
if c['initial_certified']!=ext['base_pool'] or c['final_certified']!=len(cdf) or c['initial_certified']+c['new_certified']!=len(cdf):raise RuntimeError('CDF-stage initial retention mismatch')
if b and (b['initial_certified']!=len(cdf) or b['final_certified']!=len(pre_pool) or b['initial_certified']+b['new_certified']!=len(pre_pool)):raise RuntimeError('Block-stage retention mismatch')
if pc['initial_pool']!=len(pre_pool) or pc['final_pool']!=len(pool) or len(added)!=pc['accepted'] or not pc['all_initial_retained'] or not {tuple(r['selection']) for r in cdf}<={tuple(r['selection']) for r in pre_pool}:raise RuntimeError('Precision retained-pool accounting differs')
if meta['risk_method']!=reg['method'] or pc['shared_deadline']>pc['phase_started']+reg['phase_seconds'] or pc['phase_seconds_used']>reg['phase_seconds'] or not pc['phase_within_budget'] or pc['budget_overrun'] or ext['extension_seconds']>reg['phase_seconds'] or not meta['within_budget']:raise RuntimeError('Shared phase/global budget exceeded; not eligible performance evidence')
if len({tuple(r['selection']) for r in pc['records']})!=len(pc['records']) or pc['new_integer_calls']!=sum(a['kind']=='new_same_run_integer_certificate' for r in pc['records'] for a in r['attempts']):raise RuntimeError('Precision queue/call accounting differs')
by_q={tuple(r['selection']):r for r in pool}
for row in pc['records']:
 q=tuple(row['selection']);cert=row.get('final_certificate')
 if row['initial_decision'].get('decision')!='unresolved' or any(tuple(r['selection'])==q for r in pre_pool):raise RuntimeError('Precision queue not solely own unresolved missing members')
 if cert:
  if cert['selection']!=list(q) or not cert['all_original_samples'] or cert['strict_event']!='sum<T':raise RuntimeError('Precision raw identity changed')
  n,u,den=int(cert['lower_numerator']),int(cert['upper_numerator']),int(cert['denominator'])
  if not 0<=n<=u<=den or den<=0:raise RuntimeError('Invalid precision integer interval')
  if (row['status']=='raw_certified')!=(100*n>=99*den) or (row['status']=='integer_raw_refuted')!=(100*u<99*den):raise RuntimeError('Precision integer decision differs')
 if row['status']=='raw_certified':
  if q not in by_q or by_q[q]['certificate']!=cert:raise RuntimeError('Recovered precision certificate absent/changed in final pool')
 elif q in by_q:raise RuntimeError('Uncertified precision member added to final pool')
current=json.load(open(H/'iterations/I004_robust_pair_exchange/REGISTRATION.json'))['current_qualified_costs']['39'];old2=json.loads(gzip.decompress((H/'iterations/I002_cdf_neighborhood/pilot/cdf_lns_39_seed970201.json.gz').read_bytes()));old4=json.loads(gzip.decompress((H/'iterations/I004_robust_pair_exchange/pilot/pair_exchange_39_seed970401.json.gz').read_bytes()));old12=json.loads(gzip.decompress((H/'iterations/I012_iterated_block_mitm/engineering39/result.json.gz').read_bytes()));s2={tuple(r['selection']) for r in old2['candidate_shortlist']};s4={tuple(r['selection']) for r in old4['candidate_shortlist']};s12={tuple(r['selection']) for r in old12['candidate_shortlist']};known2=json.load(open(H/'iterations/I002_cdf_neighborhood/pilot_validation/cdf_lns_39_seed970201.json.gz.post.json'))['selected'];below=[r for r in pool if r['cost']<current-1e-9];parts=[r for r in (b or {}).get('records',[]) if r['kind']=='robust_block_mitm']
result=dict(passed=True,scope='one frozen engineering search structural/source/input/budget audit, not original LSS qualification or30-run Avg',source_sha256=source,search_seconds=meta['elapsed'],within_budget=meta['within_budget'],phase_seconds_used=pc['phase_seconds_used'],phase_within_budget=pc['phase_within_budget'] and ext['extension_seconds']<=reg['phase_seconds'],precision_seconds=pc['closure_seconds'],precision_initial_unresolved=pc['unresolved_initial'],precision_new_integer_calls=pc['new_integer_calls'],precision_cached_reused=pc['cached_certificates_reused'],precision_new_raw_accepted=pc['accepted'],precision_raw_refuted=pc['refuted'],precision_unresolved_remaining=pc['unresolved_remaining'],precision_admission_skips=pc['admission_skips'],precision_added_costs=sorted(r['cost'] for r in pc['records'] if r['status']=='raw_certified'),pre_precision_pool=len(pre_pool),base_seconds=ext['base_seconds'],cdf_seconds=h['cdf_seconds'],block_seconds=h['block_seconds'],extension_seconds=ext['extension_seconds'],base_pool=ext['base_pool'],cdf_pool=len(cdf),final_pool=len(pool),new_CDF=c['new_certified'],new_blocks=b['new_certified'] if b else 0,remaining_phase_for_blocks=h['remaining_for_blocks'],all_own_CDF_candidates_retained=True,cdf_snapshot_sha256=hashlib.sha256(json.dumps(cdf,sort_keys=True).encode()).hexdigest(),current_I002_qualified_reference=current,current_I002_vector_in_CDF_pool=tuple(known2['selection']) in cdf_set,current_I002_vector_in_final_pool=tuple(known2['selection']) in final_set,lower_cost_raw_candidates=len(below),new_lower_vs_I002=sum(tuple(r['selection']) not in s2 for r in below),new_lower_vs_I002_I004_I012=sum(tuple(r['selection']) not in s2|s4|s12 for r in below),raw_min=min(r['cost'] for r in pool),blocks_by_size=dict(collections.Counter(r['block_size'] for r in parts)),blocks_by_delta=dict(collections.Counter(str(r['delta']) for r in parts)),scored_combinations=sum(r['evaluated_combinations'] for r in parts),complete_block_scans=sum(r['complete_block_scan'] for r in parts),partial_block_scans=sum(not r['complete_block_scan'] for r in parts),raw_acceptance_unchanged=True,no_LSS_calls=True,result_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))
