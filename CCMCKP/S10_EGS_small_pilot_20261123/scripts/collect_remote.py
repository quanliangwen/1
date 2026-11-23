from pathlib import Path
import hashlib,json,tarfile
H=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/work/egs_small_pilot_20261123')
files=[p for p in H.rglob('*') if p.is_file() and (p.relative_to(H).parts[0] in ['runs','outcomes'] or (p.parent==H and p.suffix in ['.json','.jsonl','.log','.txt','.py']))]
assert (H/'COMPLETED.json').exists()
with tarfile.open(H/'COMPACT_EVIDENCE_FULL.tar.gz','w:gz') as t:
 for p in files:t.add(p,arcname=p.relative_to(H).as_posix())
print(json.dumps({'files':len(files),'raw_bytes':sum(p.stat().st_size for p in files),'archive_bytes':(H/'COMPACT_EVIDENCE_FULL.tar.gz').stat().st_size,'sha256':hashlib.sha256((H/'COMPACT_EVIDENCE_FULL.tar.gz').read_bytes()).hexdigest()}))
