"""Observe registered D004, then actual independent audits, never restart MC."""
from pathlib import Path
import json,subprocess,time,os
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;D=H/'research/D004_I016_full_prefix';reg=json.load(open(D/'POSTPROCESS_REGISTRATION.json'));out=D/'POSTPROCESS_TERMINAL.json'
if out.exists():raise RuntimeError('Already terminal; inspect actual evidence')
started=time.monotonic();error=None;steps=[]
try:
 for name,digest in reg['drivers'].items():
  if sha(H/name)!=digest:raise RuntimeError('Pinned postprocessor/auditor changed')
 while not (D/'FINISHED').exists():
  process=Path('/proc')/str(reg['native_controller_pid'])/'cmdline'
  if not process.exists() or b'run_d004_i016_prefix.py' not in process.read_bytes():raise RuntimeError('D004 controller missing without terminal; no automatic restart')
  (D/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='waiting_actual_D004_complete_prefixes',time=time.time())));time.sleep(5)
 for name,digest in reg['drivers'].items():
  if sha(H/name)!=digest:raise RuntimeError('Pinned auditor changed while waiting')
 for name,args in [('snapshot_d004_isolation.py',['--phase','after']),('audit_d004_i016_prefix.py',[])]:
  (D/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage=name,time=time.time())));tick=time.monotonic();p=subprocess.run(['/home/junhao/miniconda3/bin/python','-u',str(H/name)]+args,cwd=H,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),timeout=3600);steps.append(dict(driver=name,exit=p.returncode,wall=time.monotonic()-tick))
  if p.returncode:raise RuntimeError('Actual D004 independent postprocessing failed '+name)
except Exception as ex:error=str(ex)
result=dict(passed=error is None,error=error,steps=steps,wall_including_wait=time.monotonic()-started,scope='actual single-prefix direct audit and single engineering evidence; no new MC or30formalAvg')
with out.open('x') as f:json.dump(result,f,indent=2)
(D/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='failed' if error else 'completed',time=time.time(),error=error)));print(json.dumps(result),flush=True)
if error:raise SystemExit(1)
