"""Check the new Python-only exact audit arithmetic, not the frozen solver."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
from itertools import product
import ast,json,subprocess
R=Path(__file__).resolve().parent
module=ast.parse((R/'audit_remote.py').read_text())
definition=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='independent_count')
namespace={'Counter':Counter,'Path':Path,'H':R,'subprocess':subprocess,'data':{1:{'capacity':Fraction(1),'atoms':[[Fraction(0),Fraction(1,3),Fraction(5,4)],[Fraction(1,7),Fraction(1,2)],[Fraction(0),Fraction(1,9),Fraction(2,3)]]}},'count_cache':{},'histogram_cache':{}}
exec(compile(ast.Module(body=[definition],type_ignores=[]),'<independent-reader>','exec'),namespace)
checks=0
for selection in [[0],[1],[0,1],[0,2],[0,1,2]]:
    for bins in [2,3,7,32,1024]:
        for up in [False,True]:
            direct=0;denominator=0
            for atoms in product(*(namespace['data'][1]['atoms'][j] for j in selection)):
                degrees=[]
                for atom in atoms:
                    r=atom*bins
                    q=(-(-r.numerator//r.denominator)) if up else r.numerator//r.denominator
                    degrees.append(min(bins,q))
                denominator+=1;direct+=sum(degrees)<bins
            assert namespace['independent_count'](1,selection,bins,up)==(direct,denominator)
            checks+=1
result={'status':'PASS','new_reader_exact_enumeration_checks':checks,'native_reader_helper':(R/'audit_count_helper').is_file(),'frozen_algorithm_reexecuted':False,'extra_MC':False}
(R/'AUDIT_READER_CHECKS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
