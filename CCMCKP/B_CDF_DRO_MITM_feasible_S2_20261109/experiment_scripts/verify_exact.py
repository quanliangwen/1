import os,sys,pathlib,itertools,json,math
from fractions import Fraction
from types import SimpleNamespace
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
H=pathlib.Path(__file__).parent;sys.path[:0]=[str(H/'vendor313'),str(H/'source_v2')]
from exact_oracle import ExactOracle
cases=[([['0','0.25','0.75'],['0.1','0.6'],['0','0.333333333333333333333333333333']],'1.1'),([['0.5','0.6'],['0.5','0.4']],'1'),([['0']*99+['1']],'1'),([['0','2'],['0','0.1']],'1'),([['0.999999999999999999999999999999']],'1'),([['1.000000000000000000000000000001']],'1')]
rows=[]
for index,(arrays,T) in enumerate(cases):
 root=H/'exact_tests'/str(index);root.mkdir(parents=True,exist_ok=True)
 for j,a in enumerate(arrays):(root/f'{j}_sample.txt').write_text('\n'.join(a))
 inst=SimpleNamespace(path=root,validate_selection=lambda s:tuple(s));o=ExactOracle(inst,T);sel=tuple(range(len(arrays)));D=math.prod(map(len,arrays));truth=sum(sum(x)<Fraction(T) for x in itertools.product(*[[Fraction(a) for a in row] for row in arrays]))
 for bins in [16,256,4096]:
  v=o.certify(sel,bins,True);lo=int(v['lower_numerator']);hi=int(v['upper_numerator']);assert lo<=truth<=hi and int(v['denominator'])==D
  width=D.bit_length()+1;mask=(1<<width)-1;cutmask=(1<<(width*bins))-1
  for up,expected in [(True,lo),(False,hi)]:
   product=1
   for j in sel:
    factor=sum(1<<(width*int(k)) for k in o.quantized(j,bins,up) if k<bins);product=(product*factor)&cutmask
   count=sum((product>>(width*k))&mask for k in range(bins));assert count==expected
  if v['accepted']:assert 100*truth>=99*D
 rows.append(dict(test=index,exact_true_count=truth,denominator=D,all_grids_and_independent_integer_backend_match=True))
root=H/'exact_tests/large_denominator';root.mkdir(exist_ok=True)
for j in range(50):(root/f'{j}_sample.txt').write_text('\n'.join(['0']*499+['1']))
o=ExactOracle(SimpleNamespace(path=root,validate_selection=lambda s:tuple(s)),1);v=o.certify(tuple(range(50)),256,True);assert int(v['lower_numerator'])==499**50 and int(v['denominator'])==500**50
rows.append(dict(test='50 marginals and 449-bit denominator',passed=True))
(H/'EXACT_VERIFICATION.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
