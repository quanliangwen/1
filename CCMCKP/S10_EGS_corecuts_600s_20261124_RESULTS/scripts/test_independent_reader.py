from pathlib import Path
import ast,json,itertools
from fractions import Fraction
from collections import Counter
R=Path(__file__).resolve().parent
tree=ast.parse((R/'audit_remote.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='core_upper')
ns={'Counter':Counter};exec(compile(ast.Module(body=[node],type_ignores=[]),'independent_reader_function','exec'),ns)
orders=[[Fraction(x) for x in row] for row in [['.6','.8'],['0','0'],['.6','.8'],['0','0'],['0','.05'],['.02','.05'],['0','.05'],['.02','.05']]]
d={'groups':[[0,1],[2,3],[4,5],[6,7]],'sorted_exact':orders};checked=0
for reference in itertools.product(*d['groups']):
 for mask in range(16):
  active=[g for g in range(4) if mask>>g&1]
  rows=[orders[reference[g]] if g in active else [min(orders[j][k] for j in group) for k in range(2)] for g,group in enumerate(d['groups'])]
  brute=sum(sum((v*1024).__floor__() for v in pick)<1024 for pick in itertools.product(*rows))
  nu,de=ns['core_upper'](d,reference,active,1024,Fraction(1))
  assert (nu,de)==(brute,16),(reference,active,nu,brute);checked+=1
boundary={'groups':[[0],[1]],'sorted_exact':[[Fraction(1,2)]*2,[Fraction(1,2)]*2]}
assert ns['core_upper'](boundary,[0,1],[0,1],1024,Fraction(1))==(0,4)
report={'status':'PASS','independent_polynomial_vs_cartesian_cases':checked,'strict_equality_is_unsafe':True,'writer_imports':0,'solver_or_Monte_Carlo_calls':0}
(R/'INDEPENDENT_READER_UNIT_CHECK.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
