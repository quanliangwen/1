from pathlib import Path
import json,time,hashlib,subprocess,os
H=Path(__file__).resolve().parent;F=H/'formal/F002_I016_40x30';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def launch():
 reg=json.load(open(F/'REGISTRATION.json'));receipt=json.load(open(F/'PRE_REG_REMOTE_VERIFIED.json'))
 if any((F/n).exists() for n in ['LAUNCH.json','search.log','SEARCH_FINISHED']) or ((F/'search').exists() and any((F/'search').iterdir())):raise RuntimeError('F002 may already run; inspect actual PID')
 if not receipt['independent_remote_verification'] or receipt['registration_sha256']!=sha(F/'REGISTRATION.json'):raise RuntimeError('Actual remote source/registration verification required before search')
 if sha(H/'CASES.json')!=reg['casebook_sha256']:raise RuntimeError('Frozen case/capacity book changed')
 if {p.name:sha(p) for p in (H/reg['candidate']).glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Frozen optimizer changed')
 for name,digest in {**reg['driver_sha256'],**reg['eligibility_proof_sha256'],**reg['vendor_sha256']}.items():
  if sha(H/name)!=digest:raise RuntimeError('Frozen source or complete eligibility proof changed')
 for name,digest in reg['raw_input_sha256'].items():
  if sha(Path(name))!=digest:raise RuntimeError('Original input changed')
 with (F/'search.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'run_f002_search.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'))
 row=dict(time=time.time(),pid=p.pid,runs=1200,pre_registered_commit=receipt['commit'],registration_sha256=sha(F/'REGISTRATION.json'),search_workers=reg['search_workers'],large_case_workers=reg['large_case_workers'],no_native_calls_in_search_controller=True,goal_status='active')
 with (F/'LAUNCH.json').open('x') as f:json.dump(row,f,indent=2)
 print(json.dumps(row))

if __name__=='__main__':launch()
