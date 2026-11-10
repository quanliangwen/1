from pathlib import Path
import json,hashlib,shutil,zipfile,time,os
H=Path(__file__).resolve().parent;D=H/'iterations/S10_LSS_mainflow_APP3_confirmation';original=Path('/home/quanliangwen/work/cdf_lss_S10_20261109/frozen_candidate');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=json.load(open(H/'BASELINE_S10.json'))
if (D/'REGISTRATION.json').exists():raise RuntimeError('S10 confirmation already prepared')
expected=base['source_sha256']
if {p.name:sha(p) for p in original.glob('*.py')}!=expected or len(expected)!=12:raise RuntimeError('Original frozen S10 search identity differs from baseline')
D.mkdir(parents=True,exist_ok=True);S=D/'S10_source';S.mkdir(exist_ok=True)
for p in original.glob('*.py'):shutil.copy2(p,S/p.name)
vendor=D/'vendor313'
if not vendor.exists():os.symlink('/home/quanliangwen/work/cdf_lss_S10_20261109/vendor313',vendor,target_is_directory=True)
drivers=['s10_lss_bridge.py','run_s10_lss_confirmation.py','prepare_s10_lss_confirmation.py'];reg=dict(time=time.time(),scope='user requested original S10 search unchanged, remove external real-probability hard filter; run APP_3_5_30 T21/T27 each once via original LSS output0/1/2/main CSV flow',S10_source_sha256=expected,S10_original_frozen_directory=str(original),benchmark='/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_3_5_30_',capacities=[21,27],search_seed=9821001,search_seconds=600,watchdog_seconds=640,driver_sha256={n:sha(H/n) for n in drivers},original_LSS_sources_sha256=json.load(open(H/'REFERENCE_SHA256.json'))['files'],final_feasibility='original LSS advanced_exact_evaluation CL=.99; no external real_P_test rejection',output='original Local_Search_DD output tail plus unmodified original param_test and CSV writers',real_probability='original real_P_test10m/seed832273 recorded only',S10_internal_candidate_generation='original source byte-identical, including own raw99 search and small-case branch; raw debug legacy985metadata inactive, old validate_portfolio postselector not invoked',previous_I017_algorithm_not_used=True,new_runs_per_capacity=1,no_full40_or30run_claim=True)
with (D/'REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
files=[D/'REGISTRATION.json']+list(S.glob('*.py'))+[H/n for n in drivers]+[H/'reference_loader.py',H/'REFERENCE_SHA256.json',H/'RAW_REFERENCE.json']+[H/'reference'/r['path'] for r in reg['original_LSS_sources_sha256']]
out=D/'S10_LSS_MAINFLOW_SOURCE.zip'
with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(H).as_posix())
with zipfile.ZipFile(out) as z:assert z.testzip() is None
m=dict(file=out.name,bytes=out.stat().st_size,sha256=sha(out),zip_CRC_passed=True,S10_12_search_files_byte_identical=True,files=[dict(path=p.relative_to(H).as_posix(),sha256=sha(p)) for p in files])
with (D/'SOURCE_MANIFEST.json').open('x') as f:json.dump(m,f,indent=2)
T=H/'artifact'/D.relative_to(H);T.mkdir(parents=True,exist_ok=True)
for p in [out,D/'REGISTRATION.json',D/'SOURCE_MANIFEST.json']:shutil.copy2(p,T/p.name)
for n in drivers:shutil.copy2(H/n,H/'artifact'/n)
print(json.dumps({k:v for k,v in m.items() if k!='files'}))
