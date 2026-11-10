"""Actual read-only cache branch; forbid launching simulation subprocesses."""
from pathlib import Path
import json
import isolated_original_lss as native_module
from frozen_native_catalogue import build_completed_catalogue
H=Path(__file__).resolve().parent;D=H/'research/native_catalogue_builder_preflight';D.mkdir(exist_ok=True);out=D/'ACTUAL_READONLY_CHECK.json'
if out.exists():raise RuntimeError('No actual catalogue preflight overwrite')
calls=[];old=native_module.subprocess.run
def forbidden(*args,**kwargs):
 calls.append(True);raise RuntimeError('Simulation subprocess forbidden in catalogue builder preflight')
native_module.subprocess.run=forbidden
try:catalogue,outcomes,result=build_completed_catalogue(H,D/'never_native_receipts')
finally:native_module.subprocess.run=old
if calls or len(outcomes)!=len(catalogue) or not result['passed']:raise AssertionError('Read-only catalogue branch failed')
result.update(scope=result['scope']+'; READONLY builder preflight BEFORE new study search completion, NOT D005/D006 actual registered catalogue',forbidden_subprocess_calls=len(calls),actual_new_private_native_files=len(list((D/'never_native_receipts').iterdir())),actual_study_registration_made=False,complete_new_search_audit_claimed=False)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['aliases','input_sha256']}))
