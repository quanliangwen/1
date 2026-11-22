from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import ast,difflib,json
ROOT=Path(__file__).resolve().parent
with ZipFile(ROOT/'baseline_snapshot.zip') as z:
    before={n:z.read(n) for n in z.namelist()};infos=z.infolist()
after={n:(ROOT/'candidate'/n).read_bytes() for n in before}
H=lambda b:sha256(b).hexdigest()
assert H((ROOT/'baseline_snapshot.zip').read_bytes())=='849714c8438fc9ec35b2327807b907133dc7c93bcd4b17a56d1dd0e47dafd8c4'
assert [n for n in before if before[n]!=after[n]]==['group_exchange.py']
needle=b'def return_start(self):return self.limit*2//5'
assert before['group_exchange.py'].replace(needle,b'def return_start(self):return self.limit//2')==after['group_exchange.py']
def methods(data):
    c=next(n for n in ast.parse(data).body if isinstance(n,ast.ClassDef) and n.name=='GroupExchange')
    return {n.name:ast.dump(n,include_attributes=False) for n in c.body if isinstance(n,ast.FunctionDef)}
a,b=methods(before['group_exchange.py']),methods(after['group_exchange.py'])
assert a.keys()==b.keys() and [n for n in a if a[n]!=b[n]]==['return_start']
for n,v in after.items():
    if n.endswith('.py'):compile(v,n,'exec')
with ZipFile(ROOT/'candidate_snapshot.zip','w') as z:
    for info in infos:z.writestr(info,after[info.filename])
(ROOT/'CHANGES.patch').write_text(''.join(difflib.unified_diff(before['group_exchange.py'].decode().splitlines(True),after['group_exchange.py'].decode().splitlines(True),fromfile='return40/group_exchange.py',tofile='return50/group_exchange.py')),encoding='utf8',newline='\n')
d=dict(status='PASS',baseline_zip_sha256=H((ROOT/'baseline_snapshot.zip').read_bytes()),candidate_zip_sha256=H((ROOT/'candidate_snapshot.zip').read_bytes()),
 baseline_files={n:H(v) for n,v in before.items()},candidate_files={n:H(v) for n,v in after.items()},changed_files=['group_exchange.py'],
 unchanged_files=55,edited_methods=['GroupExchange.return_start'],other_methods_ast_unchanged=True,return_ratio=.5,
 shared_submission_and_last_bomb_start_ratio=.6,wall_margin_seconds=1.5,full_matches=0,physics_steps=0,V16_remains_competition_baseline=True)
(ROOT/'BUILD.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in d.items() if k not in ('baseline_files','candidate_files')},indent=2))
