import pathlib,json,zipfile,hashlib
H=pathlib.Path(__file__).parent;I=H/'iterations/I001_risk_portfolio';out=I/'I001_DEVELOPMENT_RECORDS.zip'
if not (I/'pilot/FINISHED').exists() or not (I/'pilot_validation/FINISHED').exists():raise RuntimeError('Incomplete pilot')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for folder in ['pilot','pilot_validation','candidate']:
  for p in sorted((I/folder).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:z.write(p,p.relative_to(I).as_posix())
 for name in ['REGISTRATION.json','PILOT_LAUNCH.json','PRE_REGISTRATION_REMOTE_VERIFIED.json','PROGRESS.json','pilot_search.log','pilot_validation.log','smoke.json.gz','smoke.json.gz.run.json','smoke.log']:z.write(I/name,name)
 for name in ['run_i001_pilot.py','validate_i001_pilot.py','RISK_MATH_CHECK.json','CACHE_BOOTSTRAP_MANIFEST.json']:z.write(H/name,'pipeline/'+name)
with zipfile.ZipFile(out) as z:
 if z.testzip() is not None:raise RuntimeError('Bad archive CRC')
meta=dict(path=out.name,bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),runs=28,validation=28,qualified=28,improved=0,stage='single-seed development, not formal30-run Avg',new_native_MC_calls=0,cache_provenance='380 original S10 calls, identical source/data/seed/vector keys')
(I/'ARCHIVE_MANIFEST.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta))
