from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import ast, difflib, json

ROOT=Path(__file__).resolve().parent
H=lambda b:sha256(b).hexdigest()
with ZipFile(ROOT/'baseline_snapshot.zip') as z:
    before={n:z.read(n) for n in z.namelist()}
    infos=z.infolist()
assert H((ROOT/'baseline_snapshot.zip').read_bytes())=='0ed2e45090a6a8104c0a3bf92d8ac79382a7891eccb978ffaba8a72a2b06a449'
after={n:(ROOT/'candidate'/n).read_bytes() for n in before}
changed=sorted(n for n in before if before[n]!=after[n])
assert changed==['group_exchange.py','placement_preferences.py','red_hooks.py','second_drop_site.py'],changed
for n,b in after.items():
    if n.endswith('.py'):compile(b,n,'exec')
def methods(b,cls):
    c=next(n for n in ast.parse(b).body if isinstance(n,ast.ClassDef) and n.name==cls)
    return {n.name:ast.dump(n,include_attributes=False) for n in c.body if isinstance(n,ast.FunctionDef)}
allowed={
 'group_exchange.py':('GroupExchange',{'__init__','release','prepare_return','commit_return','receive','ordinary_submit_allowed','yield_first_round','can_finish','tick_navigation','try_submit'}),
 'placement_preferences.py':('PlacementPreferences',set()),
 'red_hooks.py':('RedHooks',{'control','_placement_block'}),
 'second_drop_site.py':('SecondDropSite',{'__init__'})}
changes={}
for n,(cls,whitelist) in allowed.items():
    a,b=methods(before[n],cls),methods(after[n],cls)
    edited={k for k in a if a[k]!=b[k]}
    assert edited==whitelist,(n,edited,whitelist)
    changes[n]=dict(edited=sorted(edited),added=sorted(set(b)-set(a)))
# All navigation geometry and fitting are byte-identical. The sole change in
# the navigation state machine is whether a local exchange is truly complete.
a=before['group_exchange.py'].decode().replace('\r\n','\n');b=after['group_exchange.py'].decode().replace('\r\n','\n')
start='        group=self.plan.branch_group\n';end='    def commit_return('
assert a[a.index(start):a.index(end)]==b[b.index(start):b.index(end)]
assert methods(before['group_exchange.py'],'GroupExchange')['go_root']==methods(after['group_exchange.py'],'GroupExchange')['go_root']
for cls,data in [('GroupExchange','group_exchange.py')]:
    def tick(s):
        tree=ast.parse(s);c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
        return next(n for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='tick_navigation')
    old=tick(before[data]);new=tick(after[data])
    new=ast.parse(ast.unparse(new).replace('self._exchange_acked(drone, step, self.group)','self.complete(self.group)')).body[0]
    assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
assert after['deadline_submission.py']==before['deadline_submission.py']
assert after['coverage_placement.py']==before['coverage_placement.py']
for name in ['_force_deadline_submission','_try_budget_submission','_budget_submission_gate','_own_map_bid','_prefer_own_submission','_receive_team_coordination']:
    assert methods(before['red_hooks.py'],'RedHooks')[name]==methods(after['red_hooks.py'],'RedHooks')[name],name
patch=[]
for n in changed:
    patch.extend(difflib.unified_diff(before[n].decode().splitlines(True),after[n].decode().splitlines(True),fromfile='budget93/'+n,tofile='finish_minimal/'+n))
(ROOT/'CHANGES.patch').write_text(''.join(patch),encoding='utf8',newline='\n')
with ZipFile(ROOT/'candidate_snapshot.zip','w') as z:
    for info in infos:z.writestr(info,after[info.filename])
data=dict(status='PASS',baseline_zip_sha256=H((ROOT/'baseline_snapshot.zip').read_bytes()),
 candidate_zip_sha256=H((ROOT/'candidate_snapshot.zip').read_bytes()),candidate_files={n:H(b) for n,b in after.items()},
 baseline_files={n:H(b) for n,b in before.items()},changed_files=changed,unchanged_files=len(before)-len(changed),methods=changes,
 fitting_and_navigation_geometry_unchanged=True,original_inventory_merge_unchanged=True,
 hard_and_budget_fallbacks_unchanged=True,wall_margin_seconds=1.5,full_matches=0,physics_steps=0,
 release_status='RESEARCH_CANDIDATE_ONLY',V16_remains_competition_baseline=True)
(ROOT/'BUILD.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in data.items() if k not in ('baseline_files','candidate_files','methods')},indent=2))
