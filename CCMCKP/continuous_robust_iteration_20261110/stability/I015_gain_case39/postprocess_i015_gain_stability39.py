from pathlib import Path
import json,subprocess,time,os
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;S=H/'stability/I015_gain_case39';reg=json.load(open(S/'POSTPROCESS_REGISTRATION.json'));out=S/'POSTPROCESS_TERMINAL.json'
if out.exists():raise RuntimeError('Actual stability postprocessing already terminal')
start=time.monotonic();error=None;code=None
try:
 for name,digest in reg['drivers'].items():
  if sha(H/name)!=digest:raise RuntimeError('Pinned stability audit source changed')
 while not (S/'SEARCH_FINISHED').exists():
  process=Path('/proc')/str(reg['search_controller_pid'])/'cmdline'
  if not process.exists() or b'run_i015_gain_stability39.py' not in process.read_bytes():raise RuntimeError('Original search controller missing without terminal; inspect same job, no automatic restart')
  (S/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='waiting_all6_actual_searches',time=time.time())));time.sleep(5)
 for name,digest in reg['drivers'].items():
  if sha(H/name)!=digest:raise RuntimeError('Pinned stability audit source changed while waiting')
 (S/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='auditing_all6_and_all_raw',time=time.time())));p=subprocess.run(['/home/junhao/miniconda3/bin/python','-u',str(H/'audit_i015_gain_stability39.py')],cwd=H,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),timeout=3600);code=p.returncode
 if code:raise RuntimeError('Actual complete stability source/raw audit failed')
except Exception as exception:error=str(exception)
result=dict(passed=error is None,error=error,audit_exit=code,wall_including_wait=time.monotonic()-start,scope='wait all6searches then independent all-source/all-raw audit only; no original MC orAvg')
with out.open('x') as f:json.dump(result,f,indent=2)
(S/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='failed' if error else 'completed',time=time.time(),error=error)));print(json.dumps(result),flush=True)
if error:raise SystemExit(1)
