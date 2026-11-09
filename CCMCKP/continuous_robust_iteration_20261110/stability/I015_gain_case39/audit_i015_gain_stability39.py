"""All six actual matched searches: namespaces, budgets, reads and raw recounts."""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,pickle,time
from independent_raw_recount import upward_grid_count
H=Path(__file__).resolve().parent;S=H/'stability/I015_gain_case39';out=S/'INDEPENDENT_SEARCH_RAW_AUDIT.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No complete six-search audit overwrite')
if not (S/'SEARCH_FINISHED').exists():raise RuntimeError('All six real search attempts must finish first')
reg=json.load(open(S/'REGISTRATION.json'));finished=json.load(open(S/'SEARCH_RESULT.json'));expected={(label,seed) for label in reg['sources'] for seed in reg['seeds']}
if finished['errors'] or len(finished['rows'])!=6 or {(r['label'],r['seed']) for r in finished['rows']}!=expected:raise RuntimeError('All six successful protocol-valid attempts required; no success-subset averages')
math=json.load(open(H/'INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json'))
if not math['passed'] or math['source_sha256']!=sha(H/'independent_raw_recount.py'):raise RuntimeError('Checked independent raw verifier required')
P=Path(reg['benchmark']);ref=json.load(open(H/'RAW_REFERENCE.json'));arrays={}
for name,digest in reg['input_sha256'].items():
 if sha(P/name)!=digest or ref[str(P/name)]!=digest:raise RuntimeError('Original raw input changed')
 if name.endswith('_sample.txt'):arrays[int(name.split('_')[0])]=[F(x) for x in (P/name).read_text().split()]
costs=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;unique={};pools=[];started=time.monotonic()
for label,seed in sorted(expected):
 info=reg['sources'][label];root=H/info['candidate'];vendor=(root.parent/'vendor313').resolve();source={p.name:sha(p) for p in root.glob('*.py')};file=S/'search'/(label+'_seed'+str(seed)+'.json.gz');meta=json.load(open(str(file)+'.run.json'));data=json.loads(gzip.decompress(file.read_bytes()));terminal=json.load(open(S/'search'/(label+'_seed'+str(seed)+'.terminal.json')))
 if source!=info['source_sha256'] or meta['source_sha256']!=source or meta['seed']!=seed or data['seed']!=seed or data['instance']!=reg['instance'] or data['capacity']!=reg['capacity'] or data['status']!='completed' or meta['risk_method']!=info['method'] or meta['budget']!=600 or not meta['within_budget'] or meta['elapsed']>600 or terminal['exit']!=0 or terminal['error'] or meta['input_sha256']!=reg['input_sha256'] or data['extension']['extension_seconds']>180:raise RuntimeError('Frozen source/seed/input/method/global/phase budget or ordinary attempt failed')
 config=data['config']
 if config['raw_threshold']!='.99' or config['external_real_P_threshold']!=.985 or config['external_MC_seed']!=832273 or config['external_MC_draws']!=10000000 or config['tail_hard_gate'] or not config['all_original_samples']:raise RuntimeError('Original raw/native acceptance protocol changed')
 own={str(file),str(file)+'.tmp',str(file)+'.run.json',str(file)+'.run.json.tmp',str(file.parent)}
 for opened in meta['opened_task_paths']:
  path=Path(opened)
  if path.name.endswith('_dist.txt') or '/lss_cache/' in opened or path.name=='BASELINE_S10.json':raise RuntimeError('True/history/cache data entered optimizer')
  if P in path.parents and path.name not in reg['input_sha256']:raise RuntimeError('Unregistered benchmark input read')
  if H.parent in path.parents and not (root in path.parents or path==root or vendor in path.parents or path==vendor or opened in own):raise RuntimeError('Other task or saved-solution input entered optimizer')
 pool=data['candidate_shortlist']
 if pool!=sorted(pool,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in pool})!=len(pool) or data['raw_certified_pool_count']!=len(pool):raise RuntimeError('Frozen own pool is not complete unique cost order')
 for row in pool:
  q=row['selection'];c=row['certificate']
  if len(q)!=len(groups) or any(j not in groups[g] for g,j in enumerate(q)) or c['selection']!=q or c['method']!='exact_integer_upward_grid_count' or not c['all_original_samples'] or c['strict_event']!='sum<T' or not c['accepted'] or 100*int(c['lower_numerator'])<99*int(c['denominator']) or abs(row['cost']-float(sum((costs[j] for j in q),F(0))))>1e-9:raise RuntimeError('Invalid canonical raw-certified member/cost')
  key=(tuple(q),c['bins'],c['lower_numerator'],c['denominator']);unique[key]=c
 if label=='I015_hybrid':
  ext=data['extension'];hybrid=ext['hybrid'];cdf=hybrid['cdf_pool_records'];precision=ext['precision_closure'];final={tuple(r['selection']) for r in pool}
  if not {tuple(r['selection']) for r in cdf}<=final or not hybrid['all_own_cdf_retained'] or not precision['all_initial_retained'] or not precision['phase_within_budget'] or precision['budget_overrun']:raise RuntimeError('Own-stage retention or precision budget failed')
 pools.append(dict(label=label,seed=seed,result_file=file.relative_to(H).as_posix(),result_sha256=sha(file),raw_candidates=len(pool),search_seconds=meta['elapsed'],phase_seconds=data['extension']['extension_seconds'],source_sha256=source,all_original_inputs_verified=True,opened_paths_verified=True))
proof=[];minimum=None
for index,((q,bins,old_n,old_d),c) in enumerate(unique.items(),1):
 n,den=upward_grid_count([arrays[j] for j in q],F(str(reg['capacity'])),bins)
 if str(n)!=old_n or str(den)!=old_d or 100*n<99*den:raise RuntimeError('Independent integer raw recount differs')
 value=F(n,den);minimum=value if minimum is None else min(minimum,value);proof.append(dict(selection=list(q),bins=bins,numerator=str(n),denominator=str(den)))
 if index%50==0 or index==len(unique):
  (S/'RAW_AUDIT_PROGRESS.json').write_text(json.dumps(dict(done=index,required=len(unique),seconds=time.monotonic()-started)));print(json.dumps(dict(recounted=index,required=len(unique),seconds=time.monotonic()-started)),flush=True)
proof_file=S/'RAW_CERTIFICATE_RECOUNTS.json.gz'
with proof_file.open('xb') as f:f.write(gzip.compress(json.dumps(proof).encode(),compresslevel=6))
result=dict(passed=True,scope='all6actual matched-seed frozen searches namespace/source/input/budget/read-guard/pool provenance and all unique semantic raw99 certificates independently recounted; no original-LSS qualification or3/30-run Avg yet',pools=pools,required_searches=6,unique_raw_certificates=len(proof),minimum_independent_raw_lower=float(minimum),raw_recounts_file=proof_file.relative_to(H).as_posix(),raw_recounts_sha256=sha(proof_file),independent_verifier_sha256=math['source_sha256'],new_original_MC_calls=0,seconds=time.monotonic()-started,registration_sha256=sha(S/'REGISTRATION.json'))
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='pools'}),flush=True)
