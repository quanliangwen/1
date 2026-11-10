from pathlib import Path
import json,zipfile,hashlib,shutil
H=Path(__file__).resolve().parent;D=H/'formal/F002_I016_40x30';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def pack():
 reg=json.load(open(D/'REGISTRATION.json'));out=D/'F002_FROZEN_SEARCH_SOURCE.zip';manifest=D/'SOURCE_MANIFEST.json'
 if out.exists() or manifest.exists():raise RuntimeError('No formal source freeze overwrite')
 S=H/reg['candidate'];inputs=[D/'REGISTRATION.json',H/'CASES.json',H/'RAW_REFERENCE.json',H/'register_f002.py',H/'pack_f002_search_source.py',H/'make_f002_search_remote_receipt.py']+[H/n for n in reg['driver_sha256']]+[H/n for n in reg['eligibility_proof_sha256']]+list(S.glob('*.py'))+[H/n for n in reg['vendor_sha256']]
 for name in ['D005_I016_pair_prefix','D006_I016_breadth_prefix']:
  Dn=H/'research'/name
  for n in ['REGISTRATION.json','RESULT.json','CATALOGUE.json','CATALOGUE_CHECK.json','POSTPROCESS_TERMINAL.json','FORMAL_ISOLATION_BEFORE.json','FORMAL_ISOLATION_AFTER.json']:inputs.append(Dn/n)
 inputs=sorted(set(inputs))
 for n,d in {**reg['driver_sha256'],**reg['eligibility_proof_sha256'],**reg['vendor_sha256']}.items():
  if sha(H/n)!=d:raise RuntimeError('Qualified source/eligibility proof changed')
 with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in inputs:z.write(p,p.relative_to(H).as_posix())
 with zipfile.ZipFile(out) as z:assert z.testzip() is None
 m=dict(file=out.name,bytes=out.stat().st_size,sha256=sha(out),zip_CRC_passed=True,scope='F0021200 registered search attempts not yet launched; frozen22optimizer/dependencies/scheduling/full6+8development eligibility; raw data referenced by SHA; native validation separately preregistered after whole1200search+raw audit',files=[dict(path=p.relative_to(H).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in inputs])
 with manifest.open('x') as f:json.dump(m,f,indent=2)
 T=H/'artifact/formal/F002_I016_40x30';T.mkdir(parents=True,exist_ok=True)
 for p in [out,manifest,D/'REGISTRATION.json']:shutil.copy2(p,T/p.name)
 print(json.dumps({k:v for k,v in m.items() if k!='files'}))
if __name__=='__main__':pack()
