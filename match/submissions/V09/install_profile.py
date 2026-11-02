from pathlib import Path
import ast,hashlib
F=Path(__file__).resolve().parent;G=F.parent/'swarm-submission-guard/check_submission_zip.py';backup=F/'audit/check_submission_zip_before_v09.py';assert not backup.exists();backup.write_bytes(G.read_bytes());s=G.read_text()
needle="def inspect_package(path,receipt=None,static_only=False,dependency_profile='pinned'):\n";assert s.count(needle)==1
s=s.replace(needle,needle+"    if dependency_profile=='p48-sdk-v09':\n        from p48_v09_release_profile import inspect_p48_v09\n        return inspect_p48_v09(path,receipt,static_only)\n")
needle="choices=['pinned','sdk-inherit-v06','j17-portable-v07','j17-gurobi-v08']";assert s.count(needle)==1;s=s.replace(needle,"choices=['pinned','sdk-inherit-v06','j17-portable-v07','j17-gurobi-v08','p48-sdk-v09']")
ast.parse(s);G.write_text(s,encoding='utf8');print('Added explicit V09-only dispatch; old profile bodies unchanged')
