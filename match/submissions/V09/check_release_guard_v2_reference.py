from pathlib import Path
import importlib.util,json,hashlib,zipfile,sys
F=Path(__file__).resolve().parent;A=F/'audit';G=F.parent/'swarm-submission-guard';sys.path.insert(0,str(G));dest=A/'GUARD_REGRESSION_V2_REFERENCE_FIXED.json';assert not dest.exists()
spec=importlib.util.spec_from_file_location('actual_guard',G/'check_submission_zip.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
old=(A/'check_submission_zip_before_v09.py').read_text();new=(G/'check_submission_zip.py').read_text();insert="    if dependency_profile=='p48-sdk-v09':\n        from p48_v09_release_profile import inspect_p48_v09\n        return inspect_p48_v09(path,receipt,static_only)\n"
assert new.replace(insert,'').replace("choices=['pinned','sdk-inherit-v06','j17-portable-v07','j17-gurobi-v08','p48-sdk-v09']","choices=['pinned','sdk-inherit-v06','j17-portable-v07','j17-gurobi-v08']")==old
paths=[(F.parent/'PJ01_team615_red_v05_20261026/team615_red_v05.zip','pinned'),(F.parent/'PJ01_team615_red_v06_20261029/team615_red_v06.zip','sdk-inherit-v06'),(F.parent/'J17_team615_red_v07_20261030/team615_red_v07.zip','j17-portable-v07'),(F.parent/'J17_gurobi_team615_red_v08_20261030/team615_red_v08.zip','j17-gurobi-v08')]
legacy=[]
for p,profile in paths:
 if not p.exists()and profile=='sdk-inherit-v06':p=Path('E:/10.12-10.26算法对抗赛/提交版本呢/正常版/team615_red_v06.zip')
 assert p.exists(),p
 r=m.inspect_package(p,static_only=True,dependency_profile=profile);assert r['status']=='STATIC_ONLY_PASS_NOT_RELEASED';legacy.append(dict(profile=profile,sha256=r['sha256'],status=r['status']))
actual=F/'team615_red_v09.zip';r=m.inspect_package(actual,static_only=True,dependency_profile='p48-sdk-v09');assert r['status']=='STATIC_ONLY_PASS_NOT_RELEASED'
negative=[];D=A/'negative_cases';D.mkdir()
for name,change in [('string_team',lambda d:d.update({'team_info.yml':b'team_number: wLoPV5EE\n'})),('wrong_dependencies',lambda d:d.update({'req.txt':b'numpy==2.0.0\n'})),('bundled_environment',lambda d:d.update({'.venv/library.so':b'bad'})),('commercial_solver',lambda d:d.update({'bad.py':b'import gurobipy\n'})),('missing_entry',lambda d:d.pop('my_drone_eval.py'))]:
 q=D/name;q.mkdir();z=q/actual.name
 with zipfile.ZipFile(actual)as a:payload={n:a.read(n)for n in a.namelist()}
 change(payload)
 with zipfile.ZipFile(z,'w')as a:
  for n,b in payload.items():a.writestr(n,b)
 try:m.inspect_package(z,static_only=True,dependency_profile='p48-sdk-v09')
 except ValueError as e:negative.append(dict(case=name,rejected=True,reason=str(e)))
 else:raise AssertionError(name)
try:m.inspect_package(actual,dependency_profile='p48-sdk-v09')
except ValueError as e:negative.append(dict(case='no_new_ABI_receipt',rejected=True,reason=str(e)))
else:raise AssertionError('Missing ABI accepted')
out=dict(status='PASS',old_profile_bodies_unchanged=True,old_static_profiles=legacy,new_static=r,negative_cases=negative,limits='Mutated archive cases are rejected at whole-tested-archive SHA gate; do not claim each downstream branch was independently covered.')
dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(status=out['status'],old_profiles=len(legacy),negative_cases=len(negative))))
