from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;D=H/'formal/F002_I016_40x30';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def make():
 reg=json.load(open(D/'REGISTRATION.json'));m=json.load(open(D/'SOURCE_MANIFEST.json'));v=json.load(open(H/'REMOTE_VERIFICATION.json'));prefix='CCMCKP/continuous_robust_iteration_20261110/formal/F002_I016_40x30/';files={r['path']:r for r in v['files']}
 if not v['root_inventory_manifest_verified'] or files.get(prefix+'REGISTRATION.json',{}).get('sha256')!=sha(D/'REGISTRATION.json') or files.get(prefix+m['file'],{}).get('sha256')!=m['sha256']:raise RuntimeError('Actual independently verified remote formal protocol/source required')
 contents={r['path']:r['sha256'] for r in m['files']}
 for n,d in reg['driver_sha256'].items():
  if sha(H/n)!=d or contents.get(n)!=d:raise RuntimeError('Formal scheduling source differs')
 row=dict(commit=v['commit'],registration_sha256=sha(D/'REGISTRATION.json'),source_zip_sha256=m['sha256'],independent_remote_verification=True,remote_files=v['verified_files'],scope='actual complete remote F002 source/registration before any1200search launch; no run outcomes yet')
 with (D/'PRE_REG_REMOTE_VERIFIED.json').open('x') as f:json.dump(row,f,indent=2)
 print(json.dumps(row))
if __name__=='__main__':make()
