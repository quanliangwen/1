from pathlib import Path
import argparse,json,zipfile,shutil
from isolated_original_lss import sha
from register_completed_pool_prefix import PROFILES
H=Path(__file__).resolve().parent
def pack(profile):
 cfg=PROFILES[profile];D=H/cfg['study'];reg=json.load(open(D/'REGISTRATION.json'));out=D/'FROZEN_COMPLETE_PREFIX_SOURCE.zip';manifest=D/'SOURCE_MANIFEST.json'
 if out.exists() or manifest.exists():raise RuntimeError('No cohort native source freeze overwrite')
 check=json.load(open(D/'CATALOGUE_CHECK.json'))
 if not check['passed'] or check['new_MC_calls']!=0 or check['checked_unique']!=reg['catalogue_unique'] or check['source_sha256']!=sha(H/'frozen_native_catalogue.py') or not check['actual_cohort_fully_audited_before_capture']:raise RuntimeError('Actual matching post-freeze completed catalogue checks required')
 number='005' if profile=='P016' else '006';files=[D/'REGISTRATION.json',D/'FORMAL_ISOLATION_BEFORE.json']+[H/n for n in reg['source_sha256']]+[H/n for n in reg['input_sha256']]
 files.extend(H/n for n in ['register_completed_pool_prefix.py','pack_completed_pool_registration.py','launch_completed_pool_prefix.py','make_completed_prefix_remote_receipt.py','postprocess_completed_pool_prefix.py','launch_completed_prefix_postprocess.py','summarize_completed_prefix.py','audit_d'+number+'_prefix.py','snapshot_d'+number+'_isolation.py','independent_raw_recount.py','INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json'])
 files.extend(H/r['path'] for r in json.load(open(D/'CATALOGUE.json')).values());files.extend(H/r['alias']['path'] for r in check['aliases']);files.extend(H/'reference'/r['path'] for r in json.load(open(H/'REFERENCE_SHA256.json'))['files']);files=sorted(set(files))
 for n,digest in {**reg['source_sha256'],**reg['input_sha256']}.items():
  if sha(H/n)!=digest:raise RuntimeError('Registered study input/source changed')
 with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.relative_to(H).as_posix())
 with zipfile.ZipFile(out) as z:
  if z.testzip() is not None:raise RuntimeError('Frozen cohort native source CRC failed')
 m=dict(file=out.name,bytes=out.stat().st_size,sha256=sha(out),zip_CRC_passed=True,scope='pre-native '+reg['scope']+'; actual frozen searches/all-raw proof/read-only completed catalogue and all original reference sources; no new private native calls yet',files=[dict(path=p.relative_to(H).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files])
 with manifest.open('x') as f:json.dump(m,f,indent=2)
 T=H/'artifact'/cfg['study'];T.mkdir(parents=True,exist_ok=True)
 for p in [out,manifest]+list(D.glob('*.json')):shutil.copy2(p,T/p.name)
 print(json.dumps({k:v for k,v in m.items() if k!='files'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort',choices=sorted(PROFILES),required=True);pack(p.parse_args().cohort)
