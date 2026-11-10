"""All8actual breadth searches, all own-stage raw certificates with instance/T namespace."""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,pickle,time
from independent_raw_recount import upward_grid_count
H=Path(__file__).resolve().parent;S=H/'breadth/I016_priority_four';out=S/'INDEPENDENT_SEARCH_RAW_AUDIT.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No all8breadth audit overwrite')
if not (S/'SEARCH_FINISHED').exists():raise RuntimeError('All8actual searches must freeze first')
reg=json.load(open(S/'REGISTRATION.json'));finished=json.load(open(S/'SEARCH_RESULT.json'));casebook={c['index']:c for c in reg['cases']};expected={(label,c['index'],c['seed']) for label in reg['sources'] for c in reg['cases']}
if finished['errors'] or len(finished['rows'])!=8 or {(r['label'],r['index'],r['seed']) for r in finished['rows']}!=expected:raise RuntimeError('All8protocol-valid actual attempts required; no success-subset analysis')
math=json.load(open(H/'INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json'))
if not math['passed'] or math['source_sha256']!=sha(H/'independent_raw_recount.py'):raise RuntimeError('Checked independent raw verifier required')
ref=json.load(open(H/'RAW_REFERENCE.json'));models={};unique={};pools=[];started=time.monotonic()
for case_info in reg['cases']:
 P=Path(case_info['benchmark']);ids={p.name:sha(p) for p in [P/'cost.txt',P/'node_to_factor.pkl']+[p for p in P.glob('*_sample.txt') if not p.name.endswith('_big_sample.txt')]}
 if ids!=case_info['input_sha256'] or any(ref[str(P/n)]!=d for n,d in ids.items()):raise RuntimeError('Complete original case input identity changed')
 if case_info['instance'] not in models:
  arrays={int(n.split('_')[0]):[F(x) for x in (P/n).read_text().split()] for n in ids if n.endswith('_sample.txt')};prices=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;models[case_info['instance']]=dict(arrays=arrays,prices=prices,groups=groups)
def pool_check(rows):
 if rows!=sorted(rows,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in rows})!=len(rows):raise RuntimeError('Pool not complete unique canonical cost order')
 for r in rows:
  q=r['selection'];c=r['certificate']
  if len(q)!=len(groups) or any(j not in groups[g] for g,j in enumerate(q)) or c['selection']!=q or c['method']!='exact_integer_upward_grid_count' or c['strict_event']!='sum<T' or not c['all_original_samples'] or not c['accepted'] or 100*int(c['lower_numerator'])<99*int(c['denominator']) or abs(r['cost']-float(sum((prices[j] for j in q),F(0))))>1e-9:raise RuntimeError('Canonical groups/original strict integer99/cost identity differs')
  unique[(current_instance,current_capacity,tuple(q),c['bins'],c['lower_numerator'],c['denominator'])]=c
 return {tuple(r['selection']) for r in rows}
for label,index,seed in sorted(expected):
 case_info=casebook[index];current_instance=case_info['instance'];current_capacity=case_info['capacity'];P=Path(case_info['benchmark']);model=models[current_instance];prices=model['prices'];groups=model['groups'];info=reg['sources'][label];root=H/info['candidate'];vendor=(root.parent/'vendor313').resolve();source={p.name:sha(p) for p in root.glob('*.py')};file=S/'search'/(label+'_case'+str(index)+'_seed'+str(seed)+'.json.gz');meta=json.load(open(str(file)+'.run.json'));data=json.loads(gzip.decompress(file.read_bytes()));terminal=json.load(open(S/'search'/(label+'_case'+str(index)+'_seed'+str(seed)+'.terminal.json')))
 if source!=info['source_sha256'] or meta['source_sha256']!=source or meta['input_sha256']!=case_info['input_sha256'] or meta['seed']!=seed or data['seed']!=seed or data['instance']!=current_instance or data['capacity']!=current_capacity or data['status']!='completed' or meta['risk_method']!=info['method'] or meta['budget']!=600 or not meta['within_budget'] or meta['elapsed']>600 or terminal['exit']!=0 or terminal['error'] or terminal['index']!=index:raise RuntimeError('Frozen breadth source/input/case/seed/capacity/method/budget/ordinary attempt differs')
 config=data['config']
 if config['raw_threshold']!='.99' or config['external_real_P_threshold']!=.985 or config['external_MC_seed']!=832273 or config['external_MC_draws']!=10000000 or config['tail_hard_gate'] or not config['all_original_samples']:raise RuntimeError('Original acceptance protocol changed')
 own={str(file),str(file)+'.tmp',str(file)+'.run.json',str(file)+'.run.json.tmp',str(file.parent)}
 for opened in meta['opened_task_paths']:
  path=Path(opened)
  if path.name.endswith('_dist.txt') or '/lss_cache/' in opened or path.name=='BASELINE_S10.json':raise RuntimeError('True/history/cache read entered breadth optimizer')
  if P in path.parents and path.name not in case_info['input_sha256']:raise RuntimeError('Unregistered benchmark read')
  if H.parent in path.parents and not (root in path.parents or path==root or vendor in path.parents or path==vendor or opened in own):raise RuntimeError('Other task or saved-solution read entered optimizer')
 ext=data['extension'];pool=data['candidate_shortlist'];pc=ext['precision_closure'];final=pool_check(pool);added={tuple(r['selection']) for r in pc['records'] if r['status']=='raw_certified'};pre=[r for r in pool if tuple(r['selection']) not in added];pre_set={tuple(r['selection']) for r in pre};h=ext['hybrid'] if label=='I015_parent' else ext['pair_cover'];cdf=h['cdf_pool_records'];cdf_set=pool_check(cdf)
 if not h['cdf_executed'] or not h['all_initial_retained'] or not h['all_own_cdf_retained'] or not cdf_set<=pre_set<=final or h['initial_pool']!=ext['base_pool'] or h['cdf_pool']!=len(cdf) or h['final_pool']!=len(pre) or data['raw_certified_pool_count']!=len(pool):raise RuntimeError('Own CDF/final pool origin or retention differs')
 stages=[('robust_cdf_lns',ext['base_pool'],len(cdf))];pair_set=cdf_set
 if label=='I016_pair_cover':
  pair_set=pool_check(h['pair_pool_records'])
  if not h['all_own_pair_retained'] or not cdf_set<=pair_set<=pre_set or h['pair_pool']!=len(pair_set):raise RuntimeError('Own pair stage not retained')
  stages.append(('robust_pairs',len(cdf_set),len(pair_set)))
 stages.append(('robust_blocks',len(pair_set),len(pre)))
 for name,before,after in stages:
  summary=h[name]
  if summary:
   if summary['initial_certified']!=before or summary['final_certified']!=after or summary['initial_certified']+summary['new_certified']!=after:raise RuntimeError('Own stage membership ledger differs '+name)
  elif before!=after:raise RuntimeError('Skipped stage changed pool '+name)
 if ext['extension_seconds']>180 or h.get('phase_seconds_used',0)>180 or pc['phase_seconds_used']>180 or not pc['phase_within_budget'] or pc['budget_overrun'] or pc['shared_deadline']>pc['phase_started']+180 or h['phase_deadline']>pc['phase_started']+180 or pc['initial_pool']!=len(pre) or pc['final_pool']!=len(pool) or not pc['all_initial_retained'] or len(added)!=pc['accepted']:raise RuntimeError('Shared phase/global deadline or precision retention differs')
 if len({tuple(r['selection']) for r in pc['records']})!=len(pc['records']) or pc['new_integer_calls']!=sum(a['kind']=='new_same_run_integer_certificate' for r in pc['records'] for a in r['attempts']):raise RuntimeError('Precision queue/call count differs')
 byq={tuple(r['selection']):r for r in pool}
 for r in pc['records']:
  q=tuple(r['selection']);c=r.get('final_certificate')
  if r['initial_decision'].get('decision')!='unresolved' or q in pre_set:raise RuntimeError('Precision not own missing unresolved queue')
  if c:
   n,u,d=map(int,[c['lower_numerator'],c['upper_numerator'],c['denominator']])
   if c['selection']!=list(q) or c['strict_event']!='sum<T' or not c['all_original_samples'] or not 0<=n<=u<=d or d<=0 or (r['status']=='raw_certified')!=(100*n>=99*d) or (r['status']=='integer_raw_refuted')!=(100*u<99*d):raise RuntimeError('Precision integer classification differs')
  if r['status']=='raw_certified':
   if q not in byq or byq[q]['certificate']!=c:raise RuntimeError('Precision final certificate absent or changed')
  elif q in byq:raise RuntimeError('Uncertified precision point in final pool')
 pools.append(dict(label=label,index=index,seed=seed,instance=current_instance,capacity=current_capacity,result_file=file.relative_to(H).as_posix(),result_sha256=sha(file),source_sha256=source,search_seconds=meta['elapsed'],phase_seconds=ext['extension_seconds'],raw_candidates=len(pool),cdf_candidates=len(cdf),pair_candidates=len(pair_set) if label=='I016_pair_cover' else None,all_stage_members_retained=True,all_original_inputs_verified=True,opened_paths_verified=True))
proof=[];minimum=None
for count,((instance,capacity,q,bins,oldn,oldd),c) in enumerate(unique.items(),1):
 n,d=upward_grid_count([models[instance]['arrays'][j] for j in q],F(str(capacity)),bins)
 if str(n)!=oldn or str(d)!=oldd or 100*n<99*d:raise RuntimeError('Independent original raw recount differs for instance/capacity')
 value=F(n,d);minimum=value if minimum is None else min(minimum,value);proof.append(dict(instance=instance,capacity=capacity,selection=list(q),bins=bins,numerator=str(n),denominator=str(d)))
 if count%50==0 or count==len(unique):
  p=dict(done=count,required=len(unique),seconds=time.monotonic()-started);(S/'RAW_AUDIT_PROGRESS.json').write_text(json.dumps(p));print(json.dumps(p),flush=True)
proof_file=S/'RAW_CERTIFICATE_RECOUNTS.json.gz'
with proof_file.open('xb') as f:f.write(gzip.compress(json.dumps(proof).encode(),compresslevel=6))
result=dict(passed=True,scope=__doc__+'; one paired seed percase; no native qualification/percaseAvg/crosscasecostAvg',pools=pools,required_searches=8,unique_raw_certificates=len(proof),minimum_independent_raw_lower=float(minimum),raw_recounts_file=proof_file.relative_to(H).as_posix(),raw_recounts_sha256=sha(proof_file),independent_verifier_sha256=math['source_sha256'],semantic_key_includes_instance_and_capacity=True,new_original_MC_calls=0,seconds=time.monotonic()-started,registration_sha256=sha(S/'REGISTRATION.json'))
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='pools'}),flush=True)
