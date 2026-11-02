from pathlib import Path
import json,shutil,zipfile,hashlib
F=Path(__file__).resolve().parent;R=Path('/home/junhao/quan/parallel_test_solver/match');H=F.parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((H/'PJ01_rules_P134_P35_route_pareto_last_slot_20261102/WORKSPACE_READY.json').read_text())['versions']['P48Reference'];W=Path(base['workspace']);assert all(sha(W/n)==h for n,h in base['sdk_files'].items())
manifest=json.loads((F/'CANDIDATE_MANIFEST.json').read_text());source=F/'versions/P154_CORNER_ASTAR/source';archive=F/'versions/P154_CORNER_ASTAR/P154_corner_cluster_research.zip';assert sha(archive)==manifest['sha256']
# Only our just-generated import cache is removable; never source/results.
cache=source/'__pycache__';removed=[]
if cache.exists():
 assert cache.resolve().is_relative_to(F.resolve())
 for p in cache.iterdir():assert p.is_file()and p.suffix=='.pyc';removed.append(p.name);p.unlink()
 cache.rmdir()
assert {p.name:sha(p)for p in source.iterdir()}==manifest['payload_files']
new=F/'actual_zip_workspace';assert not new.exists();shutil.copytree(W,new,ignore=shutil.ignore_patterns('solutions','__pycache__','*.pyc','.git'))
sol=new/'src/swarm_rescue/solutions';sol.mkdir()
with zipfile.ZipFile(archive)as z:
 for n,h in manifest['payload_files'].items():
  b=z.read(n);assert hashlib.sha256(b).hexdigest()==h;(new/'req.txt'if n=='req.txt'else sol/n).write_bytes(b)
assert all(sha(new/n)==h for n,h in base['sdk_files'].items())
paths={('req.txt'if n=='req.txt'else'src/swarm_rescue/solutions/'+n):h for n,h in manifest['payload_files'].items()}
(F/'WORKSPACE_READY.json').write_text(json.dumps(dict(versions={'P154_CORNER_ASTAR':dict(workspace=str(new),sources=paths,sdk_files=base['sdk_files'])}),indent=2)+'\n')
(F/'INTERNAL_ZIP_BINDING.json').write_text(json.dumps(dict(zip=str(archive),source=str(source),sha256=sha(archive),payload_files=manifest['payload_files'],integer615=True,official_submission_ready=False),indent=2)+'\n')
(F/'OWN_GENERATED_CACHE_CLEANUP.json').write_text(json.dumps(dict(removed_own_pyc=removed,scientific_files_deleted=False),indent=2)+'\n');print('Actual A* ZIP and original SDK bound')
