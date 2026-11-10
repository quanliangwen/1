from pathlib import Path
import json,time,subprocess,os
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;D=H/'research/F002_I016_formal_native';S=H/'formal/F002_I016_40x30'
def process():
 reg=json.load(open(D/'POSTPROCESS_REGISTRATION.json'));out=D/'POSTPROCESS_TERMINAL.json';started=time.monotonic();error=None;steps=[]
 if out.exists():raise RuntimeError('Final audit already terminal')
 try:
  for n,d in reg['drivers'].items():
   if sha(H/n)!=d:raise RuntimeError('Pinned independent final auditor changed')
  while not (D/'FINISHED').exists():
   p=Path('/proc')/str(reg['native_controller_pid'])/'cmdline'
   if not p.exists() or b'run_f002_native.py' not in p.read_bytes():raise RuntimeError('Original native controller missing; no automatic restart')
   (D/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='waiting same actual original native controller',time=time.time())));time.sleep(5)
  for n,d in reg['drivers'].items():
   if sha(H/n)!=d:raise RuntimeError('Pinned independent auditor changed during native stage')
  for name,args in [('snapshot_f002_native_isolation.py',['--phase','after']),('audit_f002_final.py',[])]:
   (D/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage=name,time=time.time())));tick=time.monotonic();p=subprocess.run(['/home/junhao/miniconda3/bin/python','-u',str(H/name)]+args,cwd=H,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'));steps.append(dict(driver=name,exit=p.returncode,wall=time.monotonic()-tick))
   if p.returncode:raise RuntimeError('Actual independent final audit failed '+name)
  stats=json.load(open(S/'FINAL_AUDIT_STATS.json'))
  if not stats['integrity_passed'] or stats['registered_attempts']!=1200:raise RuntimeError('Whole1200 original-attempt integrity proof missing')
  if not stats['all1200_qualified']:raise RuntimeError('All1200 retained; at least one trial failed qualification/protocol; incomplete case Avg/Std kept missing')
 except Exception as ex:error=str(ex)
 r=dict(passed=error is None,error=error,steps=steps,wall_including_wait=time.monotonic()-started,scope='actual whole1200trial source/raw/native/ledger/isolation final independent audit; Excel/record archives still require authoring and verification')
 with out.open('x') as f:json.dump(r,f,indent=2)
 print(json.dumps(r),flush=True)
 if error:raise SystemExit(1)
if __name__=='__main__':process()
