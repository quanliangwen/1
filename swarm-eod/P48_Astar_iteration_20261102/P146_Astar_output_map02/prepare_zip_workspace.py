from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import yaml

F=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((F/'BASE_WORKSPACE.json').read_text())['versions']['P48_ASTAR']
W=Path(base['workspace'])
assert all(sha(W/n)==h for n,h in base['sources'].items())
assert all(sha(W/n)==h for n,h in base['sdk_files'].items())
binding=json.loads((F/'INTERNAL_ZIP_BINDING_LOCAL_FIRST.json').read_text())
z=F/'versions/P145/P145_internal_evaluation.zip'
assert sha(z)==binding['sha256']
source=F/'versions/P145/source'
assert {p.name:sha(p)for p in source.iterdir()}==binding['payload_files']
new=F/'actual_zip_workspace'
assert not new.exists()
shutil.copytree(W,new,ignore=shutil.ignore_patterns('solutions','__pycache__','*.pyc','.git'))
sol=new/'src/swarm_rescue/solutions'
sol.mkdir(parents=True)
with zipfile.ZipFile(z)as archive:
    assert len(archive.namelist())==len(set(archive.namelist()))==len(binding['payload_files'])
    assert {n:hashlib.sha256(archive.read(n)).hexdigest()for n in archive.namelist()}==binding['payload_files']
    team=yaml.safe_load(archive.read('team_info.yml'))
    assert type(team['team_number'])is int and team['team_number']==615
    assert archive.read('req.txt')==(W/'req.txt').read_bytes()
    for n in archive.namelist():
        assert '/'not in n and '\\'not in n
        (new/'req.txt'if n=='req.txt'else sol/n).write_bytes(archive.read(n))
assert all(sha(new/n)==h for n,h in base['sdk_files'].items())
sources={('req.txt'if n=='req.txt'else'src/swarm_rescue/solutions/'+n):h for n,h in binding['payload_files'].items()}
out=dict(status='ACTUAL_ASTARA_OUTPUT_ZIP_EXTRACTED',versions={'P145Zip':dict(workspace=str(new),sources=sources,sdk_files=base['sdk_files'])})
(F/'WORKSPACE_READY.json').write_text(json.dumps(out,indent=2)+'\n')
binding.update(source=str(source),zip=str(z),actual_extracted_workspace=str(new),integer615=True,actual_req_unchanged=True)
(F/'INTERNAL_ZIP_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
print(json.dumps(dict(status=out['status'],actual_zip_sha256=sha(z),payloads=len(sources),sdk_sources=len(base['sdk_files']))))
