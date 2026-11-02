from pathlib import Path
import json,hashlib,shutil
F=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((F/'BASE_WORKSPACE.json').read_text())['versions']['P48_ASTAR']
W=Path(base['workspace']);assert all(sha(W/n)==h for n,h in base['sources'].items());assert all(sha(W/n)==h for n,h in base['sdk_files'].items())
manifest=json.loads((F/'CANDIDATE_MANIFEST_V2.json').read_text())
S=F/'candidate_project';assert all(sha(S/n)==h for n,h in manifest['candidate_files'].items())
new=F/'workspace_P159';assert not new.exists()
shutil.copytree(W,new,ignore=shutil.ignore_patterns('solutions','__pycache__','*.pyc','.git'))
for n in manifest['candidate_files']:
 p=new/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((S/n).read_bytes())
assert(new/'req.txt').read_bytes()==(W/'req.txt').read_bytes()
assert all(sha(new/n)==h for n,h in base['sdk_files'].items())
out=dict(versions={'P48_ASTAR':base,'P159':dict(workspace=str(new),sources=manifest['candidate_files'],sdk_files=base['sdk_files'])},dependencies_modified=False,sdk_modified=False)
(F/'WORKSPACE_READY.json').write_text(json.dumps(out,indent=2)+'\n');print('SDK and independent candidate source SHA bound')
