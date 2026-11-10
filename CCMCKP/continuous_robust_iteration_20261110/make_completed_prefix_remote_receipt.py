from pathlib import Path
import argparse,json
from isolated_original_lss import sha
from register_completed_pool_prefix import PROFILES
H=Path(__file__).resolve().parent
def make(profile):
 cfg=PROFILES[profile];D=H/cfg['study'];reg=json.load(open(D/'REGISTRATION.json'));m=json.load(open(D/'SOURCE_MANIFEST.json'));v=json.load(open(H/'REMOTE_VERIFICATION.json'));prefix='CCMCKP/continuous_robust_iteration_20261110/'+cfg['study']+'/';files={r['path']:r for r in v['files']}
 if not v['root_inventory_manifest_verified'] or files.get(prefix+'REGISTRATION.json',{}).get('sha256')!=sha(D/'REGISTRATION.json') or files.get(prefix+'FROZEN_COMPLETE_PREFIX_SOURCE.zip',{}).get('sha256')!=m['sha256']:raise RuntimeError('Actual independent remote native-source/registration verification required')
 bundled={r['path']:r['sha256'] for r in m['files']}
 for n,digest in reg['source_sha256'].items():
  if sha(H/n)!=digest or bundled.get(n)!=digest:raise RuntimeError('Registered native source differs from verified remote bundle')
 result=dict(commit=v['commit'],registration_sha256=sha(D/'REGISTRATION.json'),source_zip_sha256=m['sha256'],independent_remote_verification=True,verified_remote_files=v['verified_files'],scope='actual remote '+profile+' complete-prefix protocol/source/input verification BEFORE any private MC launch')
 with (D/'PRE_REG_REMOTE_VERIFIED.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort',choices=sorted(PROFILES),required=True);make(p.parse_args().cohort)
