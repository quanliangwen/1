from pathlib import Path
import json,subprocess,time
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;D=H/'research/D003_paired_stability_prefix'
if any((D/n).exists() for n in ['POSTPROCESS_REGISTRATION.json','POSTPROCESS_LAUNCH.json','postprocess.log','INDEPENDENT_FINAL_AUDIT.json']):raise RuntimeError('Postprocessing may already run; inspect actual PID')
launch=json.load(open(D/'LAUNCH.json'));process=Path('/proc')/str(launch['pid'])/'cmdline'
if not (D/'FINISHED').exists() and (not process.exists() or b'run_d003_stability_prefix.py' not in process.read_bytes()):raise RuntimeError('Original native controller not confirmed live')
drivers=['postprocess_d003_stability.py','snapshot_d003_isolation.py','audit_d003_stability_prefix.py','summarize_d003_paired_stability.py','independent_raw_recount.py'];reg=dict(time=time.time(),native_controller_pid=launch['pid'],drivers={n:sha(H/n) for n in drivers},scope='observe same D003 then independent six-prefix/raw-selected/physical-ledger/isolation audit then3developmentseedstatistics; no new MC')
with (D/'POSTPROCESS_REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
with (D/'postprocess.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'postprocess_d003_stability.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
row=dict(time=time.time(),pid=p.pid,native_controller_pid=launch['pid'],registration_sha256=sha(D/'POSTPROCESS_REGISTRATION.json'))
with (D/'POSTPROCESS_LAUNCH.json').open('x') as f:json.dump(row,f,indent=2)
print(json.dumps(row))
