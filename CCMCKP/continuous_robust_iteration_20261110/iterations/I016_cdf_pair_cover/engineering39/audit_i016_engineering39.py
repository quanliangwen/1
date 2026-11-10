"""Actual cold search structural/source/budget/read audit and all integer recounts."""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,pickle,time,collections
from independent_raw_recount import upward_grid_count
H=Path(__file__).resolve().parent;I=H/'iterations/I016_cdf_pair_cover';J=I/'engineering39';out=J/'INDEPENDENT_RAW_AUDIT.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No engineering audit overwrite')
started=time.monotonic();reg=json.load(open(J/'REGISTRATION.json'));terminal=json.load(open(J/'TERMINAL.json'));file=J/'result.json.gz';data=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(str(file)+'.run.json'));source={p.name:sha(p) for p in (I/'candidate').glob('*.py')}
if terminal['exit']!=0 or source!=reg['source_sha256'] or meta['source_sha256']!=source or terminal['source_sha256']!=source or data['status']!='completed' or data['seed']!=reg['seed'] or meta['seed']!=reg['seed'] or data['instance']!=reg['instance'] or data['capacity']!=reg['capacity'] or meta['risk_method']!=reg['method'] or not meta['within_budget'] or meta['elapsed']>reg['seconds'] or meta['budget']!=600:raise RuntimeError('Cold source/seed/method/input/status or total budget differs')
for n,digest in reg['checks_sha256'].items():
 c=json.load(open(I/n))
 if sha(I/n)!=digest or not c['passed'] or c['source_sha256']!=source:raise RuntimeError('Checked source changed')
config=data['config']
if config['raw_threshold']!='.99' or config['external_real_P_threshold']!=.985 or config['external_MC_seed']!=832273 or config['external_MC_draws']!=10000000 or config['tail_hard_gate'] or not config['all_original_samples']:raise RuntimeError('Original acceptance protocol changed')
P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/reg['instance'];rawref=json.load(open(H/'RAW_REFERENCE.json'));arrays={};expected=[P/'cost.txt',P/'node_to_factor.pkl']+[p for p in P.glob('*_sample.txt') if not p.name.endswith('_big_sample.txt')]
if {p.name:sha(p) for p in expected}!=meta['input_sha256']:raise RuntimeError('Actual complete raw input identity differs')
for name,digest in meta['input_sha256'].items():
 if rawref[str(P/name)]!=digest:raise RuntimeError('Original raw input changed')
 if name.endswith('_sample.txt'):arrays[int(name.split('_')[0])]=[F(x) for x in (P/name).read_text().split()]
vendor=(I/'vendor313').resolve();root=I/'candidate';own={str(file),str(file)+'.tmp',str(file)+'.run.json',str(file)+'.run.json.tmp',str(file.parent)}
for opened in meta['opened_task_paths']:
 p=Path(opened)
 if p.name.endswith('_dist.txt') or '/lss_cache/' in opened or p.name=='BASELINE_S10.json':raise RuntimeError('Optimizer read true/history/cache data')
 if P in p.parents and p.name not in meta['input_sha256']:raise RuntimeError('Unregistered benchmark read')
 if H.parent in p.parents and not (root in p.parents or p==root or vendor in p.parents or p==vendor or opened in own):raise RuntimeError('Cross-task/saved-vector input entered search')
prices=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups
ext=data['extension'];h=ext['pair_cover'];pc=ext['precision_closure'];pool=data['candidate_shortlist'];cdf=h['cdf_pool_records'];pairs=h['pair_pool_records'];added={tuple(r['selection']) for r in pc['records'] if r['status']=='raw_certified'};pre=[r for r in pool if tuple(r['selection']) not in added];sets=[{tuple(r['selection']) for r in rows} for rows in [cdf,pairs,pre,pool]]
if not h['cdf_executed'] or not h['all_initial_retained'] or not h['all_own_cdf_retained'] or not h['all_own_pair_retained'] or not pc['all_initial_retained'] or not sets[0]<=sets[1]<=sets[2]<=sets[3] or h['initial_pool']!=ext['base_pool'] or h['cdf_pool']!=len(cdf) or h['pair_pool']!=len(pairs) or h['final_pool']!=len(pre) or pc['initial_pool']!=len(pre) or pc['final_pool']!=len(pool) or len(added)!=pc['accepted']:raise RuntimeError('Own CDF/pair/block/precision pool lineage or retention differs')
for name,before,after in [('robust_cdf_lns',ext['base_pool'],len(cdf)),('robust_pairs',len(cdf),len(pairs)),('robust_blocks',len(pairs),len(pre))]:
 summary=h[name]
 if summary:
  if summary['initial_certified']!=before or summary['final_certified']!=after or summary['initial_certified']+summary['new_certified']!=after:raise RuntimeError('Stage own member accounting differs '+name)
 elif before!=after:raise RuntimeError('Skipped stage changed pool '+name)
if ext['extension_seconds']>180 or h['phase_seconds_used']>180 or pc['phase_seconds_used']>180 or pc['budget_overrun'] or not pc['phase_within_budget'] or pc['shared_deadline']>pc['phase_started']+180 or h['phase_deadline']>pc['phase_started']+180:raise RuntimeError('Shared phase deadline reset/exceeded')
if len({tuple(r['selection']) for r in pc['records']})!=len(pc['records']) or pc['new_integer_calls']!=sum(a['kind']=='new_same_run_integer_certificate' for r in pc['records'] for a in r['attempts']):raise RuntimeError('Precision unique own queue/call ledger differs')
byq={tuple(r['selection']):r for r in pool}
for row in pc['records']:
 q=tuple(row['selection']);c=row.get('final_certificate')
 if row['initial_decision'].get('decision')!='unresolved' or q in sets[2]:raise RuntimeError('Precision queue not own missing unresolved choices')
 if c:
  n,u,d=map(int,[c['lower_numerator'],c['upper_numerator'],c['denominator']])
  if c['selection']!=list(q) or not c['all_original_samples'] or c['strict_event']!='sum<T' or not 0<=n<=u<=d or d<=0 or (row['status']=='raw_certified')!=(100*n>=99*d) or (row['status']=='integer_raw_refuted')!=(100*u<99*d):raise RuntimeError('Precision original integer classification differs')
 if row['status']=='raw_certified':
  if q not in byq or byq[q]['certificate']!=c:raise RuntimeError('Precision certificate missing from retained pool')
 elif q in byq:raise RuntimeError('Uncertified precision choice entered pool')
unique={}
for rows in [pool,cdf,pairs]:
 if rows!=sorted(rows,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in rows})!=len(rows):raise RuntimeError('Pool not unique canonical cost order')
 for row in rows:
  q=row['selection'];c=row['certificate']
  if len(q)!=len(groups) or any(j not in groups[g] for g,j in enumerate(q)) or c['selection']!=q or c['method']!='exact_integer_upward_grid_count' or c['strict_event']!='sum<T' or not c['all_original_samples'] or not c['accepted'] or 100*int(c['lower_numerator'])<99*int(c['denominator']) or abs(row['cost']-float(sum((prices[j] for j in q),F(0))))>1e-9:raise RuntimeError('Pool canonical/group/raw/cost identity differs')
  unique[(tuple(q),c['bins'],c['lower_numerator'],c['denominator'])]=c
if data['raw_certified_pool_count']!=len(pool):raise RuntimeError('Final retained pool incomplete')
math=json.load(open(H/'INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json'))
if not math['passed'] or math['source_sha256']!=sha(H/'independent_raw_recount.py'):raise RuntimeError('Checked independent verifier required')
proof=[];minimum=None
for index,((q,bins,oldn,oldd),c) in enumerate(unique.items(),1):
 n,d=upward_grid_count([arrays[j] for j in q],F(str(reg['capacity'])),bins)
 if str(n)!=oldn or str(d)!=oldd or 100*n<99*d:raise RuntimeError('Independent original integer recount differs')
 value=F(n,d);minimum=value if minimum is None else min(minimum,value);proof.append(dict(selection=list(q),bins=bins,numerator=str(n),denominator=str(d)))
 if index%50==0 or index==len(unique):
  progress=dict(done=index,required=len(unique),seconds=time.monotonic()-started);(J/'RAW_AUDIT_PROGRESS.json').write_text(json.dumps(progress));print(json.dumps(progress),flush=True)
with (J/'RAW_CERTIFICATE_RECOUNTS.json.gz').open('xb') as f:f.write(gzip.compress(json.dumps(proof).encode(),compresslevel=6))
pairrows=[r for r in (h['robust_pairs'] or {}).get('records',[]) if r['kind']=='joint_pair_neighborhood'];blockrows=[r for r in (h['robust_blocks'] or {}).get('records',[]) if r['kind']=='robust_block_mitm']
result=dict(passed=True,scope='single ACTUAL fresh cold engineering all-source/input/read/budget/pool-lineage and every semantic raw certificate independently recounted; no original-LSS MC/qualification orAvg',source_sha256=source,result_sha256=sha(file),search_seconds=meta['elapsed'],extension_seconds=ext['extension_seconds'],phase_within_budget=True,cdf_seconds=h['cdf_seconds'],pair_seconds=h['pair_seconds'],block_seconds=h['block_seconds'],precision_seconds=pc['closure_seconds'],base_pool=ext['base_pool'],cdf_pool=len(cdf),pair_pool=len(pairs),final_pool=len(pool),unique_semantic_raw_certificates_recounted=len(proof),minimum_independent_raw_lower=float(minimum),raw_recounts_file=(J/'RAW_CERTIFICATE_RECOUNTS.json.gz').relative_to(H).as_posix(),raw_recounts_sha256=sha(J/'RAW_CERTIFICATE_RECOUNTS.json.gz'),complete_pair_scans=sum(r['complete_pair_scan'] for r in pairrows),partial_pair_scans=sum(not r['complete_pair_scan'] for r in pairrows),pair_group_combinations=sum(r['pairs_checked'] for r in pairrows),complete_block_scans=sum(r['complete_block_scan'] for r in blockrows),partial_block_scans=sum(not r['complete_block_scan'] for r in blockrows),new_original_MC_calls=0,all_original_inputs_verified=True,all_own_stage_members_retained=True,independent_verifier_sha256=math['source_sha256'],seconds=time.monotonic()-started)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}),flush=True)
