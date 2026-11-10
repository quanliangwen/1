from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;D=H/'formal/F002_I016_40x30';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();v=json.load(open(H/'REMOTE_VERIFICATION.json'));m=json.load(open(D/'RAW_AUDIT_SOURCE_MANIFEST.json'));prefix='CCMCKP/continuous_robust_iteration_20261110/formal/F002_I016_40x30/';files={r['path']:r for r in v['files']}
if not v['root_inventory_manifest_verified'] or files.get(prefix+'RAW_POSTPROCESS_REGISTRATION.json',{}).get('sha256')!=sha(D/'RAW_POSTPROCESS_REGISTRATION.json') or files.get(prefix+m['file'],{}).get('sha256')!=m['sha256']:raise RuntimeError('Actual independently remote-verified raw auditor source required')
r=dict(commit=v['commit'],registration_sha256=sha(D/'RAW_POSTPROCESS_REGISTRATION.json'),source_zip_sha256=m['sha256'],independent_remote_verification=True,remote_files=v['verified_files'],scope='actual remote raw audit protocol/source verification BEFORE waiting postprocessor launch; does not mean1200audit ran')
with (D/'RAW_POSTPROCESS_REMOTE_VERIFIED.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
