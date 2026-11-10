from pathlib import Path
import json,time,subprocess
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;S=H/'breadth/I016_priority_four'
if any((S/name).exists() for name in ['POSTPROCESS_REGISTRATION.json','postprocess.log','POSTPROCESS_TERMINAL.json','INDEPENDENT_SEARCH_RAW_AUDIT.json']):raise RuntimeError('Stability postprocessing may already run; inspect actual PID')
preflight=json.load(open(H/'research/B016_audit_preflight/LINEAGE_PREFLIGHT.json'))
if not preflight['passed'] or preflight['auditor_sha256']!=sha(H/'audit_i016_priority_breadth.py'):raise RuntimeError('Actual matching real-input/adversarial lineage preflight required')
namespace=json.load(open(H/'research/B016_audit_preflight/CAPACITY_NAMESPACE_MATH_CHECK.json'))
if not namespace['passed'] or namespace['auditor_sha256']!=sha(H/'audit_i016_priority_breadth.py'):raise RuntimeError('Actual capacity namespace math check required')
launch=json.load(open(S/'LAUNCH.json'));process=Path('/proc')/str(launch['pid'])/'cmdline'
if not (S/'SEARCH_FINISHED').exists() and (not process.exists() or b'run_i016_priority_breadth.py' not in process.read_bytes()):raise RuntimeError('Original search is not confirmed live')
drivers=['postprocess_i016_priority_breadth.py','audit_i016_priority_breadth.py','independent_raw_recount.py','research/B016_audit_preflight/LINEAGE_PREFLIGHT.json','research/B016_audit_preflight/CAPACITY_NAMESPACE_MATH_CHECK.json'];reg=dict(time=time.time(),search_controller_pid=launch['pid'],drivers={name:sha(H/name) for name in drivers},scope='all8frozen searches first, then full independent source/raw audit; no original native calls orpercase/crosscaseAvg')
with (S/'POSTPROCESS_REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
with (S/'postprocess.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'postprocess_i016_priority_breadth.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
record=dict(time=time.time(),pid=p.pid,search_controller_pid=launch['pid'],registration_sha256=sha(S/'POSTPROCESS_REGISTRATION.json'),scope=reg['scope'])
with (S/'POSTPROCESS_LAUNCH.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
