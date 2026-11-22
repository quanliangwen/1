from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import ast,difflib,json
ROOT=Path(__file__).resolve().parent
H=lambda data:sha256(data).hexdigest()
with ZipFile(ROOT/'baseline_snapshot.zip') as z:
    before={n:z.read(n) for n in z.namelist()};infos=z.infolist()
assert H((ROOT/'baseline_snapshot.zip').read_bytes())=='e69ea77adb25b9ecbb8bd3a38f34f2241c35ad788c147aff67bc6d83e7c227e8'
after={n:(ROOT/'candidate'/n).read_bytes() for n in before}
changed=[n for n in before if before[n]!=after[n]]
assert set(changed)=={'drop_departure.py','red_hooks.py'}
for n,data in after.items():
    if n.endswith('.py'):compile(data,n,'exec')
def methods(data):
    tree=ast.parse(data)
    return {f'{c.name}.{m.name}':ast.dump(m,include_attributes=False)
            for c in tree.body if isinstance(c,ast.ClassDef)
            for m in c.body if isinstance(m,ast.FunctionDef)}
old,new=methods(before['red_hooks.py']),methods(after['red_hooks.py'])
assert old.keys()==new.keys() and [n for n in old if old[n]!=new[n]]==['RedHooks.control']
with ZipFile(ROOT/'candidate_snapshot.zip','w') as z:
    for info in infos:z.writestr(info,after[info.filename])
(ROOT/'CHANGES.patch').write_text(''.join(''.join(difflib.unified_diff(before[n].decode().splitlines(True),after[n].decode().splitlines(True),fromfile='return50/'+n,tofile='recovery_once/'+n)) for n in changed),encoding='utf8',newline='\n')
build=dict(status='PASS',baseline_zip_sha256=H((ROOT/'baseline_snapshot.zip').read_bytes()),
    candidate_zip_sha256=H((ROOT/'candidate_snapshot.zip').read_bytes()),
    baseline_files={n:H(v) for n,v in before.items()},candidate_files={n:H(v) for n,v in after.items()},
    changed_files=changed,unchanged_files=len(before)-len(changed),wall_margin_seconds=1.5,return_ratio=.5,
    full_matches=0,physics_steps=0,V16_remains_competition_baseline=True,
    candidate_only_not_competition_release=True)
(ROOT/'BUILD.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in build.items() if k not in ('baseline_files','candidate_files')},indent=2))
