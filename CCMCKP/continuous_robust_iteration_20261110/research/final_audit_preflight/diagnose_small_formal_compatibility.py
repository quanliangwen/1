"""Independent exact small-case recount and original-cache compatibility only."""
from pathlib import Path
from fractions import Fraction as F
import ast,json,gzip,hashlib,pickle,math,time
from independent_raw_recount import verify
H=Path(__file__).parent;D=H/'research/final_audit_preflight';D.mkdir(parents=True,exist_ok=True);out=D/'SMALL_FORMAL_COMPATIBILITY.json'
if out.exists():raise RuntimeError('No diagnostic overwrite')
script=H/'audit_f001_final.py';text=script.read_text();tree=ast.parse(text);lines=text.splitlines();start=time.monotonic();cases={c['index']:c for c in json.load(open(H/'CASES.json'))};small={i:c for i,c in cases.items() if int(c['instance'].split('_')[1])<=5};source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'iterations/I002_cdf_neighborhood/candidate').glob('*.py')};base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};before={r['key']:r for r in json.load(open(H/'formal/F001_I002_40x30/CACHE_BEFORE_VALIDATION.json'))['files']}
env=dict(H=H,Path=Path,F=F,json=json,hashlib=hashlib,pickle=pickle,math=math,cases=small,models={},input_identities={},rawref=json.load(open(H/'RAW_REFERENCE.json')),reference=json.load(open(H/'REFERENCE_SHA256.json')),distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'],native={},dist_checked=set(),used=set())
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sha','check_choice','checked_native']];models=next(n for n in tree.body if isinstance(n,ast.For) and lines[n.lineno-1].startswith('for i,c in cases.items()'));exec(compile(ast.fix_missing_locations(ast.Module(body=defs+[models],type_ignores=[])),str(script),'exec'),env)
sha=env['sha'];rows=[]
for r in env['reference']['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original LSS source drift')
for i,c in sorted(small.items()):
 file=H/'formal/F001_I002_40x30/search'/f'cdf_lns_{i:02d}_seed9707001.json.gz';meta=json.load(open(str(file)+'.run.json'));terminal=json.load(open(str(file)+'.terminal.json'));data=json.loads(gzip.decompress(file.read_bytes()))
 if terminal['exit']!=0 or data['status']!='completed' or meta['source_sha256']!=source or meta['input_sha256']!=env['input_identities'][c['instance']] or data['seed']!=9707001 or meta['seed']!=9707001 or data['instance']!=c['instance'] or data['capacity']!=c['tmax'] or not meta['within_budget']:raise RuntimeError('Formal frozen search identity mismatch')
 pool=data['candidate_shortlist']
 if pool!=sorted(pool,key=lambda r:(r['cost'],r['selection'])):raise RuntimeError('Pool cost order mismatch')
 for candidate in pool:env['check_choice'](c,candidate)
 tested=[];selected=None;pending=False
 for candidate in pool:
  identity=dict(instance=c['instance'],capacity=float(c['tmax']),selection=candidate['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
  if key not in before:pending=True;break
  if sha(H/'lss_cache'/(key+'.json'))!=before[key]['sha256']:raise RuntimeError('Historical native receipt overwritten')
  checked,v=env['checked_native'](c,candidate);tested.append(dict(key=key,passed=v['passed'],point=v['real_probability']))
  if v['passed']:selected=(candidate,key,v);break
 row=dict(index=i,instance=c['instance'],capacity=c['tmax'],search_seed=9707001,original_best=base[i]['old_best'],cached_prefix_resolved=selected is not None and not pending,read_only_known_calls=len(tested),search_sha256=sha(file),tested=tested)
 if selected is not None:
  candidate,key,v=selected;recount=verify(env['models'][c['instance']][0],candidate['selection'],c['tmax'],candidate['certificate']);row.update(known_joint_cost=candidate['cost'],selection=candidate['selection'],LSS_point=v['real_probability'],raw_exact_probability=recount['lower'],raw_recount=recount,LSS_key=key,cost_minus_old_best=candidate['cost']-base[i]['old_best'])
 rows.append(row)
result=dict(integrity_passed=True,scope='one frozen actual formal seed on each of16small cases, exact decimal rational empirical recount and pre-existing original LSS receipts only; NO official F001 postselection records, new MC,30-run Avg or Std',cases=16,all16_cached_prefix_resolved=all(r['cached_prefix_resolved'] for r in rows),first3_APP_oldBest_compatible=all(abs(next(r for r in rows if r['index']==i)['cost_minus_old_best'])<1e-6 for i in [21,22,23]),source_sha256=source,final_auditor_sha256=sha(script),independent_raw_verifier_sha256=sha(H/'independent_raw_recount.py'),diagnostic_sha256=sha(Path(__file__)),new_MC_calls=0,optimizer_feedback=False,rows=rows,seconds=time.monotonic()-start)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['rows','source_sha256']}));print(json.dumps([{k:r[k] for k in ['index','known_joint_cost','original_best','raw_exact_probability','LSS_point']} for r in rows if r['index'] in [21,22,23]]))
