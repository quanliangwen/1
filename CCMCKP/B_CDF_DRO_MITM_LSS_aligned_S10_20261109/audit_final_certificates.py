"""Independent raw-decimal polynomial recount of externally selected vectors."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import pathlib,json,sys,hashlib,time,concurrent.futures,subprocess
H=pathlib.Path(__file__).parent
if '--one' in sys.argv:
 sys.path[:0]=[str(H/'frozen_candidate'),str(H/'vendor313')]
 from instance import load_instance
 from exact_oracle import ExactOracle
 source=pathlib.Path(sys.argv[2]);out=pathlib.Path(sys.argv[3]);data=json.load(open(source));selected=data['selected'];cases=json.load(open(H/'CASES.json'));c=next(c for c in cases if c['index']==data['index'])
 inst=load_instance('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance']);s=inst.validate_selection(selected['selection']);cost=inst.selection_cost(s)
 if abs(cost-selected['cost'])>1e-8:raise ArithmeticError('Cost mismatch')
 oracle=ExactOracle(inst,c['tmax'],'.99');history=[];final=None
 for bins in [1024,4096,16384,65536,262144,1048576]:
  v=oracle.certify(s,bins,True);history.append(v)
  if v['accepted']:final=v;break
  if v['infeasible']:raise ArithmeticError('Original raw .99 violated')
 if final is None:raise ArithmeticError('Independent recount unresolved')
 with out.open('x') as f:json.dump(dict(index=data['index'],selection=list(s),cost=cost,passed=True,certificate=final,refinement=history,source_postselection_sha256=hashlib.sha256(source.read_bytes()).hexdigest()),f,indent=2)
else:
 V=H/'validation';D=H/'final_certificates';D.mkdir(exist_ok=True)
 while not (V/'FINISHED').exists():time.sleep(5)
 unique={}
 for p in sorted(V.glob('*.postselection.json')):
  d=json.load(open(p))
  if d.get('accepted'):unique.setdefault(d['selected']['LSS_key'],p)
 def run(item):
  key,p=item;out=D/(key+'.json')
  if out.exists():return
  with open(D/(key+'.log'),'x') as f:r=subprocess.run(['/home/junhao/miniconda3/bin/python',str(H/'audit_final_certificates.py'),'--one',str(p),str(out)],stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  if r.returncode:raise RuntimeError('Independent certificate audit failed '+key)
 with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:list(pool.map(run,unique.items()))
 (D/'FINISHED').write_text(str(len(unique)));print('FINAL_CERTIFICATES_VERIFIED',len(unique),flush=True)
