import pathlib,json,zipfile,hashlib
H=pathlib.Path(__file__).resolve().parent;S=json.load(open(H/'USER_VALIDATION_SUMMARY.json'));R=H/'delivery_archives';R.mkdir(exist_ok=True)
if S['solver_valid']!=1200 or S['lss_accepted']!=1200 or S['all_30_accepted_cases']!=40 or S['solver_errors'] or S['MC_integrity_errors']:raise RuntimeError('Packaging gate: require complete all-output probability validation')
reg=json.load(open(H/'formal30_lss/REGISTRATION.json'));current={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'frozen_candidate').glob('*.py')}
if current!=reg['source_sha256']:raise RuntimeError('Frozen source hash mismatch')
for row in S['rows']:
 if sorted(r['seed'] for r in row['runs'])!=list(range(940001,940031)):raise RuntimeError('Not30 fresh seeds: '+str(row['index']))
def pack(name,roots):
 entries=[]
 for root in roots:
  if not root.exists():raise RuntimeError('Missing archive source '+str(root))
  for p in sorted(root.rglob('*')) if root.is_dir() else [root]:
   if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.tmp'):entries.append((p,'S9/'+str(p.relative_to(H))))
 out=R/name
 if not out.exists():
  with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for p,arc in entries:z.write(p,arc)
 with zipfile.ZipFile(out) as z:
  if z.testzip():raise RuntimeError('ZIP CRC failed')
  if sorted(z.namelist())!=sorted(arc for p,arc in entries):raise RuntimeError('Archive members differ from complete source set')
 return dict(name=name,bytes=out.stat().st_size,members=len(entries),sha256=hashlib.sha256(out.read_bytes()).hexdigest())
results=[pack('FORMAL_1200_RECORDS.zip',[H/'formal30_lss',H/'formal30_lss.log',H/'FINAL_SUMMARY.json',H/'USER_VALIDATION_SUMMARY.json',H/'FROZEN_SOURCE_SHA256.json']),pack('LSS_FINAL_VALIDATIONS.zip',[H/'formal30_lss_validation',H/'formal30_lss_validation.log',H/'lss_real_eval.py',H/'lss_eval_reference'])]
(H/'FINAL_ARCHIVE_MANIFEST.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
