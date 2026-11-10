"""Actual protocol/source freeze after whole1200 search/raw terminal, before MC."""
from pathlib import Path
import json,zipfile,shutil
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;D=H/'research/F002_I016_formal_native';S=H/'formal/F002_I016_40x30'
def pack():
 reg=json.load(open(D/'REGISTRATION.json'));formal=json.load(open(S/'REGISTRATION.json'));cat=json.load(open(D/'CATALOGUE.json'));check=json.load(open(D/'CATALOGUE_CHECK.json'));out=D/'F002_FROZEN_NATIVE_PROTOCOL.zip';manifest=D/'SOURCE_MANIFEST.json'
 if out.exists() or manifest.exists():raise RuntimeError('No formal native protocol overwrite')
 if not check['actual_all1200_search_and_raw_audit_frozen'] or check['formal_raw_audit_sha256']!=sha(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json') or reg['search_attempts']!=1200:raise RuntimeError('Actual all1200source/raw freeze required before native packet')
 files=[D/n for n in ['REGISTRATION.json','ALL1200_ATTEMPTS.json','CATALOGUE.json','CATALOGUE_CHECK.json','FORMAL_ISOLATION_BEFORE.json']]
 files.extend(S/n for n in ['REGISTRATION.json','SEARCH_FINISHED','INDEPENDENT_SEARCH_RAW_AUDIT.json','RAW_CERTIFICATE_RECOUNTS.json.gz','RAW_POSTPROCESS_TERMINAL.json'])
 files.extend(H/n for n in reg['source_sha256']);files.extend(H/n for n in ['pack_f002_native_source.py','launch_f002_native.py','postprocess_f002_native.py','make_f002_native_remote_receipt.py','snapshot_f002_native_isolation.py','f002_native_direct_audit.py','audit_f002_final.py','independent_raw_recount.py','INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json','check_f002_native_direct_audit.py','prepare_f002_native_controller.py','formal/F001_I002_40x30/FINAL_AUDIT_STATS.json','BASELINE_S10.json','CASES.json','REFERENCE_SHA256.json','LSS_DATA_REFERENCE.json','RAW_REFERENCE.json','research/F002_native_audit_preflight/ACTUAL_COMPLETED_FIXTURE_CHECK.json','research/F002_native_catalogue_preflight/ACTUAL_READONLY_CHECK.json'])
 files.extend(H/formal['candidate']/n for n in formal['source_sha256']);files.extend(H/n for n in formal['vendor_sha256']);files.extend(H/v['path'] for v in cat.values());files.extend(H/v['alias']['path'] for v in check['added_aliases']);files.extend(H/v['alias']['path'] for v in check['base_check']['aliases']);files.extend(H/'reference'/v['path'] for v in json.load(open(H/'REFERENCE_SHA256.json'))['files']);files=sorted(set(files))
 files.extend([H/'check_f002_native_controller_structure.py',H/'research/F002_native_audit_preflight/CONTROL_FLOW_IDENTITY.json'])
 for p in files:
  if not p.is_file():raise RuntimeError('Missing actual protocol source before any ZIP creation '+str(p))
 for n,d in {**reg['source_sha256'],**reg['input_sha256']}.items():
  if sha(H/n)!=d:raise RuntimeError('Registered source/input changed before packet')
 with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.relative_to(H).as_posix())
 with zipfile.ZipFile(out) as z:
  if z.testzip() is not None:raise RuntimeError('Native protocol CRC failed')
 m=dict(file=out.name,bytes=out.stat().st_size,sha256=sha(out),zip_CRC_passed=True,scope='actual complete1200attempt registration and original native protocol/source/completed catalogue; full per-run search payloads referenced by registration SHA and delivered in final40case record archives; no new F002MC yet',files=[dict(path=p.relative_to(H).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files])
 with manifest.open('x') as f:json.dump(m,f,indent=2)
 T=H/'artifact/research/F002_I016_formal_native';T.mkdir(parents=True,exist_ok=True)
 for p in [out,manifest]+list(D.glob('*.json')):shutil.copy2(p,T/p.name)
 print(json.dumps({k:v for k,v in m.items() if k!='files'}))
if __name__=='__main__':pack()
