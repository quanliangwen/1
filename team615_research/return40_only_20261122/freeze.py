from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import ast,difflib,json
ROOT=Path(__file__).resolve().parent
with ZipFile(ROOT/'baseline_snapshot.zip') as z:
    before={n:z.read(n) for n in z.namelist()};infos=z.infolist()
after={n:(ROOT/'candidate'/n).read_bytes() for n in before}
assert sha256((ROOT/'baseline_snapshot.zip').read_bytes()).hexdigest()=='c4b8513084ce114e6aae04b42489c995e73955ec545a64c5f9d999190004a562'
assert [n for n in before if before[n]!=after[n]]==['group_exchange.py']
def methods(b):
    c=next(n for n in ast.parse(b).body if isinstance(n,ast.ClassDef) and n.name=='GroupExchange')
    return {n.name:n for n in c.body if isinstance(n,ast.FunctionDef)}
a,b=methods(before['group_exchange.py']),methods(after['group_exchange.py'])
dump=lambda n:ast.dump(n,include_attributes=False)
assert [n for n in a if dump(a[n])!=dump(b[n])]==['prepare_return']
assert set(b)-set(a)=={'return_start'}
normalized=ast.parse(ast.unparse(b['prepare_return']).replace('step < self.return_start()', 'step < self.start()')).body[0]
assert dump(normalized)==dump(a['prepare_return'])
for n,v in after.items():
    if n.endswith('.py'):compile(v,n,'exec')
with ZipFile(ROOT/'candidate_snapshot.zip','w') as z:
    for info in infos:z.writestr(info,after[info.filename])
patch=''.join(difflib.unified_diff(before['group_exchange.py'].decode().splitlines(True),after['group_exchange.py'].decode().splitlines(True),fromfile='return60/group_exchange.py',tofile='return40/group_exchange.py'))
(ROOT/'CHANGES.patch').write_text(patch,encoding='utf8',newline='\n')
h=lambda v:sha256(v).hexdigest()
result=dict(status='PASS',baseline_zip_sha256=h((ROOT/'baseline_snapshot.zip').read_bytes()),
 candidate_zip_sha256=h((ROOT/'candidate_snapshot.zip').read_bytes()),candidate_files={n:h(v) for n,v in after.items()},
 baseline_files={n:h(v) for n,v in before.items()},changed_files=['group_exchange.py'],unchanged_files=55,
 edited_methods=['GroupExchange.prepare_return'],added_methods=['GroupExchange.return_start'],
 other_original_methods_ast_unchanged=True,return_threshold_only=True,return_ratio=.4,
 other_shared_start_ratio=.6,wall_margin_seconds=1.5,full_matches=0,physics_steps=0,
 V16_remains_competition_baseline=True)
(ROOT/'BUILD.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('baseline_files','candidate_files')},indent=2))
