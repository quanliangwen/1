import os,sys,pathlib,itertools,json,gzip,hashlib
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
H=pathlib.Path(__file__).parent;sys.path[:0]=[str(H/'vendor313'),str(H/'source_v2')]
from exact_oracle import ExactOracle
from instance import load_instance
inst=load_instance('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_5_5_30_');o=ExactOracle(inst,27);digest=hashlib.sha256();refuted=0;answer=None
for raw in sorted(itertools.product(*inst.groups),key=lambda s:(inst.selection_cost(s),s)):
 s=tuple(map(int,raw))
 for bins in [256,1024,4096,16384,65536,262144,1048576]:
  v=o.certify(s,bins,True);D=int(v['denominator']);up=v['accepted']
  if v['accepted'] or v['infeasible']:
   width=D.bit_length()+1;mask=(1<<width)-1;cut=(1<<(bins*width))-1;p=1
   for j in s:p=(p*sum(1<<(width*int(k)) for k in o.quantized(j,bins,up) if k<bins))&cut
   num=sum((p>>(width*k))&mask for k in range(bins));expected=int(v['lower_numerator'] if up else v['upper_numerator']);assert num==expected
   if v['accepted']:answer=dict(selection=list(s),cost=inst.selection_cost(s),certificate=v);break
   digest.update(json.dumps([list(s),bins,v['upper_numerator'],v['denominator']],separators=(',',':')).encode());refuted+=1;break
 if answer:break
r=json.load(gzip.open(H/'smoke/c25.json.gz','rt'));assert r['exhaustive']['refuted']==refuted and r['exhaustive']['refutations_sha256']==digest.hexdigest() and r['selected']['selection']==answer['selection']
result=dict(total_selections=3125,all_cheaper_selections_proved_infeasible=refuted,independent_integer_backend=True,answer=answer,refutations_sha256=digest.hexdigest());(H/'CASE25_OPTIMALITY.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
