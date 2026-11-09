import pathlib,zipfile,json,hashlib,shutil
H=pathlib.Path(__file__).resolve().parent;S=pathlib.Path('/home/quanliangwen/work/cdf_lss_aligned_S3_20261109');D=H/'delivery_archives';D.mkdir(exist_ok=True)
def pack(name,base,roots):
 out=D/name
 with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for root in roots:
   if not root.exists():continue
   for p in sorted(root.rglob('*')) if root.is_dir() else [root]:
    if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.lock'):z.write(p,str(p.relative_to(base)))
 with zipfile.ZipFile(out) as z:
  bad=z.testzip()
  if bad:raise RuntimeError('ZIP CRC failed: '+bad)
  n=len(z.infolist())
 print(json.dumps(dict(name=name,bytes=out.stat().st_size,members=n,sha256=hashlib.sha256(out.read_bytes()).hexdigest())))
if not (S/'S8_ABORTED_ATTEMPT_ACCOUNTING.json').exists():raise RuntimeError('S8 accounting not complete')
pack('S8_ABORTED_CAMPAIGN.zip',S,[S/n for n in ['formal30_lss','formal30_lss_validation','formal30_lss.log','formal30_lss_validation.log','S8_CAMPAIGN_ABORT_RECORD.json','S8_ABORTED_ATTEMPT_ACCOUNTING.json','S8_ABORTED_ACTIVE_STATUS.json','abort_S8_supervisor.py','account_S8_abort.py','account_S8_abort.log','formal_campaign.py','formal_lss_validate.py','frozen_candidate','FROZEN_SOURCE_SHA256.json']])
pack('DEVELOPMENT_AND_FAILURES.zip',H,[H/n for n in ['development','development_lss','deadline_stress','development.log','development_lss.log','deadline_stress.log','BATCH_GUIDANCE_VERIFICATION.json','FROZEN_DEVELOPMENT_SUMMARY.json','test_batch_guidance.py','stress_deadline.py','dev40.py','dev_validate.py','candidate']])
for name in ['DEVELOPMENT_AND_FAILURES.zip','OLD_COST_EXHAUSTION.zip']:
 target='EARLIER_DEVELOPMENT.zip' if name.startswith('DEVELOPMENT') else name
 shutil.copy2(S/'delivery_archives'/name,D/target)
 print(json.dumps(dict(name=target,bytes=(D/target).stat().st_size,sha256=hashlib.sha256((D/target).read_bytes()).hexdigest())))
