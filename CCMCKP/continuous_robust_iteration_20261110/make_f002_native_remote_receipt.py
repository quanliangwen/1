from pathlib import Path
import json
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;D=H/'research/F002_I016_formal_native'
def make():
 m=json.load(open(D/'SOURCE_MANIFEST.json'));v=json.load(open(H/'REMOTE_VERIFICATION.json'));prefix='CCMCKP/continuous_robust_iteration_20261110/research/F002_I016_formal_native/';files={r['path']:r for r in v['files']}
 if not v['root_inventory_manifest_verified'] or files.get(prefix+'REGISTRATION.json',{}).get('sha256')!=sha(D/'REGISTRATION.json') or files.get(prefix+m['file'],{}).get('sha256')!=m['sha256']:raise RuntimeError('Actual independent remote native protocol/registration verification required')
 r=dict(commit=v['commit'],registration_sha256=sha(D/'REGISTRATION.json'),source_zip_sha256=m['sha256'],independent_remote_verification=True,remote_files=v['verified_files'],scope='actual verified remote whole1200attempt native stage protocol BEFORE any F002 original native MC launch')
 with (D/'PRE_REG_REMOTE_VERIFIED.json').open('x') as f:json.dump(r,f,indent=2)
 print(json.dumps(r))
if __name__=='__main__':make()
