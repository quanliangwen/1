"""Exercise exact final-auditor functions/postselection statements on real pilots.

No synthetic outcomes, no final-cohort guards changed, no MC calls or new Avg.
Legacy terminal wall is read from its original 'wall' field, outside reused code.
"""
from pathlib import Path
from fractions import Fraction as F
import ast,json,gzip,hashlib,pickle,math,time,traceback
from independent_raw_recount import verify
H=Path(__file__).parent;D=H/'research/final_audit_preflight';D.mkdir(parents=True,exist_ok=True);out=D/'PREFLIGHT_REAL_DEVELOPMENT.json';attempt=D/'ATTEMPT01_FAILURE.json'
if out.exists() or attempt.exists():raise RuntimeError('Preflight attempt exists; preserve it before a new registered attempt')
script=H/'audit_f001_final.py';text=script.read_text();tree=ast.parse(text);lines=text.splitlines();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
try:
 env=dict(Path=Path,F=F,json=json,gzip=gzip,hashlib=hashlib,pickle=pickle,math=math,verify=verify,H=H,cases={r['index']:r for r in json.load(open(H/'CASES.json'))},rawref=json.load(open(H/'RAW_REFERENCE.json')),reference=json.load(open(H/'REFERENCE_SHA256.json')),distref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'],models={},input_identities={},native={},dist_checked=set(),used=set(),new_flags=[],recounts={},details=[],protocol_errors=[],logical_total=0.,reg=dict(search_seconds=600))
 defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sha','check_choice','checked_native']]
 model_loop=next(n for n in tree.body if isinstance(n,ast.For) and lines[n.lineno-1].startswith('for i,c in cases.items()'))
 loop=next(n for n in tree.body if isinstance(n,ast.For) and lines[n.lineno-1].startswith('for name,(i,seed)'))
 first=next(k for k,n in enumerate(loop.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='tested' for t in n.targets));tail=loop.body[first:]
 setup=compile(ast.fix_missing_locations(ast.Module(body=defs+[model_loop],type_ignores=[])),str(script),'exec');code=compile(ast.fix_missing_locations(ast.Module(body=tail,type_ignores=[])),str(script),'exec');exec(setup,env)
 source={p.name:sha(p) for p in (H/'iterations/I002_cdf_neighborhood/candidate').glob('*.py')}
 for r in env['reference']['files']:
  if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original LSS source changed')
 cohorts=[('I002_pilot',H/'iterations/I002_cdf_neighborhood/pilot',H/'iterations/I002_cdf_neighborhood/pilot_validation'),('I002_stability39',H/'stability/I002_case39/search',H/'stability/I002_case39/validation'),('I002_stability40',H/'stability/I002_case40/search',H/'stability/I002_case40/validation')]
 checked=[]
 for label,S,V in cohorts:
  posts=sorted(V.glob('*.post.json'))
  expected=14 if label=='I002_pilot' else 6
  if len(posts)!=expected:raise RuntimeError('Actual complete development cohort missing '+label)
  for postpath in posts:
   name=postpath.name[:-len('.post.json')];file=S/name;post=json.load(open(postpath));t=json.load(open(str(file)+'.terminal.json'));meta=json.load(open(str(file)+'.run.json'));data=json.loads(gzip.decompress(file.read_bytes()));i=t['index'];seed=t['seed'];c=env['cases'][i];pool=data['candidate_shortlist']
   if t['exit']!=0 or meta['source_sha256']!=source or meta['input_sha256']!=env['input_identities'][c['instance']] or meta['seed']!=seed or data['seed']!=seed or data['instance']!=c['instance'] or F(str(data['capacity']))!=F(str(c['tmax'])):raise RuntimeError('Development run/source/input identity mismatch')
   if post['index']!=i or post.get('search_seed',seed)!=seed or t['method']!=post['method']:raise RuntimeError('Development post identity mismatch')
   if pool!=sorted(pool,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in pool})!=len(pool):raise RuntimeError('Development source pool ordering differs')
   for candidate in pool:env['check_choice'](c,candidate)
   for opened in meta['opened_task_paths']:
    if opened.endswith('_dist.txt') or '/lss_cache/' in opened or opened.endswith('/BASELINE_S10.json'):raise RuntimeError('Search used validation/history')
   if meta['within_budget']!=(meta['elapsed']<=600):raise RuntimeError('Budget flag mismatch')
   row=dict(index=i,instance=c['instance'],tmax=c['tmax'],seed=seed,method=t['method'],search_exit=t['exit'],joint_accepted=False,protocol_valid=False,search_seconds=meta['elapsed'],search_wall_seconds=t.get('wall_seconds',t.get('wall')),within_budget=meta['within_budget'],raw_pool=len(pool),search_result_sha256=sha(file))
   env.update(c=c,i=i,seed=seed,file=file,post=post,pool=pool,t=t,row=row);exec(code,env)
   if not env['details'][-1]['protocol_valid']:raise RuntimeError('Existing qualified real development run failed shared final audit')
   checked.append(dict(cohort=label,method=t['method'],index=i,seed=seed,search_sha256=sha(file),post_sha256=sha(postpath),native_tested=len(post['tested'])))
 result=dict(passed=True,scope='exact selected final-auditor functions and postselection statements executed against26already completed real development runs; not formal1200audit or new MC/Avg/Std',final_auditor_sha256=sha(script),preflight_sha256=sha(Path(__file__)),reused_postselection_AST_sha256=hashlib.sha256(ast.dump(ast.Module(body=tail,type_ignores=[]),include_attributes=False).encode()).hexdigest(),real_runs=len(checked),all_qualified_and_source_input_cost_prefix_native_identity_verified=True,unique_selected_raw_certificates_independently_recounted=len(env['recounts']),unique_original_LSS_receipts_checked=len(env['native']),logical_native_records_checked=sum(x['native_tested'] for x in checked),new_MC_calls=0,formal_guards_unchanged=True,untested=['formal1200attempt namespace and full-cohort aggregation','formal448JSON68log physical-call accounting','final Excel calculation/render/export','formal1200native results notyet available'],runs=checked,details=env['details'],independent_raw_recounts=list(env['recounts'].values()),seconds=time.monotonic()-start)
 with out.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ['runs','details','independent_raw_recounts']}))
except Exception as ex:
 with attempt.open('x') as f:json.dump(dict(passed=False,error=str(ex),traceback=traceback.format_exc(),final_auditor_sha256=sha(script),seconds=time.monotonic()-start),f,indent=2)
 raise
