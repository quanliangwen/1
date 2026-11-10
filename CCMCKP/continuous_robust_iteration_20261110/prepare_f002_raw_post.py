from pathlib import Path
import json,time,hashlib,zipfile,shutil,argparse,subprocess
H=Path(__file__).resolve().parent;D=H/'formal/F002_I016_40x30';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
 out=D/'RAW_POSTPROCESS_REGISTRATION.json'
 if out.exists():raise RuntimeError('No raw postprocess source/registration overwrite')
 launch=json.load(open(D/'LAUNCH.json'));check=H/'research/F002_lineage_preflight/ACTUAL_LINEAGE_CHECK.json';v=json.load(open(check))
 if not v['passed'] or v['fixtures']!=9 or v['lineage_source_sha256']!=sha(H/'f002_lineage.py'):raise RuntimeError('Actual9 real lineage fixtures required')
 drivers=['audit_f002_search.py','f002_lineage.py','audit_i016_priority_breadth.py','independent_raw_recount.py','postprocess_f002_raw.py','prepare_f002_raw_post.py'];inputs=[check,H/'research/F002_lineage_preflight/REGISTRATION.json',H/'INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json']
 r=dict(time=time.time(),search_controller_pid=launch['pid'],formal_registration_sha256=sha(D/'REGISTRATION.json'),drivers={n:sha(H/n) for n in drivers},input_sha256={p.relative_to(H).as_posix():sha(p) for p in inputs},scope='wait SAMEactual1200controller; complete whole-source/input/read/lineage/raw audit only afterfreeze; lineage real9fixture branch checked, full1200branch not yet executed; noMC/noAvg/noautomaticnative orsearchrestart')
 with out.open('x') as f:json.dump(r,f,indent=2)
 files=[out,D/'REGISTRATION.json']+[H/n for n in drivers]+inputs;zfile=D/'F002_FROZEN_RAW_AUDIT_SOURCE.zip'
 with zipfile.ZipFile(zfile,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.relative_to(H).as_posix())
 with zipfile.ZipFile(zfile) as z:assert z.testzip() is None
 m=dict(file=zfile.name,bytes=zfile.stat().st_size,sha256=sha(zfile),zip_CRC_passed=True,files=[dict(path=p.relative_to(H).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in files])
 with (D/'RAW_AUDIT_SOURCE_MANIFEST.json').open('x') as f:json.dump(m,f,indent=2)
 T=H/'artifact/formal/F002_I016_40x30';T.mkdir(exist_ok=True)
 for p in [out,zfile,D/'RAW_AUDIT_SOURCE_MANIFEST.json']:shutil.copy2(p,T/p.name)
 print(json.dumps({k:x for k,x in m.items() if k!='files'}))
def launch():
 r=json.load(open(D/'RAW_POSTPROCESS_REGISTRATION.json'));v=json.load(open(D/'RAW_POSTPROCESS_REMOTE_VERIFIED.json'))
 if any((D/n).exists() for n in ['RAW_POSTPROCESS_LAUNCH.json','raw_postprocess.log','RAW_POSTPROCESS_TERMINAL.json']):raise RuntimeError('Raw auditor may already run; inspect actual PID')
 if not v['independent_remote_verification'] or v['registration_sha256']!=sha(D/'RAW_POSTPROCESS_REGISTRATION.json'):raise RuntimeError('Actual remote raw-source/registration verification required')
 for n,d in {**r['drivers'],**r['input_sha256']}.items():
  if sha(H/n)!=d:raise RuntimeError('Registered raw auditor/input changed')
 with (D/'raw_postprocess.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'postprocess_f002_raw.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 row=dict(time=time.time(),pid=p.pid,search_controller_pid=r['search_controller_pid'],pre_registered_commit=v['commit'],registration_sha256=sha(D/'RAW_POSTPROCESS_REGISTRATION.json'))
 with (D/'RAW_POSTPROCESS_LAUNCH.json').open('x') as f:json.dump(row,f,indent=2)
 print(json.dumps(row))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['prepare','launch'],required=True);a=p.parse_args();prepare() if a.phase=='prepare' else launch()
