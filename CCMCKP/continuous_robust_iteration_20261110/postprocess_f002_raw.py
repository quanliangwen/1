from pathlib import Path
import json,time,hashlib,subprocess,os
H=Path(__file__).resolve().parent;D=H/'formal/F002_I016_40x30';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def process():
 reg=json.load(open(D/'RAW_POSTPROCESS_REGISTRATION.json'));out=D/'RAW_POSTPROCESS_TERMINAL.json';started=time.monotonic();error=None;code=None
 if out.exists():raise RuntimeError('Raw postprocessor already terminal')
 try:
  for n,d in reg['drivers'].items():
   if sha(H/n)!=d:raise RuntimeError('Frozen raw auditor changed before wait')
  while not (D/'SEARCH_FINISHED').exists():
   p=Path('/proc')/str(reg['search_controller_pid'])/'cmdline'
   if not p.exists() or b'run_f002_search.py' not in p.read_bytes():raise RuntimeError('Actual registered controller missing without final marker; never restart automatically')
   (D/'RAW_POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='waiting actual original1200search controller',time=time.time())));time.sleep(5)
  for n,d in reg['drivers'].items():
   if sha(H/n)!=d:raise RuntimeError('Frozen raw auditor changed during wait')
  (D/'RAW_POSTPROCESS_STATE.json').write_text(json.dumps(dict(stage='independent all1200source/raw audit',time=time.time())))
  code=subprocess.run(['/home/junhao/miniconda3/bin/python','-u',str(H/'audit_f002_search.py')],cwd=H,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')).returncode
  if code:raise RuntimeError('Actual raw/source audit failed; preserve records and investigate')
  audit=json.load(open(D/'INDEPENDENT_SEARCH_RAW_AUDIT.json'))
  if not audit['integrity_passed'] or audit['registered_attempts']!=1200:raise RuntimeError('Complete actual integrity audit missing')
  if not audit['passed']:raise RuntimeError('Ordinary attempt/protocol errors retained; final1200qualification incomplete')
 except Exception as ex:error=str(ex)
 r=dict(passed=error is None,error=error,audit_exit=code,wall_including_wait=time.monotonic()-started,scope='actual all1200attempts, source/input/read/lineage/budgets and independent all-semantic original raw counts; no new native MC/finalAvg; separate native registration and remote verification required next')
 with out.open('x') as f:json.dump(r,f,indent=2)
 print(json.dumps(r),flush=True)
 if error:raise SystemExit(1)
if __name__=='__main__':process()
