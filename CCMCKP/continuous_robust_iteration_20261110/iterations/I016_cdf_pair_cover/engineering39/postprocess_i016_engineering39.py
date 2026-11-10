"""One guarded actual-run structural audit and full raw recount, no original MC."""
from pathlib import Path
import json,hashlib,subprocess,time,os
H=Path(__file__).resolve().parent;I=H/'iterations/I016_cdf_pair_cover';J=I/'engineering39';reg=json.load(open(J/'POSTPROCESS_REGISTRATION.json'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out=J/'POSTPROCESS_TERMINAL.json';state=J/'POSTPROCESS_STATE.json'
if out.exists():raise RuntimeError('Postprocessing already terminal; inspect evidence')
def identities():
 for name,digest in reg['driver_sha256'].items():
  if sha(H/name)!=digest:raise RuntimeError('Registered audit driver changed')
 for name,digest in reg['input_sha256'].items():
  if sha(H/name)!=digest:raise RuntimeError('Registered engineering/audit input changed')
 if {p.name:sha(p) for p in (I/'candidate').glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Frozen22source changed')
started=time.monotonic();steps=[];error=None
try:
 identities();state.write_text(json.dumps(dict(stage='waiting_for_actual_engineering_terminal',pid=reg['engineering_pid'],time=time.time())))
 while not (J/'TERMINAL.json').exists():
  command=Path('/proc')/str(reg['engineering_pid'])/'cmdline'
  if not command.exists() or b'run_i016_engineering39.py' not in command.read_bytes():raise RuntimeError('Original engineering supervisor missing without terminal; do not restart automatically')
  if time.monotonic()-started>900:raise TimeoutError('Observation deadline; inspect the same engineering PID, do not restart')
  time.sleep(5)
 identities();terminal=json.load(open(J/'TERMINAL.json'))
 if terminal['exit']!=0:raise RuntimeError('Engineering terminal failed; preserve actual log and terminal')
 for name in ['audit_i016_engineering39.py']:
  state.write_text(json.dumps(dict(stage=name,time=time.time())));tick=time.monotonic();r=subprocess.run(['/home/junhao/miniconda3/bin/python','-u',str(H/name)],cwd=H,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),timeout=2400);steps.append(dict(driver=name,exit=r.returncode,wall=time.monotonic()-tick))
  if r.returncode:raise RuntimeError('Actual engineering audit failed: '+name)
except Exception as ex:error=str(ex)
result=dict(passed=error is None,error=error,steps=steps,wall_including_wait=time.monotonic()-started,registration_sha256=sha(J/'POSTPROCESS_REGISTRATION.json'),scope='actual frozen engineering structural/budget/source/input and full independent raw recount only; no new original-LSS MC or30-run statistics')
with out.open('x') as f:json.dump(result,f,indent=2)
state.write_text(json.dumps(dict(stage='failed' if error else 'completed',time=time.time(),error=error)));print(json.dumps(result),flush=True)
if error:raise SystemExit(1)
