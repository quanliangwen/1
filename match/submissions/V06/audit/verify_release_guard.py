from pathlib import Path
import copy,hashlib,importlib.util,json,zipfile
root=Path(__file__).resolve().parent.parent;audit=root/'audit';negative=audit/'release_guard_negative_cases';negative.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('release_guard',r'E:\codex\swarm-submission-guard\check_submission_zip.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
archive=root/'team615_red_v06.zip';receipt=audit/'RELEASE_ABI_RECEIPT.json';proof=json.loads(receipt.read_text(encoding='utf-8'));results=[]
def rejected(label,p,r,profile,error):
 try:g.inspect_package(p,r,False,profile)
 except ValueError as e:
  assert str(e)==error,(label,str(e),error);results.append({'case':label,'status':'PASS','rejected_because':str(e)})
 else:raise AssertionError('Unexpected release acceptance: '+label)
# Preserve the old strict profile and its existing exact-ZIP ABI proof.
old=Path(r'E:\codex\PJ01_team615_red_v05_20261026\team615_red_v05.zip');old_proof=old.parent/'audit/RELEASE_ABI_RECEIPT.json'
assert g.inspect_package(old,old_proof)['status']=='PASS'
results.append({'case':'legacy_exact_pin_profile_unchanged','status':'PASS','scope':'Local ABI validation only; old official V05 failure remains recorded'})
rejected('v06_requires_explicit_new_profile',archive,receipt,'pinned','all_dependencies_exact_pins')
rejected('cannot_reuse_v05_abi_receipt',archive,old_proof,'sdk-inherit-v06','abi_receipt_bound_to_actual_zip')
for label,modify,error in [
 ('missing_numpy2_run',lambda x:x['abi_runs'].pop('numpy2'),'two_numpy_branches_required'),
 ('incorrect_receipt_team',lambda x:x.update(team_number='wLoPV5EE'),'sdk_reads_team615'),
 ('missing_real_random_check',lambda x:x['abi_runs']['numpy2'].update(numeric_random_pandas_cv_operations='SKIPPED'),'numpy2_real_numeric_operations'),
 ('run_bound_to_different_archive',lambda x:x['abi_runs']['numpy1'].update(submission_zip_sha256='0'*64),'numpy1_receipt_exact_zip_and_payload'),
]:
 p=negative/(label+'.json');bad=copy.deepcopy(proof);modify(bad);p.write_text(json.dumps(bad),encoding='utf-8');rejected(label,archive,p,'sdk-inherit-v06',error)
# Check the actual YAML field, not only receipt metadata.
bad_zip_dir=negative/'wrong_team';bad_zip_dir.mkdir(exist_ok=True);bad_zip=bad_zip_dir/'team615_red_v06.zip'
with zipfile.ZipFile(archive) as src,zipfile.ZipFile(bad_zip,'w',compression=zipfile.ZIP_DEFLATED) as dst:
 for n in src.namelist():
  data=src.read(n)
  if n=='team_info.yml':data=data.replace(b'team_number: 615',b'team_number: wLoPV5EE')
  dst.writestr(n,data)
rejected('actual_zip_string_team_identifier',bad_zip,receipt,'sdk-inherit-v06','team_number_yaml_integer_615')
assert g.inspect_package(archive,receipt,False,'sdk-inherit-v06')['status']=='PASS'
results.append({'case':'actual_final_v06_still_passes','status':'PASS'})
out={'status':'PASS','scope':'Release-tool regression only; no algorithm or simulation execution. Test ZIPs remain under audit/ and are not submission deliverables.','cases':results,'guard_sha256':hashlib.sha256(Path(g.__file__).read_bytes()).hexdigest()}
(audit/'RELEASE_GUARD_REGRESSION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','checks':len(results),'original_zip_unchanged':hashlib.sha256(archive.read_bytes()).hexdigest()==proof['submission_zip_sha256']}))
