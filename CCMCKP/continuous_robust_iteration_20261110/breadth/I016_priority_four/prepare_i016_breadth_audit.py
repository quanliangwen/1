"""Reuse the pinned, preflighted lineage branch without editing the live auditor."""
from pathlib import Path
import json,hashlib,ast
H=Path(__file__).resolve().parent;parent=H/'audit_i016_pair_stability39.py';out=H/'audit_i016_priority_breadth.py';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();s=parent.read_text(encoding='utf8');expected=json.load(open(H/'stability/I016_pair_cover_case39/POSTPROCESS_REGISTRATION.json'))['drivers']['audit_i016_pair_stability39.py']
if sha(parent)!=expected:raise RuntimeError('Live paired auditor changed')
if out.exists():raise RuntimeError('No prepared breadth auditor overwrite')
pool=s[s.index('def pool_check(rows):'):s.index('for label,seed in sorted(expected):')]
old="unique[(tuple(q),c['bins'],c['lower_numerator'],c['denominator'])]=c"
if pool.count(old)!=1:raise RuntimeError('Unexpected semantic-key structure')
pool=pool.replace(old,"unique[(current_instance,current_capacity,tuple(q),c['bins'],c['lower_numerator'],c['denominator'])]=c")
lineage=s[s.index(" ext=data['extension'];"):s.index(' pools.append(')]
prefix='''"""All8actual breadth searches, all own-stage raw certificates with instance/T namespace."""
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
'''
outer='''for label,index,seed in sorted(expected):
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
'''
append=" pools.append(dict(label=label,index=index,seed=seed,instance=current_instance,capacity=current_capacity,result_file=file.relative_to(H).as_posix(),result_sha256=sha(file),source_sha256=source,search_seconds=meta['elapsed'],phase_seconds=ext['extension_seconds'],raw_candidates=len(pool),cdf_candidates=len(cdf),pair_candidates=len(pair_set) if label=='I016_pair_cover' else None,all_stage_members_retained=True,all_original_inputs_verified=True,opened_paths_verified=True))\n"
suffix='''proof=[];minimum=None
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
'''
value=prefix+pool+outer+lineage+append+suffix;ast.parse(value);out.write_text(value,encoding='utf8');print(json.dumps(dict(file=out.name,source_sha256=sha(out),pinned_parent_auditor_sha256=expected,lineage_branch_reused_unchanged=True,change='outer4case namespaces plus integer key includes instance/capacity; original mathematical and lineage guards unchanged',scope='implementation only; actual8-search audit not yet run')))
