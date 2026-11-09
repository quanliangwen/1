from pathlib import Path
import json,hashlib,time
H=Path(__file__).parent;I=H/'iterations/I012_iterated_block_mitm';J=I/'engineering40';audit=json.load(open(J/'INDEPENDENT_RAW_AUDIT.json'));assessment=json.load(open(J/'ASSESSMENT.json'));meta=json.load(open(J/'result.json.gz.run.json'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if not audit['passed'] or not assessment['passed'] or audit['result_sha256']!=sha(J/'result.json.gz'):raise RuntimeError('Independent raw audit required')
reg=dict(time=time.time(),scope='post-search registration for already frozen single engineering run; not a pre-search performance registration',source_sha256=meta['source_sha256'],frozen_search_sha256=sha(J/'result.json.gz'),raw_audit_sha256=sha(J/'INDEPENDENT_RAW_AUDIT.json'),instance='APP_50_10_500_',capacity=100.0,index=40,seed=9712000,wait_for=['formal/F001_I002_40x30/validation/FINISHED','iterations/I004_robust_pair_exchange/pilot_validation/FINISHED'],cost_order='unchanged frozen complete pool; stop first original-LSS pass',LSS_seed=832273,LSS_draws=10000000,LSS_event='sum<=T',LSS_threshold=.985,driver_sha256={n:sha(H/n) for n in ['validate_i012_engineering.py','native_lss_eval.py','reference_loader.py']},no_search_feedback=True,no_30run_claim=True)
with (J/'NATIVE_REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
print(json.dumps({k:v for k,v in reg.items() if k not in ['source_sha256','driver_sha256']}))
