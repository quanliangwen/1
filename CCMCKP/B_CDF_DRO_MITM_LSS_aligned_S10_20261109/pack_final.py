import pathlib,json,zipfile,hashlib,collections
H=pathlib.Path(__file__).parent;A=H/'delivery';A.mkdir(exist_ok=True)
summary=json.load(open(H/'FINAL_SUMMARY.json'));mapping=collections.Counter();costs={}
for p in (H/'validation').glob('*.postselection.json'):
 d=json.load(open(p))
 if d.get('accepted'):mapping[d['selected']['LSS_key']]+=1
 for r in d['tested']:costs[r['key']]=r['cost']
mc=[]
for p in sorted((H/'validation/calls').glob('*.json')):
 d=json.load(open(p));key=p.stem;mc.append(dict(key=key,instance=d['instance'],capacity=d['capacity'],selection=d['selection'],cost=costs[key],seed=d['seed'],draws=d['draws'],real_probability=d['real_probability'],passed=d['passed'],seconds=d['seconds'],selected_run_count=mapping[key]))
(H/'MC_RECORDS.json').write_text(json.dumps(mc,indent=2))
for name in ['FINAL_SUMMARY.json','RUN_DETAILS.json','MC_RECORDS.json','FORMAL_LAUNCH_CONFIRMED.json','OLD_BEST_RAW_AUDIT.json']:
 (A/name).write_bytes((H/name).read_bytes())
if (H/'single_case_smoke/RESULT.json').exists():(A/'SINGLE_CASE_SMOKE_RESULT.json').write_bytes((H/'single_case_smoke/RESULT.json').read_bytes())
groups={
 'S10_FORMAL_1200_RUNS.zip':['formal30','formal_campaign.log','REGISTRATION.json','PRE_REGISTRATION_REMOTE_VERIFIED.json','FORMAL_LAUNCH_CONFIRMED.json'],
 'S10_LSS_VALIDATION_AND_CERTIFICATES.zip':['validation','validation.log','final_certificates','final_certificates.log','REFERENCE_SHA256.json','LSS_DATA_REFERENCE.json'],
 'S10_DEVELOPMENT_AND_SMOKE.zip':['development','development.log','development_validation','development_validation.log','development_source_v1','development_import_guard_attempt1','development_import_guard_attempt1.log','frozen_smoke','frozen_smoke.log','single_case_smoke','single_case_smoke.log','old_best_raw_audit','audit_old_raw.py','audit_old_raw.log','develop.py','frozen_smoke.py','check_interval_counts.py']
}
manifest=[]
for name,items in groups.items():
 out=A/name
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for item in items:
   p=H/item
   if not p.exists():continue
   files=sorted(p.rglob('*')) if p.is_dir() else [p]
   for f in files:
    if f.is_file() and '__pycache__' not in f.parts:z.write(f,f.relative_to(H).as_posix())
 with zipfile.ZipFile(out) as z:
  if z.testzip() is not None:raise RuntimeError('Bad archive CRC')
 manifest.append(dict(path=name,bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
(A/'ARCHIVE_MANIFEST.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
