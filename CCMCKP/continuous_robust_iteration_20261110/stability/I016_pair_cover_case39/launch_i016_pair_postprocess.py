from pathlib import Path
import json,time,subprocess
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;S=H/'stability/I016_pair_cover_case39'
if any((S/name).exists() for name in ['POSTPROCESS_REGISTRATION.json','postprocess.log','POSTPROCESS_TERMINAL.json','INDEPENDENT_SEARCH_RAW_AUDIT.json']):raise RuntimeError('Stability postprocessing may already run; inspect actual PID')
preflight=json.load(open(H/'research/P016_audit_preflight/LINEAGE_PREFLIGHT.json'))
if not preflight['passed'] or preflight['auditor_sha256']!=sha(H/'audit_i016_pair_stability39.py'):raise RuntimeError('Actual matching real-input/adversarial lineage preflight required')
launch=json.load(open(S/'LAUNCH.json'));process=Path('/proc')/str(launch['pid'])/'cmdline'
if not (S/'SEARCH_FINISHED').exists() and (not process.exists() or b'run_i016_pair_stability39.py' not in process.read_bytes()):raise RuntimeError('Original search is not confirmed live')
drivers=['postprocess_i016_pair_stability39.py','audit_i016_pair_stability39.py','independent_raw_recount.py','research/P016_audit_preflight/LINEAGE_PREFLIGHT.json'];reg=dict(time=time.time(),search_controller_pid=launch['pid'],drivers={name:sha(H/name) for name in drivers},scope='all6frozen searches first, then full independent source/raw audit; no original native calls or3/30Avg')
with (S/'POSTPROCESS_REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
with (S/'postprocess.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'postprocess_i016_pair_stability39.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
record=dict(time=time.time(),pid=p.pid,search_controller_pid=launch['pid'],registration_sha256=sha(S/'POSTPROCESS_REGISTRATION.json'),scope=reg['scope'])
with (S/'POSTPROCESS_LAUNCH.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
