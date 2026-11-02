from pathlib import Path
import json,zipfile,hashlib,shutil,ast,datetime
F=Path(__file__).resolve().parent;F.mkdir(exist_ok=True);A=F/'audit';A.mkdir(exist_ok=True)
P=Path('E:/codex/PJ01_rule_refinement_20261101/P55_P48_five_score_validation_20261101');binding=json.loads((P/'INTERNAL_ZIP_BINDING.json').read_text());B=Path('E:/codex/PJ01_rule_refinement_20261101/P50_P48_native_single/versions/P48/team615_red_P48_INTERNAL_RESEARCH_ONLY.zip')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(B)==binding['sha256']=='fcef716d6855e7c5048299048e8ebd8216c777663ed75faf2583155d1648abc9'
assert json.loads((P/'CAMPAIGN_CLIENT_REVIEW.json').read_text())['status']=='PASS'
r=json.loads((P/'RESULT.json').read_text());assert r['status']=='COMPLETE_FINITE_STAGED_CAMPAIGN'and not r['first_native_failure']
group=r['completed'][0];assert group['version']=='P48'and set(group['map_scores'])=={'Map01','Map02','Map03','Map04','Map05'}and sum(group['placed'].values())==50
out=F/'team615_red_v09.zip';assert not out.exists();shutil.copyfile(B,out)
with zipfile.ZipFile(out)as z:
 files={n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()};assert files==binding['payload_files']
 assert z.read('team_info.yml').decode().splitlines()[0]=='team_number: 615'
 assert z.read('req.txt').decode().split()==['numpy>=1.24.4','opencv-contrib-python>=4.10.0.84']
 assert all('/'not in n and'\\'not in n for n in files)
 for n in files:
  if n.endswith('.py'):
   tree=ast.parse(z.read(n).decode('utf-8-sig'))
   assert 'gurobi'not in z.read(n).decode().lower(),n
 source=F/'P48_v09_source';source.mkdir();sol=source/'solutions';sol.mkdir()
 for n in files:
  (source/'req.txt'if n=='req.txt'else sol/n).write_bytes(z.read(n))
 with zipfile.ZipFile(F/'P48_v09_source.zip','w',zipfile.ZIP_DEFLATED)as src:
  for p in sorted(source.rglob('*')):
   if p.is_file():src.write(p,p.relative_to(source).as_posix())
manifest=dict(status='PREPARED_NOT_RELEASED_PENDING_FRESH_ABI',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),submission_zip=str(out),submission_zip_sha256=sha(out),payload_files_sha256=files,reference_binding_sha256=sha(P/'INTERNAL_ZIP_BINDING.json'),python_payload_unchanged_from_tested_five=True,whole_zip_bytes_identical_to_tested_archive=True,team_number=615,requires_Gurobi=False,native_history=dict(status='PASS',mean=group['mean'],map_scores=group['map_scores'],placed=group['placed'],first_windows_raw_review='PASS',native_failure=False,new_native_rounds=0,result_sha256=sha(P/'RESULT.json'),campaign_review_sha256=sha(P/'CAMPAIGN_CLIENT_REVIEW.json')),official_container_verified=False)
(F/'BUILD.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(F/'team615_red_v09.zip.sha256').write_text(sha(out)+'  '+out.name+'\n')
print(json.dumps(dict(status=manifest['status'],sha256=sha(out),payload=len(files))))
