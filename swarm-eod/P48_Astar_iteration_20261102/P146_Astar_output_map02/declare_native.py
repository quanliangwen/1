from pathlib import Path
import hashlib
import importlib.util
import json

F=Path(__file__).resolve().parent
H=F.parent
R=Path('/home/junhao/quan/parallel_test_solver/match')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
assert not(F/'PREDECLARATION.json').exists()
entry=read(F/'ENTRY_ACTUAL_ZIP_FIRST.json')
evidence=read(F/'SMALL_TEST_EVIDENCE.json')
z=read(F/'INTERNAL_ZIP_BINDING.json')
protocol=read(F/'TEST_PROTOCOL.json')
assert entry['status']=='PASS_SERVER_RESEARCH_ENTRY_NOT_OFFICIAL_RELEASE'
assert entry['team_number']==615 and entry['five_native_constructors_independent']and entry['gurobi_blocked']
assert len(entry['real_sdk_setter_and_audit_passthrough'])==5
assert evidence['status']=='PASS_ASTARA_FINAL_OUTPUT_MECHANISM'and all(evidence['checks'].values())
assert entry['actual_zip_sha256']==z['sha256']==sha(z['zip'])
assert z['integer615']and z['actual_req_unchanged']and z['audit_sha256']==z['audit_historical_sha256']
q=read(F/'WORKSPACE_READY.json')['versions']['P145Zip']
assert entry['sources']==q['sources']
assert all(sha(Path(q['workspace'])/n)==h for n,h in q['sources'].items())
assert all(sha(Path(q['workspace'])/n)==h for n,h in q['sdk_files'].items())
old=read(H/'P41_environment_restore_20261101/P35_continuation_after_parent_repair/PREDECLARATION.json')
d={k:old[k]for k in ['sdk_commit','sdk_files','blue_binding','blue_binding_sha256','resource_gate','frozen_files']}
d['frozen_files']=dict(d['frozen_files'])
d.update(phase=F.name,selection=['P145'],maps=['Map02'],seed=None,history_delta=False,max_native_rounds=2,min_native_rounds=2,
         versions={'P145':dict(original_zip=z['zip'],original_zip_sha256=z['sha256'],source=z['source'],source_files=z['payload_files'])},
         schedule=[dict(version='P145',cohort='A',label='sdk_e2f022b_ASTAR_P145_FINAL_OUTPUT_MAP02_FIRST')],
         small_test_gate=dict(minimum_map=protocol['minimum_map'],minimum_wall=protocol['minimum_wall'],minimum_full=protocol['minimum_full'],time100=True,all10=True,both_no_wallhit=True,actual_active_completion=True),
         hypothesis='One historical final-output rule on frozen A-star base. Only different-source free-supported unmeasured bearing pixels removed; all parent and raw pixels protected.',
         qualification_scope='Actual new A-star 779-frame output mechanism +1.9881pp, all five credits unchanged, known authored damage preserved; new actual ZIP real ABI/615/SDK 5 independent constructors and real setter/audit passthrough. No added dependencies or safety-repair claim.',
         scientific_limits=['One unseeded Map02 RED+sameBLUE with original clocks/threads/resources, no five/control rerun.',
                            'No causal comparison to historical natural-random scores. No true official grid read by policy.',
                            'Optional output cooperative .5s budget with old wall guard; no hard realtime guarantee.',
                            'First real native failure kept, no retry/label/seed/threshold rescue. First Windows opaque raw review before own RED logs/public images.',
                            'No NPZ/pickle loading or BLUE private console/state. No automatic five/promotion/contest release.'],
         automatic_five=False,ranking_promoted=False,performance_comparison=False,
         authorization='User ACTIVE P48 A-star evidence-first autonomous rule refinement, one independent rule after mechanism support.')
for name in ['run_offline.py','declare_native.py','TEST_PROTOCOL.json','ENTRY_ACTUAL_ZIP_FIRST.json','INTERNAL_ZIP_BINDING.json','INTERNAL_ZIP_BINDING_LOCAL_FIRST.json','SMALL_TEST_EVIDENCE.json','check_sdk_actual_zip_entry.py']:
    d['frozen_files'][str(F/name)]=sha(F/name)
original=H/'P41_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py'
d['frozen_files'][str(original)]=sha(original)
(F/'versions/P145/QUALIFICATION.json').write_text(json.dumps(dict(status='PASS',payload_files_sha256=z['payload_files'],zip_sha256=z['sha256'],integer615=True,actual_entry=entry['status'],official_submission_ready=False),indent=2)+'\n')
(F/'PREDECLARATION.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('frozen_scientific_preflight',original)
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
b.F=F
b.D=d
b.BLUE=d['blue_binding']
b.WBLUE=Path(b.BLUE['blue_workspace'])
b.validate_frozen()
print(json.dumps(dict(status='FROZEN_P145_SINGLE_NOT_LAUNCHED',max_native_rounds=2,automatic_five=False)))
