from pathlib import Path
import argparse,json,subprocess,time
from isolated_original_lss import sha
from register_completed_pool_prefix import PROFILES
H=Path(__file__).resolve().parent
def launch(profile):
 cfg=PROFILES[profile];D=H/cfg['study'];number='005' if profile=='P016' else '006'
 if any((D/n).exists() for n in ['POSTPROCESS_REGISTRATION.json','POSTPROCESS_LAUNCH.json','postprocess.log','INDEPENDENT_FINAL_AUDIT.json']):raise RuntimeError('Native postprocessing may already run; inspect actual PID')
 original=json.load(open(D/'LAUNCH.json'));p=Path('/proc')/str(original['pid'])/'cmdline'
 if not (D/'FINISHED').exists() and (not p.exists() or cfg['controller'].encode() not in p.read_bytes()):raise RuntimeError('Original native controller not confirmed live')
 drivers=['postprocess_completed_pool_prefix.py','register_completed_pool_prefix.py','summarize_completed_prefix.py','snapshot_d'+number+'_isolation.py','audit_d'+number+'_prefix.py','independent_raw_recount.py'];reg=dict(time=time.time(),native_controller_pid=original['pid'],cohort=profile,drivers={n:sha(H/n) for n in drivers},scope='observe actual same native controller then independent complete-prefix/raw/ledger/isolation audit and strictly-scoped development comparison')
 with (D/'POSTPROCESS_REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
 with (D/'postprocess.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'postprocess_completed_pool_prefix.py'),'--cohort',profile],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 row=dict(time=time.time(),pid=p.pid,native_controller_pid=original['pid'],registration_sha256=sha(D/'POSTPROCESS_REGISTRATION.json'))
 with (D/'POSTPROCESS_LAUNCH.json').open('x') as f:json.dump(row,f,indent=2)
 print(json.dumps(row))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort',choices=sorted(PROFILES),required=True);launch(p.parse_args().cohort)
