from pathlib import Path
import argparse,json,subprocess,time,os
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;D=H/'research/F002_I016_formal_native'
def verified():
 reg=json.load(open(D/'REGISTRATION.json'));m=json.load(open(D/'SOURCE_MANIFEST.json'));v=json.load(open(D/'PRE_REG_REMOTE_VERIFIED.json'))
 if not v['independent_remote_verification'] or v['registration_sha256']!=sha(D/'REGISTRATION.json') or v['source_zip_sha256']!=m['sha256'] or sha(D/m['file'])!=m['sha256']:raise RuntimeError('Actual verified native protocol changed')
 for row in m['files']:
  if sha(H/row['path'])!=row['sha256']:raise RuntimeError('Remotely frozen native/audit source or included proof changed')
 for n,d in {**reg['source_sha256'],**reg['input_sha256']}.items():
  if sha(H/n)!=d:raise RuntimeError('Actual registered source/input changed')
 return reg,v
def launch(phase):
 reg,v=verified()
 if phase=='native':
  if any((D/n).exists() for n in ['LAUNCH.json','study.log','RESULT.json','FINISHED']) or any((D/'receipts').iterdir()):raise RuntimeError('Native stage may already run; inspect actual PID')
  with (D/'study.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'run_f002_native.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
  row=dict(time=time.time(),pid=p.pid,pre_registered_commit=v['commit'],registration_sha256=sha(D/'REGISTRATION.json'),workers=4,original_search_attempts=1200,native_pools=len(reg['pools']),excluded_search_attempts=len(reg['excluded_attempts']),all_new_receipts_private=True,no_optimizer_feedback=True)
  with (D/'LAUNCH.json').open('x') as f:json.dump(row,f,indent=2)
 else:
  if any((D/n).exists() for n in ['POSTPROCESS_REGISTRATION.json','POSTPROCESS_LAUNCH.json','postprocess.log','INDEPENDENT_FINAL_AUDIT.json']):raise RuntimeError('Final audit may already run; inspect actual state')
  launch=json.load(open(D/'LAUNCH.json'));cmd=Path('/proc')/str(launch['pid'])/'cmdline'
  if not (D/'FINISHED').exists() and (not cmd.exists() or b'run_f002_native.py' not in cmd.read_bytes()):raise RuntimeError('Same original native controller not confirmed live')
  drivers=['postprocess_f002_native.py','snapshot_f002_native_isolation.py','audit_f002_final.py','f002_native_direct_audit.py','independent_raw_recount.py'];r=dict(time=time.time(),native_controller_pid=launch['pid'],drivers={n:sha(H/n) for n in drivers},pre_registered_commit=v['commit'],scope='same actual native controller then independent complete native/source/raw/accounting audit and honest all1200trial statistics; no MC by postprocessor')
  with (D/'POSTPROCESS_REGISTRATION.json').open('x') as f:json.dump(r,f,indent=2)
  with (D/'postprocess.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'postprocess_f002_native.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  row=dict(time=time.time(),pid=p.pid,native_controller_pid=launch['pid'],registration_sha256=sha(D/'POSTPROCESS_REGISTRATION.json'))
  with (D/'POSTPROCESS_LAUNCH.json').open('x') as f:json.dump(row,f,indent=2)
 print(json.dumps(row))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['native','post'],required=True);launch(p.parse_args().phase)
