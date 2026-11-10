from pathlib import Path
import json
import isolated_original_lss as module
from formal_native_catalogue import build
H=Path(__file__).resolve().parent;D=H/'research/F002_native_catalogue_preflight';D.mkdir(exist_ok=True);out=D/'ACTUAL_READONLY_CHECK.json'
if out.exists():raise RuntimeError('No actual formal catalogue preflight overwrite')
calls=[];old=module.subprocess.run
def forbidden(*a,**kw):calls.append(True);raise RuntimeError('Native subprocess forbidden in preflight')
module.subprocess.run=forbidden
try:cat,outcomes,r=build(H,D/'never_native_receipts')
finally:module.subprocess.run=old
if calls or len(cat)!=len(outcomes) or not r['passed'] or r['prior89_physical_receipts_checked']!=89:raise RuntimeError('Actual completed formal catalogue helper failed')
r.update(preflight_only_not_actual_formal_catalogue=True,whole1200search_complete_claimed=False,forbidden_subprocess_calls=len(calls),new_native_files=len(list((D/'never_native_receipts').iterdir())))
with out.open('x') as f:json.dump(r,f,indent=2)
print(json.dumps({k:v for k,v in r.items() if k not in ['base_check','input_sha256','added_aliases']}))
