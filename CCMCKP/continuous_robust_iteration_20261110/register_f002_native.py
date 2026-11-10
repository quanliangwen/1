"""Register original-LSS prefixes only after ALL1200 search/raw attempts freeze.

All registered search attempts remain in the ledger. Failed searches have no
invented pool; incomplete30-run qualification is reported rather than averaged
over a successful subset. No MC is performed by this registration program.
"""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,pickle,time,os
from isolated_original_lss import sha,identity_key
from isolated_prefix_engine import ordered,describe
from formal_native_catalogue import build
H=Path(__file__).resolve().parent;S=H/'formal/F002_I016_40x30';D=H/'research/F002_I016_formal_native'

def register():
 needed=['SEARCH_FINISHED','INDEPENDENT_SEARCH_RAW_AUDIT.json','RAW_POSTPROCESS_TERMINAL.json']
 if not all((S/n).exists() for n in needed):
  print(json.dumps(dict(ready=False,reason='whole actual1200 search/raw audit not yet terminal',new_MC_calls=0,formal_native_registered=False)));return
 if (D/'REGISTRATION.json').exists():raise RuntimeError('Formal native stage already registered; inspect actual state')
 a=json.load(open(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'));reg=json.load(open(S/'REGISTRATION.json'));post=json.load(open(S/'RAW_POSTPROCESS_TERMINAL.json'));pre=json.load(open(H/'research/F002_native_catalogue_preflight/ACTUAL_READONLY_CHECK.json'));engine=json.load(open(H/'research/D004_I016_full_prefix/PREFIX_ENGINE_CHECK.json'))
 if not a['integrity_passed'] or a['registered_attempts']!=1200 or len(a['pools'])!=1200 or a['registration_sha256']!=sha(S/'REGISTRATION.json') or sha(H/a['raw_recounts_file'])!=a['raw_recounts_sha256'] or post['audit_exit']!=0:raise RuntimeError('Complete original source/raw integrity audit required; preserve failures')
 if not pre['passed'] or pre['source_sha256']!=sha(H/'formal_native_catalogue.py') or pre['forbidden_subprocess_calls'] or pre['new_native_files'] or not engine['passed'] or engine['source_sha256']!=sha(H/'isolated_prefix_engine.py'):raise RuntimeError('Matching actual read-only catalogue and generic prefix-engine preflight required')
 direct=json.load(open(H/'research/F002_native_audit_preflight/ACTUAL_COMPLETED_FIXTURE_CHECK.json'));control=json.load(open(H/'research/F002_native_audit_preflight/CONTROL_FLOW_IDENTITY.json'))
 if not direct['passed'] or direct['source_sha256']!=sha(H/'f002_native_direct_audit.py') or direct['new_MC_calls'] or not control['passed'] or control['source_sha256']!=sha(H/'run_f002_native.py') or control['new_MC_calls']:raise RuntimeError('Matching completed14pool direct audit and unchanged controller decision-flow proof required')
 expected={(i,seed) for i in reg['cases'] for seed in reg['seeds']}
 if len(expected)!=1200 or {(r['index'],r['seed']) for r in a['pools']}!=expected:raise RuntimeError('Do not omit/replace registered attempts')
 if sha(H/'CASES.json')!=reg['casebook_sha256'] or {p.name:sha(p) for p in (H/reg['candidate']).glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Frozen optimizer/case book changed')
 for n,d in {**reg['driver_sha256'],**reg['vendor_sha256']}.items():
  if sha(H/n)!=d:raise RuntimeError('Frozen search driver/dependency changed')
 for n,d in reg['raw_input_sha256'].items():
  if sha(Path(n))!=d:raise RuntimeError('Original empirical input changed')
 proof=json.loads(gzip.decompress((H/a['raw_recounts_file']).read_bytes()));recounted={(r['instance'],F(str(r['capacity'])),tuple(r['selection']),r['method'],r['bins'],r['original_lower_numerator'],r['original_upper_numerator'],r['denominator']) for r in proof};cases={c['index']:c for c in json.load(open(H/'CASES.json'))};models={};attempts={};pools={};inputfiles=[]
 for info in sorted(a['pools'],key=lambda r:(r['index'],r['seed'])):
  i,seed=info['index'],info['seed'];c=cases[i];name=f'cdf_pair_cover_{i:02d}_seed{seed}';file=S/'search'/(name+'.json.gz');terminal=Path(str(file)+'.terminal.json');term=json.load(open(terminal));attempts[name]=dict(info,native_pool=False)
  if term['index']!=i or term['seed']!=seed or term['registration_sha256']!=sha(S/'REGISTRATION.json') or info['result_file']!=file.relative_to(H).as_posix():raise RuntimeError('Frozen terminal identity differs')
  inputfiles.append(terminal)
  if info['exit']!=0 or info['error'] is not None or 'result_sha256' not in info:
   attempts[name]['native_exclusion']='original unsuccessful/incomplete search, retained in1200ledger';continue
  meta_file=Path(str(file)+'.run.json');data=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(meta_file))
  if sha(file)!=info['result_sha256'] or sha(meta_file)!=info['meta_sha256'] or data['seed']!=seed or meta['seed']!=seed or data['instance']!=c['instance'] or F(str(data['capacity']))!=F(str(c['tmax'])) or meta['source_sha256']!=reg['source_sha256']:raise RuntimeError('Audited formal pool identity changed')
  inputfiles.extend([file,meta_file]);P=Path(reg['benchmark'])/c['instance']
  if c['instance'] not in models:
   cost=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;models[c['instance']]=(cost,groups)
  cost,groups=models[c['instance']];rows=[]
  for r in data['candidate_shortlist']:
   q=r['selection'];cert=r['certificate'];key=(data['instance'],F(str(data['capacity'])),tuple(q),cert['method'],cert.get('bins'),cert['lower_numerator'],cert.get('upper_numerator'),cert['denominator'])
   if key not in recounted or len(q)!=len(groups) or len(set(q))!=len(q) or any(j not in groups[g] for g,j in enumerate(q)) or cert['selection']!=q or not cert['all_original_samples'] or cert['strict_event']!='sum<T' or 100*int(cert['lower_numerator'])<99*int(cert['denominator']) or abs(r['cost']-float(sum((cost[j] for j in q),F(0))))>1e-9:raise RuntimeError('Not a canonical independently recounted original99 pool member')
   identity=dict(instance=data['instance'],capacity=float(data['capacity']),selection=q,seed=832273,draws=10000000,event='sum<=T');rows.append(dict(key=identity_key(identity),selection=q,cost=r['cost'],identity=identity))
  if rows!=ordered(rows) or len(rows)!=info['raw_candidates'] or len(rows)!=data['raw_certified_pool_count']:raise RuntimeError('Complete cost-ordered raw pool changed')
  if not rows:
   attempts[name]['native_exclusion']='original empty raw-feasible pool retained';continue
  pools[name]=rows;attempts[name].update(native_pool=True,members=len(rows),search_seconds=meta['elapsed'],result_sha256=sha(file),meta_sha256=sha(meta_file))
 mem={l.split(':')[0]:int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')};resources=dict(time=time.time(),cpus=len(os.sched_getaffinity(0)),available_memory_kib=mem['MemAvailable'])
 if resources['cpus']<4 or resources['available_memory_kib']<16*1024*1024:raise RuntimeError('Insufficient four native-worker resources')
 D.mkdir(exist_ok=True);cat,outcomes,check=build(H,D/'receipts')
 if check['base_check']['capture_started']<max((S/'SEARCH_FINISHED').stat().st_mtime,(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json').stat().st_mtime):raise RuntimeError('Actual formal catalogue must be captured after ALLsearch/raw freeze')
 for name,rows in pools.items():attempts[name]['initial_prefix']=describe(rows,outcomes)
 inputs=['CASES.json','RAW_REFERENCE.json','REFERENCE_SHA256.json','LSS_DATA_REFERENCE.json','research/F002_native_catalogue_preflight/ACTUAL_READONLY_CHECK.json','research/D004_I016_full_prefix/PREFIX_ENGINE_CHECK.json']+list(check['input_sha256'])
 inputs.extend(['research/F002_native_audit_preflight/ACTUAL_COMPLETED_FIXTURE_CHECK.json','research/F002_native_audit_preflight/CONTROL_FLOW_IDENTITY.json'])
 inputs.extend((S/n).relative_to(H).as_posix() for n in ['REGISTRATION.json','SEARCH_FINISHED','search/DISPATCH_RESULTS.json','INDEPENDENT_SEARCH_RAW_AUDIT.json','RAW_CERTIFICATE_RECOUNTS.json.gz','RAW_POSTPROCESS_TERMINAL.json']);inputs.extend(p.relative_to(H).as_posix() for p in inputfiles);inputs.extend((H/reg['candidate']/n).relative_to(H).as_posix() for n in reg['source_sha256']);inputs.extend(reg['vendor_sha256'])
 with (D/'CATALOGUE.json').open('x') as f:json.dump(cat,f,indent=2)
 check.update(actual_all1200_search_and_raw_audit_frozen=True,formal_raw_audit_sha256=sha(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'),catalogue_sha256=sha(D/'CATALOGUE.json'))
 with (D/'CATALOGUE_CHECK.json').open('x') as f:json.dump(check,f,indent=2)
 with (D/'ALL1200_ATTEMPTS.json').open('x') as f:json.dump(attempts,f,indent=2)
 inputs.extend((D/n).relative_to(H).as_posix() for n in ['CATALOGUE.json','CATALOGUE_CHECK.json','ALL1200_ATTEMPTS.json']);drivers=['register_f002_native.py','run_f002_native.py','isolated_prefix_engine.py','isolated_original_lss.py','native_lss_eval.py','reference_loader.py','formal_native_catalogue.py','frozen_native_catalogue.py']
 r=dict(time=time.time(),scope='formal F00240x30 original-LSS complete frozen cost prefixes; all1200 attempts retained and no successful-subset Avg',formal_registration_sha256=sha(S/'REGISTRATION.json'),search_attempts=1200,raw_protocol_valid=a['protocol_valid'],pools={name:attempts[name] for name in pools},excluded_attempts={name:info for name,info in attempts.items() if not info['native_pool']},workers=4,watchdog_per_call=2400,source_sha256={n:sha(H/n) for n in drivers},input_sha256={n:sha(H/n) for n in sorted(set(inputs))},resources=resources,catalogue_unique=len(cat),cache_policy='original completed records verified by source21/env/data/identity; deterministic aliases; all new MC/logs private; optimizer no feedback',point_threshold=.985,draws=10000000,seed=832273,event='sum<=T',failure_policy='retain all1200search errors and native errors, no automatic retries; incomplete30qualification has missing Avg/Std',no_optimizer_feedback=True,registration_timing='AFTERALL1200search and independent whole raw audit, BEFOREnewF002native MC; actual source remote verification required next')
 with (D/'REGISTRATION.json').open('x') as f:json.dump(r,f,indent=2)
 print(json.dumps(dict(ready=True,registration_sha256=sha(D/'REGISTRATION.json'),original_attempts=1200,native_pools=len(pools),excluded_attempts=len(r['excluded_attempts']),catalogue_unique=len(cat),unknown_unique=len({k for v in pools.values() for k in describe(v,outcomes)['missing_keys']}),new_MC_calls=0)))

if __name__=='__main__':register()
