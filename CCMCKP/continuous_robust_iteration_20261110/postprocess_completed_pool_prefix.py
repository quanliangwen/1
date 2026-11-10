from pathlib import Path
import argparse,json,subprocess,time,os
from isolated_original_lss import sha
from register_completed_pool_prefix import PROFILES
H=Path(__file__).resolve().parent
def process(profile):
 cfg=PROFILES[profile];D=H/cfg['study'];reg=json.load(open(D/'POSTPROCESS_REGISTRATION.json'));out=D/'POSTPROCESS_TERMINAL.json'
 if out.exists():raise RuntimeError('Postprocessing already terminal')
 started=time.monotonic();error=None;steps=[]
 try:
  for n,d in reg['drivers'].items():
   if sha(H/n)!=d:raise RuntimeError('Pinned independent postprocessor changed')
  while not (D/'FINISHED').exists():
   p=Path('/proc')/str(reg['native_controller_pid'])/'cmdline'
   if not p.exists() or cfg['controller'].encode() not in p.read_bytes():raise RuntimeError('Original native controller missing without terminal; no automatic restart')
   (D/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='waiting_actual_native_prefixes',time=time.time())));time.sleep(5)
  for n,d in reg['drivers'].items():
   if sha(H/n)!=d:raise RuntimeError('Pinned independent auditor changed while waiting')
  number='005' if profile=='P016' else '006'
  for name,args in [('snapshot_d'+number+'_isolation.py',['--phase','after']),('audit_d'+number+'_prefix.py',[]),('summarize_completed_prefix.py',['--cohort',profile])]:
   (D/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage=name,time=time.time())));tick=time.monotonic();p=subprocess.run(['/home/junhao/miniconda3/bin/python','-u',str(H/name)]+args,cwd=H,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),timeout=3600);steps.append(dict(driver=name,exit=p.returncode,wall=time.monotonic()-tick))
   if p.returncode:raise RuntimeError('Actual complete independent postprocessing failed '+name)
 except Exception as ex:error=str(ex)
 value=dict(passed=error is None,error=error,steps=steps,wall_including_wait=time.monotonic()-started,scope='actual '+cfg['scope']+'; no new MC or formal30Avg')
 with out.open('x') as f:json.dump(value,f,indent=2)
 (D/'POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='failed' if error else 'completed',time=time.time(),error=error)));print(json.dumps(value),flush=True)
 if error:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort',choices=sorted(PROFILES),required=True);process(p.parse_args().cohort)
