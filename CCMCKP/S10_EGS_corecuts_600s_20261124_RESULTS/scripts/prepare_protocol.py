from pathlib import Path
import hashlib,json,base64,ast
R=Path(__file__).resolve().parent;OLD=Path('E:/codex/S10_EGS_momentbound_600s_20261124')
v=json.loads((R/'VALIDATION.json').read_text());assert v['status']=='PASS'
pins={'source/'+p.relative_to(R/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'source').rglob('*') if p.is_file()}
assert {k[7:]:h for k,h in pins.items()}==v['source_sha256']
P=json.loads((OLD/'PROTOCOL.json').read_text())
P.update({'schema':'S10_EGS_corecuts_LSS_total600_v1','source_commit':'new frozen source; MB parent0f7d62f0e9183ab774842c7ce0fe45dc27b8b471',
 'arms':[{'name':'S10_TOTAL600','flow':'frontier_mitm','gamma':None},{'name':'EGS_CORE_TOTAL600','flow':'ellipsoid_corecuts','gamma':2.4}],
 'previous_trial_protocol_sha256':'1b7d1ed21ce84744325e50a8f3fe5696b3fd9631103d55a376ed7d245c239ecd',
 'single_new_mechanism':'deterministic deletion-filtered empirical quantile-envelope infeasible core cuts; retain MB hierarchy and necessary moment row',
 'core_proof':'complete downward integer-grid upper of independently coupled original empirical marginal quantile lower envelopes; upper*100<denominator*99',
 'core_extraction':{'order':'ascending group index single pass','bins':1024,'per_proof_cooperative_seconds':2,'total_run_cooperative_seconds':40,'partial_or_timeout':'keep last complete certified core; otherwise full FOSD fallback','not_minimum_cardinality':True},
 'corecut_reference':'Forbes et al EJOR2024 312:840-854 section3 local monotonic cuts and Algorithm2; independent CCMCKP adaptation proof',
 'ellipsoid_candidate_domain':'same MB cost-primary then ellipsoid-risk-secondary model, outward necessary mean row, only replace complete FOSD infeasibility cuts by proved subset cores when possible',
 'adaptive_iteration_disclosure':'CORE designed after all MB180 valid, all3 avg worse and no90 candidate main-search improvements; within-trial Holm3 plus cumulative exploratory Holm18 including reserved incomplete paused DC tests at p1; no confirmatory generalization',
 'cumulative_cost_tests_family':18,'preflight_available_GiB':None})
pins.update({'bin/ccmckp_s10':v['binary_sha256'],'controller.py':hashlib.sha256((R/'controller.py').read_bytes()).hexdigest(),'DESIGN_AND_DIAGNOSIS.txt':hashlib.sha256((R/'DESIGN_AND_DIAGNOSIS.txt').read_bytes()).hexdigest()})
P['source_and_binary_pins']=pins
(R/'PROTOCOL.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf-8')
payload={n:base64.b64encode((R/n).read_bytes()).decode() for n in ['controller.py','PROTOCOL.json','DESIGN_AND_DIAGNOSIS.txt']}
old=(OLD/'freeze_remote.py').read_text();a=old.index('for n,b in ')
code="from pathlib import Path\nimport json,base64,hashlib,shutil,os\nB=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_corecuts_600s_20261124'\nassert Path.cwd()==B and not (H/'LAUNCH.json').exists()\n"+old[a:]
# Freeze template contains the old concrete base64 dictionary twice; replace it as a whole.
start=code.index('for n,b in ');end=code.index('.items()',start)
old_payload_literal=code[start+len('for n,b in '):end]
ast.literal_eval(old_payload_literal)
code=code.replace(old_payload_literal,repr(payload)).replace('egs_momentbound_600s_20261124','egs_corecuts_600s_20261124')
ast.parse(code,feature_version=(3,8));(R/'freeze_remote.py').write_text(code,encoding='utf-8')
for n in ['launch_health_remote.py']:
 p=R/n;p.write_text(p.read_text().replace('ellipsoid_momentbound','ellipsoid_corecuts'))
print('FREEZE_READY',hashlib.sha256((R/'PROTOCOL.json').read_bytes()).hexdigest())
