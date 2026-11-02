from pathlib import Path
import zipfile,hashlib,json,datetime
root=Path(__file__).resolve().parent.parent
project=Path(r'E:\codex\PJ01_SDK_inherit_source_20261029\candidate_project')
old=Path(r'E:\10.12-10.26算法对抗赛\提交版本呢\team615_red_v05.zip')
manifest=json.loads(Path(r'E:\codex\PJ01_SDK_inherit_source_20261029\SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for rel,sha in manifest['files_sha256'].items():assert hashlib.sha256((project/rel).read_bytes()).hexdigest()==sha
payload={p.name:p.read_bytes() for p in (project/'src/swarm_rescue/solutions').iterdir() if p.is_file()}
payload['req.txt']=(project/'req.txt').read_text(encoding='utf-8-sig').encode('ascii')
with zipfile.ZipFile(old) as z:
 assert set(payload)==set(z.namelist())
 assert [n for n,b in payload.items() if b!=z.read(n)]==['req.txt']
assert payload['req.txt']==b'numpy>=1.24.4\nopencv-contrib-python>=4.10.0.84\n'
assert b'team_number: 615' in payload['team_info.yml']
archive=root/'team615_red_v06.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,b in sorted(payload.items()):
  info=zipfile.ZipInfo(n,date_time=(2026,10,29,12,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=3;info.external_attr=0o100644<<16
  z.writestr(info,b)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'BUILT_PENDING_CHECKS','dependency_profile':'sdk-inherit-v06','submission_zip':str(archive),'submission_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'reference_v05_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'payload_files_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(payload.items())},'python_files_unchanged':36,'only_changed_file_vs_v05':'req.txt','dependency_change_reason':'User requested V06 from the SDK-inheritance candidate after V05 official ABI failure. Preserve compatible preinstalled SDK numeric libraries instead of forcing version replacement. No official portal/container verification.','packaging_note':'Normalize req.txt to LF ASCII; source candidate used valid CRLF.'}
(root/'audit/PACKAGE_MANIFEST.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for p in [Path(r'E:\codex\AGENTS.md'),Path(r'E:\codex\swarm-submission-guard\SUBMISSION_POLICY.txt'),Path(r'E:\codex\swarm-submission-guard\check_submission_zip.py')]:
 backup=root/'audit'/('before_'+p.name);assert not backup.exists();backup.write_bytes(p.read_bytes())
print(json.dumps({'zip':str(archive),'sha256':out['submission_zip_sha256'],'file_count':len(payload),'python_files_unchanged':36},ensure_ascii=False))
