from pathlib import Path
import json,hashlib,shutil
F=Path(__file__).resolve().parent;R=Path('/home/junhao/quan/parallel_test_solver/match');H=R/'solver_study/framework_screen_20261016/best87_independent_20261025';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((H/'PJ01_rules_P134_P35_route_pareto_last_slot_20261102/WORKSPACE_READY.json').read_text())['versions']['P48Reference'];W=Path(meta['workspace']);assert all(sha(W/n)==h for n,h in meta['sdk_files'].items())
build=json.loads((F/'BUILD.json').read_text());z=F/'team615_red_v09.zip';assert sha(z)==build['submission_zip_sha256']
new=F/'actual_zip_workspace';assert not new.exists();shutil.copytree(W,new,ignore=shutil.ignore_patterns('solutions','__pycache__','*.pyc','.git'))
sol=new/'src/swarm_rescue/solutions';sol.mkdir()
import zipfile
with zipfile.ZipFile(z)as archive:
 for n,h in build['payload_files_sha256'].items():
  b=archive.read(n);assert hashlib.sha256(b).hexdigest()==h
  (new/'req.txt'if n=='req.txt'else sol/n).write_bytes(b)
assert all(sha(new/n)==h for n,h in meta['sdk_files'].items())
(F/'WORKSPACE_READY.json').write_text(json.dumps(dict(workspace=str(new),sdk_files=meta['sdk_files'],submission_zip_sha256=sha(z)),indent=2)+'\n')
print(json.dumps(dict(status='ACTUAL_ZIP_EXTRACTED_SDK124_BOUND',payload=len(build['payload_files_sha256']))))
