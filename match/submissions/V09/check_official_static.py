from pathlib import Path
import sys,json,hashlib,shutil
F=Path(__file__).resolve().parent;W=Path(json.loads((F/'WORKSPACE_READY.json').read_text())['workspace']);sys.path.insert(0,str(W/'src'))
from swarm_rescue.submission_check import validate_submission
z=F/'team615_red_v09.zip';alias=F/'team615_preliminary.zip';assert not alias.exists();shutil.copyfile(z,alias)
r=validate_submission(alias);assert not r.errors,r.errors;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=dict(status='PASS',submission_zip_sha256=sha(z),alias_sha256=sha(alias),alias_name=alias.name,errors=r.errors,warnings=r.warnings,official_checker_path=str(W/'src/swarm_rescue/submission_check.py'))
(F/'OFFICIAL_STATIC_CHECK.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
