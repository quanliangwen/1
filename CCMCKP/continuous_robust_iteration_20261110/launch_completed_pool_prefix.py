from pathlib import Path
import argparse,json,time,subprocess
from isolated_original_lss import sha
from register_completed_pool_prefix import PROFILES
H=Path(__file__).resolve().parent
def launch(profile):
 cfg=PROFILES[profile];D=H/cfg['study'];reg=json.load(open(D/'REGISTRATION.json'));v=json.load(open(D/'PRE_REG_REMOTE_VERIFIED.json'))
 if any((D/n).exists() for n in ['LAUNCH.json','study.log','RESULT.json','FINISHED']) or any((D/'receipts').iterdir()):raise RuntimeError('Actual prefix study may already run; never repeat')
 if not v['independent_remote_verification'] or v['registration_sha256']!=sha(D/'REGISTRATION.json'):raise RuntimeError('Actual remote registered source verification required')
 for n,digest in {**reg['source_sha256'],**reg['input_sha256']}.items():
  if sha(H/n)!=digest:raise RuntimeError('Registered frozen source/input changed')
 with (D/'study.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/cfg['controller'])],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 row=dict(time=time.time(),pid=p.pid,workers=4,pre_registered_commit=v['commit'],registration_sha256=sha(D/'REGISTRATION.json'),scope=reg['scope'],all_new_receipts_private=True)
 with (D/'LAUNCH.json').open('x') as f:json.dump(row,f,indent=2)
 print(json.dumps(row))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort',choices=sorted(PROFILES),required=True);launch(p.parse_args().cohort)
