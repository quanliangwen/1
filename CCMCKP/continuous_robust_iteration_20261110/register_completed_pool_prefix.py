"""After a WHOLE cohort freezes/audits, register private complete native prefixes."""
from pathlib import Path
from fractions import Fraction as F
import argparse,json,gzip,pickle,time,os
from isolated_original_lss import sha,identity_key
from isolated_prefix_engine import ordered,describe
from frozen_native_catalogue import build_completed_catalogue
H=Path(__file__).resolve().parent
PROFILES={'P016':dict(cohort='stability/I016_pair_cover_case39',study='research/D005_I016_pair_prefix',controller='run_d005_pair_prefix.py',required=6,scope='six frozen3NEWmatched-seed I015/I016case39 DEVELOPMENT cost prefixes; no30formalAvg'), 'B016':dict(cohort='breadth/I016_priority_four',study='research/D006_I016_breadth_prefix',controller='run_d006_breadth_prefix.py',required=8,scope='four frozen cases x2methods,one NEWpairedseed percase, complete native prefixes; no percase/crosscasecostAvg')}
def register(profile):
 cfg=PROFILES[profile];S=H/cfg['cohort'];D=H/cfg['study'];audit_file=S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'
 if not audit_file.exists() or not (S/'SEARCH_FINISHED').exists() or not (S/'POSTPROCESS_TERMINAL.json').exists():
  print(json.dumps(dict(ready=False,cohort=profile,reason='actual whole-cohort independent source/raw audit or search marker missing',new_MC_calls=0)));return
 if (D/'REGISTRATION.json').exists():raise RuntimeError('Native study already registered; inspect actual state')
 a=json.load(open(audit_file));creg=json.load(open(S/'REGISTRATION.json'));post=json.load(open(S/'POSTPROCESS_TERMINAL.json'));finished=json.load(open(S/'SEARCH_RESULT.json'));preflight=json.load(open(H/'research/native_catalogue_builder_preflight/ACTUAL_READONLY_CHECK.json'))
 if not a['passed'] or not post['passed'] or finished['errors'] or a['required_searches']!=cfg['required'] or len(a['pools'])!=cfg['required'] or a['registration_sha256']!=sha(S/'REGISTRATION.json') or sha(H/a['raw_recounts_file'])!=a['raw_recounts_sha256'] or not preflight['passed'] or preflight['source_sha256']!=sha(H/'frozen_native_catalogue.py') or preflight['helper_sha256']!=sha(H/'isolated_original_lss.py') or preflight['forbidden_subprocess_calls']!=0:raise RuntimeError('Actual full cohort/raw proof and matching read-only catalogue preflight required')
 expected={(label,creg['index'],seed) for label in creg['sources'] for seed in creg['seeds']} if profile=='P016' else {(label,c['index'],c['seed']) for label in creg['sources'] for c in creg['cases']}
 observed={(r['label'],r.get('index',creg.get('index')),r['seed']) for r in a['pools']}
 if observed!=expected or len(expected)!=cfg['required'] or {(r['label'],r.get('index',creg.get('index')),r['seed']) for r in finished['rows']}!=expected:raise RuntimeError('Actual unique registered namespaces not complete')
 proof=json.loads(gzip.decompress((H/a['raw_recounts_file']).read_bytes()));recounted=set()
 for r in proof:
  instance=r.get('instance',creg.get('instance'));capacity=r.get('capacity',creg.get('capacity'))
  if instance is None or capacity is None:raise RuntimeError('Multi-case raw proof lacks instance/capacity namespace')
  recounted.add((instance,F(str(capacity)),tuple(r['selection']),r['bins'],r['numerator'],r['denominator']))
 mem={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')};resources=dict(time=time.time(),available_cpus=len(os.sched_getaffinity(0)),available_memory_kib=mem['MemAvailable'])
 if resources['available_cpus']<4 or resources['available_memory_kib']<16*1024*1024:raise RuntimeError('Insufficient four-native-worker resources')
 D.mkdir(exist_ok=True);catalogue,outcomes,ccheck=build_completed_catalogue(H,D/'receipts')
 ccheck.update(actual_cohort_search_finished_mtime=(S/'SEARCH_FINISHED').stat().st_mtime,actual_cohort_raw_audit_sha256=sha(audit_file),actual_cohort_fully_audited_before_capture=True)
 if ccheck['capture_started']<(S/'SEARCH_FINISHED').stat().st_mtime or ccheck['capture_started']<audit_file.stat().st_mtime:raise RuntimeError('Actual catalogue capture must follow complete search/raw audit')
 inputs=['REFERENCE_SHA256.json','LSS_DATA_REFERENCE.json','RAW_REFERENCE.json','research/native_catalogue_builder_preflight/ACTUAL_READONLY_CHECK.json','research/D004_I016_full_prefix/PREFIX_ENGINE_CHECK.json']+list(ccheck['input_sha256'])
 inputs.extend((S/n).relative_to(H).as_posix() for n in ['REGISTRATION.json','SEARCH_RESULT.json','POSTPROCESS_TERMINAL.json','INDEPENDENT_SEARCH_RAW_AUDIT.json','RAW_CERTIFICATE_RECOUNTS.json.gz'])
 engine=json.load(open(H/'research/D004_I016_full_prefix/PREFIX_ENGINE_CHECK.json'))
 if not engine['passed'] or engine['source_sha256']!=sha(H/'isolated_prefix_engine.py'):raise RuntimeError('Previously tested unchanged prefix engine required')
 cases={c['index']:c for c in creg.get('cases',[])};rawref=json.load(open(H/'RAW_REFERENCE.json'));pools={};infos={};loaded={}
 for info in a['pools']:
  label=info['label'];index=info.get('index',creg.get('index'));seed=info['seed'];c=creg if profile=='P016' else cases[index];name=label+('' if profile=='P016' else '_case'+str(index))+'_seed'+str(seed);file=S/'search'/(name+'.json.gz')
  if file.relative_to(H).as_posix()!=info['result_file'] or sha(file)!=info['result_sha256']:raise RuntimeError('Actual frozen result path/hash changed')
  data=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(str(file)+'.run.json'));terminal=S/'search'/(name+'.terminal.json');term=json.load(open(terminal));src=creg['sources'][label];root=H/src['candidate']
  if {p.name:sha(p) for p in root.glob('*.py')}!=src['source_sha256'] or info['source_sha256']!=src['source_sha256'] or meta['source_sha256']!=src['source_sha256'] or data['seed']!=seed or meta['seed']!=seed or data['instance']!=c['instance'] or data['capacity']!=c['capacity'] or data['status']!='completed' or meta['input_sha256']!=c['input_sha256'] or meta['risk_method']!=src['method'] or term['exit']!=0 or term['error'] or not meta['within_budget'] or meta['elapsed']>600 or data['extension']['extension_seconds']>180 or info['search_seconds']!=meta['elapsed']:raise RuntimeError('Frozen actual identity/source/ordinary attempt/phase/total budget differs')
  P=Path(c['benchmark'])
  if str(P) not in loaded:
   for n,digest in c['input_sha256'].items():
    if sha(P/n)!=digest or rawref[str(P/n)]!=digest:raise RuntimeError('Original raw input differs')
   prices=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;loaded[str(P)]=(prices,groups)
  prices,groups=loaded[str(P)];rows=[]
  for row in data['candidate_shortlist']:
   q=row['selection'];cert=row['certificate']
   if len(q)!=len(groups) or len(set(q))!=len(q) or any(j not in groups[g] for g,j in enumerate(q)) or cert['selection']!=q or cert['method']!='exact_integer_upward_grid_count' or cert['strict_event']!='sum<T' or not cert['all_original_samples'] or not cert['accepted'] or 100*int(cert['lower_numerator'])<99*int(cert['denominator']) or abs(row['cost']-float(sum((prices[j] for j in q),F(0))))>1e-9 or (data['instance'],F(str(data['capacity'])),tuple(q),cert['bins'],cert['lower_numerator'],cert['denominator']) not in recounted:raise RuntimeError('Pool not original canonical independently recounted99member')
   identity=dict(instance=data['instance'],capacity=float(data['capacity']),selection=q,seed=832273,draws=10000000,event='sum<=T');rows.append(dict(key=identity_key(identity),selection=q,cost=row['cost'],identity=identity))
  if rows!=ordered(rows) or len(rows)!=info['raw_candidates'] or len(rows)!=data['raw_certified_pool_count']:raise RuntimeError('Frozen full pool order/completeness differs')
  pools[name]=rows;infos[name]=dict(info,index=index,instance=data['instance'],capacity=data['capacity'],members=len(rows),initial_prefix=describe(rows,outcomes));inputs.extend(p.relative_to(H).as_posix() for p in [file,Path(str(file)+'.run.json'),terminal]);inputs.extend(p.relative_to(H).as_posix() for p in root.glob('*.py'))
 with (D/'CATALOGUE.json').open('x') as f:json.dump(catalogue,f,indent=2)
 ccheck['catalogue_sha256']=sha(D/'CATALOGUE.json')
 with (D/'CATALOGUE_CHECK.json').open('x') as f:json.dump(ccheck,f,indent=2)
 drivers=[cfg['controller'],'isolated_prefix_engine.py','isolated_original_lss.py','native_lss_eval.py','reference_loader.py','frozen_native_catalogue.py'];inputs.extend((D/n).relative_to(H).as_posix() for n in ['CATALOGUE.json','CATALOGUE_CHECK.json'])
 reg=dict(time=time.time(),cohort=profile,cohort_directory=cfg['cohort'],pools=infos,workers=4,watchdog_per_call=2400,source_sha256={n:sha(H/n) for n in drivers},input_sha256={n:sha(H/n) for n in sorted(set(inputs))},resources=resources,cache_policy='completed original578+stable shared snapshot, readonly fixed by SHA, earlier deterministic receipt retained on aliases; all new MC/logs private tothisstudy; no shared/formal writes',catalogue_unique=len(catalogue),catalogue_validated_receipts=ccheck['validated_receipts_including_aliases'],scope=cfg['scope'],scheduling='unchanged tested generic whole batches4 global cost/selection/key; each pool min only after all cheaper members rejected; errors remain incomplete, no automatic retry',accounting='each own pool full logical MC time incl reuse, unique new physical/speculative/errors separately; prior physical executions and later duplicate calls remain separately billed',point_threshold=.985,draws=10000000,seed=832273,event='sum<=T',no_optimizer_feedback=True,earlier_registered_queues_unchanged=True,registration_timing='AFTERwholecohort freeze+all-independent-source/raw audit and fresh completed catalogue capture, BEFOREanynewprivateMC')
 with (D/'REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
 print(json.dumps(dict(ready=True,cohort=profile,study=cfg['study'],registration_sha256=sha(D/'REGISTRATION.json'),pools=len(pools),catalogue_unique=len(catalogue),checked_aliases=ccheck['checked_aliases'],initial_unknown_by_pool={k:len(describe(v,outcomes)['missing_keys']) for k,v in pools.items()},initial_union_unknown=len({key for p in pools.values() for key in describe(p,outcomes)['missing_keys']}))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort',choices=sorted(PROFILES),required=True);register(p.parse_args().cohort)
