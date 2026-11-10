from pathlib import Path
import json,hashlib,time,subprocess
H=Path(__file__).resolve().parent;I=H/'iterations/I016_cdf_pair_cover';J=I/'engineering39';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if any((J/n).exists() for n in ['POSTPROCESS_REGISTRATION.json','POSTPROCESS_LAUNCH.json','postprocess.log','ASSESSMENT.json','INDEPENDENT_RAW_AUDIT.json']):raise RuntimeError('Postprocessing may already be running or done; inspect actual PID/evidence')
launch=json.load(open(J/'LAUNCH.json'));engineering=json.load(open(J/'REGISTRATION.json'));source={p.name:sha(p) for p in (I/'candidate').glob('*.py')}
if engineering['source_sha256']!=source or launch['registration_sha256']!=sha(J/'REGISTRATION.json'):raise RuntimeError('Frozen engineering identity differs')
command=Path('/proc')/str(launch['pid'])/'cmdline'
if not (J/'TERMINAL.json').exists() and (not command.exists() or b'run_i016_engineering39.py' not in command.read_bytes()):raise RuntimeError('Engineering is not confirmed live; inspect actual state')
drivers=['postprocess_i016_engineering39.py','audit_i016_engineering39.py','independent_raw_recount.py'];inputs=['iterations/I016_cdf_pair_cover/engineering39/REGISTRATION.json','INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json'];reg=dict(time=time.time(),engineering_pid=launch['pid'],source_sha256=source,driver_sha256={n:sha(H/n) for n in drivers},input_sha256={n:sha(H/n) for n in inputs},scope='wait same actual engineering then source/budget/pool audit and full independent raw recount; no original MC')
with (J/'POSTPROCESS_REGISTRATION.json').open('x') as f:json.dump(reg,f,indent=2)
with (J/'postprocess.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'postprocess_i016_engineering39.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
record=dict(time=time.time(),pid=p.pid,engineering_pid=launch['pid'],registration_sha256=sha(J/'POSTPROCESS_REGISTRATION.json'),scope=reg['scope'])
with (J/'POSTPROCESS_LAUNCH.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
