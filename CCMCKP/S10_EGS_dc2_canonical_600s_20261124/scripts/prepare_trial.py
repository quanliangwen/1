from pathlib import Path
import hashlib,json,base64,ast
R=Path(__file__).resolve().parent;OLD=Path('E:/codex/S10_EGS_costfront_600s_20261124')
controller=(OLD/'controller.py').read_bytes();(R/'controller.py').write_bytes(controller)
v=json.loads((R/'VALIDATION.json').read_text());assert v['status']=='PASS'
P=json.loads((OLD/'PROTOCOL.json').read_text())
P.update({'schema':'S10_EGS_DC2_canonical_LSS_total600_v1','source_commit':'new frozen source; parent40ccef5f7898d074de61c174e3b84e225786871a',
 'arms':[{'name':'S10_TOTAL600','flow':'frontier_mitm','gamma':None},{'name':'EGS_DC2_TOTAL600','flow':'ellipsoid_dominance','gamma':2.4}],
 'ellipsoid_candidate_domain':'no hard risk cap; native SOC min mu+x+2.4t under improving cost bound, exact empirical FOSD proof cuts',
 'native_infeasibility_cut':'requires complete original integer CDF upper*100<denominator*99; never from Monte Carlo or undecided status',
 'dominance_definition':'every sorted original decimal sample >= reference, exact rational comparisons within each group',
 'proof_distribution':'independent uniform original empirical marginals, no population confidence guarantee',
 'same_run_initialization':True,'parent_clock_guard_reuse':'exact same controller bytes and unchanged full-pipeline deadline/evaluator functions; old tests retained by source equality',
 'previous_trial_protocol_sha256':'59bac59e7c550a05a29fe985e1ab1f5e916b4d6a61a9ea45b580fd32b12b443d', 'canonical_SOC_witness':'exact binary rational coefficients; outward rounded t; no change in x projection', 'historical_failure_cause':'unknown; no old failures rerun',
 'adaptive_iteration_disclosure':'DC2 corrects canonical witness after paused DC record audit; within-trial Holm3 plus cumulative Holm9 across CF, paused DC and DC2; incomplete groups not tested, no generalization claim',
 'cumulative_cost_tests_family':9,'no_further_unregistered_full40_expansion':True,
 'preflight_available_GiB':None})
P['source_and_binary_pins']={'source/'+p.relative_to(R/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'source').rglob('*') if p.is_file()}
assert v['source_sha256']=={k[7:]:h for k,h in P['source_and_binary_pins'].items()}
P['source_and_binary_pins'].update({'bin/ccmckp_s10':v['binary_sha256'],'controller.py':hashlib.sha256(controller).hexdigest(),
 'DESIGN_AND_DIAGNOSIS.txt':hashlib.sha256((R/'DESIGN_AND_DIAGNOSIS.txt').read_bytes()).hexdigest()})
(R/'PROTOCOL.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf-8')
payload={n:base64.b64encode((R/n).read_bytes()).decode() for n in ['controller.py','PROTOCOL.json','DESIGN_AND_DIAGNOSIS.txt']}
code='''from pathlib import Path
import json,base64,hashlib,shutil,os
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_dc2_canonical_600s_20261124'
assert Path.cwd()==B and not (H/'LAUNCH.json').exists()
for n,b in PAYLOAD.items():assert not (H/n).exists(),n
for n,b in PAYLOAD.items():(H/n).write_bytes(base64.b64decode(b))
for n in ['bin','logs','runs','outcomes']:(H/n).mkdir()
shutil.copy2(H/'build/ccmckp_s10',H/'bin/ccmckp_s10')
P=json.loads((H/'PROTOCOL.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in P['source_and_binary_pins'].items():assert sha(H/n)==h,n
for n,h in P['input_pins'].items():assert sha(B/n)==h,n
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:args=(p/'cmdline').read_bytes().split(b'\\0')
 except OSError:continue
 if any(str(B).encode() in a for a in args):active.append({'pid':p.name,'cmd':[a.decode(errors='replace') for a in args if a]})
assert not active,active
mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines()}
receipt={'status':'FROZEN_READY','protocol_sha256':sha(H/'PROTOCOL.json'),'available_GiB':mem['MemAvailable']/2**30,
 'disk_free_bytes':shutil.disk_usage(B).free,'CPU_affinity_count':len(os.sched_getaffinity(0)),
 'input_pins':len(P['input_pins']),'max_workers':60,'total':180,'strict_total_budget':600,'watchdog':595}
(H/'FRESH_PREFLIGHT.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
'''.replace('PAYLOAD',repr(payload))
(R/'freeze_remote.py').write_text(code,encoding='utf-8')
for n in ['launch_remote.py','monitor_remote.py','watch.py','early_record_check_remote.py','collect_remote.py','collect.py']:
 t=(OLD/n).read_text().replace('egs_costfront_600s_20261124','egs_dc2_canonical_600s_20261124');(R/n).write_text(t,encoding='utf-8')
print('PROTOCOL_READY',hashlib.sha256((R/'PROTOCOL.json').read_bytes()).hexdigest())
