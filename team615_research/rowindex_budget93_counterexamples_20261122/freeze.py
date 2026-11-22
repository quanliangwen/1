from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import ast,difflib,json
ROOT=Path(__file__).resolve().parent
H=lambda data:sha256(data).hexdigest()
with ZipFile(ROOT/'rowindex_baseline_snapshot.zip') as z:
    before={n:z.read(n) for n in z.namelist()};infos=z.infolist()
after={n:(ROOT/'candidate'/n).read_bytes() for n in before}
changed=[n for n in before if before[n]!=after[n]]
assert changed==['deadline_submission.py','red_hooks.py'],changed
assert len(before)==56 and after['line_regularization.py']==before['line_regularization.py']
patch=[]
for n in changed:
    patch.extend(difflib.unified_diff(before[n].decode().splitlines(keepends=True),after[n].decode().splitlines(keepends=True),fromfile='rowindex/'+n,tofile='budget93/'+n))
(ROOT/'CHANGES.patch').write_text(''.join(patch),encoding='utf8',newline='\n')
with ZipFile(ROOT/'candidate_snapshot.zip','w') as z:
    for info in infos:
        data=after[info.filename]
        if info.filename.endswith('.py'):compile(data,info.filename,'exec')
        z.writestr(info,data)
def cls(data,name):return next(n for n in ast.parse(data).body if isinstance(n,ast.ClassDef) and n.name==name)
dump=lambda n:ast.dump(n,include_attributes=False)
assert dump(cls(before['deadline_submission.py'],'DeadlineSubmission'))==dump(cls(after['deadline_submission.py'],'DeadlineSubmission'))
def methods(data):return {n.name:n for n in cls(data,'RedHooks').body if isinstance(n,ast.FunctionDef)}
a,b=methods(before['red_hooks.py']),methods(after['red_hooks.py'])
changed_methods=[n for n in a if dump(a[n])!=dump(b[n])]
assert changed_methods==['__init__','_own_map_bid','control'],changed_methods
added=[n for n in b if n not in a]
assert added==['_budget_submission_candidate','_budget_submission_gate','_try_budget_submission']
# The original control body remains byte-for-byte equivalent at AST level,
# after removing the single new early-exit call.
control=ast.parse(ast.unparse(b['control'])).body[0]
removed=[n for n in control.body if isinstance(n,ast.If) and isinstance(n.test,ast.Call) and isinstance(n.test.func,ast.Attribute) and n.test.func.attr=='_try_budget_submission']
assert len(removed)==1
control.body.remove(removed[0]);assert dump(control)==dump(a['control'])
with ZipFile(ROOT.parent/'team615_red_v16_first30_release_20261121/delivery/team615_red_v16.zip') as z:
    assert H((ROOT.parent/'team615_red_v16_first30_release_20261121/delivery/team615_red_v16.zip').read_bytes())=='e98990cfd9269ab521621bc97d7c9e81e21fa83bb83dafbfefb3943480dd6791'
    assert [n for n in before if before[n]!=z.read(n)]==['line_regularization.py']
data=dict(status='PASS',release_status='RESEARCH_CANDIDATE_NOT_COMPETITION_RELEASE',
    baseline='frozen row-index candidate',baseline_zip_sha256=H((ROOT/'rowindex_baseline_snapshot.zip').read_bytes()),
    candidate_zip_sha256=H((ROOT/'candidate_snapshot.zip').read_bytes()),
    baseline_files={n:H(d) for n,d in before.items()},candidate_files={n:H(d) for n,d in after.items()},
    changed_files=changed,unchanged_files=54,changed_existing_methods=changed_methods,added_methods=added,
    deadline_class_ast_unchanged=True,original_control_ast_unchanged_except_budget_hook=True,
    row_index_fit_bytes_unchanged=True,wall_margin_seconds=1.5,budget_window_5400=[5022,5051],
    stale_stock_threshold_steps=360,new_full_matches=0,simulation_steps=0,V16_remains_competition_baseline=True)
(ROOT/'BUILD.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in data.items() if k not in ['baseline_files','candidate_files']},indent=2))
