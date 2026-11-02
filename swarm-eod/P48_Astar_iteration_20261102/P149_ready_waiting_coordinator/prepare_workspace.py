from pathlib import Path
import hashlib
import json
import shutil

F=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((F/'BASE_WORKSPACE.json').read_text())['versions']['P48_ASTAR']
manifest=json.loads((F/'CANDIDATE_MANIFEST_FIRST.json').read_text())
W=Path(base['workspace'])
assert all(sha(W/n)==h for n,h in base['sources'].items())
assert all(sha(W/n)==h for n,h in base['sdk_files'].items())
S=F/'candidate_project'
assert all(sha(S/n)==h for n,h in manifest['candidate_files'].items())
new=F/'workspace_P149'
assert not new.exists()
shutil.copytree(W,new,ignore=shutil.ignore_patterns('solutions','__pycache__','*.pyc','.git'))
for n in manifest['candidate_files']:
    p=new/n
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((S/n).read_bytes())
assert(new/'req.txt').read_bytes()==(W/'req.txt').read_bytes()
assert all(sha(new/n)==h for n,h in base['sdk_files'].items())
out=dict(status='INDEPENDENT_ASTARA_JOINT_WAITING_SOURCE_BOUND',versions={'P149':dict(workspace=str(new),sources=manifest['candidate_files'],sdk_files=base['sdk_files'])},sdk_modified=False,dependencies_modified=False)
(F/'WORKSPACE_READY.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(status=out['status'],source_files=len(manifest['candidate_files']),sdk_files=len(base['sdk_files']))))
