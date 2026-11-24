from pathlib import Path
import ast,base64,hashlib,io,json,zipfile
R=Path(__file__).resolve().parent;OLD=Path('E:/codex/S10_EGS_large_pilot_20261123')
S=Path('E:/codex/S10_EGS_LSS_fix_20261124/source')
controller=(OLD/'controller.py').read_text()
controller=controller.replace("'tasks':270","'tasks':P['total_runs']").replace("'total':270","'total':P['total_runs']")
controller=controller.replace("binary=H/'bin'/('baseline' if arm['name']=='S10_MITM' else 'candidate')", "binary=H/'bin/ccmckp_s10'")
controller=controller.replace("str(H/'candidate/BENCHMARK_MANIFEST.json')", "str(H/'source/BENCHMARK_MANIFEST.json')")
controller=controller.replace("if arm['name']!='S10_MITM':cmd+=['--search-flow','ellipsoid_oa','--ellipsoid-gamma',str(arm['gamma']),'--ellipsoid-slice','5']", "cmd+=['--search-flow',arm['flow']]\n                if arm['gamma'] is not None:cmd+=['--ellipsoid-gamma',str(arm['gamma']),'--ellipsoid-slice','5']")
controller=controller.replace('last_state=0\ntry:', 'last_state=0\nmax_active=0\ntry:')
controller=controller.replace("active[identity]=item", "active[identity]=item\n                max_active=max(max_active,len(active))")
controller=controller.replace("'active_identities':list(active)", "'max_active_observed':max_active,'active_identities':list(active)")
controller=controller.replace("'all_source_and_input_pins_unchanged':True", "'max_active_observed':max_active,'elapsed_seconds':time.monotonic()-started,'all_source_and_input_pins_unchanged':True")
controller=controller.replace("if available>=needed and free>P['minimum_free_disk_bytes']:", "if available>=needed and total_rss+reserve+P['worker_reserve_bytes']<=P['total_own_rss_limit_bytes'] and free>P['minimum_free_disk_bytes']:")
ast.parse(controller,feature_version=(3,8));(R/'controller.py').write_text(controller,encoding='utf-8')
cases=[c for c in json.loads((S/'CASES.json').read_text()) if c['index'] in [19,35,39]]
manifest=json.loads((S/'BENCHMARK_MANIFEST.json').read_text());inputs={}
for c in cases:
 for name,digest in manifest[c['instance']].items():
  if name in ['cost.txt','node_to_factor.pkl'] or name.endswith('_sample.txt') and not name.endswith('_big_sample.txt'):
   inputs['benchmark/'+c['instance']+'/'+name]=digest
pins={'source/'+p.relative_to(S).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in S.rglob('*') if p.is_file()}
pins.update({'bin/ccmckp_s10':'ae4a5d663a5efdd8bf99f1d78c48c5606e75538cbb07ec513ccb09778854b574','controller.py':hashlib.sha256(controller.encode()).hexdigest()})
P={'schema':'S10_EGS_LSS_fixed_3large_60workers_v1','source_commit':'c4ab9a3fa10b9e34a11088844280320c78ab92c0','cases':cases,
 'arms':[{'name':'S10_LSS_FIXED','flow':'frontier_mitm','gamma':None},{'name':'EGS_LSS_FIXED_2p4','flow':'ellipsoid_oa','gamma':2.4}],
 'repetitions':30,'total_runs':180,'seeds':list(range(960001,960031)),
 'acceptance':'last LSS probability >= 0.99 for main output and all variants, matched to final trace; no additional probability acceptance gate',
 'probability_threshold':.99,'sampling_index_range':[0,499],'real_probability_calculation':False,
 'raw_empirical_certificate':'unchanged internal search mechanism only, not an additional final statistical acceptance gate',
 'search_budget_seconds':600,'search_common_reserve_seconds':45,'LSS_outside_search_budget':True,
 'primary_runtime':'controller-observed process wall time excluding dispatch queue, includes startup/load/search/LSS/output, approx 0.3-second observation granularity',
 'secondary_runtime':'worker metadata elapsed search seconds under the original search-clock definition',
 'official_avg_std_requires_30_valid':True,'std_ddof':1,'best_is_observed_valid_minimum_not_global_optimum':True,
 'paired_cost_tests':'3 same-seed two-sided mean sign-flip tests, Holm3; complete30 per arm required',
 'sign_flip_patterns':99999,'sign_flip_seed':20261124,'validity_tests':'paired exact McNemar, separate Holm3 family',
 'time_comparisons':'descriptive means and sample standard deviations; no post-hoc timing gate',
 'numeric_tie_abs':1e-8,'max_workers':60,'available_headroom_bytes':5*1024**3,'worker_reserve_bytes':1024**3,
 'reserve_basis':'previous batch measured peak 0.6433GiB; 1GiB admission reserve per worker; no distribution-generator reporting in corrected binary',
 'single_rss_limit_bytes':6*1024**3,'total_own_rss_limit_bytes':90*1024**3,'emergency_available_bytes':2*1024**3,
 'minimum_free_disk_bytes':4*1024**3,'process_wall_watchdog_seconds':1200,
 'independent_starts':True,'no_historical_or_cross_run_solutions':True,'no_retry_or_seed_selection':True,
 'no_algorithm_or_protocol_changes_during_run':True,'automatic_full40_expansion':False,
 'source_and_binary_pins':pins,'input_pins':inputs,
 'preflight_available_GiB':113.95192337036133,'preflight_CPU_affinity_count':256,
 'dispatch_order':'rep blocks; cases19/35/39; rotate two arm order by rep+case index; same physical CPU workload',
 'environment':'same Gurobi11.0.3 binary for both arms, Threads=1 per solver; no historical result pooling'}
(R/'PROTOCOL.json').write_text(json.dumps(P,indent=2),encoding='utf-8')
b=io.BytesIO()
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
 for p in S.rglob('*'):
  if p.is_file():z.writestr('source/'+p.relative_to(S).as_posix(),p.read_bytes())
 z.writestr('PROTOCOL.json',(R/'PROTOCOL.json').read_bytes());z.writestr('controller.py',controller)
payload=b.getvalue()
remote='''from pathlib import Path
import base64,hashlib,io,json,shutil,zipfile
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_lss_3large_60w_20261124'
assert Path.cwd().resolve()==B.resolve() and not H.exists()
data=base64.b64decode(PAYLOAD);assert hashlib.sha256(data).hexdigest()==EXPECTED
H.mkdir()
with zipfile.ZipFile(io.BytesIO(data)) as z:
 for name in z.namelist():
  p=(H/name).resolve();assert H.resolve() in p.parents
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
for folder in ['bin','logs','outcomes','runs']:(H/folder).mkdir()
shutil.copy2(B/'work/egs_lss_fix_20261124/build/ccmckp_s10',H/'bin/ccmckp_s10')
P=json.loads((H/'PROTOCOL.json').read_text())
for name,digest in P['source_and_binary_pins'].items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==digest,name
for name,digest in P['input_pins'].items():assert hashlib.sha256((B/name).read_bytes()).hexdigest()==digest,name
print(json.dumps({'status':'READY','total':P['total_runs'],'max_workers':P['max_workers'],'input_pins':len(P['input_pins']),'protocol_sha256':hashlib.sha256((H/'PROTOCOL.json').read_bytes()).hexdigest()}))
'''.replace('PAYLOAD',repr(base64.b64encode(payload).decode())).replace('EXPECTED',repr(hashlib.sha256(payload).hexdigest()))
(R/'deploy_remote.py').write_text(remote,encoding='utf-8')
for name in ['launch_remote.py','monitor_remote.py']:
 code=(OLD/name).read_text().replace('egs_large_pilot_20261123','egs_lss_3large_60w_20261124')
 (R/name).write_text(code,encoding='utf-8')
print(json.dumps({'cases':cases,'total':180,'workers':60,'protocol_sha256':hashlib.sha256((R/'PROTOCOL.json').read_bytes()).hexdigest()}))
